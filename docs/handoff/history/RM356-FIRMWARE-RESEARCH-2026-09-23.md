# RM-356 firmware research checkpoint — 2026-09-23

Status: RESEARCH CHECKPOINT ONLY — no B47 runtime semantics changed.

## Why this checkpoint exists

B46 proved the stock RM-356 guest launches native AknSkinSrv and registers
`!AknSkinServer`. B47 is build-validated and is waiting for device evidence
around the Themes CenRep / WindowServer / ECom boundary.

This checkpoint records external firmware/catalog evidence that can classify
B47 without inventing a B48 behavior.

## Internet Archive package set

Internet Archive item:
https://archive.org/details/Nokia_BB5_firmwares

The indexed directory listing exposes the Nokia 5800 set as:

- `5800 RM-356_part1.zip` — ~4.0 GB
- `5800 RM-356_part2.zip` — ~4.0 GB
- `5800 RM-356_part3.zip` — ~4.0 GB
- `5800 RM-356_part4.zip` — ~4.0 GB
- `5800 RM-356_part5.zip` — ~4.1 GB
- `5800 RM-356_part6.zip` — ~4.1 GB
- `5800 RM-356_part7.zip` — ~4.0 GB
- `5800 RM-356_part8.zip` — ~1.5 GB

The archive-internal directory view currently returns HTTP 403 to automated
fetches, so the exact mapping of an individual Nokia installer package to
part1..part8 remains unproven.

Do not download all ~30 GB solely to resolve that mapping.

## Confirmed RM-356 package names

Old Nokia firmware catalogs independently list:

- `RM-356_APAC_40.0.005_v12.0.exe`
- `RM-356_APAC_50.0.005_v13.0.exe`
- `RM-356_APAC_51.0.006_v14.0.exe`
- `RM-356_EMEA_40.0.005_v12.0.exe`
- multiple EMEA V50/V51 revisions
- `RM-356_EMEA_52.0.007_v15.0.exe`

Source:
http://bb5firmware.blogspot.com/2011/04/5800-xpressmusic-rm-356.html

A CycloneBox support-server release log records, on 3 Dec 2010:

- `RM-356_APAC_52.0.007_v15.0.exe`
- `RM-356_EMEA_52.0.007_v15.0.exe`
- `RM-356_MENA_52.0.007_v15.0.exe`
- `RM-356_LTA_52.0.007_v15.0.exe`

The same thread records earlier APAC revisions including:

- `RM-356_APAC_50.0.005_v13.08.exe`
- `RM-356_APAC_50.0.005_v13.09.exe`
- `RM-356_APAC_51.0.006_v14.01.exe`
- `RM-356_APAC_51.0.006_v14.02.exe`
- `RM-356_APAC_51.0.006_v14.03.exe`

Source:
https://forum.gsmhosting.com/vbb/f528/cyclonebox-support-server-news-info-request-1126066-print/?pp=50

Conclusion:
APAC V40/V50/V51/V52 are real package families. The already-downloaded
`RM-356_APAC_52.0.007_v15.0` is a valid control and should not be blocked on
finding the base V40/V50 archive part first.

## Vietnam product-code mapping

Historical RM-356 product-code lists consistently map:

- `0573800` = Vietnam Black
- `0559962` = Vietnam Blue
- `0559676` = Vietnam Red
- `0591831` = Vietnam Gun and Black

Sources:
https://nokiaport.de/forum/thread-5903.html
https://www.hardreset.info/devices/nokia/nokia-5800-navigation-edition/product-codes/

V50-specific lists also include the same Vietnam codes, including
`0591831 VIETNAM GUN and BLACK 50.0.005`.

Source:
https://fony.sk/comment/195645

## Themes CenRep key 0x9 — critical B47 interpretation

Multiple Symbian firmware-modding references identify:

`private\\10202BE9\\102818E8.txt`

as the Themes settings repository and key `0x9` as the theme-effects control.

Observed community conventions:

- `0x7FFFFFFF` = theme effects disabled
- `0x8` = theme effects enabled by default
- one S60v5 reference describes `0` as automatic

Sources:
https://dimonvideo.ru/forum/topic_1728146654
https://gsm.vn/archive/threads/tong-hop-cac-mod-cook-app-cho-s60v3-fp2-18-08-2011.258288/
https://bbs.ihei5.com/forum.php/forum.php?extra=page%3D1&mobile=no&mod=viewthread&tid=35611

This is directly consistent with the source-level AknSkin logic already in the
project:

- `TransitionFxState()` returns `KMaxTInt` on missing/error.
- `StartTransitionSrvL()` does not load the TFX provider when the state is
  `KMaxTInt`.

Therefore B47 device classification should be:

1. If repo `0x102818E8`, key `0x9` returns an error or `0x7FFFFFFF`
   (`KMaxTInt`), absence of TFX ECom/ALF/TfxServer is firmware-selected
   behavior. Do not synthesize a provider.
2. If the key returns a non-KMaxTInt value such as `0x8` or `0`, the next
   required evidence is the native AknSkinSrv WindowServer connection and then
   ECom traffic for `0x10282DBD` / `0x10282DBC`.

## Preferred control-firmware extraction

Highest priority from the already-downloaded APAC V52 package:

- `private\\10202BE9\\102818E8.txt`
- `sys\\bin\\AknSkinSrv.exe`
- `sys\\bin\\AknSkinSrv.dll`
- `tfxsrvplugin.dll`
- `akntransitionutils.dll`
- `aknlistloadertfx.dll`
- `alfredserver*`
- ALF/UI Accelerator resources
- ECom registration resources / SPI
- package VPL for product-code/version mapping

EMEA V50/V40 remain useful controls for common system binaries and
TFX/ALF/ECom components.

## Next project action

Priority remains unchanged:

- analyze B47 device logs first when available;
- otherwise extract APAC V52 and compare `102818E8.txt` key `0x9` plus the
  TFX/ALF/ECom component set against the current V60 firmware;
- do not select B48 until the first missing stage is device-proven.
