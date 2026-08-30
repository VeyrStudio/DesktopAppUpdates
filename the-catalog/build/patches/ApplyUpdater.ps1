$ErrorActionPreference = 'Stop'
$root = 'catalog-source/TheCatalog-WPF-v0.3-runtime-src'
$patchRoot = 'the-catalog/build/patches'

# Overlay the 1.0.12 story workflow: wider cards, popup editor, and .catalogentry importing.
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
if ($null -eq $featureBytes) { throw 'The 1.0.12 feature bundle did not match its verified SHA-256.' }

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
$text = $text.Replace('<Version>0.3.0</Version>', '<Version>1.0.12</Version>')
$text = $text.Replace('<AssemblyVersion>0.3.0.0</AssemblyVersion>', '<AssemblyVersion>1.0.12.0</AssemblyVersion>')
$text = $text.Replace('<FileVersion>0.3.0.0</FileVersion>', '<FileVersion>1.0.12.0</FileVersion>')
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

# 1.0.12 readability pass:
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

# 1.0.12: make story deletion obvious instead of hiding it only in the ellipsis menu.
$mainXaml = Join-Path $root 'MainWindow.xaml'
$text = Get-Content $mainXaml -Raw
$editButton = '<Button Content="EDIT" Style="{StaticResource PaperButtonStyle}" Padding="10,5" Margin="6,0,4,0" Click="EditStory_Click" ToolTip="Edit this story in its own window"/>'
$visibleDelete = '<Button Content="DELETE" Style="{StaticResource BurgundyButtonStyle}" Padding="10,5" Margin="0,0,4,0" Click="DeleteStory_Click" ToolTip="Move this story to Recently Deleted"/>'
if ($text -notmatch 'Content="DELETE"[^>]+Click="DeleteStory_Click"') {
    $text = $text.Replace($editButton, $editButton + [Environment]::NewLine + '                                ' + $visibleDelete)
}
Set-Content -Path $mainXaml -Value $text -Encoding utf8

# 1.0.12: broaden the secondary-name field from 'Original' to 'Other'.
# Keep the underlying model/database property names unchanged for backward compatibility.
@(
    (Join-Path $root 'MainWindow.xaml'),
    (Join-Path $root 'Views/EditStoryWindow.xaml')
) | ForEach-Object {
    $xaml = Get-Content $_ -Raw
    $xaml = $xaml.Replace('Has an original name', 'Has another name')
    $xaml = $xaml.Replace('HAS AN ORIGINAL NAME', 'HAS ANOTHER NAME')
    $xaml = $xaml.Replace('Original name', 'Other name')
    $xaml = $xaml.Replace('ORIGINAL NAME', 'OTHER NAME')
    $xaml = $xaml.Replace('Text="Original"', 'Text="Other"')
    $xaml = $xaml.Replace('Content="Original"', 'Content="Other"')
    $xaml = $xaml.Replace('Text="ORIGINAL"', 'Text="OTHER"')
    $xaml = $xaml.Replace('Content="ORIGINAL"', 'Content="OTHER"')
    Set-Content -Path $_ -Value $xaml -Encoding utf8
}

# 1.0.12: make the right Story Dossier column collapsible.
$mainXaml = Join-Path $root 'MainWindow.xaml'
$text = Get-Content $mainXaml -Raw
$text = $text.Replace(
    '<ColumnDefinition Width="0.85*" MinWidth="430" MaxWidth="700"/>',
    '<ColumnDefinition x:Name="DossierColumn" Width="0.85*" MinWidth="430" MaxWidth="700"/>'
)
$text = $text.Replace(
    '<Border Grid.Column="2" Margin="0,12,12,12" Background="#11100F" BorderBrush="#82633B" BorderThickness="1" Effect="{StaticResource SmallPaperShadow}">',
    '<Border x:Name="DossierBorder" Grid.Column="2" Margin="0,12,12,12" Background="#11100F" BorderBrush="#82633B" BorderThickness="1" Effect="{StaticResource SmallPaperShadow}">'
)
$storyHeader = '<DockPanel Grid.Row="1" Margin="0,17,0,12">'
$toggle = '<Button x:Name="DossierToggleButton" Content="HIDE DOSSIER  ‹" DockPanel.Dock="Right" Style="{StaticResource FlatInkButtonStyle}" Foreground="{StaticResource GoldBrush}" FontSize="11" Padding="10,3" Margin="12,0,0,0" Click="DossierToggle_Click" ToolTip="Collapse or restore the Story Dossier"/>'
if ($text -notmatch 'x:Name="DossierToggleButton"') {
    $text = $text.Replace($storyHeader, $storyHeader + [Environment]::NewLine + '                        ' + $toggle)
}
Set-Content -Path $mainXaml -Value $text -Encoding utf8

$mainCode = Join-Path $root 'MainWindow.xaml.cs'
$code = Get-Content $mainCode -Raw
if ($code -notmatch '_dossierCollapsed') {
    $fieldAnchor = '    private bool _loadingEditor;'
    if ($code.Contains($fieldAnchor)) {
        $code = $code.Replace($fieldAnchor, $fieldAnchor + [Environment]::NewLine + '    private bool _dossierCollapsed;')
    }

    $method = @'

    private void DossierToggle_Click(object sender, RoutedEventArgs e)
    {
        if (!_dossierCollapsed)
        {
            DossierBorder.Visibility = Visibility.Collapsed;
            DossierColumn.MinWidth = 0;
            DossierColumn.MaxWidth = 0;
            DossierColumn.Width = new GridLength(0);
            DossierToggleButton.Content = "SHOW DOSSIER  ›";
            DossierToggleButton.ToolTip = "Restore the Story Dossier";
            _dossierCollapsed = true;
        }
        else
        {
            DossierColumn.MaxWidth = 700;
            DossierColumn.MinWidth = 430;
            DossierColumn.Width = new GridLength(0.85, GridUnitType.Star);
            DossierBorder.Visibility = Visibility.Visible;
            DossierToggleButton.Content = "HIDE DOSSIER  ‹";
            DossierToggleButton.ToolTip = "Collapse the Story Dossier";
            _dossierCollapsed = false;
        }
    }
'@

    $lastBrace = $code.LastIndexOf('}')
    if ($lastBrace -lt 0) { throw 'Could not find MainWindow class closing brace for dossier toggle.' }
    $code = $code.Insert($lastBrace, $method + [Environment]::NewLine)
}
Set-Content -Path $mainCode -Value $code -Encoding utf8

# 1.0.12: single centered story carousel with full-height title artwork.
$mainXaml = Join-Path $root 'MainWindow.xaml'
$text = Get-Content $mainXaml -Raw

$carouselStart = $text.IndexOf('                    <ScrollViewer Grid.Row="2" VerticalScrollBarVisibility="Auto" HorizontalScrollBarVisibility="Disabled">')
if ($carouselStart -lt 0) { throw 'Could not find story-list start for carousel conversion.' }
$carouselEndMarker = '                    </ScrollViewer>'
$carouselEnd = $text.IndexOf($carouselEndMarker, $carouselStart)
if ($carouselEnd -lt 0) { throw 'Could not find story-list end for carousel conversion.' }
$carouselEnd += $carouselEndMarker.Length

$carousel = @'
                    <Grid Grid.Row="2" Margin="0,0,0,12">
                        <Grid.ColumnDefinitions>
                            <ColumnDefinition Width="76"/>
                            <ColumnDefinition Width="*"/>
                            <ColumnDefinition Width="76"/>
                        </Grid.ColumnDefinitions>

                        <Button Grid.Column="0" Content="‹" Click="PreviousStory_Click" Style="{StaticResource FlatInkButtonStyle}"
                                FontSize="52" Foreground="{StaticResource GoldBrush}" Padding="8"
                                HorizontalAlignment="Center" VerticalAlignment="Center" ToolTip="Previous story"/>

                        <ScrollViewer Grid.Column="1" VerticalScrollBarVisibility="Auto" HorizontalScrollBarVisibility="Disabled"
                                      HorizontalContentAlignment="Center">
                            <ItemsControl x:Name="StoriesList" HorizontalAlignment="Center">
                                <ItemsControl.ItemTemplate>
                                    <DataTemplate>
                                        <Button Click="StoryCard_Click" Tag="{Binding Id}" Width="430" Height="730" Margin="8,0,8,18" Padding="0"
                                                Background="Transparent" BorderThickness="0" HorizontalContentAlignment="Stretch"
                                                VerticalContentAlignment="Stretch" Cursor="Hand">
                                            <Border x:Name="StoryCard" Background="{StaticResource CardPaperTextureBrush}"
                                                    BorderBrush="#5B452C" BorderThickness="1" Effect="{StaticResource SmallPaperShadow}">
                                                <Grid>
                                                    <Grid.RowDefinitions>
                                                        <RowDefinition Height="560"/>
                                                        <RowDefinition Height="*"/>
                                                    </Grid.RowDefinitions>

                                                    <Grid Grid.Row="0" ClipToBounds="True" Background="#080707">
                                                        <Image Source="{Binding CardPreviewPath}" Stretch="Uniform" Margin="8"/>
                                                        <TextBlock Text="❦" FontSize="48" Foreground="#6FA9844E"
                                                                   HorizontalAlignment="Center" VerticalAlignment="Center">
                                                            <TextBlock.Style>
                                                                <Style TargetType="TextBlock">
                                                                    <Setter Property="Visibility" Value="Collapsed"/>
                                                                    <Style.Triggers>
                                                                        <DataTrigger Binding="{Binding CardPreviewPath}" Value="{x:Null}">
                                                                            <Setter Property="Visibility" Value="Visible"/>
                                                                        </DataTrigger>
                                                                        <DataTrigger Binding="{Binding CardPreviewPath}" Value="">
                                                                            <Setter Property="Visibility" Value="Visible"/>
                                                                        </DataTrigger>
                                                                    </Style.Triggers>
                                                                </Style>
                                                            </TextBlock.Style>
                                                        </TextBlock>
                                                        <Border BorderBrush="#66513A" BorderThickness="0,0,0,1"/>
                                                    </Grid>

                                                    <Grid Grid.Row="1" Margin="18,12,18,13">
                                                        <Grid.RowDefinitions>
                                                            <RowDefinition Height="Auto"/>
                                                            <RowDefinition Height="Auto"/>
                                                            <RowDefinition Height="Auto"/>
                                                            <RowDefinition Height="*"/>
                                                            <RowDefinition Height="Auto"/>
                                                        </Grid.RowDefinitions>
                                                        <TextBlock Text="{Binding Title}" FontSize="20" Foreground="#D6B47B"
                                                                   FontWeight="Bold" TextWrapping="Wrap" MaxHeight="52"/>
                                                        <TextBlock Grid.Row="1" Text="{Binding PairingDisplay}" FontSize="13"
                                                                   Foreground="{StaticResource InkBrush}" Margin="0,5,0,6" TextTrimming="CharacterEllipsis"/>
                                                        <Border Grid.Row="2" HorizontalAlignment="Left" BorderBrush="#6D423A"
                                                                BorderThickness="1" Background="#2A1115" Padding="7,2" Margin="0,0,0,7">
                                                            <TextBlock Text="{Binding PairingCategory}" FontSize="11" Foreground="#C7A98B"/>
                                                        </Border>
                                                        <TextBlock Grid.Row="3" Text="{Binding SummaryPreview}" Foreground="{StaticResource InkSoftBrush}"
                                                                   FontSize="12.5" TextWrapping="Wrap" LineHeight="18" MaxHeight="48"/>
                                                        <TextBlock Grid.Row="4" Text="{Binding UpdatedDisplay}" Foreground="#746652"
                                                                   FontSize="10.5" Margin="0,7,0,0"/>
                                                    </Grid>
                                                </Grid>
                                                <Border.Style>
                                                    <Style TargetType="Border">
                                                        <Style.Triggers>
                                                            <DataTrigger Binding="{Binding IsSelected}" Value="True">
                                                                <Setter Property="BorderBrush" Value="#B18A52"/>
                                                                <Setter Property="BorderThickness" Value="2"/>
                                                            </DataTrigger>
                                                        </Style.Triggers>
                                                    </Style>
                                                </Border.Style>
                                            </Border>
                                        </Button>
                                    </DataTemplate>
                                </ItemsControl.ItemTemplate>
                            </ItemsControl>
                        </ScrollViewer>

                        <Button Grid.Column="2" Content="›" Click="NextStory_Click" Style="{StaticResource FlatInkButtonStyle}"
                                FontSize="52" Foreground="{StaticResource GoldBrush}" Padding="8"
                                HorizontalAlignment="Center" VerticalAlignment="Center" ToolTip="Next story"/>
                    </Grid>
'@
$text = $text.Substring(0, $carouselStart) + $carousel + $text.Substring($carouselEnd)

# Remove the old duplicate navigation arrows from the dossier header.
$text = $text.Replace('                                <Button Content="‹" Style="{StaticResource FlatInkButtonStyle}" FontSize="22" Padding="7,1" Click="PreviousStory_Click" ToolTip="Previous story"/>' + [Environment]::NewLine, '')
$text = $text.Replace('                                <Button Content="›" Style="{StaticResource FlatInkButtonStyle}" FontSize="22" Padding="7,1" Click="NextStory_Click" ToolTip="Next story"/>' + [Environment]::NewLine, '')
Set-Content -Path $mainXaml -Value $text -Encoding utf8

$mainCode = Join-Path $root 'MainWindow.xaml.cs'
$code = Get-Content $mainCode -Raw
$oldRefresh = '    private void RefreshStoryList() => StoriesList.ItemsSource = GetVisibleStories();'
$newRefresh = @'
    private void RefreshStoryList()
    {
        var visible = GetVisibleStories();
        Story? display = null;

        if (_selectedStory is not null)
            display = visible.FirstOrDefault(s => s.Id == _selectedStory.Id);

        display ??= visible.FirstOrDefault();
        StoriesList.ItemsSource = display is null ? Array.Empty<Story>() : new[] { display };
    }
'@
if ($code.Contains($oldRefresh)) {
    $code = $code.Replace($oldRefresh, $newRefresh.TrimEnd())
} else {
    throw 'Could not find RefreshStoryList for carousel conversion.'
}
Set-Content -Path $mainCode -Value $code -Encoding utf8
