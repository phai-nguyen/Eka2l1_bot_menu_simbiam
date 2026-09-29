# NATIVEBOOT2 B68 STARTERWAKE1

Date: 2026-09-25
Status: BUILD-VALIDATED; DEVICE TEST REQUIRED
Recommended install mode: INSTALL OVER B67 OR B66

## Selection

RM-356 SYM.RPKG analysis resolves the normal-mode StartingCriticalApps list
(RID6) and B66 DEVICE1 proves the final process item,
profilesettingsmonitor.exe, rendezvouses successfully with reason 0.

After that final rendezvous SYSSTART never requests global state 102.

B66 also shows a recurring KErrCancel completion on request status 0x00700364
for SYSSTART / StarterServer after successful WaitForStart rendezvous. The same
status/cancel pattern occurs after earlier entries where Starter continues
normally, so KErrCancel itself is not treated as causal.

B68 therefore traces the request/wakeup boundary without changing it.

## B68 markers

[NBOOT2][STARTER_WAKE]
- emitted around the B65 process-rendezvous notify completion
- request-status address
- request count before/after
- StarterServer thread state before/after

[NBOOT2][STARTER_NOTIFY_WAKE]
- generic notify_info completion for SYSSTART only
- completion result and request-status address
- request count/thread state before and after signal_request()

[NBOOT2][STARTER_WAIT_ANY]
- SYSSTART WaitForAnyRequest before and after invoking the request-semaphore wait
- request count and thread state

[NBOOT2][STARTER_SCHED]
- scheduler switches to a SYSSTART-owned thread
- previous/next process/thread
- target request count and state

[NBOOT2][STARTER_SVC]
- every SVC entered by SYSSTART
- proves guest code resumed and identifies the first kernel operation after a
  wakeup

The implementation is scoped by SYSSTART UID3 0x100059C9.

## Deliberately omitted timer-specific patch

A timer-source probe was considered because EKA2L1 timer cancellation completes
its request with KErrCancel. The B28 FASTBUILD bootstrap carries an older timer
implementation than current upstream, however, so B68 deliberately remains
independent of timer implementation details.

The core diagnostic is sufficient to determine whether the final RID6
completion:

1. signals StarterServer correctly;
2. is consumed by WaitForAnyRequest;
3. causes StarterServer to be scheduled;
4. resumes guest execution;
5. reaches another SVC/wait or stalls before that point.

No timer behavior is modified.

## Behavior contract

B68 does NOT:

- force KPSGlobalSystemState 102;
- alter any P&S value;
- alter any completion result;
- alter signal_request count;
- alter scheduler selection;
- alter process/rendezvous behavior;
- alter SAServer self-test behavior;
- alter graphics or teardown.

B31/B33/B61/B62/B64/B65/B66/B67 remain in the chain.

## Canonical GREEN

- run ID: 36081287241
- run number: 206
- job: 107903597467
- build HEAD: 4f4f03648498c2511e35d941fbc2d003adbfbe99
- FASTBUILD1 manifest VALID
- B68 apply PASS
- B68 contract PASS
- full regression chain PASS
- iOS compile/link PASS
- binary invariants PASS
- IPA package/upload PASS
- compile requests: 150
- cache hits: 145
- cache misses: 5
- cache hit rate: 96.67%
- compilation failures: 0
- NOJAVA / MANIC3 preserved

Unsigned IPA SHA-256:

45809eea0e6bce81b2822ebeaca2021330791b378c9b65e7930454f1f5ab0e57

IPA artifact:
- ID: 10841699589
- ZIP digest: sha256:6353b3a9ccf0950973e69c3b1334924e7c81aa4e2e53c9c51e62af705bd07b18
- expires: 2026-10-09

Audit artifact:
- ID: 10841769277
- ZIP digest: sha256:b379bf5e99abcac1b35c7bd1058a19947c636d2daf40b5de8d18c202c57442f8
- expires: 2026-10-09

## Device test

Install B68 over B67 if B67 is already installed; otherwise install over B66.
All required previous patches are in the B68 build.

Boot RM-356 normally through NOKIA -> blank-white Startup.
Leave the emulator running until the white Startup state is stable, then exit
normally.

Send:
- EKA2L1.log
- EKA2L1_Persistent.log
- EKA2L1_TakeThis.log
- Persistent-prev only if produced and convenient

Video is not required unless visible behavior changes.

## Primary analysis target

Find the final:

[NBOOT2][STARTER_WAKE]
target_process=profilesettingsmonitor

Then correlate the immediately following:

- STARTER_NOTIFY_WAKE
- STARTER_WAIT_ANY
- STARTER_SCHED
- STARTER_SVC
- STARTER_GLOBAL_STATE
- SA_RESPONSE / SA_SELFTEST_RESPONSE

Compare this final cycle against earlier successful rendezvous cycles.

Decision matrix:

- notify count changes but no scheduler switch:
  scheduler/ready/request-semaphore wakeup problem.
- scheduler switches to StarterServer but no following SVC:
  guest continuation stalls before its next kernel operation.
- StarterServer resumes and immediately WaitForAnyRequest again:
  a second async dependency is missing.
- StarterServer resumes and enters an unimplemented/failed SVC:
  that exact SVC becomes the next blocker.
- StarterServer resumes normally and requests state 102:
  inspect the 102 adaptation/IPC path instead.
- final accounting differs from earlier WaitForStart cycles:
  isolate the request accounting difference before any functional fix.

Do not force state 102 until B68 DEVICE1 establishes which branch applies.
