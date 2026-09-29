# C6-00 CONTROL FIRMWARE COMPARISON PLAN

Date: 2026-09-25
Project: EKA2L1 NATIVEBOOT2
Primary target: Nokia 5800 XM RM-356 v60.0.003
Control target: Nokia C6-00 S60 5th Edition / Symbian OS 9.4
Status: READY FOR FIRMWARE INPUT

## Why C6-00 is useful

Nokia 5800 XM and Nokia C6-00 both belong to the S60 5th Edition / Symbian OS
9.4 generation.  That makes the C6-00 firmware useful as a control image for
system-layer boot behavior.

The control image is NOT used to assume identical binary addresses.
Build/product differences can move code and change feature variants.

The useful comparison axes are semantic:
- binary identity / UID / capability surface;
- import/export and EABI ordinal surface;
- startup process ordering;
- Startup P&S states;
- Starter/SysStart/SysAp interactions;
- PhoneUI resource registration sequence;
- resource IDs and signature bases;
- language-resource selection;
- code-byte signatures of specific routines;
- server/session/rendezvous ordering.

## Existing RM-356 blocker to validate against C6-00

Current 5800 path reaches:
- Telephone UID3 0x100058B3;
- PhoneUIUtils.dll;
- phoneui.r01 resource processing;
- CONE 14;
- requested resource 0x1099B02D;
- resource owner callhandlingui.r01.

Observed on RM-356:
- phoneui.r01 opens;
- callhandlingui.r01 exists;
- callhandlingui.r01 is not observed being opened/registered before CONE14;
- CPhoneResourceResolverBase::BaseConstructL export ordinal 182 resolves;
- BaseConstructL is not present in the captured failing stack windows.

Public Symbian PhoneUI source defines BaseConstructL to register:
1. phoneui
2. callhandlingui
3. phoneuitouch

Therefore the C6-00 control firmware can answer whether the Nokia production
S60v5 binary follows the same practical initialization shape.

## Comparison layers

### L0 — image/platform identity

Record:
- RM number;
- firmware version;
- core/ROFS filenames;
- ROM EPOC version;
- language pack;
- product code if present.

Do not compare raw image offsets.

### L1 — kernel and base servers

Compare presence / metadata / code signatures for:
- euser.dll
- ekern.exe / kernel image metadata if extractable
- fileserver
- loader
- ws32
- font/bitmap server surface
- cone.dll
- eikcore/eikon surface
- apparc/application architecture surface

Goal:
separate generic EKA2/S60v5 dependencies from RM-356-specific behavior.

### L2 — system startup

Compare:
- SysStart / Starter binaries;
- startup properties and scripts;
- State Manager / startup services;
- SAServer / startup adaptation services;
- SysAp;
- Alarm/charging/normal-state branches;
- startup P&S category/key transitions;
- rendezvous ordering and wait conditions.

Goal:
derive a semantic startup chain for each device and diff the chains.

### L3 — telephony / Phone application

Compare:
- Telephone executable UID3 and dependencies;
- PhoneUIUtils.dll;
- Phone UI state/factory DLLs;
- telephony variant libraries;
- relevant CenRep repositories and feature flags.

For PhoneUIUtils specifically:
- export count;
- ordinal 181;
- ordinal 182 BaseConstructL;
- ordinal 307 ResolveResourceID;
- ordinal 308 IsTelephonyFeatureSupported;
- normalized function-byte signatures;
- callers/callees around BaseConstructL and resource setup.

Goal:
determine whether RM-356 is missing a call/registration step that exists in a
normal sibling S60v5 firmware.

### L4 — resource layer

Compare:
- Z:\resource\apps\phoneui.rXX
- Z:\resource\apps\callhandlingui.rXX
- Z:\resource\apps\phoneuitouch.rXX
- corresponding .rsc/.r01/.r96 variants
- resource signature bases
- resource count / offset table
- ID 0x1099B02D ownership
- nearest-language selection behavior

Goal:
prove whether 0x1099B02D is structurally identical across devices and whether
the resource is registered through the same resolver path.

### L5 — runtime boot traces

If C6-00 can later be installed/dumped in EKA2L1, collect the same markers as
RM-356:
- process creation/order;
- Starter/SAServer/P&S transitions;
- FileServer resource-open order;
- PhoneUIUtils call-chain edges;
- CONE/Eikon panics;
- first home-screen process and window-group creation.

Goal:
produce a side-by-side timeline:
C6-00 control vs RM-356 target.

## Strong comparison rules

1. Do not compare absolute runtime addresses between devices.
2. Compare normalized module offsets only after mapping exact binary build.
3. Prefer export ordinals and function byte signatures over guessed symbols.
4. Treat nearest-export ownership as a range label, not proof of function
   identity.
5. Resource IDs may be stable while localized resource-file suffixes differ.
6. Product feature flags can legitimately alter branches.
7. A difference is actionable only when it occurs before the first divergent
   startup/result state.

## Minimum firmware input

Best input:
- C6-00 SYM.ROM
- C6-00 SYM.RPKG

Alternative:
- complete C6-00 Nokia firmware package containing core + ROFS files.

Known C6-00 product families include RM-612 and RM-624.  The exact RM and
firmware version must be detected from the supplied package rather than
assumed.

For standard Nokia firmware packages, useful files typically include:
- *_prd.core.*
- *_prd.rofs2.*
- *_prd.rofs3.*
- *.uda.fpsx
- .vpl / .dcp / signature metadata

For system comparison, CORE + ROFS are the important pieces; UDA is secondary.

## First extraction target set

Once the C6 firmware is available, extract or locate these first:

System:
- Z:\sys\bin\sysstart.exe if present
- Z:\sys\bin\starter.exe if present
- Z:\sys\bin\sysap.exe
- Z:\sys\bin\cone.dll
- Z:\sys\bin\eikcore.dll / Eikon equivalents
- Z:\sys\bin\phoneuiutils.dll
- Telephone / Phone executable and Phone UI state/factory DLLs
- startup adaptation/server binaries seen in the image

Resources:
- Z:\resource\apps\phoneui.*
- Z:\resource\apps\callhandlingui.*
- Z:\resource\apps\phoneuitouch.*
- SysAp/startup resources
- Starter/startup scripts/resources

Configuration:
- startup P&S / CenRep data involved in normal/offline/SIM paths
- telephony variation repositories where extractable

## First deliverables after firmware upload

1. C6 firmware identity report.
2. C6 vs 5800 boot-surface file matrix:
   SAME / DIFFERENT / C6-ONLY / 5800-ONLY.
3. PhoneUIUtils export comparison.
4. Resource-ID comparison for 0x1099B02D.
5. Normalized BaseConstructL code comparison.
6. Startup-chain diff:
   kernel/base servers -> Starter/SysStart -> SysAp -> Telephone/PhoneUI -> Home.
7. B80/B81 decision:
   whether C6 supplies enough evidence for a functional RM-356 fix or whether
   another runtime probe is still needed.

## Relationship to B79

B79 remains the immediate RM-356 runtime experiment.

C6-00 comparison is a parallel evidence source, not a replacement for B79.

When B79 DEVICE1 arrives, correlate:
- +0x4274
- +0x41AC
- +0x4350
- +0x3A28
- +0x3B2E

against normalized PhoneUIUtils code signatures in the C6 control firmware.

If a C6 routine with equivalent code performs resource registration before
Telephone continues, that becomes strong evidence for the missing RM-356
boundary.
