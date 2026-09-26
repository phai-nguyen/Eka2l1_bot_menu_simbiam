# B83 PHONEUICENREPDIAG1 — Central Repository IPC trace

Date: 2026-09-26
Branch: `nativeboot2-current`
Status: **B28-COMPATIBLE PATCH IMPLEMENTED; LOCAL CONTRACT PASS; FASTBUILD PENDING**

## Why the original patch was replaced

The first B83 implementation tried to patch
`src/emu/scripting/src/builtin_patches.cpp`. FASTBUILD run #254 restored the
immutable B28 cache and stopped before compilation because that source file is
not present in the cached tree. The earlier local test used a newer upstream
checkout and therefore did not establish compatibility with the B28 cache.

The file belongs to a newer native no-Lua scripting path; it is not a valid
assumption for this older bootstrap. B28 remains unchanged. The revised probe
uses the Central Repository HLE source files already exercised by B29+ on the
B28-derived build.

## Revised diagnostic

The probe adds two read-only records:

- `[NBOOT2][CENREP_IPC_ENTRY]` in `centralrepo.cpp`: message ID, thread,
  opcode, and four raw IPC argument words at Central Repository entry.
- `[NBOOT2][CENREP_IPC_COMPLETE]` in `context.cpp`: matching message ID,
  thread, opcode, and completion status, filtered to
  `!CentralRepository`.

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
- Revised FASTBUILD/iOS compile, package, binary markers, and RM-356 device test:
  PENDING.

Do not call B83 build-GREEN until the revised FASTBUILD verifies both markers,
compiles, and packages the IPA. Device validation is a separate step.
