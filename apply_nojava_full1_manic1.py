#!/usr/bin/env python3
"""Promote MENUUI22 NOJAVA FAST1 into a source-clean native-only iOS baseline.

NOJAVA_FULL1 removes the core src/emu/j2me target and all historical Java/iOS
sources. MANIC_NATIVE1 preserves the proven Manic artwork/layout engine under a
native controls path and exposes it as layout 7 ("Manic") for Symbian/N-Gage.
"""
from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

MARK = "NOJAVA_FULL1_MANIC1"


def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: {msg}")


def find_braced(text: str, signature: str) -> tuple[int, int, int]:
    start = text.find(signature)
    if start < 0:
        fail(f"signature not found: {signature}")
    if text.find(signature, start + len(signature)) >= 0:
        fail(f"signature is not unique: {signature}")
    brace = text.find("{", start)
    if brace < 0:
        fail(f"opening brace not found: {signature}")

    depth = 0
    i = brace
    in_str = in_char = in_line = in_block = esc = False
    while i < len(text):
        ch = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ""
        if in_line:
            if ch == "\n":
                in_line = False
        elif in_block:
            if ch == "*" and nxt == "/":
                in_block = False
                i += 1
        elif in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        elif in_char:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == "'":
                in_char = False
        else:
            if ch == "/" and nxt == "/":
                in_line = True
                i += 1
            elif ch == "/" and nxt == "*":
                in_block = True
                i += 1
            elif ch == '"':
                in_str = True
            elif ch == "'":
                in_char = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return start, brace, i + 1
        i += 1
    fail(f"unterminated braced block: {signature}")


def remove_braced(text: str, signature: str, *, required: bool = False) -> str:
    if signature not in text:
        if required:
            fail(f"required block missing: {signature}")
        return text
    start, _, end = find_braced(text, signature)
    while end < len(text) and text[end] in " \t":
        end += 1
    if end < len(text) and text[end] == "\n":
        end += 1
    return text[:start] + text[end:]


def replace_method(text: str, signature: str, body: str, *, required: bool = True) -> str:
    if signature not in text:
        if required:
            fail(f"required method missing: {signature}")
        return text
    start, brace, end = find_braced(text, signature)
    prefix = text[start:brace].rstrip()
    replacement = prefix + " {\n" + body.rstrip() + "\n}"
    return text[:start] + replacement + text[end:]


def move_manic(app: Path) -> tuple[Path, Path]:
    old_root = app / "j2me"
    old_h = old_root / "J2MEManicControlsView.h"
    old_m = old_root / "J2MEManicControlsView.m"
    old_assets = old_root / "J2MEManicControls"
    for p in (old_h, old_m, old_assets / "info.json", old_assets / "dpad.png", old_assets / "thumbstick.png"):
        if not p.exists():
            fail(f"Manic source/resource missing: {p}")

    dst_root = app / "controls" / "manic"
    dst_assets = dst_root / "EKAManicControls"
    dst_root.mkdir(parents=True, exist_ok=True)
    if dst_assets.exists():
        shutil.rmtree(dst_assets)
    shutil.copytree(old_assets, dst_assets)

    h = old_h.read_text(encoding="utf-8")
    m = old_m.read_text(encoding="utf-8")
    for old, new in (
        ("J2MEManic", "EKAManic"),
        ("J2MEMANIC", "MANIC_NATIVE"),
        ("MIDP", "Symbian"),
    ):
        h = h.replace(old, new)
        m = m.replace(old, new)

    h = "// MANIC_NATIVE1: native Manic controls for Symbian/N-Gage.\n" + h
    m = "// MANIC_NATIVE1: native Manic controls for Symbian/N-Gage.\n" + m
    h_path = dst_root / "EKAManicControlsView.h"
    m_path = dst_root / "EKAManicControlsView.m"
    h_path.write_text(h, encoding="utf-8")
    m_path.write_text(m, encoding="utf-8")

    for p in (h_path, m_path):
        txt = p.read_text(encoding="utf-8")
        if re.search(r"J2ME|phoneME|PHONEME|MIDP", txt, re.I):
            fail(f"legacy Java token survived in native Manic source: {p}")
    return h_path, m_path


def clean_unified(app: Path) -> tuple[Path, Path]:
    old_root = app / "j2me"
    old_h = old_root / "EKAUnifiedLibraryViewController.h"
    old_m = old_root / "EKAUnifiedLibraryViewController.mm"
    if not old_h.is_file() or not old_m.is_file():
        fail("FAST1 unified controller missing")

    h = old_h.read_text(encoding="utf-8")
    m = old_m.read_text(encoding="utf-8")

    h = re.sub(
        r"\n\+ \(BOOL\)importJARAtPath:\(NSString \*\)path\n"
        r"\s+error:\(NSError \* _Nullable \* _Nullable\)error\n"
        r"\s+importedName:\(NSString \* _Nullable \* _Nullable\)importedName;\n",
        "\n",
        h,
        count=1,
    )

    m = m.replace("// NOJAVA_FAST1: shared launcher retained; Java/J2ME section removed.\n",
                  "// NOJAVA_FULL1: native Symbian/N-Gage launcher.\n")
    m = remove_braced(m, "static NSURL *EKAJ2MELibraryURL", required=False)
    for sig in (
        "+ (BOOL)importJARAtPath:",
        "- (NSArray<NSDictionary *> *)loadJ2MEGames",
        "- (void)closeJ2MEPlayer:",
        "- (void)openJ2MEProfile:",
        "- (void)deleteJ2ME:",
    ):
        m = remove_braced(m, sig, required=False)

    m = re.sub(r"(?m)^\s*NSMutableDictionary<NSString \*, UIImage \*> \*_j2meIcons;\n", "", m)
    m = re.sub(r"(?m)^\s*_j2meIcons = \[NSMutableDictionary dictionary\];\n", "", m)

    old_symbol = '''        NSString *symbol = [kind isEqualToString:@"j2me"] ? @"gamecontroller.fill" :
                           ([kind isEqualToString:@"ngage"] ? @"gamecontroller.fill" :
                           ([kind isEqualToString:@"system"] ? @"square.grid.2x2.fill" : @"app.fill"));'''
    new_symbol = '''        NSString *symbol = [kind isEqualToString:@"ngage"] ? @"gamecontroller.fill" :
                           ([kind isEqualToString:@"system"] ? @"square.grid.2x2.fill" : @"app.fill");'''
    if old_symbol in m:
        m = m.replace(old_symbol, new_symbol, 1)

    image_pat = re.compile(
        r'    UIImage \*image = nil;\n'
        r'    if \(\[item\[@"kind"\] isEqualToString:@"j2me"\]\) \{.*?'
        r'\n    \} else if \(item\[@"uid"\]\) \{\n'
        r'        image = _icons\[item\[@"uid"\]\];\n'
        r'    \}',
        re.S,
    )
    m, n = image_pat.subn('    UIImage *image = item[@"uid"] ? _icons[item[@"uid"]] : nil;', m, count=1)
    if n == 0 and 'isEqualToString:@"j2me"' in m:
        fail("could not remove stale J2ME icon branch from unified controller")

    m = m.replace('    if ([kind isEqualToString:@"j2me"]) return;\n', "")
    m = m.replace('        if ([section[@"kind"] isEqualToString:@"j2me"]) continue;\n', "")
    m = m.replace("NOJAVA_FAST1", "NOJAVA_FULL1")

    dst = app / "library"
    dst.mkdir(parents=True, exist_ok=True)
    h_path = dst / "EKAUnifiedLibraryViewController.h"
    m_path = dst / "EKAUnifiedLibraryViewController.mm"
    h_path.write_text(h, encoding="utf-8")
    m_path.write_text(m, encoding="utf-8")

    for p in (h_path, m_path):
        txt = p.read_text(encoding="utf-8")
        if re.search(r"J2ME|phoneME|PHONEME|importJAR|loadJ2ME", txt, re.I):
            fail(f"legacy Java token survived in native unified controller: {p}")
    return h_path, m_path


def clean_root(root: Path) -> None:
    text = root.read_text(encoding="utf-8")
    text = text.replace('#import "j2me/EKAUnifiedLibraryViewController.h"',
                        '#import "library/EKAUnifiedLibraryViewController.h"')
    for sig in (
        "static BOOL EKAIsJARPackagePath",
        "- (void)onJavaJ2ME",
        "- (void)closeJavaJ2ME:",
    ):
        text = remove_braced(text, sig, required=False)

    replacements = {
        "one icon library for Symbian, J2ME and N-Gage.": "one icon library for Symbian and N-Gage.",
        "// J2ME R1 PHONEME INTERPRETER\n": "",
        "four primary toolbar entries; Java lives inside Apps.": "four primary native toolbar entries.",
        "// NOJAVA_FAST1: JAR route removed; SIS/SISX/N-Gage routing preserved.":
            "// NOJAVA_FULL1: SIS/SISX/N-Gage routing only.",
        'message:@"Chọn JAR, SIS, SISX hoặc tệp .n-gage."':
            'message:@"Chọn SIS, SISX hoặc tệp .n-gage."',
        "NOJAVA_FAST1": "NOJAVA_FULL1",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)

    if re.search(r"J2ME|phoneME|PHONEME|onJavaJ2ME|EKAIsJARPackagePath|\bJAR\b", text, re.I):
        matches = sorted(set(re.findall(r"J2ME|phoneME|PHONEME|onJavaJ2ME|EKAIsJARPackagePath|\bJAR\b", text, re.I)))
        fail("RootViewController still contains Java route tokens: " + ", ".join(matches))
    root.write_text(text, encoding="utf-8")


def clean_controls(app: Path) -> None:
    h_path = app / "GameControlsView.h"
    m_path = app / "GameControlsView.mm"
    s_path = app / "GameSettingsViewController.mm"
    for p in (h_path, m_path, s_path):
        if not p.is_file():
            fail(f"native controls file missing: {p}")

    h = h_path.read_text(encoding="utf-8")
    m = m_path.read_text(encoding="utf-8")
    s = s_path.read_text(encoding="utf-8")
    for old, new in (
        ("J2MECONTROLS1", "NATIVE_CONTROLS1"),
        ("J2MEMANIC4", "MANIC_NATIVE1"),
        ("Java Flex", "Manic"),
        ("MIDP", "Symbian"),
    ):
        h = h.replace(old, new)
        m = m.replace(old, new)
        s = s.replace(old, new)

    # Strip any remaining historical naming from comments/markers. These three
    # native files no longer own or expose a Java runtime API.
    for old, new in (
        ("J2ME", "Native"),
        ("j2me", "native"),
        ("phoneME", "native"),
        ("PHONEME", "NATIVE"),
    ):
        h = h.replace(old, new)
        m = m.replace(old, new)
        s = s.replace(old, new)

    # Layout 7 was introduced for the old Java frontend; it is now the native
    # Manic layout shared by normal Symbian and N-Gage titles.
    if 'if (layout == 7) return @"Manic";' not in s:
        fail('layout 7 was not renamed to "Manic"')
    if "case 7:" not in m:
        fail("layout 7 missing from GameControlsView")

    for name, txt in (("GameControlsView.h", h), ("GameControlsView.mm", m), ("GameSettingsViewController.mm", s)):
        if re.search(r"J2ME|phoneME|PHONEME|Java Flex|MIDP", txt, re.I):
            fail(f"legacy Java marker survived in {name}")

    h_path.write_text(h, encoding="utf-8")
    m_path.write_text(m, encoding="utf-8")
    s_path.write_text(s, encoding="utf-8")


def wire_manic_into_root(root: Path) -> None:
    text = root.read_text(encoding="utf-8")

    import_anchor = '#import "GameControlsView.h"\n'
    manic_import = '#import "controls/manic/EKAManicControlsView.h"\n'
    if manic_import not in text:
        if import_anchor not in text:
            fail("GameControlsView import anchor missing")
        text = text.replace(import_anchor, import_anchor + manic_import, 1)

    prop_anchor = '@property (nonatomic, strong) GameControlsView *controlsView;\n'
    prop_line = '@property (nonatomic, strong) EKAManicControlsArtworkView *manicArtworkView;\n'
    if prop_line not in text:
        if prop_anchor not in text:
            fail("controlsView property anchor missing")
        text = text.replace(prop_anchor, prop_anchor + prop_line, 1)

    setup_anchor = '''    self.controlsView.hidden = YES;
    [self.view addSubview:self.controlsView];
'''
    setup = '''    self.controlsView.hidden = YES;
    [self.view addSubview:self.controlsView];

    // MANIC_NATIVE1: artwork is visual-only; GameControlsView remains the
    // authoritative Symbian scancode/hitbox engine.
    self.manicArtworkView = [[EKAManicControlsArtworkView alloc] initWithFrame:self.view.bounds];
    self.manicArtworkView.autoresizingMask = UIViewAutoresizingFlexibleWidth | UIViewAutoresizingFlexibleHeight;
    self.manicArtworkView.hidden = YES;
    [self.view addSubview:self.manicArtworkView];
    __weak typeof(self) weakManicSelf = self;
    self.controlsView.keyVisualOutput = ^(int32_t code, BOOL down) {
        [weakManicSelf.manicArtworkView setControlCode:code down:down];
    };
    self.controlsView.controlVisualOutput = ^(NSString *controlID, BOOL down) {
        [weakManicSelf.manicArtworkView setControlIdentifier:controlID down:down];
    };
'''
    if "MANIC_NATIVE1: artwork is visual-only" not in text:
        if setup_anchor not in text:
            fail("controlsView setup anchor missing")
        text = text.replace(setup_anchor, setup, 1)

    bring = "        [self.view bringSubviewToFront:self.controlsView];\n"
    if "bringSubviewToFront:self.manicArtworkView" not in text:
        if bring not in text:
            fail("controlsView z-order anchor missing")
        text = text.replace(
            bring,
            bring + "        [self.view bringSubviewToFront:self.manicArtworkView];\n",
            1,
        )

    body = '''    if (!self.gameRunning) {
        self.controlsView.customLayout = nil;
        self.controlsView.layout = 0;
        self.manicArtworkView.layout = @[];
        self.manicArtworkView.hidden = YES;
        [self.manicArtworkView resetControlVisualState];
        return;
    }
    EKAGameSettings *s = [GameSettingsStore settingsForUid:self.currentGameUid];
    BOOL portrait = self.view.bounds.size.height >= self.view.bounds.size.width;
    NSArray<NSDictionary *> *custom = portrait ? s.customLayoutPortrait : s.customLayoutLandscape;
    BOOL useManic = (self.keyLayout == 7);
    NSArray<NSDictionary *> *activeLayout = custom.count ? custom : nil;
    if (useManic && activeLayout.count == 0) {
        activeLayout = EKAManicDefaultControlLayout(self.view.bounds.size, self.traitCollection);
    }

    // The native Manic artwork occupies the exact same normalized frames used
    // by GameControlsView. Generic drawing is transparent only for layout 7;
    // touch/scancode semantics remain inside GameControlsView.
    self.controlsView.overlayOpacity = useManic ? 0.0 : s.controlsOpacity;
    self.controlsView.hapticsEnabled = s.hapticFeedback;
    self.controlsView.autoScaleButtons = [self autoScaleForCurrentOrientation];
    self.controlsView.customLayout = (activeLayout.count ? activeLayout : nil);
    self.controlsView.layout = self.keyLayout;

    self.manicArtworkView.layout = useManic ? (activeLayout ?: @[]) : @[];
    self.manicArtworkView.controlsOpacity = s.controlsOpacity;
    self.manicArtworkView.hidden = !useManic;
'''
    text = replace_method(text, "- (void)applyControls", body, required=True)

    if "EKAManicControlsArtworkView" not in text or "EKAManicDefaultControlLayout" not in text:
        fail("native Manic wiring did not land in RootViewController")
    root.write_text(text, encoding="utf-8")


def clean_core_j2me(up: Path) -> None:
    """Remove EKA2L1's host-side J2ME app-list plumbing from system core.

    This does not touch Symbian ROM ABI/export metadata (for example epoc9.def);
    those names describe guest-side compatibility and are not the iOS host J2ME
    runtime target we are removing.
    """
    h_path = up / "src/emu/system/include/system/epoc.h"
    cpp_path = up / "src/emu/system/src/epoc.cpp"
    for p in (h_path, cpp_path):
        if not p.is_file():
            fail(f"system core file missing: {p}")

    h = h_path.read_text(encoding="utf-8")
    cpp = cpp_path.read_text(encoding="utf-8")

    h, n_ns = re.subn(
        r"\n\s*namespace j2me \{\s*\n\s*class app_list;\s*\n\s*\}\s*\n",
        "\n",
        h,
        count=1,
    )
    h, n_get = re.subn(
        r"(?m)^\s*j2me::app_list \*get_j2me_applist\(\);\s*\n",
        "",
        h,
        count=1,
    )
    if n_ns != 1 or n_get != 1:
        fail(f"epoc.h J2ME anchors changed: namespace={n_ns} getter={n_get}")

    cpp, n_inc = re.subn(
        r"(?m)^\s*#include <j2me/applist\.h>\s*\n",
        "",
        cpp,
        count=1,
    )
    cpp, n_member = re.subn(
        r"(?m)^\s*std::unique_ptr<j2me::app_list> j2me_applist_;\s*\n",
        "",
        cpp,
        count=1,
    )
    cpp, n_init = re.subn(
        r"(?m)^\s*j2me_applist_ = std::make_unique<j2me::app_list>\(\*conf_\);\s*\n",
        "",
        cpp,
        count=1,
    )
    cpp = remove_braced(cpp, "j2me::app_list *get_j2me_applist", required=True)
    cpp = remove_braced(cpp, "j2me::app_list *system::get_j2me_applist", required=True)

    if (n_inc, n_member, n_init) != (1, 1, 1):
        fail(
            "epoc.cpp J2ME anchors changed: "
            f"include={n_inc} member={n_member} init={n_init}"
        )

    h_path.write_text(h, encoding="utf-8")
    cpp_path.write_text(cpp, encoding="utf-8")

    for p in (h_path, cpp_path):
        txt = p.read_text(encoding="utf-8")
        if re.search(r"j2me::|get_j2me|<j2me/|j2me_applist", txt, re.I):
            fail(f"host J2ME core reference survived in {p}")


def clean_cmake(up: Path) -> None:
    emu_cmake = up / "src/emu/CMakeLists.txt"
    ios_cmake = up / "src/emu/ios/CMakeLists.txt"
    for p in (emu_cmake, ios_cmake):
        if not p.is_file():
            fail(f"CMake file missing: {p}")

    emu = emu_cmake.read_text(encoding="utf-8")
    emu, n = re.subn(r"(?m)^\s*add_subdirectory\s*\(\s*j2me\s*\)\s*\n?", "", emu, count=1)
    if n != 1:
        fail("src/emu/CMakeLists.txt add_subdirectory(j2me) anchor missing")
    emu_cmake.write_text(emu, encoding="utf-8")

    ios = ios_cmake.read_text(encoding="utf-8")

    # The proven FAST1 build compiles the Xcode 26 Icon Composer package with
    # the simulator actool backend even though the binary itself is arm64/iPhoneOS.
    # On a fresh macos-15 runner, plain xcrun can resolve to Xcode 16.4, which
    # does not understand this .icon package and reports that "AppIcon" is
    # missing. Keep the proven actool platform, but pin actool itself to Xcode
    # 26.3 without changing the C/C++ SDK used by the cached build graph.
    if ios.count("--platform iphonesimulator") != 1:
        fail("AppIcon actool simulator-platform anchor changed")
    actool_cmd = "    COMMAND xcrun actool --compile"
    pinned_actool_cmd = (
        "    COMMAND ${CMAKE_COMMAND} -E env "
        "\"DEVELOPER_DIR=/Applications/Xcode_26.3.app/Contents/Developer\" "
        "xcrun actool --compile"
    )
    if ios.count(actool_cmd) != 1:
        fail("AppIcon actool command anchor changed")
    ios = ios.replace(actool_cmd, pinned_actool_cmd, 1)

    ios = ios.replace("app/j2me/EKAUnifiedLibraryViewController.h",
                      "app/library/EKAUnifiedLibraryViewController.h")
    ios = ios.replace("app/j2me/EKAUnifiedLibraryViewController.mm",
                      "app/library/EKAUnifiedLibraryViewController.mm")
    ios = re.sub(
        r"(?ms)^\s*# BUILDFIX13 MMAPIFIX1 GM-SYNTH1 resources\s*\n"
        r".*?(?=^\s*# NOJAVA_FAST1:|\Z)",
        "",
        ios,
        count=1,
    )
    ios = re.sub(r"(?ms)^\s*file\s*\(GLOB\s+PHONEME_J2MEMANIC3_SKIN.*?\)\s*\n", "", ios)
    ios = ios.replace("# NOJAVA_FAST1: phoneME/J2ME runtime excluded; shared native launcher retained.\n", "")

    native_block = '''
# NOJAVA_FULL1 + MANIC_NATIVE1: native-only Symbian/N-Gage controls.
target_sources(eka2l1 PRIVATE
    app/controls/manic/EKAManicControlsView.h
    app/controls/manic/EKAManicControlsView.m)

set(EKA_MANIC_NATIVE1_DIR
    "${CMAKE_CURRENT_SOURCE_DIR}/app/controls/manic/EKAManicControls")
add_custom_command(TARGET eka2l1 POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E make_directory "$<TARGET_BUNDLE_DIR:eka2l1>/EKAManicControls"
    COMMAND ${CMAKE_COMMAND} -E copy_directory
        "${EKA_MANIC_NATIVE1_DIR}"
        "$<TARGET_BUNDLE_DIR:eka2l1>/EKAManicControls"
    VERBATIM)
'''
    if "MANIC_NATIVE1: native-only" not in ios:
        ios = ios.rstrip() + "\n" + native_block
    ios_cmake.write_text(ios, encoding="utf-8")

    # The deleted core target may have been pulled transitively by another CMake
    # list. Remove every remaining source-path or standalone target reference.
    for p in sorted((up / "src/emu").rglob("CMakeLists.txt")):
        if "build-ios-device" in p.parts:
            continue
        txt = p.read_text(encoding="utf-8")
        lines = []
        for line in txt.splitlines(True):
            low = line.lower()
            if "/j2me/" in low or "phoneme" in low:
                continue
            if re.match(r"^\s*j2me\s*(?:#.*)?$", line.strip(), re.I):
                continue
            lines.append(line)
        txt = "".join(lines)
        # One-line link/dependency commands can carry the target inline.
        txt = re.sub(r"(?<![A-Za-z0-9_])j2me(?![A-Za-z0-9_])", "", txt, flags=re.I)
        p.write_text(txt, encoding="utf-8")

    for p in sorted((up / "src/emu").rglob("CMakeLists.txt")):
        if "build-ios-device" in p.parts:
            continue
        txt = p.read_text(encoding="utf-8")
        if re.search(r"j2me|phoneme", txt, re.I):
            fail(f"Java target reference survived in CMake: {p}")


def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: apply_nojava_full1_manic1.py <upstream-root>")
    up = Path(sys.argv[1]).resolve()
    app = up / "src/emu/ios/app"
    root = app / "RootViewController.mm"
    if not root.is_file():
        fail(f"invalid upstream tree: {root}")

    move_manic(app)
    clean_unified(app)
    clean_root(root)
    clean_controls(app)
    wire_manic_into_root(root)
    clean_core_j2me(up)

    # Remove the actual Java source trees after extracting the two native pieces.
    shutil.rmtree(up / "src/emu/j2me", ignore_errors=True)
    shutil.rmtree(app / "j2me", ignore_errors=True)
    shutil.rmtree(up / "third_party/phoneme-r1", ignore_errors=True)

    clean_cmake(up)

    required = [
        app / "library/EKAUnifiedLibraryViewController.h",
        app / "library/EKAUnifiedLibraryViewController.mm",
        app / "controls/manic/EKAManicControlsView.h",
        app / "controls/manic/EKAManicControlsView.m",
        app / "controls/manic/EKAManicControls/info.json",
        app / "controls/manic/EKAManicControls/dpad.png",
        app / "controls/manic/EKAManicControls/thumbstick.png",
    ]
    for p in required:
        if not p.exists():
            fail(f"native migration output missing: {p}")

    if (up / "src/emu/j2me").exists() or (app / "j2me").exists():
        fail("legacy j2me source directory survived")

    root_text = root.read_text(encoding="utf-8")
    cmake_text = (up / "src/emu/ios/CMakeLists.txt").read_text(encoding="utf-8")
    settings_text = (app / "GameSettingsViewController.mm").read_text(encoding="utf-8")
    assert "EKAManicControlsArtworkView" in root_text
    assert "EKAManicDefaultControlLayout" in root_text
    assert 'if (layout == 7) return @"Manic";' in settings_text
    assert "app/controls/manic/EKAManicControlsView.m" in cmake_text
    assert "app/library/EKAUnifiedLibraryViewController.mm" in cmake_text
    assert "app/j2me/" not in cmake_text
    assert "--platform iphonesimulator" in cmake_text
    assert "DEVELOPER_DIR=/Applications/Xcode_26.3.app/Contents/Developer" in cmake_text
    epoc_h = (up / "src/emu/system/include/system/epoc.h").read_text(encoding="utf-8")
    epoc_cpp = (up / "src/emu/system/src/epoc.cpp").read_text(encoding="utf-8")
    assert not re.search(r"j2me::|get_j2me|<j2me/|j2me_applist", epoc_h, re.I)
    assert not re.search(r"j2me::|get_j2me|<j2me/|j2me_applist", epoc_cpp, re.I)
    print("NOJAVA_FULL1 + MANIC_NATIVE1 source migration gates: PASS")


if __name__ == "__main__":
    main()
