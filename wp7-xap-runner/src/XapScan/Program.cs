using System.IO.Compression;
using System.Reflection;
using System.Reflection.Metadata;
using System.Reflection.PortableExecutable;
using System.Security.Cryptography;
using System.Text.Json;
using System.Xml.Linq;

namespace XapScan;

internal static class Program
{
    private const string ScannerVersion = "XAPSCAN1";

    public static int Main(string[] args)
    {
        if (args.Length == 0 || args.Contains("--help", StringComparer.OrdinalIgnoreCase))
        {
            PrintUsage();
            return args.Length == 0 ? 2 : 0;
        }

        string? xapPath = null;
        string? outPath = null;
        for (var i = 0; i < args.Length; i++)
        {
            if (args[i] == "--out" && i + 1 < args.Length)
            {
                outPath = args[++i];
            }
            else if (!args[i].StartsWith("--", StringComparison.Ordinal))
            {
                xapPath ??= args[i];
            }
        }

        if (string.IsNullOrWhiteSpace(xapPath) || !File.Exists(xapPath))
        {
            Console.Error.WriteLine($"[{ScannerVersion}][INPUT_NOT_FOUND] path={xapPath ?? "<null>"}");
            return 2;
        }

        try
        {
            var report = XapScanner.Scan(xapPath);
            var json = JsonSerializer.Serialize(report, JsonOptions);
            if (!string.IsNullOrWhiteSpace(outPath))
            {
                var full = Path.GetFullPath(outPath);
                Directory.CreateDirectory(Path.GetDirectoryName(full) ?? ".");
                File.WriteAllText(full, json);
                Console.Error.WriteLine($"[{ScannerVersion}][REPORT_WRITTEN] path={full}");
            }
            else
            {
                Console.WriteLine(json);
            }

            foreach (var finding in report.Findings)
            {
                Console.Error.WriteLine($"[{ScannerVersion}][{finding.Code}] {finding.Message}");
            }

            return 0;
        }
        catch (InvalidDataException ex)
        {
            Console.Error.WriteLine($"[{ScannerVersion}][INVALID_XAP] {ex.Message}");
            return 2;
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine($"[{ScannerVersion}][FATAL] {ex}");
            return 3;
        }
    }

    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        WriteIndented = true,
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
        DefaultIgnoreCondition = System.Text.Json.Serialization.JsonIgnoreCondition.WhenWritingNull,
    };

    private static void PrintUsage()
    {
        Console.WriteLine("XAPSCAN1 - Windows Phone 7 XAP static compatibility scanner");
        Console.WriteLine("Usage: dotnet run --project src/XapScan/XapScan.csproj -- <file.xap> [--out report.json]");
    }
}

internal static class XapScanner
{
    public static XapScanReport Scan(string xapPath)
    {
        var packageSha = Sha256File(xapPath);
        using var fs = File.OpenRead(xapPath);
        using var zip = new ZipArchive(fs, ZipArchiveMode.Read, leaveOpen: false);

        var entries = zip.Entries
            .Where(e => !string.IsNullOrEmpty(e.Name))
            .Select(ScanEntry)
            .OrderBy(e => e.Path, StringComparer.OrdinalIgnoreCase)
            .ToList();

        var findings = new List<Finding>();
        var appManifestEntry = FindEntry(zip, "AppManifest.xaml") ?? FindEntry(zip, "AppManifest.xml");
        var wmManifestEntry = FindEntry(zip, "WMAppManifest.xml");

        AppManifestInfo? appManifest = null;
        if (appManifestEntry is null)
        {
            findings.Add(new("MISSING_APP_MANIFEST", "Neither AppManifest.xaml nor AppManifest.xml was found."));
        }
        else
        {
            appManifest = ParseAppManifest(appManifestEntry);
        }

        WmAppManifestInfo? wmManifest = null;
        if (wmManifestEntry is null)
        {
            findings.Add(new("MISSING_WMAPP_MANIFEST", "WMAppManifest.xml was not found."));
        }
        else
        {
            wmManifest = ParseWmAppManifest(wmManifestEntry);
        }

        var assemblyResults = new List<AssemblyScanResult>();
        foreach (var entry in zip.Entries.Where(e =>
                     e.Name.EndsWith(".dll", StringComparison.OrdinalIgnoreCase) ||
                     e.Name.EndsWith(".exe", StringComparison.OrdinalIgnoreCase)))
        {
            assemblyResults.Add(AssemblyScanner.Scan(entry));
        }

        foreach (var asm in assemblyResults)
        {
            if (!asm.IsManaged)
                findings.Add(new("NATIVE_OR_UNMANAGED_IMAGE", $"{asm.Path} has no CLR metadata."));
            if (asm.IsMixedMode)
                findings.Add(new("MIXED_MODE_IMAGE", $"{asm.Path} is managed but not IL-only."));
            if (asm.PInvokes.Count > 0)
                findings.Add(new("PINVOKE_PRESENT", $"{asm.Path} contains {asm.PInvokes.Count} P/Invoke method(s)."));
            if (asm.XnaGraphicsTypeReferenceCount > 0)
                findings.Add(new("XNA_GRAPHICS_REQUIRED", $"{asm.Path} references Microsoft.Xna.Framework.Graphics types."));
            else if (asm.AssemblyReferences.Any(r => r.Name.StartsWith("Microsoft.Xna.Framework", StringComparison.OrdinalIgnoreCase)))
                findings.Add(new("XNA_PARTIAL_REQUIRED", $"{asm.Path} references XNA assemblies but no Graphics type was observed."));
        }

        bool? entryAssemblyResolved = null;
        bool? entryTypeResolved = null;
        if (appManifest is not null && !string.IsNullOrWhiteSpace(appManifest.EntryPointAssembly))
        {
            var entryAsm = assemblyResults.FirstOrDefault(a =>
                a.IsManaged && string.Equals(a.Name, appManifest.EntryPointAssembly, StringComparison.OrdinalIgnoreCase));
            entryAssemblyResolved = entryAsm is not null;
            if (entryAsm is null)
            {
                findings.Add(new("ENTRY_ASSEMBLY_UNRESOLVED", $"EntryPointAssembly '{appManifest.EntryPointAssembly}' was not found among managed package assemblies."));
            }
            else if (!string.IsNullOrWhiteSpace(appManifest.EntryPointType))
            {
                entryTypeResolved = entryAsm.TypeDefinitions.Contains(appManifest.EntryPointType, StringComparer.Ordinal);
                if (entryTypeResolved == false)
                    findings.Add(new("ENTRY_TYPE_UNRESOLVED", $"EntryPointType '{appManifest.EntryPointType}' was not found in '{entryAsm.Path}'."));
            }
        }

        var tags = Classify(appManifest, wmManifest, assemblyResults, findings);
        var dependencyGroups = BuildDependencyGroups(assemblyResults);

        return new XapScanReport(
            Scanner: "XAPSCAN1",
            ScannerSchema: 1,
            Package: new PackageInfo(
                Path: Path.GetFullPath(xapPath),
                FileName: Path.GetFileName(xapPath),
                Sha256: packageSha,
                SizeBytes: new FileInfo(xapPath).Length,
                EntryCount: entries.Count),
            AppManifest: appManifest,
            WmAppManifest: wmManifest,
            EntryPoint: new EntryPointResolution(entryAssemblyResolved, entryTypeResolved),
            Files: entries,
            Assemblies: assemblyResults.OrderBy(a => a.Path, StringComparer.OrdinalIgnoreCase).ToList(),
            ApiDependencies: dependencyGroups,
            CompatibilityTags: tags,
            Findings: findings);
    }

    private static ZipEntryInfo ScanEntry(ZipArchiveEntry entry)
    {
        using var stream = entry.Open();
        var sha = Convert.ToHexString(SHA256.HashData(stream)).ToLowerInvariant();
        return new(entry.FullName, entry.Length, entry.CompressedLength, sha);
    }

    private static ZipArchiveEntry? FindEntry(ZipArchive zip, string baseName) =>
        zip.Entries.FirstOrDefault(e => string.Equals(Path.GetFileName(e.FullName), baseName, StringComparison.OrdinalIgnoreCase));

    private static AppManifestInfo ParseAppManifest(ZipArchiveEntry entry)
    {
        using var stream = entry.Open();
        var doc = XDocument.Load(stream, LoadOptions.None);
        var deployment = doc.Root ?? throw new InvalidDataException($"{entry.FullName} has no root element.");
        var parts = deployment.Descendants().Where(e => e.Name.LocalName == "AssemblyPart")
            .Select(e => new AssemblyPartInfo(
                Name: Attr(e, "Name"),
                Source: Attr(e, "Source")))
            .ToList();

        return new(
            Path: entry.FullName,
            RuntimeVersion: Attr(deployment, "RuntimeVersion"),
            EntryPointAssembly: Attr(deployment, "EntryPointAssembly"),
            EntryPointType: Attr(deployment, "EntryPointType"),
            AssemblyParts: parts);
    }

    private static WmAppManifestInfo ParseWmAppManifest(ZipArchiveEntry entry)
    {
        using var stream = entry.Open();
        var doc = XDocument.Load(stream, LoadOptions.None);
        var app = doc.Descendants().FirstOrDefault(e => e.Name.LocalName == "App");
        var task = doc.Descendants().FirstOrDefault(e => e.Name.LocalName == "DefaultTask");
        var caps = doc.Descendants()
            .Where(e => e.Name.LocalName == "Capability")
            .Select(e => Attr(e, "Name"))
            .Where(x => !string.IsNullOrWhiteSpace(x))
            .Distinct(StringComparer.OrdinalIgnoreCase)
            .OrderBy(x => x, StringComparer.OrdinalIgnoreCase)
            .Cast<string>()
            .ToList();

        return new(
            Path: entry.FullName,
            ProductId: Attr(app, "ProductID") ?? Attr(app, "ProductId"),
            Title: Attr(app, "Title"),
            RuntimeType: Attr(app, "RuntimeType"),
            Version: Attr(app, "Version"),
            Genre: Attr(app, "Genre"),
            Author: Attr(app, "Author"),
            Description: Attr(app, "Description"),
            AppPlatformVersion: Attr(app, "AppPlatformVersion"),
            DefaultTaskName: Attr(task, "Name"),
            NavigationPage: Attr(task, "NavigationPage"),
            Capabilities: caps);
    }

    private static string? Attr(XElement? e, string localName) => e?.Attributes()
        .FirstOrDefault(a => a.Name.LocalName.Equals(localName, StringComparison.OrdinalIgnoreCase))?.Value;

    private static List<string> Classify(
        AppManifestInfo? appManifest,
        WmAppManifestInfo? wmManifest,
        IReadOnlyList<AssemblyScanResult> assemblies,
        IReadOnlyList<Finding> findings)
    {
        var tags = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        if (appManifest is null || wmManifest is null)
            tags.Add("MANIFEST_INCOMPLETE");
        if (assemblies.Count == 0)
            tags.Add("NO_ASSEMBLIES");
        if (assemblies.Any(a => !a.IsManaged))
            tags.Add("HAS_NATIVE_IMAGE");
        if (assemblies.Any(a => a.IsMixedMode))
            tags.Add("MIXED_MODE");
        if (assemblies.Any(a => a.PInvokes.Count > 0))
            tags.Add("HAS_PINVOKE");
        if (assemblies.Any(a => a.XnaGraphicsTypeReferenceCount > 0))
            tags.Add("NEEDS_XNA_FULL");
        else if (assemblies.Any(a => a.AssemblyReferences.Any(r => r.Name.StartsWith("Microsoft.Xna.Framework", StringComparison.OrdinalIgnoreCase))))
            tags.Add("NEEDS_XNA_PARTIAL");
        if (assemblies.Any(a => a.AssemblyReferences.Any(r => r.Name.Equals("Microsoft.Phone", StringComparison.OrdinalIgnoreCase))))
            tags.Add("WP7_PHONE_API");
        if (assemblies.Any(a => a.AssemblyReferences.Any(r => r.Name.Equals("System.Windows", StringComparison.OrdinalIgnoreCase))))
            tags.Add("SILVERLIGHT");

        var hardBlock = tags.Contains("HAS_NATIVE_IMAGE") || tags.Contains("MIXED_MODE") || tags.Contains("HAS_PINVOKE") || tags.Contains("NEEDS_XNA_FULL");
        if (!hardBlock && appManifest is not null && wmManifest is not null && assemblies.Any(a => a.IsManaged))
            tags.Add("BOOT_CANDIDATE");
        if (!hardBlock && tags.Contains("SILVERLIGHT"))
            tags.Add("SILVERLIGHT_BASIC_CANDIDATE");

        if (findings.Count == 0)
            tags.Add("STATIC_SCAN_CLEAN");

        return tags.OrderBy(x => x, StringComparer.OrdinalIgnoreCase).ToList();
    }

    private static List<ApiDependencyGroup> BuildDependencyGroups(IEnumerable<AssemblyScanResult> assemblies)
    {
        var groups = new Dictionary<string, Dictionary<string, SortedSet<string>>>(StringComparer.OrdinalIgnoreCase);
        foreach (var asm in assemblies.Where(a => a.IsManaged))
        {
            foreach (var dep in asm.ApiReferences)
            {
                var targetAssembly = dep.TargetAssembly ?? "<unresolved>";
                if (!groups.TryGetValue(targetAssembly, out var types))
                    groups[targetAssembly] = types = new(StringComparer.Ordinal);
                if (!types.TryGetValue(dep.TypeName, out var members))
                    types[dep.TypeName] = members = new(StringComparer.Ordinal);
                if (!string.IsNullOrWhiteSpace(dep.MemberName))
                    members.Add(dep.MemberName);
            }
        }

        return groups
            .OrderBy(kv => kv.Key, StringComparer.OrdinalIgnoreCase)
            .Select(kv => new ApiDependencyGroup(
                kv.Key,
                kv.Value.OrderBy(t => t.Key, StringComparer.Ordinal)
                    .Select(t => new ApiTypeDependency(t.Key, t.Value.ToList()))
                    .ToList()))
            .ToList();
    }

    private static string Sha256File(string path)
    {
        using var fs = File.OpenRead(path);
        return Convert.ToHexString(SHA256.HashData(fs)).ToLowerInvariant();
    }
}

internal static class AssemblyScanner
{
    public static AssemblyScanResult Scan(ZipArchiveEntry entry)
    {
        using var memory = new MemoryStream();
        using (var source = entry.Open())
            source.CopyTo(memory);
        memory.Position = 0;

        using var pe = new PEReader(memory, PEStreamOptions.LeaveOpen);
        if (!pe.HasMetadata)
        {
            return AssemblyScanResult.Unmanaged(entry.FullName);
        }

        MetadataReader reader;
        try
        {
            reader = pe.GetMetadataReader();
        }
        catch (BadImageFormatException)
        {
            return AssemblyScanResult.Unmanaged(entry.FullName);
        }

        var corHeader = pe.PEHeaders.CorHeader;
        var isIlOnly = corHeader is not null && (corHeader.Flags & CorFlags.ILOnly) != 0;
        var isMixedMode = corHeader is not null && !isIlOnly;

        string name = Path.GetFileNameWithoutExtension(entry.Name);
        Version? version = null;
        string? culture = null;
        string? publicKeyToken = null;
        if (reader.IsAssembly)
        {
            var def = reader.GetAssemblyDefinition();
            name = reader.GetString(def.Name);
            version = def.Version;
            culture = def.Culture.IsNil ? null : reader.GetString(def.Culture);
            publicKeyToken = PublicKeyTokenFromDefinition(reader, def);
        }

        var module = reader.GetModuleDefinition();
        var moduleName = module.Name.IsNil ? null : reader.GetString(module.Name);
        var mvid = module.Mvid.IsNil ? (Guid?)null : reader.GetGuid(module.Mvid);

        var assemblyRefs = new List<AssemblyReferenceInfo>();
        foreach (var handle in reader.AssemblyReferences)
        {
            var ar = reader.GetAssemblyReference(handle);
            assemblyRefs.Add(new(
                Name: reader.GetString(ar.Name),
                Version: ar.Version.ToString(),
                Culture: ar.Culture.IsNil ? null : reader.GetString(ar.Culture),
                PublicKeyToken: PublicKeyTokenFromReference(reader, ar),
                Flags: ar.Flags.ToString()));
        }

        var typeDefinitions = new List<string>();
        foreach (var handle in reader.TypeDefinitions)
        {
            var td = reader.GetTypeDefinition(handle);
            var typeName = FullTypeName(reader, td.Namespace, td.Name);
            if (typeName != "<Module>")
                typeDefinitions.Add(typeName);
        }

        var apiRefs = new List<ApiReference>();
        var xnaGraphicsCount = 0;
        foreach (var handle in reader.TypeReferences)
        {
            var tr = reader.GetTypeReference(handle);
            var typeName = FullTypeName(reader, tr.Namespace, tr.Name);
            var targetAssembly = ResolveTypeReferenceAssembly(reader, handle, new HashSet<TypeReferenceHandle>());
            apiRefs.Add(new(targetAssembly, typeName, null));
            if (typeName.StartsWith("Microsoft.Xna.Framework.Graphics.", StringComparison.Ordinal))
                xnaGraphicsCount++;
        }

        foreach (var handle in reader.MemberReferences)
        {
            var mr = reader.GetMemberReference(handle);
            var memberName = reader.GetString(mr.Name);
            var (targetAssembly, typeName) = ResolveMemberParent(reader, mr.Parent);
            apiRefs.Add(new(targetAssembly, typeName, memberName));
        }

        var pinvokes = new List<PInvokeInfo>();
        foreach (var handle in reader.MethodDefinitions)
        {
            var method = reader.GetMethodDefinition(handle);
            if ((method.Attributes & MethodAttributes.PinvokeImpl) == 0)
                continue;
            var import = method.GetImport();
            var moduleRef = reader.GetModuleReference(import.Module);
            pinvokes.Add(new(
                ManagedMethod: reader.GetString(method.Name),
                NativeModule: reader.GetString(moduleRef.Name),
                EntryPoint: import.Name.IsNil ? null : reader.GetString(import.Name),
                Attributes: import.Attributes.ToString()));
        }

        var resources = new List<ManagedResourceInfo>();
        foreach (var handle in reader.ManifestResources)
        {
            var resource = reader.GetManifestResource(handle);
            resources.Add(new(
                Name: reader.GetString(resource.Name),
                Attributes: resource.Attributes.ToString(),
                Offset: resource.Offset,
                ImplementationKind: resource.Implementation.IsNil ? "Embedded" : resource.Implementation.Kind.ToString()));
        }

        var dedupedApiRefs = apiRefs
            .Distinct(ApiReferenceComparer.Instance)
            .OrderBy(x => x.TargetAssembly, StringComparer.OrdinalIgnoreCase)
            .ThenBy(x => x.TypeName, StringComparer.Ordinal)
            .ThenBy(x => x.MemberName, StringComparer.Ordinal)
            .ToList();

        return new AssemblyScanResult(
            Path: entry.FullName,
            IsManaged: true,
            IsIlOnly: isIlOnly,
            IsMixedMode: isMixedMode,
            Name: name,
            Version: version?.ToString(),
            Culture: culture,
            PublicKeyToken: publicKeyToken,
            MetadataVersion: reader.MetadataVersion,
            ModuleName: moduleName,
            Mvid: mvid?.ToString("D"),
            AssemblyReferences: assemblyRefs.OrderBy(r => r.Name, StringComparer.OrdinalIgnoreCase).ToList(),
            TypeDefinitions: typeDefinitions.OrderBy(x => x, StringComparer.Ordinal).ToList(),
            TypeReferenceCount: reader.TypeReferences.Count,
            MemberReferenceCount: reader.MemberReferences.Count,
            XnaGraphicsTypeReferenceCount: xnaGraphicsCount,
            PInvokes: pinvokes,
            ManagedResources: resources,
            ApiReferences: dedupedApiRefs);
    }

    private static string FullTypeName(MetadataReader reader, StringHandle nsHandle, StringHandle nameHandle)
    {
        var ns = nsHandle.IsNil ? string.Empty : reader.GetString(nsHandle);
        var name = reader.GetString(nameHandle);
        return string.IsNullOrEmpty(ns) ? name : $"{ns}.{name}";
    }

    private static string? ResolveTypeReferenceAssembly(MetadataReader reader, TypeReferenceHandle handle, HashSet<TypeReferenceHandle> visited)
    {
        if (!visited.Add(handle))
            return null;
        var tr = reader.GetTypeReference(handle);
        return tr.ResolutionScope.Kind switch
        {
            HandleKind.AssemblyReference => reader.GetString(reader.GetAssemblyReference((AssemblyReferenceHandle)tr.ResolutionScope).Name),
            HandleKind.TypeReference => ResolveTypeReferenceAssembly(reader, (TypeReferenceHandle)tr.ResolutionScope, visited),
            HandleKind.ModuleDefinition => "<current-module>",
            HandleKind.ModuleReference => reader.GetString(reader.GetModuleReference((ModuleReferenceHandle)tr.ResolutionScope).Name),
            _ => null,
        };
    }

    private static (string? TargetAssembly, string TypeName) ResolveMemberParent(MetadataReader reader, EntityHandle parent)
    {
        return parent.Kind switch
        {
            HandleKind.TypeReference => ResolveTypeRefParent(reader, (TypeReferenceHandle)parent),
            HandleKind.TypeDefinition => ("<current-assembly>", TypeDefName(reader, (TypeDefinitionHandle)parent)),
            HandleKind.ModuleReference => (reader.GetString(reader.GetModuleReference((ModuleReferenceHandle)parent).Name), "<module>"),
            HandleKind.MethodDefinition => ("<current-assembly>", "<methoddef-parent>"),
            HandleKind.TypeSpecification => ("<unresolved-typespec>", "<typespec>"),
            _ => (null, $"<{parent.Kind}>"),
        };
    }

    private static (string? TargetAssembly, string TypeName) ResolveTypeRefParent(MetadataReader reader, TypeReferenceHandle handle)
    {
        var tr = reader.GetTypeReference(handle);
        return (
            ResolveTypeReferenceAssembly(reader, handle, new HashSet<TypeReferenceHandle>()),
            FullTypeName(reader, tr.Namespace, tr.Name));
    }

    private static string TypeDefName(MetadataReader reader, TypeDefinitionHandle handle)
    {
        var td = reader.GetTypeDefinition(handle);
        return FullTypeName(reader, td.Namespace, td.Name);
    }

    private static string? PublicKeyTokenFromDefinition(MetadataReader reader, AssemblyDefinition def)
    {
        if (def.PublicKey.IsNil)
            return null;
        var publicKey = reader.GetBlobBytes(def.PublicKey);
        if (publicKey.Length == 0)
            return null;
        var hash = SHA1.HashData(publicKey);
        return Convert.ToHexString(hash[^8..].Reverse().ToArray()).ToLowerInvariant();
    }

    private static string? PublicKeyTokenFromReference(MetadataReader reader, AssemblyReference ar)
    {
        if (ar.PublicKeyOrToken.IsNil)
            return null;
        var bytes = reader.GetBlobBytes(ar.PublicKeyOrToken);
        if (bytes.Length == 0)
            return null;
        if ((ar.Flags & AssemblyFlags.PublicKey) != 0)
        {
            var hash = SHA1.HashData(bytes);
            return Convert.ToHexString(hash[^8..].Reverse().ToArray()).ToLowerInvariant();
        }
        return Convert.ToHexString(bytes).ToLowerInvariant();
    }

    private sealed class ApiReferenceComparer : IEqualityComparer<ApiReference>
    {
        public static readonly ApiReferenceComparer Instance = new();
        public bool Equals(ApiReference? x, ApiReference? y) =>
            x is not null && y is not null &&
            string.Equals(x.TargetAssembly, y.TargetAssembly, StringComparison.OrdinalIgnoreCase) &&
            string.Equals(x.TypeName, y.TypeName, StringComparison.Ordinal) &&
            string.Equals(x.MemberName, y.MemberName, StringComparison.Ordinal);

        public int GetHashCode(ApiReference obj) => HashCode.Combine(
            StringComparer.OrdinalIgnoreCase.GetHashCode(obj.TargetAssembly ?? string.Empty),
            StringComparer.Ordinal.GetHashCode(obj.TypeName),
            StringComparer.Ordinal.GetHashCode(obj.MemberName ?? string.Empty));
    }
}

internal sealed record XapScanReport(
    string Scanner,
    int ScannerSchema,
    PackageInfo Package,
    AppManifestInfo? AppManifest,
    WmAppManifestInfo? WmAppManifest,
    EntryPointResolution EntryPoint,
    List<ZipEntryInfo> Files,
    List<AssemblyScanResult> Assemblies,
    List<ApiDependencyGroup> ApiDependencies,
    List<string> CompatibilityTags,
    List<Finding> Findings);

internal sealed record PackageInfo(string Path, string FileName, string Sha256, long SizeBytes, int EntryCount);
internal sealed record ZipEntryInfo(string Path, long SizeBytes, long CompressedSizeBytes, string Sha256);
internal sealed record AssemblyPartInfo(string? Name, string? Source);
internal sealed record AppManifestInfo(string Path, string? RuntimeVersion, string? EntryPointAssembly, string? EntryPointType, List<AssemblyPartInfo> AssemblyParts);
internal sealed record WmAppManifestInfo(
    string Path,
    string? ProductId,
    string? Title,
    string? RuntimeType,
    string? Version,
    string? Genre,
    string? Author,
    string? Description,
    string? AppPlatformVersion,
    string? DefaultTaskName,
    string? NavigationPage,
    List<string> Capabilities);
internal sealed record EntryPointResolution(bool? AssemblyResolved, bool? TypeResolved);
internal sealed record Finding(string Code, string Message);
internal sealed record AssemblyReferenceInfo(string Name, string Version, string? Culture, string? PublicKeyToken, string Flags);
internal sealed record PInvokeInfo(string ManagedMethod, string NativeModule, string? EntryPoint, string Attributes);
internal sealed record ManagedResourceInfo(string Name, string Attributes, uint Offset, string ImplementationKind);
internal sealed record ApiReference(string? TargetAssembly, string TypeName, string? MemberName);
internal sealed record ApiDependencyGroup(string Assembly, List<ApiTypeDependency> Types);
internal sealed record ApiTypeDependency(string Type, List<string> Members);

internal sealed record AssemblyScanResult(
    string Path,
    bool IsManaged,
    bool IsIlOnly,
    bool IsMixedMode,
    string Name,
    string? Version,
    string? Culture,
    string? PublicKeyToken,
    string? MetadataVersion,
    string? ModuleName,
    string? Mvid,
    List<AssemblyReferenceInfo> AssemblyReferences,
    List<string> TypeDefinitions,
    int TypeReferenceCount,
    int MemberReferenceCount,
    int XnaGraphicsTypeReferenceCount,
    List<PInvokeInfo> PInvokes,
    List<ManagedResourceInfo> ManagedResources,
    List<ApiReference> ApiReferences)
{
    public static AssemblyScanResult Unmanaged(string path) => new(
        Path: path,
        IsManaged: false,
        IsIlOnly: false,
        IsMixedMode: false,
        Name: System.IO.Path.GetFileNameWithoutExtension(path),
        Version: null,
        Culture: null,
        PublicKeyToken: null,
        MetadataVersion: null,
        ModuleName: null,
        Mvid: null,
        AssemblyReferences: new(),
        TypeDefinitions: new(),
        TypeReferenceCount: 0,
        MemberReferenceCount: 0,
        XnaGraphicsTypeReferenceCount: 0,
        PInvokes: new(),
        ManagedResources: new(),
        ApiReferences: new());
}
