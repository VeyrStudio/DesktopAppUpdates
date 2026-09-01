using System.Windows;
using TheBookworm.Models;
using TheBookworm.Services;

namespace TheBookworm;

public partial class SettingsWindow : Window
{
    private readonly SettingsService _service = new();
    private AppSettings _settings = new();
    private bool _loaded;

    public SettingsWindow()
    {
        InitializeComponent();
        Loaded += (_, _) =>
        {
            _settings = _service.Load();
            QuestionsToggle.IsChecked = _settings.QuestionsAndQuizzesEnabled;
            QuestionsToggle.Content = _settings.QuestionsAndQuizzesEnabled ? "On" : "Off";
            AutomaticUpdatesToggle.IsChecked = _settings.AutomaticUpdatesEnabled;
            AutomaticUpdatesToggle.Content = _settings.AutomaticUpdatesEnabled ? "On" : "Off";
            _loaded = true;
        };
    }

    private void QuestionsToggle_Changed(object sender, RoutedEventArgs e)
    {
        if (!_loaded) return;
        _settings.QuestionsAndQuizzesEnabled = QuestionsToggle.IsChecked == true;
        QuestionsToggle.Content = _settings.QuestionsAndQuizzesEnabled ? "On" : "Off";
        _service.Save(_settings);
    }

    private void AutomaticUpdatesToggle_Changed(object sender, RoutedEventArgs e)
    {
        if (!_loaded) return;
        _settings.AutomaticUpdatesEnabled = AutomaticUpdatesToggle.IsChecked == true;
        AutomaticUpdatesToggle.Content = _settings.AutomaticUpdatesEnabled ? "On" : "Off";
        _service.Save(_settings);
    }

    private void MakeShortcut_Click(object sender, RoutedEventArgs e)
    {
        try
        {
            var desktop = Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory);
            var shortcutPath = Path.Combine(desktop, "The Bookworm.lnk");

            var iconDirectory = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                "TheBookworm");
            Directory.CreateDirectory(iconDirectory);

            var iconPath = Path.Combine(iconDirectory, "TheBookworm.ico");
            var resource = Application.GetResourceStream(
                new Uri("pack://application:,,,/Assets/TheBookworm.ico"));

            if (resource?.Stream is null)
                throw new InvalidOperationException("The Bookworm icon could not be loaded.");

            using (resource.Stream)
            using (var output = File.Create(iconPath))
            {
                resource.Stream.CopyTo(output);
            }

            var exePath = Environment.ProcessPath;
            if (string.IsNullOrWhiteSpace(exePath) || !File.Exists(exePath))
                throw new InvalidOperationException("Bookworm could not find its executable.");

            var shellType = Type.GetTypeFromProgID("WScript.Shell");
            if (shellType is null)
                throw new InvalidOperationException("Windows shortcut support is unavailable.");

            dynamic shell = Activator.CreateInstance(shellType)!;
            dynamic shortcut = shell.CreateShortcut(shortcutPath);
            shortcut.TargetPath = exePath;
            shortcut.WorkingDirectory = AppContext.BaseDirectory;
            shortcut.IconLocation = iconPath + ",0";
            shortcut.Description = "The Bookworm";
            shortcut.Save();

            ShortcutStatus.Text = "Shortcut created on your desktop.";
        }
        catch (Exception ex)
        {
            ShortcutStatus.Text = "Could not create the shortcut.";
            MessageBox.Show(
                "Bookworm could not create the desktop shortcut.\n\n" + ex.Message,
                "The Bookworm",
                MessageBoxButton.OK,
                MessageBoxImage.Warning);
        }
    }

    private void Close_Click(object sender, RoutedEventArgs e) => Close();
}
