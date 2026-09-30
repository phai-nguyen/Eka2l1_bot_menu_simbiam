# B98 — CompatBoot Menu3 FileServer Entry status probe

Date: 2026-09-27

## B97 evidence that selects this probe

At 15:33:34.662 B97 logs a FileServer `Entry` lookup for
`C:\private\101F4CD2\appshell.ini`. One millisecond later the Menu3 thread
traps `Leave(-5)` in `CAknApplication::OpenIniFileLC(RFs&) const`. The leave
record's last IPC is FileServer opcode `0x16`, matching `Entry`. This is a
strong sequence match, but B97 did not log the Entry completion status, so it
does not prove the value Avkon received.

## Change

B98 adds `[COMPATBOOT][MENU3_ENTRY]` to FileServer `entry()` after the VFS
lookup and before the existing IPC completion branches. In explicit CompatBoot
mode, it logs only the active target UID3, the normalized guest path, whether
the entry exists, and the corresponding unchanged status (`KErrNone` or
`KErrNotFound`). This should directly confirm whether the `appshell.ini`
lookup returned `KErrNotFound` before Avkon's `Leave(-5)`.

The probe does not modify `get_entry_info`, `ctx->complete`, guest memory,
firmware, service readiness, TFX/CenRep behavior, Native Boot default, or Menu3
launch. Branch 1 retains the existing B88/B89 behavior as requested; this is
not a no-bypass validation.

## Verification

Pending FASTBUILD on the B98 commit. Do not report GREEN or an IPA before the
GitHub Actions run confirms it. Local B98 contracts cover the target-mode gate,
path/result logging, original completion branches, idempotence, manifest
registration, and the compiled-marker check.

## Device question

After the B98 build is confirmed and device-tested, check whether the trace
reports `appshell.ini` with status `-1` immediately before the Avkon Leave.
Keep the EStor Revert, TfxServer miss, and phone-startup message as separate
observations unless a trace establishes a causal link.
