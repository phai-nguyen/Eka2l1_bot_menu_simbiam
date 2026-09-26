# B91 post-fix device result and Menu3 trace

Updated: 2026-09-26
Branch: `codex/compatboot1-menuprobe1`
PR: #6 (open; not merged)
Latest confirmed build: FASTBUILD #289, run `36251856831`, source commit
`65ac01722e8a741b3a5d15e2a70dd7763a7df8b3`

## Result

The user reports that this attempt no longer crashes back to the iOS Home
screen. The log captures the requested exit through `os_join_done`,
`state_reset_done`, and `shutdown_done`. This is one successful shutdown
observation. The install method was not stated, and the log does not embed an
IPA build ID, so do not classify it as a clean-install validation series.

## CompatBoot and Menu3 evidence

- `BARRIER_READY` at `22:45:52.948`; all six required services were present.
- Real `Z:\sys\bin\menu3.exe` launched once at `22:45:52.965` as
  `menu3[101f4cd2]0001`.
- `[COMPATBOOT][TARGET_VISIBLE]`: zero occurrences. A visible Menu surface is
  not confirmed by this log.
- The first Menu3 failure marker is `MISSING_SERVER`, `server=TfxServer`, at
  `22:45:58.428`. Earlier, Themes CenRep `0x102818E8` key `0x09` was read as
  `0x7FFFFFFF` (`enabled=0 suppressed=1`), matching the stock firmware value.
  Menu3 continues after the missing-server result. Do not enable TFX or create
  a replacement server.

The first `[COMPATBOOT][MENU3_LEAVE5]` is at `22:45:58.391`, 37 ms before the
TfxServer miss. The immediately preceding FileServer `FileFlush` completes
with result 0 (`hle=1`); the `Leave(-5)` is trapped. It is not evidence of a
failed flush or a fatal Menu3 exit.

At `22:45:58.894`, Menu3 sends CentralRepository opcode 12. The HLE completion
is status `-1`; the raw arguments are
`[0x0050385C, 0x101F4CD2, 0x00503870, 0x0000000D]`. These values include guest
addresses and have not been decoded into a repository/key/query. Treat this
as an unresolved negative CenRep result, not yet as a missing dependency.

At `22:45:59.694`, FileServer `Fs::Entry` for
`C:\private\101F4CD2\appshell.ini` returns `-1`. The same path is opened at
`22:45:59.697`, then FileFlush returns success. Its earlier absent-entry result
does not establish that the file is required.

At `22:46:01.937`, Menu3's own thread exits with `exit_type=0 reason=0`. The
process exit is guest-side and is not a host crash. Its cause remains unknown.
The emulator's later shutdown reaches `shutdown_done` at `22:48:28.316`, in
agreement with the user's report.

## Next diagnostic

Identify the exact B28 CentralRepository opcode-12 handler and determine how
it consumes the four IPC arguments. If a new trace is needed, decode only
validated descriptor/query data and preserve the returned status and guest
behavior. Keep Native Boot as the default; leave stock firmware values,
readiness checks, `appshell.ini`, and `TfxServer` behavior untouched. The next
device evidence should establish whether Menu3's window ever becomes visible
and what causes its self-termination.

## Capture integrity

Source log: `EKA2L1_Persistent-prev(20260926-155027).log`

```text
b3cf63d4c9a00789e6d4df4a38879143db85061ae09ada22c8d250702f6a7463
```

Overlapping capture: `EKA2L1_TakeThis(20260926-155027).log`

```text
6e6ebd1e377cca396f2a21a6e1ce6b9c0238eaf6c731c5281e7e569b9d5433cf
```

`EKA2L1(20260926-155019).log` and
`EKA2L1_Persistent(20260926-155020).log` are byte-identical; SHA-256:

```text
943f7d77ca5232542268c15668b093040042c750a3e845cdd8648cc3e8022246
```

The supplied screen recording is not from this run: its metadata creation time
is `2026-09-26T15:08:41Z` with duration 14:10, earlier than the log session
around 15:45Z. It is excluded as evidence for whether the Menu3 surface was
visible during this attempt.

FASTBUILD #289 remains the latest confirmed green build and IPA artifact.
This device observation does not create a new build result or change the open
PR status.
