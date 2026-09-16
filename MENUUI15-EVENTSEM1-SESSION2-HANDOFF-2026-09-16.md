# MENUUI15 EVENTSEM1 — Session 2 handoff — 2026-09-16

## Authority / frozen baseline

- Device-proven baseline: MENUUI13 FS-DIRUID1.
- Preserve EPOC94 syscall map: 0xAA unmapped, 0xAB message_construct, 0xAC message_kill.
- MENUUI14 INPUTDISPATCH1 FIX2 is diagnostic-only and device-tested for the input path.
- MENUUI14 successful workflow authority commit: `df0ff57277f433c394720857b5391559024dc661`.
- Frozen iOS upstream head used by the authority chain: `661031f9d8ccd37612797e32a52b2d4c6aadfcdc`.

## MENUUI14 device result

The center-screen tap is proven to travel end-to-end through EKA2L1 WindowServer and into the Menu client:

`UIKit -> bridge -> driver -> screen mapping -> HLE hit test -> FIFO -> EventReady wake -> RWsSession::GetEvent()`.

Observed center tap:

- host `(564, 828)`
- guest `(180, 264)`
- pointer number `0`
- target handle `7360904` (`0x705188`)
- target client thread `322`
- DOWN reaches GetEvent as type `5`, evtype `0`
- UP reaches GetEvent as type `5`, evtype `1`
- Menu re-arms EventReady after both events

The same handle `0x705188` also receives `window_visibility_change` events before the tap, so it is an active Menu/CONE window handle, not an arbitrary invalid value.

The center tap is therefore NOT being lost in UIKit, bridge, coordinate transform, HLE FIFO, EventReady, or GetEvent.

## Secondary input bug, not the center-tap root cause

Host touches below the guest display rectangle can be dropped (`INPUT_SCREEN_DROP`). The current HLE separately clamps release events, so an outside-screen sequence can theoretically generate an orphan release. Keep this for later; it does not explain the center icon tap.

## CONE / handle semantics confirmed from Symbian source

`CCoeEnv::RunL()` does:

1. `RWsSession::GetEvent(event)`
2. `handle = event.Handle()`
3. if aligned, reinterpret handle as `CCoeControl*`
4. call `iAppUi->HandleWsEventL(event, window)`

`CCoeControl::CreateWindowL()` constructs `RWindow` with `(TUint32)this` as the client handle. Therefore a WindowServer pointer-event handle is deliberately the destination `CCoeControl*` value expected by CONE.

`CCoeAppUi::HandleWsEventL()` calls `aDestination->ProcessPointerEventL(*aEvent.Pointer())` for `EEventPointer`.

## Strong static candidate: legacy vs advanced pointer semantics

Frozen EKA2L1 `window_server::make_mouse_event()` currently does this for every touch:

```cpp
guest_evt_.adv_pointer_evt_.ptr_num = driver_evt_.mouse_.mouse_id;
guest_evt_.adv_pointer_evt_.modifier = epoc::event_modifier_adv_pointer;
```

So every host touch is unconditionally advertised to the guest as an advanced pointer event.

The frozen opcode table declares `EWsWinOpEnableAdvancedPointers`, but `canvas_base::execute_command_detail()` has no corresponding handler.

Opcode mapping in this frozen table:

- `EWsWinOpEnableVisibilityChangeEvents = 0x74`
- `EWsWinOpClearChildGroup = 0x7F`
- `EWsWinOpEnableAdvancedPointers = 0x91`

The old MENUUI14 log contains unimplemented opcode `0x7F`; that is **ClearChildGroup**, not EnableAdvancedPointers. All three MENUUI14 logs were checked and no `0x91` occurrence was found.

## Official Symbian WSERV comparison

Official Symbian graphics source shows two relevant behaviors:

### non-NGA WindowServer path

`windowing/windowserver/nonnga/SERVER/POINTER.CPP` uses ordinary `TPointerEvent` for pointer routing and queueing. This path does not add the advanced-pointer flag in its normal pointer queue path.

This is the closest public WSERV behavior to the S60v5 / Symbian 9.4 target.

### NGA WindowServer path

For later advanced-pointer-capable WSERV, delivery is still per-window. When a target window has not enabled advanced pointers, real WSERV:

```cpp
if (!aWindow->AdvancedPointersEnabled()) {
    TAdvancedPointerEventHelper::SetPointerNumber(
        aEvent, TAdvancedPointerEvent::EDefaultPointerNumber);
    aEvent.Pointer()->iModifiers &= ~EModifierAdvancedPointerEvent;
}
```

and only then queues the event.

Official handler for `EWsWinOpEnableAdvancedPointers` sets a per-window `EBaseWinAdvancedPointersEnabled` flag and requires it to be requested before window activation.

ClassicUI/CONE also checks `TPointerEvent::IsAdvancedPointerEvent()` in `CCoeControl::ProcessPointerEventL()`, validates the advanced pointer number, and uses the pointer number for pointer-grab routing.

Production ClassicUI search found `Window().EnableAdvancedPointers()` in multi-pointer test controls, not as a blanket behavior for ordinary controls.

## Upstream EKA2L1 status

Current public `EKA2L1/EKA2L1` still shows the same unconditional `event_modifier_adv_pointer` assignment in `make_mouse_event()`. Code search for `EnableAdvancedPointers` finds the opcode declaration but no implementation to backport. This is therefore not already fixed upstream.

## MENUUI15 EVENTSEM1 diagnostic build added

Repository files created:

- `apply_menuui15_eventsem1.py`
- `.github/workflows/build-ios-symbian-systemapps1-menuui15-eventsem1.yml`
- `.github/run-menuui15-eventsem1`

MENUUI15 is **diagnostic-only**. It does not change pointer behavior.

New runtime markers:

- `SYMBIAN-SYSTEMAPPS1 MENUUI15 EVENT_TARGET:`
  - target window id/handle/client thread/type/priority/flags
  - absolute rectangle
  - pointer filter + visible region count
  - parent metadata
  - group metadata
  - modifier, advanced bit, event type, pointer number, coordinates

- `SYMBIAN-SYSTEMAPPS1 MENUUI15 EVENT_GET_FULL:`
  - full event fields immediately before descriptor copy to guest
  - `sizeof(epoc::event)`
  - type/handle/time/evtype/modifier/advanced/position/parent position/z/pointer number

- `SYMBIAN-SYSTEMAPPS1 MENUUI15 ADV_OPCODE:`
  - observes `EWsWinOpEnableAdvancedPointers` and `EWsWinOpSendAdvancedPointerEvent`
  - does NOT consume or implement the command

## Current GitHub Actions state at handoff

MENUUI15 workflow run:

- run id: `35080728869`
- job id: `104743835152`
- trigger head: `8d7d1ba7bb432d009ccfe6f5cec764fe4772795f`
- workflow: `Build EKA2L1 SYMBIAN SYSTEMAPPS1 MENUUI15 EVENTSEM1 IPA`

At the end of Session 2 the job is still `in_progress`, in step:

`Replay device-validated MENUUI14 FIX2 build chain`

Do not claim the build succeeded until this run is checked again.

## Next-session procedure

1. Check run `35080728869`.
2. If failed, fetch job `104743835152` logs, fix patch/workflow, retrigger immediately.
3. If successful, download IPA and audit artifacts; verify ZIP/IPA integrity, SHA-256, and binary markers.
4. Device test on fresh Nokia 5800 RM-356 V60.0.003 session:
   - open Menu and wait for grid
   - tap exactly one center icon once
   - return EKA2L1, Persistent, and TakeThis logs from the same session
5. Interpret:
   - `ADV_OPCODE enable_adv=1`: missing per-window handler is directly material; implement proper state + delivery gating.
   - no `ADV_OPCODE` for Menu + `EVENT_GET_FULL advanced=1`: EKA2L1 is feeding an advanced event to a legacy window; candidate fix is to down-convert/clear the advanced flag for non-enabled windows, matching WSERV semantics.
   - `advanced=0`: advanced-pointer hypothesis is disproven; continue into target/control routing after GetEvent.

## Candidate behavioral fix after confirmation

Use a new MENUUI16 branch/workflow; keep MENUUI13/MENUUI14/MENUUI15 diagnostics initially.

Preferred complete semantic fix, if device evidence confirms it:

- store per-window `advanced_pointers_enabled` state
- implement `EWsWinOpEnableAdvancedPointers`
- default normal windows to legacy pointer delivery
- for non-enabled windows, force pointer number 0 and clear `event_modifier_adv_pointer` before queueing
- preserve advanced delivery only for windows that explicitly enabled it

Do not change the device-proven MENUUI13 authority workflow itself.
