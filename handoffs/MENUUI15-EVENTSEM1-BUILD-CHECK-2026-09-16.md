# MENUUI15 EVENTSEM1 — build check — 2026-09-16

## Result

Original run 35080728869 failed. MENUUI14 FIX2 replay compiled and packaged successfully, and the MENUUI15 patcher applied successfully. The subsequent source gate failed before the MENUUI15 incremental compilation.

Exact failure: `AssertionError: SYMBIAN-SYSTEMAPPS1 MENUUI14 INPUT_WAKE:`.

The workflow looked for every MENUUI14 marker in `window.cpp + io.cpp`. The frozen MENUUI14 patcher inserts INPUT_WAKE into `src/emu/services/src/window/fifo.cpp`, which the gate did not read. This was a validation-scope error. It does not establish that the newly added MENUUI15 C++ diagnostics compile.

No MENUUI15 IPA or audit artifact was produced by the failed run. Only diagnostic-log artifact 10440978385 was uploaded. The MENUUI14 package generated during replay is not a MENUUI15 artifact.

## Repair and verification

- Fix commit: `195af895a69bed83f99c679bae12516946f34571`.
- Workflow: `.github/workflows/build-ios-symbian-systemapps1-menuui15-eventsem1.yml`.
- Added fifo.cpp to the source gate inputs and checked each existing marker in its owning source.
- Owners: INPUT_POINTER and INPUT_GET in window.cpp; INPUT_HIT and INPUT_FIFO_ENQUEUE in io.cpp; INPUT_WAKE in fifo.cpp.
- All five existing required markers remain required.
- YAML parsed; all workflow shell blocks passed bash syntax checking; embedded Python and patcher Python parsed successfully.
- Marker ownership independently checked against the frozen MENUUI14 patcher source insertions.
- No emulator C++ or patcher code was changed; the MENUUI15 diagnostic-only scope and preserved baselines remain unchanged.

## New run

- Trigger commit: `16653be42030f4d4f116221aa5d0a5d149a0d65d`.
- Run: `35084666319`.
- URL: https://github.com/phai-nguyen/Eka2l1_bot_menu_simbiam/actions/runs/35084666319
- Created: 2026-09-16T10:22:55Z.
- Last observed status at this check: in_progress; no success conclusion yet.

## Next check

Check run 35084666319. If it fails, read the first failing job/step and correct the specific build error while retaining diagnostic-only behavior. If it succeeds, obtain the IPA and audit artifacts, validate integrity, SHA-256 and binary markers, then provide the IPA for the device test described in MENUUI15-EVENTSEM1-SESSION2-HANDOFF-2026-09-16.md.

Preserve EPOC94 mapping 0xAA unmapped, 0xAB message_construct, 0xAC message_kill, MENUUI13 FS-DIRUID1, and MENUUI14 input diagnostics. MENUUI15 is not yet a device-tested fix for Menu interaction.
