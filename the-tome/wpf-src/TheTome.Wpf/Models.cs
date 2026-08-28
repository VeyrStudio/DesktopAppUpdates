using System.ComponentModel;
using System.Runtime.CompilerServices;

namespace TheTome;

public sealed class BookRecord : INotifyPropertyChanged
{
    private string _title = "";
    private string _author = "";
    private string _series = "";
    private string _bookNumber = "";
    private string _status = "Unread";
    private double _progress;
    private string _notes = "";

    public string Id { get; set; } = Guid.NewGuid().ToString("N");
    public string Title { get => _title; set => Set(ref _title, value); }
    public string Author { get => _author; set => Set(ref _author, value); }
    public string Series { get => _series; set => Set(ref _series, value); }
    public string BookNumber { get => _bookNumber; set => Set(ref _bookNumber, value); }
    public string FilePath { get; set; } = "";
    public string CoverPath { get; set; } = "";
    public string Description { get; set; } = "";
    public string Status { get => _status; set => Set(ref _status, value); }
    public double Progress { get => _progress; set => Set(ref _progress, Math.Clamp(value, 0, 100)); }
    public string Notes { get => _notes; set => Set(ref _notes, value); }
    public DateTime AddedAt { get; set; } = DateTime.Now;
    public DateTime? LastReadAt { get; set; }
    public string Sha256 { get; set; } = "";
    public string FileName => Path.GetFileName(FilePath);
    public string SeriesLine => string.IsNullOrWhiteSpace(Series) ? "Standalone" : string.IsNullOrWhiteSpace(BookNumber) ? Series : $"{Series} • Book {BookNumber}";

    public event PropertyChangedEventHandler? PropertyChanged;
    private void Set<T>(ref T field, T value, [CallerMemberName] string? name = null)
    {
        if (EqualityComparer<T>.Default.Equals(field, value)) return;
        field = value;
        PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(name));
    }
}

public sealed class SeriesGroup
{
    public string Name { get; set; } = "";
    public List<BookRecord> Books { get; set; } = [];
    public string CountText => Books.Count == 1 ? "1 book" : $"{Books.Count} books";
}

public sealed class WindowPrefs
{
    public double Width { get; set; } = 1280;
    public double Height { get; set; } = 820;
    public double Left { get; set; } = double.NaN;
    public double Top { get; set; } = double.NaN;
    public bool Maximized { get; set; }
    public bool AutomaticUpdates { get; set; } = true;
}
