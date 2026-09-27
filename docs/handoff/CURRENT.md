# EKA2L1 NATIVEBOOT2 — Current

Updated: 2026-09-27

Latest handoff: [NEWCHAT-COMPATBOOT1-MENUPROBE1-2026-09-26.md](NEWCHAT-COMPATBOOT1-MENUPROBE1-2026-09-26.md)
Latest device evidence: [B95 installed-over, retained logs](history/B95-DEVICE1.md)
Latest diagnostic change: [B96 EStor Leave stack export probe](history/B96-ESTORLEAVEEXPORTS1.md)

Repository: `phai-nguyen/Eka2l1_bot_menu_simbiam`
PR: [#6 — B90 COMPATBOOT1 Menu Probe](https://github.com/phai-nguyen/Eka2l1_bot_menu_simbiam/pull/6), open and unmerged
Branch: `codex/compatboot1-menuprobe1`
Worktree: `/workspace/scratch/4ac0d495afb9/Eka2l1_bot_menu_simbiam/.worktrees/compatboot1-menuprobe1`
Base branch: `nativeboot2-current` (B89 baseline)

## Current finding

B95 was installed over the app with old logs retained. The recording lasts
247 seconds. The user observed the unchanged “Phone start-up failed” screen and
then manually chose **Thoát Emulator**; the log records an orderly exit. There
was no automatic return to iOS Home during this run.

CompatBoot reached its six-service barrier and launched the real firmware
`menu3.exe`. The ROM's Themes CenRep `0x102818E8:0x09` returned
`0x7FFFFFFF` (`suppressed=1`); the TFX DLLs exist in the ROM, but no TFX plugin
load or `TfxServer` registration was observed. Menu's first logged
`Leave(-5)` precedes Menu's own `TfxServer` miss by 38 ms. Thus the missing
server is explained by the stock disabled-TFX setting, but the capture does
not prove that it caused Menu's leave or the phone startup failure.

## Current change — B96

B96 adds read-only `[COMPATBOOT][MENU3_LEAVE5_EXPORT]` and
`[COMPATBOOT][MENU3_LEAVE5_CODE16]` diagnostics to the existing Menu3
`Leave(-5)` stack trace. They resolve the nearest loaded E32 export and a
bounded Thumb/ARM instruction window for stack values that map to guest code.
The existing CompatBoot and target-UID gates remain in force; leave/trap
handling, firmware, CenRep, TFX/server behavior, and the six-service barrier
are unchanged.

Local verification: 62 tests passed, two upstream-dependent tests skipped
(64 total); manifest validation and `git diff --check` passed. B96 has not yet been
FASTBUILD-validated. The latest GREEN build is FASTBUILD #313, source commit
`c83d4b3749ba0436ecf467ee25ba087f02a04b09`, run
[36290239618](https://github.com/phai-nguyen/Eka2l1_bot_menu_simbiam/actions/runs/36290239618).

## Next

Build and validate B96 through FASTBUILD. If GREEN, use that IPA for one
CompatBoot capture and inspect the new export/halfword records for the first
Menu `Leave(-5)`. Keep Native Boot as default and do not change firmware, the
stock TFX setting, server behavior, or readiness checks based on B95 alone.
