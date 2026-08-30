$ErrorActionPreference = 'Stop'
$root = 'catalog-source/TheCatalog-WPF-v0.3-runtime-src'
$patchRoot = 'the-catalog/build/patches'

# Overlay the 1.0.8 story workflow: wider cards, popup editor, and .catalogentry importing.
$featureHead =
    (Get-Content 'the-catalog/build/v108-feature-part-00.b64' -Raw) +
    (Get-Content 'the-catalog/build/v108-feature-part-01.b64' -Raw) +
    (Get-Content 'the-catalog/build/v108-feature-part-02.b64' -Raw) +
    (Get-Content 'the-catalog/build/v108-feature-part-03.b64' -Raw) +
    (Get-Content 'the-catalog/build/v108-feature-part-04.b64' -Raw) +
    (Get-Content 'the-catalog/build/v108-feature-part-05a.b64' -Raw)
$featureTail =
    (Get-Content 'the-catalog/build/v108-feature-part-05b0.b64' -Raw) +
    (Get-Content 'the-catalog/build/v108-feature-part-05b1.b64' -Raw) +
    (Get-Content 'the-catalog/build/v108-feature-part-05b2.b64' -Raw) +
    (Get-Content 'the-catalog/build/v108-feature-part-05b3.b64' -Raw)
$featureExpectedSha = '428a0bbafa91c67836c540fd67f9db78c068ea2584a38a7ac83cec10bf27acf5'

function Get-FeatureSha([byte[]]$bytes) {
    return [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($bytes)).ToLowerInvariant()
}

$featureBytes = $null
try {
    $candidateBytes = [Convert]::FromBase64String($featureHead + $featureTail)
    if ((Get-FeatureSha $candidateBytes) -eq $featureExpectedSha) { $featureBytes = $candidateBytes }
} catch {}

if ($null -eq $featureBytes) {
    Write-Host 'Repairing one-character feature-bundle transfer mismatch...'
    for ($i = 0; $i -lt $featureTail.Length; $i++) {
        try {
            $candidate = $featureHead + $featureTail.Remove($i, 1)
            $candidateBytes = [Convert]::FromBase64String($candidate)
            if ((Get-FeatureSha $candidateBytes) -eq $featureExpectedSha) {
                $featureBytes = $candidateBytes
                Write-Host "Feature bundle repaired at tail index $i."
                break
            }
        } catch {}
    }
}
if ($null -eq $featureBytes) { throw 'The 1.0.8 feature bundle did not match its verified SHA-256.' }

$featureZip = Join-Path $env:TEMP ('TheCatalog-v108-' + [Guid]::NewGuid().ToString('N') + '.zip')
$featureStage = Join-Path $env:TEMP ('TheCatalog-v108-' + [Guid]::NewGuid().ToString('N'))
[IO.File]::WriteAllBytes($featureZip, $featureBytes)
Expand-Archive -Path $featureZip -DestinationPath $featureStage -Force

Copy-Item (Join-Path $featureStage 'MainWindow.xaml') (Join-Path $root 'MainWindow.xaml') -Force
Copy-Item (Join-Path $featureStage 'MainWindow.xaml.cs') (Join-Path $root 'MainWindow.xaml.cs') -Force
Copy-Item (Join-Path $featureStage 'Views/EditStoryWindow.xaml') (Join-Path $root 'Views/EditStoryWindow.xaml') -Force
Copy-Item (Join-Path $featureStage 'Views/EditStoryWindow.xaml.cs') (Join-Path $root 'Views/EditStoryWindow.xaml.cs') -Force
Copy-Item (Join-Path $featureStage 'Services/CatalogEntryService.cs') (Join-Path $root 'Services/CatalogEntryService.cs') -Force

# These files are overlaid after the generic compile-fix step, so make sure System.IO is present.
@(
    (Join-Path $root 'MainWindow.xaml.cs'),
    (Join-Path $root 'Views/EditStoryWindow.xaml.cs'),
    (Join-Path $root 'Services/CatalogEntryService.cs')
) | ForEach-Object {
    $source = Get-Content $_ -Raw
    if ($source -notmatch '(?m)^using System\.IO;') {
        $prefix = 'using System.IO;' + [Environment]::NewLine
        Set-Content -Path $_ -Value ($prefix + $source) -Encoding utf8
    }
}
Remove-Item $featureZip -Force -ErrorAction SilentlyContinue
Remove-Item $featureStage -Recurse -Force -ErrorAction SilentlyContinue

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
$text = $text.Replace('<Version>0.3.0</Version>', '<Version>1.0.8</Version>')
$text = $text.Replace('<AssemblyVersion>0.3.0.0</AssemblyVersion>', '<AssemblyVersion>1.0.8.0</AssemblyVersion>')
$text = $text.Replace('<FileVersion>0.3.0.0</FileVersion>', '<FileVersion>1.0.8.0</FileVersion>')
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


# Give the custom antique title bar real Windows caption behavior so Aero Snap,
# Win+Arrow, drag-to-edge, drag-to-top, and Windows 11 Snap Layouts work.
$mainXaml = Join-Path $root 'MainWindow.xaml'
$text = Get-Content $mainXaml -Raw
$text = $text.Replace('CaptionHeight="0"', 'CaptionHeight="54"')
$text = $text.Replace(' BorderThickness="0,0,0,1" MouseLeftButtonDown="TitleBar_MouseLeftButtonDown">', ' BorderThickness="0,0,0,1">')
$text = $text.Replace(
    '<Button Content="—" Click="Minimize_Click" Style="{StaticResource WindowButtonStyle}" ToolTip="Minimize"/>',
    '<Button Content="—" Click="Minimize_Click" Style="{StaticResource WindowButtonStyle}" ToolTip="Minimize" shell:WindowChrome.IsHitTestVisibleInChrome="True"/>'
)
$text = $text.Replace(
    '<Button Content="□" Click="Maximize_Click" Style="{StaticResource WindowButtonStyle}" ToolTip="Maximize / Restore"/>',
    '<Button Content="□" Click="Maximize_Click" Style="{StaticResource WindowButtonStyle}" ToolTip="Maximize / Restore" shell:WindowChrome.IsHitTestVisibleInChrome="True"/>'
)
$text = $text.Replace(
    '<Button Content="×" Click="Close_Click" Style="{StaticResource WindowButtonStyle}" ToolTip="Close"/>',
    '<Button Content="×" Click="Close_Click" Style="{StaticResource WindowButtonStyle}" ToolTip="Close" shell:WindowChrome.IsHitTestVisibleInChrome="True"/>'
)
Set-Content -Path $mainXaml -Value $text -Encoding utf8

# 1.0.8 readability pass:
# - give the dossier more width on large windows without breaking snapped layouts
# - enlarge both Title Card display areas
# - enlarge the Summary editor and snap its vertical scrolling to whole lines
$mainXaml = Join-Path $root 'MainWindow.xaml'
$text = Get-Content $mainXaml -Raw
$text = $text.Replace(
    '<ColumnDefinition Width="430"/>',
    '<ColumnDefinition Width="0.85*" MinWidth="430" MaxWidth="700"/>'
)
$text = $text.Replace(
    'Width="282" Height="350" Margin="0,0,16,16"',
    'Width="306" Height="410" Margin="0,0,16,16"'
)
$text = $text.Replace(
    '<RowDefinition Height="150"/>',
    '<RowDefinition Height="195"/>'
)
$text = $text.Replace(
    'BorderThickness="1" Height="165" Margin="0,0,0,8" ClipToBounds="True"',
    'BorderThickness="1" Height="230" Margin="0,0,0,8" ClipToBounds="True"'
)
$text = $text.Replace(
    '<TextBox x:Name="SummaryEditor" AcceptsReturn="True" TextWrapping="Wrap" VerticalScrollBarVisibility="Auto" MinHeight="190" MaxHeight="310" FontSize="14" TextChanged="Editor_TextChanged" SpellCheck.IsEnabled="True"/>',
    '<TextBox x:Name="SummaryEditor" AcceptsReturn="True" TextWrapping="Wrap" HorizontalScrollBarVisibility="Disabled" VerticalScrollBarVisibility="Auto" MinHeight="320" MaxHeight="520" FontSize="14" Padding="12,12,18,12" VerticalContentAlignment="Top" TextOptions.TextFormattingMode="Display" Loaded="SummaryEditor_Loaded" TextChanged="Editor_TextChanged" SpellCheck.IsEnabled="True"/>'
)
Set-Content -Path $mainXaml -Value $text -Encoding utf8

$mainCode = Join-Path $root 'MainWindow.xaml.cs'
$code = Get-Content $mainCode -Raw
if ($code -notmatch '_summaryScrollViewer') {
    $code = $code.Replace(
        '    private bool _loadingEditor;',
        ('    private bool _loadingEditor;' + [Environment]::NewLine + '    private ScrollViewer? _summaryScrollViewer;' + [Environment]::NewLine + '    private bool _summaryScrollSnapping;')
    )

    $summaryMethods = @'
    private void SummaryEditor_Loaded(object sender, RoutedEventArgs e)
    {
        _summaryScrollViewer ??= FindVisualChild<ScrollViewer>(SummaryEditor);
        if (_summaryScrollViewer is null) return;

        _summaryScrollViewer.ScrollChanged -= SummaryScrollViewer_ScrollChanged;
        _summaryScrollViewer.ScrollChanged += SummaryScrollViewer_ScrollChanged;
    }

    private void SummaryScrollViewer_ScrollChanged(object sender, ScrollChangedEventArgs e)
    {
        if (_summaryScrollSnapping || Math.Abs(e.VerticalChange) < 0.01) return;

        Dispatcher.BeginInvoke(() =>
        {
            if (_summaryScrollSnapping || _summaryScrollViewer is null) return;

            var firstLine = SummaryEditor.GetFirstVisibleLineIndex();
            if (firstLine < 0 || firstLine >= SummaryEditor.LineCount) return;

            var characterIndex = SummaryEditor.GetCharacterIndexFromLineIndex(firstLine);
            if (characterIndex < 0) return;

            var rect = SummaryEditor.GetRectFromCharacterIndex(characterIndex);
            if (rect.IsEmpty || rect.Top >= 0) return;

            var nextLine = Math.Min(firstLine + 1, Math.Max(0, SummaryEditor.LineCount - 1));
            _summaryScrollSnapping = true;
            _summaryScrollViewer.ScrollChanged -= SummaryScrollViewer_ScrollChanged;
            SummaryEditor.ScrollToLine(nextLine);
            _summaryScrollViewer.ScrollChanged += SummaryScrollViewer_ScrollChanged;
            _summaryScrollSnapping = false;
        }, DispatcherPriority.Background);
    }

    private static T? FindVisualChild<T>(DependencyObject parent) where T : DependencyObject
    {
        for (var i = 0; i < VisualTreeHelper.GetChildrenCount(parent); i++)
        {
            var child = VisualTreeHelper.GetChild(parent, i);
            if (child is T match) return match;

            var nested = FindVisualChild<T>(child);
            if (nested is not null) return nested;
        }

        return null;
    }

'@

    $code = $code.Replace(
        '    private void Editor_TextChanged(object sender, TextChangedEventArgs e) => QueueSave();',
        ($summaryMethods + '    private void Editor_TextChanged(object sender, TextChangedEventArgs e) => QueueSave();')
    )
}
Set-Content -Path $mainCode -Value $code -Encoding utf8
