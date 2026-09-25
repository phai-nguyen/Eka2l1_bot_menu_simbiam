# RM-356 NORMAL BOOT WITH SIM PRESENT — ROM/RPKG MAP

Date: 2026-09-25
Status: FIRMWARE/POLICY MAP; USED TO INTERPRET B69

## Sources

Actual user firmware artifacts:
- SYM.ROM: RM-356 XIP system binaries
- SYM.RPKG: matching Z-drive package
- RPKG SHA-256:
  bc41496abc8d4c87de976b65cadfb922b4dfd9583a0dbcf35b7e4bff23eb008f

Authoritative RM-356 firmware components observed in ROM:
- sysstart.exe, UID3/SID 0x100059C9
- startup.exe, UID3/SID 0x100058F4
- StartupAdaptation.DLL
- SAStartupService.DLL
- starterclient.dll

Actual RPKG Starter policy:
- Z:\resource\Starter_Arm.rsc
- Z:\resource\starter_ui_seq.rsc
- Z:\resource\starter_background_apps.rsc
- Z:\resource\starter_non_critical_1.rsc

Reference semantics cross-checked against Symbian/Nokia headers:
- startupadaptationcommands.h
- startupdomainpskeys.h
- simutils.h
- cmdsimsecuritycheck.cpp
- ssmstartuppolicy.cpp

## Startup mode

RM-356 B69 device path reports:

EGetGlobalStartupMode -> ENormal = 100

For Starter_Arm.rsc the actual normal-mode command arrays seen on device are:

- pre-critical / state 100 phase: RID4
- StartingCriticalApps / state 101 phase: RID6

Other selector alternatives correspond to non-normal startup modes such as
Alarm, Charging and Test; they are not the normal SIM-present route.

## Normal boot state path with a usable SIM

Expected global-state sequence:

100 StartingUiServices
  -> 101 StartingCriticalApps
  -> 102 SelfTestOK
  -> 103 SecurityCheck
  -> 104 CriticalPhaseOK
  -> 109 NormalRfOn

If the user/device policy selects offline mode after the security phase, the
terminal state is 110 NormalRfOff instead of 109 NormalRfOn.

The adaptation and P&S state enums agree on these values through 115.

## State 100 — StartingUiServices / RID4

The actual RM-356 RID4 list contains the early critical services and plugins.
Observed/decoded items include:

- sysagt2svr.exe
- first-boot/deep/pre-ui plugins
- fbserv.exe
- ewsrv.exe -NoShell
- tzserver.exe
- cntsrv.exe
- dbrecovery.exe
- hwrmserver.exe
- accserver.exe
- mediatorserver.exe
- splashscreen.exe
- randsvr.exe
- apsexe.exe
- akncapserver.exe
- set-palette/post-ui plugins

B66/B68 device execution matches this list.

When this phase completes, SYSSTART publishes state 101.

## State 101 — StartingCriticalApps / RID6

Actual RM-356 RID6:

1. ailaunch.exe
2. startup.exe
3. sysap.exe
4. phoneui.exe
5. clknitzmdls.exe
6. touchscreencalib.exe (conditional)
7. conditional/plugin item
8. profilesettingsmonitor.exe

The final profilesettingsmonitor WaitForStart rendezvous completes reason 0 on
device. B68 proves StarterServer is then correctly signalled, rescheduled and
continues guest execution.

Self-tests are requested through:
- StartupAdaptation::EExecuteSelftests = 103 / SAServer opcode 0x67

B64 implements the proven RM-356 response envelope and completes KErrNone.

The intended next global state is 102 SelfTestOK.

## State 102 — SelfTestOK

For a NORMAL boot, the documented allowed transition is:

102 SelfTestOK -> 103 SecurityCheck

Alarm/Charging/Test boot modes may branch from 102 to their own terminal paths,
but the current device reports ENormal=100, so those are not the intended path.

## State 103 — SecurityCheck with SIM present

The SIM/security state machine begins from:

StartupAdaptation::ESIMPresent = 100

For a real present, valid SIM the successful path is conceptually:

ESIMPresent
  -> ESIMReadable
  -> SIM rejected/blocked/PIN checks
  -> EPINRequired
     -> if PIN required: EAskPIN -> accepted
     -> if PIN not required: continue directly
  -> ESIMCodesOK
  -> ESIMLock
  -> SIM becomes usable
  -> ESecurityCheckOK

Relevant SIM P&S:

KPSUidStartup = 0x101F8766

KPSSimStatus = 0x31
- 100 Uninitialized
- 101 ESimUsable
- 102 ESimReadable
- 103 ESimNotReady
- 104 ESimNotPresent
- 105 ESimNotSupported

KPSSimOwned = 0x32
- 100 Uninitialized
- 101 ESimOwned
- 102 ESimNotOwned

KPSSimChanged = 0x33
- 100 Uninitialized
- 101 ESimChanged
- 102 ESimNotChanged

For a valid inserted SIM, the decisive status for leaving the successful SIM
security path is KPSSimStatus=101 / ESimUsable.

If SIM security fails, the policy can route to EmergencyCallsOnly instead of
CriticalPhaseOK.

## State 104 — CriticalPhaseOK

With the SIM present, Startup Adaptation has dedicated queries:

- EGetSimChanged = 108 / 0x6C
- EGetSimOwned = 109 / 0x6D

The API explicitly specifies these queries are made only when a SIM is present
and in CriticalPhaseOK.

The actual RM-356 SAStartupService.DLL contains:
- CSASStartupGetSimOwned
- CSASStartupGetSimChanged
- CSASStartupHandleSimIndications
- CSASStartupSecurityStateChange
- CSASStartupGS_CriticalPhaseOK_NormalRfOn

This directly matches the normal present-SIM path.

## Terminal normal state

For normal online boot:

104 CriticalPhaseOK -> 109 NormalRfOn

For normal offline selection:

104 CriticalPhaseOK -> 110 NormalRfOff

NormalRfOn is the expected endpoint before/while the remaining UI and
non-critical startup workload is released.

## Post-critical UI / non-critical firmware lists

The RPKG contains nested real Nokia policy resources.

starter_ui_seq.rsc includes:
- starter_background_apps.rsc
- enable-apps-key plugin
- enable-global-notes plugin
- startup sync plugins
- swidaemon.exe

starter_background_apps.rsc includes:
- clockapp.exe
- iaupdatebg.exe
- logs.exe
- mce.exe
- phonebook2.exe
- CseSchedulerServer.exe
- cctautosync.exe

starter_non_critical_1.rsc includes, among others:
- alwaysonlinestarter.exe
- autolock.exe
- calensvr.exe
- cbsserver.exe
- cfserver.exe
- dataconnectionlogger.exe
- menu3.exe
- ncnlist.exe
- satserver.exe
- schexe.exe
- sipprofilesrv.exe
- systemams.exe -boot
- usbwatcher.exe
- watcher.exe
- xnthemeserver.exe
- locationconfigurationcontroller.exe
- startupsettings.exe
- CseSchedulerServer.exe
- harvesterserver.exe
- mediabar.exe
- popupclock.exe

These resources describe the later path toward the usable S60 UI after the
critical/security phase succeeds.

## Correct dual-enum shutdown mapping

Do not mix the two 116/117 layouts.

StartupAdaptation::TGlobalState, passed to EGlobalStateChange / opcode 0x64:
- 116 = ShuttingDown
- 117 = FatalStartupError

TPSGlobalSystemState, published through 0x101F8766:0x41:
- 116 = FatalStartupError
- 117 = ShuttingDown

They represent the same semantic states with the last two numeric values
reversed.

## B69 deviation from the intended SIM-present path

B69 currently follows:

ENormal
  -> state 100 / RID4
  -> state 101 / RID6
  -> EExecuteSelftests KErrNone
  -> Alarm ID-list 0x0B KErrNone
  -> Alarm ID-list 0x0C KErrNone
  -> async request status 0x007008D4 completes KErrNone
  -> StartupAdaptation EGlobalStateChange input 116 = ShuttingDown
  -> P&S global state 117 = ShuttingDown

Therefore B69 NEVER reaches:
- state 102 SelfTestOK publication
- state 103 SecurityCheck
- ESIMPresent / SIM security state machine
- KPSSimStatus=ESimUsable
- state 104 CriticalPhaseOK
- EGetSimChanged / EGetSimOwned
- state 109 NormalRfOn

This is the key comparison: the emulator is currently leaving the normal
SIM-present path before SIM security is even entered.

## Next diagnostic implication

The next diagnostic should identify why the completion associated with
request status 0x007008D4 makes SYSSTART select ShuttingDown while still in
StartingCriticalApps.

B70 should trace:
- the exact creator/owner of request status 0x007008D4;
- server/session/opcode or timer source;
- full IPC descriptor ABI and output payload;
- whether this request is a shutdown/power-event/startup-policy notifier;
- all reads/writes of KPSUidStartup SIM keys 0x31/0x32/0x33;
- all SAServer commands 0x65/0x66/0x68/0x6C/0x6D;
- the exact branch immediately before EGlobalStateChange(116 ShuttingDown).

Do not fake ESimUsable, do not force state 102, and do not suppress shutdown
until its origin is proven.
