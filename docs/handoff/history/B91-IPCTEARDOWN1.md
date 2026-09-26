# B91 IPC teardown crash fix

Updated: 2026-09-26
Branch: `codex/compatboot1-menuprobe1`
PR: #6 (open; not merged)
Build: FASTBUILD #289, run `36251856831`, commit `65ac01722e8a741b3a5d15e2a70dd7763a7df8b3`

## Device evidence

Three clean-install attempts produced crash reports at 21:53:03, 21:58:05,
and 22:03:07 (+0700). All three have the same signature:

- `EXC_BAD_ACCESS` / `SIGSEGV` / `KERN_INVALID_ADDRESS` at `0x2f`
- Triggered thread: `Symbian OS thread`
- Stack: `eka2l1::ipc_msg::~ipc_msg()` -> `kernel_system::wipeout()` ->
  `system_impl::~system_impl()` -> `system::~system()` -> iOS `os_thread`
- Logs show `BRIDGE_EXIT_PHASE exit_requested` and `os_join_begin`, but no
  `shutdown_done`.

Before exit, CompatBoot reaches `BARRIER_READY` and launches real `menu3.exe`.
The Menu3 path reports its first missing dependency and `Leave(-5)` traces;
these guest events are separate from the host-side teardown crash.

## Root cause

The B28 `kernel_system::wipeout()` destroys sessions and servers before it
resets the IPC message array. Destroying a still-referenced `ipc_msg` calls its
destructor, which forces its final `unref()`. That unref may dereference the
message's stale `msg_session` or `own_thr`; the device reports a low invalid
address during this exact destructor/wipeout path. This matches upstream
commit `437b29006bd8a0186f4070c9445f43e98e5c7435`, which documents and fixes
this teardown lifetime class.

## B91 change

Immediately before resetting each non-null IPC message during full kernel
wipeout, B91 clears `own_thr`, `msg_session`, and `ref_count`. The destructor
then has no stale owner/session side effects to run. This is shutdown-only:
normal IPC operation, guest-visible error handling, NativeBoot default, and
firmware state are unchanged. No dependency is fabricated and no startup
readiness check is bypassed.

FASTBUILD #288 (`36251705615`) caught a patch-application mismatch before
compilation: B28's `msgs_[i].reset();` line has trailing spaces. The patcher was
changed to accept trailing horizontal whitespace, with a regression reproducing
that exact source shape.

## Verification and artifact

FASTBUILD #289 (`36251856831`) is GREEN. B28 baseline validation, post-bootstrap
application and regressions, iOS build, binary invariants, IPA packaging, and
both artifact uploads passed. Local `python3 -m unittest discover -p
'test_*.py'` passed 48 tests; manifest validation and `git diff --check` passed.

- IPA artifact: `EKA2L1-NATIVEBOOT2-CURRENT-FAST-NOJAVA-MANIC3-IPA`
- Artifact ID: `10909561923`
- Run: https://github.com/phai-nguyen/Eka2l1_bot_menu_simbiam/actions/runs/36251856831
- Expires: 2026-10-10 (14-day artifact retention)
- IPA filename in ZIP: `EKA2L1-NATIVEBOOT2-CURRENT-FAST-NOJAVA-MANIC3-unsigned.ipa`

Build GREEN confirms compilation and packaging only; the fix is not yet
confirmed on device. Install this IPA and repeat the clean-install exit test.
Do not merge PR #6 until the user evaluates the device result.
