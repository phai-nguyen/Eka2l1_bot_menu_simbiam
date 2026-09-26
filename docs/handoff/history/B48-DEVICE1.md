# B48 XNTHEMEPOST1 — DEVICE1

Date: 2026-09-23  
Status: DEVICE-OBSERVED; DIAGNOSTIC SUCCESS — FileFlush/FS27 hypothesis closed

## Device evidence

Files supplied by the user:

- `EKA2L1(9).log`
- `EKA2L1_Persistent(9).log`
- `EKA2L1_TakeThis(9).log`

Authoritative current-session analysis is based primarily on
`EKA2L1_TakeThis(9).log`, beginning at 22:38:27.509.

Firmware profile remains RM-356 / Nokia 5800 XpressMusic with native phone boot.

## B47 authority remains intact

At 22:38:59.740 native AknSkinSrv still reads:

```
repo=0x102818E8
key=0x00000009
result=0
value_valid=1
value=0x7FFFFFFF
enabled=0
suppressed=1
```

WindowServer remains reachable:

```
AKNSKIN_TFX_WSERV phase=lookup found=1 server_hle=1
```

Therefore B47's stock-V60 TFX suppression conclusion remains unchanged.

## xnthemeserver startup

Home screen first encounters the missing native server at 22:39:03.459.

The guest launches xnthemeserver and it registers at 22:39:03.482:

```
SERVER_REGISTER
process=xnthemeserver[10207254]0001
server=xnthemeserver
```

The server remains alive through emulator teardown; at 22:42:09.768 its
pending request status is cancelled during normal shutdown.

## Decisive B48 FileFlush result

B48 captured 40 native xnthemeserver FileServer FileFlush operations.

Every one of the 40 calls reports:

```
flush_ok=1
completion=0
behavior=OBSERVE_ONLY
```

This includes the exact cache files that were suspicious in B47:

```
C:\Private\10207254\themes\sources\hdrcache.dat
C:\Private\10207254\themes\sources\cleanupfiles.dat
```

and the ROM theme object files under:

```
Z:\Private\10207254\themes\...
```

Example:

```
XNTHEME_FSFLUSH phase=enter
path=Z:\Private\10207254\themes\271012080\270513751\271068379\1.0\ft.o0096
opcode=0x27

XNTHEME_FSFLUSH phase=result
flush_ok=1
completion=0
```

The older MENUUI2 diagnostics agree:

```
FS27 POST-DISPATCH: result=0 hle=1
FS27 POST-PROCESS: HLE service dispatch returned
```

Therefore hexadecimal FileServer opcode `0x27` / decimal 39
(`fs_msg_file_flush`) is not returning `KErrNotSupported(-5)`.

Do not patch FileFlush.

## Interpretation of the recurring xnthemeserver Leave(-5)

There are 37 trapped `Leave(-5)` events in native xnthemeserver.

Many occur immediately after a successful FileFlush, for example:

```
XNTHEME_FSFLUSH ... flush_ok=1 completion=0
FS27 POST-PROCESS: HLE service dispatch returned
V11 LEAVE5 ... r0=0xFFFFFFFB ... last_opcode=0x27
Leave trapped by trap handler
```

B48 proves that the `last_opcode=0x27` correlation is not the error source:
the FileServer operation already completed successfully with 0.

The -5 is generated in guest-side code after the successful IPC and is trapped.
The server continues processing additional theme files and later completes
Home screen requests successfully. Treat these leaves as guest fallback/control
flow unless later evidence proves one escapes its trap or blocks presentation.

## Native xnthemeserver IPC results

Observed Home screen -> xnthemeserver completions include:

- function -1 -> result 0
- function 9 -> result 18
- function 3 -> result 4
- function 4 -> result 6 (repeated)
- function 13 -> result 22

No B48-observed xnthemeserver completion is negative.

Function 4 and function 11 also appear as asynchronous sends. Outstanding
asynchronous sends by themselves are not evidence of failure.

## Post-theme progress

The native Home screen reaches WindowServer/event-loop setup.

At 22:39:04.626:

```
SYMBIAN-SYSTEMAPPS1 MENUUI14 INPUT_EVENTREADY_ARM
```

WindowServer batch traffic continues after this point.

The only negative B48-era Wserv batch result observed after this transition is
three occurrences of op `0x2B` returning `-1`. In the pinned upstream
WindowServer opcode table, decimal 43 / hex 0x2B is
`ws_cl_op_find_window_group_identifier`.

This is a candidate next boundary only. A not-found result from a window-group
lookup can be normal; do not patch it without correlating the visible device
state and caller/target identifier.

Four `RM356_FS_UNKNOWN opcode=80` observations also occur later. The pinned
FileServer opcode table maps decimal 80 to `fs_msg_notify_disk_space`.
These occur after Home screen has entered event-loop setup and are not proven
to be the current presentation blocker.

## Stability

No current-session occurrence of:

- `KERN-EXEC`
- `EIKFAULT_AV`
- `EXC_BAD_ACCESS`
- host access violation

was found.

Exit Emulator remains healthy.

```
22:42:09.732 os_join_begin
22:42:09.776 os_join_done
```

Join time is about 44 ms.

The normal log then reaches:

```
BRIDGE_EXIT_PHASE phase=normal_restart_done has_device=1
```

B41 remains healthy.

## B48 conclusion

B48 is a diagnostic success.

The decisive chain is:

```
native xnthemeserver
 -> FileServer opcode 0x27 / FileFlush
 -> VFS flush succeeds
 -> completion=0
 -> guest later executes trapped Leave(-5)
 -> xnthemeserver continues
 -> Home screen receives successful xntheme completions
 -> Home screen reaches INPUT_EVENTREADY_ARM
```

Therefore the old theme-cache/FileFlush hypothesis is closed.

Do not:
- return -5 from FileFlush to imitate the guest leave;
- suppress the guest Leave(-5);
- change FS-DIRUID1;
- reopen TFX;
- fake xnthemeserver completion values.

## Next-boundary decision

B49 functional behavior is not selected yet.

The next diagnostic should be chosen from the visible device state:

- if Home screen is visually blank/white/black while event-ready is armed,
  trace the post-theme WindowServer presentation/focus path, starting with
  the caller and target of `ws_cl_op_find_window_group_identifier (0x2B)`
  and subsequent focus/window activation;
- if a specific Nokia startup screen is visible but progress stops earlier,
  correlate that exact visual milestone first.

A screenshot or short recording of the B48 device state should accompany the
next step so the WindowServer trace is tied to the actual visual blocker.


## Device video correlation

The user supplied:

`ScreenRecording_09-23-2026 22-38-23_1.mp4`

Video duration is approximately 228.1 seconds at 30 fps, 510x1108.

Observed visual timeline:

- recording begins on the iOS Home Screen;
- emulator launch enters a black display;
- the display remains black through approximately 35 seconds;
- the white Nokia startup screen with blue `NOKIA` logo appears at approximately
  36 seconds;
- the Nokia logo then remains visually unchanged for roughly three minutes;
- at approximately 225 seconds the user opens the emulator exit UI;
- Exit Emulator returns normally to the EKA2L1 library and then iOS Home
  Screen.

The recording filename/start time aligns the logo appearance with roughly
22:38:59, which is the same boot interval in which the B48 log reaches active
WindowServer traffic. The log later reaches native Home screen event-ready,
while the video still shows the unchanged Nokia startup logo.

This is the decisive visual classification for the next boundary:

**rendering itself works, but the boot presentation never transitions away
from the Nokia startup surface to the Home screen.**

Therefore B49 should observe the post-logo WindowServer window-group/focus/
activation/z-order path, rather than theme storage, TFX, or FileFlush.

Project test protocol from this point forward:
the user can provide a screen recording for every device-tested build. Request
the three logs plus a screen recording whenever a new diagnostic build is
device-tested, so log milestones can be correlated with the actual visual
state.
