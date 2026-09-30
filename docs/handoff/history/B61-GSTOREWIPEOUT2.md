# NATIVEBOOT2 B61 GSTOREWIPEOUT2

Date: 2026-09-24
Status: BUILD-VALIDATED; DEVICE TEST REQUIRED

## Selection

B60 DEVICE1 reproduces the B58 host teardown crash:

- EXC_BAD_ACCESS / SIGSEGV
- invalid address 0x18
- gdi_store_command_segment::~gdi_store_command_segment
- redraw_msg_canvas::~redraw_msg_canvas
- window_server_client::~window_server_client
- kernel_system::wipeout

B59 only guarded one narrow retained-FBS case:
final ref with owner == nullptr (plus null/exhausted checks).
B60 crashed again without the B59 guard marker firing, proving that B59 is not
a complete teardown fix.

## B61 behavior

B61 is shutdown-only.

Every redraw-store segment now captures the kernel pointer at creation time,
including:

- collection redraw/pending-redraw segments;
- direct redraw_msg_canvas pending_segment_.

At destruction:

- if kernel_system::wipeout() is active, the segment returns before touching
  any retained FBS font/bitmap pointer;
- outside wipeout, the existing B59 checks and normal refcount/deref behavior
  remain unchanged.

Marker:

[NBOOT2][GSTORE_WIPEOUT_GUARD]

Expected on emulator exit while retained refs exist:

action=SKIP_ALL_FBS_DEREF_WIPEOUT

No Startup state, P&S, drawing, focus, compositor, TFX or normal-runtime
redraw-store behavior is changed.

## Canonical GREEN

Initial run 179 stopped only on an overly strict B61 test assertion after the
apply itself succeeded. The assertion was corrected without changing B61
runtime logic.

Canonical run:

- run ID: 36007760773
- run number: 180
- job: 107660254711
- HEAD: 24e84ad10c53e85216343728699f2af2ffc09f27
- B61 apply PASS
- B61 contract PASS
- regressions PASS
- iOS compile/link PASS
- binary invariants PASS
- package/upload PASS
- compile requests/hits/misses: 149/110/39
- actual compilations: 39
- compilation failures: 0
- NOJAVA / MANIC3 preserved

Unsigned IPA SHA-256:

f07178925ea6b92e063d74856daf3a9e10a02f5cf477c27305042a30cc0910b1

IPA artifact:

- ID: 10811377565
- ZIP digest: sha256:a975ccfee6beaae83301b77f4e44a59a8bb4591a84eea8f2582b0230148a5fb5
- expires: 2026-10-08

Audit artifact:

- ID: 10811596815
- ZIP digest: sha256:a63bc8c010098475a9011cf55ee2fb4d65027684d5c389b7168550259bc3ff90
- expires: 2026-10-08

## Device acceptance

Primary B61 test is teardown stability:

1. Boot the same SIM-present RM-356 path through NOKIA -> white Startup.
2. Open the Emulator menu.
3. Select "Thoát Emulator".
4. Expected: return to EKA2L1 UI without an iOS process crash.
5. Logs should ideally show [NBOOT2][GSTORE_WIPEOUT_GUARD].
6. If iOS still produces a .ips, send it.

Boot progression is not expected to improve in B61. B60 already established
that StartAnimations=2 is not published through either observed integer P&S
writer path. After B61 exit validation, the next boot track should trace
SSM/Starter command-list execution that should publish value 2.
