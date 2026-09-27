# EKA2L1 NATIVEBOOT2 — Current

Updated: 2026-09-27

Latest handoff: [NEWCHAT-COMPATBOOT1-MENUPROBE1-2026-09-26.md](NEWCHAT-COMPATBOOT1-MENUPROBE1-2026-09-26.md)
Latest device evidence: [B97 overlay-install log](history/B97-DEVICE1.md)
Latest diagnostic change: [B96 EStor Leave stack export probe](history/B96-ESTORLEAVEEXPORTS1.md)

Repository: `phai-nguyen/Eka2l1_bot_menu_simbiam`
PR: [#6 — B90 COMPATBOOT1 Menu Probe](https://github.com/phai-nguyen/Eka2l1_bot_menu_simbiam/pull/6), open and unmerged
Branch: `codex/compatboot1-menuprobe1`
Worktree: `/workspace/scratch/4ac0d495afb9/Eka2l1_bot_menu_simbiam/.worktrees/compatboot1-menuprobe1`
Base branch: `nativeboot2-current` (B89 baseline)

## Latest device result — B97

B97 was installed over the existing app with old logs cleared. The user reports
the phone-startup failure remained visible and the app exited cleanly; there
was no video for this run. The log covers about 4m07s and reaches
`shutdown_done`, with no crash sequence. The six-service barrier passed and
real `menu3.exe` launched, but there is no `[COMPATBOOT][TARGET_VISIBLE]`.

The first Menu `Leave(-5)` again follows a successful FileFlush of
`hasclassicgrid.o0001` and maps to stock EStor `CFileStore::DoRevertL()` in the
stack. B97 also records a second `Leave(-5)` from Avkon's
`CAknApplication::OpenIniFileLC(RFs&) const`, whose ROM code explicitly calls
`User::Leave(-5)`. The attempted INI filename and its relationship to phone
startup are not yet known. `TfxServer` is missing for several system processes
before Menu3; the Menu3-scoped first-failure marker is not the first
system-wide miss. Neither that miss nor the EStor Leave is proven to cause the
persistent startup message.

The log also confirms inherited B89 behavior: Telephone `CONE 14` is converted
to a clean exit, and SYSSTART's global-state request `101 -> 116` is overridden
to `109` (`NormalRfOn`). This is a startup-gate bypass that predates B97; the
Phone startup error remained visible despite it. B97 is therefore not a
no-bypass test. The current COMPATBOOT1 scope says not to bypass checks, so
settle whether this inherited B89 behavior remains in the device-test baseline
before the next run. See [B97 device evidence](history/B97-DEVICE1.md).

## Previous device result — B96

B96's 328.7-second recording shows “Phone start-up failed. Contact the
retailer.” still present near the five-minute mark, then shows the emulator's
**Thoát Emulator** dialog near the end. The app did not crash to iOS Home; its
log records `exit_requested` at 14:08:07.628 and `shutdown_done` at
14:08:07.688. There was no `[COMPATBOOT][TARGET_VISIBLE]` marker.

CompatBoot passed its six-service barrier at 14:03:25.436 and launched the
real `menu3.exe` at 14:03:25.463. The first Menu `Leave(-5)` occurred at
14:03:30.669, just after Menu opened and flushed the theme object
`hasclassicgrid.o0001` (`flush_ok=1`, `completion=0`). EPOC9 export mapping
places the first Leave in stock `CFileStore::DoRevertL()`: the ROM Thumb code
loads `-5` into `r0` and calls the EUser `User::Leave(int)` import. The B96
stack contains that call's return address, and its logged `r0` is `0xFFFFFFFB`.
`CStreamStore::Revert()` and destructor frames fit the cleanup path. This
explains this specific trapped Leave, but not why Menu enters Revert or why the
phone-startup screen remains failed. FileFlush had succeeded; the target-scoped
`TfxServer` miss came 38 ms after the Leave and is not established as its cause.
See [B96 device evidence](history/B96-DEVICE1.md).

## Current change — B96

B96 adds read-only `[COMPATBOOT][MENU3_LEAVE5_EXPORT]` and
`[COMPATBOOT][MENU3_LEAVE5_CODE16]` diagnostics to the existing Menu3
`Leave(-5)` stack trace. They resolve the nearest loaded E32 export and a
bounded Thumb/ARM instruction window for stack values that map to guest code.
The existing CompatBoot and target-UID gates remain in force; leave/trap
handling, firmware, CenRep, TFX/server behavior, and the six-service barrier
are unchanged.

Local verification: 62 tests passed, two upstream-dependent tests skipped
(64 total); manifest validation and `git diff --check` passed. FASTBUILD #315
found one B96 integration-test scope assertion error; the assertion was fixed
to cover the whole diagnostic block. FASTBUILD #316 is **GREEN** on source
commit `9268e8bfbf546afef801a3bd24c090a0bdb7affe`, run
[36295344432](https://github.com/phai-nguyen/Eka2l1_bot_menu_simbiam/actions/runs/36295344432).
B28 baseline, milestone application and regressions, iOS compile, binary
invariants, unsigned IPA packaging, and artifact upload all passed. The build
took 121 seconds; iOS compile took 43 seconds.

FASTBUILD #318 ran on the following docs-only commit
`af4a5172ee26e5be083d64b6f50de8d6bdc6fced` and also completed GREEN. It
produced artifact ID `10925518795`, expiring 2026-10-11 07:34 UTC. Since #318
contains no runtime code changes, B97's Leave evidence comes from the same
runtime diagnostics as #316.

Latest IPA artifact: `EKA2L1-NATIVEBOOT2-CURRENT-FAST-NOJAVA-MANIC3-IPA`,
ID `10923757448`, ZIP size 20,011,611 bytes, expires 2026-10-11 04:49 UTC.
The contained unsigned IPA SHA-256 is
`cf9e2ce80f9748d23d04362ab7efe156c796ad935e8496da42dba3c722719cb2`.
On iPhone, open the FASTBUILD #316 run page above in Safari while signed into
GitHub, download that artifact under **Artifacts**, then tap the ZIP in Files
to extract it. Import the unsigned `.ipa` into ESign Match or the usual
sideloading tool to sign and install; Files does not install an unsigned IPA.

## Next

Trace the Phone startup failure and inspect the INI path/status behind
`CAknApplication::OpenIniFileLC`. Continue determining whether Menu's trapped
EStor `KErrNotFound` is expected cleanup or reaches startup. Keep Native Boot
as default; do not change firmware, the stock TFX setting, server behavior, or
readiness checks. Add only read-only caller/status diagnostics if static
analysis cannot resolve the relationship.
