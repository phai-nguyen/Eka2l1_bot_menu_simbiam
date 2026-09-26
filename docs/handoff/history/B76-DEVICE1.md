# NATIVEBOOT2 B76 GAMEMENUSAFETITLE1 — DEVICE1

Date: 2026-09-25
Status: DEVICE-PASS; HOST GAME MENU STABLE; EXIT EMULATOR CLEAN
Selected route: NORMAL BOOT + SIM PRESENT

## Device inputs

Received:
- EKA2L1(20260925-133836).log
- EKA2L1_TakeThis(20260925-133844).log
- EKA2L1_Persistent-prev(7).log
- ScreenRecording_09-25-2026 20-35-29_1.mp4

No .ips was produced.

## Host validation

User opened the three-dot GameMenu and pressed Cancel repeatedly.
The app did not crash to iOS Home.

User then selected Exit Emulator normally.
The app returned to the EKA2L1 host UI without crashing.

The host log reaches:
[NBOOT2][BRIDGE_EXIT_PHASE] phase=normal_restart_done has_device=1

Therefore B76 closes the B75 main-thread UIButtonLegacyVisualProvider/titleLabel
crash for this device test and does not reproduce the older
ipc_msg::~ipc_msg() teardown crash either.

Host crash track is now CLOSED unless a future build reproduces a new .ips.

## Guest state

Guest startup blocker is unchanged.

Telephone still self-panics:
- UID3 0x100058B3
- category CONE
- reason 14
- r6 = 0x1099B02D

B75 PhoneUI resource probes still fire for phoneui.r01.
No callhandlingui.r01 registration/open occurs before CONE14.

## Diagnostic correction before B77

The repeated B75/B76 value PhoneUIUtils.dll +0x5094 is not sufficient evidence
of an executing function frame.

B71 code-window bytes around +0x5094 decode as UTF-16 literal/descriptor data,
including the resource-path text. +0x50B8 is the same literal region.

The CONE14 stack does contain real Thumb return-address candidates inside
PhoneUIUtils, including:
- +0x1BC0
- +0x3A38
- +0x3B2C
- +0x3B4C

Therefore B77 must resolve the exact firmware export for
CPhoneResourceResolverBase::BaseConstructL() and correlate that function's
runtime address rather than treating the full image range as executable code.
