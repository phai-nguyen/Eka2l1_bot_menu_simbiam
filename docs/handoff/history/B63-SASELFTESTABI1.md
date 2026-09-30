# NATIVEBOOT2 B63 SASELFTESTABI1

Date: 2026-09-24
Status: BUILD-VALIDATED; DEVICE TEST REQUIRED
Recommended install mode: CLEAN INSTALL is acceptable; otherwise install over B62.

## Selection

B62 clean-install device evidence proves:

KPSGlobalSystemState 0x101F8766:0x41
  0 -> 100 StartingUiServices
  100 -> 101 StartingCriticalApps
  then no further SET.

Immediately after StarterServer publishes 101, SAServer receives the first
unimplemented request:

  opcode 0x67

Public Symbian Startup Adaptation API identifies command 103 / 0x67 as:

  StartupAdaptation::EExecuteSelftests

The same API specifies its response as TResponsePckg, i.e. a TInt success/error
payload. This command is semantically consistent with the next global-state
checkpoint SelfTestOK=102.

B63 does not assume the RM-356 transport ABI. It observes it first.

## B63 behavior

Registers exactly:

  SAServer opcode 0x67

New marker:

  [NBOOT2][SA_SELFTEST_ABI]

Captured fields:

- raw function / public command identity
- caller process
- caller thread
- session id
- IPC flag
- four raw arguments
- four argument types
- current/max descriptor lengths
- descriptor presence
- first 32 bytes of each descriptor

Guest-visible behavior is deliberately unchanged from the prior generic
unimplemented-opcode path:

  KErrNotSupported

B63 does NOT:

- return KErrNone
- write or resize descriptors
- force global state 102/103/104
- force Startup private state 2
- change graphics/focus/compositor behavior

B61 wipeout guard and B62 Starter global-state diagnostics remain active.

## Public-source identity

Symbian startupadaptationcommands.h:

- EExecuteSelftests = 103
- response = TResponsePckg / TInt
- self-tests are required before software using specific hardware is launched;
  Starter expects the result when this command is issued.

StartupAdaptationStub.cpp confirms EExecuteSelftests returns TResponsePckg.

## Canonical GREEN

- run ID: 36022003611
- run number: 182
- job: 107708966701
- HEAD: 68cf65b983850f614f046158db278ebd6feb3eac
- B63 apply PASS
- B63 contract PASS
- regressions PASS
- iOS compile/link PASS
- binary invariants PASS
- package/upload PASS
- compile requests/hits/misses: 149/148/1
- actual compilations: 1
- compilation failures: 0
- NOJAVA / MANIC3 preserved

Unsigned IPA SHA-256:

89528414195d1b93d1aabcb2b342c8a262ce93c547a08ca45fc200415339f59b

IPA artifact:

- ID: 10816504737
- ZIP digest: sha256:4c70357071df3c30f6215cf2d8eba4933a9d96075b4fca77e85d7a0999026c43
- expires: 2026-10-08

Audit artifact:

- ID: 10817586261
- ZIP digest: sha256:9eeafe0c9f3b62e9ef3842b16995cdedb42a64a4c70f302f6baa76f05fdc81a7
- expires: 2026-10-08

## Device test

Run the normal SIM-present RM-356 boot to the white Startup surface and allow
the run to continue for at least 2-3 minutes.

Then exit normally.

Primary B63 questions:

1. Which process/thread sends SAServer 0x67?
2. What are its descriptor types/sizes/max lengths?
3. Does the request use the same response-envelope ABI as the already supported
   0x64/0x66/0x6B commands?
4. Does global state remain at 101 after KErrNotSupported?

If the RM-356 request ABI matches the standard TResponsePckg path, the next
behavioral build can implement EExecuteSelftests success narrowly and test
whether Starter advances 101 -> 102.
