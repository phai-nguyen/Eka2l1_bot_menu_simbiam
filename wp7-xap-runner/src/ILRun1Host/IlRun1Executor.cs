using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using Foundation;

namespace WP7ILRun1;

internal sealed record IlRun1Result(bool Success, string Log, string? SavedLogPath);

internal static class IlRun1Executor
{
    private const string ExpectedResult = "XAP_ILRUN1_PASS:42";

    public static IlRun1Result Execute(Action<string>? onLine = null)
    {
        var log = new StringBuilder();

        void Emit(string marker)
        {
            log.AppendLine(marker);
            Console.WriteLine(marker);
            onLine?.Invoke(marker);
        }

        Emit("[ILRUN1][START]");
        Emit($"[ILRUN1][RUNTIME] {System.Runtime.InteropServices.RuntimeInformation.FrameworkDescription}");
        Emit($"[ILRUN1][OS] {System.Runtime.InteropServices.RuntimeInformation.OSDescription}");
        Emit($"[ILRUN1][ARCH] {System.Runtime.InteropServices.RuntimeInformation.ProcessArchitecture}");

        var success = false;
        string? savedPath = null;

        try
        {
            var payloadPath = Path.Combine(NSBundle.MainBundle.BundlePath, "IlPayload.dll");
            Emit($"[ILRUN1][PAYLOAD_PATH] {payloadPath}");

            if (!File.Exists(payloadPath))
            {
                Emit("[ILRUN1][FILE_NOT_FOUND]");
                return Finish(false);
            }

            Emit("[ILRUN1][FILE_FOUND]");

            var payload = File.ReadAllBytes(payloadPath);
            Emit($"[ILRUN1][FILE_READ_OK] bytes={payload.Length}");

            var sha256 = Convert.ToHexString(SHA256.HashData(payload)).ToLowerInvariant();
            Emit($"[ILRUN1][PAYLOAD_SHA256] {sha256}");

            // This is the decisive operation: IlPayload.dll is not a ProjectReference.
            // It exists only as a raw bundle file and is loaded from its bytes at runtime.
            var assembly = Assembly.Load(payload);
            Emit($"[ILRUN1][ASSEMBLY_LOAD_OK] {assembly.FullName}");

            var type = assembly.GetType("IlPayload.EntryPoint", throwOnError: false, ignoreCase: false);
            if (type is null)
            {
                Emit("[ILRUN1][TYPE_RESOLVE_FAIL] IlPayload.EntryPoint");
                return Finish(false);
            }

            Emit("[ILRUN1][TYPE_RESOLVE_OK] IlPayload.EntryPoint");

            var method = type.GetMethod(
                "Run",
                BindingFlags.Public | BindingFlags.Static,
                binder: null,
                Type.EmptyTypes,
                modifiers: null);

            if (method is null)
            {
                Emit("[ILRUN1][METHOD_RESOLVE_FAIL] IlPayload.EntryPoint.Run()");
                return Finish(false);
            }

            Emit("[ILRUN1][METHOD_RESOLVE_OK] IlPayload.EntryPoint.Run()");

            var value = method.Invoke(null, null)?.ToString();
            Emit($"[ILRUN1][METHOD_INVOKE_OK] result={value ?? "<null>"}");

            success = string.Equals(value, ExpectedResult, StringComparison.Ordinal);
            Emit(success
                ? "[ILRUN1][PASS] external managed IL executed on iOS"
                : $"[ILRUN1][RESULT_MISMATCH] expected={ExpectedResult} actual={value ?? "<null>"}");
        }
        catch (TargetInvocationException ex)
        {
            var inner = ex.InnerException ?? ex;
            Emit($"[ILRUN1][INVOKE_EXCEPTION] {inner.GetType().FullName}: {inner.Message}");
            Emit(inner.StackTrace ?? "<no stack>");
        }
        catch (Exception ex)
        {
            Emit($"[ILRUN1][FATAL] {ex.GetType().FullName}: {ex.Message}");
            Emit(ex.StackTrace ?? "<no stack>");
        }

        return Finish(success);

        IlRun1Result Finish(bool passed)
        {
            try
            {
                var documents = Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments);
                if (!string.IsNullOrWhiteSpace(documents))
                {
                    Directory.CreateDirectory(documents);
                    savedPath = Path.Combine(documents, "ILRUN1.log");
                    File.WriteAllText(savedPath, log.ToString());
                    Emit($"[ILRUN1][LOG_SAVED] {savedPath}");
                    File.WriteAllText(savedPath, log.ToString());
                }
            }
            catch (Exception ex)
            {
                Emit($"[ILRUN1][LOG_SAVE_FAIL] {ex.GetType().Name}: {ex.Message}");
            }

            Emit(passed ? "[ILRUN1][END] PASS" : "[ILRUN1][END] FAIL");
            return new IlRun1Result(passed, log.ToString(), savedPath);
        }
    }
}
