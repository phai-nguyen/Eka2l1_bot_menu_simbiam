# B36 DEVICE2 — iPhone 8 Plus / iOS 15.6.1 / TrollStore

Updated: 2026-09-22
Build: NATIVEBOOT2 B36 WSERVHANDLECARRY1
Comparison baseline: B36 device log from iPhone 12 Pro Max / iOS 18.7

## Device under test

- iPhone 8 Plus
- iOS 15.6.1
- installed through TrollStore
- same B36 unsigned IPA lineage / WSERVHANDLECARRY1 runtime behavior

## Result

B36 reproduces the same guest-side failure family on this older device/iOS.

iPhone 8 Plus counts:
- WSERV_HANDLE_CARRY: 17
- WSERV_NONFADING_ENTER: 17
- WSERV_NONFADING_COMPLETE: 17
- EikAppUiServerThread EIKFAULT_LEAVE(-3): 16
- EIKFAULT_AV: 16
- EIKCALLSITE: 64
- KERN-EXEC: 16
- Object handle is invalid: 58

Handle distribution:
- effective_handle 0x00080008: 1
- effective_handle 0x00060006: 16
- explicit_handle=0: all 17 SetNonFading observations

Invalid-handle distribution:
- 335544320 / 0x14000000: 29
- 0: 29

Completion state:
- signaled_before=1: 17/17
- signaled_after=1: 17/17

All 16 EikAppUiServerThread Leave(-3) observations use:
- pc=0x8029833C
- lr=0x802ABB29
- r0=0xFFFFFFFD

The stable B35/B36 ws32 callsite remains:
- ws32.dll + 0x370A
- ordinal 206 = RWindowTreeNode::SetNonFading(TBool)

The access-violation family also retains the same fault PCs/addresses as the iPhone 12 Pro Max run; only transient register values and timing vary.

## Cross-device comparison

The iPhone 12 Pro Max / iOS 18.7 B36 log has the same principal counts:
- 17 handle-carry
- 17 SetNonFading enter
- 17 SetNonFading complete
- 16 Leave(-3)
- 16 access violations
- 64 EIKCALLSITE
- 58 invalid handles
- 16 KERN-EXEC

The first SetNonFading marker precedes the first repeated EikAppUiServerThread Leave(-3) window by about:
- iPhone 12 Pro Max: 31.955 s
- iPhone 8 Plus: 32.868 s

Leave-to-next-SetNonFading timing differs by device scheduling, but the guest PC/LR, handle values, completion state, fault family, and event counts remain the same.

## Exit Emulator

B34 exit choreography remains healthy on iPhone 8 Plus.

Observed joins:
- one os_join_begin -> os_join_done in about 9 ms
- user exit at 20:52:21: os_join_begin -> os_join_done in about 49 ms
- shutdown_done and normal_restart_done follow successfully

No evidence in these logs indicates the B36 causal failure is specific to iOS 18, iPhone 12 Pro Max, or the signing/install method.

This does not prove TrollStore can never affect unrelated behavior; it does show the specific B36 WindowServer/Eiksrv failure signature is reproduced across both tested device/iOS environments.

## Decision

B37 WSERVBATCHCOMPLETE1 remains the correct next device-test target.

Cross-device B36 evidence strengthens the B37 hypothesis:
the problematic state is guest/WindowServer request-signaling order, not an iOS-version-specific host crash.

Do not create B38 until B37 device evidence is reviewed.
