using System.IO.Compression;
using System.Security.Cryptography;
using System.Text.Json;
using System.Windows;
using System.Windows.Media.Imaging;

namespace TheLibrary;

public sealed class LibraryStore
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        WriteIndented = true,
        PropertyNameCaseInsensitive = true
    };

    public string AppRoot { get; } = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "CoverVault");
    public string AppDir => Path.Combine(AppRoot, "App");
    public string DataRoot => Path.Combine(AppRoot, "Data");
    public string FilesRoot => Path.Combine(DataRoot, "Files");
    public string MetaFile => Path.Combine(DataRoot, "library.json");
    public List<CoverItem> Items { get; private set; } = [];

    public LibraryStore()
    {
        Directory.CreateDirectory(FilesRoot);
        if (!File.Exists(MetaFile)) File.WriteAllText(MetaFile, "[]");
    }

    public void Load()
    {
        try
        {
            Items = JsonSerializer.Deserialize<List<CoverItem>>(File.ReadAllText(MetaFile), JsonOptions) ?? [];
            foreach (var item in Items)
            {
                if (string.IsNullOrWhiteSpace(item.CoverType)) item.CoverType = "Unsorted";
            }
        }
        catch (Exception ex)
        {
            throw new InvalidDataException("The Library could not read library.json.", ex);
        }
    }

    public void Save() => AtomicWrite(MetaFile, JsonSerializer.Serialize(Items, JsonOptions));

    public string StoredPath(CoverItem item) => Path.Combine(FilesRoot, item.StoredName);

    public CoverItem ImportFile(string source, string position, string coverType, string project, string ship, string fandom, string tags, bool removeSource)
    {
        var extension = Path.GetExtension(source).ToLowerInvariant();
        if (string.IsNullOrWhiteSpace(extension)) extension = ".img";
        var stored = Guid.NewGuid().ToString("N") + extension;
        var destination = Path.Combine(FilesRoot, stored);
        File.Copy(source, destination, true);
        if (removeSource && !Path.GetFullPath(source).StartsWith(Path.GetFullPath(FilesRoot), StringComparison.OrdinalIgnoreCase))
        {
            try { File.Delete(source); } catch { }
        }

        var info = new FileInfo(destination);
        var item = new CoverItem
        {
            Id = Guid.NewGuid().ToString("N"), OriginalName = Path.GetFileName(source), StoredName = stored,
            Position = position, CoverType = coverType, Project = project.Trim(), Ship = ship.Trim(),
            Fandom = fandom.Trim(), Tags = NormalizeTags(tags), AddedAt = DateTimeOffset.Now.ToString("O"),
            Size = info.Length, Hash = Sha256(destination)
        };
        Items.Add(item);
        Save();
        return item;
    }

    public void AddCrop(BitmapSource source, Int32Rect rect, string originalName, string position,
        string coverType, string project, string ship, string fandom, string tags)
    {
        var stored = Guid.NewGuid().ToString("N") + ".png";
        var path = Path.Combine(FilesRoot, stored);
        var crop = new CroppedBitmap(source, rect);
        using (var stream = File.Create(path))
        {
            var encoder = new PngBitmapEncoder();
            encoder.Frames.Add(BitmapFrame.Create(crop));
            encoder.Save(stream);
        }
        var info = new FileInfo(path);
        Items.Add(new CoverItem
        {
            Id = Guid.NewGuid().ToString("N"), OriginalName = originalName, StoredName = stored,
            Position = position, CoverType = coverType, Project = project.Trim(), Ship = ship.Trim(),
            Fandom = fandom.Trim(), Tags = NormalizeTags(tags), Generated = true,
            AddedAt = DateTimeOffset.Now.ToString("O"), Size = info.Length, Hash = Sha256(path)
        });
    }

    public void Delete(IEnumerable<CoverItem> items)
    {
        foreach (var item in items.ToList())
        {
            try { var path = StoredPath(item); if (File.Exists(path)) File.Delete(path); } catch { }
            Items.RemoveAll(x => x.Id == item.Id);
        }
        Save();
    }

    public void ExportBackup(string destination)
    {
        if (File.Exists(destination)) File.Delete(destination);
        ZipFile.CreateFromDirectory(DataRoot, destination, CompressionLevel.Optimal, false);
    }

    public void RestoreBackup(string backup)
    {
        var temp = Path.Combine(Path.GetTempPath(), "TheLibraryRestore-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(temp);
        try
        {
            ZipFile.ExtractToDirectory(backup, temp);
            var candidate = File.Exists(Path.Combine(temp, "library.json")) ? temp : Path.Combine(temp, "Data");
            if (!File.Exists(Path.Combine(candidate, "library.json"))) throw new InvalidDataException("This backup does not contain library.json.");
            var recovery = Path.Combine(AppRoot, "Recovery Backups");
            Directory.CreateDirectory(recovery);
            ExportBackup(Path.Combine(recovery, $"Before Restore {DateTime.Now:yyyy-MM-dd HH-mm-ss}.zip"));
            if (Directory.Exists(DataRoot)) Directory.Delete(DataRoot, true);
            CopyDirectory(candidate, DataRoot);
            Directory.CreateDirectory(FilesRoot);
            Load();
        }
        finally { try { Directory.Delete(temp, true); } catch { } }
    }

    public static BitmapImage? LoadImage(string path, int decodeWidth = 0)
    {
        if (!File.Exists(path)) return null;
        try
        {
            var image = new BitmapImage();
            image.BeginInit();
            image.CacheOption = BitmapCacheOption.OnLoad;
            if (decodeWidth > 0) image.DecodePixelWidth = decodeWidth;
            image.StreamSource = new MemoryStream(File.ReadAllBytes(path));
            image.EndInit();
            image.Freeze();
            return image;
        }
        catch { return null; }
    }

    public static string NormalizeTags(string value) => string.Join(", ", value.Split(',', StringSplitOptions.TrimEntries | StringSplitOptions.RemoveEmptyEntries));
    public static string Sha256(string path) => Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path))).ToLowerInvariant();

    private static void AtomicWrite(string path, string value)
    {
        var temp = path + ".tmp";
        File.WriteAllText(temp, value);
        File.Move(temp, path, true);
    }

    private static void CopyDirectory(string source, string destination)
    {
        Directory.CreateDirectory(destination);
        foreach (var file in Directory.EnumerateFiles(source)) File.Copy(file, Path.Combine(destination, Path.GetFileName(file)), true);
        foreach (var dir in Directory.EnumerateDirectories(source)) CopyDirectory(dir, Path.Combine(destination, Path.GetFileName(dir)));
    }
}
