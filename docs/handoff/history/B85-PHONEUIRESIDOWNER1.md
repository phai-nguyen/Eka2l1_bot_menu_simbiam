# NATIVEBOOT2 B85 PHONEUIRESIDOWNER1

Date: 2026-09-26
Base: B84, commit 22d8270570096ce2a3b9fdb1a5b2ce7fc0983e02

## B84 device evidence

The B84 `EKA2L1_Persistent-prev` and `EKA2L1_TakeThis` logs show Telephone UID3 `0x100058B3` panicking with CONE reason 14 at `13:08:11.934` (log clock). The panic register snapshot has PC `0x80298584`, LR `0x802A3A39`, SP `0x005041C0`, and R6 `0x1099B02D`. Stack candidates include `VPbkCntModel.dll` and `VPbkEng.dll`. `VPbkCntModelRes.r01` was opened shortly before the panic. The logs do not prove it owns the resource ID.

B84's `owner=callhandlingui.r01` text was hard-coded by its diagnostic patch and is not observed ownership evidence. `source=REGISTER` means the CPU register containing the ID, not resource registration. The B84 summary says resource registration and boot behavior were unchanged. Panic remains.

## B85 change

- Relabel the source as `CPU_REGISTER` and owner as `UNVERIFIED`.
- Capture exact `z:\\resource\\VPbkCntModelRes.r01` bytes through a separate read-only VFS handle, capped at 262144 bytes and logged as 512-byte hex chunks.
- Emit the capture only once after the read-only file opens successfully. Failed opens can be retried at a later open.
- Keep resource registration, guest state, panic, and boot behavior unchanged.
- Add a FASTBUILD binary marker check so the IPA cannot pass without the B85 capture code.

The VPbk RSC remains a candidate for offline inspection, not a proven owner. B85 is diagnostic, not a fix for CONE14. A later log/device test is required to establish ownership and choose a behavior change safely.

## Verification

Local B85 contract tests cover marker correction, bounded read-only dump insertion, idempotence, and refusal when B84 evidence gates are absent. FASTBUILD and IPA status: pending at commit time.
