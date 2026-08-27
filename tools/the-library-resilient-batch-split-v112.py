from pathlib import Path
import base64, hashlib, json

ROOT = Path(__file__).resolve().parents[1]
TF = ROOT / "the-library"
VERSION = "1.0.12"

m = json.loads((TF / "manifest.json").read_text(encoding="utf-8"))
if m.get("version") != "1.0.11":
    raise SystemExit(f"Expected live base 1.0.11, got {m.get('version')}")

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
    if(-not(Test-Path -LiteralPath $backupMain)){throw 'The updater backup is missing the previous Library app script.'}
    $text=[IO.File]::ReadAllText($backupMain,[Text.Encoding]::UTF8)

    if(-not $text.Contains('function Add-InlineBatchSplitter')){throw 'Could not find the multi-wrap splitter feature in this Library build.'}
    if(-not $text.Contains('function Start-InlineBatchSplit')){throw 'Could not find the multi-wrap splitter start function in this Library build.'}

    if(-not $text.Contains('function Load-InlineBatchImageSafe')){
        $helper=@'
# ROBUST BATCH IMAGE LOADER v1.0.12
function Load-InlineBatchImageSafe([string]$Path){
    if([string]::IsNullOrWhiteSpace($Path)){throw 'Image path is empty.'}
    if(-not(Test-Path -LiteralPath $Path -PathType Leaf)){throw ('Image file was not found: '+$Path)}

    $bytes=$null
    $stream=$null
    $image=$null
    $copy=$null
    $graphics=$null
    try{
        $bytes=[IO.File]::ReadAllBytes($Path)
        if($null -eq $bytes -or $bytes.Length -eq 0){throw 'Image file is empty.'}

        $stream=New-Object IO.MemoryStream(,$bytes)
        $image=[Drawing.Image]::FromStream($stream,$true,$true)
        if($null -eq $image){throw 'Windows could not decode the image.'}
        if($image.Width -le 0 -or $image.Height -le 0){throw 'The image has invalid dimensions.'}

        $copy=New-Object Drawing.Bitmap($image.Width,$image.Height,[Drawing.Imaging.PixelFormat]::Format32bppArgb)
        $graphics=[Drawing.Graphics]::FromImage($copy)
        if($null -eq $graphics){throw 'Windows could not create the image drawing surface.'}

        $destRect=New-Object Drawing.Rectangle(0,0,$copy.Width,$copy.Height)
        $graphics.DrawImage($image,$destRect,0,0,$image.Width,$image.Height,[Drawing.GraphicsUnit]::Pixel)
        return $copy
    }
    catch{
        if($null -ne $copy){try{$copy.Dispose()}catch{}}
        throw
    }
    finally{
        if($null -ne $graphics){try{$graphics.Dispose()}catch{}}
        if($null -ne $image){try{$image.Dispose()}catch{}}
        if($null -ne $stream){try{$stream.Dispose()}catch{}}
    }
}

'@
        $text=$text.Replace('function Add-InlineBatchSplitter',$helper+'function Add-InlineBatchSplitter')
    }

    $start=$text.IndexOf('function Add-InlineBatchSplitter')
    $finish=$text.IndexOf('function Start-InlineBatchSplit',$start)
    if($start -lt 0 -or $finish -le $start){throw 'Could not isolate the multi-wrap splitter function.'}

    $replacement=@'
# PERSISTENT BATCH PANEL STATE v1.0.12
function Add-InlineBatchSplitter([string]$path,[int]$ordinal,[int]$total){
    $bitmap=$null
    try{
        $bitmap=Load-InlineBatchImageSafe $path
    }catch{
        throw ("Could not open image: " + [IO.Path]::GetFileName($path) + " - " + $_.Exception.Message)
    }
    if($null -eq $bitmap){throw ("Could not open image: " + [IO.Path]::GetFileName($path))}

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
    $leftNum.Minimum=1
    $leftNum.Maximum=[math]::Max(1,$bitmap.Width-2)
    $leftNum.Value=[math]::Max(1,$center-$half)
    $leftNum.Location=New-Object Drawing.Point(14,438)
    $leftNum.Width=110
    $panel.Controls.Add((New-InlineBatchLabel 'BACK / SPINE EDGE' 14 416 150))
    $panel.Controls.Add($leftNum)

    $rightNum=New-Object Windows.Forms.NumericUpDown
    $rightNum.Minimum=2
    $rightNum.Maximum=[math]::Max(2,$bitmap.Width-1)
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
        Path=$path
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

    $pic.Tag=$state
    $leftNum.Tag=$state
    $rightNum.Tag=$state
    $save.Tag=$state
    $remove.Tag=$state

    $pic.Add_Paint({
        param($sender,$e)
        $st=$sender.Tag
        if($null -eq $st -or $null -eq $st.Bitmap -or $null -eq $st.LeftNum -or $null -eq $st.RightNum){return}
        $rect=Get-InlineBatchDisplayRect $sender $st.Bitmap
        if($rect.Width -le 0){return}
        $x1=[single]($rect.X+([int]$st.LeftNum.Value/[double]$st.Bitmap.Width)*$rect.Width)
        $x2=[single]($rect.X+([int]$st.RightNum.Value/[double]$st.Bitmap.Width)*$rect.Width)
        $pen=New-Object Drawing.Pen([Drawing.Color]::FromArgb(240,196,80),3)
        try{
            $e.Graphics.DrawLine($pen,$x1,$rect.Y,$x1,$rect.Bottom)
            $e.Graphics.DrawLine($pen,$x2,$rect.Y,$x2,$rect.Bottom)
        }finally{
            if($null -ne $pen){$pen.Dispose()}
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
        if($null -eq $st -or $null -eq $st.Bitmap -or $null -eq $st.LeftNum -or $null -eq $st.RightNum){return}
        $rect=Get-InlineBatchDisplayRect $sender $st.Bitmap
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
        if($null -eq $st -or $null -eq $st.Bitmap -or $null -eq $st.LeftNum -or $null -eq $st.RightNum -or $null -eq $st.DragState){return}
        if([string]::IsNullOrEmpty([string]$st.DragState.Which)){return}
        $rect=Get-InlineBatchDisplayRect $sender $st.Bitmap
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
            if($null -eq $st){throw 'This cover editor lost its internal state.'}
            if($null -eq $st.Bitmap){throw 'This cover editor no longer has an image.'}
            $l=[int]$st.LeftNum.Value
            $r=[int]$st.RightNum.Value
            if($l -ge $r){throw 'The left spine edge must be before the right spine edge.'}

            $args=@{
                bitmap=$st.Bitmap
                sourcePath=$st.Path
                left=$l
                right=$r
                project=$st.Project.Text
                ship=$st.Ship.Text
                fandom=$st.Fandom.Text
                tags=$st.Tags.Text
                coverType=$st.CoverType.Text
            }
            Add-InlineBatchRecord @args
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
        if($null -ne $st.Bitmap){
            try{$st.Bitmap.Dispose()}catch{}
            $st.Bitmap=$null
        }
        if($null -ne $st.Panel){
            $parent=$st.Panel.Parent
            if($null -ne $parent){$parent.Controls.Remove($st.Panel)}
            $st.Panel.Dispose()
        }
    })

    [void]$script:InlineBatchPanels.Add($panel)
    return $panel
}

'@

    $text=$text.Substring(0,$start)+$replacement+$text.Substring($finish)

    [IO.File]::WriteAllText($targetMain,$text,(New-Object Text.UTF8Encoding($true)))

    @'
{
  "appId": "the-library",
  "appName": "The Library",
  "version": "1.0.12",
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
            ('The Library could not install the resilient batch-split repair.'+[Environment]::NewLine+[Environment]::NewLine+$message+[Environment]::NewLine+[Environment]::NewLine+'The previous app version was restored.'),
            'The Library Update'
        )|Out-Null
    }catch{}
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
name="payload-1.0.12-resilient-batch-split.txt"
(TF/name).write_bytes(raw)
sha=hashlib.sha256(raw).hexdigest()

validation={
    "version":VERSION,
    "baseVersion":"1.0.11",
    "payload":name,
    "payloadSha256":sha,
    "requirements":{
        "doesNotRequireV110Marker":"Could not find the v1.0.10 safe batch image loader" not in patcher,
        "addsLoaderIfMissing":"if(-not $text.Contains('function Load-InlineBatchImageSafe'))" in patcher,
        "replacesSplitterRegardlessOfPriorMarker":"$start=$text.IndexOf('function Add-InlineBatchSplitter')" in patcher,
        "persistentControlState":"$pic.Tag=$state" in patcher and "$save.Tag=$state" in patcher,
        "allInternalHashesVerified":all(hashlib.sha256(base64.b64decode(f["contentBase64"])).hexdigest()==f["sha256"] for f in files)
    }
}
if not all(validation["requirements"].values()):
    raise SystemExit(validation)

(TF/"resilient-batch-split-1.0.12-validation.json").write_text(json.dumps(validation,indent=2),encoding="utf-8")
vd=ROOT/".library-v112-validation"
vd.mkdir(exist_ok=True)
(vd/"CoverVault.ps1").write_bytes(base64.b64decode(files[0]["contentBase64"]))
print(json.dumps(validation,indent=2))
