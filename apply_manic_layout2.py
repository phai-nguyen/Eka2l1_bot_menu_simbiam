#!/usr/bin/env python3
"""Expose the native Manic skin in Symbian/N-Gage layout pickers and editor.

Input is the proven MENUUI22 NOJAVA FULL1 MANIC1 cached tree.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

MARK = "MANIC_LAYOUT2"


def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: {msg}")


def replace_once(text: str, old: str, new: str, name: str) -> str:
    count = text.count(old)
    if count != 1:
        fail(f"{name}: expected one anchor, found {count}")
    return text.replace(old, new, 1)


def ensure_layout7_order(text: str, name: str) -> str:
    """Expose layout 7 in the one layoutOrder method without assuming old formatting."""
    pat = re.compile(
        r'(\+\s*\(NSArray<NSNumber \*> \*\)layoutOrder\s*\{\s*return\s*@\[)'
        r'([^\]]*)'
        r'(\];\s*\})',
        re.S,
    )
    matches = list(pat.finditer(text))
    if len(matches) != 1:
        fail(f"{name}: expected one layoutOrder method, found {len(matches)}")
    m = matches[0]
    body = m.group(2)
    if re.search(r'(?<!\d)@7(?!\d)', body):
        return text
    if "@6" in body:
        body = body.replace("@6", "@6, @7", 1)
    elif "@2" in body:
        body = body.replace("@2", "@7, @2", 1)
    else:
        body = body.rstrip() + ", @7"
    return text[:m.start()] + m.group(1) + body + m.group(3) + text[m.end():]


def patch_settings(app: Path) -> None:
    p = app / "GameSettingsViewController.mm"
    text = p.read_text(encoding="utf-8")

    if 'if (layout == 7) return @"Manic Skin";' not in text:
        text = replace_once(
            text,
            '    if (layout == 7) return @"Manic";\n',
            '    if (layout == 7) return @"Manic Skin";\n',
            "settings Manic label",
        )
    text = ensure_layout7_order(text, "settings layoutOrder")
    p.write_text(text, encoding="utf-8")


def patch_root(root: Path) -> None:
    text = root.read_text(encoding="utf-8")
    text = ensure_layout7_order(text, "runtime layoutOrder")

    if 'if (i == 7) return @"Manic Skin";' not in text:
        anchor = '    if (i == 6) return @"Joystick";\n'
        insert = '    if (i == 6) return @"Joystick";\n    if (i == 7) return @"Manic Skin";\n'
        text = replace_once(text, anchor, insert, "runtime Manic label")
    root.write_text(text, encoding="utf-8")


def patch_editor(app: Path) -> None:
    p = app / "LayoutEditorViewController.mm"
    text = p.read_text(encoding="utf-8")

    import_anchor = '#import "GameSettingsStore.h"\n'
    import_line = '#import "controls/manic/EKAManicControlsView.h"\n'
    if import_line not in text:
        text = replace_once(
            text, import_anchor, import_anchor + import_line, "editor Manic import"
        )

    ivar_anchor = '    NSArray<NSDictionary *> *_defaultSeed;   // built-in layout the editor seeds/resets to\n'
    ivar_insert = (
        ivar_anchor
        + '    EKAManicControlsArtworkView *_manicArtwork;\n'
        + '    BOOL _manicMode;\n'
    )
    if "_manicArtwork;" not in text:
        text = replace_once(text, ivar_anchor, ivar_insert, "editor Manic ivars")

    old_block = '''    _controls = [[GameControlsView alloc] initWithFrame:CGRectZero];
    _controls.editDelegate = self;
    EKAGameSettings *s = [GameSettingsStore settingsForUid:_uid];
    // The "default" for this layout is the selected on-screen layout (e.g. Joystick) rendered as
    // editable elements, so the editor — and the Reset button — reflect the user's choice. None
    // (layout 0) falls back to a sensible D-pad default.
    NSArray *seed = [GameControlsView customLayoutForBuiltinLayout:s.keyLayout];
    _defaultSeed = seed.count ? seed : [GameControlsView defaultCustomLayout];
    NSArray *existing = _portrait ? s.customLayoutPortrait : s.customLayoutLandscape;
    _controls.customLayout = existing.count ? existing : _defaultSeed;
    _controls.editing = YES;
    [_preview addSubview:_controls];
'''
    new_block = '''    EKAGameSettings *s = [GameSettingsStore settingsForUid:_uid];
    _manicMode = (s.keyLayout == 7);

    _controls = [[GameControlsView alloc] initWithFrame:CGRectZero];
    _controls.editDelegate = self;

    // MANIC_LAYOUT2: Manic is a first-class native layout for both Symbian and
    // N-Gage. Seed the editor from the same representation JSON used at runtime,
    // so portrait/landscape edits match the actual skin geometry.
    CGSize screen = UIScreen.mainScreen.bounds.size;
    CGFloat mn = MIN(screen.width, screen.height);
    CGFloat mx = MAX(screen.width, screen.height);
    CGSize targetSize = _portrait ? CGSizeMake(mn, mx) : CGSizeMake(mx, mn);
    NSArray *seed = _manicMode
        ? EKAManicDefaultControlLayout(targetSize, self.traitCollection)
        : [GameControlsView customLayoutForBuiltinLayout:s.keyLayout];
    _defaultSeed = seed.count ? seed : [GameControlsView defaultCustomLayout];

    NSArray *existing = _portrait ? s.customLayoutPortrait : s.customLayoutLandscape;
    NSArray *active = existing.count ? existing : _defaultSeed;
    _controls.customLayout = active;
    _controls.editing = YES;

    if (_manicMode) {
        _manicArtwork = [[EKAManicControlsArtworkView alloc] initWithFrame:CGRectZero];
        _manicArtwork.layout = active;
        _manicArtwork.controlsOpacity = 1.0;
        [_preview addSubview:_manicArtwork];

        // Hide generic button artwork but keep GameControlsView's editor boxes,
        // drag/pinch gestures and native Symbian scancode model.
        _controls.overlayOpacity = 0.0;
    }
    [_preview addSubview:_controls];
'''
    text = replace_once(text, old_block, new_block, "editor setup")

    layout_anchor = '    _controls.frame = _preview.bounds;\n'
    layout_insert = (
        '    _controls.frame = _preview.bounds;\n'
        '    if (_manicArtwork) _manicArtwork.frame = _preview.bounds;\n'
    )
    if "_manicArtwork.frame = _preview.bounds" not in text:
        text = replace_once(text, layout_anchor, layout_insert, "editor artwork frame")

    reset_old = '        handler:^(UIAlertAction *a) { self->_controls.customLayout = self->_defaultSeed; }]];\n'
    reset_new = '''        handler:^(UIAlertAction *a) {
            self->_controls.customLayout = self->_defaultSeed;
            if (self->_manicMode) self->_manicArtwork.layout = self->_defaultSeed;
        }]];
'''
    text = replace_once(text, reset_old, reset_new, "editor reset sync")

    delegate_old = '''- (void)gameControlsDidChange:(GameControlsView *)view {
    // Selection/geometry changed — nothing else needed; the view redraws itself.
}
'''
    delegate_new = '''- (void)gameControlsDidChange:(GameControlsView *)view {
    // MANIC_LAYOUT2: keep skin artwork locked to the same editable normalized
    // frames. GameControlsView remains authoritative for hitboxes/scancodes.
    if (_manicMode) {
        _manicArtwork.layout = [view currentLayout];
    }
}
'''
    text = replace_once(text, delegate_old, delegate_new, "editor live artwork sync")

    p.write_text(text, encoding="utf-8")


def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: apply_manic_layout2.py <upstream-root>")

    up = Path(sys.argv[1]).resolve()
    app = up / "src/emu/ios/app"
    root = app / "RootViewController.mm"

    required = [
        app / "GameSettingsViewController.mm",
        app / "LayoutEditorViewController.mm",
        app / "controls/manic/EKAManicControlsView.h",
        app / "controls/manic/EKAManicControlsView.m",
        root,
    ]
    for p in required:
        if not p.is_file():
            fail(f"FULL1 native baseline missing: {p}")

    if (up / "src/emu/j2me").exists() or (app / "j2me").exists():
        fail("legacy J2ME tree unexpectedly present; expected FULL1 baseline")

    patch_settings(app)
    patch_root(root)
    patch_editor(app)

    settings = (app / "GameSettingsViewController.mm").read_text(encoding="utf-8")
    root_text = root.read_text(encoding="utf-8")
    editor = (app / "LayoutEditorViewController.mm").read_text(encoding="utf-8")

    assert 'if (layout == 7) return @"Manic Skin";' in settings
    assert "@7" in re.search(r'\+\s*\(NSArray<NSNumber \*> \*\)layoutOrder.*?\}', settings, re.S).group(0)
    assert 'if (i == 7) return @"Manic Skin";' in root_text
    assert "@7" in re.search(r'\+\s*\(NSArray<NSNumber \*> \*\)layoutOrder.*?\}', root_text, re.S).group(0)
    assert "EKAManicDefaultControlLayout(targetSize" in editor
    assert "_manicArtwork.layout = [view currentLayout]" in editor
    assert "_controls.overlayOpacity = 0.0" in editor
    assert not re.search(r"J2ME|phoneME|PHONEME", editor, re.I)

    print("MANIC_LAYOUT2 Symbian/N-Gage picker + editor integration: PASS")


if __name__ == "__main__":
    main()
