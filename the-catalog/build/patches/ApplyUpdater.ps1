$ErrorActionPreference = 'Stop'
$root = 'catalog-source/TheCatalog-WPF-v0.3-runtime-src'
$patchRoot = 'the-catalog/build/patches'

Copy-Item (Join-Path $patchRoot 'UpdateService.cs') (Join-Path $root 'Services/UpdateService.cs') -Force
Copy-Item (Join-Path $patchRoot 'App.xaml.cs') (Join-Path $root 'App.xaml.cs') -Force

$project = Join-Path $root 'TheCatalog.csproj'
$text = Get-Content $project -Raw
$text = $text.Replace('<Version>0.3.0</Version>', '<Version>1.0.0</Version>')
$text = $text.Replace('<AssemblyVersion>0.3.0.0</AssemblyVersion>', '<AssemblyVersion>1.0.0.0</AssemblyVersion>')
$text = $text.Replace('<FileVersion>0.3.0.0</FileVersion>', '<FileVersion>1.0.0.0</FileVersion>')
Set-Content -Path $project -Value $text -Encoding utf8

$appXaml = Join-Path $root 'App.xaml'
$text = Get-Content $appXaml -Raw
$text = $text -replace '\s+StartupUri="MainWindow\.xaml"', ''
Set-Content -Path $appXaml -Value $text -Encoding utf8

$settingsXaml = Join-Path $root 'Views/SettingsWindow.xaml'
$text = Get-Content $settingsXaml -Raw
$text = $text.Replace('<Button Content="Update" Width="120"', '<Button x:Name="UpdateButton" Content="Update" Width="120"')
Set-Content -Path $settingsXaml -Value $text -Encoding utf8

$settingsCode = Join-Path $root 'Views/SettingsWindow.xaml.cs'
$text = Get-Content $settingsCode -Raw
$pattern = '(?s)    private void Update_Click\(object sender, RoutedEventArgs e\).*?(?=\r?\n    private void Backup_Click)'
$replacement = @'
    private async void Update_Click(object sender, RoutedEventArgs e)
    {
        UpdateButton.IsEnabled = false;
        try
        {
            await UpdateService.CheckAndInstallAsync(true, message => StatusText.Text = message);
        }
        catch (Exception ex)
        {
            StatusText.Text = $"Update failed: {ex.Message}";
        }
        finally
        {
            UpdateButton.IsEnabled = true;
        }
    }
'@
$newText = [regex]::Replace($text, $pattern, $replacement, 1)
if ($newText -eq $text) { throw 'Could not patch the Settings Update button handler.' }
Set-Content -Path $settingsCode -Value $newText -Encoding utf8

$mainCode = Join-Path $root 'MainWindow.xaml.cs'
$text = Get-Content $mainCode -Raw
$pattern = '(?s)(    private async void MainWindow_Loaded\(object sender, RoutedEventArgs e\)\s*\{.*?        else await CreateStoryAsync\(\);)\s*\}'
$replacement = @'
$1

        _ = CheckAutomaticUpdatesAsync();
    }

    private async Task CheckAutomaticUpdatesAsync()
    {
        if (!SettingsService.Load().AutomaticUpdates) return;
        try
        {
            await UpdateService.CheckAndInstallAsync(false, message => Dispatcher.Invoke(() => SaveStatus.Text = message));
        }
        catch
        {
            // Automatic update checks stay quiet when the network or release source is unavailable.
        }
    }
'@
$newText = [regex]::Replace($text, $pattern, $replacement, 1)
if ($newText -eq $text) { throw 'Could not patch automatic update startup.' }
Set-Content -Path $mainCode -Value $newText -Encoding utf8
