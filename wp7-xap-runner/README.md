# WP7 XAP Runner — XAPSCAN1

This branch is intentionally isolated from the EKA2L1/Symbian work. Its first milestone is **XAPSCAN1**: a static scanner for original Windows Phone 7 / Silverlight `.xap` packages.

## What XAPSCAN1 extracts

- package SHA-256 and full ZIP inventory
- `AppManifest.xaml` / `AppManifest.xml`: runtime, entry assembly/type, Deployment.Parts
- `WMAppManifest.xml`: metadata, DefaultTask/NavigationPage, capabilities
- every managed DLL/EXE: identity, CLR metadata version, IL-only status, AssemblyRef, TypeRef, MemberRef, resources, P/Invoke
- XNA Graphics dependency detection
- compatibility tags such as `BOOT_CANDIDATE`, `SILVERLIGHT_BASIC_CANDIDATE`, `NEEDS_XNA_FULL`, `HAS_PINVOKE`, and `MIXED_MODE`

The scanner does **not** claim that a package will run. It produces the dependency contract required by `ILRUN1`, `BIND1`, and `XAML1`.

## Run

```bash
dotnet run --project src/XapScan/XapScan.csproj -- MyApp.xap --out MyApp.xapscan1.json
```

Failure-oracle markers are emitted on stderr with prefix `[XAPSCAN1]`.

## Current gate

After scanning a real WP7 XAP, **ILRUN1** must prove on a physical iPhone that the selected Mono interpreter configuration can load and execute managed IL from an assembly that was not part of the original iOS app build.
