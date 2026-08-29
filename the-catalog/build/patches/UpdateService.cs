using System.IO;
using System.Threading;
using System.Diagnostics;
using System.Net.Http;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Windows;

namespace TheCatalog.Services;

public sealed class UpdateManifest
{
    public int SchemaVersion { get; set; }
    public string AppId { get; set; } = string.Empty;
    public string AppName { get; set; } = string.Empty;
    public string Version { get; set; } = string.Empty;
    public string PayloadSha256 { get; set; } = string.Empty;
    public List<UpdatePayloadPart> PayloadParts { get; set; } = new();
    public string Notes { get; set; } = string.Empty;
}

public sealed class UpdatePayloadPart
{
    public string Url { get; set; } = string.Empty;
    public string Sha256 { get; set; } = string.Empty;
}

public static class UpdateService
{
    public const string ManifestUrl = "https://raw.githubusercontent.com/VeyrStudio/DesktopAppUpdates/main/the-catalog/manifest.json";
    private static readonly HttpClient Client = CreateClient();

    public static Version CurrentVersion => Assembly.GetExecutingAssembly().GetName().Version ?? new Version(1, 0, 0, 0);

    private static HttpClient CreateClient()
    {
        var client = new HttpClient { Timeout = TimeSpan.FromMinutes(10) };
        client.DefaultRequestHeaders.UserAgent.ParseAdd("TheCatalog-WPF-Updater/1.0");
        return client;
    }

    public static async Task<bool> CheckAndInstallAsync(bool manual, Action<string>? status = null)
    {
        if (manual) status?.Invoke("Checking for updates...");

        var manifest = await GetManifestAsync();
        if (!Version.TryParse(manifest.Version, out var latest))
            throw new InvalidDataException("The update manifest has an invalid version number.");

        if (latest <= CurrentVersion)
        {
            if (manual) status?.Invoke("The Catalog is up to date.");
            return false;
        }

        status?.Invoke($"Downloading The Catalog {latest}...");
        var executable = await DownloadPayloadAsync(manifest, status);
        if (executable.Length < 2 || executable[0] != (byte)'M' || executable[1] != (byte)'Z')
            throw new InvalidDataException("The downloaded update is not a valid Windows executable.");

        var target = Environment.ProcessPath;
        if (string.IsNullOrWhiteSpace(target) || !File.Exists(target))
            throw new InvalidOperationException("The Catalog could not locate its running executable.");

        var tempDirectory = Path.Combine(Path.GetTempPath(), $"TheCatalog-Update-{Guid.NewGuid():N}");
        Directory.CreateDirectory(tempDirectory);
        var stagedExe = Path.Combine(tempDirectory, "TheCatalog.exe");
        await File.WriteAllBytesAsync(stagedExe, executable);

        status?.Invoke("Update ready. Restarting The Catalog...");

        var start = new ProcessStartInfo
        {
            FileName = stagedExe,
            UseShellExecute = false,
            WorkingDirectory = tempDirectory
        };
        start.ArgumentList.Add("--catalog-updater");
        start.ArgumentList.Add(target);
        start.ArgumentList.Add("--pid");
        start.ArgumentList.Add(Environment.ProcessId.ToString());
        _ = Process.Start(start) ?? throw new InvalidOperationException("The Catalog could not start the updater.");

        Application.Current.Dispatcher.BeginInvoke(() => Application.Current.Shutdown());
        return true;
    }

    private static async Task<UpdateManifest> GetManifestAsync()
    {
        var uri = $"{ManifestUrl}?v={DateTimeOffset.UtcNow.ToUnixTimeSeconds()}";
        var json = await Client.GetStringAsync(uri);
        var manifest = JsonSerializer.Deserialize<UpdateManifest>(json, new JsonSerializerOptions
        {
            PropertyNameCaseInsensitive = true
        });
        if (manifest is null || !string.Equals(manifest.AppId, "the-catalog-wpf", StringComparison.OrdinalIgnoreCase))
            throw new InvalidDataException("The Catalog received an invalid update manifest.");
        if (manifest.PayloadParts.Count == 0)
            throw new InvalidDataException("The update manifest does not contain a downloadable payload.");
        return manifest;
    }

    private static async Task<byte[]> DownloadPayloadAsync(UpdateManifest manifest, Action<string>? status)
    {
        var combined = new StringBuilder();
        for (var i = 0; i < manifest.PayloadParts.Count; i++)
        {
            var part = manifest.PayloadParts[i];
            if (!Uri.TryCreate(part.Url, UriKind.Absolute, out var uri) || uri.Scheme != Uri.UriSchemeHttps)
                throw new InvalidDataException("The update manifest contains an invalid download URL.");

            status?.Invoke($"Downloading update... {i + 1}/{manifest.PayloadParts.Count}");
            var bytes = await Client.GetByteArrayAsync(uri);
            VerifySha256(bytes, part.Sha256, $"update part {i + 1}");
            combined.Append(Encoding.UTF8.GetString(bytes));
        }

        var payloadText = combined.ToString();
        VerifySha256(Encoding.UTF8.GetBytes(payloadText), manifest.PayloadSha256, "complete update payload");

        try
        {
            return Convert.FromBase64String(payloadText);
        }
        catch (FormatException ex)
        {
            throw new InvalidDataException("The update payload is corrupted.", ex);
        }
    }

    private static void VerifySha256(byte[] bytes, string expected, string label)
    {
        var actual = Convert.ToHexString(SHA256.HashData(bytes)).ToLowerInvariant();
        if (!actual.Equals(expected?.Trim(), StringComparison.OrdinalIgnoreCase))
            throw new InvalidDataException($"The {label} failed its integrity check.");
    }

    public static bool TryRunUpdaterMode(string[] args)
    {
        if (args.Length < 4 || !string.Equals(args[0], "--catalog-updater", StringComparison.Ordinal))
            return false;

        var target = args[1];
        if (!string.Equals(args[2], "--pid", StringComparison.Ordinal) || !int.TryParse(args[3], out var oldPid))
            return true;

        try
        {
            try
            {
                using var oldProcess = Process.GetProcessById(oldPid);
                oldProcess.WaitForExit(90_000);
            }
            catch (ArgumentException) { }

            var source = Environment.ProcessPath ?? throw new InvalidOperationException("Updater executable path is unavailable.");
            Directory.CreateDirectory(Path.GetDirectoryName(target)!);

            Exception? lastError = null;
            for (var attempt = 0; attempt < 30; attempt++)
            {
                try
                {
                    File.Copy(source, target, true);
                    lastError = null;
                    break;
                }
                catch (Exception ex) when (ex is IOException or UnauthorizedAccessException)
                {
                    lastError = ex;
                    Thread.Sleep(1000);
                }
            }
            if (lastError is not null) throw lastError;

            Process.Start(new ProcessStartInfo
            {
                FileName = target,
                UseShellExecute = true,
                WorkingDirectory = Path.GetDirectoryName(target)!
            });
        }
        catch (Exception ex)
        {
            MessageBox.Show($"The Catalog downloaded an update, but could not replace the current app file.\n\n{ex.Message}", "The Catalog Update", MessageBoxButton.OK, MessageBoxImage.Error);
        }

        return true;
    }

    public static void CleanupOldUpdateFiles()
    {
        try
        {
            var temp = Path.GetTempPath();
            foreach (var directory in Directory.EnumerateDirectories(temp, "TheCatalog-Update-*"))
            {
                try
                {
                    var info = new DirectoryInfo(directory);
                    if (DateTime.UtcNow - info.CreationTimeUtc > TimeSpan.FromHours(2))
                        info.Delete(true);
                }
                catch { }
            }
        }
        catch { }
    }
}