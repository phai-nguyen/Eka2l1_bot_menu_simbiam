# RM-356 SYM.RPKG STARTER POLICY MAP

Date: 2026-09-25
Status: FIRMWARE-EXTRACTED; STARTINGCRITICALAPPS COMMAND LIST RESOLVED

## Source artifact

User-supplied RM-356 companion package:

- file: SYM.RPKG
- size: 134540934 bytes
- SHA-256: bc41496abc8d4c87de976b65cadfb922b4dfd9583a0dbcf35b7e4bff23eb008f
- format: EKA2L1 RPKG v1
- parsed Z-drive entries: 8030
- parser consumed the package exactly

The format matches EKA2L1's loader::rpkg_header/rpkg_entry implementation:
uint64 attrib, uint64 time, uint64 UTF-16 path length, path, uint64 data size,
then file bytes.

## Exact RM-356 Starter resources

Extracted directly from RPKG:

- Z:\resource\Starter_Arm.rsc
  - size 2448
  - SHA-256 d29b88c93023f201e0b647e248036049ea4fce87acdb511d3e1450b491a05d92
- Z:\resource\starter_non_critical_1.rsc
  - size 2483
  - SHA-256 4ee461045cceffb24e68df6506a6a44cc7afc4388c4af1d1f682dd9e2732e91b
- Z:\resource\starter_background_apps.rsc
  - size 464
  - SHA-256 6f9213bbdc8190ef4fe072f214e518be53160933a6d6d8232402901269e75701
- Z:\resource\starter_ui_seq.rsc
  - size 378
  - SHA-256 1b92cc5a36ee9bd5a2c905e3e0b5f1f39a1b839c1e8a5b88b3c3fd2c53ad1505

Also extracted:

- Z:\private\100059C9\ScriptInit.txt, 1504 bytes
- Z:\private\100059C9\script0.txt, 20 bytes
- Z:\private\100059C9\script1.txt, 16 bytes

script0.txt and script1.txt contain only the PLUGINS directive (plus line/BOM
formatting). They do not contain a hidden critical-app command list.

## Starter_Arm.rsc structure

The resource is a modern Symbian RSC with UID1 0x101F4A6B.

- total resource records: 59
- resource-index offset: 2328
- resources 3-12: command arrays / linked startup lists
- resources 13+: concrete EXE, APP, plugin and nested-SSCR items

The executable/app/plugin contents reconstructed from the firmware include:

- accserver.exe
- akncapserver.exe
- apsexe.exe
- calensvr.exe
- cntsrv.exe
- cfserver.exe
- dbrecovery.exe
- fbserv.exe
- hwrmserver.exe
- ailaunch.exe
- locod.exe
- mediatorserver.exe
- clknitzmdls.exe
- phoneui.exe
- profilesettingsmonitor.exe
- randsvr.exe
- eshell.exe
- splashscreen.exe
- startup.exe
- sysagt2svr.exe
- sysap.exe
- touchscreencalib.exe
- tzserver.exe
- usbwatcher.exe
- welcome2.exe
- ewsrv.exe
- locationconfigurationcontroller.exe
- startupsettings.exe
- CseSchedulerServer.exe
- pacontroller.exe

Nested SSCR resource:

- Z:\resource\starter_ui_seq.rsc

Plugin labels include reserve, init, deep, first boot, post ui, pre ui,
set palette, shutdown apps and wait phone.

## Root selector and command arrays

Resource 2 is a 13-entry selector table. Its linked command arrays are:

- RID3:  [24,20]
- RID4:  [40,32,31,34,21,51,46,17,19,22,13,26,35,38,30,15,14,33]
- RID5:  [40,21,51,22,13,36]
- RID6:  [23,39,41,28,27,45,44,29]
- RID7:  [42,18,16,29,25]
- RID8:  [41,18,16,29]
- RID9:  [38,28,23,27,45,44,39,58]
- RID10: [47,49,50]
- RID11: [39,43]
- RID12: [37]

For the observed normal RM-356 boot the selector maps the pre-101 phase to RID4
and StartingCriticalApps to RID6. This mapping is independently proven by the
device execution order below.

## B66 device correlation: RID4 -> global state 101

Device mode is normal:

[NBOOT2][SA_STARTUP_MODE] mapped=ENormal value=100

Before global state 101 the observed SYSSTART sequence follows RID4:

- sysagt2svr
- fbserv
- ewsrv
- tzserver
- cntsrv
- dbrecovery
- hwrmserver
- accserver
- mediatorserver
- splashscreen
- randsvr
- apsexe
- akncapserver

Conditional/plugin entries occur in the matching positions.

HWRMServer uses a 30000 ms wait and times out/cancels, but Starter continues.
AknCapServer rendezvous completes at 06:50:44.104.

Starter then publishes:

KPSGlobalSystemState: 100 -> 101 at 06:50:44.107.

Therefore the earlier HWRM timeout is not the active post-101 blocker.

## Exact RM-356 StartingCriticalApps list: RID6

RID6 is:

1. RID23: z:\sys\bin\ailaunch.exe
2. RID39: z:\sys\bin\startup.exe
3. RID41: z:\sys\bin\sysap.exe
4. RID28: z:\sys\bin\phoneui.exe
5. RID27: z:\sys\bin\clknitzmdls.exe
6. RID45: z:\sys\bin\touchscreencalib.exe (conditional)
7. RID44: plugin/config item (conditional/opaque)
8. RID29: z:\sys\bin\profilesettingsmonitor.exe

Immediately after state 101 the B66 device log executes this same sequence:

- ailaunch 06:50:44.108
- startup 06:50:44.110
- sysap 06:50:44.111
- phoneui 06:50:44.146
- clknitzmdls 06:50:44.156
- profilesettingsmonitor 06:50:44.158

The conditional touchscreen/plugin items do not create a visible process in
this boot.

profilesettingsmonitor is a WaitForStart-style entry with a 30000 ms timeout.
It rendezvouses successfully:

06:50:48.282
[NBOOT2][STARTER_RENDEZVOUS] phase=complete
target_process=profilesettingsmonitor
reason=0

This is the final process item in the real normal-mode RID6 command list.

## Post-RID6 transition finding

After profilesettingsmonitor successfully rendezvouses at 06:50:48.282:

- there is no further SYSSTART/StarterServer action in the log until teardown;
- no KPSGlobalSystemState write to 102 occurs;
- no SAServer EGlobalStateChange request for value 102 occurs.

The previous B64 self-test at the 101 edge is healthy:

- opcode 0x67 / EExecuteSelftests
- RM-356 response envelope written
- payload KErrNone
- completion KErrNone

Therefore the current blocker is no longer an unknown critical process or
process-rendezvous dependency.

The observed boundary is:

RID6 final WaitForStart completes
    -> Starter should advance toward SelfTestOK=102
    -> SYSSTART emits no 102 state-change request

This points to the Starter state-machine continuation / async-request wakeup
boundary after the final command list item, rather than the contents of an
additional startup EXE.

## Public state mapping cross-check

Symbian/S60 public definitions match the device values:

KPSUidStartup = 0x101F8766
KPSGlobalSystemState = 0x41

- ESwStateStartingUiServices = 100
- ESwStateStartingCriticalApps = 101
- ESwStateSelfTestOK = 102

Startup adaptation EGlobalStateChange is command 100 (0x64). B66 contains
successful state-change calls for 100 and 101 but no corresponding request for
102.

## Implication for B67

B67 STARTERSSCDUMP1 remains safe and useful as a device-side byte-for-byte VFS
verification, but it is no longer required to obtain the resource contents:
the exact Starter_Arm.rsc has now been extracted directly from the user's
matching RM-356 RPKG.

Do not force state 102 merely because the list is known.

## Recommended next diagnostic

The next narrow diagnostic should instrument the exact continuation boundary
after SYSSTART's final RID6 WaitForStart completion.

Goal:

- prove whether StarterServer is rescheduled after the
  profilesettingsmonitor rendezvous;
- trace the request status / wait object it returns to;
- identify the first branch/IPC/P&S/timer operation after that wakeup, or prove
  that the wakeup itself is lost;
- only then select a functional fix.

This should replace further broad process/rendezvous probing.
