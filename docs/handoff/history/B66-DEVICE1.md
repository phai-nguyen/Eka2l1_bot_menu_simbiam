# NATIVEBOOT2 B66 STARTERSCRIPTDUMP1 DEVICE1

Date: 2026-09-25
Status: DEVICE-OBSERVED; SCRIPT CAPTURE SUCCESS; TEXT SCRIPTS RULED OUT AS THE 101 -> 102 POLICY SOURCE

## Evidence set

Device supplied:

- EKA2L1(20260925-000613).log
- EKA2L1_Persistent(20260925-000616).log
- EKA2L1_TakeThis(20260925-000614).log

Persistent and TakeThis contain the same B66 boot evidence.

## Global Starter state

B62 tracing remains stable:

- 06:50:11.251: SYSSTART / StarterServer writes 0 -> 100
- 06:50:44.107: SYSSTART / StarterServer writes 100 -> 101
- no later global-state write is observed
- AknCapServer, Startup and Home screen subsequently read value 101

Therefore B66 does not change the established blocker: Starter remains at
ESwStateStartingCriticalApps = 101.

## B64 self-test preservation

At the exact 100 -> 101 edge B64 remains healthy:

- SAServer function 0x67
- RM-356 response template copied successfully
- TInt payload = KErrNone
- RMessage completion = KErrNone

The B63 FatalStartupError=117 path does not return. Self-test transport is not
the active blocker.

## B66 script capture

[NBOOT2][STARTER_SCRIPT_DUMP] fires 42 times.

Complete successful captures include:

- Z:\private\100059C9\ScriptInit.txt
  - raw size 1504 bytes
  - captured 1504
  - truncated=false
- C:\private\100059C9\plg_script1.txt
  - raw size 138 bytes
- C:\private\100059C9\plg_script2.txt
  - raw size 200 bytes
- C:\private\100059C9\plg_script3.txt
  - raw size 1016 bytes
- C:\private\100059C9\plg_script4.txt
  - raw size 156 bytes

The early open_fail events for plg_script1..4 occur before those generated files
exist. Later opens capture them successfully. plg_script5 remains absent.

Neither Z:\private\100059C9\script0.txt nor script1.txt is opened during this
boot.

## Meaning of the captured text files

The captured contents are file-system initialisation scripts, not the ordered
Starter critical-state policy.

Observed command families are MD/CD/CP and include:

- copying Metadata Engine schema/backup files from Z: to C:
- copying BrowserBookmarks.db
- copying certificate databases
- creating media directories on root/mass-storage drives
- creating Wap/Cbs/System\Temp on the RAM drive

No captured B66 text script contains the critical-app state machine needed to
explain why Starter remains at 101.

## Critical new observation

General EFsrv tracing shows SYSSTART opens:

Z:\resource\starter_arm.RSC

at 06:50:10.709, before global state 100 is published.

This is the RM-356 ROM Starter resource and is the correct next policy artifact
to capture. Symbian System Starter's Static Startup Configuration is represented
as a ROM resource containing the startup states/commands; therefore this
resource is materially closer to the 101 -> 102 boundary than the B66 first-run
text scripts.

## Teardown

B61 remains healthy:

- [NBOOT2][GSTORE_WIPEOUT_GUARD] fires 27 times
- shutdown_done is reached
- Persistent log reaches normal_restart_done has_device=1

No B66 teardown regression is established.

## Decision

Do not modify HWRM, profilesettingsmonitor, B64 self-test, Startup private
state, or global state based on B66.

Selected next diagnostic:

B67 STARTERSSCDUMP1

It must capture exact Z:\resource\starter_arm.RSC bytes through a separate
read-only VFS handle and emit them as unambiguous hex. It must not alter the
guest file cursor, P&S, IPC completion, rendezvous, process behavior, graphics,
or teardown.

Primary B67 acceptance:

- [NBOOT2][STARTER_SSC_DUMP] begin/data/end all present
- captured == raw_size
- truncated=false

After device capture, reconstruct starter_arm.RSC byte-for-byte and decode its
SSC commands around StartingCriticalApps=101 before selecting any functional
B68 change.
