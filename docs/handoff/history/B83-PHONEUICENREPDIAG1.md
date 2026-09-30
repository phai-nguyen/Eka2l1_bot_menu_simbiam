# B83 PHONEUICENREPDIAG1 — Central Repository IPC trace

Date: 2026-09-26
Branch: `nativeboot2-current`
Status: **BUILD-GREEN; RM-356 DEVICE TEST REQUIRED**

## Why the original patch was replaced

The first B83 implementation tried to patch
`src/emu/scripting/src/builtin_patches.cpp`. FASTBUILD run #254 restored the
immutable B28 cache and stopped before compilation because that source file is
not present in the cached tree. The earlier local test used a newer upstream
checkout and therefore did not establish compatibility with the B28 cache.

The file belongs to a newer native no-Lua scripting path; it is not a valid
assumption for this older bootstrap. B28 remains unchanged. The revised probe
uses the Central Repository HLE source files already exercised by B29+ on the
B28-derived build. A first attempt to log in generic `ipc_context::complete()`
also failed on run #255 because the completion implementation anchor differs
in the cached B28 tree. This version wraps CenRep-owned completions directly,
without assuming the newer generic IPC implementation.

## Revised diagnostic

The probe adds two read-only records:

- `[NBOOT2][CENREP_IPC_ENTRY]` in `centralrepo.cpp`: message ID, thread,
  opcode, and four raw IPC argument words at Central Repository entry.
- `[NBOOT2][CENREP_IPC_COMPLETE]` from a shared CenRep completion wrapper in
  `centralrepo.cpp`: matching message ID, thread, opcode, and result status.
  Only CenRep operation completions in `repo.cpp` delegate through the wrapper
  to the original `ctx->complete(res)` unchanged. Session-level and B20
  ResetAll paths in `centralrepo.cpp` remain unwrapped.

Correlate records by message ID/thread with existing FileServer resource-path,
PhoneUI, CONE, and Leave/panic logs. This observes the service boundary rather
than the guest `centralrepository.dll` instruction boundary; it can prove
whether a request reached the HLE service and what status the service returned,
but does not decode the guest descriptor or prove the native wrapper returned.

No guest registers, descriptors, IPC arguments, CenRep values, resource
registration, CONE behavior, or completion codes are modified by the probe.
B79 and earlier are out of scope for this continuation.

## Verification status

- RED observed: revised B83 contract failed on a clean source tree because the
  entry marker was absent.
- GREEN observed: patcher applied to a clean upstream source worktree; contract
  passed; second apply reported `already applied`.
- `git diff --check`: PASS on the patched source worktree.
- FASTBUILD run #254: FAIL before compilation on the obsolete B83 source-path
  assumption; it does not validate this revised implementation.
- FASTBUILD run #255: FAIL before compilation because the cached B28
  `ipc_context::complete()` anchor differed from newer local source.
- FASTBUILD run #256: B83 applied and passed its contract on B28, but a broad
  completion rewrite broke the B20 ResetAll regression.
- FASTBUILD run #257: the B20 ResetAll block is in `repo.cpp`, so limiting the
  rewrite to that file alone still failed the B20 contract. The current patch
  explicitly preserves the entire B20 ResetAll block and wraps only other
  `repo.cpp` completions; a synthetic regression fixture tests that boundary.
- FASTBUILD run #258 / run ID `36215233436` / job `108329304750`:
  - commit `f0c6ed94a1921ed61f58604deb02f36f446e1bed`
  - B28 cache restore: PASS
  - B83 apply/contract: PASS
  - B20-B28 regressions: PASS
  - all post-bootstrap milestone apply/tests: PASS
  - iOS build/link: PASS
  - both B83 binary marker checks: PASS
  - IPA package/upload: PASS
  - sccache: 152 requests, 143 hits, 9 misses/compilations, 0 failures
  - build audit: bootstrap 49s; patch/regressions 6s; build 55s;
    package 3s; total 143s
  - Xcode 16.4 Build 16F6; Apple clang 17
  - NOJAVA / MANIC3: preserved
  - IPA SHA-256:
    `4deaafd918517bd7875bb231a1645b1a9293d87a25bcc085e0fa9bd5d8590c37`
  - IPA artifact ID `10897146861`; audit artifact ID `10897586156`;
    both expire 2026-10-10
- The audit artifact's IPA SHA-256 was independently compared with the
  downloaded IPA payload and matched.
- Revised FASTBUILD/iOS compile, package, binary markers, and RM-356 device test:
  PENDING.

Device-test this IPA on RM-356 over B82. Reproduce the same Phone startup
condition, wait 5-10 seconds, exit normally, and send standard EKA2L1 logs.
Correlate `[NBOOT2][CENREP_IPC_ENTRY]` and
`[NBOOT2][CENREP_IPC_COMPLETE]` by message ID/thread with FileServer
resource-path, PhoneUI, CONE, and Leave/panic records. These show HLE service
traffic/status, not guest descriptor decoding or native wrapper return.
