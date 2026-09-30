# NATIVEBOOT2 B69 ALARMIDLIST1

Date: 2026-09-25
Status: BUILD-VALIDATED; DEVICE TEST REQUIRED

## Selection evidence

B68 DEVICE1 proves the final profilesettingsmonitor rendezvous, notify wakeup,
request semaphore and scheduler path all work. StarterServer resumes guest code
normally after the final RM-356 RID6 WaitForStart.

The first concrete unimplemented service request immediately before the durable
post-RID6 wait is:

Alarm server opcode 0x0C

Current EKA2L1 upstream identifies opcode 12 / 0x0C as
EASShdOpCodeGetAlarmIdList.

Upstream commit:

127823a47b76c7edd50ef8e0b52ddb9b71a18782
alarm: Answer all three alarm id list requests
2026-08-20

adds Alarm ID-list opcodes 9 and 12 and routes 9/11/12 through the same
serializer. The request writes the serialized alarm-id array size to descriptor
slot 1 and completes KErrNone.

The emulated Alarm queue is empty, so this returns the correctly serialized
empty ID list instead of leaving the synchronous request unanswered.

## B69 implementation

B69 is a narrow functional backport of upstream 127823a plus a diagnostic
acceptance marker.

Alarm enum:
- 9 = alarm_get_alarm_id_list_for_category
- 11 = alarm_get_alarm_id_list_by_state
- 12 = alarm_get_alarm_id_list

All three call stream_alarm_id_list().

The handler:
- serializes alarm_ids into transfer_buf;
- writes transfer_buf size to descriptor argument 1;
- completes epoc::error_none.

New marker:

[NBOOT2][ALARM_ID_LIST]

Fields include:
- opcode
- alarm_count
- transfer_bytes
- request_status
- client process/thread
- completion=KErrNone
- behavior=UPSTREAM_BACKPORT_127823A

## Scope

B69 does NOT:
- force KPSGlobalSystemState 102;
- modify any P&S state;
- modify Starter process/rendezvous semantics;
- modify request semaphore/scheduler behavior;
- modify SAServer self-test response;
- modify graphics;
- modify teardown.

B61/B64/B65/B68 remain preserved.

## Canonical GREEN

Workflow:
Build EKA2L1 NATIVEBOOT2 CURRENT FAST

- run ID: 36094691714
- run number: 209
- job ID: 107944359982
- build HEAD: 7902d36459ddc3d6aea09e11ecd120f8ded27e11
- B28 bootstrap cache restored
- FASTBUILD manifest VALID
- B69 apply PASS
- B69 contract PASS
- full regression chain PASS
- iOS compile/link PASS
- binary invariants PASS
- package/upload PASS
- compile requests: 150
- cache hits: 148
- cache misses: 2
- cache hit rate: 98.67%
- compilation failures: 0
- NOJAVA / MANIC3 preserved

Unsigned IPA SHA-256:

dede20f7b4392d236c0fc71d0b57ec5150de791bf6beca896baf2b073e18ac58

IPA artifact:
- ID: 10846748557
- ZIP digest:
  sha256:ccd3147949d323a09fa002050f3fec3cefeba9812d4473e315c05923810e3246
- expires: 2026-10-09

Audit artifact:
- ID: 10846684036
- ZIP digest:
  sha256:6d3dedbc4f0cb1f32028e306102db5647436d5cbb2d7814270e0454ae7c6c69e
- expires: 2026-10-09

## Device test

Install B69 over B68.

Boot RM-356 normally.

Primary acceptance:
1. [NBOOT2][ALARM_ID_LIST] must show opcode=0xC and completion=KErrNone.
2. The old Alarm-server "Unimplemented opcode ... 0xC" must disappear.
3. StarterServer should move past the former immediate WaitForAnyRequest
   boundary.
4. Check whether 0x101F8766:0x41 advances beyond 101.
5. If not, identify the first new request/wait boundary after successful opcode
   0xC completion.

Because this is a functional compatibility fix rather than a pure diagnostic,
a visible boot change is possible. Record/send video only if the visible
behavior differs from B68.

Send:
- EKA2L1.log
- EKA2L1_Persistent.log
- EKA2L1_TakeThis.log
