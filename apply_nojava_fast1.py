#!/usr/bin/env python3
"""Remove the phoneME/J2ME runtime from a reconstructed MENUUI22 iOS tree.

The SystemApps/N-Gage launcher introduced by BUILDFIX7 lives in the historical
`app/j2me` directory. This patch deliberately keeps only that shared launcher
controller active while removing the Java runtime, JAR import route, phoneME
linkage, media bridge and Java resources from the CMake target.
"""
from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

MARK = "NOJAVA_FAST1"


def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: {msg}")


def find_braced_method(text: str, signature: str) -> tuple[int, int, int]:
    start = text.find(signature)
    if start < 0:
        fail(f"method not found: {signature}")
    if text.find(signature, start + len(signature)) >= 0:
        fail(f"method signature not unique: {signature}")
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
    fail(f"unterminated method: {signature}")


def replace_method(text: str, signature: str, body: str, *, required: bool = True) -> str:
    if signature not in text:
        if required:
            fail(f"method not found: {signature}")
        return text
    start, brace, end = find_braced_method(text, signature)
    prefix = text[start:brace].rstrip()
    replacement = prefix + " {\n" + body.rstrip() + "\n}"
    return text[:start] + replacement + text[end:]


def strip_root(root: Path) -> None:
    text = root.read_text(encoding="utf-8")

    lines = []
    for line in text.splitlines(True):
        if line.lstrip().startswith("#import") and "J2ME" in line and "EKAUnified" not in line:
            continue
        lines.append(line)
    text = "".join(lines)

    if "- (void)onJavaJ2ME" in text:
        text = replace_method(
            text,
            "- (void)onJavaJ2ME",
            "    // NOJAVA_FAST1: Java/J2ME runtime intentionally removed.",
            required=False,
        )

    if "static BOOL EKAIsJARPackagePath" in text:
        text = replace_method(
            text,
            "static BOOL EKAIsJARPackagePath",
            "    (void)path;\n    return NO;",
            required=False,
        )

    jar_start = text.find("    // AUTOIMPORT1: JAR is independent from the Symbian firmware/device lifecycle.")
    route = text.find("    // ROUTEFIX1:", jar_start + 1) if jar_start >= 0 else -1
    if jar_start >= 0 and route >= 0:
        text = text[:jar_start] + "    // NOJAVA_FAST1: JAR route removed; SIS/SISX/N-Gage routing preserved.\n" + text[route:]

    text = text.replace(
        "[self showAppsScreen];  // UNIFIEDLIBRARY1: J2ME does not require Symbian firmware.",
        "[self showAppsScreen];  // NOJAVA_FAST1: show native library before firmware selection.",
    )

    if "EKAUnifiedLibraryViewController importJARAtPath" in text:
        fail("RootViewController still calls JAR importer")
    for token in ("J2MELibraryViewController", "J2MEPlayerViewController", "J2MEProfileViewController"):
        if token in text:
            fail(f"RootViewController still references {token}")

    if MARK not in text:
        text = "// NOJAVA_FAST1: phoneME/J2ME removed from active iOS build.\n" + text
    root.write_text(text, encoding="utf-8")


def strip_unified(unified: Path) -> None:
    text = unified.read_text(encoding="utf-8")

    kept = []
    for line in text.splitlines(True):
        if line.lstrip().startswith("#import") and "J2ME" in line:
            continue
        kept.append(line)
    text = "".join(kept)

    text = replace_method(
        text,
        "+ (BOOL)importJARAtPath:",
        """    (void)path;
    if (importedName) *importedName = nil;
    if (error) {
        *error = [NSError errorWithDomain:@\"EKA2L1.NOJAVA\" code:-1001
            userInfo:@{NSLocalizedDescriptionKey:@\"Java/J2ME support is not included in this build.\"}];
    }
    return NO;""",
        required=False,
    )
    text = replace_method(
        text,
        "- (NSArray<NSDictionary *> *)loadJ2MEGames",
        "    return @[];",
        required=False,
    )

    text = replace_method(
        text,
        "- (void)reloadWithSymbianApps:",
        """    _deviceKey = [deviceKey copy] ?: @\"-1\";
    [_icons removeAllObjects];
    if (iconCache) [_icons addEntriesFromDictionary:iconCache];

    NSMutableSet<NSNumber *> *currentUIDs = [NSMutableSet set];
    for (NSDictionary *raw in apps ?: @[]) {
        NSNumber *uid = raw[@\"uid\"];
        if (uid) [currentUIDs addObject:uid];
    }
    [EKAUnifiedLibraryViewController reconcileNGageDetectionForDeviceKey:_deviceKey
                                                              currentUIDs:currentUIDs];
    NSSet<NSNumber *> *knownNGage =
        [EKAUnifiedLibraryViewController knownNGageUIDsForDeviceKey:_deviceKey];
    NSMutableArray *symbian = [NSMutableArray array];
    NSMutableArray *ngage = [NSMutableArray array];
    for (NSDictionary *raw in apps ?: @[]) {
        NSMutableDictionary *item = [raw mutableCopy];
        NSNumber *uid = item[@\"uid\"];
        BOOL isNGage = uid && [knownNGage containsObject:uid];
        item[@\"kind\"] = isNGage ? @\"ngage\" : @\"symbian\";
        if (isNGage) [ngage addObject:item]; else [symbian addObject:item];
    }
    _sections = [NSMutableArray arrayWithObjects:
        @{ @\"title\":@\"Symbian\", @\"kind\":@\"symbian\", @\"items\":symbian },
        @{ @\"title\":@\"N-Gage\", @\"kind\":@\"ngage\", @\"items\":ngage }, nil];
    _cursorFlatIndex = -1;
    [_collectionView reloadData];""",
        required=True,
    )

    text = replace_method(
        text,
        "- (void)activateItem:",
        """    NSString *kind = item[@\"kind\"];
    if ([kind isEqualToString:@\"j2me\"]) return;
    NSNumber *uid = item[@\"uid\"];
    if (self.onLaunchSymbian && uid) {
        self.onLaunchSymbian((uint32_t)uid.unsignedLongValue);
    }""",
        required=True,
    )

    text = replace_method(text, "- (void)openJ2MEProfile:", "    (void)item;", required=False)
    text = replace_method(text, "- (void)deleteJ2ME:", "    (void)item;", required=False)
    text = replace_method(text, "- (void)closeJ2MEPlayer:", "    (void)sender;", required=False)

    if "- (void)onLongPress:" in text:
        text = replace_method(
            text,
            "- (void)onLongPress:",
            """    if (gr.state != UIGestureRecognizerStateBegan) return;
    NSIndexPath *ip = [_collectionView indexPathForItemAtPoint:[gr locationInView:_collectionView]];
    if (!ip) return;
    NSDictionary *item = _sections[ip.section][@\"items\"][ip.item];
    NSString *name = item[@\"name\"] ?: @\"Ứng dụng\";
    NSNumber *uidNumber = item[@\"uid\"];
    if (!uidNumber) return;
    uint32_t uid = (uint32_t)uidNumber.unsignedLongValue;

    UIAlertController *sheet = [UIAlertController alertControllerWithTitle:name message:nil
        preferredStyle:UIAlertControllerStyleActionSheet];
    [sheet addAction:[UIAlertAction actionWithTitle:@\"Chạy\" style:UIAlertActionStyleDefault
        handler:^(__unused UIAlertAction *a){ [self activateItem:item]; }]];
    if (self.onOpenSymbianSettings) {
        [sheet addAction:[UIAlertAction actionWithTitle:@\"Cài đặt trò chơi\" style:UIAlertActionStyleDefault
            handler:^(__unused UIAlertAction *a){ self.onOpenSymbianSettings(uid, name); }]];
    }
    if (self.onHideSymbian) {
        [sheet addAction:[UIAlertAction actionWithTitle:@\"Ẩn ứng dụng\" style:UIAlertActionStyleDestructive
            handler:^(__unused UIAlertAction *a){ self.onHideSymbian(uid, name); }]];
    }
    [sheet addAction:[UIAlertAction actionWithTitle:@\"Hủy\" style:UIAlertActionStyleCancel handler:nil]];
    UICollectionViewCell *cell = [_collectionView cellForItemAtIndexPath:ip];
    sheet.popoverPresentationController.sourceView = cell ?: _collectionView;
    sheet.popoverPresentationController.sourceRect = cell ? cell.bounds : CGRectMake(0, 0, 1, 1);
    [self.parentViewController presentViewController:sheet animated:YES completion:nil];""",
            required=False,
        )

    for token in ("J2MEPlayerViewController", "J2MEProfileViewController"):
        if token in text:
            fail(f"unified controller still references {token}")
    if "J2MEInspectJarAtPath" in text or "J2MEExtractJarResourceAtPath" in text:
        fail("unified controller still calls J2ME JAR helpers")

    if MARK not in text:
        text = "// NOJAVA_FAST1: shared launcher retained; Java/J2ME section removed.\n" + text
    unified.write_text(text, encoding="utf-8")


def strip_cmake(cmake: Path) -> None:
    text = cmake.read_text(encoding="utf-8")

    # Parse complete CMake commands before filtering individual app/j2me source
    # lines. Some historical Java resource blocks close the set(...) command on
    # the same line as the final resource path, so deleting path lines first can
    # remove the closing ')' and make an otherwise valid command look unbalanced.
    lines = text.splitlines(True)
    stage2: list[str] = []
    i = 0
    command_start = re.compile(
        r"^\s*(set|set_source_files_properties|target_sources|target_link_libraries|"
        r"target_include_directories|target_compile_definitions)\s*\(", re.I
    )
    java_word = re.compile(r"PHONEME|phoneME|J2ME|GeneralUser GS SoftSynth", re.I)
    while i < len(lines):
        line = lines[i]
        m = command_start.match(line)
        if not m:
            stage2.append(line)
            i += 1
            continue
        depth = line.count("(") - line.count(")")
        block = [line]
        j = i + 1
        while depth > 0 and j < len(lines):
            block.append(lines[j])
            depth += lines[j].count("(") - lines[j].count(")")
            j += 1
        if depth != 0:
            fail(f"unbalanced CMake command near: {line.strip()}")
        command = "".join(block)
        mixed_ios_sources = re.match(r"^\s*set\s*\(\s*IOS_APP_SOURCES\b", command, re.I) is not None
        keep_unified = "EKAUnifiedLibraryViewController" in command
        if java_word.search(command) and not mixed_ios_sources and not keep_unified:
            i = j
            continue
        stage2.extend(block)
        i = j

    text = "".join(stage2)

    # Now remove residual Java/J2ME source entries from retained mixed source
    # lists (notably IOS_APP_SOURCES), while preserving EKAUnifiedLibraryViewController.
    # If a historical list puts its closing ')' on the same line as a removed
    # Java entry, keep that structural close so CMake remains balanced.
    stage1: list[str] = []
    for line in text.splitlines(True):
        low = line.lower()
        if "app/j2me/" in low and "ekaunifiedlibraryviewcontroller" not in low:
            opens = line.count("(")
            closes = line.count(")")
            if closes > opens:
                indent = re.match(r"^\\s*", line).group(0)
                stage1.append(indent + (")" * (closes - opens)) + "\n")
            continue
        stage1.append(line)
    text = "".join(stage1)

    src_lines = text.splitlines(True)
    cleaned: list[str] = []
    skip_depth = 0
    for line in src_lines:
        stripped = line.strip()
        if skip_depth:
            if re.match(r"(?i)^if\s*\(", stripped):
                skip_depth += 1
            elif re.match(r"(?i)^endif\s*\(", stripped) or stripped.lower() == "endif()":
                skip_depth -= 1
            continue
        if re.match(r"(?i)^if\s*\(.*(?:PHONEME|phoneME|J2ME)", stripped):
            skip_depth = 1
            continue
        cleaned.append(line)
    if skip_depth:
        fail("unterminated Java/phoneME CMake if block")
    text = "".join(cleaned)

    text = re.sub(r"(?m)^\s*#.*(?:J2ME|phoneME|PHONEME).*$\n?", "", text)

    forbidden = [
        "PHONEME_R1_LIB",
        "libphoneMECore",
        "PhoneMEMediaBridge",
        "J2MEBridge.mm",
        "J2MEPlayerViewController",
        "J2MEProfileViewController",
        "GeneralUser GS SoftSynth",
    ]
    for token in forbidden:
        if token in text:
            fail(f"CMake still references {token}")

    if "EKAUnifiedLibraryViewController.mm" not in text:
        fail("shared SystemApps/N-Gage unified controller was accidentally removed from CMake")
    text += "\n# NOJAVA_FAST1: phoneME/J2ME runtime excluded; shared native launcher retained.\n"
    cmake.write_text(text, encoding="utf-8")


def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: apply_nojava_fast1.py <upstream-root>")
    up = Path(sys.argv[1]).resolve()
    cmake = up / "src/emu/ios/CMakeLists.txt"
    root = up / "src/emu/ios/app/RootViewController.mm"
    unified = up / "src/emu/ios/app/j2me/EKAUnifiedLibraryViewController.mm"
    for p in (cmake, root, unified):
        if not p.is_file():
            fail(f"required file missing: {p}")

    strip_root(root)
    strip_unified(unified)
    strip_cmake(cmake)

    shutil.rmtree(up / "third_party/phoneme-r1", ignore_errors=True)
    for name in (
        "GeneralUser GS SoftSynth v1.44.sf2",
        "GeneralUser-GS-SoftSynth-1.44-PROVENANCE.txt",
        "GeneralUser-GS-LICENSE.txt",
        "TinySoundFont-LICENSE.txt",
    ):
        try:
            (up / "src/emu/ios/app/j2me" / name).unlink()
        except FileNotFoundError:
            pass

    cm = cmake.read_text(encoding="utf-8")
    rt = root.read_text(encoding="utf-8")
    un = unified.read_text(encoding="utf-8")
    assert "EKAUnifiedLibraryViewController.mm" in cm
    assert "J2MEBridge.mm" not in cm
    assert "PhoneMEMediaBridge" not in cm
    assert "PHONEME_R1_LIB" not in cm
    assert "importJARAtPath:path" not in rt
    assert "@\"J2ME\", @\"kind\":@\"j2me\"" not in un
    print("NOJAVA_FAST1 source purge gates: PASS")


if __name__ == "__main__":
    main()
