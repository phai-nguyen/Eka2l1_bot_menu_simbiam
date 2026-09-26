# EKA2L1 NATIVEBOOT2 — Current

Updated: 2026-09-26

Latest handoff: [NEWCHAT-COMPATBOOT1-MENUPROBE1-2026-09-26.md](NEWCHAT-COMPATBOOT1-MENUPROBE1-2026-09-26.md)
Latest history: [B91-IPCTEARDOWN1.md](history/B91-IPCTEARDOWN1.md)

Repository: `phai-nguyen/Eka2l1_bot_menu_simbiam`
Base branch: `nativeboot2-current` (B89 baseline)
Active PR: [#6 — B90 COMPATBOOT1 Menu Probe](https://github.com/phai-nguyen/Eka2l1_bot_menu_simbiam/pull/6)
Active branch: `codex/compatboot1-menuprobe1`
Latest build-validated source commit: `65ac01722e8a741b3a5d15e2a70dd7763a7df8b3`
Target: RM-356 / Nokia 5800 firmware on EKA2L1 iOS.

Current objective: keep Native Boot as the default and test an explicitly selected CompatBoot path that waits for the UI services before launching firmware `menu3.exe`.

Three clean-install device runs reproduced the shutdown crash with identical `EXC_BAD_ACCESS` at `0x2f`; the stack is `ipc_msg::~ipc_msg()` -> `kernel_system::wipeout()` -> system destruction. B91 neutralizes outstanding IPC message owner/session references before `reset()`, matching the upstream teardown fix while leaving guest IPC behavior unchanged.

FASTBUILD #289 (run `36251856831`) is GREEN on `65ac01722e8a741b3a5d15e2a70dd7763a7df8b3`. B28 validation, all patch regressions, iOS build, binary invariants, unsigned IPA packaging, and upload passed. B90 still confirms real Menu3 launch but no visible surface; the CompatBoot-only `Leave(-5)` trace does not change guest behavior.

Latest IPA artifact: `EKA2L1-NATIVEBOOT2-CURRENT-FAST-NOJAVA-MANIC3-IPA` (ID `10909561923`), from [FASTBUILD #289](https://github.com/phai-nguyen/Eka2l1_bot_menu_simbiam/actions/runs/36251856831); expires 2026-10-10.

PR #6 is still open and unmerged. No firmware image or startup checks were changed to get this build through CI.
