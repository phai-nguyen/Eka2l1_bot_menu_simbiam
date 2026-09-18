# EKA2L1 iOS Nokia 5800 project handoff

Handoff date: 2026-09-18 19:23 UTC+7

Repository: phai-nguyen/Eka2l1_bot_menu_simbiam

Current branch: main

Current main HEAD at handoff: 962c3e531a60d6ba1f098e9527ca35fbc78eafcd

Current functional baseline: MENUUI23 APPTYPE1 + MENUUI22 SCHEDRUN1 + NOJAVA FULL1 + MANIC3 MODALFIX1

Primary guest under test: Nokia 5800 XpressMusic RM-356 V 60.0.003

## 1. Immediate project state

The user installed the current MENUUI23 APPTYPE1 IPA on device.

Latest device result: Messaging opens successfully.

The user intentionally did not test Messaging deeply and has not tested the other Nokia 5800 system apps yet.

This is the exact continuation point for the next chat.

Do not restart from generic EKA2L1 upstream assumptions. Preserve the current baseline and analyze the latest device logs before adding another fix.

## 2. Library device evidence saved for the next chat

The four latest logs were copied into this persistent Library folder:

/EKA2L1_bot_menu_simbiam/CURRENT/MENUUI23-APPTYPE1-MESSAGING-PASS-HANDOFF-2026-09-18/DEVICE-EVIDENCE-LATEST

Files:

- EKA2L1_Persistent(20260918-103855).log
- EKA2L1(20260918-103859).log
- EKA2L1_TakeThis(20260918-103910).log
- EKA2L1_Persistent-prev(9).log

These are authoritative evidence for the state “MENUUI23 APPTYPE1, Messaging opens”.

## 3. Meaning of MENUUI22 in this project

The user clarified that the line where Java/J2ME was removed is still conceptually MENUUI22.

MANIC1, MANIC2, MANIC3 and SCHEDRUN1 are incremental work on the same MENUUI22 lineage, not separate product branches.

MENUUI23 APPTYPE1 is the newest targeted service fix built on that same baseline.

There is no Git branch literally named menuui22. The development line is on main.

## 4. Repository and upstream

User repo:

https://github.com/phai-nguyen/Eka2l1_bot_menu_simbiam

Main source ancestry:

MuhannadYT/EKA2L1_IOS

Target:

- iOS arm64
- current Symbian guest test: Nokia 5800 XpressMusic RM-356
- firmware: V 60.0.003

## 5. Historical MENUUI22 authority

Historical workflow:

.github/workflows/build-ios-symbian-systemapps1-menuui22-waitowner1.yml

Historical authoritative run:

- run 35237612973
- URL: https://github.com/phai-nguyen/Eka2l1_bot_menu_simbiam/actions/runs/35237612973
- authority head before NOJAVA: bbe898f1921ce1929378bfc89af033a713ecaaa9

Important diagnostic markers that must remain until the Nokia 5800 menu/system-app path is stable:

- SYMBIAN-SYSTEMAPPS1 MENUUI22 SYNC_SEND:
- SYMBIAN-SYSTEMAPPS1 MENUUI22 SYNC_COMPLETE:
- SYMBIAN-SYSTEMAPPS1 MENUUI22 ALF_WAKE_CONTEXT:
- SYMBIAN-SYSTEMAPPS1 MENUUI22 WAIT_OWNER:
- SYMBIAN-SYSTEMAPPS1 MENUUI22 WAIT_FRAME:
- SYMBIAN-SYSTEMAPPS1 MENUUI21 SCHED_SCAN:
- SYMBIAN-SYSTEMAPPS1 MENUUI21 VTABLE:

## 6. NOJAVA FULL1 baseline

Main patcher:

apply_nojava_full1_manic1.py

Successful first full native-only run:

- run 35303058650
- head 0955fbcaed4679d1d108fd4af108bbee7fe86dff
- cache eka2l1-menuui22-nojava-full1-manic1-macos15-v1
- IPA EKA2L1-SYMBIAN-SYSTEMAPPS1-MENUUI22-NOJAVA-FULL1-MANIC1-unsigned.ipa

What this baseline established:

- removed host src/emu/j2me
- removed libj2me.a from the iOS build/link
- removed iOS Java/JAR runtime and UI path
- removed phoneME runtime
- moved native shared launcher/library UI out of app/j2me
- preserved native Symbian/N-Gage controls
- preserved native defaultbank.sf2
- migrated Manic controls to native Objective-C under app/controls/manic

Do not re-add host Java/J2ME/phoneME as a shortcut for Symbian AppArc compatibility.

Symbian ROM ABI/export metadata that contains Java-related names is guest compatibility metadata and must not be blindly deleted.

## 7. MANIC2

Successful run:

- run 35316412231
- URL: https://github.com/phai-nguyen/Eka2l1_bot_menu_simbiam/actions/runs/35316412231
- cache eka2l1-menuui22-nojava-full1-manic2-macos15-v1
- IPA SHA-256 e433eeb0ecf82245d125043840b0043107b50384894c20a07afadcc21bd50ff5

MANIC2 exposed layout 7 as Manic Skin for native Symbian/N-Gage controls and connected the portrait/landscape editor to Manic geometry.

GameControlsView remains the authoritative touch/hitbox/scancode engine.

EKAManicControlsArtworkView is visual-only.

## 8. MANIC3 MODALFIX1

Patcher:

apply_manic_modalfix1.py

Workflow:

.github/workflows/build-ios-symbian-systemapps1-menuui22-nojava-full1-manic3-modalfix1.yml

Successful run:

- run 35318183627
- URL: https://github.com/phai-nguyen/Eka2l1_bot_menu_simbiam/actions/runs/35318183627
- cache eka2l1-menuui22-nojava-full1-manic3-modalfix1-macos15-v1

Root cause fixed:

GameMenuView is a custom sibling UIView. updateChrome raised controls and Manic artwork above it, so all control skins could draw over the in-game settings/key-layout menu.

Fix:

keep activeMenu topmost immediately after presentation and after updateChrome z-order changes.

Device result confirmed by user:

- Manic Skin no longer overlaps the settings/key-layout menu
- default layouts also no longer overlap the settings/key-layout menu

Treat this as a proven device baseline.

## 9. Future .manicskin import work is postponed

The user explicitly decided to postpone import/select of .manicskin files per game.

Do not continue .manicskin import work in the next chat unless the user explicitly returns to it.

## 10. MENUUI22 SCHEDRUN1

Patcher:

apply_menuui22_schedrun1.py

Workflow:

.github/workflows/build-ios-symbian-systemapps1-menuui22-schedrun1-nojava-manic3.yml

Successful run:

- run 35325489625
- URL: https://github.com/phai-nguyen/Eka2l1_bot_menu_simbiam/actions/runs/35325489625
- IPA EKA2L1-SYMBIAN-SYSTEMAPPS1-MENUUI22-SCHEDRUN1-NOJAVA-MANIC3-unsigned.ipa
- IPA SHA-256 d2b7540d376c935e080c97d32d37d17962232a100ce295cc7d38dae32984387b
- cache eka2l1-menuui22-schedrun1-nojava-manic3-macos15-v1

New diagnostic markers:

- SCHEDRUN_ARM:
- SCHEDRUN_SVC:
- SCHEDRUN_FRAME:
- SCHEDRUN_DONE:

SCHEDRUN1 is diagnostic-only.

It does not force RunL, alter guest request status, alter request semaphore state, mutate the active scheduler queue, modify guest registers, or change IPC behavior.

Conclusion from SCHEDRUN1 device logs:

The earlier theory that CActiveScheduler was failing to dispatch a completed ALF active object was not the root cause.

The ready active object remained valid, active and ready, but Menu was being held by another synchronous IPC.

Do not patch the scheduler unless new evidence independently proves a scheduler bug.

## 11. Root cause found after SCHEDRUN1

The blocking request was:

- server !AppListServer
- opcode 73 decimal, 0x49 hex
- synchronous request
- native app UID, initially observed for UID 0x2001FE2F and later many other apps

EKA2L1 logged:

Unimplemented applist opcode 0x49

Because this request was synchronous and not completed, Menu entered WaitForAnyRequest and the downstream scheduler state looked suspicious.

Source comparison with Symbian AppArc established:

opcode 73 = EAppListServGetAppType = applist_request_get_app_type.

For a native Symbian app, GetAppType returns KNullUid.

## 12. MENUUI23 APPTYPE1 — current preferred baseline

Patcher:

apply_menuui23_apptype1.py

Workflow:

.github/workflows/build-ios-symbian-systemapps1-menuui23-apptype1-nojava-manic3.yml

Current workflow is manual-only.

Successful run:

- run 35331120515
- URL: https://github.com/phai-nguyen/Eka2l1_bot_menu_simbiam/actions/runs/35331120515
- run head SHA 83210abf26bf7abd3775c515e376d2c313ee9795
- current main after trigger cleanup 962c3e531a60d6ba1f098e9527ca35fbc78eafcd
- IPA artifact ID 10541365699
- audit artifact ID 10541635070
- IPA EKA2L1-SYMBIAN-SYSTEMAPPS1-MENUUI23-APPTYPE1-NOJAVA-MANIC3-unsigned.ipa
- IPA size about 20 MB
- IPA SHA-256 d81a1dce07af89bd5358e9de68adefbc613fb8b2122f38791cd0e5badd1c261d
- cache eka2l1-menuui23-apptype1-nojava-manic3-macos15-v1

Implementation behavior:

- known registration => type UID KNullUid and KErrNone
- unknown app UID => KErrNotFound
- bad output descriptor => KErrBadDescriptor
- Java/J2ME application-type mappings are intentionally not added

This preserves the NOJAVA design.

## 13. Latest device evidence proves APPTYPE1 works

In EKA2L1_TakeThis(20260918-103910).log around line 36284:

Menu sends !AppListServer opcode 73 for native UIDs.

Examples in the current device log:

- app UID 0x100058CA => MENUUI23 APPTYPE result=native type_uid=0
- app UID 0x100058C5 => MENUUI23 APPTYPE result=native type_uid=0
- app UID 0x10005234 => MENUUI23 APPTYPE result=native type_uid=0

UID 0x100058C5 is Messaging.

This directly proves that the previous unimplemented opcode 0x49 blocker is removed on the real device path.

The old failure “Unimplemented applist opcode 0x49” is no longer the point where Menu stalls.

## 14. Messaging now genuinely launches

Latest TakeThis log shows:

- Mce thread activity
- Mce resources load
- Z:\Resource\Apps\Mce.r01 opens
- thread name changes from Mce to Messaging
- Rendezvous to: Messaging occurs
- Mce.exe frames appear in leave diagnostics
- Messaging resources under z:\Private\100058C5 are read

This is a real process launch, not merely menu selection.

User observation confirms Messaging becomes visible/open.

## 15. Do not overreact to every leave in Messaging

After Messaging launches, the log still contains trapped leaves.

Examples:

- Create session to unexist server: NcnServer
- Leave -1 paths involving NCNNOTIFICATION.dll and Mce.exe
- Leave -5 around Fontbitmapserver
- later Leave -5 around FeatMgrServer / MsvServer

Because Messaging actually opens, these are not currently proven fatal.

Classify them by visible behavior before patching.

Do not assume every Leave -1 or -5 is the next bug.

## 16. New AppList candidate seen in latest log: opcode 33 / 0x21

At about 17:37:23.933 in the latest TakeThis log:

- process Menu UID 0x101F4CD2
- server !AppListServer
- opcode 33
- sync=0
- status pointer 0x0081576C
- followed by Unimplemented applist opcode 0x21

In the current applist_request_newarch enum, decimal 33 maps to:

applist_request_set_notify

This is an asynchronous AppList notification registration.

Important distinction:

opcode 73 was synchronous and caused a deadlock/stall.

opcode 33 is asynchronous, so do not implement it blindly just because it is unimplemented.

It is a likely candidate only if testing shows app-list refresh/change-notification problems or an outstanding async status causes a real lifecycle issue.

## 17. Other current unimplemented warnings

The latest log still contains examples such as:

- window group opcode 0x26
- redraw canvas opcode 0x7F
- redraw canvas opcode 0x57
- graphic drawer opcode 0x1
- OOM AKNCAP opcodes 0x3A, 0x40, 0x44 currently stubbed to success

These are lower priority than a proven synchronous IPC blocker or fatal app crash.

Only fix them when correlated with a visible problem.

## 18. Build-cache architecture

Old builds took roughly 25 to 30 minutes because they replayed a large historical chain including Java/J2ME/phoneME and many intermediate patches.

Current incremental builds are roughly 3 minutes for small changes.

Current cache chain:

1. eka2l1-menuui22-nojava-fast1-macos15-bbe898f1921ce192-v1
2. eka2l1-menuui22-nojava-full1-manic1-macos15-v1
3. eka2l1-menuui22-nojava-full1-manic2-macos15-v1
4. eka2l1-menuui22-nojava-full1-manic3-modalfix1-macos15-v1
5. eka2l1-menuui22-schedrun1-nojava-manic3-macos15-v1
6. eka2l1-menuui23-apptype1-nojava-manic3-macos15-v1

For the next targeted fix, restore cache 6 and patch only the required component.

Do not replay the old long historical build unless validating from scratch.

Persistent CMake in the cached tree:

upstream/.tools/cmake-3.31.6-macos-universal/CMake.app/Contents/bin/cmake

Build only target eka2l1 with parallel 4 unless a dependency change requires more.

## 19. NOJAVA invariants that must remain

- no upstream/src/emu/j2me
- no iOS app/j2me runtime/UI tree
- no libj2me.a
- no phoneME runtime
- no JAR import/runtime UI
- no compiled host j2me:: / get_j2me / j2me_applist plumbing
- preserve native defaultbank.sf2
- preserve guest Symbian ROM ABI/export metadata even when names mention Java

Do not add Java non-native type mappings to AppList just to implement native system-app behavior.

## 20. Native Manic state to preserve

Current native files include:

src/emu/ios/app/controls/manic/EKAManicControlsView.h
src/emu/ios/app/controls/manic/EKAManicControlsView.m

Layout 7 is Manic Skin.

GameControlsView is authoritative for native touch/scancodes.

Manic artwork is visual-only and follows the same normalized control layout geometry.

Portrait/landscape layout editor works with Manic.

The z-order fix keeps GameMenuView above all control artwork while the menu is open.

## 21. Build trigger mechanics

The GitHub connector path used in this project does not provide direct workflow_dispatch.

Established one-shot trigger method:

1. fetch current workflow and SHA
2. temporarily add push trigger restricted to a unique marker file
3. commit workflow
4. create marker file
5. confirm run ID/head
6. restore workflow to manual-only immediately
7. delete marker file

Never leave temporary push triggers active.

Do not rerun an old run after source changes because a rerun uses the old head.

## 22. Recommended next device test sequence

Do not add another patch before testing the current build.

Suggested order:

1. Messaging again
   - main screen responsive
   - Inbox
   - Drafts
   - Sent
   - Outbox
   - open Text message composer if available
   - back and exit
2. Contacts
3. Calendar
4. Gallery / Photos
5. Music player
6. Settings / Themes
7. Browser later because it pulls in more networking/web services

For every failure capture:

- app name
- exact visible behavior: opens, white screen, freeze, closes, partial
- approximate timestamp
- screenshot/video if visual
- EKA2L1 log
- Persistent log
- TakeThis log
- Persistent-prev log

Then correlate the first visible failure with:

1. synchronous IPC with no completion
2. process/thread panic or untrapped fatal leave
3. missing required server
4. async notification lifecycle bug
5. rendering-only warning

Priority should be in that order.

## 23. Current GitHub files to inspect first

Current patch/workflow:

- apply_menuui23_apptype1.py
- .github/workflows/build-ios-symbian-systemapps1-menuui23-apptype1-nojava-manic3.yml

Inherited diagnostics:

- apply_menuui22_schedrun1.py
- .github/workflows/build-ios-symbian-systemapps1-menuui22-schedrun1-nojava-manic3.yml

Stable Manic/menu fixes:

- apply_manic_modalfix1.py
- .github/workflows/build-ios-symbian-systemapps1-menuui22-nojava-full1-manic3-modalfix1.yml
- apply_manic_layout2.py
- apply_nojava_full1_manic1.py

Create a new narrowly scoped patcher/workflow for the next confirmed issue and restore the current MENUUI23 APPTYPE1 cache.

## 24. Current stopping point

Confirmed:

- RM-356 firmware/profile works
- MENUUI22 diagnostics retained
- host Java/J2ME/phoneME removed
- native Manic Skin integrated
- controls no longer overlap in-game settings
- incremental cached build path works
- AppList GetAppType opcode 73 implemented
- real-device logs confirm opcode 73 returns native KNullUid
- Messaging UID 0x100058C5 progresses past GetAppType
- Messaging process launches and reaches rendezvous
- user sees Messaging open

Not yet deeply tested:

- Messaging internal functionality
- Contacts
- Calendar
- Gallery/Photos
- Music player
- Settings/Themes
- Browser
- other Nokia 5800 system apps

Next action:

Read the latest Library logs first, then continue controlled device testing. Patch only the next issue that is correlated with an actual visible failure.

## 25. Exact prompt for a new conversation

Use this in the next chat:

Tiếp tục dự án EKA2L1. Đọc handoff HANDOFFS/MENUUI23-APPTYPE1-MESSAGING-PASS-HANDOFF-2026-09-18/EKA2L1_PROJECT_HANDOFF_2026-09-18_MENUUI23_APPTYPE1_TO_NEXT.md trong repo phai-nguyen/Eka2l1_bot_menu_simbiam trước. Sau đó đọc các log trong Library tại /EKA2L1_bot_menu_simbiam/CURRENT/MENUUI23-APPTYPE1-MESSAGING-PASS-HANDOFF-2026-09-18/DEVICE-EVIDENCE-LATEST. Baseline hiện tại là MENUUI23 APPTYPE1 + MENUUI22 SCHEDRUN1 + NOJAVA FULL1 + MANIC3 MODALFIX1. Messaging đã mở được trên Nokia 5800 RM-356 nhưng chưa test sâu; các app khác chưa test. Không quay lại Java/J2ME và không sửa scheduler nếu chưa có bằng chứng mới.
