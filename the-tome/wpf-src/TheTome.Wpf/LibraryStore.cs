using System.IO.Compression;
using System.Security.Cryptography;
using System.Text.Json;
using System.Xml.Linq;

namespace TheTome;

public sealed class LibraryStore
{
    private static readonly JsonSerializerOptions JsonOptions = new() { WriteIndented = true, PropertyNameCaseInsensitive = true };
    public string DataRoot { get; } = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "VeyrStudio", "TheTomeWPF");
    public string ManagedRoot { get; } = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments), "The Tome Library");
    public string CoversRoot => Path.Combine(DataRoot, "Covers");
    public string LibraryPath => Path.Combine(DataRoot, "library.json");
    public string SettingsPath => Path.Combine(DataRoot, "settings.json");
    public List<BookRecord> Books { get; private set; } = [];

    public LibraryStore()
    {
        Directory.CreateDirectory(DataRoot);
        Directory.CreateDirectory(ManagedRoot);
        Directory.CreateDirectory(CoversRoot);
    }

    public async Task LoadAsync()
    {
        if (File.Exists(LibraryPath))
        {
            try { Books = JsonSerializer.Deserialize<List<BookRecord>>(await File.ReadAllTextAsync(LibraryPath), JsonOptions) ?? []; }
            catch { Books = []; }
        }

        var known = new HashSet<string>(Books.Where(b => !string.IsNullOrWhiteSpace(b.FilePath)).Select(b => SafeFull(b.FilePath)), StringComparer.OrdinalIgnoreCase);
        foreach (var file in Directory.EnumerateFiles(ManagedRoot, "*", SearchOption.AllDirectories).Where(IsSupported))
        {
            var full = SafeFull(file);
            if (known.Contains(full)) continue;
            var record = await BuildRecordAsync(file, false);
            Books.Add(record);
            known.Add(full);
        }

        Books.RemoveAll(b => string.IsNullOrWhiteSpace(b.FilePath));
        await SaveAsync();
    }

    public async Task<BookRecord> ImportAsync(string source)
    {
        if (!IsSupported(source)) throw new InvalidOperationException("The Tome supports EPUB, PDF, MOBI, AZW, and AZW3 files.");
        var hash = await HashFileAsync(source);
        var duplicate = Books.FirstOrDefault(b => !string.IsNullOrWhiteSpace(b.Sha256) && b.Sha256.Equals(hash, StringComparison.OrdinalIgnoreCase));
        if (duplicate != null) throw new DuplicateBookException(duplicate);

        var fileName = Path.GetFileName(source);
        var destination = UniquePath(Path.Combine(ManagedRoot, fileName));
        File.Copy(source, destination, false);
        var copyHash = await HashFileAsync(destination);
        if (!copyHash.Equals(hash, StringComparison.OrdinalIgnoreCase))
        {
            File.Delete(destination);
            throw new IOException("The managed copy failed verification.");
        }

        var record = await BuildRecordAsync(destination, true);
        record.Sha256 = hash;
        Books.Add(record);
        await SaveAsync();
        return record;
    }

    public async Task SaveAsync()
    {
        Directory.CreateDirectory(DataRoot);
        var temp = LibraryPath + ".tmp";
        await File.WriteAllTextAsync(temp, JsonSerializer.Serialize(Books, JsonOptions));
        File.Move(temp, LibraryPath, true);
    }

    public async Task<WindowPrefs> LoadPrefsAsync()
    {
        try
        {
            if (File.Exists(SettingsPath))
                return JsonSerializer.Deserialize<WindowPrefs>(await File.ReadAllTextAsync(SettingsPath), JsonOptions) ?? new WindowPrefs();
        }
        catch { }
        return new WindowPrefs();
    }

    public Task SavePrefsAsync(WindowPrefs prefs) =>
        File.WriteAllTextAsync(SettingsPath, JsonSerializer.Serialize(prefs, JsonOptions));

    public async Task RemoveAsync(BookRecord book, bool deleteManaged)
    {
        Books.Remove(book);
        if (deleteManaged && File.Exists(book.FilePath) && SafeFull(book.FilePath).StartsWith(SafeFull(ManagedRoot) + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase))
        {
            try { File.Delete(book.FilePath); } catch { }
        }
        if (!string.IsNullOrWhiteSpace(book.CoverPath) && File.Exists(book.CoverPath)) { try { File.Delete(book.CoverPath); } catch { } }
        await SaveAsync();
    }

    private async Task<BookRecord> BuildRecordAsync(string file, bool newlyAdded)
    {
        var record = new BookRecord
        {
            FilePath = Path.GetFullPath(file),
            Title = Path.GetFileNameWithoutExtension(file),
            Author = "Unknown Author",
            AddedAt = newlyAdded ? DateTime.Now : File.GetCreationTime(file)
        };
        try { record.Sha256 = await HashFileAsync(file); } catch { }

        if (Path.GetExtension(file).Equals(".epub", StringComparison.OrdinalIgnoreCase))
        {
            try { ReadEpubMetadata(file, record); } catch { }
        }
        return record;
    }

    private void ReadEpubMetadata(string file, BookRecord book)
    {
        using var zip = ZipFile.OpenRead(file);
        var container = zip.GetEntry("META-INF/container.xml") ?? return;
        XDocument containerXml;
        using (var stream = container.Open()) containerXml = XDocument.Load(stream);
        var rootFile = containerXml.Descendants().FirstOrDefault(x => x.Name.LocalName == "rootfile")?.Attribute("full-path")?.Value;
        if (string.IsNullOrWhiteSpace(rootFile)) return;
        var opfEntry = zip.GetEntry(rootFile.Replace('\\','/'));
        if (opfEntry == null) return;
        XDocument opf;
        using (var stream = opfEntry.Open()) opf = XDocument.Load(stream);

        string? Meta(string local) => opf.Descendants().FirstOrDefault(x => x.Name.LocalName == local)?.Value?.Trim();
        var title = Meta("title");
        var creator = Meta("creator");
        if (!string.IsNullOrWhiteSpace(title)) book.Title = title;
        if (!string.IsNullOrWhiteSpace(creator)) book.Author = creator;

        var series = opf.Descendants().FirstOrDefault(x => x.Name.LocalName == "meta" &&
            ((string?)x.Attribute("name"))?.Equals("calibre:series", StringComparison.OrdinalIgnoreCase) == true)?.Attribute("content")?.Value;
        var number = opf.Descendants().FirstOrDefault(x => x.Name.LocalName == "meta" &&
            ((string?)x.Attribute("name"))?.Equals("calibre:series_index", StringComparison.OrdinalIgnoreCase) == true)?.Attribute("content")?.Value;
        if (!string.IsNullOrWhiteSpace(series)) book.Series = series;
        if (!string.IsNullOrWhiteSpace(number)) book.BookNumber = number;

        var description = Meta("description");
        if (!string.IsNullOrWhiteSpace(description)) book.Description = description;

        var coverId = opf.Descendants().FirstOrDefault(x => x.Name.LocalName == "meta" &&
            ((string?)x.Attribute("name"))?.Equals("cover", StringComparison.OrdinalIgnoreCase) == true)?.Attribute("content")?.Value;
        var coverItem = opf.Descendants().FirstOrDefault(x => x.Name.LocalName == "item" &&
            ((!string.IsNullOrWhiteSpace(coverId) && (string?)x.Attribute("id") == coverId) ||
             (((string?)x.Attribute("properties"))?.Split(' ', StringSplitOptions.RemoveEmptyEntries).Contains("cover-image") == true)));
        var href = coverItem?.Attribute("href")?.Value;
        if (!string.IsNullOrWhiteSpace(href))
        {
            var baseDir = Path.GetDirectoryName(rootFile)?.Replace('\\','/') ?? "";
            var full = NormalizeZipPath(string.IsNullOrWhiteSpace(baseDir) ? href : baseDir + "/" + href);
            var imageEntry = zip.GetEntry(full);
            if (imageEntry != null)
            {
                var ext = Path.GetExtension(href);
                if (string.IsNullOrWhiteSpace(ext)) ext = ".jpg";
                var coverPath = Path.Combine(CoversRoot, book.Id + ext);
                using var input = imageEntry.Open();
                using var output = File.Create(coverPath);
                input.CopyTo(output);
                book.CoverPath = coverPath;
            }
        }
    }

    private static string NormalizeZipPath(string path)
    {
        var parts = new List<string>();
        foreach (var part in path.Replace('\\','/').Split('/'))
        {
            if (part == "." || part.Length == 0) continue;
            if (part == "..") { if (parts.Count > 0) parts.RemoveAt(parts.Count - 1); }
            else parts.Add(part);
        }
        return string.Join("/", parts);
    }

    public static bool IsSupported(string file)
    {
        var ext = Path.GetExtension(file);
        return new[] { ".epub", ".pdf", ".mobi", ".azw", ".azw3" }.Contains(ext, StringComparer.OrdinalIgnoreCase);
    }

    public static async Task<string> HashFileAsync(string file)
    {
        await using var stream = File.OpenRead(file);
        var hash = await SHA256.HashDataAsync(stream);
        return Convert.ToHexString(hash).ToLowerInvariant();
    }

    private static string UniquePath(string path)
    {
        if (!File.Exists(path)) return path;
        var dir = Path.GetDirectoryName(path)!;
        var name = Path.GetFileNameWithoutExtension(path);
        var ext = Path.GetExtension(path);
        for (var i = 2; ; i++)
        {
            var candidate = Path.Combine(dir, $"{name} ({i}){ext}");
            if (!File.Exists(candidate)) return candidate;
        }
    }

    private static string SafeFull(string p)
    {
        try { return Path.GetFullPath(p).TrimEnd(Path.DirectorySeparatorChar); }
        catch { return p; }
    }
}

public sealed class DuplicateBookException : Exception
{
    public BookRecord Existing { get; }
    public DuplicateBookException(BookRecord existing) : base($"This file already exists in The Tome as “{existing.Title}”.") => Existing = existing;
}
