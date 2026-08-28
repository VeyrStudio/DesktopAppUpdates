using System.Diagnostics;
using System.Net.Http;
using System.Reflection;
using System.Security.Cryptography;
using System.Text.Json;
using System.Windows;

namespace TheTome;

public sealed class UpdateService
{
    private const string ManifestUrl = "https://raw.githubusercontent.com/VeyrStudio/DesktopAppUpdates/main/the-tome/wpf-manifest.json";
    private readonly string _appDir;
    private readonly HttpClient _http = new() { Timeout = TimeSpan.FromMinutes(3) };
    private static readonly JsonSerializerOptions JsonOptions = new() { PropertyNameCaseInsensitive = true };

    public string CurrentVersion { get; }

    public UpdateService(string appDir)
    {
        _appDir = appDir;
        CurrentVersion = ReadCurrentVersion(appDir);
    }

    public async Task<UpdateCheckResult> CheckAsync()
    {
        using var request = new HttpRequestMessage(HttpMethod.Get, ManifestUrl);
        request.Headers.CacheControl = new System.Net.Http.Headers.CacheControlHeaderValue { NoCache = true };
        using var response = await _http.SendAsync(request);
        response.EnsureSuccessStatusCode();
        var json = await response.Content.ReadAsStringAsync();
        var manifest = JsonSerializer.Deserialize<UpdateManifest>(json, JsonOptions)
            ?? throw new InvalidDataException("The update feed was empty.");
        if (manifest.AppId != "the-tome-wpf") throw new InvalidDataException("The update feed belongs to another app.");
        if (!Version.TryParse(manifest.Version, out var remote) || !Version.TryParse(CurrentVersion, out var local))
            throw new InvalidDataException("The update version could not be read.");
        if (remote <= local) return new UpdateCheckResult(null, $"The Tome is up to date. Installed version: {CurrentVersion}");
        return new UpdateCheckResult(manifest, $"The Tome v{manifest.Version} is available.");
    }

    public async Task DownloadAndStartAsync(UpdateManifest manifest, Window owner)
    {
        if (manifest.PayloadParts.Count == 0) throw new InvalidDataException("The update payload list is empty.");
        var work = Path.Combine(Path.GetTempPath(), "TheTomeWpfUpdate-" + Guid.NewGuid().ToString("N"));
        var payloadDir = Path.Combine(work, "payload");
        Directory.CreateDirectory(payloadDir);
        using var combined = new MemoryStream();

        foreach (var part in manifest.PayloadParts)
        {
            var bytes = await _http.GetByteArrayAsync(part.Url);
            VerifyHash(bytes, part.Sha256, "An update part failed its safety check.");
            combined.Write(bytes);
        }

        var payloadBytes = combined.ToArray();
        VerifyHash(payloadBytes, manifest.PayloadSha256, "The update payload failed its safety check.");
        var payload = JsonSerializer.Deserialize<UpdatePayload>(payloadBytes, JsonOptions)
            ?? throw new InvalidDataException("The update payload could not be read.");
        if (payload.AppId != "the-tome-wpf" || payload.Version != manifest.Version)
            throw new InvalidDataException("The update payload does not match the manifest.");

        foreach (var file in payload.Files)
        {
            var relative = file.Path.Replace('/', Path.DirectorySeparatorChar);
            var destination = Path.GetFullPath(Path.Combine(payloadDir, relative));
            if (!destination.StartsWith(Path.GetFullPath(payloadDir) + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase))
                throw new InvalidDataException("The update contained an unsafe path.");
            Directory.CreateDirectory(Path.GetDirectoryName(destination)!);
            var bytes = Convert.FromBase64String(file.ContentBase64);
            VerifyHash(bytes, file.Sha256, $"{file.Path} failed verification.");
            await File.WriteAllBytesAsync(destination, bytes);
        }

        if (payload.Delete.Count > 0) await File.WriteAllLinesAsync(Path.Combine(payloadDir, "_delete.txt"), payload.Delete);
        if (!File.Exists(Path.Combine(payloadDir, "TheTome.exe"))) throw new InvalidDataException("The update does not contain TheTome.exe.");

        var currentExe = Environment.ProcessPath ?? throw new InvalidOperationException("The Tome could not locate its executable.");
        var updater = Path.Combine(work, "TheTome-Updater.exe");
        File.Copy(currentExe, updater, true);
        Process.Start(new ProcessStartInfo(updater)
        {
            UseShellExecute = true,
            ArgumentList = { "--apply-update", Environment.ProcessId.ToString(), payloadDir, _appDir }
        });
        owner.Close();
    }

    private static void VerifyHash(byte[] bytes, string expected, string message)
    {
        var actual = Convert.ToHexString(SHA256.HashData(bytes)).ToLowerInvariant();
        if (!actual.Equals(expected.Trim(), StringComparison.OrdinalIgnoreCase)) throw new InvalidDataException(message);
    }

    private static string ReadCurrentVersion(string appDir)
    {
        try
        {
            var path = Path.Combine(appDir, "AppVersion.json");
            using var json = JsonDocument.Parse(File.ReadAllText(path));
            var version = json.RootElement.GetProperty("version").GetString();
            if (!string.IsNullOrWhiteSpace(version)) return version;
        }
        catch { }

        var assembly = Assembly.GetExecutingAssembly().GetName().Version;
        return assembly is null ? "1.0.0" : $"{assembly.Major}.{assembly.Minor}.{Math.Max(0, assembly.Build)}";
    }
}

public sealed record UpdateCheckResult(UpdateManifest? Manifest, string Message);

public sealed class UpdateManifest
{
    public int SchemaVersion { get; set; }
    public string AppId { get; set; } = "";
    public string AppName { get; set; } = "";
    public string Version { get; set; } = "";
    public string PayloadSha256 { get; set; } = "";
    public List<UpdatePart> PayloadParts { get; set; } = [];
    public string Notes { get; set; } = "";
}

public sealed class UpdatePart
{
    public string Url { get; set; } = "";
    public string Sha256 { get; set; } = "";
}

public sealed class UpdatePayload
{
    public int SchemaVersion { get; set; }
    public string AppId { get; set; } = "";
    public string AppName { get; set; } = "";
    public string Version { get; set; } = "";
    public List<UpdateFile> Files { get; set; } = [];
    public List<string> Delete { get; set; } = [];
}

public sealed class UpdateFile
{
    public string Path { get; set; } = "";
    public string Sha256 { get; set; } = "";
    public string ContentBase64 { get; set; } = "";
}
