# B93 — CompatBoot device run with retained logs

Date: 2026-09-27

Repository: `phai-nguyen/Eka2l1_bot_menu_simbiam`

PR: [#6](https://github.com/phai-nguyen/Eka2l1_bot_menu_simbiam/pull/6)

Build tested: FASTBUILD #294, commit
`a9ceeb2b6e589c3195aa533f5f9babbbaa249e0f`.

Install method: overwrite installation while retaining prior logs (test method
3, following the user's three-mode test plan).

## Device result

The video shows the emulator mode chooser, then a black screen, followed by
the Nokia boot logo. The logo remains visible through most of the 4m30s
recording; no Symbian Menu surface appears. The log confirms the six-service
barrier was ready at `05:32:18.450` and real `Z:\sys\bin\menu3.exe` launched
at `05:32:18.471` as `menu3[101f4cd2]0001`. There is no
`[COMPATBOOT][TARGET_VISIBLE]` record.

Menu's first `Leave(-5)` is at `05:32:23.536` and is trapped. Its last IPC
context is FileServer opcode `0x27`; the HLE dispatch returns 0. The first
target-specific failure marker follows at `05:32:23.573`, when Menu requests
`TfxServer` and receives the existing not-found result. This is 37 ms after
the first leave, so the missing server does not explain that first leave. The
log has no other Menu-origin missing-server entry in this run.

Menu makes the same five `FindEqInt` queries as in B92, all against repository
`0x102858F2`, with `partial_key=0`, `id_mask=0xFFFF0000`, and
`result_count=0 status=-1`:

| Time | Caller | Compared UID/value |
|---|---|---:|
| 05:32:21.711 | Startup | `0x100058F4` |
| 05:32:22.185 | SysAp | `0x100058F3` |
| 05:32:22.634 | Home screen | `0x102750F0` |
| 05:32:22.675 | Telephone | `0x100058B3` |
| 05:32:24.055 | Menu | `0x101F4CD2` |

As in B92, Menu's own query happens after the first leave and TfxServer miss;
it is not the cause of that first leave. The four earlier query misses also
precede it. Together, B92 and B93 reproduce the same server/query/leave order
under install methods 2 and 3. This still does not establish whether a CenRep
match is required or whether absent `TfxServer` prevents drawing the menu.

Menu's second process instance eventually exits with `exit_type=0 reason=0` at
`05:32:26.922`, about 8.45 seconds after the target launch. Host shutdown
reaches `shutdown_done` at `05:36:12.469`; the short post-session log records
`normal_restart_done has_device=1` at `05:36:12.600`. The video ends on the
iOS Home screen, but no crash report was supplied, so the video alone cannot
distinguish a user exit from an app crash after the logged orderly shutdown.

## Supplied files

- `Log(1).zip` — SHA-256
  `8c83ee4542fe66124b09bada83e3895d140e2e6b8d80b12c675c3ccd7439c737`.
- `ScreenRecording_09-27-2026 05-31-44_1.mp4` — SHA-256
  `96cf2c7bb41342f8274f8db0588de8d86202ebda8fb5699bdcf72f5e02fa317b`.
- The ZIP's short `EKA2L1_Persistent.log` and `EKA2L1.log` are byte-identical;
  they record the later normal restart. The long
  `EKA2L1_Persistent-prev.log` and `EKA2L1_TakeThis.log` overlap the same
  CompatBoot run.

## Next step

Do not change firmware values, IPC results, Native Boot default, or the
readiness barrier. Since B92 and B93 repeat the same event order, prioritize
symbolicating the first Menu `Leave(-5)` stack and decoding the FileServer
operation from the RM-356 firmware/available symbols. Treat `TfxServer` as an
observed missing service, not yet a proven cause of the absent Menu surface.
