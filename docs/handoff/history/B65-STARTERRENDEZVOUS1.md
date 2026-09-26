# NATIVEBOOT2 B65 STARTERRENDEZVOUS1

Date: 2026-09-25
Status: BUILD-VALIDATED; DEVICE TEST REQUIRED
Recommended install mode: INSTALL OVER B64 for direct A/B; clean install also valid.

## Selection

B64 DEVICE1 proves the RM-356 EExecuteSelftests response is now accepted:

- header template copied successfully;
- slot-2 header write succeeds;
- slot-3 TInt(KErrNone) payload write succeeds;
- RMessage completes KErrNone;
- the B63 101 -> 117 FatalStartupError path disappears.

However KPSGlobalSystemState still remains at 101 StartingCriticalApps and never
advances to 102 SelfTestOK.

The generic Symbian critical-app command list architecture uses deferred
wait-for-signal startup entries plus a multiple-wait barrier in this state.
B64's existing process trace shows only generic "Rendezvous to: StarterServer"
messages and does not identify which target process each wait belongs to.

B65 therefore instruments the process rendezvous path without changing process
or startup semantics.

## B65 marker

[NBOOT2][STARTER_RENDEZVOUS]

Scope is restricted to rendezvous requests owned by SYSSTART UID3 0x100059C9.

Logged phases:

- arm_dead_target
- arm
- handled_immediate
- queued
- cancel_miss
- cancel
- complete

Fields include:

- target process name
- target UID3
- target thread count
- queue count
- requester process/thread
- rendezvous completion reason

Existing rendezvous completion, cancellation and logon behavior remain
unchanged.

B65 does NOT:

- force state 102;
- touch KPSGlobalSystemState;
- change child-process success/failure;
- modify SAServer self-test response;
- alter graphics or teardown behavior.

## Canonical GREEN

- run ID: 36069095793
- run number: 185
- job: 107865597224
- build HEAD: b9ef9ad46cd9092586b0d4254b81aa454f0228d6
- B65 apply PASS
- B65 contract PASS
- regressions PASS
- iOS compile/link PASS
- binary invariants PASS
- package/upload PASS
- compile requests/hits/misses: 150/149/1
- actual compilations: 1
- compilation failures: 0
- NOJAVA / MANIC3 preserved

Unsigned IPA SHA-256:

9dc349c9674a0059fa9566a8eb3c9a61910b56e609151e2536fce7503d7a990f

IPA artifact:

- ID: 10837880606
- ZIP digest: sha256:fb7469aaeaf3b6b88fe5b9df4864206aa170dc218bf7db5aaca0814676cac3b1
- expires: 2026-10-08

Audit artifact:

- ID: 10837930432
- ZIP digest: sha256:5c51a73893bc560359efaf65c477939c18117f6bb9e20a4da88ab4ac93bbfdde
- expires: 2026-10-08

## Device test

Prefer installing B65 over the confirmed B64 clean installation so the only
behavioral difference is rendezvous instrumentation.

Run the normal SIM-present RM-356 path through NOKIA -> blank-white Startup.
Leave it running at least 2-3 minutes, then exit normally.

Primary questions:

1. Which processes does StarterServer arm with DeferredWaitForSignal?
2. Which of those processes actually completes rendezvous and with what reason?
3. Which request remains queued or gets cancelled?
4. Does the unresolved wait correspond to a critical app such as cfserver,
   sysap, profilesettingsmonitor, or an RM-356-specific merged command-list
   component?
5. Does global state remain 101 throughout?

Do not patch a child process until B65 identifies the exact pending target.
