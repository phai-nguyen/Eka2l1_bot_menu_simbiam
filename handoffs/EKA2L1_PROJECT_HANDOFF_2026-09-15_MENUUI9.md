# EKA2L1 iOS / Symbian Menu3 — Full Project Handoff

Date: 2026-09-15

Canonical Library root: `/EKA2L1_bot_menu_simbiam`
Canonical GitHub repo: `phai-nguyen/Eka2l1_bot_menu_simbiam`
Device: iPhone 12 Pro Max, iOS 18.7
Firmware: Nokia 5800 XpressMusic RM-356, SW `V 60.0.003`
Profile: `rm-356__v-60.0.003__5f9fd6d77ac214ec`
ROM mode: SYM.ROM

## Mandatory continuation rules

- User manually triggers GitHub Actions. Do not auto-run builds unless explicitly requested.
- `workflow_dispatch` only.
- Exactly one active `.yml` under `.github/workflows` plus `.gitkeep`.
- Preserve baseline chain: `JAVA-STABLE1` → `N-GAGE-STABILITY1-CUBEB1` → `N-GAGE-COMPAT1-T9AKN1` → `MENUUI1-VIEW19TEST1` → `MENUUI2-XNTHEME-CRASH-TRACE1` → `MENUUI3-WINFOCUS-NULL1` → `MENUUI4-KILLTRACE1` → `MENUUI5-SELFKILLTRACE1` → `MENUUI6-ERRORORIGINTRACE1 FIX1` → `MENUUI7-PRESENTATIONTRACE1 FIX1` → `MENUUI8-XNTHEME-SVCABTRACE1`.
- Do not fake FileServer `0x27`, SVC `0xAB`, SVC `0x800018`, EikAppUi opcode `0x7`, or thread-kill behavior.
- Do not weaken MENUUI3 WINFOCUS null guard.
- Menu runtime tests must be clean sessions.
- Always collect same-session `EKA2L1`, `EKA2L1_Persistent`, and `EKA2L1_TakeThis` logs.

## MENUUI4/5 locked conclusion

Menu kills itself after returning `-1`; `thread_kill` is downstream. Postmortem WINFOCUS null/WGID 0/-1003 occurs after death and is not root cause.

MENUUI5 strongest guest return frame: `Menu3.exe +0x5252`. PC/LR path is through euser/User::Exit.

## MENUUI6

Patcher: `apply_menuui6_errororigintrace1_fix1.py`
Patcher blob SHA: `3d28684b6414ae76e2548f79798b7a40acf6b3d8`
Build run `34849589789`, job `103993873459`, artifact `10350122945`, archive digest `301acf536ab8465d417713ed47a7c40c453d9244d21ce6c8b92503cc1f6be9df`.

Key result: Menu `Leave(-1)` contains dense `presentationmanager.dll` frames: `+0xC70/+0xCA2/+0xCDC/+0xCE6/+0x1078/+0x10B2/+0x10BC/+0x1AE`. EikAppUi opcode 7 and later ALF/CDL `-3` are downstream.

## MENUUI7

Patcher: `apply_menuui7_presentationtrace1.py`
FIX1 commit: `8d3d532dfd60ffb76678f35d9a31fee9d05865f7`
Patcher blob SHA: `57ff016b061c597627058246a53945bef8840ea2`
Build run `34871015540`, job `104066622195`, artifact `10360086089`, digest `6bc878e26d387e81c61e46f5fea63aab8baee05b9c04c755ce8780104b379916`.

MENUUI7 showed the decisive sequence: Menu sends `xnthemeserver opcode=7`; xnthemeserver immediately executes unmapped SVC `0xAB`; Menu then `Leave(-1)` with PresentationManager frames. No direct `NEGIPC ... opcode=7 result=-1` was observed, so do not claim opcode 7 itself completed `-1`.

## MENUUI8

Patcher: `apply_menuui8_xntheme_svcabtrace1.py`
Final prep commit: `e60cc870f202c5108fe59ccb6d3def1dc4750221`
Patcher blob SHA: `fa8a511f81d985511943936d37b3732928d7bced`
Successful build run `34916890255`, job `104216363143`, artifact `10376853798`, artifact name `EKA2L1-SYMBIAN-SYSTEMAPPS1-MENUUI8-XNTHEME-SVCABTRACE1-IPA`, size `52,016,949`, ZIP SHA-256 `14caaea16f5ff87a3150898de9a46cf8bc028fb8ed8789356df07b2a501bb69e`.

Device logs: `EKA2L1(20260915-024645).log`, `EKA2L1_Persistent(20260915-024645).log`, `EKA2L1_TakeThis(20260915-024645).log`.

MENUUI8 captured two real `0xAB` calls by `xnthemeserver[10207254]0001`. Important caller resolution: PC `0x8029819C` -> `euser.dll +0x2D54`; LR `0x802A48B7` -> `euser.dll +0xF46E`; r3 `0x82250719` -> `xnthemeserver.exe +0x8440`; stack frame -> `xnthemeserver.exe +0x844C`.

Critical second call: `r0=1`, `r1=0x00401B48`, `r2=0x00701710`, `r3=0x82250719`, immediately after Menu sends xnthemeserver opcode 7, followed within ~1 ms by Menu `Leave(-1)`.

## Semantic identification of SVC 0xAB

Symbian kernel source documents `MessageConstructFromPtr(RMessageK*, TAny*)` ABI as `r0 -> RMessageK`, `r1 -> user-side message to be populated`. `RMessage2::RMessage2(const RMessagePtr2&)` calls `Exec::MessageConstructFromPtr(iHandle, this)`. This exactly matches MENUUI8 register shape.

Therefore RM-356's missing `0xAB` is identified as `MessageConstructFromPtr`, not `message_kill`.

Important enum nuance: logged integer `epocver=10` means EKA2L1 `epocver::epoc95` (S^3); `epocver::epoc10`/EPOC100 is enum value 11. EKA2L1 confusingly names the S^3 SVC table `svc_register_funcs_v10`.

Current S^3/v10-base IPC area is `0xA9 message_ipc_copy`, `0xAA message_client`, missing `0xAB/0xAC`, then `0xAD message_kill`. Do not infer `0xAC`.

Existing EKA2L1 `message_construct` should also explicitly set `msg_to_construct->spare1 = 0` to match Symbian's RMessageU2 construction.

## MENUUI9 prepared semantic fix

Patcher: `apply_menuui9_xntheme_msgconstruct1.py`
Initial patcher commit: `7c17ad546daf5f2799cad642e957c359bedfe1a5`
MENUUI8 workflow deletion: `192dddb194d52c66f4af24abbadb0d4c6795ba61`
MENUUI9 workflow creation: `420c752141302beb0303c56ff77c344135521e6c`
Corrected epoc95 runtime guard commit: `b5b05b39b6c44e0a9c869d97cdab1cac84723588`
Current patcher blob: `764682c4b76d88a70d900d04be0069036984c2d7`

Use `b5b05b39b6c44e0a9c869d97cdab1cac84723588` or a later corrective commit. Do not build `420c752...`.

Active workflow: `.github/workflows/build-ios-symbian-systemapps1-menuui9-xntheme-msgconstruct1-manual.yml`
Display name: `Build EKA2L1 SYMBIAN SYSTEMAPPS1 MENUUI9 XNTHEME MSGCONSTRUCT1 Manual IPA`

MENUUI9 changes only:
1. S^3/v10-base `0xAB -> message_construct`.
2. Preserve `0xAD -> message_kill`.
3. Leave `0xAC` unmapped.
4. Set `msg_to_construct->spare1 = 0`.
5. Add runtime marker `SYMBIAN-SYSTEMAPPS1 MENUUI9 MSGCONSTRUCT:` for epoc95 xnthemeserver.
6. Preserve MENUUI3-8 diagnostics.
7. No fake xntheme response, FileServer change, thread-kill change, or EikAppUi result change.

## Next action

User manually triggers MENUUI9. Assistant must not auto-run.

When user reports build started/completed, inspect latest GitHub Actions run and report exact head SHA, run ID, job ID, artifact ID, size and digest. Expected artifact: `EKA2L1-SYMBIAN-SYSTEMAPPS1-MENUUI9-XNTHEME-MSGCONSTRUCT1-IPA`.

After signing/installing, run a clean Menu3 session and collect the same 3 logs. Validate that `MENUUI9 MSGCONSTRUCT` appears, the missing-SVC `0xAB` no longer appears for that call, and check whether `MENUUI6 LEAVE_NEG1` still follows xnthemeserver opcode 7.

If Menu progresses, missing MessageConstructFromPtr was causal. If MSGCONSTRUCT executes but Menu still leaves `-1`, trace only the next missing/negative operation; do not broaden speculative fixes.

## New-chat instruction

Read this handoff first, then continue from MENUUI9. Keep the entire baseline/diagnostic chain intact and do not auto-run GitHub Actions.