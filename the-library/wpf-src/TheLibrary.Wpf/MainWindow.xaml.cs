using Microsoft.Win32;
using System.Collections.ObjectModel;
using System.Diagnostics;
using System.Globalization;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Controls.Primitives;
using System.Windows.Input;
using System.Windows.Media.Imaging;
using System.Windows.Threading;

namespace TheLibrary;

public partial class MainWindow : Window
{
    private enum ArchiveScope { All, Fandoms, Ships, Complete, Incomplete, Archived }

    private readonly LibraryStore _store = new();
    private readonly UpdateService _updates;
    private ArchiveScope _scope = ArchiveScope.All;
    private ArchiveCard? _selectedCard;
    private string? _singlePath;
    private WrapJob? _selectedJob;
    private bool _updatingWrapUi;
    private bool _updatingGuideUi;
    private double _zoom = 1;

    public ObservableCollection<ArchiveCard> Cards { get; } = [];
    public ObservableCollection<WrapJob> WrapJobs { get; } = [];

    public MainWindow()
    {
        InitializeComponent();
        ApplyStartupBounds();
        DataContext = this;
        _updates = new UpdateService(_store.AppDir);
        try { _store.Load(); }
        catch (Exception ex) { MessageBox.Show(ex.Message, "The Library", MessageBoxButton.OK, MessageBoxImage.Error); }
        StoragePath.Text = _store.DataRoot;
        VersionText.Text = $"Current version: {_updates.CurrentVersion}";
        RefreshArchive();
    }

    private void ApplyStartupBounds()
    {
        const double margin = 16;
        var workArea = SystemParameters.WorkArea;
        var maxWidth = Math.Max(MinWidth, workArea.Width - (margin * 2));
        var maxHeight = Math.Max(MinHeight, workArea.Height - (margin * 2));

        Width = Math.Min(Width, maxWidth);
        Height = Math.Min(Height, maxHeight);
        WindowStartupLocation = WindowStartupLocation.Manual;
        Left = workArea.Left + Math.Max(margin, (workArea.Width - Width) / 2);
        Top = workArea.Top + Math.Max(margin, (workArea.Height - Height) / 2);
    }

    private static string ComboText(ComboBox combo) =>
        (combo.SelectedItem as ComboBoxItem)?.Content?.ToString() ?? combo.Text ?? "";

    private void ShowPage(Grid page)
    {
        ArchivePage.Visibility = page == ArchivePage ? Visibility.Visible : Visibility.Collapsed;
        AddPage.Visibility = page == AddPage ? Visibility.Visible : Visibility.Collapsed;
        SettingsPage.Visibility = page == SettingsPage ? Visibility.Visible : Visibility.Collapsed;
    }

    private void AllCovers_Click(object sender, RoutedEventArgs e) { _scope = ArchiveScope.All; ArchiveHeading.Text = "Cover Archive"; ShowPage(ArchivePage); RefreshArchive(); }
    private void Fandoms_Click(object sender, RoutedEventArgs e) { _scope = ArchiveScope.Fandoms; ArchiveHeading.Text = "Fandoms"; ShowPage(ArchivePage); RefreshArchive(); }
    private void Ships_Click(object sender, RoutedEventArgs e) { _scope = ArchiveScope.Ships; ArchiveHeading.Text = "Ships"; ShowPage(ArchivePage); RefreshArchive(); }
    private void CompleteSets_Click(object sender, RoutedEventArgs e) { _scope = ArchiveScope.Complete; ArchiveHeading.Text = "Complete Sets"; ShowPage(ArchivePage); RefreshArchive(); }
    private void IncompleteSets_Click(object sender, RoutedEventArgs e) { _scope = ArchiveScope.Incomplete; ArchiveHeading.Text = "Incomplete Sets"; ShowPage(ArchivePage); RefreshArchive(); }
    private void Archived_Click(object sender, RoutedEventArgs e) { _scope = ArchiveScope.Archived; ArchiveHeading.Text = "Archive"; ShowPage(ArchivePage); RefreshArchive(); }
    private void AddCovers_Click(object sender, RoutedEventArgs e) => ShowPage(AddPage);
    private void Settings_Click(object sender, RoutedEventArgs e) => ShowPage(SettingsPage);
    private void SingleMode_Click(object sender, RoutedEventArgs e) { SinglePanel.Visibility = Visibility.Visible; WrapPanel.Visibility = Visibility.Collapsed; }
    private void WrapMode_Click(object sender, RoutedEventArgs e) { SinglePanel.Visibility = Visibility.Collapsed; WrapPanel.Visibility = Visibility.Visible; }

    private void ArchiveFilter_Changed(object sender, EventArgs e)
    {
        if (!IsLoaded) return;
        RefreshArchive();
    }

    private void RefreshArchive()
    {
        var archived = _scope == ArchiveScope.Archived;
        IEnumerable<CoverItem> query = _store.Items.Where(x => x.Archived == archived);
        var search = SearchBox?.Text?.Trim() ?? "";
        if (!string.IsNullOrWhiteSpace(search))
        {
            query = query.Where(x => $"{x.Project} {x.Fandom} {x.Ship} {x.Tags} {x.OriginalName} {x.Position}"
                .Contains(search, StringComparison.OrdinalIgnoreCase));
        }

        var panel = PositionFilter is null ? "All Panels" : ComboText(PositionFilter);
        if (panel != "All Panels") query = query.Where(x => x.Position == panel);

        var items = query.ToList();
        var grouped = ViewMode is null || ComboText(ViewMode) == "Grouped Sets";
        IEnumerable<ArchiveCard> cards;
        if (grouped)
        {
            cards = items.GroupBy(x => $"{x.Project}\u001f{x.Fandom}\u001f{x.Ship}\u001f{x.CoverType}")
                .Select(g => MakeCard(g.Key, g.ToList()));
        }
        else cards = items.Select(x => MakeCard(x.Id, [x]));

        if (_scope == ArchiveScope.Complete) cards = cards.Where(x => x.IsComplete);
        if (_scope == ArchiveScope.Incomplete) cards = cards.Where(x => !x.IsComplete);

        cards = _scope switch
        {
            ArchiveScope.Fandoms => cards.OrderBy(x => x.Fandom).ThenBy(x => x.Title),
            ArchiveScope.Ships => cards.OrderBy(x => x.Ship).ThenBy(x => x.Title),
            _ => SortCards(cards)
        };

        Cards.Clear();
        foreach (var card in cards) Cards.Add(card);
        ResultCount.Text = $"{Cards.Count} shown";
        var active = _store.Items.Count(x => !x.Archived);
        var setCount = _store.Items.Where(x => !x.Archived).GroupBy(x => $"{x.Project}|{x.Fandom}|{x.Ship}|{x.CoverType}").Count();
        SidebarStats.Text = $"{active} panels\n{setCount} cover sets";
        ArchiveSubheading.Text = grouped ? "Grouped Sets" : "All Images";
        ArchiveEmptyState.Visibility = Cards.Count == 0 ? Visibility.Visible : Visibility.Collapsed;
        if (_selectedCard is not null && !Cards.Any(x => x.Key == _selectedCard.Key)) ClearDetails();
    }

    private IEnumerable<ArchiveCard> SortCards(IEnumerable<ArchiveCard> cards)
    {
        var sort = SortBox is null ? "Recently Added" : ComboText(SortBox);
        return sort switch
        {
            "Title" => cards.OrderBy(x => x.Title, StringComparer.CurrentCultureIgnoreCase),
            "Fandom" => cards.OrderBy(x => x.Fandom, StringComparer.CurrentCultureIgnoreCase).ThenBy(x => x.Title),
            "Ship" => cards.OrderBy(x => x.Ship, StringComparer.CurrentCultureIgnoreCase).ThenBy(x => x.Title),
            _ => cards.OrderByDescending(x => x.Items.Max(i => ParseDate(i.AddedAt)))
        };
    }

    private ArchiveCard MakeCard(string key, List<CoverItem> items)
    {
        var representative = items.FirstOrDefault(x => x.Position == "Front Cover") ?? items[0];
        var title = string.IsNullOrWhiteSpace(representative.Project)
            ? Path.GetFileNameWithoutExtension(representative.OriginalName) : representative.Project;
        var positions = items.Select(x => x.Position).Distinct().ToHashSet(StringComparer.OrdinalIgnoreCase);
        var complete = positions.Contains("Front Cover") && positions.Contains("Spine") && positions.Contains("Back Cover");
        return new ArchiveCard
        {
            Key = key, Title = title,
            Fandom = string.IsNullOrWhiteSpace(representative.Fandom) ? "No fandom" : representative.Fandom,
            Ship = string.IsNullOrWhiteSpace(representative.Ship) ? "No ship" : representative.Ship,
            PanelSummary = items.Count == 1 ? representative.Position : complete ? "Complete set • 3 panels" : $"Incomplete set • {items.Count} panel(s)",
            Items = new ObservableCollection<CoverItem>(items),
            CoverImage = LibraryStore.LoadImage(_store.StoredPath(representative), 340),
            IsComplete = complete
        };
    }

    private static DateTimeOffset ParseDate(string value) => DateTimeOffset.TryParse(value, out var date) ? date : DateTimeOffset.MinValue;

    private void CoverCard_Click(object sender, RoutedEventArgs e)
    {
        if ((sender as FrameworkElement)?.Tag is not ArchiveCard card) return;
        _selectedCard = card;
        var item = card.Items.FirstOrDefault(x => x.Position == "Front Cover") ?? card.Items[0];
        DetailImage.Source = LibraryStore.LoadImage(_store.StoredPath(item), 720);
        DetailProject.Text = item.Project;
        DetailFandom.Text = item.Fandom;
        DetailShip.Text = item.Ship;
        DetailTags.Text = item.Tags;
        SelectCombo(DetailPosition, item.Position);
        SelectCombo(DetailType, item.CoverType);
        DetailPieces.Text = string.Join("  •  ", card.Items.Select(x => x.Position));
        DetailEmpty.Visibility = Visibility.Collapsed;
        DetailEditor.IsEnabled = true;
        ArchiveButton.Content = item.Archived ? "RESTORE" : "ARCHIVE";
        AutosaveStatus.Text = "";
    }

    private static void SelectCombo(ComboBox combo, string value)
    {
        foreach (var candidate in combo.Items.OfType<ComboBoxItem>())
            if (candidate.Content?.ToString() == value) { combo.SelectedItem = candidate; return; }
        combo.Text = value;
    }

    private void ClearDetails()
    {
        _selectedCard = null;
        DetailImage.Source = null;
        DetailEmpty.Visibility = Visibility.Visible;
        DetailEditor.IsEnabled = false;
    }

    private void SaveDetails_Click(object sender, RoutedEventArgs e)
    {
        if (_selectedCard is null) return;
        foreach (var item in _selectedCard.Items)
        {
            item.Project = DetailProject.Text.Trim(); item.Fandom = DetailFandom.Text.Trim(); item.Ship = DetailShip.Text.Trim();
            item.Tags = LibraryStore.NormalizeTags(DetailTags.Text); item.CoverType = ComboText(DetailType);
        }
        if (_selectedCard.Items.Count == 1) _selectedCard.Items[0].Position = ComboText(DetailPosition);
        _store.Save();
        AutosaveStatus.Text = $"Saved {DateTime.Now:h:mm:ss tt}";
        RefreshArchive();
    }

    private void Download_Click(object sender, RoutedEventArgs e)
    {
        if (_selectedCard is null) return;
        if (_selectedCard.Items.Count == 1)
        {
            var item = _selectedCard.Items[0];
            var dialog = new SaveFileDialog { FileName = item.OriginalName, Filter = "Image files|*.*" };
            if (dialog.ShowDialog(this) == true) File.Copy(_store.StoredPath(item), dialog.FileName, true);
            return;
        }
        var folder = new OpenFolderDialog { Title = "Choose where to save this cover set" };
        if (folder.ShowDialog(this) != true) return;
        foreach (var item in _selectedCard.Items)
        {
            var destination = UniquePath(folder.FolderName, item.OriginalName);
            File.Copy(_store.StoredPath(item), destination);
        }
    }

    private void Replace_Click(object sender, RoutedEventArgs e)
    {
        if (_selectedCard is null) return;
        var item = _selectedCard.Items.FirstOrDefault(x => x.Position == "Front Cover") ?? _selectedCard.Items[0];
        var dialog = ImageDialog(false);
        if (dialog.ShowDialog(this) != true) return;
        try
        {
            var extension = Path.GetExtension(dialog.FileName).ToLowerInvariant();
            var stored = Guid.NewGuid().ToString("N") + extension;
            var destination = Path.Combine(_store.FilesRoot, stored);
            File.Copy(dialog.FileName, destination);
            var old = _store.StoredPath(item);
            item.StoredName = stored; item.OriginalName = Path.GetFileName(dialog.FileName);
            item.Size = new FileInfo(destination).Length; item.Hash = LibraryStore.Sha256(destination);
            _store.Save();
            try { if (File.Exists(old)) File.Delete(old); } catch { }
            RefreshArchive();
            CoverCard_Click(new Button { Tag = Cards.FirstOrDefault(x => x.Key == _selectedCard.Key) }, e);
        }
        catch (Exception ex) { ShowError("The replacement image could not be saved.", ex); }
    }

    private void ArchiveSelected_Click(object sender, RoutedEventArgs e)
    {
        if (_selectedCard is null) return;
        var target = !_selectedCard.Items[0].Archived;
        foreach (var item in _selectedCard.Items) item.Archived = target;
        _store.Save(); ClearDetails(); RefreshArchive();
    }

    private void DeleteSelected_Click(object sender, RoutedEventArgs e)
    {
        if (_selectedCard is null) return;
        var label = _selectedCard.Items.Count == 1 ? "this stored image" : $"all {_selectedCard.Items.Count} stored panels in this set";
        if (MessageBox.Show($"Delete {label}? This cannot be undone.", "Delete from The Library", MessageBoxButton.YesNo, MessageBoxImage.Warning) != MessageBoxResult.Yes) return;
        _store.Delete(_selectedCard.Items); ClearDetails(); RefreshArchive();
    }

    private void ChooseSingle_Click(object sender, RoutedEventArgs e)
    {
        var dialog = ImageDialog(false);
        if (dialog.ShowDialog(this) != true) return;
        _singlePath = dialog.FileName;
        SingleFileName.Text = Path.GetFileName(_singlePath);
        SinglePreview.Source = LibraryStore.LoadImage(_singlePath, 1000);
        SinglePreviewEmpty.Visibility = Visibility.Collapsed;
        SingleStatus.Text = "Ready to save.";
    }

    private void SaveSingle_Click(object sender, RoutedEventArgs e)
    {
        if (string.IsNullOrWhiteSpace(_singlePath) || !File.Exists(_singlePath)) { SingleStatus.Text = "Choose an image first."; return; }
        try
        {
            _store.ImportFile(_singlePath, ComboText(SinglePosition), ComboText(SingleType), SingleProject.Text, SingleShip.Text,
                SingleFandom.Text, SingleTags.Text, SingleRemoveSource.IsChecked == true);
            _singlePath = null; SinglePreview.Source = null; SinglePreviewEmpty.Visibility = Visibility.Visible;
            SingleFileName.Text = "No image selected"; SingleStatus.Text = "Saved to The Library.";
            RefreshArchive();
        }
        catch (Exception ex) { ShowError("The panel could not be imported.", ex); }
    }

    private static OpenFileDialog ImageDialog(bool multi) => new()
    {
        Filter = "Image files|*.png;*.jpg;*.jpeg;*.bmp;*.tif;*.tiff|All files|*.*",
        Multiselect = multi
    };

    private void ChooseWraps_Click(object sender, RoutedEventArgs e)
    {
        var dialog = ImageDialog(true);
        if (dialog.ShowDialog(this) != true) return;
        foreach (var path in dialog.FileNames)
        {
            try
            {
                var bitmap = LibraryStore.LoadImage(path) ?? throw new InvalidDataException("Windows could not decode the image.");
                var center = bitmap.PixelWidth / 2;
                var half = Math.Max(2, (int)Math.Round(bitmap.PixelWidth * .04));
                var job = new WrapJob { SourcePath = path, SourceBitmap = bitmap, Left = Math.Max(1, center - half), Right = Math.Min(bitmap.PixelWidth - 1, center + half) };
                UpdateJobCrops(job);
                WrapJobs.Add(job);
            }
            catch (Exception ex) { MessageBox.Show($"Could not add {Path.GetFileName(path)}.\n\n{ex.Message}", "The Library", MessageBoxButton.OK, MessageBoxImage.Warning); }
        }
        WrapQueueEmpty.Visibility = WrapJobs.Count == 0 ? Visibility.Visible : Visibility.Collapsed;
        if (_selectedJob is null && WrapJobs.Count > 0) SelectJob(WrapJobs[0]);
    }

    private void QueueJob_Click(object sender, RoutedEventArgs e)
    {
        if ((sender as FrameworkElement)?.Tag is WrapJob job) SelectJob(job);
    }

    private void SelectJob(WrapJob job)
    {
        SaveWrapMetadataToCurrent();
        _selectedJob = job;
        _updatingWrapUi = true;
        WrapEditorTitle.Text = job.FileName; WrapSourcePreview.Source = job.SourceBitmap;
        WrapProject.Text = job.Project; WrapFandom.Text = job.Fandom; WrapShip.Text = job.Ship; WrapTags.Text = job.Tags;
        SelectCombo(WrapType, job.CoverType); WrapStatus.Text = job.Status;
        _updatingWrapUi = false;
        ConfigureGuideControls();
        Dispatcher.BeginInvoke(DispatcherPriority.Loaded, new Action(FitZoom));
    }

    private void ConfigureGuideControls()
    {
        if (_selectedJob is null) return;
        _updatingGuideUi = true;
        LeftSlider.Maximum = _selectedJob.PixelWidth - 2; RightSlider.Maximum = _selectedJob.PixelWidth - 1;
        LeftSlider.Value = _selectedJob.Left; RightSlider.Value = _selectedJob.Right;
        LeftPixels.Text = _selectedJob.Left.ToString(CultureInfo.InvariantCulture); RightPixels.Text = _selectedJob.Right.ToString(CultureInfo.InvariantCulture);
        _updatingGuideUi = false;
        RefreshGuideVisuals();
    }

    private void GuideSlider_Changed(object sender, RoutedPropertyChangedEventArgs<double> e)
    {
        if (_selectedJob is null || _updatingGuideUi) return;
        var left = Math.Clamp((int)Math.Round(LeftSlider.Value), 1, _selectedJob.PixelWidth - 2);
        var right = Math.Clamp((int)Math.Round(RightSlider.Value), 2, _selectedJob.PixelWidth - 1);
        if (left >= right) { if (sender == LeftSlider) left = right - 1; else right = left + 1; }
        SetGuides(left, right);
    }

    private void GuidePixels_Changed(object sender, TextChangedEventArgs e)
    {
        if (_selectedJob is null || _updatingGuideUi) return;
        if (!int.TryParse(LeftPixels.Text, out var left) || !int.TryParse(RightPixels.Text, out var right)) return;
        left = Math.Clamp(left, 1, _selectedJob.PixelWidth - 2); right = Math.Clamp(right, 2, _selectedJob.PixelWidth - 1);
        if (left >= right) return;
        SetGuides(left, right);
    }

    private void SetGuides(int left, int right)
    {
        if (_selectedJob is null) return;
        _selectedJob.Left = left; _selectedJob.Right = right;
        _updatingGuideUi = true;
        LeftSlider.Value = left; RightSlider.Value = right; LeftPixels.Text = left.ToString(); RightPixels.Text = right.ToString();
        _updatingGuideUi = false;
        UpdateJobCrops(_selectedJob); RefreshGuideVisuals();
    }

    private void LeftGuide_DragDelta(object sender, DragDeltaEventArgs e) => DragGuide(true, e.HorizontalChange);
    private void RightGuide_DragDelta(object sender, DragDeltaEventArgs e) => DragGuide(false, e.HorizontalChange);

    private void DragGuide(bool leftGuide, double displayDelta)
    {
        if (_selectedJob is null || GuideCanvas.ActualWidth <= 0) return;
        var pixelDelta = (int)Math.Round(displayDelta / GuideCanvas.ActualWidth * _selectedJob.PixelWidth);
        var left = _selectedJob.Left; var right = _selectedJob.Right;
        if (leftGuide) left = Math.Clamp(left + pixelDelta, 1, right - 1);
        else right = Math.Clamp(right + pixelDelta, left + 1, _selectedJob.PixelWidth - 1);
        SetGuides(left, right);
    }

    private void GuideCanvas_SizeChanged(object sender, SizeChangedEventArgs e) => RefreshGuideVisuals();

    private void RefreshGuideVisuals()
    {
        if (_selectedJob is null || GuideCanvas.ActualWidth <= 0) return;
        LeftGuide.Height = GuideCanvas.ActualHeight; RightGuide.Height = GuideCanvas.ActualHeight;
        Canvas.SetLeft(LeftGuide, (_selectedJob.Left / (double)_selectedJob.PixelWidth) * GuideCanvas.ActualWidth - LeftGuide.Width / 2);
        Canvas.SetLeft(RightGuide, (_selectedJob.Right / (double)_selectedJob.PixelWidth) * GuideCanvas.ActualWidth - RightGuide.Width / 2);
        Canvas.SetTop(LeftGuide, 0); Canvas.SetTop(RightGuide, 0);
        GuideSummary.Text = _selectedJob.GuideSummary;
        BackPreview.Source = _selectedJob.BackPreview; SpinePreview.Source = _selectedJob.SpinePreview; FrontPreview.Source = _selectedJob.FrontPreview;
    }

    private static void UpdateJobCrops(WrapJob job)
    {
        if (job.Left <= 0 || job.Right <= job.Left || job.Right >= job.PixelWidth) return;
        job.BackPreview = FreezeCrop(job.SourceBitmap, new Int32Rect(0, 0, job.Left, job.PixelHeight));
        job.SpinePreview = FreezeCrop(job.SourceBitmap, new Int32Rect(job.Left, 0, job.Right - job.Left, job.PixelHeight));
        job.FrontPreview = FreezeCrop(job.SourceBitmap, new Int32Rect(job.Right, 0, job.PixelWidth - job.Right, job.PixelHeight));
    }

    private static BitmapSource FreezeCrop(BitmapSource bitmap, Int32Rect rect)
    {
        var crop = new CroppedBitmap(bitmap, rect); crop.Freeze(); return crop;
    }

    private void FitZoom_Click(object sender, RoutedEventArgs e) => FitZoom();
    private void ActualZoom_Click(object sender, RoutedEventArgs e) => SetZoom(1);
    private void FitZoom()
    {
        if (_selectedJob is null) return;
        var availableWidth = Math.Max(100, WrapPreviewScroller.ViewportWidth - 20);
        var availableHeight = Math.Max(100, WrapPreviewScroller.ViewportHeight - 20);
        SetZoom(Math.Min(availableWidth / _selectedJob.PixelWidth, availableHeight / _selectedJob.PixelHeight));
    }

    private void SetZoom(double zoom)
    {
        if (_selectedJob is null) return;
        _zoom = Math.Clamp(zoom, .05, 4);
        var width = _selectedJob.PixelWidth * _zoom; var height = _selectedJob.PixelHeight * _zoom;
        WrapImageSurface.Width = width; WrapImageSurface.Height = height;
        WrapSourcePreview.Width = width; WrapSourcePreview.Height = height;
        GuideCanvas.Width = width; GuideCanvas.Height = height;
        RefreshGuideVisuals();
    }

    private void WrapMetadata_Changed(object sender, EventArgs e)
    {
        if (_updatingWrapUi) return;
        SaveWrapMetadataToCurrent();
    }

    private void SaveWrapMetadataToCurrent()
    {
        if (_selectedJob is null || _updatingWrapUi) return;
        _selectedJob.Project = WrapProject.Text; _selectedJob.Fandom = WrapFandom.Text; _selectedJob.Ship = WrapShip.Text;
        _selectedJob.Tags = WrapTags.Text; _selectedJob.CoverType = ComboText(WrapType);
    }

    private void SaveCurrentWrap_Click(object sender, RoutedEventArgs e)
    {
        if (_selectedJob is null) { WrapStatus.Text = "Add or select a wrap first."; return; }
        SaveWrap(_selectedJob);
    }

    private void SaveAllWraps_Click(object sender, RoutedEventArgs e)
    {
        SaveWrapMetadataToCurrent();
        var failed = 0;
        foreach (var job in WrapJobs.Where(x => x.Status != "Saved").ToList()) if (!SaveWrap(job, false)) failed++;
        WrapStatus.Text = failed == 0 ? "All queued wraps were saved." : $"Finished with {failed} failure(s).";
        RefreshArchive();
    }

    private bool SaveWrap(WrapJob job, bool refresh = true)
    {
        try
        {
            if (job == _selectedJob) SaveWrapMetadataToCurrent();
            if (job.Left <= 0 || job.Right <= job.Left || job.Right >= job.PixelWidth) throw new InvalidDataException("The split guides are invalid.");
            var baseName = Path.GetFileNameWithoutExtension(job.SourcePath);
            _store.AddCrop(job.SourceBitmap, new Int32Rect(0, 0, job.Left, job.PixelHeight), $"{baseName} - Back Cover.png", "Back Cover", job.CoverType, job.Project, job.Ship, job.Fandom, job.Tags);
            _store.AddCrop(job.SourceBitmap, new Int32Rect(job.Left, 0, job.Right - job.Left, job.PixelHeight), $"{baseName} - Spine.png", "Spine", job.CoverType, job.Project, job.Ship, job.Fandom, job.Tags);
            _store.AddCrop(job.SourceBitmap, new Int32Rect(job.Right, 0, job.PixelWidth - job.Right, job.PixelHeight), $"{baseName} - Front Cover.png", "Front Cover", job.CoverType, job.Project, job.Ship, job.Fandom, job.Tags);
            _store.Save();
            if (WrapRemoveSource.IsChecked == true) { try { File.Delete(job.SourcePath); } catch { } }
            job.Status = "Saved";
            if (job == _selectedJob) WrapStatus.Text = "Saved Back, Spine, and Front. The full wrap was not stored.";
            if (refresh) RefreshArchive();
            return true;
        }
        catch (Exception ex)
        {
            job.Status = "Save failed";
            if (job == _selectedJob) WrapStatus.Text = ex.Message;
            return false;
        }
    }

    private void RemoveCurrentWrap_Click(object sender, RoutedEventArgs e)
    {
        if (_selectedJob is null) return;
        var index = WrapJobs.IndexOf(_selectedJob); WrapJobs.Remove(_selectedJob); _selectedJob = null;
        if (WrapJobs.Count > 0) SelectJob(WrapJobs[Math.Clamp(index, 0, WrapJobs.Count - 1)]); else ClearWrapEditor();
    }

    private void ClearWraps_Click(object sender, RoutedEventArgs e)
    {
        WrapJobs.Clear(); _selectedJob = null; ClearWrapEditor(); WrapStatus.Text = "Queue cleared.";
    }

    private void ClearWrapEditor()
    {
        WrapQueueEmpty.Visibility = Visibility.Visible; WrapSourcePreview.Source = null; BackPreview.Source = null; SpinePreview.Source = null; FrontPreview.Source = null;
        WrapEditorTitle.Text = "Select a queued wrap"; GuideSummary.Text = "";
    }

    private void ExportBackup_Click(object sender, RoutedEventArgs e)
    {
        var dialog = new SaveFileDialog { Filter = "The Library backup|*.zip", FileName = $"The Library Backup {DateTime.Now:yyyy-MM-dd}.zip" };
        if (dialog.ShowDialog(this) != true) return;
        try { _store.ExportBackup(dialog.FileName); BackupStatus.Text = "Backup created successfully."; }
        catch (Exception ex) { BackupStatus.Text = ex.Message; }
    }

    private void RestoreBackup_Click(object sender, RoutedEventArgs e)
    {
        var dialog = new OpenFileDialog { Filter = "The Library backup|*.zip;*.librarybackup|All files|*.*" };
        if (dialog.ShowDialog(this) != true) return;
        if (MessageBox.Show("Restore this backup? A recovery copy of the current Library will be created first.", "Restore The Library", MessageBoxButton.YesNo, MessageBoxImage.Question) != MessageBoxResult.Yes) return;
        try { _store.RestoreBackup(dialog.FileName); RefreshArchive(); BackupStatus.Text = "Backup restored successfully."; }
        catch (Exception ex) { BackupStatus.Text = ex.Message; }
    }

    private async void CheckUpdates_Click(object sender, RoutedEventArgs e)
    {
        UpdateStatus.Text = "Checking for updates…";
        try
        {
            var result = await _updates.CheckAsync();
            if (result.Manifest is null) { UpdateStatus.Text = result.Message; return; }
            var answer = MessageBox.Show($"{result.Message}\n\nInstall this update now?", "The Library Update", MessageBoxButton.YesNo, MessageBoxImage.Information);
            if (answer != MessageBoxResult.Yes) { UpdateStatus.Text = "Update postponed."; return; }
            UpdateStatus.Text = "Downloading and verifying the update…";
            await _updates.DownloadAndStartAsync(result.Manifest, this);
        }
        catch (Exception ex) { UpdateStatus.Text = ex.Message; }
    }

    private void OpenStorage_Click(object sender, RoutedEventArgs e) =>
        Process.Start(new ProcessStartInfo("explorer.exe", _store.DataRoot) { UseShellExecute = true });

    private static string UniquePath(string folder, string name)
    {
        var safe = string.Concat(name.Select(ch => Path.GetInvalidFileNameChars().Contains(ch) ? '_' : ch));
        var path = Path.Combine(folder, safe); var number = 2;
        while (File.Exists(path)) path = Path.Combine(folder, $"{Path.GetFileNameWithoutExtension(safe)} ({number++}){Path.GetExtension(safe)}");
        return path;
    }

    private void ShowError(string message, Exception ex) => MessageBox.Show($"{message}\n\n{ex.Message}", "The Library", MessageBoxButton.OK, MessageBoxImage.Error);
}
