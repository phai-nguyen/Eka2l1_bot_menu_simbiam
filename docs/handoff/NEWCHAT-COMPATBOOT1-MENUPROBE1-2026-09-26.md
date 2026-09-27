# New-chat handoff — COMPATBOOT1-MENUPROBE1

Updated: 2026-09-27

## Continue from here

- Repository: `phai-nguyen/Eka2l1_bot_menu_simbiam`
- PR: [#6 — B90 COMPATBOOT1 Menu Probe](https://github.com/phai-nguyen/Eka2l1_bot_menu_simbiam/pull/6)
- Branch: `codex/compatboot1-menuprobe1`
- Latest build-validated source commit: `9268e8bfbf546afef801a3bd24c090a0bdb7affe`
- Worktree used: `/workspace/scratch/4ac0d495afb9/Eka2l1_bot_menu_simbiam/.worktrees/compatboot1-menuprobe1`
- Base branch remains `nativeboot2-current` at the B89 baseline.

Do not restart earlier milestone research. The current objective is COMPATBOOT1-MENUPROBE1: retain Native Boot as the default, wait for the required UI services, then launch the real firmware `menu3.exe` and report the first missing dependency or visible target marker. No firmware replacement or readiness bypass is part of this change.

## Newest device result and next diagnostic — B96

B96's 328.7-second recording still shows “Phone start-up failed. Contact the
retailer.” near the five-minute mark. The user opened **Thoát Emulator** near
the end; `exit_requested` and `shutdown_done` confirm normal exit. The app did
not crash to iOS Home, and `[COMPATBOOT][TARGET_VISIBLE]` did not occur. See
[B96 device evidence](history/B96-DEVICE1.md).

Static disassembly of stock `estor.dll` resolves the first Menu `Leave(-5)`:
`CFileStore::DoRevertL()` constructs `0xFFFFFFFB` and calls the EUser
`User::Leave(int)` import. The Leave stack contains the return address after
that call and the same `r0=-5`; `CStreamStore::Revert()` and destructor frames
fit the cleanup path. FileFlush success is not the source of this Leave. This
does not show why Menu called Revert or whether the trapped Leave causes the
persistent phone-startup failure. Menu's `TfxServer` miss occurs 38 ms later
and is not established as its cause. Next, inspect the Menu caller and phone
startup path; add only read-only diagnostics if static analysis is
insufficient. Do not change firmware, stock TFX/CenRep state, server behavior,
Native Boot default, or readiness checks. See
[B96 diagnostic](history/B96-ESTORLEAVEEXPORTS1.md) and [CURRENT](CURRENT.md).

Latest IPA: artifact `EKA2L1-NATIVEBOOT2-CURRENT-FAST-NOJAVA-MANIC3-IPA`, ID
`10923757448`, expires 2026-10-11 04:49 UTC; IPA SHA-256
`cf9e2ce80f9748d23d04362ab7efe156c796ad935e8496da42dba3c722719cb2`. On
iPhone, open [FASTBUILD #316](https://github.com/phai-nguyen/Eka2l1_bot_menu_simbiam/actions/runs/36295344432)
in Safari while signed into GitHub, download the artifact, tap its ZIP in
Files to extract, then import the unsigned `.ipa` into ESign Match or the usual
sideloading tool to sign and install.

## Previous diagnostic build — B94 teardown probe and FASTBUILD #313

B94 added read-only diagnostics, enabled only in explicit CompatBoot mode, for
process kill entry, property cancellation, `notify_info::complete()` status
translation, and the matching process address-space lookup. It logs the
requester/process, property reference, guest status address, resolved host
pointer, and whether the cancel path itself checks requester liveness. It does
not change completion results, signal count, firmware, Native Boot default,
Menu3 launch, or the readiness barrier.

FASTBUILD #313, run
[36290239618](https://github.com/phai-nguyen/Eka2l1_bot_menu_simbiam/actions/runs/36290239618),
is **GREEN** on commit `c83d4b3749ba0436ecf467ee25ba087f02a04b09`.
B28 baseline, patch application, regressions, iOS compile, binary invariants,
unsigned IPA packaging, and artifact upload passed. Local discovery passed 41
tests (one skipped); the B94 contract passed 7 tests. This confirms the
diagnostic build compiles; it does not establish the B94 crash's root cause or
confirm a visible Menu surface.

Latest IPA artifact:

- `EKA2L1-NATIVEBOOT2-CURRENT-FAST-NOJAVA-MANIC3-IPA`, ID `10921448412`
- ZIP contains `EKA2L1-NATIVEBOOT2-CURRENT-FAST-NOJAVA-MANIC3-unsigned.ipa`
- IPA SHA-256: `f9e2a019dd92941fc73694f9d36eee22eebce5738c2e07cba3115c894514aa72`
- Artifact expires 2026-10-11 03:04 UTC; ZIP size 20,011,779 bytes
- Run page: [FASTBUILD #313](https://github.com/phai-nguyen/Eka2l1_bot_menu_simbiam/actions/runs/36290239618)

On iPhone, open the run page in Safari while signed in to GitHub. Under
**Artifacts**, download `EKA2L1-NATIVEBOOT2-CURRENT-FAST-NOJAVA-MANIC3-IPA`.
In Files, tap the ZIP to extract it, then import the unsigned `.ipa` into
ESign Match (or the user's usual sideloading tool) to sign and install it.
Files cannot install the unsigned IPA directly.

## Previous milestone — Menu3 FileFlush trace and FASTBUILD #302

B92 adds `[COMPATBOOT][CENREP_FIND_EQ_INT]` in `central_repo_client_subsession::find()`. It logs the attached repository UID, validated filter values, signed comparison value, result count, and status, gated on `compat_menu_probe_mode` and the `cen_rep_find_eq_int` opcode. It does not change the result or completion status. The FASTBUILD integration contract verifies that this patch applies to the B28 cache and that the trace remains after argument validation.

The latest change adds a read-only `[COMPATBOOT][MENU3_FSFLUSH]` trace scoped to the active CompatBoot target UID3. It records process/thread, handle, path, `flush_ok`, and IPC completion while preserving the flush result and completion path. B28 has the earlier B48 implementation, so this trace reuses `b48_flush_ok` and does not call `flush()` a second time. `<config/config.h>` is included so `config::state` is complete at the access site.

FASTBUILD #299 and #300 stopped in patch application because the source shape is B48's `b48_flush_ok` form. FASTBUILD #301 passed patch application/regressions but compile found incomplete `config::state` in `files.cpp`. These were fixed without changing firmware or IPC results. FASTBUILD #302, run [36279806117](https://github.com/phai-nguyen/Eka2l1_bot_menu_simbiam/actions/runs/36279806117), is **GREEN** on commit `c0a1056069cb709895c72ef9093e7dbb1d8ebcca`: B28 baseline, patch application/regressions, iOS compile, binary invariants, unsigned IPA packaging, and artifact upload all passed.

Latest IPA artifact:

- `EKA2L1-NATIVEBOOT2-CURRENT-FAST-NOJAVA-MANIC3-IPA`, ID `10918187160`
- IPA in ZIP: `EKA2L1-NATIVEBOOT2-CURRENT-FAST-NOJAVA-MANIC3-unsigned.ipa`
- Artifact expires 2026-10-10 23:36 UTC
- ZIP size: 20,006,864 bytes
- IPA SHA-256: `2c46be975611125673b19ae89b4e2220b20f10e390ab42d23afd30037e139331`
- Run page: [FASTBUILD #302](https://github.com/phai-nguyen/Eka2l1_bot_menu_simbiam/actions/runs/36279806117)

On iPhone, open the FASTBUILD #302 run page in Safari while signed in to GitHub. Under **Artifacts**, download `EKA2L1-NATIVEBOOT2-CURRENT-FAST-NOJAVA-MANIC3-IPA`. In Files, tap the downloaded ZIP once to extract it. Import the unsigned `.ipa` into ESign Match (or the user's normal sideloading tool) to sign/install it; Files cannot install it directly.

## B94 installed-over crash result

B94 was installed over the prior app and the old logs were cleared. The user confirms the video shows the app running and crashing to iOS Home without a swipe; this does not change the B93 manual-exit result. The capture reached `BARRIER_READY`, launched real `menu3.exe`, and recorded two successful Menu3 FileFlush calls (`flush_ok=1`, `completion=0`). It still had trapped `Leave(-5)`, a missing `TfxServer`, zero CenRep matches for Menu3's `FindEqInt`, and no `TARGET_VISIBLE`.

The iOS .ips report records `EXC_BAD_ACCESS / KERN_PROTECTION_FAILURE` at a PC resolving to `vtable for eka2l1::kernel::chunk + 16`. The stack passes through `notify_info::complete()`, `property::cancel()`, `property_reference::~property_reference()`, `kernel_system::destroy()`, and `process::kill()`. This points to an invalid virtual dispatch or object-lifetime problem during guest process teardown, but does not yet identify the stale object or guest process. Full capture details and hashes are in [B94 crash evidence](history/B94-CRASH1.md).

## B94 next-work item — superseded by B95

B94's teardown investigation is recorded in
[history/B94-TEARDOWNPROBE1.md](history/B94-TEARDOWNPROBE1.md). B95 exited
normally after a longer device run, so the active next step is B96's Menu3/
EStor stack resolution above, not another repetition of B94's test.

PR #6 is still open and unmerged. B92 (test method 2) and B93 (method 3) both reached `BARRIER_READY` and launched real `menu3.exe`; neither emitted `[COMPATBOOT][TARGET_VISIBLE]`. B93's video shows the Nokia logo persisting without the Symbian Menu. Its logs record `shutdown_done` and `normal_restart_done has_device=1`; the user confirms they exited manually, without a crash. All five `FindEqInt` calls against repo `0x102858F2` returned `-1`; the Menu query for UID3 `0x101F4CD2` followed the first trapped `Leave(-5)` and the first Menu `TfxServer` miss. The matching order across methods 2 and 3 does not identify the cause. The B93 checkpoint proposed symbolizing the Leave stack and decoding opcode `0x27`; FASTBUILD #302 now adds the read-only FileFlush path/result trace for the next device capture. See [B93 device evidence](history/B93-DEVICE1.md) and [B92 device evidence](history/B92-DEVICE1.md).

## Earlier build checkpoints

FASTBUILD #281, run [36241917700](https://github.com/phai-nguyen/Eka2l1_bot_menu_simbiam/actions/runs/36241917700), is **GREEN** on commit `0bced6f0f897cfcce0e214ce77814177800c9887`. B28 baseline validation, manifest regressions, CMake configuration, iOS compile, binary invariants, unsigned IPA packaging, and artifact upload all succeeded.

The next patch added a CompatBoot-only `Leave(-5)` trace for Menu3: register values, trap/caller frame resolution, and at most 32 stack words. The trace leaves exception handling and guest behavior unchanged. FASTBUILD #284 initially stopped in patch application because the GitHub copy of the patcher had acquired a truncated-output banner. It was restored from the worktree in commit `2ff5817ef0e347d59408632d944b6a89059d9ce5`. FASTBUILD #285, run [36245715377](https://github.com/phai-nguyen/Eka2l1_bot_menu_simbiam/actions/runs/36245715377), is **GREEN** on that commit. It passed B28 baseline validation, manifest regressions, iOS compile, binary marker invariants, unsigned IPA packaging, and artifact uploads.

The two previous compile failures and fixes:

- FASTBUILD #278 exposed the injected `eka2l1::kernel::svc` helper namespace left open before the original `eka2l1::epoc` block. This nested the rest of `svc.cpp` and caused the `security_policy`, `ptr`, and `LOG_WARN` cascade. The helper now closes its namespace. Its version lookup uses `kernel_system::get_epoc_version()` instead of dereferencing the forward-declared `system` type.
- FASTBUILD #279 then exposed the target-visible marker's `config::state` lookup resolving under `epoc::config` and its `ctx.sys` dereference of incomplete `system`. It now uses `eka2l1::config::state` and the existing window-client path `client->get_ws().get_kernel_system()->get_config()`.
- The final local suite passed 44 Python tests; the COMPATBOOT contract module passed all 17 tests; `ci/fastbuild1_manifest.py validate .` and `git diff --check` passed.

## Earlier IPA artifact (#285)

- Artifact: `EKA2L1-NATIVEBOOT2-CURRENT-FAST-NOJAVA-MANIC3-IPA`
- Artifact ID: `10907232828` (FASTBUILD #285; latest artifact)
- IPA inside the ZIP: `EKA2L1-NATIVEBOOT2-CURRENT-FAST-NOJAVA-MANIC3-unsigned.ipa`
- Expiration: 2026-10-10 (14-day retention)
- Run page: [FASTBUILD #285](https://github.com/phai-nguyen/Eka2l1_bot_menu_simbiam/actions/runs/36245715377)

On iPhone, open the run page in Safari while signed in to GitHub, scroll to **Artifacts**, and tap the IPA artifact name. In Files, open **Downloads** and tap the downloaded ZIP once to extract it. Import the `.ipa` into ESign Match to sign/install it; this workflow deliberately produces an unsigned IPA, so tapping the IPA in Files alone will not install it.

## B90 device result

B90 (`EKA2L1_TakeThis(20260926-125351).log`) confirms the barrier became ready and launched real `menu3.exe`. The visible marker did not fire. The first system-wide TfxServer miss is from `eiksrvs` at 19:49:16.979; Menu3 reports its own first failure at 19:49:21.932. Before those misses, AknSkinSrv reads Themes CenRep `0x102818E8` key `0x09` as `0x7FFFFFFF` (`enabled=0 suppressed=1`). Alfred starts and its AppServer registers successfully, but no TFX plugin DLL load or `TfxServer` registration is observed. See [B90 device evidence](history/B90-COMPATBOOT1-DEVICE1.md).

The observed value `0x7FFFFFFF` matches the extracted stock V60 ROM repository default for `0x102818E8:0x09`; generic `changes saved` lines do not establish a per-key write. Menu continues after the expected missing `TfxServer`. Its next notable event is FileServer `Fs::Entry` opcode 22 for `C:\\private\\101F4CD2\\appshell.ini`, returning `KErrNotFound`, followed by `Leave(-5)` in the same thread. This is correlated evidence, not proof the file is required or caused the leave. FASTBUILD #285 passed with the CompatBoot-only register/trap/32-word stack trace, preserving the leave path, so this IPA can be used for the next device capture. Do not force-enable TFX, create `appshell.ini`, fabricate a server, or change firmware.

- `[COMPATBOOT][BARRIER_WAIT]` / `[COMPATBOOT][BARRIER_READY]`
- `[COMPATBOOT][TARGET_LAUNCH]`
- `[COMPATBOOT][FIRST_FAILURE]` and the exact missing server, if Menu3 stops
- `[COMPATBOOT][TARGET_VISIBLE]`, if a Menu3 window becomes visible

FASTBUILD proves the binary compiles and preserves its markers. It does not prove that the firmware menu is visible on the phone. PR #6 is unmerged, and device acceptance remains pending.

## B91 shutdown crash result (before fix)

Three new clean-install attempts reproduced the same host crash: `EXC_BAD_ACCESS`
at `0x2f` on the `Symbian OS thread`, with the stack
`ipc_msg::~ipc_msg()` -> `kernel_system::wipeout()` -> system destruction ->
iOS `os_thread`. The logs end after `exit_requested` / `os_join_begin` and do
not reach `shutdown_done`. The guest Menu3 `Leave(-5)` diagnostics occur before
exit and are a separate issue.

Root cause was confirmed against B28 source: wipeout destroys sessions/servers,
then resets messages; an outstanding message destructor forces `unref()` and
can touch stale `msg_session` / `own_thr`. B91 nulls those references and zeros
the count before reset, only during full kernel shutdown. NativeBoot remains the
default; no firmware values, guest IPC semantics, or readiness checks changed.
See [B91 evidence](history/B91-IPCTEARDOWN1.md).

FASTBUILD #288 (`36251705615`) stopped before compilation because the patch
anchor omitted trailing spaces in the B28 reset line. The B91 regression now
includes that source shape, and the patcher accepts the trailing whitespace.
FASTBUILD #289, run [36251856831](https://github.com/phai-nguyen/Eka2l1_bot_menu_simbiam/actions/runs/36251856831),
is GREEN on `65ac01722e8a741b3a5d15e2a70dd7763a7df8b3`: B28 validation,
manifest apply/regressions, iOS build, binary checks, unsigned IPA packaging,
and upload all passed. Local unittest discovery passed 48 tests.

Artifact at the #289 checkpoint (superseded by #294 above):

- `EKA2L1-NATIVEBOOT2-CURRENT-FAST-NOJAVA-MANIC3-IPA`
- Artifact ID `10909561923`; expires 2026-10-10
- ZIP contains `EKA2L1-NATIVEBOOT2-CURRENT-FAST-NOJAVA-MANIC3-unsigned.ipa`
- Download from the FASTBUILD #289 run page above, open/extract the ZIP in Files,
  then import the unsigned IPA into ESign Match to sign and install it.

At the time of the original B91 handoff, this build had not been device-validated.
The later post-fix attempt is recorded below.

## B91 post-fix device result

The user reports that the latest attempt exited without crashing back to the
iOS Home screen. The persistent device log ends the requested exit through
`os_join_done`, `state_reset_done`, and `shutdown_done`; no crash signature is
present in this capture. The install method was not stated, so record this as
one successful shutdown observation, not a clean-install validation series.

CompatBoot reached `BARRIER_READY` and launched the real firmware
`Z:\sys\bin\menu3.exe` as `menu3[101f4cd2]0001`. The log has zero
`[COMPATBOOT][TARGET_VISIBLE]` records, so the guest Menu surface is not
confirmed. The first Menu3 failure marker is a missing `TfxServer` at
22:45:58.428. Before it, Themes CenRep `0x102818E8:0x09` was read as
`0x7FFFFFFF` (`enabled=0 suppressed=1`), matching the stock firmware setting;
Menu3 continues after the missing server.

The first Menu3 `Leave(-5)` is at 22:45:58.391. Its preceding FileServer
`FileFlush` completes with result 0, and the leave is trapped. Later, an
`appshell.ini` `Fs::Entry` returns `-1`, but the same path is successfully
opened shortly afterward. At 22:45:58.894, CentralRepository opcode 12 returns
`-1` for Menu3 message 231. The current upstream enum maps opcode 12 to
`cen_rep_find_eq_int`; the handler treats arg0 as a key-filter descriptor,
arg1 as the signed integer to match, arg2 as the result array, and arg3 as the
subsession ID. Here arg1 is Menu3 UID3 `0x101F4CD2`, and `-1` means no key in
the attached repository matched the filter and value. The filter contents and
repository UID remain unknown. This is a query miss, not evidence that the
CenRep service or repository is absent. Cross-reference:
[upstream opcode enum](https://github.com/EKA2L1/EKA2L1/blob/dd3e2219f561d5f938cbd78c606980bbd5cd4723/src/emu/services/include/services/centralrepo/common.h#L42)
and [upstream Find handler](https://github.com/EKA2L1/EKA2L1/blob/dd3e2219f561d5f938cbd78c606980bbd5cd4723/src/emu/services/src/centralrepo/repo.cpp#L517-L640).
The current source routes arg3 to a subsession and reads the repository UID
during `init` ([session handler](https://github.com/EKA2L1/EKA2L1/blob/dd3e2219f561d5f938cbd78c606980bbd5cd4723/src/emu/services/src/centralrepo/centralrepo.cpp#L815-L857)).
The existing B83 entry marker is in the subsession handler, so it misses that
UID and the filter descriptor values. The B28 cache source is not present in
this worktree; verify the mapping against that baseline before changing
instrumentation or drawing a repository-specific conclusion. Menu3's thread
later exits with
`exit_type=0 reason=0` at 22:46:01.937. This is not a host crash and does not
identify which guest condition caused Menu3 to exit.

The supplied 14:10 screen recording has metadata creation time 15:08 UTC and
ends before this log's 22:45 local-time session; do not use it as visual
evidence for this attempt. Full evidence and hashes are in
[B91 post-fix device evidence](history/B91-POSTFIX-DEVICE1.md).

The B92 trace now covers that `FindEqInt` request on the B28 cache. It logs the
repository UID, validated filter values, comparison value, result count, and
status only for CompatBoot, while preserving IPC completion semantics. The
latest GREEN build is #294 above. Preserve the stock firmware state, Native
Boot default, and all startup checks. PR #6 stays open and unmerged.
