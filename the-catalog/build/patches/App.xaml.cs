using System.IO;
using System.Text;
using System.Windows;
using System.Windows.Threading;
using TheCatalog.Services;

namespace TheCatalog;

public partial class App : Application
{
    protected override void OnStartup(StartupEventArgs e)
    {
        DispatcherUnhandledException += OnDispatcherUnhandledException;
        AppDomain.CurrentDomain.UnhandledException += OnUnhandledException;
        TaskScheduler.UnobservedTaskException += OnUnobservedTaskException;

        try
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
        catch (Exception ex)
        {
            ShowStartupCrash(ex);
            Shutdown(-1);
        }
    }

    private static string CrashLogPath
    {
        get
        {
            var root = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                "TheCatalog");
            Directory.CreateDirectory(root);
            return Path.Combine(root, "crash.log");
        }
    }

    private static void WriteCrashLog(string source, Exception ex)
    {
        try
        {
            var sb = new StringBuilder();
            sb.AppendLine($"[{DateTimeOffset.Now:O}] {source}");
            sb.AppendLine(ex.ToString());
            sb.AppendLine(new string('-', 80));
            File.AppendAllText(CrashLogPath, sb.ToString());
        }
        catch
        {
            // Never let crash logging hide the original startup error.
        }
    }

    private static void ShowStartupCrash(Exception ex)
    {
        WriteCrashLog("Startup", ex);
        MessageBox.Show(
            $"The Catalog could not finish starting.\n\n{ex.Message}\n\nA crash log was written to:\n{CrashLogPath}",
            "The Catalog — Startup Error",
            MessageBoxButton.OK,
            MessageBoxImage.Error);
    }

    private void OnDispatcherUnhandledException(object sender, DispatcherUnhandledExceptionEventArgs e)
    {
        WriteCrashLog("Dispatcher", e.Exception);
        MessageBox.Show(
            $"The Catalog hit an error and could not continue.\n\n{e.Exception.Message}\n\nCrash log:\n{CrashLogPath}",
            "The Catalog — Error",
            MessageBoxButton.OK,
            MessageBoxImage.Error);
        e.Handled = true;
        Shutdown(-1);
    }

    private static void OnUnhandledException(object? sender, UnhandledExceptionEventArgs e)
    {
        if (e.ExceptionObject is Exception ex)
            WriteCrashLog("AppDomain", ex);
    }

    private static void OnUnobservedTaskException(object? sender, UnobservedTaskExceptionEventArgs e)
    {
        WriteCrashLog("Task", e.Exception);
        e.SetObserved();
    }
}
