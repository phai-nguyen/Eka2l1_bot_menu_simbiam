# NATIVEBOOT2 B73 PHONEUIFSFLOW1

Date: 2026-09-25
Status: BUILD-VALIDATED; DEVICE TEST REQUIRED
Selected route: NORMAL BOOT + SIM PRESENT

## B72 DEVICE1 selection

B72 reproduces the Telephone CONE14 failure and exits Emulator cleanly.

Important B72 result:
phoneui.r01 is opened repeatedly, including approximately 1 ms before
Telephone CONE14, but neither of the B72 markers fires:

- [NBOOT2][PHONEUI_RSC_READ] = 0
- [NBOOT2][PHONEUI_RSC_SEEK] = 0

Final timing:
- 17:24:53.937 Get entry z:\resource\apps\phoneui.r01
- 17:24:53.938 Opening phoneui.r01 raw mode 1
- 17:24:53.938 Handle opened 1114122
- 17:24:53.939 Telephone self-panic CONE14

There are no Unknown FSServer client opcodes in that interval.

This rules out the simple B72 model:
Open -> fs_server_client::file_read/file_seek -> missing record -> panic.

Possible remaining paths:
- open/read is issued by a different process/session;
- BAFL uses ReadFileSection;
- another FileServer opcode participates;
- CONE resource registration/search rejects the resource before data reads.

Exit remains clean:
- shutdown_threads_done
- shutdown_done
- normal_restart_begin
- normal_restart_done has_device=1

The B70 ipc_msg teardown crash remains non-reproducible and is not patched.

## B73 diagnostics

B73 is diagnostic-only.

[NBOOT2][PHONEUI_FS_FLOW]

For every FileServer request issued by Telephone UID3 0x100058B3, records:
- raw function before EFsrv version translation
- translated function
- low opcode
- IPC argument types
- raw arguments
- thread
- whether arg3 resolves to an open file node/path

This identifies the exact FileServer opcode sequence around phoneui.r01.

[NBOOT2][PHONEUI_RSC_OPEN]

For every exact phoneui.r01 open, records:
- path
- returned handle
- raw open mode
- caller process
- caller UID3
- caller thread

This determines whether the opens seen in B72 are actually issued by Telephone.

[NBOOT2][PHONEUI_READ_SECTION]

Targets Telephone + exact phoneui.r01 direct ReadFileSection requests.

Records:
- function
- position
- requested length
- actual length

B72 PHONEUI_RSC_READ/SEEK markers remain preserved.

A dedicated IsFileInRom body probe was deliberately not kept because the B28
bootstrap implementation differs from current upstream. The generic FileServer
flow is sufficient to prove whether that opcode is used; if so, the exact B28
implementation can be targeted next.

## Behavior contract

B73 does NOT:
- alter FileServer results
- alter file cursor/data
- alter PhoneUI resource bytes
- suppress CONE14
- force state 102
- force ESimUsable
- alter Starter/SAServer/P&S/scheduler/graphics/teardown

B61/B64/B68/B69/B70/B71/B72 preserved.
NOJAVA / MANIC3 preserved.

## Canonical GREEN

Workflow:
Build EKA2L1 NATIVEBOOT2 CURRENT FAST

- run ID: 36125160546
- run number: 237
- job ID: 108039473244
- build HEAD: 80e46d162bb17ccc71b325e830607d49f625aed4
- manifest: VALID
- B73 apply: PASS
- B73 contract: PASS
- full regression chain: PASS
- iOS compile/link: PASS
- binary invariants: PASS
- package/upload: PASS
- compile requests: 151
- cache hits: 149
- cache misses: 2
- cache hit rate: 98.68%
- compilation failures: 0
- NOJAVA / MANIC3: preserved

Unsigned IPA SHA-256:

c36cfe695a0c4fc5475b197fa7a30c26036a076c277d5f9d302db4997c67ad0e

IPA artifact:
- ID: 10859887042
- ZIP digest:
  sha256:f86821fa38e874b8112592d26a37b9b39c975dd7b2bf00fd2ac7a7556bd144e
- size: 19977765 bytes
- expires: 2026-10-09

Audit artifact:
- ID: 10858947250
- ZIP digest:
  sha256:c6b6c3476785ce4acbcb4c8563babe5622874b511fe0b748ea5e411b06fe941b

## DEVICE1 instructions

Install B73 over B72.

Run the same normal Emulator boot until either:
- the same Phone start-up failed screen appears, or
- visible behavior changes.

If the same failure appears, wait 5-10 seconds and exit via the game-menu /
Emulator path.

Send:
- EKA2L1.log
- EKA2L1_Persistent.log
- EKA2L1_TakeThis.log
- Persistent-prev if produced

Video only if visible behavior differs.

Also report whether exit remains clean.

## B74 decision

First correlate:
- PHONEUI_RSC_OPEN
- PHONEUI_FS_FLOW
- PHONEUI_READ_SECTION
- PHONEUI_RSC_READ / SEEK
- CONE14_PHONEUI

If Telephone opens phoneui.r01 and then sends a specific non-read/seek opcode,
that opcode becomes the B74 target.

If the open is issued by another process, trace that process/resource
registration ownership instead.

If ReadFileSection is used, map its position against the exact RPKG index table.

If Telephone opens the file and then no FileServer request occurs before
CONE14, the failure is above EFsrv: move B74 to CONE/BAFL resource-file
registration/search logic.

Do not synthesize SIM success or suppress the critical-app panic.
