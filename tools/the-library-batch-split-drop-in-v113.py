from pathlib import Path
import base64, hashlib, json

ROOT = Path(__file__).resolve().parents[1]
TF = ROOT / "the-library"
VERSION = "1.0.13"

manifest = json.loads((TF / "manifest.json").read_text(encoding="utf-8"))
if manifest.get("version") != "1.0.12":
    raise SystemExit(f"Expected live base 1.0.12, got {manifest.get('version')}")

dropin = r"""# THE LIBRARY BATCH SPLIT DROP-IN v1.0.13
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

function New-LibraryDropInLabel([string]$Text,[int]$X,[int]$Y,[int]$W=150){
    $label=New-Object Windows.Forms.Label
    $label.Text=$Text
    $label.AutoSize=$false
    $label.Size=New-Object Drawing.Size($W,20)
    $label.Location=New-Object Drawing.Point($X,$Y)
    $label.ForeColor=[Drawing.Color]::FromArgb(80,60,45)
    return $label
}

function New-LibraryDropInTextBox([int]$X,[int]$Y,[int]$W){
    $box=New-Object Windows.Forms.TextBox
    $box.Location=New-Object Drawing.Point($X,$Y)
    $box.Size=New-Object Drawing.Size($W,24)
    return $box
}

function Open-LibraryDropInBitmap([string]$Path){
    if([string]::IsNullOrWhiteSpace($Path)){throw 'Image path is empty.'}
    if(-not(Test-Path -LiteralPath $Path -PathType Leaf)){throw ('Image file was not found: '+$Path)}

    $bytes=$null
    $stream=$null
    $source=$null
    $copy=$null
    $graphics=$null
    try{
        $bytes=[IO.File]::ReadAllBytes($Path)
        if($null -eq $bytes -or $bytes.Length -eq 0){throw 'Image file is empty.'}
        $stream=New-Object IO.MemoryStream(,$bytes)
        $source=[Drawing.Image]::FromStream($stream,$true,$true)
        if($null -eq $source){throw 'Windows could not decode the image.'}
        if($source.Width -le 0 -or $source.Height -le 0){throw 'Image dimensions are invalid.'}

        $copy=New-Object Drawing.Bitmap($source.Width,$source.Height,[Drawing.Imaging.PixelFormat]::Format32bppArgb)
        $graphics=[Drawing.Graphics]::FromImage($copy)
        if($null -eq $graphics){throw 'Windows could not create a drawing surface.'}
        $dest=New-Object Drawing.Rectangle(0,0,$copy.Width,$copy.Height)
        $graphics.DrawImage($source,$dest,0,0,$source.Width,$source.Height,[Drawing.GraphicsUnit]::Pixel)
        return $copy
    }
    catch{
        if($null -ne $copy){try{$copy.Dispose()}catch{}}
        throw
    }
    finally{
        if($null -ne $graphics){try{$graphics.Dispose()}catch{}}
        if($null -ne $source){try{$source.Dispose()}catch{}}
        if($null -ne $stream){try{$stream.Dispose()}catch{}}
    }
}

function Get-LibraryDropInDisplayRect($PictureBox,$Bitmap){
    if($null -eq $PictureBox -or $null -eq $Bitmap){return [Drawing.RectangleF]::Empty}
    $cw=[double]$PictureBox.ClientSize.Width
    $ch=[double]$PictureBox.ClientSize.Height
    $iw=[double]$Bitmap.Width
    $ih=[double]$Bitmap.Height
    if($cw -le 0 -or $ch -le 0 -or $iw -le 0 -or $ih -le 0){return [Drawing.RectangleF]::Empty}
    $scale=[math]::Min($cw/$iw,$ch/$ih)
    $dw=$iw*$scale
    $dh=$ih*$scale
    return New-Object Drawing.RectangleF(
        [single](($cw-$dw)/2.0),
        [single](($ch-$dh)/2.0),
        [single]$dw,
        [single]$dh
    )
}

function Save-LibraryDropInCrop($Bitmap,[Drawing.Rectangle]$SourceRect,[string]$Destination){
    if($null -eq $Bitmap){throw 'The cover image is no longer available.'}
    if($SourceRect.Width -le 0 -or $SourceRect.Height -le 0){throw 'A crop region has zero size.'}

    $output=$null
    $graphics=$null
    try{
        $output=New-Object Drawing.Bitmap($SourceRect.Width,$SourceRect.Height,[Drawing.Imaging.PixelFormat]::Format32bppArgb)
        $graphics=[Drawing.Graphics]::FromImage($output)
        if($null -eq $graphics){throw 'Could not create the crop drawing surface.'}
        $dest=New-Object Drawing.Rectangle(0,0,$output.Width,$output.Height)
        $graphics.DrawImage($Bitmap,$dest,$SourceRect,[Drawing.GraphicsUnit]::Pixel)
        $output.Save($Destination,[Drawing.Imaging.ImageFormat]::Png)
    }
    finally{
        if($null -ne $graphics){try{$graphics.Dispose()}catch{}}
        if($null -ne $output){try{$output.Dispose()}catch{}}
    }
}

function Save-LibraryDropInCover($State){
    if($null -eq $State){throw 'This cover editor lost its state.'}
    if($null -eq $State.Bitmap){throw 'This cover editor no longer has an image.'}

    $left=[int]$State.LeftNum.Value
    $right=[int]$State.RightNum.Value
    $width=[int]$State.Bitmap.Width
    $height=[int]$State.Bitmap.Height

    if($left -lt 1 -or $right -gt ($width-1) -or $left -ge $right){
        throw 'The spine guides are not valid.'
    }

    $base=[IO.Path]::GetFileNameWithoutExtension([string]$State.Path)
    $tempDir=Join-Path ([IO.Path]::GetTempPath()) ('TheLibrary-DropIn-'+[guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $tempDir -Force|Out-Null
    try{
        $pieces=@(
            [pscustomobject]@{Position='Back Cover';Name=($base+' - Back Cover.png');Rect=(New-Object Drawing.Rectangle(0,0,$left,$height))},
            [pscustomobject]@{Position='Spine';Name=($base+' - Spine.png');Rect=(New-Object Drawing.Rectangle($left,0,($right-$left),$height))},
            [pscustomobject]@{Position='Front Cover';Name=($base+' - Front Cover.png');Rect=(New-Object Drawing.Rectangle($right,0,($width-$right),$height))}
        )

        foreach($piece in $pieces){
            $tempPath=Join-Path $tempDir $piece.Name
            Save-LibraryDropInCrop $State.Bitmap $piece.Rect $tempPath
            $stored=Copy-Or-Move-IntoVault $tempPath $false
            $script:PendingCoverType=[string]$State.CoverType.Text
            Add-LibraryRecord -OriginalName $piece.Name -StoredName $stored -Position $piece.Position -Project $State.Project.Text -Ship $State.Ship.Text -Fandom $State.Fandom.Text -Tags $State.Tags.Text | Out-Null
        }
    }
    finally{
        Remove-Item -LiteralPath $tempDir -Force -Recurse -ErrorAction SilentlyContinue
    }
}

function New-LibraryDropInBatchPanel([string]$Path,[int]$Ordinal,[int]$Total){
    $bitmap=Open-LibraryDropInBitmap $Path

    $panel=New-Object Windows.Forms.Panel
    $panel.Width=[math]::Max(780,$tabSplit.ClientSize.Width-40)
    $panel.Height=700
    $panel.BorderStyle='FixedSingle'
    $panel.BackColor=[Drawing.Color]::FromArgb(246,236,211)
    $panel.Margin=New-Object Windows.Forms.Padding(8)

    $head=New-Object Windows.Forms.Label
    $head.Text=("COVER {0} OF {1}  -  {2}" -f $Ordinal,$Total,[IO.Path]::GetFileName($Path))
    $head.AutoSize=$true
    $head.Font=New-Object Drawing.Font('Segoe UI',11,[Drawing.FontStyle]::Bold)
    $head.ForeColor=[Drawing.Color]::FromArgb(65,45,33)
    $head.Location=New-Object Drawing.Point(14,12)
    $panel.Controls.Add($head)

    $pic=New-Object Windows.Forms.PictureBox
    $pic.Location=New-Object Drawing.Point(14,44)
    $pic.Size=New-Object Drawing.Size(470,360)
    $pic.SizeMode='Zoom'
    $pic.BackColor=[Drawing.Color]::FromArgb(28,23,20)
    $pic.Image=$bitmap
    $panel.Controls.Add($pic)

    $center=[int]([math]::Round($bitmap.Width/2.0))
    $half=[int]([math]::Max(2,[math]::Round($bitmap.Width*0.04)))

    $leftNum=New-Object Windows.Forms.NumericUpDown
    $leftNum.Minimum=1
    $leftNum.Maximum=[math]::Max(1,$bitmap.Width-2)
    $leftNum.Value=[math]::Max(1,$center-$half)
    $leftNum.Location=New-Object Drawing.Point(14,438)
    $leftNum.Width=110
    $panel.Controls.Add((New-LibraryDropInLabel 'BACK / SPINE EDGE' 14 416 150))
    $panel.Controls.Add($leftNum)

    $rightNum=New-Object Windows.Forms.NumericUpDown
    $rightNum.Minimum=2
    $rightNum.Maximum=[math]::Max(2,$bitmap.Width-1)
    $rightNum.Value=[math]::Min($bitmap.Width-1,$center+$half)
    $rightNum.Location=New-Object Drawing.Point(150,438)
    $rightNum.Width=110
    $panel.Controls.Add((New-LibraryDropInLabel 'SPINE / FRONT EDGE' 150 416 160))
    $panel.Controls.Add($rightNum)

    $panel.Controls.Add((New-LibraryDropInLabel 'TITLE / BOOK' 510 52 180))
    $project=New-LibraryDropInTextBox 510 74 235
    $panel.Controls.Add($project)

    $panel.Controls.Add((New-LibraryDropInLabel 'SHIP' 510 112 180))
    $ship=New-LibraryDropInTextBox 510 134 235
    $panel.Controls.Add($ship)

    $panel.Controls.Add((New-LibraryDropInLabel 'FANDOM' 510 172 180))
    $fandom=New-LibraryDropInTextBox 510 194 235
    $panel.Controls.Add($fandom)

    $panel.Controls.Add((New-LibraryDropInLabel 'EXTRA TAGS' 510 232 180))
    $tags=New-LibraryDropInTextBox 510 254 235
    $panel.Controls.Add($tags)

    $panel.Controls.Add((New-LibraryDropInLabel 'COVER TYPE' 510 292 180))
    $coverType=New-LibraryDropInTextBox 510 314 235
    $panel.Controls.Add($coverType)

    $status=New-Object Windows.Forms.Label
    $status.Text='NOT SAVED'
    $status.AutoSize=$true
    $status.Font=New-Object Drawing.Font('Segoe UI',9,[Drawing.FontStyle]::Bold)
    $status.ForeColor=[Drawing.Color]::FromArgb(120,70,40)
    $status.Location=New-Object Drawing.Point(510,365)
    $panel.Controls.Add($status)

    $save=New-Object Windows.Forms.Button
    $save.Text='SAVE THIS COVER TO LIBRARY'
    $save.Location=New-Object Drawing.Point(510,392)
    $save.Size=New-Object Drawing.Size(235,42)
    $panel.Controls.Add($save)

    $remove=New-Object Windows.Forms.Button
    $remove.Text='REMOVE THIS COVER'
    $remove.Location=New-Object Drawing.Point(510,444)
    $remove.Size=New-Object Drawing.Size(235,34)
    $panel.Controls.Add($remove)

    $state=[pscustomobject]@{
        Bitmap=$bitmap
        Path=$Path
        Panel=$panel
        Pic=$pic
        LeftNum=$leftNum
        RightNum=$rightNum
        DragState=[pscustomobject]@{Which=''}
        Project=$project
        Ship=$ship
        Fandom=$fandom
        Tags=$tags
        CoverType=$coverType
        Status=$status
    }

    $panel.Tag=$state
    $pic.Tag=$state
    $leftNum.Tag=$state
    $rightNum.Tag=$state
    $save.Tag=$state
    $remove.Tag=$state

    $pic.Add_Paint({
        param($sender,$e)
        $st=$sender.Tag
        if($null -eq $st -or $null -eq $st.Bitmap -or $null -eq $e -or $null -eq $e.Graphics){return}
        $rect=Get-LibraryDropInDisplayRect $sender $st.Bitmap
        if($rect.Width -le 0){return}
        $x1=[single]($rect.X+([int]$st.LeftNum.Value/[double]$st.Bitmap.Width)*$rect.Width)
        $x2=[single]($rect.X+([int]$st.RightNum.Value/[double]$st.Bitmap.Width)*$rect.Width)
        $pen=$null
        try{
            $pen=New-Object Drawing.Pen([Drawing.Color]::FromArgb(240,196,80),3)
            $e.Graphics.DrawLine($pen,$x1,$rect.Y,$x1,$rect.Bottom)
            $e.Graphics.DrawLine($pen,$x2,$rect.Y,$x2,$rect.Bottom)
        }finally{
            if($null -ne $pen){try{$pen.Dispose()}catch{}}
        }
    })

    $leftNum.Add_ValueChanged({
        param($sender,$e)
        $st=$sender.Tag
        if($null -ne $st -and $null -ne $st.Pic){$st.Pic.Invalidate()}
    })
    $rightNum.Add_ValueChanged({
        param($sender,$e)
        $st=$sender.Tag
        if($null -ne $st -and $null -ne $st.Pic){$st.Pic.Invalidate()}
    })

    $pic.Add_MouseDown({
        param($sender,$e)
        $st=$sender.Tag
        if($null -eq $st -or $null -eq $st.Bitmap){return}
        $rect=Get-LibraryDropInDisplayRect $sender $st.Bitmap
        if($rect.Width -le 0){return}
        $x1=$rect.X+([int]$st.LeftNum.Value/[double]$st.Bitmap.Width)*$rect.Width
        $x2=$rect.X+([int]$st.RightNum.Value/[double]$st.Bitmap.Width)*$rect.Width
        $st.DragState.Which=''
        if([math]::Abs($e.X-$x1) -le [math]::Abs($e.X-$x2)){
            if([math]::Abs($e.X-$x1) -le 16){$st.DragState.Which='Left'}
        }else{
            if([math]::Abs($e.X-$x2) -le 16){$st.DragState.Which='Right'}
        }
    })

    $pic.Add_MouseMove({
        param($sender,$e)
        $st=$sender.Tag
        if($null -eq $st -or $null -eq $st.Bitmap -or $null -eq $st.DragState){return}
        if([string]::IsNullOrEmpty([string]$st.DragState.Which)){return}
        $rect=Get-LibraryDropInDisplayRect $sender $st.Bitmap
        if($rect.Width -le 0){return}
        $px=[int][math]::Round((($e.X-$rect.X)/$rect.Width)*$st.Bitmap.Width)
        $px=[math]::Max(1,[math]::Min($st.Bitmap.Width-1,$px))
        if($st.DragState.Which -eq 'Left'){
            $px=[math]::Min($px,[int]$st.RightNum.Value-1)
            $st.LeftNum.Value=[decimal][math]::Max([double]$st.LeftNum.Minimum,[math]::Min([double]$st.LeftNum.Maximum,$px))
        }else{
            $px=[math]::Max($px,[int]$st.LeftNum.Value+1)
            $st.RightNum.Value=[decimal][math]::Max([double]$st.RightNum.Minimum,[math]::Min([double]$st.RightNum.Maximum,$px))
        }
    })

    $pic.Add_MouseUp({
        param($sender,$e)
        $st=$sender.Tag
        if($null -ne $st -and $null -ne $st.DragState){$st.DragState.Which=''}
    })
    $pic.Add_MouseLeave({
        param($sender,$e)
        $st=$sender.Tag
        if($null -ne $st -and $null -ne $st.DragState){$st.DragState.Which=''}
    })

    $save.Add_Click({
        param($sender,$e)
        $st=$sender.Tag
        try{
            Save-LibraryDropInCover $st
            Refresh-HierarchyTree
            Refresh-LibraryGrid
            $st.Status.Text='SAVED TO LIBRARY'
            $st.Status.ForeColor=[Drawing.Color]::FromArgb(35,120,65)
            $sender.Enabled=$false
        }catch{
            [Windows.Forms.MessageBox]::Show(
                ('Could not save this cover to The Library.'+[Environment]::NewLine+[Environment]::NewLine+$_.Exception.Message),
                'Batch Split'
            )|Out-Null
        }
    })

    $remove.Add_Click({
        param($sender,$e)
        $st=$sender.Tag
        if($null -eq $st){return}
        if($null -ne $st.Pic){$st.Pic.Image=$null}
        if($null -ne $st.Bitmap){try{$st.Bitmap.Dispose()}catch{};$st.Bitmap=$null}
        if($null -ne $st.Panel){
            $parent=$st.Panel.Parent
            if($null -ne $parent){$parent.Controls.Remove($st.Panel)}
            $st.Panel.Dispose()
        }
    })

    return $panel
}

function Remove-LibraryDropInBatchHost {
    if($null -eq $tabSplit){return}
    foreach($control in @($tabSplit.Controls)){
        if($control.Name -in @('InlineBatchSplitHost','LibraryDropInBatchHost')){
            foreach($panel in @($control.Controls)){
                try{
                    $st=$panel.Tag
                    if($null -ne $st -and $null -ne $st.Bitmap){
                        if($null -ne $st.Pic){$st.Pic.Image=$null}
                        $st.Bitmap.Dispose()
                        $st.Bitmap=$null
                    }
                }catch{}
            }
            $tabSplit.Controls.Remove($control)
            try{$control.Dispose()}catch{}
        }
    }
}

function Start-LibraryDropInBatchSplit {
    $pick=New-Object Windows.Forms.OpenFileDialog
    $pick.Title='Choose full-wrap covers'
    $pick.Filter='Image files|*.png;*.jpg;*.jpeg;*.bmp;*.tif;*.tiff|All files|*.*'
    $pick.Multiselect=$true
    if($pick.ShowDialog() -ne [Windows.Forms.DialogResult]::OK){return}

    $paths=@($pick.FileNames)
    if($paths.Count -eq 0){return}

    Remove-LibraryDropInBatchHost

    $host=New-Object Windows.Forms.FlowLayoutPanel
    $host.Name='LibraryDropInBatchHost'
    $host.FlowDirection='TopDown'
    $host.WrapContents=$false
    $host.AutoScroll=$true
    $host.Dock='Fill'
    $host.Padding=New-Object Windows.Forms.Padding(10,56,10,10)
    $host.BackColor=$tabSplit.BackColor
    $script:LibraryDropInBatchHost=$host
    $tabSplit.Controls.Add($host)
    $host.BringToFront()

    $failed=New-Object Collections.Generic.List[string]
    $ordinal=0
    foreach($path in $paths){
        try{
            $ordinal++
            $panel=New-LibraryDropInBatchPanel $path $ordinal $paths.Count
            $host.Controls.Add($panel)
        }catch{
            $ordinal--
            $failed.Add(([IO.Path]::GetFileName($path)+': '+$_.Exception.Message))
        }
    }

    if($host.Controls.Count -eq 0){
        $tabSplit.Controls.Remove($host)
        $host.Dispose()
        $detail=if($failed.Count -gt 0){[Environment]::NewLine+[Environment]::NewLine+(@($failed|Select-Object -First 8)-join [Environment]::NewLine)}else{''}
        [Windows.Forms.MessageBox]::Show(('None of those files could be opened as cover images.'+$detail),'Batch Split')|Out-Null
        return
    }

    if($failed.Count -gt 0){
        [Windows.Forms.MessageBox]::Show(
            ("Some covers could not be opened: $($failed.Count)"+[Environment]::NewLine+[Environment]::NewLine+(@($failed|Select-Object -First 8)-join [Environment]::NewLine)),
            'Batch Split'
        )|Out-Null
    }
}

function Start-InlineBatchSplit {
    Start-LibraryDropInBatchSplit
}

function Initialize-LibraryBatchSplitDropIn {
    if($null -eq $tabSplit){throw 'The Split tab is unavailable.'}

    foreach($control in @($tabSplit.Controls)){
        if($control -is [Windows.Forms.Button] -and $control.Text -in @('ADD MULTIPLE FULL WRAPS','BATCH SPLIT WRAPS')){
            $tabSplit.Controls.Remove($control)
            try{$control.Dispose()}catch{}
        }
    }

    $button=New-Object Windows.Forms.Button
    $button.Name='LibraryDropInBatchButton'
    $button.Text='ADD MULTIPLE FULL WRAPS'
    $button.Size=New-Object Drawing.Size(210,36)
    $button.Location=New-Object Drawing.Point(12,12)
    $button.Add_Click({Start-LibraryDropInBatchSplit})
    $tabSplit.Controls.Add($button)
    $button.BringToFront()
    $script:LibraryDropInBatchButton=$button
}
"""

patcher = r"""$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Windows.Forms

$appRoot=Split-Path -Parent $PSScriptRoot
$backupDir=Join-Path $appRoot 'UpdateBackup'
$backupMain=Join-Path $backupDir 'CoverVault.ps1'
$backupVersion=Join-Path $backupDir 'AppVersion.json'
$targetMain=Join-Path $PSScriptRoot 'CoverVault.ps1'
$targetVersion=Join-Path $PSScriptRoot 'AppVersion.json'
$launcher=Join-Path $PSScriptRoot 'Launch Cover Vault.vbs'
$dropIn=Join-Path $PSScriptRoot 'BatchSplitDropIn.ps1'

function Relaunch-App {
    if(Test-Path -LiteralPath $launcher){
        Start-Process -FilePath 'wscript.exe' -ArgumentList ('"' + $launcher + '"')
    }
}

try{
    if(-not(Test-Path -LiteralPath $backupMain)){throw 'The updater backup is missing the previous Library app script.'}
    if(-not(Test-Path -LiteralPath $dropIn)){throw 'The Batch Split drop-in file is missing.'}

    $text=[IO.File]::ReadAllText($backupMain,[Text.Encoding]::UTF8)
    if(-not $text.Contains('$tabSplit')){throw 'Could not find The Library Split tab.'}
    if(-not $text.Contains('function Add-LibraryRecord')){throw 'Could not find The Library record function.'}
    if(-not $text.Contains('function Copy-Or-Move-IntoVault')){throw 'Could not find The Library storage function.'}

    $marker='# LOAD BATCH SPLIT DROP-IN v1.0.13'
    if(-not $text.Contains($marker)){
        $block=@'
# LOAD BATCH SPLIT DROP-IN v1.0.13
$libraryBatchDropIn=Join-Path $PSScriptRoot 'BatchSplitDropIn.ps1'
if(-not(Test-Path -LiteralPath $libraryBatchDropIn)){throw 'BatchSplitDropIn.ps1 is missing.'}
. $libraryBatchDropIn
Initialize-LibraryBatchSplitDropIn

'@

        $patterns=@(
            '(?m)^\s*\[void\]\s*\$form\.ShowDialog\(\)\s*$',
            '(?m)^\s*\$form\.ShowDialog\(\)\s*\|\s*Out-Null\s*$',
            '(?m)^\s*\$form\.ShowDialog\(\)\s*$'
        )
        $match=$null
        foreach($pattern in $patterns){
            $rx=New-Object Text.RegularExpressions.Regex($pattern)
            $candidate=$rx.Match($text)
            if($candidate.Success){$match=$candidate;break}
        }
        if($null -eq $match){throw 'Could not find The Library window startup point.'}
        $text=$text.Substring(0,$match.Index)+$block+$text.Substring($match.Index)
    }

    [IO.File]::WriteAllText($targetMain,$text,(New-Object Text.UTF8Encoding($true)))

    @'
{
  "appId": "the-library",
  "appName": "The Library",
  "version": "1.0.13",
  "manifestUrl": "https://raw.githubusercontent.com/VeyrStudio/DesktopAppUpdates/main/the-library/manifest.json"
}
'@ | Set-Content -LiteralPath $targetVersion -Encoding UTF8

    Relaunch-App
}
catch{
    $message=$_.Exception.Message
    try{if(Test-Path -LiteralPath $backupMain){Copy-Item -LiteralPath $backupMain -Destination $targetMain -Force}}catch{}
    try{if(Test-Path -LiteralPath $backupVersion){Copy-Item -LiteralPath $backupVersion -Destination $targetVersion -Force}}catch{}
    try{
        [Windows.Forms.MessageBox]::Show(
            ('The Library could not install the Batch Split drop-in.'+[Environment]::NewLine+[Environment]::NewLine+$message+[Environment]::NewLine+[Environment]::NewLine+'The previous app version was restored.'),
            'The Library Update'
        )|Out-Null
    }catch{}
    Relaunch-App
}
"""

appver=json.dumps({
    "appId":"the-library",
    "appName":"The Library",
    "version":VERSION,
    "manifestUrl":"https://raw.githubusercontent.com/VeyrStudio/DesktopAppUpdates/main/the-library/manifest.json"
},indent=2).encode()

files=[]
for path,data in [
    ("CoverVault.ps1",patcher.encode("utf-8-sig")),
    ("BatchSplitDropIn.ps1",dropin.encode("utf-8-sig")),
    ("AppVersion.json",appver),
]:
    files.append({
        "path":path,
        "sha256":hashlib.sha256(data).hexdigest(),
        "contentBase64":base64.b64encode(data).decode("ascii")
    })

payload={
    "schemaVersion":1,
    "appId":"the-library",
    "appName":"The Library",
    "version":VERSION,
    "files":files,
    "delete":[]
}
raw=json.dumps(payload,separators=(",",":")).encode()
name="payload-1.0.13-batch-split-drop-in.txt"
(TF/name).write_bytes(raw)
sha=hashlib.sha256(raw).hexdigest()

validation={
    "version":VERSION,
    "baseVersion":"1.0.12",
    "payload":name,
    "payloadSha256":sha,
    "requirements":{
        "separateDropInFile":any(f["path"]=="BatchSplitDropIn.ps1" for f in files),
        "minimalMainHook":"Initialize-LibraryBatchSplitDropIn" in patcher and "BatchSplitDropIn.ps1" in patcher,
        "replacesButton":"LibraryDropInBatchButton" in dropin,
        "persistentPanelState":"$panel.Tag=$state" in dropin and "$pic.Tag=$state" in dropin and "$save.Tag=$state" in dropin,
        "selfContainedImageLoader":"function Open-LibraryDropInBitmap" in dropin,
        "selfContainedCropper":"function Save-LibraryDropInCrop" in dropin,
        "multiSelect":"$pick.Multiselect=$true" in dropin,
        "allInternalHashesVerified":all(hashlib.sha256(base64.b64decode(f["contentBase64"])).hexdigest()==f["sha256"] for f in files)
    }
}
if not all(validation["requirements"].values()):
    raise SystemExit(validation)

(TF/"batch-split-drop-in-1.0.13-validation.json").write_text(json.dumps(validation,indent=2),encoding="utf-8")
vd=ROOT/".library-v113-validation"
vd.mkdir(exist_ok=True)
for f in files:
    (vd/f["path"]).write_bytes(base64.b64decode(f["contentBase64"]))
print(json.dumps(validation,indent=2))
