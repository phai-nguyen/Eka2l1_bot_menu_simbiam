# NATIVEBOOT2 B75 PHONEUIRESCALLER2 — DEVICE1

Date: 2026-09-25
Status: DEVICE-OBSERVED; PHONEUI CALLER PROBE PASS; RESOURCE-INIT CALL CHAIN NARROWED; NEW HOST GAMEMENU CRASH PROVEN

## Inputs
- EKA2L1(20260925-130800).log
- EKA2L1_Persistent(20260925-130849).log
- EKA2L1_TakeThis(20260925-130751).log
- eka2l1-2026-09-25-195134.ips

Selected route remains NORMAL BOOT + SIM PRESENT.

## Guest progress

B75 path-match correction works:
- PHONEUI_RES_MATCH2: 41
- PHONEUI_RES_CALLER: 41
- PHONEUI_RES_FRAME: 43
- PHONEUI_RES_CONTEXT_DONE: 41
- PHONEUI_RES_ID: 0

The critical Telephone sequence at 19:50:53.829 repeatedly resolves
PhoneUIUtils.dll runtime 0x80EDDE3C = module offset +0x5094 while
phoneui.r01 is being entered/opened/sized/seeked/read.

The later CONE14 stack also contains PhoneUIUtils.dll +0x5094, together with
+0x50B8, +0x3A38, +0x3B2C, +0x3B4C and cone/bafl frames.

CONE14 still carries requested resource ID 0x1099B02D in r6.
Matching RM-356 RPKG still maps this to callhandlingui.r01 resource 0x2D/45.
No callhandlingui.r01 registration/open occurs before panic.

Therefore B75 establishes a real bridge between the valid phoneui.r01
FileServer/resource-init path and the later CONE14 call chain:
PhoneUIUtils.dll +0x5094 is present on both sides.

Do not interpret PHONEUI_RES_ID=0 as loss of the resource ID; the ID becomes
visible later at CONE14 in r6 rather than at the FileServer calls.

## Host crash

The user pressed only the three-dot menu button. Exit Emulator was never chosen.

The .ips matches the canonical B75 Mach-O UUID:
2D8931FD-E4FC-3B1D-91ED-E4ACF3C9462E

This crash is NOT the B70/B74 ipc_msg teardown crash.

Fault:
- EXC_BAD_ACCESS / SIGBUS
- KERN_PROTECTION_FAILURE
- possible pointer-authentication failure
- faulting thread: com.apple.main-thread

Stack:
onMenuController
-> presentGameMenu
-> GameMenuView::showInView
-> UIButton::titleLabel
-> UIButtonLegacyVisualProvider
-> UILabel text attribute setup
-> objc_msgSend/lookup crash

The Symbian OS thread is waiting in the scheduler and is not the faulting
thread.

Reconstructed exact GameMenuView source identifies the implicated line:
b.titleLabel.font = [UIFont systemFontOfSize:18 weight:UIFontWeightMedium];

## Decision

Per the user's rule that a B75 Home crash should now be fixed, B76 targets this
newly proven GameMenuView crash first.

Do not mix a callhandlingui functional patch into B76. Preserve B75 guest
diagnostics so host stability can be validated independently.

The older ipc_msg::~ipc_msg() teardown fix remains deferred unless it
reappears after the menu can be opened and Exit Emulator can actually be
selected.
