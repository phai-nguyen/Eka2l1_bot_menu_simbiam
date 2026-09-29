# B25 FBSSHAREDHEAP1 Snapshot

Date: 2026-09-21
Branch: nativeboot2-b25-fbssharedheap1
HEAD after cleanup: d930f4b3e958642e2e5821a15eadded903c9d722

## Build
Run: 35591745431
Status: SUCCESS
Artifact ID: 10634908262
Artifact: EKA2L1-NATIVEBOOT2-B25-FBSSHAREDHEAP1-NOJAVA-MANIC3-IPA
IPA SHA-256: 069676f3e3aa4badd31a53043bc808464fa7ddd54f76ac893e8aa74766c6daff

## TDD
RED run: 35581550088
GREEN run: 35591745431

B25 contract PASS.
B20-B24 regression PASS.
iOS compile PASS.
IPA packaging/upload PASS.

## Root cause targeted
Canonical FBS global chunk name collision between native fbserv and HLE FBS.

B24 evidence:
- native FbsSharedChunk = 0x40200000
- HLE FbsSharedChunk = 0x54200000
- returned offset = 0x1598
- AknCapServer r0 at KERN-EXEC 3 = 0x40201598

## B25 change
Rename existing guest-owned canonical native FBS chunks to internal names before HLE FBS creates its canonical chunks.

Internal names:
- FbsSharedChunk.NativeBoot
- FbsLargeChunk.NativeBoot

Native fbserv is preserved.
Native chunk handles are preserved.
Native RHeap is not adopted by HLE.

## New markers
[NBOOT2][FBS_SHARED_HEAP_HANDOFF]
[NBOOT2][FBS_SHARED_HEAP_READY]

## Next evidence needed
Device-test B25 and capture full logs.
Primary success signal: AknCapServer no longer reaches the B24 PC=0xF0 / r0=0x40201598 failure path.
