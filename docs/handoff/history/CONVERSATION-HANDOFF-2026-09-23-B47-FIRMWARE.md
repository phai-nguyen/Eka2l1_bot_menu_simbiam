# Conversation Handoff — B47 + RM-356 Firmware Research

Updated: 2026-09-23
Repository: phai-nguyen/Eka2l1_bot_menu_simbiam
Branch: nativeboot2-current

## Purpose

This snapshot exists because the current ChatGPT conversation became too long.
Use it together with `docs/handoff/CURRENT.md` to continue immediately in a
new conversation.

## Project state

B47 `NATIVEBOOT2-B47-AKNSKINTFXSTATE1` is BUILD-VALIDATED and awaiting device
test.

Canonical GREEN:
- implementation `ab4415d0f94b002d01e6ea2035600a2dddc99c1d`
- binary invariants `cc7d53ebb99f0ea754ffc432f9221586bef13fcc`
- run/job `35854365057 / 107159241200`
- unsigned IPA SHA-256
  `ae3a0b0e467c19d30277274355c3eb537fdcd75becd55f2f2e463dbca1b27885`
- artifact ID `10746604288`

B47 markers:
- AKNSKIN_TFX_STATE
- AKNSKIN_TFX_WSERV
- AKNSKIN_TFX_ECOM

B47 is diagnostic-only.

## Device baseline

B46 DEVICE1 proved:
- RM-356 device metadata route works;
- HLE AknSkinServer is skipped;
- stock guest launches native AknSkinSrv.exe;
- UID3 0x10207114;
- native !AknSkinServer registers;
- clients bind server_hle=0;
- TFX provider still does not appear.

Source-guided B47 gate:
- KCRUidThemes = 0x102818E8
- KThemesTransitionEffects = key 0x9

## Firmware archive research

Internet Archive item:
https://archive.org/details/Nokia_BB5_firmwares

Eight RM-356 ZIPs hold roughly 30 GB total. Automated ZIP browsing is currently
restricted, so exact part mapping is unresolved.

Exa/catalog evidence confirms:
- RM-356_APAC_40.0.005_v12.0.exe
- RM-356_APAC_50.0.005_v13.0.exe
- RM-356_APAC_51.0.006_v14.0.exe
- RM-356_APAC_52.0.007_v15.0.exe

A separate old firmware index also lists APAC 50.0.005 revisions v13.05 through
v13.09.

## User-downloaded control packages

From screenshots:
- RM-356_APAC_52.0.007_v15.0 (~154.4 MB)
- RM-356_EMEA_50.0.005_v13.0 (~174.3 MB)
- RM-356_EMEA_40.0.005_v12.0 (~170.3 MB)
- RM-356_EMEA_31.0.101_v9.44 (~21 MB)
- RM-356_EMEA_31.0.101_v9.45 (~113.4 MB)
- RM-356_EMEA_31.0.101_v9.46 (~92.4 MB)

Priority:
1. APAC V52 first.
2. EMEA V50.
3. EMEA V40.
4. V31 only if a deeper historical control is needed.

Do not block on locating APAC V40/V50.

## Differential targets

Extract/compare:
- private/10202BE9/102818E8.txt
- sys/bin/AknSkinSrv.exe
- sys/bin/AknSkinSrv.dll
- tfxsrvplugin.dll
- akntransitionutils.dll
- aknlistloadertfx.dll
- alfredserver*
- ALF/UI Accelerator resources
- ECom registration resources/SPI

Preferred Vietnam product codes:
0573800, 0559962, 0559676, 0591831.

## New-conversation entry point

Read:
`docs/handoff/CURRENT.md`

Then:
- analyze B47 device logs if supplied;
- otherwise analyze uploaded control firmware packages;
- only then choose B48 from evidence.
