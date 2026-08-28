using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Runtime.CompilerServices;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Windows.Media.Imaging;

namespace TheLibrary;

public abstract class ObservableObject : INotifyPropertyChanged
{
    public event PropertyChangedEventHandler? PropertyChanged;
    protected bool Set<T>(ref T field, T value, [CallerMemberName] string? name = null)
    {
        if (EqualityComparer<T>.Default.Equals(field, value)) return false;
        field = value;
        PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(name));
        return true;
    }
    protected void Raise([CallerMemberName] string? name = null) =>
        PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(name));
}

public sealed class CoverItem : ObservableObject
{
    private string _id = Guid.NewGuid().ToString("N");
    private string _originalName = "";
    private string _storedName = "";
    private string _position = "Front Cover";
    private string _coverType = "Unsorted";
    private string _project = "";
    private string _ship = "";
    private string _fandom = "";
    private string _tags = "";
    private string _parentId = "";
    private bool _generated;
    private string _addedAt = DateTimeOffset.Now.ToString("O");
    private long _size;
    private string _hash = "";
    private bool _archived;

    public string Id { get => _id; set => Set(ref _id, value ?? ""); }
    public string OriginalName { get => _originalName; set => Set(ref _originalName, value ?? ""); }
    public string StoredName { get => _storedName; set => Set(ref _storedName, value ?? ""); }
    public string Position { get => _position; set => Set(ref _position, value ?? ""); }
    public string CoverType { get => _coverType; set => Set(ref _coverType, value ?? "Unsorted"); }
    public string Project { get => _project; set => Set(ref _project, value ?? ""); }
    public string Ship { get => _ship; set => Set(ref _ship, value ?? ""); }
    public string Fandom { get => _fandom; set => Set(ref _fandom, value ?? ""); }
    public string Tags { get => _tags; set => Set(ref _tags, value ?? ""); }
    public string ParentId { get => _parentId; set => Set(ref _parentId, value ?? ""); }
    public bool Generated { get => _generated; set => Set(ref _generated, value); }
    public string AddedAt { get => _addedAt; set => Set(ref _addedAt, value ?? ""); }
    public long Size { get => _size; set => Set(ref _size, value); }
    public string Hash { get => _hash; set => Set(ref _hash, value ?? ""); }
    public bool Archived { get => _archived; set => Set(ref _archived, value); }

    [JsonExtensionData]
    public Dictionary<string, JsonElement>? Extra { get; set; }
}

public sealed class ArchiveCard
{
    public required string Key { get; init; }
    public required string Title { get; init; }
    public required string Fandom { get; init; }
    public required string Ship { get; init; }
    public required string PanelSummary { get; init; }
    public required ObservableCollection<CoverItem> Items { get; init; }
    public BitmapImage? CoverImage { get; init; }
    public bool IsComplete { get; init; }
}

public sealed class WrapJob : ObservableObject
{
    private int _left;
    private int _right;
    private string _project = "";
    private string _ship = "";
    private string _fandom = "";
    private string _tags = "";
    private string _coverType = "FanFiction";
    private string _status = "Not saved";
    private BitmapSource? _backPreview;
    private BitmapSource? _spinePreview;
    private BitmapSource? _frontPreview;

    public required string SourcePath { get; init; }
    public required BitmapSource SourceBitmap { get; init; }
    public string FileName => Path.GetFileName(SourcePath);
    public int PixelWidth => SourceBitmap.PixelWidth;
    public int PixelHeight => SourceBitmap.PixelHeight;
    public int Left { get => _left; set { if (Set(ref _left, value)) Raise(nameof(GuideSummary)); } }
    public int Right { get => _right; set { if (Set(ref _right, value)) Raise(nameof(GuideSummary)); } }
    public string Project { get => _project; set => Set(ref _project, value); }
    public string Ship { get => _ship; set => Set(ref _ship, value); }
    public string Fandom { get => _fandom; set => Set(ref _fandom, value); }
    public string Tags { get => _tags; set => Set(ref _tags, value); }
    public string CoverType { get => _coverType; set => Set(ref _coverType, value); }
    public string Status { get => _status; set => Set(ref _status, value); }
    public BitmapSource? BackPreview { get => _backPreview; set => Set(ref _backPreview, value); }
    public BitmapSource? SpinePreview { get => _spinePreview; set => Set(ref _spinePreview, value); }
    public BitmapSource? FrontPreview { get => _frontPreview; set => Set(ref _frontPreview, value); }
    public string GuideSummary => $"Back {Left}px  •  Spine {Math.Max(0, Right - Left)}px  •  Front {Math.Max(0, PixelWidth - Right)}px";
}
