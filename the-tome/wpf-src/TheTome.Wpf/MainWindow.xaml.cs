using Microsoft.Win32;
using System.Collections.ObjectModel;
using System.Diagnostics;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media.Imaging;

namespace TheTome;

public partial class MainWindow : Window
{
    private readonly LibraryStore _store = new();
    private readonly UpdateService _updates;
    private BookRecord? _selected;
    private WindowPrefs _prefs = new();
    private bool _loaded;
    private bool _seriesMode;

    public MainWindow()
    {
        InitializeComponent();
        _updates = new UpdateService(AppContext.BaseDirectory);
        Loaded += MainWindow_Loaded;
        Closing += MainWindow_Closing;
    }

    private async void MainWindow_Loaded(object sender, RoutedEventArgs e)
    {
        _prefs = await _store.LoadPrefsAsync();
        if (_prefs.Width >= MinWidth) Width = _prefs.Width;
        if (_prefs.Height >= MinHeight) Height = _prefs.Height;
        if (!double.IsNaN(_prefs.Left) && !double.IsNaN(_prefs.Top))
        {
            Left = _prefs.Left;
            Top = _prefs.Top;
        }
        if (_prefs.Maximized) WindowState = WindowState.Maximized;

        UpdateStatusText.Text = "Loading library…";
        await _store.LoadAsync();
        RefreshViews();
        UpdateStatusText.Text = $"WPF {_updates.CurrentVersion}";
        _loaded = true;

        if (_prefs.AutomaticUpdates)
            await CheckForUpdatesAsync(false);
    }

    private async void MainWindow_Closing(object? sender, System.ComponentModel.CancelEventArgs e)
    {
        if (!_loaded) return;
        try
        {
            await _store.SaveAsync();
            var bounds = RestoreBounds;
            _prefs.Width = bounds.Width;
            _prefs.Height = bounds.Height;
            _prefs.Left = bounds.Left;
            _prefs.Top = bounds.Top;
            _prefs.Maximized = WindowState == WindowState.Maximized;
            await _store.SavePrefsAsync(_prefs);
        }
        catch { }
    }

    private void RefreshViews()
    {
        if (!_loaded && _store.Books.Count == 0) { }
        IEnumerable<BookRecord> books = _store.Books;

        var query = SearchBox.Text?.Trim();
        if (!string.IsNullOrWhiteSpace(query))
        {
            books = books.Where(b =>
                b.Title.Contains(query, StringComparison.OrdinalIgnoreCase) ||
                b.Author.Contains(query, StringComparison.OrdinalIgnoreCase) ||
                b.Series.Contains(query, StringComparison.OrdinalIgnoreCase));
        }

        var filter = (FilterBox.SelectedItem as ComboBoxItem)?.Content?.ToString() ?? "All";
        books = filter switch
        {
            "Unread" or "Reading" or "Finished" => books.Where(b => b.Status.Equals(filter, StringComparison.OrdinalIgnoreCase)),
            "Series" => books.Where(b => !string.IsNullOrWhiteSpace(b.Series)),
            "Standalone" => books.Where(b => string.IsNullOrWhiteSpace(b.Series)),
            _ => books
        };

        var sort = (SortBox.SelectedItem as ComboBoxItem)?.Content?.ToString() ?? "Recently Added";
        books = sort switch
        {
            "Title" => books.OrderBy(b => b.Title, StringComparer.CurrentCultureIgnoreCase),
            "Author" => books.OrderBy(b => b.Author, StringComparer.CurrentCultureIgnoreCase).ThenBy(b => b.Title),
            "Status" => books.OrderBy(b => b.Status).ThenBy(b => b.Title),
            _ => books.OrderByDescending(b => b.AddedAt)
        };

        var list = books.ToList();
        RecentItems.ItemsSource = list.OrderByDescending(b => b.AddedAt).Take(12).ToList();
        AllItems.ItemsSource = list;

        SeriesItems.ItemsSource = list.Where(b => !string.IsNullOrWhiteSpace(b.Series))
            .GroupBy(b => b.Series.Trim(), StringComparer.CurrentCultureIgnoreCase)
            .OrderBy(g => g.Key, StringComparer.CurrentCultureIgnoreCase)
            .Select(g => new SeriesGroup
            {
                Name = g.Key,
                Books = g.OrderBy(b => ParseNumber(b.BookNumber)).ThenBy(b => b.Title).ToList()
            }).ToList();

        var seriesCount = _store.Books.Where(b => !string.IsNullOrWhiteSpace(b.Series))
            .Select(b => b.Series.Trim()).Distinct(StringComparer.CurrentCultureIgnoreCase).Count();
        LibraryCountText.Text = $"{_store.Books.Count} books  •  {seriesCount} series  •  {_store.ManagedRoot}";
    }

    private static decimal ParseNumber(string value) => decimal.TryParse(value, out var n) ? n : decimal.MaxValue;

    private void Book_Click(object sender, RoutedEventArgs e)
    {
        if (sender is not Button { Tag: BookRecord book }) return;
        SelectBook(book);
    }

    private void SelectBook(BookRecord book)
    {
        _selected = book;
        DetailsPanel.DataContext = book;
        CoverPlaceholder.Visibility = string.IsNullOrWhiteSpace(book.CoverPath) || !File.Exists(book.CoverPath)
            ? Visibility.Visible : Visibility.Collapsed;
        if (!string.IsNullOrWhiteSpace(book.CoverPath) && File.Exists(book.CoverPath))
        {
            try
            {
                var bmp = new BitmapImage();
                bmp.BeginInit();
                bmp.CacheOption = BitmapCacheOption.OnLoad;
                bmp.UriSource = new Uri(book.CoverPath);
                bmp.EndInit();
                bmp.Freeze();
                CoverImage.Source = bmp;
            }
            catch { CoverImage.Source = null; }
        }
        else CoverImage.Source = null;
    }

    private async void AddBook_Click(object sender, RoutedEventArgs e)
    {
        var picker = new OpenFileDialog
        {
            Title = "Add a book to The Tome",
            Filter = "Ebooks|*.epub;*.pdf;*.mobi;*.azw;*.azw3|All files|*.*",
            Multiselect = false
        };
        if (picker.ShowDialog(this) != true) return;

        try
        {
            UpdateStatusText.Text = "Importing book…";
            var book = await _store.ImportAsync(picker.FileName);
            RefreshViews();
            SelectBook(book);
            UpdateStatusText.Text = $"Added {book.Title}";
        }
        catch (DuplicateBookException ex)
        {
            if (MessageBox.Show($"{ex.Message}\n\nOpen the existing book?", "Duplicate Book",
                MessageBoxButton.YesNo, MessageBoxImage.Information) == MessageBoxResult.Yes)
                SelectBook(ex.Existing);
            UpdateStatusText.Text = "Duplicate import cancelled";
        }
        catch (Exception ex)
        {
            MessageBox.Show(ex.Message, "The Tome", MessageBoxButton.OK, MessageBoxImage.Error);
            UpdateStatusText.Text = "Import failed";
        }
    }

    private void SearchBox_TextChanged(object sender, TextChangedEventArgs e) => RefreshViews();
    private void SortFilter_Changed(object sender, SelectionChangedEventArgs e) { if (IsLoaded) RefreshViews(); }

    private void LibraryMode_Click(object sender, RoutedEventArgs e)
    {
        _seriesMode = false;
        LibrarySections.Visibility = Visibility.Visible;
        SeriesSection.Visibility = Visibility.Collapsed;
    }

    private void SeriesMode_Click(object sender, RoutedEventArgs e)
    {
        _seriesMode = true;
        LibrarySections.Visibility = Visibility.Collapsed;
        SeriesSection.Visibility = Visibility.Visible;
    }

    private async void SaveDetails_Click(object sender, RoutedEventArgs e)
    {
        if (_selected == null) return;
        await _store.SaveAsync();
        RefreshViews();
        UpdateStatusText.Text = "Book details saved";
    }

    private void Read_Click(object sender, RoutedEventArgs e)
    {
        if (_selected == null) return;
        if (Path.GetExtension(_selected.FilePath).Equals(".epub", StringComparison.OrdinalIgnoreCase))
        {
            if (_selected.Status == "Unread") _selected.Status = "Reading";
            _selected.LastReadAt = DateTime.Now;
            var reader = new ReaderWindow(_selected) { Owner = this };
            reader.ShowDialog();
            _ = _store.SaveAsync();
        }
        else
        {
            MessageBox.Show("The WPF migration reader currently renders EPUB inside The Tome. PDF/MOBI/AZW/AZW3 rendering is being ported next.\n\nUse Open Externally for this book for now.",
                "Reader Migration", MessageBoxButton.OK, MessageBoxImage.Information);
        }
    }

    private void OpenExternal_Click(object sender, RoutedEventArgs e)
    {
        if (_selected == null || !File.Exists(_selected.FilePath)) return;
        Process.Start(new ProcessStartInfo(_selected.FilePath) { UseShellExecute = true });
    }

    private async void ChangeCover_Click(object sender, RoutedEventArgs e)
    {
        if (_selected == null) return;
        var picker = new OpenFileDialog
        {
            Title = "Choose a cover",
            Filter = "Images|*.png;*.jpg;*.jpeg;*.webp;*.bmp"
        };
        if (picker.ShowDialog(this) != true) return;
        try
        {
            var ext = Path.GetExtension(picker.FileName);
            var destination = Path.Combine(_store.CoversRoot, _selected.Id + ext);
            File.Copy(picker.FileName, destination, true);
            _selected.CoverPath = destination;
            await _store.SaveAsync();
            SelectBook(_selected);
        }
        catch (Exception ex) { MessageBox.Show(ex.Message, "Change Cover", MessageBoxButton.OK, MessageBoxImage.Error); }
    }

    private void Export_Click(object sender, RoutedEventArgs e)
    {
        if (_selected == null || !File.Exists(_selected.FilePath)) return;
        var save = new SaveFileDialog
        {
            Title = "Export original ebook",
            FileName = Path.GetFileName(_selected.FilePath),
            Filter = "Original format|*" + Path.GetExtension(_selected.FilePath)
        };
        if (save.ShowDialog(this) == true) File.Copy(_selected.FilePath, save.FileName, true);
    }

    private async void Remove_Click(object sender, RoutedEventArgs e)
    {
        if (_selected == null) return;
        var result = MessageBox.Show(
            $"Remove “{_selected.Title}” from The Tome?\n\nYes = remove the managed ebook file too.\nNo = remove it from the catalog only.\nCancel = keep everything.",
            "Remove Book", MessageBoxButton.YesNoCancel, MessageBoxImage.Warning);
        if (result == MessageBoxResult.Cancel) return;
        await _store.RemoveAsync(_selected, result == MessageBoxResult.Yes);
        _selected = null;
        DetailsPanel.DataContext = null;
        CoverImage.Source = null;
        CoverPlaceholder.Visibility = Visibility.Visible;
        RefreshViews();
    }

    private async void UpdateNow_Click(object sender, RoutedEventArgs e) => await CheckForUpdatesAsync(true);

    private async Task CheckForUpdatesAsync(bool manual)
    {
        try
        {
            UpdateStatusText.Text = manual ? "Checking for updates…" : $"WPF {_updates.CurrentVersion} • checking updates…";
            var result = await _updates.CheckAsync();
            if (result.Manifest == null)
            {
                UpdateStatusText.Text = $"WPF {_updates.CurrentVersion} • up to date";
                if (manual) MessageBox.Show(result.Message, "The Tome Update", MessageBoxButton.OK, MessageBoxImage.Information);
                return;
            }

            UpdateStatusText.Text = $"Updating to {result.Manifest.Version}…";
            if (manual || _prefs.AutomaticUpdates)
                await _updates.DownloadAndStartAsync(result.Manifest, this);
        }
        catch (Exception ex)
        {
            UpdateStatusText.Text = $"WPF {_updates.CurrentVersion} • update check failed";
            if (manual) MessageBox.Show(ex.Message, "The Tome Update", MessageBoxButton.OK, MessageBoxImage.Warning);
        }
    }
}
