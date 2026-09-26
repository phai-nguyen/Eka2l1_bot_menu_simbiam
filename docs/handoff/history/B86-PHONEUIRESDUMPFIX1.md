# NATIVEBOOT2 B86 PHONEUIRESDUMPFIX1

Date: 2026-09-26
Base: B85 device test, branch `nativeboot2-current`

## B85 results

The B85 `EKA2L1_Persistent-prev` / `EKA2L1_TakeThis` logs show Telephone still panics with CONE 14 at 14:06:27.417. The exact resource ID remains `0x1099B02D`, seen in CPU R6 and twice in the bounded stack window. The log shows `z:\\resource\\VPbkCntModelRes.r01` opened at 14:06:27.083 and again at 14:06:27.091, with VPbk code loaded. It does not prove that file owns the resource ID.

B85 emitted no `PHONEUI_RESID_RSC_CANDIDATE_DUMP` lines. The B85 predicate lowercased the incoming path and compared it to a mixed-case constant (`VPbkCntModelRes.r01`), so the candidate match could never succeed. This explains why the intended capture was absent.

The supplied iOS crash report records `EXC_BAD_ACCESS / SIGSEGV` at address `0x3` at 14:07:24.719 +0700. Its main-thread frames pass through `RootViewController exitEmulator` → `showAppsScreen` → UIKit remote-keyboard/window appearance cleanup. This matches the reported crash after using the game menu to exit. The exact ownership/lifetime cause is not established.

## B86 scope

- Correct only the comparison constant to lowercase so it matches the already-lowercased path.
- Rename the capture log tag to `[NBOOT2][PHONEUI_RESID_CANDIDATE_DUMP_B86]` and require that marker in FASTBUILD's compiled-binary checks.
- Preserve the separate read-only handle, capture bound, and hex-chunk format.
- Do not change iOS `exitEmulator` / `showAppsScreen`, host teardown, guest resource registration, CONE14 behavior, or boot flow.

The Game Menu exit crash is intentionally left untouched for this device test. If B86 reproduces that crash, use its new report/log to fix the host exit path next. If it does not recur, keep the change out and proceed with the VPbk resource evidence.

## Verification

B86 contract tests pass locally, including the FASTBUILD manifest invocation with an upstream directory argument. FASTBUILD/IPA result: pending at commit time.
