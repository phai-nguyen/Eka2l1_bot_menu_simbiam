# NATIVEBOOT2 B60 STARTUPSTATEWRITER1

Date: 2026-09-24
Status: BUILD-VALIDATED; DEVICE TEST REQUIRED

## Selection

B58/B59 prove Startup's category/key P&S write enters Wait=1, but no
category/key StartAnimations=2 write is observed.

The baseline already contains B44 diagnostics around handle-based P&S writes:

- service::property *b44_obj = prop->get_property_object()
- b44_obj->set_int(val)

B60 observes that existing handle setter for exactly:

- category 0x100058F4
- key 0x00000001

New marker:

[NBOOT2][STARTUP_STATE_HANDLE]

Fields:

- before / requested / after
- set result
- writer process / UID3 / thread
- property-reference handle
- path=HANDLE_INT
- behavior=OBSERVE_ONLY

B58's category/key marker remains active, so B60 provides both major integer
writer paths without changing P&S semantics.

## Canonical GREEN

- run ID: 35999937174
- run number: 178
- job: 107633834377
- HEAD: 5a51e6a749e8d7fa357f7a747cc0156db55322c9
- B60 apply PASS
- B60 contract PASS
- regressions PASS
- iOS compile/link PASS
- binary invariants PASS
- package/upload PASS
- compile requests/hits/misses: 149/148/1
- actual compilations: 1
- compilation failures: 0

Unsigned IPA SHA-256:

e456da3b8a8269666b3a0e1f92be7b74440512e1b5e50b804950b4ee36e86295

IPA artifact:

- ID: 10808270519
- ZIP digest: sha256:f8e10ddb52290dadbbc6cfc71d560b50a4e95273a9e25f83935d8b2c413324fe
- expires: 2026-10-08

Audit artifact:

- ID: 10807427655
- ZIP digest: sha256:c7efdef1a741617546aad8548354d6c34ae112a35e7bbe11b4a7c841cc510c2f
- expires: 2026-10-08

## Device decision

Run the same SIM-present normal boot path through NOKIA -> white.

Primary question:

Does any [STARTUP_STATE_HANDLE] marker request value 2?

Interpretation:

- no category/key 2 and no handle-based 2:
  move upstream to the SSM/Starter command-list execution that should publish
  EStartupAppStateStartAnimations.

- handle-based 2 appears and after=2:
  trace Startup's subscribed completion / property_get_int callback.

- 2 appears but set_result fails:
  inspect property-reference lifetime/type/permissions.

Exit should remain clean as in B59 DEVICE1.
