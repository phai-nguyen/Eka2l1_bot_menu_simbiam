# B96 — device capture with EStor Leave export trace

Date: 2026-09-27 (user-provided iPhone capture)

## Device result

The 328.7-second recording shows the emulator's Symbian screen continuing to
display “Phone start-up failed. Contact the retailer.” At about five minutes,
that message is still visible; near the end, the emulator's **Thoát Emulator**
dialog is opened. The app did not crash to iOS Home during the capture.

The log records `exit_requested` at 14:08:07.628 and `shutdown_done` at
14:08:07.688, consistent with an orderly emulator exit. No iOS `.ips` crash
report was provided. CompatBoot became ready and launched real `menu3.exe`, but
`[COMPATBOOT][TARGET_VISIBLE]` did not occur.

## First Menu failure and EStor evidence

- 14:03:25.436 — all six UI services passed the readiness barrier.
- 14:03:25.463 — real firmware `menu3.exe` launched.
- 14:03:30.632 — Menu opened
  `Z:\Private\10207254\themes\270486738\270513751\271067333\1.0\hasclassicgrid.o0001`.
- 14:03:30.669 — Menu's FileFlush trace reports `flush_ok=1 completion=0`;
  at the same timestamp Menu traps `Leave(-5)` (`KErrNotFound`).
- 14:03:30.707 — the first target-scoped `TfxServer` miss is logged, 38 ms
  after the Leave.

EKA2L1's EPOC9 export map associates the nearest preceding exports in the
first Leave stack with:

| Stack candidate | Export | EPOC9 symbol | Distance |
|---|---:|---|---:|
| EStor offset `0x38AA` | 47 | `CFileStore::DoRevertL()` | `0x0E` |
| EStor offset `0x777C` | 151 | `CStreamStore::Revert()` | `0x12` |
| EStor offset `0x358E` | 41 | `CFileStore::Destruct()` | `0x18` |
| EStor offset `0x35A4` | 54 | `CFileStore::~CFileStore()` | `0x0E` |
| EUser offset `0x92F0` | 1272 | `CCleanup::DoPop(int, int)` | `0x48` |
| EUser offset `0x95CE` | 202 | `CleanupStack::PopAndDestroy(int)` | `0x1C` |

The original stock `estor.dll` was then disassembled at the matching ROM
addresses. The B96 halfwords match the image after its 120-byte ROM header.
`CFileStore::DoRevertL()` begins at offset `0x389C` and contains:

```text
0x389C  push {r4, lr}
0x389E  bl   0x80360C06
0x38A2  movs r0, #4
0x38A4  mvns r0, r0          ; r0 = 0xFFFFFFFB = -5 / KErrNotFound
0x38A6  blx  0x8035D758
0x38AA  pop  {r4, pc}
```

The call target at `0x8035D758` is an EStor import veneer whose literal points
to `0x802ABB1F`. EUser ordinal 649 maps `User::Leave(int)` to that exact
address. The raw stack word `0x80360CD3` is the Thumb return address immediately
after the `User::Leave(-5)` call, and the log's `r0=0xFFFFFFFB` agrees with the
argument constructed by the instruction sequence. `CStreamStore::Revert()`
dispatches through its virtual slot at `0x777A`; the same stack scan also finds
`CFileStore::Destruct()` and its destructor, which fits a store revert during
cleanup.

This resolves the origin of this particular trapped `Leave(-5)`: stock EStor
explicitly raises `KErrNotFound` in `CFileStore::DoRevertL()` after its helper
returns. It is not evidence that `FileFlush` returned `-5`; the B96 trace says
flush succeeded. The logger scans raw stack words instead of unwinding, so the
surrounding frames are supporting context rather than a proven full call
chain. The captured Leave is trapped, and this finding does not establish
that it causes the persistent phone-startup error or identify why Menu entered
the revert path.

Firmware image hashes: `estor.dll`
`23cd8d2c1a33026ebad1be2e23431c00d0f15306c5991e091f17e5443bd07458`;
`euser.dll`
`1aaf171c061e5cce3acc8aae2c4bc45aaf3969dc6bce5e393efc8dfd25509f33`.

The same theme object is opened by `xnthemeserver` earlier in the log, and the
stock RPKG extraction contains that path (`hasclassicgrid.o0001`, 2,103 bytes).
The successful FileFlush only confirms that flush operation completed; it does
not validate the object's internal store contents. The timing does not prove
that this object caused `Leave(-5)`. Likewise, the later `TfxServer` miss is not
shown to cause the earlier Leave. Do not alter the firmware, TFX/CenRep state,
server behavior, or readiness barrier based on this capture.

## Evidence integrity

- `ScreenRecording_09-27-2026 14-02-42_1.mp4` SHA-256:
  `90e96e46cde4eccbf87998c4ab3f90282a76b31ff2e334f026bca66b602fe237`
- `EKA2L1_TakeThis(20260927-071139).log` SHA-256:
  `1518e8fd6207241e4611564a410a0ac0d84f72cb14f9f4c2cd8dff31d80ae72b`
- `EKA2L1_Persistent-prev(20260927-071226).log` SHA-256:
  `4a08b86a3cc9caa0c230565ee4bab5addf4d8837fd0710f8c58b265d54250397`
- `EKA2L1(20260927-071125).log` and
  `EKA2L1_Persistent(20260927-071135).log` are byte-identical; SHA-256:
  `a38214a252db722f86824d33e36793cf965ac24ac52f9d323fe769c9f136176e`.

## Next investigation

The next question is what Menu operation enters `CStreamStore::Revert()` and
whether its trapped `KErrNotFound` is expected cleanup behavior or propagates
into startup. Inspect Menu's caller/context and correlate it with the phone
startup path. If static caller analysis cannot answer that, add read-only
caller/status diagnostics around the revert trigger; do not change store or
server semantics, firmware, TFX/CenRep state, or the readiness barrier.
