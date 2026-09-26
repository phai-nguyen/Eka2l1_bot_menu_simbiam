# B31 DEVICE1 — SCHEDREADYMM1

Date: 2026-09-22
Status: DEVICE-VALIDATED FOR THE B30 HOST SCHEDULER CRASH
Device: iPhone 12 Pro Max, iOS 18.7
Firmware: Nokia 5800 RM-356

Immutable branch:
`nativeboot2-b31-schedreadymm1`

Build-tested/device-tested code commit:
`6ccdd5c1b9101124981315322af5002dac057edc`

## Device result

The B31 device run confirms the narrow scheduler hypothesis from B30.

B30 loader behavior remains healthy:

`09:35:07.081 [NBOOT2][LDR_ROOT_RESOLVED] request=\sys\bin\EiksrvUi.dll candidate=Z:\sys\bin\EiksrvUi.dll success=1`

The same late AknCapServer teardown boundary seen in B30 still occurs:

`09:35:36.830 Thread akncapserver forcefully killed with category: Domino and exit code: -33`

Immediately afterward the already-observed missing executive appears:

`09:35:36.836 V5 SVCMISS: svc=0xE3 ...`

B31 then catches the stale ready entry that caused the B30 host crash:

`09:35:36.932 [NBOOT2][SCHED_STALE_READY_DROP] thread=akncapserver owner_present=true mem_model_present=false`

This marker appears exactly once.

The emulator does not terminate in `thread_scheduler::switch_context()`. Instead the native-phone session continues for more than 100 seconds after the B31 marker and later exits through the existing B26 clean bridge path:

`09:37:23.324 [NBOOT2][BRIDGE_EXIT] restoring normal EKA2L1 mode`
`09:37:23.349 [NBOOT2][BRIDGE_EXIT_PHASE] phase=shutdown_done`
`09:37:23.349 [NBOOT2][BRIDGE_EXIT_PHASE] phase=normal_restart_begin`

Conclusion:
B31 removes the B30 native iOS `EXC_BAD_ACCESS` scheduler failure at its intended causal boundary.

## New guest-side failure boundary

Once the host crash is removed, the strongest repeatable guest-side symptom is `EikAppUiServerThread`.

After the single B31 stale-ready marker:
- `eiksrvs` is spawned 16 times;
- there are 16 access-violation events in `EikAppUiServerThread`;
- all 16 corresponding threads terminate with `KERN-EXEC 3`.

First fault family (11 occurrences):
- operation: write;
- address: `0x10`;
- PC: `0x802A01C4`;
- module: `euser.dll`;
- runtime module base observed in the same log: `0x80295448`;
- module offset: `+0xAD7C`.

Second fault family (5 occurrences):
- operation: read;
- address: `0x4`;
- PC: `0x806EA236`;
- module: `cone.dll`;
- runtime module base observed in the same log: `0x806E8E68`;
- module offset: `+0x13CE`.

The final five CONE faults occur immediately after the splashscreen process exits normally.

This is now the first high-signal boundary for further investigation. The host scheduler is no longer the blocker.

## Executive gaps still observed

After the B31 marker:
- SVCMISS `0x2D` occurs repeatedly;
- SVCMISS `0xE3` was observed immediately before the B31 marker.

These remain observations, not yet proven causes of the repeated EikAppUiServerThread access violations.

Upstream EKA2L1 commit
`437b29006bd8a0186f4070c9445f43e98e5c7435`
contains a real `Exec::GetModuleNameFromAddress` implementation, but executive numbers differ across Symbian version tables. The exact project EPOC 9.4 table must be reconciled with the device's `V5 SVCMISS 0xE3` evidence before any executive backport.

Do not batch-patch 0xE3 or 0x2D merely because they are present.

## Next direction

Preferred next milestone:
`B32 EIKSRVFAULTDIAG1`

Diagnostics only.

Goal:
localize the repeated `EikAppUiServerThread` KERN-EXEC 3 to the immediately preceding guest operation/executive/IPC context, without altering guest behavior.

The first B32 trace should answer whether the missing 0xE3/0x2D executives are actually issued by the failing eiksrvs process/thread or are incidental activity from other startup processes.

Only after that evidence should a functional B32/B33 compatibility fix be selected.

## Preserved invariants

Keep all B20-B31 behavior, especially:
- firmware SYSSTART startup ownership;
- native fbserv;
- B25 FBS shared heap;
- B26 safe Exit Emulator choreography;
- B28 LibraryType;
- B29 CenRep transaction compatibility;
- B30 rooted-no-drive library resolution;
- B31 stale-ready scheduler guard;
- NOJAVA;
- MANIC3.

Do not import the rest of upstream 437b290 as a batch.
