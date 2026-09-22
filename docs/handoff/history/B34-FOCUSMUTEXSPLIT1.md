# B34 FOCUSMUTEXSPLIT1

Date: 2026-09-22
Status: BUILD-VALIDATED, DEVICE TEST REQUIRED
Active branch: nativeboot2-current

## Root cause

B33 device evidence showed Exit Emulator accepted the request and reached:

`BRIDGE_EXIT -> shutdown_threads -> os_join_begin`

but never reached `os_join_done`.

The iOS process snapshot taken after the user manually swiped the hung app to
the Home Screen showed the lifecycle worker waiting in
`shutdown_threads()/pthread_join()`, while the Symbian OS thread was blocked
inside:

`screen::fire_focus_change_callbacks()`
-> `screen::update_focus()`
-> `window_group::~window_group()`
-> `window_server_client::~window_server_client()`
-> Wserv teardown.

Exact B33 reconstructed source inspection then proved the same-thread lock
cycle:

1. `window_server_client::~window_server_client()` locks
   `scr->screen_mutex` when canceling.
2. It calls `objects.clear()` while that mutex remains held.
3. Destroying the focused `window_group` calls `screen::update_focus()`.
4. `update_focus()` calls `fire_focus_change_callbacks()`.
5. B33 `fire_focus_change_callbacks()` tries to lock the same
   non-recursive `screen_mutex` again.

That nested acquisition cannot complete.

The B33 baseline also used `screen_mutex` for
`add_focus_change_callback()` and `remove_focus_change_callback()`.

## Upstream reference

Upstream EKA2L1 commit:

`2896f1a0b0189d06db95fa5cfc0a5c14ee89be1d`

contains the same window-server locking correction family. Among a larger batch
it adds a dedicated `focus_callback_mutex` and moves
`fire/add/remove_focus_change_callback()` away from `screen_mutex`.

B34 ports only that focus-callback mutex split. It does NOT import the unrelated
redraw/mode callback changes or any other part of the upstream batch.

## B34 change

Apply script:
`apply_nativeboot2_b34_focusmutexsplit1.py`

Contract:
`test_nativeboot2_b34_focusmutexsplit1.py`

Functional patch script commit:
`b332286861becc205de491a67bdea68abb54d441`

FASTBUILD1 manifest commit:
`b1ac9fd243f58b257a9ee581294a3271f2d6c383`

Authoritative GREEN run HEAD:
`24001e3306070fab2145bc1a4dd326a9fa83587d`

The patch:
- keeps `std::mutex screen_mutex`;
- adds `std::mutex focus_callback_mutex`;
- changes only `fire_focus_change_callbacks()`,
  `add_focus_change_callback()`, and `remove_focus_change_callback()` to
  lock `focus_callback_mutex`;
- adds binary marker `[NBOOT2][FOCUS_MUTEX_SPLIT]`.

It does NOT:
- make `screen_mutex` recursive;
- change the outer Wserv teardown lock;
- change `objects.clear()`;
- change `window_group` teardown;
- change `screen::update_focus()`;
- change redraw/mode callback locking;
- change iOS Exit Emulator choreography;
- change guest IPC, SVC, FEP, leave, exception, loader, scheduler, FBS, or CenRep behavior.

## TDD RED

Contract-first commits:
- test: `fea5759e9120b8f735d44a60824cd419bee9b30d`
- RED workflow: `c6525d73c9a12919c662107d916d7d4760d2cbf1`

RED run:
`35691246288`

Expected conclusion:
failure.

B28 -> B33 reconstruction passed all milestone tests.

Exact intended RED failure:

`NATIVEBOOT2-B34-FOCUSMUTEXSPLIT1-TEST: FAIL: missing in screen.h dedicated focus callback mutex: std::mutex focus_callback_mutex;`

Thus the B34 contract was proven to detect the missing fix on the exact B33
baseline before the functional patch was written.

## Authoritative GREEN

Run:
`35691395487`

Job:
`106628955424`

Run HEAD:
`24001e3306070fab2145bc1a4dd326a9fa83587d`

Result:
- workflow conclusion: success;
- FASTBUILD1 manifest VALID;
- B34 apply PASS;
- B34 contract PASS;
- full FASTBUILD1 regression chain PASS;
- iOS compile/link PASS;
- binary invariants PASS;
- packaged Mach-O contains `[NBOOT2][FOCUS_MUTEX_SPLIT]`;
- IPA package PASS;
- IPA upload PASS;
- audit upload PASS;
- NOJAVA preserved;
- MANIC3 preserved.

FASTBUILD1 audit:
- bootstrap_source=B28_CACHE
- bootstrap restore: 35 s
- patch + regression: 1 s
- CMake build: 25 s
- package: 3 s
- total: 83 s
- compile requests: 50
- cache hits: 50
- cache misses: 0
- hit rate: 100%
- actual compilations: 0
- compilation failures: 0
- Xcode 16.4 / build 16F6
- Apple clang 17.0.0

Unsigned IPA SHA-256:
`486ed148c18689b9582988df1e30616ab4bb40c18070a7e554078161d20c4c5c`

The downloaded artifact was independently extracted and hashed locally; the
hash matches the CI `FASTBUILD1-IPA-SHA256.txt` exactly.

IPA artifact:
- ID: `10679545002`
- ZIP digest:
  `sha256:f16a1ba31c6a72ba47ea157a60768ac6ebcc3599bb2e8cc25b286c6278bdd150`
- expires: 2026-10-06

Audit artifact:
- ID: `10677634965`
- ZIP digest:
  `sha256:3db7b24c1d3d5ff9cd92572ffcdf4bb50afb57069183a8ff6f646cf3b69bbc48`
- expires: 2026-10-06

## Device validation

B34 is build-validated only.

Primary test:
1. sign/install B34;
2. boot Nokia 5800 firmware through the same path as B33;
3. choose `Thoát Emulator`;
4. do NOT manually swipe the app away;
5. verify whether the app itself returns to the normal EKA2L1 library/frontend.

Success markers should continue past the B33 boundary:
- `[NBOOT2][BRIDGE_EXIT_PHASE] phase=os_join_begin`
- then `phase=os_join_done`
- `phase=shutdown_threads_done`
- `phase=shutdown_done`
- normal restart/library restore markers from B26.

If it still hangs, collect the standard EKA2L1 logs and a fresh iOS process
report only if one is naturally produced or useful. Do not infer a crash merely
from the user manually leaving the app.

Secondary boot behavior:
verify B30/B31/B32/B33 behavior did not regress.

Do not create an immutable B34 milestone branch until device validation.
