# B92 — CompatBoot device log

Date: 2026-09-26

Repository: `phai-nguyen/Eka2l1_bot_menu_simbiam`

PR: [#6](https://github.com/phai-nguyen/Eka2l1_bot_menu_simbiam/pull/6)

Build tested on device: FASTBUILD #294, commit
`a9ceeb2b6e589c3195aa533f5f9babbbaa249e0f`.

## Result

The capture shows one CompatBoot session. The six-service barrier became ready
at `05:05:08.040`; the real `Z:\sys\bin\menu3.exe` launched at
`05:05:08.067` as `menu3[101f4cd2]0001`. There is no
`[COMPATBOOT][TARGET_VISIBLE]` record, so a visible Menu surface is not
confirmed.

The first target-specific failure marker is Menu's request for `TfxServer` at
`05:05:13.308`, returning the existing `KErrNotFound` result. Other system
clients request the same missing server earlier. Menu continues running after
its request. Do not treat this marker alone as proof that the missing server
caused Menu's earlier `Leave(-5)`.

The first Menu `Leave(-5)` is at `05:05:13.270`, 38 ms before the target's
`TfxServer` failure marker. It is trapped by the existing guest trap handler.
The captured last IPC context is FileServer opcode `0x27`, with raw arguments
`[0x00805288,0x00000000,0x00000000,0x00020002]`; its HLE dispatch returned 0
before the leave. This establishes ordering and context, not causation. The
trace resolves PC and LR to `euser.dll` offsets `0x2EF4` and `0x166E0`; stack
candidates include `estor.dll` and `XnRequestClient.dll`, but the log has no
symbols to identify the originating function.

## FindEqInt observations

There are five `FindEqInt` requests against attached repository `0x102858F2`.
Every request has `partial_key=0`, `id_mask=0xFFFF0000`, and a valid comparison
value. Every result is `result_count=0 status=-1`.

| Time | Caller | Compared UID/value |
|---|---|---:|
| 05:05:11.400 | Startup | `0x100058F4` |
| 05:05:11.868 | SysAp | `0x100058F3` |
| 05:05:12.332 | Home screen | `0x102750F0` |
| 05:05:12.374 | Telephone | `0x100058B3` |
| 05:05:13.789 | Menu | `0x101F4CD2` |

The first four misses occur before the first Menu leave, and their callers
continue booting. Menu's own miss occurs after both the first leave and its
`TfxServer` miss. This makes that Menu query an unlikely cause of the first
leave, but does not establish whether any query match is optional or required.
The attached repository UID is now known; the capture does not identify its
name or explain the caller-specific query semantics. B92 is marked
`behavior=OBSERVE_ONLY`; the trace does not change IPC results.

Menu later exits with `exit_type=0 reason=0` at `05:05:16.652`. The host-side
shutdown reaches `shutdown_done` at `05:06:54.486`, followed by a normal Native
Boot restart. The user confirms this was **overwrite installation with the
previous logs cleared** (test method 2). This run did not return to iOS Home
with a crash. It is one successful shutdown observation for that install
method; it does not establish results for clean install or overwrite while
retaining logs.

## Supplied files and provenance

- `EKA2L1_Persistent-prev(20260926-221100).log` — full session and shutdown;
  SHA-256 `4e5478b61e8a1c8bf66bcfa99728f4a45dc4a88531c9266ef3b90fe0f2ac86ff`.
- `EKA2L1_TakeThis(20260926-221102).log` — overlapping capture of the same
  session; SHA-256
  `1c3dfc40c134303b0c798a618e10165325cb01d333fba49d86537208c9be3539`.
- `EKA2L1_Persistent(20260926-221041).log` and
  `EKA2L1(20260926-221041).log` are byte-identical post-exit logs (SHA-256
  `38925ecc3d68398302ba9e391f906b537701ff153daf7473f2ffed90fbec1ed5`).
  They show the later normal Native Boot restart and are not separate test
  runs.

## Next step

Keep the Native Boot default, stock firmware values, IPC results, and readiness
barrier unchanged. Do not add a server or guest file based on correlation
alone. Continue diagnosing the first Menu leave from its call path and the
first dependency that prevents Menu from displaying; retain the full log and
capture a screen recording on the next device run.
