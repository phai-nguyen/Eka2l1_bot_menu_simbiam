# NATIVEBOOT2 B72 PHONEUIRSCIO1 DEVICE1

Date: 2026-09-25
Status: DEVICE-OBSERVED; PHONEUI RSC OPEN PROVEN; ZERO B72 READ/SEEK MARKERS; CLEAN EXIT

## Inputs

- EKA2L1_Persistent(20260925-102647).log
- EKA2L1(20260925-102644).log
- EKA2L1_Persistent-prev(5).log
- EKA2L1_TakeThis(20260925-102652).log

User reports Exit Emulator returned normally.

## Startup / failure path

B72 reproduces the B71 Telephone CONE14 path.

P&S global state:
- 0 -> 100
- 100 -> 101
- 101 -> 116

Telephone[0x100058B3] self-panics:
- category CONE
- reason 14

B71 CONE14 diagnostics still fire, so B72 did not alter panic semantics.

SIM keys remain initialized/non-usable in the proven interval:
- KPSSimStatus 0x31 = 100
- KPSSimOwned 0x32 = 100
- KPSSimChanged 0x33 = 100
- VPbkSimServer later reads KPSSimStatus=100

No ESimUsable transition is observed before Telephone failure.

## PhoneUI resource-file observation

The logs show phoneui.r01 is found/opened repeatedly:

- 17:24:48.198/199:
  Z:\resource\apps\PhoneUi.r01
- 17:24:50.803/804:
  z:\resource\apps\phoneui.r01
- 17:24:52.571:
  z:\resource\apps\phoneui.r01
- 17:24:53.937/938:
  z:\resource\apps\phoneui.r01

The final open returns handle 1114122.

Telephone CONE14 occurs at 17:24:53.939, approximately 1 ms after that final
phoneui.r01 open.

However:
- [NBOOT2][PHONEUI_RSC_READ] count = 0
- [NBOOT2][PHONEUI_RSC_SEEK] count = 0

Therefore no Telephone + exact-path execution reached the instrumented
fs_server_client::file_read() or file_seek() paths.

This rules out B72's expected simple model of:
open -> RFile read/seek resource record -> CONE14.

The next possibilities are:
1. the opens are issued by another process/session rather than Telephone;
2. BAFL/CONE uses another FileServer opcode such as ReadFileSection;
3. ROM-backed resource path via IsFileInRom bypasses RFile read/seek;
4. CONE fails in resource-file registration/search ownership before record I/O.

## Strong timing boundary

The last visible sequence is:

17:24:53.937  Get entry phoneui.r01
17:24:53.938  Opening phoneui.r01 raw mode 1
17:24:53.938  Handle opened 1114122
17:24:53.939  Telephone self-panic CONE14

There are no Unknown FSServer client opcodes in this interval.

## Exit Emulator

Exit remains clean for a second consecutive build after the B70 crash:

Persistent-prev / TakeThis:
- shutdown_threads_done
- shutdown_done
- normal_restart_begin

new log:
- normal_restart_done has_device=1

No host crash / ipc_msg::~ipc_msg() recurrence.

Do not apply teardown fix while this remains non-reproducible.

## Selected B73

B73 PHONEUIFSFLOW1 should trace:
- which process opens phoneui.r01 and returned handle;
- every FileServer request from Telephone (raw + translated opcode);
- arg3 file-handle path resolution;
- ReadFileSection against phoneui.r01;
- IsFileInRom result / rom_address for Telephone + phoneui.r01.

This will distinguish FileServer alternate path from CONE registration/search
failure without changing resource/SIM/startup behavior.
