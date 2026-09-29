# B48 XNTHEMEPOST1 — BUILD SNAPSHOT

Date: 2026-09-23  
Status: BUILD-VALIDATED; DEVICE TEST REQUIRED

## Why B48 exists

B47 closed the AknSkin/TFX hypothesis on the real RM-356 V60 firmware:
native AknSkinSrv reads Themes CenRep `0x102818E8:0x9` successfully as
`0x7FFFFFFF/KMaxTInt`, matching stock firmware and intentionally suppressing
TFX provider startup.

The first post-B47 activity worth classifying is the native Home screen ->
`xnthemeserver` theme path. B47 device logs show xnthemeserver launches,
registers and remains alive, but repeated trapped `Leave(-5)` events occur
near historical FileServer `0x27` observations.

Source authority resolves `0x27` unambiguously:
`src/emu/services/include/services/fs/op.h` maps decimal 39 / hex 0x27 to
`fs_msg_file_flush`.

Correlation is not enough to claim FileFlush returns -5, so B48 is
diagnostic-only.

## New markers

### `[NBOOT2][XNTHEME_IPC]`

Two phases:

- `phase=send`: every native-phone-boot IPC sent to server
  `xnthemeserver`, including process UID3, thread, function/opcode, sync
  mode, status address, argument flags and raw argument words.
- `phase=complete`: every completion made by native
  `xnthemeserver[10207254]`, including client process/UID3/thread,
  function/opcode, exact completion result, message ID and request status.

Unlike the older MENUUI12 probe, the completion probe is not limited to the
old Menu client UID, so Home screen traffic is visible.

### `[NBOOT2][XNTHEME_FSFLUSH]`

For FileServer `FileFlush` requests made by xnthemeserver UID3
`0x10207254`, B48 records:

- handle;
- resolved file path;
- `flush_ok`;
- the exact existing completion result.

The VFS flush is still called exactly once.

## Semantic guard

B48 does not:

- change xnthemeserver IPC function/arguments/result;
- rewrite `message_complete` value;
- change FileServer FileFlush completion semantics;
- restore the obsolete FS directory/UID bug;
- modify CenRep;
- enable TFX;
- fake TfxServer/ECom/ALF;
- alter WindowServer behavior.

MENUUI13 FS-DIRUID1 remains preserved.

B47 stock-TFX suppression remains preserved.

FileFlush still has exactly the original result classes:

- bad handle -> `KErrBadHandle`;
- VFS flush failure -> `KErrGeneral`;
- success -> `KErrNone`.

## Build chronology

Initial implementation commit:

`c47a3ca4a81836a0d2c500ff618d176756943c41`

Initial run:

`35879300163`

It failed before compilation because the B48 apply-script baseline guard looked
for `[NBOOT2][AKNSKIN_TFX_STATE]` in `svc.cpp`. B47 actually places that
marker in `centralrepo/repo.cpp`. This was a diagnostic contract-location
error, not a runtime or compile failure.

Correction commits:

- `650fe61bf88292dff23b0781bfd7a3a5dabac194`
- `174e00388a0aef1a02e07bb44b55b5f0488ca75e`

Canonical GREEN:

- run: `35879560705`
- job: `107244189576`
- build HEAD: `174e00388a0aef1a02e07bb44b55b5f0488ca75e`
- FASTBUILD1 manifest: VALID
- B29-B48 apply/tests: PASS
- B20-B28 regressions: PASS
- iOS build: PASS
- binary invariants: PASS
- package/upload: PASS
- compile requests: 149
- cache hits: 147
- cache misses: 2
- hit rate: 98.66%
- actual compilations: 2
- compilation failures: 0
- NOJAVA: PRESERVED
- MANIC3: PRESERVED

FASTBUILD timing:

- bootstrap source: B28_CACHE
- bootstrap restore: 57 s
- patch/regression: 3 s
- CMake build: 137 s
- package: 2 s
- total: 231 s

## IPA

Unsigned IPA SHA-256:

`4b5c59119ceb5940cdefca8c52a3bd7545861511896659b3302c38e44b504a32`

Extracted IPA size:

`19,977,357` bytes

GitHub IPA artifact:

- ID: `10759779669`
- ZIP size: `19,916,084` bytes
- ZIP digest:
  `sha256:f98d14ddb4f8f9b6b350d91d70ef9194717acc0382e6955d75897c196ec34c24`
- expires: 2026-10-07

Audit artifact:

- ID: `10759379488`
- ZIP digest:
  `sha256:03bc38b5504014e0a70215b3ea998718670152e6144784a429ac44da8f3169a7`

## Device-test acceptance

Use the same RM-356 V60 `SYM.ROM + SYM.RPKG` pair used for B47 and send the
same three logs.

Primary decision tree:

```
Home screen / theme client
 -> XNTHEME_IPC phase=send
 -> xnthemeserver native handling
 -> XNTHEME_FSFLUSH enter/result if FileFlush occurs
 -> XNTHEME_IPC phase=complete exact result
```

Classification:

1. If `XNTHEME_FSFLUSH` shows `flush_ok=1 completion=0`, FileFlush is not
   the source of `Leave(-5)`; do not patch FileServer from the old FS27
   correlation.
2. If the xnthemeserver completion result is nonzero, correlate that exact
   function and client with the subsequent Leave before changing behavior.
3. If FileFlush itself returns a nonzero completion, preserve the exact path,
   handle and VFS result and investigate that backend narrowly.
4. If xnthemeserver requests/completions remain healthy, move the next
   investigation beyond theme storage into the post-render WindowServer /
   focus / input-event boundary.

Do not reopen the TFX hypothesis unless new device evidence contradicts the
stock V60 B47 result.
