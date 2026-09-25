# NATIVEBOOT2 B76 GAMEMENUSAFETITLE1

Date: 2026-09-25
Status: BUILD-VALIDATED; DEVICE TEST REQUIRED
Selected route: NORMAL BOOT + SIM PRESENT

## Purpose

B75 DEVICE1 crashes to iOS Home merely by pressing the three-dot menu button.
The .ips proves the main-thread crash enters UIButtonLegacyVisualProvider
through UIButton::titleLabel while GameMenuView is being constructed.

B76 is a host-UI-only fix.

## Change

GameMenuView keeps UIButton as the hit target but no longer uses UIButton's
legacy title machinery.

Removed from each menu row:
- setTitle:
- setTitleColor:
- b.titleLabel.font

Added a plain UILabel child:
- label.text = menu option title
- same destructive/normal color
- same 18pt medium font
- centered
- autoresizes with the button
- userInteractionEnabled = NO

Button tag/target, navigation, highlighting, dismiss-before-handler semantics,
menu z-order and option handlers remain unchanged.

Runtime proof marker:
[NBOOT2][GAMEMENU_SAFE_TITLE] ... legacy_title_label=0

## Scope

No changes to:
- PhoneUI resource registration
- FileServer guest behavior
- CONE14
- SIM/state/Starter/SAServer/P&S
- B75 PHONEUI_RES_* diagnostics
- ipc_msg teardown
- graphics/scheduler guest behavior

NOJAVA / MANIC3 preserved.

## Canonical GREEN

- workflow run: 36139803235 / #244
- job: 108086557161
- functional HEAD: 2bb392ac7cf4b18384d15344f149543036ba6c41
- B76 apply PASS
- B76 contract PASS
- full manifest/regression PASS
- iOS compile/link PASS
- binary invariants PASS including GAMEMENU_SAFE_TITLE
- package/upload PASS
- compile requests/hits/misses: 152/151/1
- cache hit rate: 99.34%
- compilation failures: 0
- bootstrap: B28_CACHE
- bootstrap restore: 22 s
- patch/regression: 3 s
- CMake build: 76 s
- package: 2 s
- total audit: 126 s

Unsigned IPA SHA-256:
eb68fd326ac856331611c5162575f797110ab0683f843b5659b0523d7e38aa99

IPA artifact:
- ID 10866436282
- ZIP digest sha256:21f748a0ce1db72b3e2eb259569be88a41ad24d0817babf9f555015a869cc1eb
- expires 2026-10-09

Audit artifact:
- ID 10866436293
- ZIP digest sha256:9c4db82cbf2c0bfe2ec0d8c6e4e07cea3f6d973182f34e45ef9d879084defb7e
- expires 2026-10-09

Packaged Mach-O UUID:
B52D1C26-0C93-3833-8E88-E4B40E66AEA5

## DEVICE1

1. Install B76 over B75.
2. Boot normal Emulator path until the same Phone start-up failed screen.
3. Press the three-dot button first.
   Acceptance: Emulator menu renders and app does not crash to Home.
4. Press Cancel once.
5. Open three-dot again.
6. Choose Exit Emulator.
7. Send standard logs.
8. If Home crash occurs, send the new .ips.

If three-dot now works but Exit Emulator produces the old
ipc_msg::~ipc_msg() -> kernel_system::wipeout() signature, promote the
separate teardown fix next.

Guest-side next step remains separate: use the B75 +0x5094 bridge to map the
exact PhoneUI resource-init routine before restoring callhandlingui
registration.
