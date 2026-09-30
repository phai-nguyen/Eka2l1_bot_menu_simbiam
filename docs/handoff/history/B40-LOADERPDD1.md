# NATIVEBOOT2 B40 — LOADERPDD1

Updated: 2026-09-23
Branch: nativeboot2-current
Status: BUILD-VALIDATED; DEVICE TEST REQUIRED

## Purpose

B39 device evidence identified the first causal startup break in the canonical
eiksrvs instance:

```
CEikServAppUiBase::InitializeL
 -> StartC32
 -> User::LoadPhysicalDevice("EUART1")
 -> !Loader opcode 4 / ELoadPhysicalDevice
 -> no handler in the B28-cache Loader
 -> synchronous IPC dropped by the historical dispatcher
 -> canonical eiksrvs stalls before SetEikServAppUiSessionFactory
 -> later session factory is NULL
 -> CServer2::DoConnectL dereferences a NULL session
 -> KERN-EXEC 3
```

B40 ports only the missing physical-device Loader behavior from upstream
EKA2L1 commit `0987745cc0bde96511fce2a4bfefcfd8fbced3dc`
(`loader: Answer Loader::LoadPhysicalDevice`).

## Functional change

B40 changes only the Loader PDD path:

- declares `loader_server::load_physical_device()`;
- registers `ELoadPhysicalDevice` / opcode 4;
- reads PDD descriptor argument 1;
- invalid descriptor completes `KErrArgument`;
- a valid HLE-backed PDD completes `KErrNone`;
- adds runtime marker `[NBOOT2][LOADER_PDD]` with:
  - `phase=enter name=<PDD>`
  - `phase=complete name=<PDD> result=0`.

The expected Nokia 5800 device value is `EUART1`.

## Explicit non-scope

B40 does NOT port upstream generic unknown-IPC completion commit
`9f28c76fe0f54f43a39319da5f4042c853505807`.

The old generic dispatcher behavior is deliberately preserved so B40 isolates
one causal variable only.

B40 also does not change:

- stock Nokia `avkonfep.dll`;
- KErrCancel / Leave / TRAP behavior;
- SVC 0xDF / 0xE0;
- CServer2 or Eik session-factory semantics;
- WindowServer dispatch/completion;
- B36 implicit-handle carry;
- B37 batch signal deferral;
- scheduler behavior;
- B30 rooted library resolution;
- B34/B26 Exit Emulator choreography;
- EPOC94 0xAA unmapped / 0xAB message_construct / 0xAC message_kill;
- NOJAVA / MANIC3.

## TDD

Canonical RED:

- RED commit: `b17881d811da6f8ba63af165073d3994c84be745`
- run: `35764848484`
- job: `106871644557`
- expected failure:
  `NATIVEBOOT2-B40-LOADERPDD1-TEST: FAIL: missing in B40 Loader PDD runtime marker: [NBOOT2][LOADER_PDD]`

First GREEN implementation attempt:

- commit: `af9f5bbb23b74174c1c3655b3c9f5383ccf353a2`
- run: `35765202193`
- job: `106872855353`
- stopped before compile because the apply script used an over-specific constructor-tail anchor;
- no IPA was produced from this failed attempt;
- functional B40 scope was unchanged.

Final GREEN:

- code HEAD: `adde620f6c2b57bec69268b32a889035e0a3eb51`
- run: `35765468574`
- job: `106873756994`
- FASTBUILD manifest validation: PASS
- B29-B40 apply/tests: PASS
- full regression suite: PASS
- iOS compile/link: PASS
- binary invariants: PASS
- packaged Mach-O contains `[NBOOT2][LOADER_PDD]`
- IPA package/upload: PASS
- compilation failures: 0
- NOJAVA / MANIC3: PRESERVED

## FASTBUILD audit

- bootstrap source: B28_CACHE
- bootstrap restore: 53 s
- patch/regression: 2 s
- CMake build: 44 s
- package: 2 s
- total wall time to audit write: about 128 s
- compile requests: 149
- cache hits: 147
- cache misses: 2
- hit rate: 98.66%
- actual compilations: 2
- compilation failures: 0

## Artifacts

Unsigned IPA SHA-256:

`782d03a38bd3f87c0b0394b5d8753ec8599f8d8ef23b6d7168f3dc92faf3b5f6`

IPA artifact:

- ID: `10711662557`
- artifact ZIP digest:
  `sha256:ce9f6e97866cee9ff3ffd41255f3cc4db1b7ce1a6bd8b3f8d15e7864c6eaf378`
- expires: 2026-10-06
- ZIP size: 19,891,721 bytes

FASTBUILD audit artifact:

- ID: `10711767320`
- digest:
  `sha256:2e03559f71c68a3ddad7c2a2eba02e65f63d71b5d3530b92a97453b398ca9cbd`
- expires: 2026-10-06

## Device-test acceptance

Install/sign the B40 IPA and boot the same Nokia 5800 RM-356 path.

Collect:

- `EKA2L1.log`
- `EKA2L1_Persistent.log`
- `EKA2L1_TakeThis.log`

First acceptance checks:

1. `[NBOOT2][LOADER_PDD] phase=enter name=EUART1` appears.
2. `[NBOOT2][LOADER_PDD] phase=complete name=EUART1 result=0` follows.
3. The canonical eiksrvs instance proceeds beyond the former
   `!Loader opcode 0x4` boundary.
4. A healthy `!EikAppUiServer` / System GUI session-factory path is reached,
   or the next blocker is later and identifiable.
5. The repeated B39 CServer2 NULL-session AV family disappears or moves to a
   later boundary.
6. B34 Exit Emulator remains healthy through
   `os_join_done -> shutdown_done -> normal_restart_done has_device=1`.

Do not promote B40 to an immutable functional milestone until device evidence
validates the behavior.
