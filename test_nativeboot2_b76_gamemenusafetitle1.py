#!/usr/bin/env python3
"""Contract for NATIVEBOOT2 B76 GAMEMENUSAFETITLE1."""
from pathlib import Path
import sys

MARK="NATIVEBOOT2-B76-GAMEMENUSAFETITLE1-TEST"

def fail(msg):
    raise SystemExit(f"{MARK}: FAIL: {msg}")

def need(text,needle,where):
    if needle not in text:
        fail(f"missing in {where}: {needle}")

def main():
    if len(sys.argv)!=2:
        fail("usage: test_nativeboot2_b76_gamemenusafetitle1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    menu=(up/"src/emu/ios/app/GameMenuView.mm").read_text(encoding="utf-8")
    fs=(up/"src/emu/services/src/fs/fs.cpp").read_text(encoding="utf-8")
    svc=(up/"src/emu/kernel/src/svc.cpp").read_text(encoding="utf-8")

    for x in (
        "[NBOOT2][GAMEMENU_SAFE_TITLE]",
        "UILabel *label = [[UILabel alloc] initWithFrame:b.bounds];",
        "label.text = _titles[i];",
        "label.textColor = fg;",
        "label.font = [UIFont systemFontOfSize:18 weight:UIFontWeightMedium];",
        "label.textAlignment = NSTextAlignmentCenter;",
        "label.userInteractionEnabled = NO;",
        "[b addSubview:label];",
    ):
        need(menu,x,"GameMenuView.mm")

    for x in ("b.titleLabel","[b setTitle:_titles[i]","[b setTitleColor:fg"):
        if x in menu:
            fail("legacy UIButton title path remains: "+x)

    for x in (
        "[b addTarget:self action:@selector(onTap:) forControlEvents:UIControlEventTouchUpInside];",
        "[self dismiss];",
        "((void (^)(void))handler)();",
    ):
        need(menu,x,"menu behavior")

    need(fs,"[NBOOT2][PHONEUI_RES_MATCH2]","B75")
    need(fs,"[NBOOT2][PHONEUI_RES_CALLER]","B75")
    need(svc,"[NBOOT2][CONE14_PHONEUI]","B71")

    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    print(MARK+": PASS")
    print("scope=IOS_GAMEMENU_TITLE_RENDER_ONLY")
    print("uibutton_titlelabel=ABSENT")
    print("plain_uilabel_title=PRESENT")
    print("phoneui_b75=PRESERVED")
    print("guest_behavior=UNCHANGED")

if __name__=="__main__":
    main()
