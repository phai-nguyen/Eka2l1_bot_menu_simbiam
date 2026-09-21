# B28 WSERVLIBTYPE1 — Build Snapshot

Date: 2026-09-21
Branch: nativeboot2-b28-wservlibtype1
Build-tested code HEAD: 773752a4475dce019e8ae4342f2ab7d0b2abc060

## Purpose

B27 device evidence isolated this chain:

EKDATA.DLL load
-> EPOC94 SVCMISS 0x63
-> Symbian leave
-> EWsPanicFailedToInitialise
-> WSERV-INTERNAL 13
-> Domino 13 downstream

B28 is deliberately narrow: implement only the EPOC 9.4 LibraryType executive ABI at SVC 0x63.

## External source validation

Symbian source and documentation establish:
- RLibrary::Type() returns the DLL's TUidType.
- RLibrary::Type() constructs a TUidType and calls Exec::LibraryType(iHandle, u).
- Exec::LibraryType(TInt, TUidType&) dispatches EExecLibraryType.

Therefore the EKA2 ABI is:
LibraryType(library_handle, TUidType_output_reference)

The project EPOC94 table already contains ProcessType at 0x64 and lacked 0x63.

## TDD RED proof

Final focused RED run:
- run ID: 35605582017
- job ID: 106351726824
- expected failure:
  NATIVEBOOT2-B28-WSERVLIBTYPE1-TEST: FAIL: missing in svc.cpp:
  BRIDGE_FUNC(void, library_type, kernel::handle h, eka2l1::ptr<epoc::uid_type> type_ptr)

Earlier temporary RED/inspection runs were used only to correct CI/cache/table-layout assumptions and are not behavior evidence.

## Implementation

Files:
- apply_nativeboot2_b28_wservlibtype1.py
- test_nativeboot2_b28_wservlibtype1.py
- .github/workflows/build-ios-nativeboot2-b28-wservlibtype1-nojava-manic3.yml

Implementation:
- adds EKA2 LibraryType bridge:
  BRIDGE_FUNC(void, library_type, kernel::handle h, eka2l1::ptr<epoc::uid_type> type_ptr)
- resolves kernel::library from the handle
- reads lib->get_codeseg()->get_uids()
- writes UID1 / UID2 / UID3 to the guest TUidType output
- registers EPOC94:
  BRIDGE_REGISTER(0x63, library_type)
- preserves:
  BRIDGE_REGISTER(0x64, process_type)
- runtime marker:
  [NBOOT2][WSERV_LIBRARY_TYPE]

No implementation was added for SVC 0x48, 0x4A, or 0x50.
No Wserv panic suppression was added.

## CI investigation note

B28 initially assumed the current project source followed the pinned upstream table layout. The B19 cached project baseline contains earlier NativeBoot patches and the real table ordering is:

- svc_register_funcs_v95_extras
- svc_register_funcs_v10
- svc_register_funcs_menuui10_epoc95_diff
- svc_register_funcs_v94
- svc_register_funcs_v93
- ...

A temporary inspection workflow proved the correct B28 EPOC94 boundary is v94 -> v93. Both apply and contract were corrected accordingly before the successful build.

## Successful build

Workflow run:
https://github.com/phai-nguyen/Eka2l1_bot_menu_simbiam/actions/runs/35606704683

Run ID:
35606704683

Job ID:
106355431925

Conclusion:
SUCCESS

Regression evidence:
- B20 CENRESETALL1 PASS
- B21 FBSFONTALIAS1 PASS
- B22 FBSDEFAULTTYPEFACE1 PASS
- B23 FBSFONTSPECV2ABI1 PASS
- B24 FBSVTABLEABI1 PASS
- B25 FBSSHAREDHEAP1 PASS
- B26 IOSLIBRARYEXIT1 PASS
- B27 WSERVPANIC13TRACE1 PASS
- B28 WSERVLIBTYPE1 PASS
- iOS compilation/link PASS
- NOJAVA preserved
- MANIC3 preserved

## IPA

File:
EKA2L1-NATIVEBOOT2-B28-WSERVLIBTYPE1-NOJAVA-MANIC3-unsigned.ipa

Unsigned IPA SHA-256:
8fd1ef35863a8b8deb175650259052977d15c0e66dc578a415e95050ebfbc81b

IPA artifact:
- ID: 10642526382
- name: EKA2L1-NATIVEBOOT2-B28-WSERVLIBTYPE1-NOJAVA-MANIC3-IPA
- artifact ZIP SHA-256: 3d92f5b4ba6812ba44e4a3a6516750bbd08e35418197e6f988e2a808f4afd145
- expires: 2026-10-05

Audit artifact:
- ID: 10642476357
- name: EKA2L1-NATIVEBOOT2-B28-WSERVLIBTYPE1-NOJAVA-MANIC3-AUDIT
- artifact ZIP SHA-256: 7bb7db13282a9e1fb4a83c914079cbb7cfb6c276e81d633ebf7606ae7c32359f
- expires: 2026-10-05

## Device validation status

NOT YET DEVICE-VALIDATED.

Required B28 device checks:
1. Confirm EKDATA.DLL still loads.
2. Confirm SVCMISS 0x63 is gone.
3. Find:
   [NBOOT2][WSERV_LIBRARY_TYPE]
4. Verify the returned UID triplet; for the observed EKDATA.DLL call, UID3 is expected to correspond to 0x100039E0 if the handle is the just-loaded EKDATA library.
5. Check whether EWsPanicFailedToInitialise / WSERV-INTERNAL 13 disappears.
6. If Wserv still fails, identify the first new divergence after LibraryType rather than adding speculative fixes.
7. Check whether boot advances beyond the NOKIA splash.
8. Re-test Exit Emulator to retain B26 validation.

## Next decision rule

If B28 removes SVCMISS 0x63 and moves Wserv farther into InitStaticsL, treat B28 as validated for its narrow purpose and investigate the next first failing call.

Do not preemptively implement 0x48/0x4A/0x50 without fresh B28 device ordering evidence.
