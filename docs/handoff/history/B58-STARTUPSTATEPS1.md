# NATIVEBOOT2 B58 STARTUPSTATEPS1

Date: 2026-09-24
Status: BUILD-VALIDATED; DEVICE TEST REQUIRED
Scope: DIAGNOSTIC READBACK ONLY

## Selection

B57 proves the white screen is a real guest Startup waiting frame, not a
renderer artifact.

Official Nokia/Symbian Startup source shows Startup's synchronization contract:

- KPSUidStartupApp = 0x100058F4
- KPSStartupAppState = 1
- EStartupAppStateWait = 1
- EStartupAppStateStartAnimations = 2
- EStartupAppStateFinished = 3

Startup ConstructL() defines the integer property and sets state 1, then
subscribes to it. A later state 2 starts the animation/next startup phase.

## Baseline classification

Early B58 apply attempts intentionally tested whether the current B28-derived
baseline still contained an older EKA2L1 category/key integer setter bug.

The authoritative apply classification is:

baseline_setter=SET_INT_ALREADY_PRESENT

Therefore the current NATIVEBOOT2 baseline already calls property::set_int()
correctly. B58 does NOT change P&S semantics.

B58 only surrounds the existing set_int call with before/after readback and
logs the Startup state key.

Marker:

[NBOOT2][STARTUP_STATE_PS]

Fields:

- category/key
- before
- requested
- after
- set_result
- path=CATEGORY_KEY_INT
- behavior=PRESERVE_EXISTING_SET_INT

## Canonical GREEN

- run ID: 35969142523
- run number: 168
- job: 107534490446
- HEAD: 9a7a47a37d95c3d4ddecc29e26f5edbcd3c4037e
- FASTBUILD apply/regression PASS
- B58 contract PASS
- iOS compile/link PASS
- binary invariants PASS
- package/upload PASS
- compile requests/hits/misses: 149/148/1
- actual compilations: 1
- compilation failures: 0
- NOJAVA / MANIC3 preserved

Unsigned IPA SHA-256:

49ff189c66556f77184041edf341a2ba1fbad72803eb98e084e7fc1bb18dfe8f

IPA artifact:

- ID: 10795800813
- ZIP digest: sha256:3e5c5b5e76bc9c07073c0a78445a21327822b0fb947a515b39c57479465d18db
- expires: 2026-10-08

Audit artifact:

- ID: 10795451320
- ZIP digest: sha256:275a6a7788e5efb4e1d4595f5cc3c0d589a48f3a3f417c6d77508beeb2cef9f1
- expires: 2026-10-08

## Device decision

Use the same RM-356 V60 path.

Primary questions:

1. Does Startup write 100058F4:1 from 0 -> 1 successfully?
2. Is there a later category/key write requesting value 2?
3. If value 2 appears, does Startup receive/process it and emit later GDI work?
4. If no value 2 ever appears, move upstream to the component responsible for
   advancing Startup app synchronization rather than touching compositor/focus.
5. If 2 appears but Startup stays white, trace the subscription completion /
   RProperty::Get path next.

Do not change TfxServer, ClearRedrawStore, focus, redraw scheduling, or Home
screen ordering before the B58 state evidence.
