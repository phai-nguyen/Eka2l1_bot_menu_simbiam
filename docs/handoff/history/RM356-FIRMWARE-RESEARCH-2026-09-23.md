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


## Reproducible firmware probe added

Tool:
`tools/rm356_firmware_probe.py`

Test:
`test_rm356_firmware_probe.py`

Implementation commits:
- initial probe: `37c2045010424497f688bbb32ecdb1089ed8bc3f`
- initial tests: `3cfe14578674b0c3416743bdd5180fabd2460aed`
- BOM-less UTF-16 CenRep fix: `5f8d6ccecc6cbdba5d3c0dd04eb699120d8e099b`
- UTF-16 regression test: `58dcd1bbcb5ebff36837f06e0c2b803fb1d8df39`

The probe accepts extracted firmware roots in `LABEL=/path` form and reports:
- `private/10202BE9/102818E8.txt` key `0x9` value/classification;
- SHA-256 and size for AknSkinSrv, TFX transition libraries and matching ALF files;
- ECom paths containing `10282DBD` / `10282DBC`;
- per-component presence and hash equality across firmware trees.

Synthetic validation passed for:
- UTF-8 CenRep text;
- UTF-16LE without BOM;
- UTF-16BE without BOM;
- key `0x7FFFFFFF` / `0x8` classification;
- identical/different AknSkinSrv SHA-256 comparison.

This tool is diagnostic/research-only and changes no EKA2L1 runtime behavior.


## V60 device-pair authority confirmed — 2026-09-23

The user supplied the exact `SYM.ROM` currently paired with the previously
stored `SYM.RPKG` for device testing.

### Exact V60 identity from RPKG

The RPKG version resources report:

- `resource\\versions\\sw.txt`:
  `V 60.0.003 / 22-09-2011 / RM-356`
- `resource\\versions\\product.txt`:
  `Manufacturer=Nokia`, `Model=5800 XpressMusic`, `Product=RM-356`
- `resource\\versions\\platform.txt`:
  `SymbianOSMajorVersion=9`, `SymbianOSMinorVersion=4`
- `resource\\versions\\fwid1.txt`:
  `id=core`, `version=RM-356_60.0.003`
- `resource\\versions\\customersw.txt`:
  `60.0.003.C04.01 / 22-09-2011`

RPKG raw size:
`134,540,934` bytes.

RPKG SHA-256:
`bc41496abc8d4c87de976b65cadfb922b4dfd9583a0dbcf35b7e4bff23eb008f`.

### Exact V60 Themes gate

The real V60 RPKG contains:

`Z:\\private\\10202BE9\\102818E8.txt`

SHA-256:
`4aafb9dc1113a89a6ec3febb861d8e719ea936c050cfdfc0cedebb6838fb69fc`.

Its exact key is:

`0x9 int 0x7fffffff 16777216 cap_rd=alwayspass cap_wr=WriteDeviceData`

This is direct firmware evidence, not web inference. It matches the B47
source-level `KMaxTInt` suppression branch.

### Exact ECom UID presence

`Z:\\private\\10009d8f\\ecom-0-0.spi` contains both UIDs exactly once:

- `0x10282DBC`
- `0x10282DBD`

Therefore the stock V60 firmware contains the ECom registrations even though
the Themes key suppresses the transition-provider startup path.

### Exact uploaded V60 ROM

The corrected device-test `SYM.ROM` is:

- size: `41,283,584` bytes
- SHA-256:
  `b4328dfa555d73e14a4bab2de46bbec702970e4b63c8ce878da589fa6b64c444`
- ROM base: `0x80000000`
- declared ROM size: `0x02800000` (40 MiB)

The burn tree parses successfully and contains 2,161 file entries.

The ROM itself contains these B47-relevant core binaries:

- `aknlistloadertfx.dll`
- `aknskinsrv.dll`
- `aknskinsrv.exe`
- `akntransitionutils.dll`
- `TfxSrvPlugin.dll`
- `tfxserverclient.dll`
- `tfxserver.dll`
- `tfxserveranim.dll`

For all eight files, ROM size and SHA-256 are byte-identical to the copy in
the paired RPKG.

Important layout distinction:
the CenRep repository, ECom SPI and ALF/Alfred components are supplied by the
RPKG/ROFS side, while the ROM confirms the core AknSkin/TFX binaries.

### B47 consequence

The V60 device pair now proves simultaneously:

1. TFX binaries are present.
2. TFX ECom registrations are present.
3. Themes key `0x102818E8:0x9` is `0x7FFFFFFF == KMaxTInt`.

Therefore, if B47 device tracing reports the same value/result, the absence of
native AknSkinSrv -> WindowServer/ECom/ALF/TfxServer startup is the expected
stock-firmware branch. Do not synthesize a provider and do not choose a B48
TFX-enablement workaround from firmware presence alone.

The next runtime decision still requires the B47 device log to verify that
EKA2L1 CenRep returns this exact stock value to native AknSkinSrv.
