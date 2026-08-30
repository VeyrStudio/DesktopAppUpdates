$ErrorActionPreference = 'Stop'
$root = 'catalog-source/TheCatalog-WPF-v0.3-runtime-src'
$patchRoot = 'the-catalog/build/patches'

Copy-Item (Join-Path $patchRoot 'UpdateService.cs') (Join-Path $root 'Services/UpdateService.cs') -Force
Copy-Item (Join-Path $patchRoot 'App.xaml.cs') (Join-Path $root 'App.xaml.cs') -Force

# Reconstruct the approved worn-rose Windows icon.
$iconBase64 =
    (Get-Content 'the-catalog/build/icon/icon-part-00.b64' -Raw) +
    (Get-Content 'the-catalog/build/icon/icon-part-01.b64' -Raw) +
    (Get-Content 'the-catalog/build/icon/icon-part-02.b64' -Raw) +
    (Get-Content 'the-catalog/build/icon/icon-part-03.b64' -Raw)
$assets = Join-Path $root 'Assets'
New-Item -ItemType Directory -Path $assets -Force | Out-Null
[IO.File]::WriteAllBytes((Join-Path $assets 'TheCatalog.ico'), [Convert]::FromBase64String($iconBase64))

$project = Join-Path $root 'TheCatalog.csproj'
$text = Get-Content $project -Raw
$text = $text.Replace('<Version>0.3.0</Version>', '<Version>1.0.5</Version>')
$text = $text.Replace('<AssemblyVersion>0.3.0.0</AssemblyVersion>', '<AssemblyVersion>1.0.5.0</AssemblyVersion>')
$text = $text.Replace('<FileVersion>0.3.0.0</FileVersion>', '<FileVersion>1.0.5.0</FileVersion>')
$text = $text.Replace('<UseWPF>true</UseWPF>', "<UseWPF>true</UseWPF>`r`n    <ApplicationIcon>Assets\TheCatalog.ico</ApplicationIcon>")
Set-Content -Path $project -Value $text -Encoding utf8

# Keep the rose as the native Windows executable icon only.
# Do not load the .ico through WPF Window.Icon at startup; that path caused
# the 1.0.1 build to exit silently on the user's PC.

$appXaml = Join-Path $root 'App.xaml'
$text = Get-Content $appXaml -Raw
$text = $text -replace '\s+StartupUri="MainWindow\.xaml"', ''
Set-Content -Path $appXaml -Value $text -Encoding utf8

$settingsXaml = Join-Path $root 'Views/SettingsWindow.xaml'
$text = Get-Content $settingsXaml -Raw
if ($text -notmatch 'x:Name="UpdateButton"') {
    $text = $text.Replace('<Button Content="Update"', '<Button x:Name="UpdateButton" Content="Update"')
}
Set-Content -Path $settingsXaml -Value $text -Encoding utf8

$settingsCode = Join-Path $root 'Views/SettingsWindow.xaml.cs'
$text = Get-Content $settingsCode -Raw
$pattern = '(?s)    private (?:async )?void Update_Click\(object sender, RoutedEventArgs e\).*?(?=\r?\n    private (?:async )?void (?:MakeShortcut_Click|Backup_Click))'
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
