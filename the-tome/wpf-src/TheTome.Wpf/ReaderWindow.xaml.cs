using System.IO.Compression;
using System.Windows;
using System.Windows.Documents;
using System.Xml.Linq;

namespace TheTome;

public partial class ReaderWindow : Window
{
    private readonly BookRecord _book;

    public ReaderWindow(BookRecord book)
    {
        InitializeComponent();
        _book = book;
        ReaderTitle.Text = book.Title;
        LoadBook();
    }

    private void LoadBook()
    {
        var doc = new FlowDocument
        {
            PagePadding = new Thickness(20),
            FontFamily = new System.Windows.Media.FontFamily("Crimson Pro, Georgia"),
            FontSize = FontSlider.Value,
            Foreground = new System.Windows.Media.SolidColorBrush(System.Windows.Media.Color.FromRgb(37, 23, 43))
        };

        try
        {
            if (Path.GetExtension(_book.FilePath).Equals(".epub", StringComparison.OrdinalIgnoreCase))
            {
                LoadEpub(doc, _book.FilePath);
            }
            else
            {
                doc.Blocks.Add(new Paragraph(new Run("This format is not yet rendered inside the WPF reader.")) { FontSize = 22, FontWeight = FontWeights.SemiBold });
                doc.Blocks.Add(new Paragraph(new Run("Use “Open externally” from the book details for this migration build.")));
            }
        }
        catch (Exception ex)
        {
            doc.Blocks.Add(new Paragraph(new Run("The Tome could not render this book.")) { FontWeight = FontWeights.Bold });
            doc.Blocks.Add(new Paragraph(new Run(ex.Message)));
        }
        Viewer.Document = doc;
    }

    private static void LoadEpub(FlowDocument doc, string file)
    {
        using var zip = ZipFile.OpenRead(file);
        var containerEntry = zip.GetEntry("META-INF/container.xml") ?? throw new InvalidDataException("EPUB container.xml is missing.");
        XDocument container;
        using (var stream = containerEntry.Open()) container = XDocument.Load(stream);
        var opfPath = container.Descendants().FirstOrDefault(x => x.Name.LocalName == "rootfile")?.Attribute("full-path")?.Value
            ?? throw new InvalidDataException("EPUB package path is missing.");
        var opfEntry = zip.GetEntry(opfPath.Replace('\\','/')) ?? throw new InvalidDataException("EPUB package file is missing.");
        XDocument opf;
        using (var stream = opfEntry.Open()) opf = XDocument.Load(stream);

        var manifest = opf.Descendants().Where(x => x.Name.LocalName == "item")
            .Select(x => new { Id = (string?)x.Attribute("id"), Href = (string?)x.Attribute("href"), Type = (string?)x.Attribute("media-type") })
            .Where(x => !string.IsNullOrWhiteSpace(x.Id) && !string.IsNullOrWhiteSpace(x.Href))
            .ToDictionary(x => x.Id!, x => x);

        var baseDir = Path.GetDirectoryName(opfPath)?.Replace('\\','/') ?? "";
        var itemRefs = opf.Descendants().Where(x => x.Name.LocalName == "itemref")
            .Select(x => (string?)x.Attribute("idref")).Where(x => !string.IsNullOrWhiteSpace(x));

        var chapterCount = 0;
        foreach (var id in itemRefs)
        {
            if (!manifest.TryGetValue(id!, out var item)) continue;
            if (item.Type is not null && !item.Type.Contains("html", StringComparison.OrdinalIgnoreCase)) continue;
            var entryPath = Normalize(string.IsNullOrWhiteSpace(baseDir) ? item.Href! : baseDir + "/" + item.Href);
            var entry = zip.GetEntry(entryPath);
            if (entry == null) continue;
            XDocument xhtml;
            try { using var stream = entry.Open(); xhtml = XDocument.Load(stream); }
            catch { continue; }

            var body = xhtml.Descendants().FirstOrDefault(x => x.Name.LocalName == "body");
            if (body == null) continue;
            chapterCount++;

            foreach (var el in body.Descendants().Where(x => new[] { "h1","h2","h3","p","blockquote","li" }.Contains(x.Name.LocalName)))
            {
                var text = string.Join(" ", el.DescendantNodes().OfType<XText>().Select(t => t.Value)).Trim();
                if (string.IsNullOrWhiteSpace(text)) continue;
                var p = new Paragraph(new Run(text))
                {
                    Margin = el.Name.LocalName.StartsWith("h") ? new Thickness(0, 22, 0, 10) : new Thickness(0, 0, 0, 12),
                    FontSize = el.Name.LocalName switch { "h1" => 30, "h2" => 26, "h3" => 23, _ => doc.FontSize },
                    FontWeight = el.Name.LocalName.StartsWith("h") ? FontWeights.SemiBold : FontWeights.Normal,
                    TextAlignment = TextAlignment.Left
                };
                doc.Blocks.Add(p);
            }
        }

        if (chapterCount == 0) throw new InvalidDataException("No readable EPUB chapters were found.");
    }

    private static string Normalize(string path)
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

    private void FontSlider_ValueChanged(object sender, RoutedPropertyChangedEventArgs<double> e)
    {
        if (Viewer?.Document != null) Viewer.Document.FontSize = e.NewValue;
    }

    private void Back_Click(object sender, RoutedEventArgs e) => Close();
}
