# NATIVEBOOT2 B57 STARTUPGDIORIGIN1

Date: 2026-09-24
Status: BUILD-VALIDATED; DEVICE TEST REQUIRED

## Selection

B56 DEVICE1 proves that the Startup replay is not an empty/background-only
result. The one stored redraw segment contains:

CLIP -> full-screen BLIT -> CLIP -> full-screen white RECT -> full-screen white RECT.

The two final opaque white rectangles explain the white screen.

B57 traces the record-time source of those commands without changing behavior.

## Marker

[NBOOT2][STARTUP_GDI_ORIGIN]

The marker is limited to graphics contexts attached to Startup 0x100058F4
WindowGroups and records:

- process / UID3 / thread
- guest graphics-context opcode
- canvas handle and group identity
- source operation
- BLIT variant/version/ws-bitmap flag/source handle/source+dest geometry
- CLEAR / CLEAR_RECT / DRAW_RECT geometry
- brush colour / brush style
- pen state for DRAW_RECT

Observed source labels include:

- SET_BRUSH_COLOR
- SET_BRUSH_STYLE
- GDI_BLT
- DRAW_RECT
- CLEAR
- CLEAR_RECT

B56 stored-command tracing remains enabled.

## Canonical GREEN

- run ID: 35957525692
- run number: 163
- job: 107498900591
- HEAD: de2d65ce0333f7b5335e0b1f6ca7f6aaa4730ee0
- FASTBUILD apply/regression PASS
- iOS compile/link PASS
- compile requests/hits/misses: 149/148/1
- actual compilations: 1
- compilation failures: 0
- package/upload PASS
- NOJAVA preserved
- MANIC3 preserved

Unsigned IPA SHA-256:

803c02aa2db4bb49454329452d57e1da37a519e979f6954a71d6edc4b9e7b6fd

IPA artifact:

- ID: 10791615213
- ZIP digest: sha256:8cde257a844e142b508a60bbfe4b004a3488b3b83726e2027d249e7a0a9040b
- expires: 2026-10-08

Audit artifact:

- ID: 10790719138
- ZIP digest: sha256:d9dedd0082bd68a32a5367de94baf76a9c91f99c388ca37c2c482715091f41b8
- expires: 2026-10-08

## Device acceptance

Use the same RM-356 V60 runtime path.

The first decision is to correlate the record-time STARTUP_GDI_ORIGIN sequence
with the final B56 five-command segment.

Especially determine:

1. which source produces the full-screen BLIT;
2. whether the two white rectangles come from CLEAR, CLEAR_RECT, or DRAW_RECT;
3. whether both are guest-requested or one is emulator-generated;
4. whether any later Startup GDI origin events target the same canvas before the
   natural handoff.

Do not change focus, timers, redraw scheduling, or stored command ordering until
B57 device evidence resolves this.
