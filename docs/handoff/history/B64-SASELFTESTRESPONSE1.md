# NATIVEBOOT2 B64 SASELFTESTRESPONSE1

Date: 2026-09-25
Status: BUILD-VALIDATED; DEVICE TEST REQUIRED

## Selection

B63 DEVICE1 proves exact SAServer opcode 0x67 is
StartupAdaptation::EExecuteSelftests (103), sent by SYSSTART / StarterServer.

Observed RM-356 ABI:

- types [4,6,4,4]
- sizes [12,0,12,0]
- max [12,0,12,16]
- slot 2 response template [0x00010004,0x01000067,txn]
- slot 3 writable response payload buffer

B63 explicitly returned KErrNotSupported (-5), after which Starter published:

101 StartingCriticalApps -> 117 FatalStartupError

Public Symbian API defines EExecuteSelftests response as TResponsePckg (TInt).

## B64 behavior

B64 implements the same RM-356 response transport already validated for
EGlobalStateChange:

1. Copy/echo the exact 12-byte response template from slot 2.
2. Write TInt(KErrNone) to slot 3.
3. Complete the RMessage with KErrNone.

New marker:

[NBOOT2][SA_SELFTEST_RESPONSE]

Fields include:

- echoed response header
- template-copied flag
- slot2 size/max
- slot3 max
- header write result
- payload write result
- TInt payload value
- completion

B64 does NOT:

- write KPSGlobalSystemState directly
- force state 102/103/104
- force KPSStartupAppState=2
- alter graphics, focus, compositor or teardown behavior

B61 wipeout guard, B62 Starter state trace and B63 ABI marker remain active.

## Canonical GREEN

The first B64 run 183 stopped only because the test contract checked for a
nonexistent literal log phrase. B64 apply itself passed. The assertion was
corrected without changing runtime code.

Canonical run:

- run ID: 36064120244
- run number: 184
- job: 107849736732
- HEAD: 8e5bf9c24b6f3583e34e76ed4d03c8363abbb711
- B64 apply PASS
- B64 contract PASS
- regressions PASS
- iOS compile/link PASS
- binary invariants PASS
- package/upload PASS
- compile requests/hits/misses: 149/148/1
- actual compilations: 1
- compilation failures: 0
- NOJAVA / MANIC3 preserved

Unsigned IPA SHA-256:

400849d5f2109f4857881b98979d3d4a5740f97480f9d91079027685de450372

IPA artifact:

- ID: 10835737543
- ZIP digest: sha256:199073871a0163b4f977a34b444c38f0c073a5b05be585236cdfc50398265123
- expires: 2026-10-08

Audit artifact:

- ID: 10835867300
- ZIP digest: sha256:a5615aa69cd83453ea08475b53c942088abece028335543663dd05392277263d
- expires: 2026-10-08

## Device acceptance

Recommended: clean install B64 and clear old logs before one boot run.

Run normal SIM-present RM-356 boot.

Primary evidence:

1. [SA_SELFTEST_RESPONSE]
   - template=1
   - header_ok=1
   - payload_ok=1
   - payload=0

2. KPSGlobalSystemState:
   expected next transition is 101 -> 102 SelfTestOK.

3. There must be no 101 -> 117 FatalStartupError caused by self-test failure.

4. If 102 is reached, identify the first new SAServer/Starter dependency after
   SelfTestOK before implementing anything else.

5. Preserve B61 clean-exit behavior.
