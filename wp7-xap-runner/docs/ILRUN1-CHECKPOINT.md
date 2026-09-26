# ILRUN1 checkpoint — iOS external managed IL execution probe

Status: **BUILD GREEN / DEVICE TEST REQUIRED**

## Goal

Prove on a physical iPhone that the Mono interpreter can execute managed IL from an assembly that was not statically referenced or AOT-compiled into the iOS host.

## Contract

`IlPayload.dll` is built separately as `netstandard2.0`, copied into the app bundle only as `BundleResource`, and is deliberately not a `ProjectReference` or assembly `Reference`.

At runtime the host performs:

1. read `IlPayload.dll` bytes from the app bundle;
2. `Assembly.Load(byte[])`;
3. resolve `IlPayload.EntryPoint`;
4. resolve public static `Run()`;
5. invoke with reflection;
6. require exact result `XAP_ILRUN1_PASS:42`.

The payload creates and mutates a generic managed type before returning the result.

## Required device markers

```text
[ILRUN1][START]
[ILRUN1][BUILD] ILRUN1-IOS1
[ILRUN1][FILE_FOUND]
[ILRUN1][FILE_READ_OK]
[ILRUN1][ASSEMBLY_LOAD_OK]
[ILRUN1][TYPE_RESOLVE_OK]
[ILRUN1][METHOD_RESOLVE_OK]
[ILRUN1][METHOD_INVOKE_OK] result=XAP_ILRUN1_PASS:42
[ILRUN1][PASS] external managed IL executed on iOS
[ILRUN1][END] PASS
```

Any missing marker is the new failure boundary.

## iOS build contract

- Target: `net10.0-ios`
- Device RID: `ios-arm64`
- Minimum iOS: **15.0**
- Mono interpreter: `UseInterpreter=true`
- NativeAOT: not used
- Payload: raw bundle file, no static assembly reference
- CI Xcode: 26.0.1
- Distribution for this experiment: unsigned IPA, intended to be re-signed with ESign for device testing.

## Next gates

- **PASS on device** → start BIND1: legacy assembly identity/binding layer for `mscorlib`, `System.Windows`, `Microsoft.Phone`.
- `Assembly.Load` fails → test stream/AssemblyLoadContext path, then embedded Mono/runtime-host alternatives.
- Assembly loads but invocation fails → classify missing runtime/BCL/generic/reflection dependency and reduce the payload to the failing IL feature.
