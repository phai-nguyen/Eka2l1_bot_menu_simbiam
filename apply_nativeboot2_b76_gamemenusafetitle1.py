#!/usr/bin/env python3
"""NATIVEBOOT2 B76 GAMEMENUSAFETITLE1.

B75 DEVICE1 reproduces a host crash by pressing the three-dot menu button.
The .ips proves the crash happens on the iOS main thread before Exit Emulator:
RootViewController::onMenuController -> presentGameMenu ->
GameMenuView::showInView -> UIButton::titleLabel -> UILabel/UIKit text attrs.

The exact reconstructed GameMenuView.mm contains:
    [b setTitle:...]
    [b setTitleColor:...]
    b.titleLabel.font = ...

B76 keeps UIButton only as the touch target and renders each row title using an
ordinary UILabel child. This avoids the UIButtonLegacyVisualProvider/titleLabel
path implicated by the crash while preserving menu layout, handlers, z-order,
keyboard navigation and dismissal semantics.

Host UI only. No guest, PhoneUI, FileServer, SIM/state, CONE14 or teardown
behavior changes.
"""
from pathlib import Path
import sys

MARK="NATIVEBOOT2-B76-GAMEMENUSAFETITLE1"

def fail(msg):
    raise SystemExit(f"{MARK}: {msg}")

def rep1(text,old,new,label):
    n=text.count(old)
    if n != 1:
        fail(f"{label}: expected one anchor, found {n}")
    return text.replace(old,new,1)

def main():
    if len(sys.argv) != 2:
        fail("usage: apply_nativeboot2_b76_gamemenusafetitle1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    menu=up/"src/emu/ios/app/GameMenuView.mm"
    fs=up/"src/emu/services/src/fs/fs.cpp"
    svc=up/"src/emu/kernel/src/svc.cpp"
    for p in (menu,fs,svc):
        if not p.is_file():
            fail(f"missing source: {p}")

    text=menu.read_text(encoding="utf-8")
    fs_text=fs.read_text(encoding="utf-8")
    svc_text=svc.read_text(encoding="utf-8")

    if "[NBOOT2][GAMEMENU_SAFE_TITLE]" in text:
        print(MARK+": already applied")
        return

    # B75 evidence chain must still be present.
    for gate,body in (
        ("[NBOOT2][PHONEUI_RES_MATCH2]",fs_text),
        ("[NBOOT2][PHONEUI_RES_CALLER]",fs_text),
        ("[NBOOT2][CONE14_PHONEUI]",svc_text),
    ):
        if gate not in body:
            fail("B75/B71 gate missing: "+gate)

    old=r'''        UIButton *b = [UIButton buttonWithType:UIButtonTypeCustom];
        b.frame = CGRectMake(pad, titleH + i * rowH, W - 2 * pad, rowH - 6);
        b.layer.cornerRadius = 10;
        [b setTitle:_titles[i] forState:UIControlStateNormal];
        UIColor *fg = [_destructive[i] boolValue] ? [UIColor systemRedColor] : [UIColor whiteColor];
        [b setTitleColor:fg forState:UIControlStateNormal];
        b.titleLabel.font = [UIFont systemFontOfSize:18 weight:UIFontWeightMedium];
        b.tag = i;
        [b addTarget:self action:@selector(onTap:) forControlEvents:UIControlEventTouchUpInside];
        [_panel addSubview:b];
        [_buttons addObject:b];
'''

    new=r'''        UIButton *b = [UIButton buttonWithType:UIButtonTypeCustom];
        b.frame = CGRectMake(pad, titleH + i * rowH, W - 2 * pad, rowH - 6);
        b.layer.cornerRadius = 10;

        // NATIVEBOOT2 B76: keep UIButton as a hit target only. B75 DEVICE1
        // crashes inside UIButtonLegacyVisualProvider while titleLabel is
        // created. Render the visible title with a plain UILabel child so this
        // path never asks UIButton for its legacy titleLabel.
        UIColor *fg = [_destructive[i] boolValue] ? [UIColor systemRedColor] : [UIColor whiteColor];
        UILabel *label = [[UILabel alloc] initWithFrame:b.bounds];
        label.autoresizingMask = UIViewAutoresizingFlexibleWidth | UIViewAutoresizingFlexibleHeight;
        label.text = _titles[i];
        label.textColor = fg;
        label.font = [UIFont systemFontOfSize:18 weight:UIFontWeightMedium];
        label.textAlignment = NSTextAlignmentCenter;
        label.userInteractionEnabled = NO;
        [b addSubview:label];

        b.tag = i;
        [b addTarget:self action:@selector(onTap:) forControlEvents:UIControlEventTouchUpInside];
        [_panel addSubview:b];
        [_buttons addObject:b];
'''

    text=rep1(text,old,new,"safe menu row")

    loop_anchor='''    for (NSInteger i = 0; i < (NSInteger)_titles.count; i++) {
'''
    loop_new='''    NSLog(@"[NBOOT2][GAMEMENU_SAFE_TITLE] title=%@ options=%ld legacy_title_label=0",
          _title, (long)_titles.count);
    for (NSInteger i = 0; i < (NSInteger)_titles.count; i++) {
'''
    text=rep1(text,loop_anchor,loop_new,"runtime proof marker")

    for required in (
        "[NBOOT2][GAMEMENU_SAFE_TITLE]",
        "UILabel *label = [[UILabel alloc] initWithFrame:b.bounds];",
        "label.text = _titles[i];",
        "label.userInteractionEnabled = NO;",
        "[b addSubview:label];",
    ):
        if required not in text:
            fail("post-apply gate missing: "+required)

    # Crash path must be absent from GameMenuView implementation after B76.
    for forbidden in (
        "b.titleLabel",
        "[b setTitle:_titles[i]",
        "[b setTitleColor:fg",
    ):
        if forbidden in text:
            fail("legacy UIButton title path remains: "+forbidden)

    # Preserve menu behavior.
    for required in (
        "[b addTarget:self action:@selector(onTap:) forControlEvents:UIControlEventTouchUpInside];",
        "[self refreshHighlight];",
        "[self dismiss];",
        "((void (^)(void))handler)();",
    ):
        if required not in text:
            fail("menu behavior gate missing: "+required)

    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    menu.write_text(text,encoding="utf-8")

    print(MARK+": applied")
    print("scope=IOS_GAMEMENU_TITLE_RENDER_ONLY")
    print("button=HIT_TARGET_ONLY")
    print("visible_title=PLAIN_UILABEL")
    print("uibutton_titlelabel=NOT_ACCESSED")
    print("guest_behavior=UNCHANGED")
    print("phoneui_b75=PRESERVED")
    print("teardown_fix=UNCHANGED")
    print("NOJAVA=MANIC3=PRESERVED")

if __name__=="__main__":
    main()
