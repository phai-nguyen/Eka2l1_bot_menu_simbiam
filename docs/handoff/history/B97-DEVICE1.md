# B97 — device log after overlay install

Date: 2026-09-27 (user-provided iPhone capture)

## Device result

The user reports B97 was installed over the existing app after clearing the
previous log. The emulator continued to show “Phone start-up failed. Contact
the retailer.” and was then exited cleanly; no video was supplied for this
attempt. The run in `EKA2L1_TakeThis(20260927-084046).log` spans 15:32:56.307
to 15:37:03.745 (about 4 minutes 7 seconds). It records `exit_requested` at
15:37:03.685 and `shutdown_done` at 15:37:03.745. This agrees with the user's
report of a clean exit and contains no host crash sequence.

The six-service barrier became ready at 15:33:28.023 and the real firmware
`menu3.exe` launched at 15:33:28.043. There is no
`[COMPATBOOT][TARGET_VISIBLE]` marker. The continuing phone-startup message is
user-reported; the log does not itself record rendered text.

## Inherited B89 startup-state override

This B97 runtime includes the earlier B89 behavior. At 15:33:34.028 the log
records the exact Telephone `CONE` reason-14 exit being converted to a clean
termination. At 15:33:34.069, SYSSTART's global startup-state write for
category `0x101F8766`, key `0x41`, is changed from requested value `116`
(`FatalStartupError`) to applied value `109` (`NormalRfOn`). This is a
targeted bypass of the failed critical
PhoneUI/SIM startup gate, not an observe-only event. It predates B97; no new
runtime code was built for this log. Despite that override, the user still saw
the Phone startup failure and the Menu target did not become visible. This
means B97 is not evidence from a no-bypass boot. The current
COMPATBOOT1-MENUPROBE1 constraint says not to bypass checks, so this inherited
behavior must be resolved explicitly before treating a later device run as a
strict no-bypass test.

## Menu Leave evidence

At 15:33:33.118, Menu flushes
`z:\Private\10207254\themes\270486738\270513751\271067333\1.0\hasclassicgrid.o0001`
with `flush_ok=1 completion=0`, then traps `Leave(-5)`. As in B96, stack
candidates map to stock EStor `CFileStore::DoRevertL()`,
`CStreamStore::Revert()`, and cleanup/destructor frames. The successful flush
does not establish that the object's contents are valid or explain why the
store enters Revert.

A second `Leave(-5)` occurs at 15:33:34.663. A stack return address at Avkon
offset `0xA3E` lies 10 bytes into the EPOC9 export
`CAknApplication::OpenIniFileLC(RFs&) const` (ordinal 3049). The matching stock
Avkon instructions immediately before that return address construct `-5` in
`r0` and call the EUser `User::Leave(int)` import. This identifies the source
of this Leave, but does not reveal which INI path was being opened, whether
`KErrNotFound` is expected there, or whether it relates to the phone-startup
screen.

A third scoped Menu Leave(-5) is logged at 15:33:34.685 in process
`Menu[101f4cd2]0003`; its stack candidates do not resolve to a caller with the
same confidence, so no cause is assigned.

## TfxServer scope and interpretation

The system-wide log has `TfxServer` misses before Menu3's scoped failure,
including requests from `eiksrvs`, `akncapserver`, `Telephone`, and `Home
screen`. The `[COMPATBOOT][FIRST_FAILURE]` marker at 15:33:33.155 means the
first failure within the Menu3 target scope; it is not the first missing
server in the full boot. Menu3's request is 37 ms after its first EStor Leave.
That timing does not establish that either event caused the persistent
phone-startup failure.

No `[COMPATBOOT][TARGET_VISIBLE]` marker appears. The log contains no host
crash sequence; the orderly shutdown markers match the user's statement that
it exited cleanly. No firmware image was changed. The inherited B89 behavior
does change the guest startup state, as described above.

## Evidence integrity

- `EKA2L1_Persistent-prev(20260927-084041).log`, 20,162,495 bytes; SHA-256
  `2661fe012fc6985ec619218baf0945bd509503e79f1267b249df31c390b4492d`.
- `EKA2L1_TakeThis(20260927-084046).log`, 20,105,144 bytes; SHA-256
  `8b2b689ddad21aaad5d2e9f16fefcdc194221c7f7ac94d112cab9455d75c2aee`.
- `EKA2L1(20260927-084023).log` and
  `EKA2L1_Persistent(20260927-084024).log` are byte-identical; SHA-256
  `896ff24b95e447340f8eecca3bb3f4e6818902047b04ff546bde4fe2f870b444`.

## Next investigation

Continue read-only tracing of the Phone startup failure and Menu's call into
`CAknApplication::OpenIniFileLC`, including the attempted filename and returned
status if recoverable from the ROM code and existing filesystem trace. Treat
the EStor Revert and missing TfxServer as separate observations until a causal
link is demonstrated. Keep Native Boot as default; do not alter firmware,
TFX/CenRep state, server behavior, or readiness checks.
