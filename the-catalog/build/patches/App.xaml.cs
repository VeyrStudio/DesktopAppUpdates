using System.Windows;
using TheCatalog.Services;

namespace TheCatalog;

public partial class App : Application
{
    protected override void OnStartup(StartupEventArgs e)
    {
        base.OnStartup(e);

        if (UpdateService.TryRunUpdaterMode(e.Args))
        {
            Shutdown();
            return;
        }

        UpdateService.CleanupOldUpdateFiles();
        var mainWindow = new MainWindow();
        MainWindow = mainWindow;
        mainWindow.Show();
    }
}