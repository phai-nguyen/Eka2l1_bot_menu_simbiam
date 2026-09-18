#!/usr/bin/env python3
"""Fix in-game GameMenuView z-order over all on-screen control layouts.

Input is the proven MENUUI22 NOJAVA FULL1 MANIC2 cached tree.
The bug is not Manic-specific: updateChrome() raises GameControlsView (and the
Manic artwork layer) after GameMenuView has been added, so any layout can draw
over the in-game menu/layout chooser during a layout pass.
"""
from __future__ import annotations

import sys
from pathlib import Path

MARK = "MANIC_MODALFIX1"


def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: {msg}")


def replace_once(text: str, old: str, new: str, name: str) -> str:
    count = text.count(old)
    if count != 1:
        fail(f"{name}: expected one anchor, found {count}")
    return text.replace(old, new, 1)


def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: apply_manic_modalfix1.py <upstream-root>")

    up = Path(sys.argv[1]).resolve()
    root = up / "src/emu/ios/app/RootViewController.mm"
    menu_h = up / "src/emu/ios/app/GameMenuView.h"
    menu_mm = up / "src/emu/ios/app/GameMenuView.mm"

    for p in (root, menu_h, menu_mm):
        if not p.is_file():
            fail(f"MANIC2 baseline file missing: {p}")

    text = root.read_text(encoding="utf-8")

    present_old = '''- (void)presentGameMenu:(GameMenuView *)menu {
    [self.activeMenu dismiss];
    self.activeMenu = menu;
    self.inputManager.menuShown = YES;
    __weak RootViewController *weakSelf = self;
    [menu showInView:self.view onDismiss:^{
        RootViewController *s = weakSelf;
        if (s.activeMenu == menu) {
            s.activeMenu = nil;
            s.inputManager.menuShown = NO;
        }
    }];
}
'''
    present_new = '''- (void)presentGameMenu:(GameMenuView *)menu {
    [self.activeMenu dismiss];
    self.activeMenu = menu;
    self.inputManager.menuShown = YES;
    __weak RootViewController *weakSelf = self;
    [menu showInView:self.view onDismiss:^{
        RootViewController *s = weakSelf;
        if (s.activeMenu == menu) {
            s.activeMenu = nil;
            s.inputManager.menuShown = NO;
        }
    }];

    // MANIC_MODALFIX1: GameMenuView is a full-screen UIView sibling of the
    // emulator controls. Keep it above every control skin immediately.
    [self.view bringSubviewToFront:menu];
}
'''
    text = replace_once(text, present_old, present_new, "presentGameMenu")

    chrome_anchor = '''    }
    // Forward hardware key/controller input to the guest only while a game runs; while the
    // homescreen apps list is up, the same keys drive its selection cursor instead.
    self.inputManager.enabled = self.gameRunning;
'''
    chrome_new = '''    }

    // MANIC_MODALFIX1: updateChrome() is called from layout/orientation changes
    // while GameMenuView may already be visible. controlsView/manicArtworkView,
    // menuButton and statusOverlay are raised above the GL view above, so the
    // active menu must be raised last. This fixes every built-in layout as well
    // as Manic Skin, without hiding or changing the native scancode engine.
    if (self.activeMenu && self.activeMenu.superview == self.view) {
        [self.view bringSubviewToFront:self.activeMenu];
    }

    // Forward hardware key/controller input to the guest only while a game runs; while the
    // homescreen apps list is up, the same keys drive its selection cursor instead.
    self.inputManager.enabled = self.gameRunning;
'''
    text = replace_once(text, chrome_anchor, chrome_new, "updateChrome topmost menu")

    # Defensive source invariants: keep the proven GameMenuView dismissal order.
    menu_impl = menu_mm.read_text(encoding="utf-8")
    if "[self dismiss];" not in menu_impl or "((void (^)(void))handler)();" not in menu_impl:
        fail("GameMenuView choose/dismiss semantics changed")
    if menu_impl.index("[self dismiss];") > menu_impl.index("((void (^)(void))handler)();"):
        fail("GameMenuView must dismiss before running option handler")

    if text.count("MANIC_MODALFIX1") < 2:
        fail("modal fix markers did not land")
    if "[self.view bringSubviewToFront:self.activeMenu];" not in text:
        fail("active menu final z-order gate missing")
    if "[self.view bringSubviewToFront:menu];" not in text:
        fail("menu immediate z-order gate missing")

    root.write_text(text, encoding="utf-8")
    print("MANIC_MODALFIX1 GameMenuView z-order gates: PASS")


if __name__ == "__main__":
    main()
