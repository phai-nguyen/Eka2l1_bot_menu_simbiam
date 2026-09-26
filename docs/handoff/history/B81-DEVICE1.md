# B81 PHONEUIBLXDECODE1 — DEVICE1

Date: 2026-09-26
Build tested: B81 PHONEUIBLXDECODE1
Branch: `nativeboot2-current`
Build commit: `42ca0136983714b01fd259120921188066c71af4`
Device: iPhone 12 Pro Max / iOS 18.7 / RM-356 Vietnamese firmware
Status: **DEVICE-OBSERVED; EMULATOR RESPONSIVE; PHONE CONE14 PERSISTS; CLEAN EXIT**

## User report and video

User reports the Emulator no longer hangs at “Phone start-up failed. Contact
the retailer.” The 4:13 recording shows the Nokia splash throughout the
recorded startup interval, with the in-app three-dot control still visible.
No forced app close is shown. Logs end with a normal shutdown/restart sequence.

This confirms the host Emulator remains alive and can exit cleanly. The video
does not show Phone completing startup; the Nokia splash remains visible.

## Phone result

At `00:50:59.381`, Telephone UID3 `0x100058B3` panics:
- category: CONE
- reason: 14
- PC: `0x80298584`
- LR: `0x802A3A39`
- `r6=0x1099B02D`
- CONE summary: `NoResourceFileForId`

There are zero `callhandlingui.r01` path mentions in the captured persistent
runtime log before/after the panic. Thus B81 does not change the known missing
resource registration boundary.

## Corrected B81 callchain evidence

B81's corrected decoder confirms:
| Callsite | Target | State | FNV-1a 64 fingerprint |
|---|---|---|---|
| FileServer `+0x1B70` | `+0x46F4` | ARM veneer | `0x1860DC4122EA1341` |
| FileServer `+0x1B78` | `+0x4694` | ARM veneer | `0x606CFB7EE7158871` |
| CONE14 `+0x3A34` | `+0x46C4` | ARM veneer | `0x3614601287EC99EE` |
| CONE14 BL `+0x3B48` | `+0x3A28` | Thumb | `0xE554D55F0A411FDF` |
| CONE14 BL `+0x1BBC` | `+0x3B2E` | Thumb | `0xC1DF19A359FDF4BC` |

The ARM veneers start with `E51FF004` and load literal function pointers.
Exact symbol identity is not inferred from the 410-entry production export
surface; B81 records the warning that public DEF ordinal labels are unverified.

Other B81 marker counts:
- 11 `PHONEUI_BLX_TARGET`
- 13 `PHONEUI_TARGET_FINGERPRINT`
- 13 `PHONEUI_CALLCHAIN_EDGE`
- 42 `PHONEUI_EXPORT_SURFACE`
- 41 `PHONEUI_RES_MATCH2`
- 1 `CONE14_SUMMARY`

These diagnostics are observe-only and do not change resource registration
or panic behavior.

## Host result

At `00:54:19`, the user exits normally. Host log confirms:
`shutdown_done -> normal_restart_begin -> normal_restart_done has_device=1`.

No host .ips crash report was supplied.

## B80 comparison

The guest Phone failure and resource ID are unchanged from B80. Marker counts
and later service activity are materially the same, consistent with B81 being
diagnostic-only. B81's corrected targets and fingerprints now provide
trustworthy static-analysis inputs. The user-observed improvement is that the
Emulator is no longer hung; successful Phone startup is not yet proven.

## Next step

Map the three ARM veneer literal pointers and the corrected Thumb code
fingerprints against exact RM-356 PhoneUIUtils bytes/export boundaries.
Keep ordinal-to-symbol names unverified unless confirmed in the production
image. Choose a narrow subsequent change only after that mapping. No RM-612
resend is required.



### B81 offline veneer-pointer correlation

The literal pointers in the B81 64-byte fingerprints can be assigned to
already-loaded modules using their exact B81 runtime code bases:
- `+0x46F4` veneer literal `0x8038AD15` -> BAFL base
  `0x80387898`, Thumb code offset `+0x346C`.
- `+0x4694` fingerprint includes literals `0x806EC875`,
  `0x806EC941`, `0x806ECF37`, `0x806EC205`; CONE base
  `0x806E8E68` maps these to Thumb code offsets
  `+0x3A0C / +0x3AD8 / +0x40CE / +0x339C`.
- `+0x46C4` veneer literal `0x806ECA17` -> CONE Thumb code offset
  `+0x3BAE`. This falls between the active CONE stack frames
  `+0x3B96` and `+0x3BBA` recorded at CONE14.

These are address-to-module mappings only; export/function names remain
unverified. Next offline work is to inspect exact RM-356 BAFL/CONE export
boundaries and disassembly at the mapped offsets. Do not infer a functional
resource-registration fix solely from proximity.
