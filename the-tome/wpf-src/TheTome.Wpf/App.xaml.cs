using System.Diagnostics;
using System.Threading;
using System.Windows;

namespace TheTome;

public partial class App : Application
{
    private Mutex? _instanceMutex;

    protected override void OnStartup(StartupEventArgs e)
    {
        if (e.Args.Length > 0 && e.Args[0].Equals("--apply-update", StringComparison.OrdinalIgnoreCase))
        {
            ShutdownMode = ShutdownMode.OnExplicitShutdown;
            try
            {
                ApplyUpdate(e.Args);
                Shutdown(0);
            }
            catch (Exception ex)
            {
                MessageBox.Show($"The Tome could not finish the update.\n\n{ex.Message}", "The Tome Update",
                    MessageBoxButton.OK, MessageBoxImage.Error);
                Shutdown(1);
            }
            return;
        }

        _instanceMutex = new Mutex(true, @"Local\VeyrStudio.TheTome.WPF", out var first);
        if (!first)
        {
            MessageBox.Show("The Tome is already open.", "The Tome", MessageBoxButton.OK, MessageBoxImage.Information);
            Shutdown(0);
            return;
        }

        base.OnStartup(e);
        MainWindow = new MainWindow();
        MainWindow.Show();
    }

    protected override void OnExit(ExitEventArgs e)
    {
        try { _instanceMutex?.ReleaseMutex(); } catch { }
        _instanceMutex?.Dispose();
        base.OnExit(e);
    }

    private static void ApplyUpdate(string[] args)
    {
        if (args.Length < 4) throw new ArgumentException("The update instructions are incomplete.");
        var waitPid = int.Parse(args[1]);
        var payloadDir = Path.GetFullPath(args[2]);
        var appDir = Path.GetFullPath(args[3]);

        try { Process.GetProcessById(waitPid).WaitForExit(60000); } catch { }
        Directory.CreateDirectory(appDir);

        foreach (var source in Directory.EnumerateFiles(payloadDir, "*", SearchOption.AllDirectories))
        {
            if (Path.GetFileName(source).Equals("_delete.txt", StringComparison.OrdinalIgnoreCase)) continue;
            var relative = Path.GetRelativePath(payloadDir, source);
            var destination = Path.GetFullPath(Path.Combine(appDir, relative));
            if (!destination.StartsWith(appDir + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase))
                throw new InvalidOperationException("The update contained an unsafe path.");
            Directory.CreateDirectory(Path.GetDirectoryName(destination)!);
            File.Copy(source, destination, true);
        }

        var deleteFile = Path.Combine(payloadDir, "_delete.txt");
        if (File.Exists(deleteFile))
        {
            foreach (var relative in File.ReadAllLines(deleteFile).Where(x => !string.IsNullOrWhiteSpace(x)))
            {
                var target = Path.GetFullPath(Path.Combine(appDir, relative.Trim()));
                if (target.StartsWith(appDir + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase) && File.Exists(target))
                    File.Delete(target);
            }
        }

        Process.Start(new ProcessStartInfo(Path.Combine(appDir, "TheTome.exe")) { UseShellExecute = true });
    }
}