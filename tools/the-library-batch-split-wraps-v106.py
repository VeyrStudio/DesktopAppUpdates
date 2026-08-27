from pathlib import Path
import base64, hashlib, json

ROOT = Path(__file__).resolve().parents[1]
TF = ROOT / "the-library"
VERSION = "1.0.6"

m = json.loads((TF / "manifest.json").read_text(encoding="utf-8"))
if m.get("version") != "1.0.5":
    raise SystemExit(f"Expected live base 1.0.5, got {m.get('version')}")

patcher = r"""$ErrorActionPreference='Stop'
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
    if(-not(Test-Path -LiteralPath $backupMain)){ throw 'The updater backup is missing the previous Library app script.' }
    $text=[IO.File]::ReadAllText($backupMain,[Text.Encoding]::UTF8)

    $marker='# BATCH SPLIT WRAPS v1.0.6'
    if(-not $text.Contains($marker)){
        if(-not $text.Contains('$tabSplit')){ throw 'Could not find The Library Split tab.' }

        $feature=@'
# BATCH SPLIT WRAPS v1.0.6
function Open-BatchSplitWraps {
    $pick = New-Object System.Windows.Forms.OpenFileDialog
    $pick.Title = 'Choose full-wrap covers'
    $pick.Filter = 'Image files|*.png;*.jpg;*.jpeg;*.bmp;*.tif;*.tiff|All files|*.*'
    $pick.Multiselect = $true
    if($pick.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK){ return }

    $paths = @($pick.FileNames)
    if($paths.Count -eq 0){ return }

    $items = New-Object System.Collections.ArrayList
    foreach($p in $paths){
        try {
            $fs=[IO.File]::Open($p,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::ReadWrite)
            try {
                $img=[Drawing.Image]::FromStream($fs)
                $w=[int]$img.Width
                $h=[int]$img.Height
            } finally {
                if($img){$img.Dispose()}
                $fs.Dispose()
            }
            if($w -lt 3 -or $h -lt 1){ continue }
            $center=[int]([math]::Round($w/2.0))
            $half=[int]([math]::Max(2,[math]::Round($w*0.04)))
            $left=[int][math]::Max(1,$center-$half)
            $right=[int][math]::Min($w-1,$center+$half)
            [void]$items.Add([pscustomobject]@{
                Path=$p; Width=$w; Height=$h; Left=$left; Right=$right;
                Ready=$false; Skipped=$false
            })
        } catch {}
    }

    if($items.Count -eq 0){
        [Windows.Forms.MessageBox]::Show('None of the selected files could be opened as images.','Batch Split Wraps')|Out-Null
        return
    }

    $script:BatchSplitIndex=0
    $script:BatchSplitBitmap=$null
    $script:BatchSplitDragging=''
    $script:BatchSplitLoading=$false

    $win=New-Object Windows.Forms.Form
    $win.Text='The Library - Batch Split Wraps'
    $win.StartPosition='CenterParent'
    $win.Size=New-Object Drawing.Size(1120,760)
    $win.MinimumSize=New-Object Drawing.Size(820,600)
    $win.BackColor=[Drawing.Color]::FromArgb(28,23,20)

    $queuePanel=New-Object Windows.Forms.Panel
    $queuePanel.Dock='Left'
    $queuePanel.Width=255
    $queuePanel.Padding=New-Object Windows.Forms.Padding(10)
    $queuePanel.BackColor=[Drawing.Color]::FromArgb(37,30,26)
    $win.Controls.Add($queuePanel)

    $queueTitle=New-Object Windows.Forms.Label
    $queueTitle.Text='WRAP QUEUE'
    $queueTitle.AutoSize=$true
    $queueTitle.ForeColor=[Drawing.Color]::FromArgb(230,210,171)
    $queueTitle.Font=New-Object Drawing.Font('Segoe UI',11,[Drawing.FontStyle]::Bold)
    $queueTitle.Location=New-Object Drawing.Point(10,10)
    $queuePanel.Controls.Add($queueTitle)

    $queue=New-Object Windows.Forms.ListBox
    $queue.Location=New-Object Drawing.Point(10,40)
    $queue.Size=New-Object Drawing.Size(230,570)
    $queue.Anchor='Top,Bottom,Left,Right'
    $queue.BackColor=[Drawing.Color]::FromArgb(246,236,211)
    $queue.ForeColor=[Drawing.Color]::FromArgb(40,32,27)
    $queuePanel.Controls.Add($queue)

    $removeBtn=New-Object Windows.Forms.Button
    $removeBtn.Text='REMOVE'
    $removeBtn.Size=New-Object Drawing.Size(108,34)
    $removeBtn.Location=New-Object Drawing.Point(10,620)
    $removeBtn.Anchor='Bottom,Left'
    $queuePanel.Controls.Add($removeBtn)

    $skipBtn=New-Object Windows.Forms.Button
    $skipBtn.Text='SKIP / UNSKIP'
    $skipBtn.Size=New-Object Drawing.Size(112,34)
    $skipBtn.Location=New-Object Drawing.Point(128,620)
    $skipBtn.Anchor='Bottom,Left'
    $queuePanel.Controls.Add($skipBtn)

    $main=New-Object Windows.Forms.Panel
    $main.Dock='Fill'
    $main.Padding=New-Object Windows.Forms.Padding(12)
    $win.Controls.Add($main)

    $status=New-Object Windows.Forms.Label
    $status.AutoSize=$true
    $status.ForeColor=[Drawing.Color]::FromArgb(240,225,195)
    $status.Font=New-Object Drawing.Font('Segoe UI',10,[Drawing.FontStyle]::Bold)
    $status.Location=New-Object Drawing.Point(14,12)
    $main.Controls.Add($status)

    $pic=New-Object Windows.Forms.PictureBox
    $pic.Location=New-Object Drawing.Point(14,44)
    $pic.Size=New-Object Drawing.Size(800,500)
    $pic.Anchor='Top,Bottom,Left,Right'
    $pic.BackColor=[Drawing.Color]::FromArgb(18,16,14)
    $pic.SizeMode='Zoom'
    $main.Controls.Add($pic)

    $leftLabel=New-Object Windows.Forms.Label
    $leftLabel.Text='LEFT SPINE EDGE'
    $leftLabel.AutoSize=$true
    $leftLabel.ForeColor=[Drawing.Color]::FromArgb(230,210,171)
    $leftLabel.Anchor='Bottom,Left'
    $leftLabel.Location=New-Object Drawing.Point(14,558)
    $main.Controls.Add($leftLabel)

    $leftNum=New-Object Windows.Forms.NumericUpDown
    $leftNum.Minimum=1
    $leftNum.Maximum=999999
    $leftNum.Width=110
    $leftNum.Anchor='Bottom,Left'
    $leftNum.Location=New-Object Drawing.Point(14,580)
    $main.Controls.Add($leftNum)

    $rightLabel=New-Object Windows.Forms.Label
    $rightLabel.Text='RIGHT SPINE EDGE'
    $rightLabel.AutoSize=$true
    $rightLabel.ForeColor=[Drawing.Color]::FromArgb(230,210,171)
    $rightLabel.Anchor='Bottom,Left'
    $rightLabel.Location=New-Object Drawing.Point(142,558)
    $main.Controls.Add($rightLabel)

    $rightNum=New-Object Windows.Forms.NumericUpDown
    $rightNum.Minimum=2
    $rightNum.Maximum=999999
    $rightNum.Width=110
    $rightNum.Anchor='Bottom,Left'
    $rightNum.Location=New-Object Drawing.Point(142,580)
    $main.Controls.Add($rightNum)

    $prevBtn=New-Object Windows.Forms.Button
    $prevBtn.Text='< PREVIOUS'
    $prevBtn.Size=New-Object Drawing.Size(120,38)
    $prevBtn.Anchor='Bottom,Left'
    $prevBtn.Location=New-Object Drawing.Point(275,576)
    $main.Controls.Add($prevBtn)

    $nextBtn=New-Object Windows.Forms.Button
    $nextBtn.Text='NEXT >'
    $nextBtn.Size=New-Object Drawing.Size(120,38)
    $nextBtn.Anchor='Bottom,Left'
    $nextBtn.Location=New-Object Drawing.Point(405,576)
    $main.Controls.Add($nextBtn)

    $saveBtn=New-Object Windows.Forms.Button
    $saveBtn.Text='SAVE ALL READY'
    $saveBtn.Size=New-Object Drawing.Size(170,38)
    $saveBtn.Anchor='Bottom,Right'
    $saveBtn.Location=New-Object Drawing.Point(650,576)
    $main.Controls.Add($saveBtn)

    function Get-BatchDisplayRect {
        if($null -eq $script:BatchSplitBitmap){ return [Drawing.RectangleF]::Empty }
        $iw=[double]$script:BatchSplitBitmap.Width
        $ih=[double]$script:BatchSplitBitmap.Height
        if($iw -le 0 -or $ih -le 0 -or $pic.ClientSize.Width -le 0 -or $pic.ClientSize.Height -le 0){ return [Drawing.RectangleF]::Empty }
        $scale=[math]::Min($pic.ClientSize.Width/$iw,$pic.ClientSize.Height/$ih)
        $dw=$iw*$scale; $dh=$ih*$scale
        $x=($pic.ClientSize.Width-$dw)/2.0
        $y=($pic.ClientSize.Height-$dh)/2.0
        return New-Object Drawing.RectangleF([single]$x,[single]$y,[single]$dw,[single]$dh)
    }

    function Update-BatchQueue {
        $sel=$script:BatchSplitIndex
        $queue.BeginUpdate()
        try {
            $queue.Items.Clear()
            for($i=0;$i -lt $items.Count;$i++){
                $it=$items[$i]
                $state=if($it.Skipped){'[SKIP]'}elseif($it.Ready){'[READY]'}else{'[ ]'}
                [void]$queue.Items.Add(("{0} {1}" -f $state,[IO.Path]::GetFileName($it.Path)))
            }
            if($items.Count -gt 0 -and $sel -ge 0 -and $sel -lt $items.Count){$queue.SelectedIndex=$sel}
        } finally {$queue.EndUpdate()}
    }

    function Load-BatchItem([int]$index){
        if($items.Count -eq 0){ return }
        if($index -lt 0){$index=0}
        if($index -ge $items.Count){$index=$items.Count-1}
        $script:BatchSplitIndex=$index
        $it=$items[$index]

        if($null -ne $script:BatchSplitBitmap){
            $pic.Image=$null
            $script:BatchSplitBitmap.Dispose()
            $script:BatchSplitBitmap=$null
        }

        $fs=[IO.File]::Open($it.Path,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::ReadWrite)
        try {
            $tmp=[Drawing.Image]::FromStream($fs)
            try {$script:BatchSplitBitmap=New-Object Drawing.Bitmap($tmp)} finally {$tmp.Dispose()}
        } finally {$fs.Dispose()}
        $pic.Image=$script:BatchSplitBitmap

        $script:BatchSplitLoading=$true
        try {
            $leftNum.Maximum=[decimal]([math]::Max(1,$it.Width-2))
            $rightNum.Maximum=[decimal]([math]::Max(2,$it.Width-1))
            $leftNum.Value=[decimal][math]::Min([double]$leftNum.Maximum,[math]::Max(1,$it.Left))
            $rightNum.Value=[decimal][math]::Min([double]$rightNum.Maximum,[math]::Max(2,$it.Right))
        } finally {$script:BatchSplitLoading=$false}

        $status.Text=("{0} of {1}  -  {2}" -f ($index+1),$items.Count,[IO.Path]::GetFileName($it.Path))
        if($it.Skipped){$status.Text += '  [SKIPPED]'}elseif($it.Ready){$status.Text += '  [READY]'}
        Update-BatchQueue
        $pic.Invalidate()
    }

    function Commit-BatchGuides([bool]$markReady){
        if($items.Count -eq 0){return $false}
        $it=$items[$script:BatchSplitIndex]
        $l=[int]$leftNum.Value
        $r=[int]$rightNum.Value
        if($l -lt 1 -or $r -gt ($it.Width-1) -or $l -ge $r){
            [Windows.Forms.MessageBox]::Show('The left spine edge must be to the left of the right spine edge.','Batch Split Wraps')|Out-Null
            return $false
        }
        $it.Left=$l; $it.Right=$r
        if($markReady -and -not $it.Skipped){$it.Ready=$true}
        Update-BatchQueue
        return $true
    }

    $leftNum.Add_ValueChanged({
        if($script:BatchSplitLoading -or $items.Count -eq 0){return}
        $items[$script:BatchSplitIndex].Left=[int]$leftNum.Value
        $items[$script:BatchSplitIndex].Ready=$false
        Update-BatchQueue
        $pic.Invalidate()
    })
    $rightNum.Add_ValueChanged({
        if($script:BatchSplitLoading -or $items.Count -eq 0){return}
        $items[$script:BatchSplitIndex].Right=[int]$rightNum.Value
        $items[$script:BatchSplitIndex].Ready=$false
        Update-BatchQueue
        $pic.Invalidate()
    })

    $pic.Add_Paint({
        param($sender,$e)
        if($items.Count -eq 0 -or $null -eq $script:BatchSplitBitmap){return}
        $rect=Get-BatchDisplayRect
        if($rect.Width -le 0){return}
        $it=$items[$script:BatchSplitIndex]
        $x1=[single]($rect.X + ($it.Left/[double]$it.Width)*$rect.Width)
        $x2=[single]($rect.X + ($it.Right/[double]$it.Width)*$rect.Width)
        $pen1=New-Object Drawing.Pen([Drawing.Color]::FromArgb(240,196,80),3)
        $pen2=New-Object Drawing.Pen([Drawing.Color]::FromArgb(240,196,80),3)
        try {
            $e.Graphics.DrawLine($pen1,$x1,$rect.Y,$x1,$rect.Bottom)
            $e.Graphics.DrawLine($pen2,$x2,$rect.Y,$x2,$rect.Bottom)
        } finally {$pen1.Dispose();$pen2.Dispose()}
    })

    $pic.Add_MouseDown({
        param($sender,$e)
        if($items.Count -eq 0){return}
        $rect=Get-BatchDisplayRect
        if($rect.Width -le 0 -or $e.X -lt $rect.X -or $e.X -gt $rect.Right){return}
        $it=$items[$script:BatchSplitIndex]
        $x1=$rect.X + ($it.Left/[double]$it.Width)*$rect.Width
        $x2=$rect.X + ($it.Right/[double]$it.Width)*$rect.Width
        if([math]::Abs($e.X-$x1) -le [math]::Abs($e.X-$x2)){
            if([math]::Abs($e.X-$x1) -le 16){$script:BatchSplitDragging='Left'}
        } else {
            if([math]::Abs($e.X-$x2) -le 16){$script:BatchSplitDragging='Right'}
        }
    })
    $pic.Add_MouseMove({
        param($sender,$e)
        if([string]::IsNullOrEmpty($script:BatchSplitDragging) -or $items.Count -eq 0){return}
        $rect=Get-BatchDisplayRect
        if($rect.Width -le 0){return}
        $it=$items[$script:BatchSplitIndex]
        $px=[int][math]::Round((($e.X-$rect.X)/$rect.Width)*$it.Width)
        $px=[math]::Max(1,[math]::Min($it.Width-1,$px))
        if($script:BatchSplitDragging -eq 'Left'){
            $px=[math]::Min($px,$it.Right-1)
            $leftNum.Value=[decimal][math]::Max([double]$leftNum.Minimum,[math]::Min([double]$leftNum.Maximum,$px))
        } else {
            $px=[math]::Max($px,$it.Left+1)
            $rightNum.Value=[decimal][math]::Max([double]$rightNum.Minimum,[math]::Min([double]$rightNum.Maximum,$px))
        }
    })
    $pic.Add_MouseUp({$script:BatchSplitDragging=''})
    $pic.Add_MouseLeave({$script:BatchSplitDragging=''})

    $prevBtn.Add_Click({
        if($items.Count -eq 0){return}
        [void](Commit-BatchGuides $false)
        if($script:BatchSplitIndex -gt 0){Load-BatchItem ($script:BatchSplitIndex-1)}
    })
    $nextBtn.Add_Click({
        if($items.Count -eq 0){return}
        if(-not (Commit-BatchGuides $true)){return}
        if($script:BatchSplitIndex -lt ($items.Count-1)){Load-BatchItem ($script:BatchSplitIndex+1)}
        else {
            [Windows.Forms.MessageBox]::Show('That was the last cover. Use SAVE ALL READY when you are finished.','Batch Split Wraps')|Out-Null
            Load-BatchItem $script:BatchSplitIndex
        }
    })
    $skipBtn.Add_Click({
        if($items.Count -eq 0){return}
        $it=$items[$script:BatchSplitIndex]
        $it.Skipped=-not $it.Skipped
        if($it.Skipped){$it.Ready=$false}
        Update-BatchQueue
        Load-BatchItem $script:BatchSplitIndex
    })
    $removeBtn.Add_Click({
        if($items.Count -eq 0){return}
        if($null -ne $script:BatchSplitBitmap){$pic.Image=$null;$script:BatchSplitBitmap.Dispose();$script:BatchSplitBitmap=$null}
        $items.RemoveAt($script:BatchSplitIndex)
        if($items.Count -eq 0){$win.Close();return}
        if($script:BatchSplitIndex -ge $items.Count){$script:BatchSplitIndex=$items.Count-1}
        Load-BatchItem $script:BatchSplitIndex
    })
    $queue.Add_SelectedIndexChanged({
        if($script:BatchSplitLoading){return}
        if($queue.SelectedIndex -ge 0 -and $queue.SelectedIndex -lt $items.Count -and $queue.SelectedIndex -ne $script:BatchSplitIndex){
            [void](Commit-BatchGuides $false)
            Load-BatchItem $queue.SelectedIndex
        }
    })

    function Save-BatchCrop([Drawing.Bitmap]$source,[Drawing.Rectangle]$srcRect,[string]$dest){
        if($srcRect.Width -le 0 -or $srcRect.Height -le 0){throw 'A crop region has zero size.'}
        $out=New-Object Drawing.Bitmap($srcRect.Width,$srcRect.Height,[Drawing.Imaging.PixelFormat]::Format32bppArgb)
        try {
            $g=[Drawing.Graphics]::FromImage($out)
            try {
                $g.DrawImage($source,(New-Object Drawing.Rectangle(0,0,$out.Width,$out.Height)),$srcRect,[Drawing.GraphicsUnit]::Pixel)
            } finally {$g.Dispose()}
            $out.Save($dest,[Drawing.Imaging.ImageFormat]::Png)
        } finally {$out.Dispose()}
    }

    $saveBtn.Add_Click({
        if($items.Count -eq 0){return}
        [void](Commit-BatchGuides $false)
        $ready=@($items | Where-Object {$_.Ready -and -not $_.Skipped})
        if($ready.Count -eq 0){
            [Windows.Forms.MessageBox]::Show('No covers are marked READY yet. Click NEXT after adjusting a cover to mark it ready.','Batch Split Wraps')|Out-Null
            return
        }
        $folder=New-Object Windows.Forms.FolderBrowserDialog
        $folder.Description='Choose where to save all finished cover splits'
        if($folder.ShowDialog() -ne [Windows.Forms.DialogResult]::OK){return}

        $saved=0
        $errors=New-Object Collections.Generic.List[string]
        foreach($it in $ready){
            try {
                $fs=[IO.File]::Open($it.Path,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::ReadWrite)
                try {
                    $tmp=[Drawing.Image]::FromStream($fs)
                    try {$bmp=New-Object Drawing.Bitmap($tmp)} finally {$tmp.Dispose()}
                } finally {$fs.Dispose()}

                try {
                    if($it.Left -lt 1 -or $it.Right -gt ($bmp.Width-1) -or $it.Left -ge $it.Right){throw 'Invalid spine guide positions.'}
                    $base=[IO.Path]::GetFileNameWithoutExtension($it.Path)
                    $safe=$base -replace '[\\/:*?"<>|]','_'
                    $destDir=Join-Path $folder.SelectedPath $safe
                    New-Item -ItemType Directory -Force -Path $destDir|Out-Null
                    Save-BatchCrop $bmp (New-Object Drawing.Rectangle(0,0,$it.Left,$bmp.Height)) (Join-Path $destDir 'Back.png')
                    Save-BatchCrop $bmp (New-Object Drawing.Rectangle($it.Left,0,($it.Right-$it.Left),$bmp.Height)) (Join-Path $destDir 'Spine.png')
                    Save-BatchCrop $bmp (New-Object Drawing.Rectangle($it.Right,0,($bmp.Width-$it.Right),$bmp.Height)) (Join-Path $destDir 'Front.png')
                    $saved++
                } finally {$bmp.Dispose()}
            } catch {
                $errors.Add(([IO.Path]::GetFileName($it.Path)+': '+$_.Exception.Message))
            }
        }

        $msg="Saved $saved cover split"
        if($saved -ne 1){$msg+='s'}
        $msg+='.'
        if($errors.Count -gt 0){
            $msg += [Environment]::NewLine+[Environment]::NewLine+"Could not save: $($errors.Count)"
            $msg += [Environment]::NewLine+(@($errors|Select-Object -First 5)-join [Environment]::NewLine)
        }
        [Windows.Forms.MessageBox]::Show($msg,'Batch Split Wraps')|Out-Null
    })

    $win.Add_FormClosed({
        if($null -ne $script:BatchSplitBitmap){
            $pic.Image=$null
            $script:BatchSplitBitmap.Dispose()
            $script:BatchSplitBitmap=$null
        }
    })

    Load-BatchItem 0
    [void]$win.ShowDialog($form)
}

$btnBatchSplitWraps=New-Object Windows.Forms.Button
$btnBatchSplitWraps.Text='BATCH SPLIT WRAPS'
$btnBatchSplitWraps.Size=New-Object Drawing.Size(185,36)
$btnBatchSplitWraps.Anchor='Top,Right'
$btnBatchSplitWraps.Location=New-Object Drawing.Point([math]::Max(10,$tabSplit.ClientSize.Width-205),12)
$btnBatchSplitWraps.Add_Click({Open-BatchSplitWraps})
$tabSplit.Controls.Add($btnBatchSplitWraps)
$btnBatchSplitWraps.BringToFront()
$tabSplit.Add_Resize({
    try{$btnBatchSplitWraps.Location=New-Object Drawing.Point([math]::Max(10,$tabSplit.ClientSize.Width-205),12)}catch{}
})
'@

        $patterns=@(
            '(?m)^\s*\[void\]\s*\$form\.ShowDialog\(\)\s*$',
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
  "version": "1.0.6",
  "manifestUrl": "https://raw.githubusercontent.com/VeyrStudio/DesktopAppUpdates/main/the-library/manifest.json"
}
'@ | Set-Content -LiteralPath $targetVersion -Encoding UTF8

    Relaunch-App
}
catch {
    $message=$_.Exception.Message
    try{if(Test-Path -LiteralPath $backupMain){Copy-Item -LiteralPath $backupMain -Destination $targetMain -Force}}catch{}
    try{if(Test-Path -LiteralPath $backupVersion){Copy-Item -LiteralPath $backupVersion -Destination $targetVersion -Force}}catch{}
    try{
        [Windows.Forms.MessageBox]::Show(
            ('The Library could not install the Batch Split Wraps update.'+[Environment]::NewLine+[Environment]::NewLine+$message+[Environment]::NewLine+[Environment]::NewLine+'The previous app version was restored.'),
            'The Library Update'
        )|Out-Null
    }catch{}
    Relaunch-App
}
"""

appver = json.dumps({
    "appId":"the-library",
    "appName":"The Library",
    "version":VERSION,
    "manifestUrl":"https://raw.githubusercontent.com/VeyrStudio/DesktopAppUpdates/main/the-library/manifest.json"
}, indent=2).encode()

files=[]
for path,data in [
    ("CoverVault.ps1",patcher.encode("utf-8-sig")),
    ("AppVersion.json",appver),
]:
    files.append({
        "path":path,
        "sha256":hashlib.sha256(data).hexdigest(),
        "contentBase64":base64.b64encode(data).decode("ascii")
    })

payload={"schemaVersion":1,"appId":"the-library","appName":"The Library","version":VERSION,"files":files,"delete":[]}
raw=json.dumps(payload,separators=(",",":")).encode()
name="payload-1.0.6-batch-split-wraps.txt"
(TF/name).write_bytes(raw)
sha=hashlib.sha256(raw).hexdigest()

validation={
    "version":VERSION,
    "baseVersion":"1.0.5",
    "payload":name,
    "payloadSha256":sha,
    "requirements":{
        "batchSplitButtonPresent":"BATCH SPLIT WRAPS" in patcher,
        "multipleWrapSelection":"$pick.Multiselect = $true" in patcher,
        "perCoverGuideStorage":"Left=$left; Right=$right" in patcher,
        "previousNextQueue":"NEXT >" in patcher and "< PREVIOUS" in patcher,
        "dragGuides":"BatchSplitDragging" in patcher,
        "noApplyToAll":"APPLY TO ALL" not in patcher.upper(),
        "skipAndRemove":"SKIP / UNSKIP" in patcher and "REMOVE" in patcher,
        "saveAllReady":"SAVE ALL READY" in patcher,
        "threePartOutput":all(x in patcher for x in ["'Back.png'","'Spine.png'","'Front.png'"]),
        "rollbackPreserved":"The previous app version was restored." in patcher,
        "allInternalHashesVerified":all(hashlib.sha256(base64.b64decode(f["contentBase64"])).hexdigest()==f["sha256"] for f in files)
    }
}
if not all(validation["requirements"].values()):
    raise SystemExit(validation)

(TF/"batch-split-wraps-1.0.6-validation.json").write_text(json.dumps(validation,indent=2),encoding="utf-8")
vd=ROOT/".library-v106-validation"
vd.mkdir(exist_ok=True)
(vd/"CoverVault.ps1").write_bytes(base64.b64decode(files[0]["contentBase64"]))
print(json.dumps(validation,indent=2))
