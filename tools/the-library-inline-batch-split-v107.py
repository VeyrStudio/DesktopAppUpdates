from pathlib import Path
import base64, hashlib, json

ROOT = Path(__file__).resolve().parents[1]
TF = ROOT / "the-library"
VERSION = "1.0.7"

m=json.loads((TF/"manifest.json").read_text(encoding="utf-8"))
if m.get("version")!="1.0.6":
    raise SystemExit(f"Expected live base 1.0.6, got {m.get('version')}")

patcher=r"""$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$appRoot=Split-Path -Parent $PSScriptRoot
$backupDir=Join-Path $appRoot 'UpdateBackup'
$backupMain=Join-Path $backupDir 'CoverVault.ps1'
$backupVersion=Join-Path $backupDir 'AppVersion.json'
$targetMain=Join-Path $PSScriptRoot 'CoverVault.ps1'
$targetVersion=Join-Path $PSScriptRoot 'AppVersion.json'
$launcher=Join-Path $PSScriptRoot 'Launch Cover Vault.vbs'

function Relaunch-App {
    if(Test-Path -LiteralPath $launcher){
        Start-Process -FilePath 'wscript.exe' -ArgumentList ('"' + $launcher + '"')
    }
}

try {
    if(-not(Test-Path -LiteralPath $backupMain)){throw 'The updater backup is missing the previous Library app script.')}
    $text=[IO.File]::ReadAllText($backupMain,[Text.Encoding]::UTF8)

    # Remove the old v1.0.6 launch button so users cannot enter the separate-window flow.
    $oldBlockPattern='(?s)# BATCH SPLIT WRAPS v1\.0\.6.*?\$tabSplit\.Add_Resize\(\\{.*?\\}\)\s*'
    $text=[Text.RegularExpressions.Regex]::Replace($text,$oldBlockPatter,'')

    $marker='# INLINE BATCH SPLIT WRAPS v1.0.7'
    if(-not $text.Contains($marker)){
        foreach($needed in @('function Add-LibraryRecord','function Copy-Or-Move-IntoVault','$tabSplit')){
            if(-not $text.Contains($needed)i{throw "Could not find required Library feature: $needed"}
        }

        $feature=@'
# INLINE BATCH SPLIT WRAPS v1.0.7
$script:InlineBatchPanels = New-Object System.Collections.ArrayList

function New-InlineBatchLabel([string]$Text,[int]$X,[int]$Y,[int]$W=150){
    $l=New-Object Windows.Forms.Label
    $l.Text=$Text
    $l.AutoSize=$false
    $l.Size=New-Object Drawing.Size($W,20)
    $l.Location=New-Object Drawing.Point($X,$Y)
    $l.ForeColor=[Drawing.Color]::FromArgb(80,60,45)
    return $l
}

function New-InlineBatchTextBox([int]$X,[int]$Y,[int]$W){
    $t=New-Object Windows.Forms.TextBox
    $t.Location=New-Object Drawing.Point($X,$Y)
    $t.Size=New-Object Drawing.Size($W,24)
    return $t
}

function Get-InlineBatchDisplayRect($pic,$bitmap){
    if($null -eq $bitmap){return [Drawing.RectangleF]::Empty}
    $iw=[double]$bitmap.Width;$ih=[double]$bitmap.Height
    if($iw -le 0 -or $ih -le 0 -or $pic.ClientSize.Width -le 0 -or $pic.ClientSize.Height -le 0){return [Drawing.RectangleF]::Empty}
    $scale=[math]::Min($pic.ClientSize.Width/$iw,$pic.ClientSize.Height/$ih)
    $dw=$iw*$scale;$dh=$ih*$scale
    return New-Object Drawing.RectangleF(
        [single](($pic.ClientSize.Width-$dw)/2.0),
        [single](($pic.ClientSize.Height-$dh)/2.0),
        [single]$dw,[single]$dh
    )
}

function Save-InlineBatchCrop([Drawing.Bitmap]$source,[Drawing.Rectangle]$srcRect,[string]$dest){
    if($srcRect.Width -le 0 -or $srcRect.Height -le 0){throw 'A crop region has zero size.'}
    $out=New-Object Drawing.Bitmap($srcRect.Width,$srcRect.Height,[Drawing.Imaging.PixelFormat]::Format32bppArgb)
    try{
        $g=[Drawing.Graphics]::FromImage($out)
        try{
            $g.DrawImage($source,(New-Object Drawing.Rectangle(0,0,$out.Width,$out.Height)),$srcRect,[Drawing.GraphicsUnit]::Pixel)
        }finally{$g.Dispose()}
        $out.Save($dest,[Drawing.Imaging.ImageFormat]::Png)
    }finally{$out.Dispose()}
}

function Add-InlineBatchRecord($bitmap,[string]$sourcePath,[int]$left,[int]$right,[string]$project,[string]$ship,[string]$fandom,[string]$tags,[string]$coverType){
    if($left -lt 1 -or $right -gt ($bitmap.Width-1) -or $left -ge $right){throw 'The spine guides are not valid.'}

    $base=[IO.Path]::GetFileNameWithoutExtension($sourcePath)
    $tempDir=Join-Path ([IO.Path]::GetTempPath()) ('TheLibrary-Batch-'+[guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $tempDir -Force|Out-Null
    try{
        $pieces=@(
            [pscustomobject]@{Position='Back Cover';Name=($base+' - Back Cover.png');Rect=(New-Object Drawing.Rectangle(0,0,$left,$bitmap.Height))},
            [pscustomobject]@{Position='Spine';Name=($base+' - Spine.png');Rect=(New-Object Drawing.Rectangle($left,0,($right-$left),$bitmap.Height))},
            [pscustomobject]@{Position='Front Cover';Name=($base+' - Front Cover.png');Rect=(New-Object Drawing.Rectangle($right,0,($bitmap.Width-$right),$bitmap.Height)}
        )

        foreach($piece in $pieces){
            $tmp=Join-Path $tempDir $piece.Name
            Save-InlineBatchCrop $bitmap $piece.Rect $tmp
            $stored=Copy-Or-Move-IntoVault $tmp $false
            $script:PendingCoverType=$coverType
            Add-LibraryRecord `
                -OriginalName $piece.Name `
                -StoredName $stored `
                -Position $piece.Position `
                -Project $project `
                -Ship $ship `
                -Fandom $fandom `
                -Tags $tags | Out-Null
        }
    }finally{
        Remove-Item -LiteralPath $tempDir -Force -Recurse -ErrorAction SilentlyContinue
    }
}

function Add-InlineBatchSplitter([string]$path,[int]$ordinal,[int]$total){
    $fs=[IO.File]::Open($path,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::ReadWrite)
    try{
        $tmp=[Drawing.Image]::FromStream($fs)
        try{$bitmap=New-Object Drawing.Bitmap($tmp)}finally{$tmp.Dispose()}
    }finally{$fs.Dispose()}

    $panel=New-Object Windows.Forms.Panel
    $panel.Width=[math]::Max(760,$tabSplit.ClientSize.Width-40)
    $panel.Height=700
    $panel.BorderStyle='FixedSingle'
    $panel.BackColor=[Drawing.Color]::FromArgb(246,236,211)
    $panel.Margin=New-Object Windows.Forms.Padding(8)
    $panel.Tag=$bitmap

    $head=New-Object Windows.Forms.Label
    $head.Text=("COVER {0} OF {1}  -  {2}" -f $ordinal,$total,[IO.Path]::GetFileName($path))
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
    $leftNum.Minimum=1;$leftNum.Maximum=[math]::Max(1,$bitmap.Width-2)
    $leftNum.Value=[math]::Max(1,$center-$half)
    $leftNum.Location=New-Object Drawing.Point(14,438)
    $leftNum.Width=110
    $panel.Controls.Add((New-InlineBatchLabel 'BACK / SPINE EDGE' 14 416 150))
    $panel.Controls.Add($leftNum)

    $rightNum=New-Object Windows.Forms.NumericUpDown
    $rightNum.Minimum=2;$rightNum.Maximum=[math]::Max(2,$bitmap.Width-1)
    $rightNum.Value=[math]::Min($bitmap.Width-1,$center+$half)
    $rightNum.Location=New-Object Drawing.Point(150,438)
    $rightNum.Width=110
    $panel.Controls.Add((New-InlineBatchLabel 'SPINE / FRONT EDGE' 150 416 160))
    $panel.Controls.Add($rightNum)

    $panel.Controls.Add((New-InlineBatchLabel 'TITLE / BOOK' 510 52 180))
    $project=New-InlineBatchTextBox 510 74 235
    $panel.Controls.Add($project)

    $panel.Controls.Add((New-InlineBatchLabel 'SHIP' 510 112 180))
    $ship=New-InlineBatchTextBox 510 134 235
    $panel.Controls.Add($ship)

    $panel.Controls.Add((New-InlineBatchLabel 'FANDOM' 510 172 180))
    $fandom=New-InlineBatchTextBox 510 194 235
    $panel.Controls.Add($fandom)

    $panel.Controls.Add((New-InlineBatchLabel 'EXTRA TAGS' 510 232 180))
    $tags=New-InlineBatchTextBox 510 254 235
    $panel.Controls.Add($tags)

    $panel.Controls.Add((New-InlineBatchLabel 'COVER TYPE' 510 292 180))
    $coverType=New-InlineBatchTextBox 510 314 235
    $panel.Controls.Add($coverType)

    $status=New-Object Windows.Forms.Label
    $status.Text='NOT SAVED'
    $status.AutoSize=$true
    $status.Font=New-Object Drawing.Font('Segoe UI',9,[Drawing.FontStyle]::Bold)
    $status.ForeColor=[Drawing.Color]::FromArgc(120,70,40)
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

    $dragState=[pscustomobject]@{Which=''}
    $pic.Add_Paint({
        param($sender,$e)
        $rect=Get-InlineBatchDisplayRect $pic $bitmap
        if($rect.Width -le 0){return}
        $x1=[single]($rect.X+([int]$leftNum.Value/[double]$bitmap.Width)*$rect.Width)
        $x2=[single]($rect.X+([int]$rightNum.Value/[double]$bitmap.Width)*$rect.Width)
        $pen=New-Object Drawing.Pen([Drawing.Color]::FromArgb(240,196,80),3)
        try{
            $e.Graphics.DrawLine($pen,$x1,$rect.Y,$x1,$rect.Bottom)
            $e.Graphics.DrawLine($pen,$x2,$rect.Y,$x2,$rect.Bottom)
        }finally{$pen.Dispose()}
    })
    $leftNum.Add_ValueChanged({$pic.Invalidate()})
    $rightNum.Add_ValueChanged({$pic.Invalidate()})
    $pic.Add_MouseDown({
        param($sender,$e)
        $rect=Get-InlineBatchDisplayRect $pic $bitmap
        if($rect.Width -le 0){return}
        $x1=$rect.X+[[int]$leftNum.Value/[double]$bitmap.Width)*$rect.Width
        $x2=$rect.X+([int]$rightNum.Value/[double]$bitmap.Width)*$rect.Width
        if([math]::Abs($e.X-$x1) -le [math]::Abs($e.X-$x2)){
            if([math]::Abs($e.X-$x1) -le 16){$dragState.Which='Left'}
        }else{
            if([math]::Abs($e.X-$x2) -le 16){$dragState.Which='Right'}
        }
    })
    $pic.Add_MouseMove({
        param($sender,$e)
        if([string]::IsNullOrEmpty($dragState.Which)){return}
        $rect=Get-InlineBatchDisplayRect $pic $bitmap
        if($rect.Width -le 0){return}
        $px=[int][math]::Round((($e.X-$rect.X)/$rect.Width)*$bitmap.Width)
        $px=[math]::Max(1,[math]::Min($bitmap.Width-1,$px))
        if($dragState.Which -eq 'Left'){
            $px=[math]::Min($px,[int]$rightNum.Value-1)
            $leftNum.Value=[decimal][math]::Max([double]$leftNum.Minimum,[math]::Min(double]$leftNum.Maximum,$px))
        }else{
            $px=[math]::Max($px,[int]$leftNum.Value+1)
            $rightNum.Value=[decimal][math]::Max([double]$rightNum.Minimum,[math]::Min([double]$rightNum.Maximum,$px))
        }
    })
    $pic.Add_MouseUp({$dragState.Which=''})
    $pic.Add_MouseLeave({$dragState.Which=''})

    $save.Add_Click({
        try{
            $l=[int]$leftNum.Value;$r=[int]$rightNum.Value
            if($l -ge $r){throw 'The left spine edge must be before the right spine edge.'}
            Add-InlineBatchRecord `
                -bitmap $bitmap `
                -sourcePath $path `
                -left $l `
                -right $r `
                -project $project.Text `
                -ship $ship.Text `
                -fandom $fandom.Text `
                -tags $tags.Text `
                -coverType $coverType.Text

            Refresh-HierarchyTree
            Refresh-LibraryGrid
            $status.Text='SAVED TO LIBRARY'
            $status.ForeColor=[Drawing.Color]::FromArgb(35,120,65)
            $save.Enabled=$false
        }catch{
            [Windows.Forms.MessageBox]::Show(('Could not save this cover to The Library.'+[Environment]::NewLine+[Environment]::NewLine+$_.Exception.Message),'Batch Split')|Out-Null
        }
    })

    $remove.Add_Click({
        $pic.Image=$null
        if($null -ne $panel.Tag){
            try{$panel.Tag.Dispose()}catch{}
            $panel.Tag=$null
        }
        $panel.Parent.Controls.Remove($panel)
        $panel.Dispose()
    })

    [void]$script:InlineBatchPanels.Add($panel)
    return $panel
}

function Start-InlineBatchSplit {
    $pick=New-Object Windows.Forms.OpenFileDialog
    $pick.Title='Choose full-wrap covers'
    $pick.Filter='Image files|*.png;*.jpg;*.jpeg;*.bmp;*.tif;*.tiff|All files|*.*'
    $pick.Multiselect=$true
    if($pick.ShowDialog() -ne [Windows.Forms.DialogResult]::OK){return}

    $paths=@($pick.FileNames)
    if($paths.Count -eq 0){return}

    if($null -ne $script:InlineBatchHost){
        foreach($c in @($script:InlineBatchHost.Controls)){
            try{
                if($null -ne $c.Tag -and $c.Tag -is [Drawing.Image]){$c.Tag.Dispose()}
            }catch{}
        }
        $tabSplit.Controls.Remove($script:InlineBatchHost)
        $script:InlineBatchHost.Dispose()
        $script:InlineBatchHost=$null
    }

    $host=New-Object Windows.Forms.FlowLayoutPanel
    $host.Name='InlineBatchSplitHost'
    $host.FlowDirection='TopDown'
    $host.WrapContents=$false
    $host.AutoScroll=$true
    $host.Dock='Fill'
    $host.Padding=New-Object Windows.Forms.Padding(10,56,10,10)
    $host.BackColor=$tabSplit.BackColor
    $script:InlineBatchHost=$host
    $tabSplit.Controls.Add($host)
    $host.BringToFront()

    $n=0
    foreach($p in $paths){
        try{
            $n++
            $panel=Add-InlineBatchSplitter $p $n $paths.Count
            $host.Controls.Add($panel)
        }catch{
            $n--
        }
    }

    if($host.Controls.Count -eq 0){
        $tabSplit.Controls.Remove($host)
        $host.Dispose()
        $script:InlineBatchHost=$null
        [Windows.Forms.MessageBox]::Show('None of those files could be opened as cover images.','Batch Split')|Out-Null
    }
}

$btnInlineBatchSplit=New-Object Windows.Forms.Button
$btnInlineBatchSplit.Text='ADD MULTIPLE FULL WRAPS'
$btnInlineBatchSplit.Size=New-Object Drawing.Size(210,36)
$btnInlineBatchSplit.Location=New-Object Drawing.Point(12,12)
$btnInlineBatchSplit.Add_Click({Start-InlineBatchSplit})
$tabSplit.Controls.Add($btnInlineBatchSplit)
$btnInlineBatchSplit.BringToFront()
'@

        $patterns=@(
            '(?m)^\s*\[[void\]]\s*\$form\.ShowDialog\(\)\s*$',
            '(?m)^\s*\$form\.ShowDialog\(\)\s*\|\s*Out-Null\s*$',
            '(?m)^\s*\$form\.ShowDialog\(\)\s*$'
        )
        $match=$null
        foreach($pat in $patterns){
            $rx=New-Object Text.RegularExpressions.Regex($pat)
            $m=$rx.Match($text)
            if($m.Success){$match=$m;break}
        }
        if($null -eq $match){throw 'Could not find The Library window startup point.'}
        $text=$text.Substring(0,$match.Index)+$feature+[Environment]::NewLine+$text.Substring($match.Index)
    }

    [IO.File]::WriteAllText($targetMain,$text,(New-Object Text.UTF8Encoding($true)))
    @'
{
  "appId": "the-library",
  "appName": "The Library",
  "version": "1.0.7",
  "manifestUrl": "https://raw.githubusercontent.com/VeyrStudio/DesktopAppUpdates/main/the-library/manifest.json"
}
'@ | Set-Content -LiteralPath $targetVersion -Encoding UTF8

    Relaunch-App
}
catch{
    $message=$_.Exception.Message
    try{if(Test-Path -LiteralPath $backupMain){Copy-Item -LiteralPath $backupMain -Destination $targetMain -Force}}catch{}
    try{if(Test-Path -LiteralPath $backupVersion){Copy-Item -LiteralPath $backupVersion -Destination $targetVersion -Force}}catch{}
    try{[Windows.Forms.MessageBox]::Show(('The Library could not install the inline batch-split fix.'+[Environment]::NewLine+[Environment]::NewLine+$message+[Environment]::NewLine+[Environment]::NewLine+'The previous app version was restored.'),'The Library Update')|Out-Null}catch{}
    Relaunch-App
}
"""

appver=json.dumps({
    "appId":"the-library","appName":"The Library","version":VERSION,
    "manifestUrl":"https://raw.githubusercontent.com/VeyrStudio/DesktopAppUpdates/main/the-library/manifest.json"
},indent=2).encode()

files=[]
for path,data in [
    ("CoverVault.ps1",patcher.encode("utf-8-sig")),
    ("AppVersion.json",appver),
]:
    files.append({"path":path,"sha256":hashlib.sha256(data).hexdigest(),"contentBase64":base64.b64encode(data).decode("ascii")})

payload={"schemaVersion":1,"appId":"the-library","appName":"The Library","version":VERSION,"files":files,"delete":[]}
raw=json.dumps(payload,separators=(",",":")).encode()
name="payload-1.0.7-inline-batch-split.txt"
(TF/name).write_bytes(raw)
sha=hashlib.sha256(raw).hexdigest()

validation={
    "version":VERSION,"baseVersion":"1.0.6","payload":name,"payloadSha256":sha,
    "requirements":{
        "removesSeparateWindowFlow":"oldBlockPatter" in patcher,
        "sameSplitTab":"$tabSplit.Controls.Add($host)" in patcher,
        "multipleWrapSelection":"$pick.Multiselect=$true" in patcher,
        "perCoverBookField":"TITLE / BOOK" in patcher,
        "perCoverShipField":"SHIP" in patcher,
        "perCoverFandomField":"FANDOM" in patcher,
        "perCoverTagsField":"EXTRA TAGS" in patcher,
        "perCoverTypeField":"COVER TYPE" in patcher,
        "perCoverSave":"SAVE THIS COVER TO LIBRARY" in patcher,
        "savesToLibrary":"Add-LibraryRecord" in patcher and "Copy-Or-Move-IntoVault" in patcher,
        "threePartLibrarySave":all(x in patcher for x in ["Back Cover","Spine","Front Cover"]),
        "noFolderExport":"FolderBrowserDialog" not in patcher,
        "noApplyToAll":"APPLY TO ALL" not in patcher.upper(),
        "allInternalHashesVerified":all(hashlib.sha256(base64.b64decode(f["contentBase64"])).hexdigest()==f["sha256"] for f in files)
    }
}
if not all(validation["requirements"].values()):
    raise SystemExit(validation)

(TF/"inline-batch-split-1.0.7-validation.json").write_text(json.dumps(validation,indent=2),encoding="utf-8")
vd=ROOT/".library-v107-validation"
vd.mkdir(exist_ok=True)
(vd/"CoverVault.ps1").write_bytes(base64.b64decode(files[0]["contentBase64"]))
print(json.dumps(validation,indent=2))
