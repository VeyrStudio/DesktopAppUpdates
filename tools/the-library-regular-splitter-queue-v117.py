from pathlib import Path
import base64, hashlib, json

ROOT=Path(__file__).resolve().parents[1]
TF=ROOT/"the-library"
VERSION="1.0.17"

manifest=json.loads((TF/"manifest.json").read_text(encoding="utf-8"))
if manifest.get("version")!="1.0.16":
    raise SystemExit(f"Expected live base 1.0.16, got {manifest.get('version')}")

dropin=r"""# THE LIBRARY REGULAR SPLITTER QUEUE v1.0.17
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$script:LibraryWrapQueue=@()
$script:LibraryWrapQueueIndex=-1
$script:LibraryWrapQueueSwitching=$false
$script:LibraryWrapQueueLabel=$null
$script:LibraryWrapPrevButton=$null
$script:LibraryWrapNextButton=$null

function New-LibraryWrapQueueItem([string]$Path){
    [pscustomobject]@{
        Path=[string]$Path
        Loaded=$false
        SplitLeft=0
        SplitRight=0
        Project=''
        Ship=''
        Fandom=''
        Tags=''
        CoverType=''
    }
}

function Get-LibraryWrapQueueCurrent {
    $count=@($script:LibraryWrapQueue).Count
    if($count -eq 0){return $null}
    if($script:LibraryWrapQueueIndex -lt 0 -or $script:LibraryWrapQueueIndex -ge $count){return $null}
    return @($script:LibraryWrapQueue)[$script:LibraryWrapQueueIndex]
}

function Save-LibraryWrapQueueUiState {
    if($script:LibraryWrapQueueSwitching){return}
    $item=Get-LibraryWrapQueueCurrent
    if($null -eq $item){return}
    try{
        $item.SplitLeft=[int]$numSplitLeft.Value
        $item.SplitRight=[int]$numSplitRight.Value
        $item.Project=[string]$txtWrapProject.Text
        $item.Ship=[string]$txtWrapShip.Text
        $item.Fandom=[string]$txtWrapFandom.Text
        $item.Tags=[string]$txtWrapTags.Text
        $item.CoverType=[string]$cmbWrapCoverType.Text
        $item.Loaded=$true
    }catch{}
}

function Update-LibraryWrapQueueUi {
    $count=@($script:LibraryWrapQueue).Count
    $item=Get-LibraryWrapQueueCurrent

    if($null -ne $script:LibraryWrapPrevButton){
        $script:LibraryWrapPrevButton.Visible=($count -gt 1)
        $script:LibraryWrapPrevButton.Enabled=($count -gt 1 -and $script:LibraryWrapQueueIndex -gt 0)
    }
    if($null -ne $script:LibraryWrapNextButton){
        $script:LibraryWrapNextButton.Visible=($count -gt 1)
        $script:LibraryWrapNextButton.Enabled=($count -gt 1 -and $script:LibraryWrapQueueIndex -lt ($count-1))
    }
    if($null -ne $script:LibraryWrapQueueLabel){
        if($count -gt 1 -and $null -ne $item){
            $script:LibraryWrapQueueLabel.Text=("COVER {0} OF {1}" -f ($script:LibraryWrapQueueIndex+1),$count)
            $script:LibraryWrapQueueLabel.Visible=$true
        }else{
            $script:LibraryWrapQueueLabel.Text=''
            $script:LibraryWrapQueueLabel.Visible=$false
        }
    }
    if($null -ne $lblWrapFile -and $null -ne $item){
        if($count -gt 1){
            $lblWrapFile.Text=("{0} of {1}  -  {2}" -f ($script:LibraryWrapQueueIndex+1),$count,[IO.Path]::GetFileName($item.Path))
        }else{
            $lblWrapFile.Text=[IO.Path]::GetFileName($item.Path)
        }
    }
}

function Show-LibraryWrapQueueItem([int]$Index){
    $count=@($script:LibraryWrapQueue).Count
    if($count -eq 0){return}
    if($Index -lt 0 -or $Index -ge $count){return}

    Save-LibraryWrapQueueUiState
    $script:LibraryWrapQueueSwitching=$true
    try{
        $script:LibraryWrapQueueIndex=$Index
        $item=@($script:LibraryWrapQueue)[$Index]
        if($null -eq $item -or [string]::IsNullOrWhiteSpace([string]$item.Path)){
            throw 'The queued cover path is missing.'
        }

        Set-WrapDroppedFile $item.Path

        if($item.Loaded){
            if($item.SplitLeft -ge [int]$numSplitLeft.Minimum -and $item.SplitLeft -le [int]$numSplitLeft.Maximum){
                $numSplitLeft.Value=[decimal]$item.SplitLeft
            }
            if($item.SplitRight -ge [int]$numSplitRight.Minimum -and $item.SplitRight -le [int]$numSplitRight.Maximum){
                $numSplitRight.Value=[decimal]$item.SplitRight
            }
            $txtWrapProject.Text=[string]$item.Project
            $txtWrapShip.Text=[string]$item.Ship
            $txtWrapFandom.Text=[string]$item.Fandom
            $txtWrapTags.Text=[string]$item.Tags
            if(-not [string]::IsNullOrWhiteSpace([string]$item.CoverType)){
                $cmbWrapCoverType.Text=[string]$item.CoverType
            }
            Update-SplitPreview
        }else{
            $item.SplitLeft=[int]$numSplitLeft.Value
            $item.SplitRight=[int]$numSplitRight.Value
            $item.CoverType=[string]$cmbWrapCoverType.Text
            $item.Loaded=$true
        }

        Update-LibraryWrapQueueUi
    }finally{
        $script:LibraryWrapQueueSwitching=$false
    }
}

function Start-LibraryWrapQueue([string[]]$Paths){
    $valid=@(
        $Paths | Where-Object {
            if([string]::IsNullOrWhiteSpace([string]$_)){return $false}
            if(-not(Test-Path -LiteralPath $_ -PathType Leaf)){return $false}
            $ext=[IO.Path]::GetExtension([string]$_).ToLowerInvariant()
            return $ext -in @('.png','.jpg','.jpeg','.bmp','.tif','.tiff')
        }
    )
    if($valid.Count -eq 0){
        Show-Info 'Drop image files only: PNG, JPG, BMP, TIF, or TIFF.'
        return
    }

    $script:LibraryWrapQueue=@($valid | ForEach-Object { New-LibraryWrapQueueItem $_ })
    $script:LibraryWrapQueueIndex=-1
    Show-LibraryWrapQueueItem 0
}

function Show-LibraryUnifiedWrapPaths([string[]]$Paths){
    Start-LibraryWrapQueue -Paths $Paths
}

function Clear-LibraryWrapQueueCurrentUi {
    $script:SelectedWrapFile=$null
    if($null -ne $lblWrapFile){$lblWrapFile.Text='No full wrap selected'}
    if($null -ne $script:WrapBitmap){
        try{$script:WrapBitmap.Dispose()}catch{}
        $script:WrapBitmap=$null
    }
    if($null -ne $pbWrapPreview){Set-PictureImage $pbWrapPreview $null}
    if($null -ne $pbBackPreview){Set-PictureImage $pbBackPreview $null}
    if($null -ne $pbSpinePreview){Set-PictureImage $pbSpinePreview $null}
    if($null -ne $pbFrontPreview){Set-PictureImage $pbFrontPreview $null}
    if($null -ne $txtWrapProject){$txtWrapProject.Clear()}
    if($null -ne $txtWrapShip){$txtWrapShip.Clear()}
    if($null -ne $txtWrapFandom){$txtWrapFandom.Clear()}
    if($null -ne $txtWrapTags){$txtWrapTags.Clear()}
}

function Remove-LibraryWrapQueueCurrent {
    $count=@($script:LibraryWrapQueue).Count
    if($count -eq 0){return}
    $index=$script:LibraryWrapQueueIndex
    if($index -lt 0 -or $index -ge $count){$index=0}

    $remaining=@()
    for($i=0;$i -lt $count;$i++){
        if($i -ne $index){$remaining += @($script:LibraryWrapQueue)[$i]}
    }
    $script:LibraryWrapQueue=@($remaining)

    if(@($script:LibraryWrapQueue).Count -eq 0){
        $script:LibraryWrapQueueIndex=-1
        Clear-LibraryWrapQueueCurrentUi
        Update-LibraryWrapQueueUi
        return
    }

    if($index -ge @($script:LibraryWrapQueue).Count){$index=@($script:LibraryWrapQueue).Count-1}
    $script:LibraryWrapQueueIndex=-1
    Show-LibraryWrapQueueItem $index
}

function Save-WrapAndPieces {
    if($null -eq $script:WrapBitmap -or [string]::IsNullOrWhiteSpace([string]$script:SelectedWrapFile)){
        Show-Info 'Choose or drop a full cover wrap first.'
        return
    }

    Update-SplitPreview
    if($script:SplitLeft -le 0 -or $script:SplitRight -le $script:SplitLeft -or $script:SplitRight -ge $script:WrapBitmap.Width){
        Show-Error 'The split guide positions are invalid.'
        return
    }

    try{
        $sourcePath=[string]$script:SelectedWrapFile
        $base=[IO.Path]::GetFileNameWithoutExtension($sourcePath)

        $pieces=@(
            @{Position='Back Cover';X=0;Width=[int]$script:SplitLeft;Label='Back Cover'},
            @{Position='Spine';X=[int]$script:SplitLeft;Width=[int]($script:SplitRight-$script:SplitLeft);Label='Spine'},
            @{Position='Front Cover';X=[int]$script:SplitRight;Width=[int]($script:WrapBitmap.Width-$script:SplitRight);Label='Front Cover'}
        )

        $createdFiles=@()
        try{
            foreach($piece in $pieces){
                if([int]$piece.Width -le 0){throw ("The "+$piece.Label+" crop has zero width.")}
                $stored=Make-UniqueStoredName '.png'
                $dest=Join-Path $script:FilesRoot $stored
                Save-CropPng $script:WrapBitmap ([int]$piece.X) ([int]$piece.Width) $dest
                $createdFiles += $dest

                $script:PendingCoverType=[string]$cmbWrapCoverType.Text
                $recordArgs=@{
                    OriginalName=(Make-SplitName $base $piece.Label)
                    StoredName=$stored
                    Position=$piece.Position
                    Project=$txtWrapProject.Text
                    Ship=$txtWrapShip.Text
                    Fandom=$txtWrapFandom.Text
                    Tags=$txtWrapTags.Text
                }
                Add-LibraryRecord @recordArgs | Out-Null
            }
        }catch{
            foreach($file in @($createdFiles)){
                try{Remove-Item -LiteralPath $file -Force -ErrorAction SilentlyContinue}catch{}
            }
            throw
        }

        if($null -ne $chkMoveWrap -and $chkMoveWrap.Checked){
            try{Remove-Item -LiteralPath $sourcePath -Force -ErrorAction Stop}catch{}
        }

        Refresh-HierarchyTree
        Refresh-LibraryGrid

        if(@($script:LibraryWrapQueue).Count -gt 0){
            Remove-LibraryWrapQueueCurrent
            if(@($script:LibraryWrapQueue).Count -gt 0){
                Show-Info ('Saved Back Cover, Spine, and Front Cover.'+[Environment]::NewLine+[Environment]::NewLine+'Next queued cover is ready.')
            }else{
                Show-Info 'Saved Back Cover, Spine, and Front Cover. All queued covers are finished.'
            }
        }else{
            Clear-LibraryWrapQueueCurrentUi
            Show-Info 'Saved Back Cover, Spine, and Front Cover.'
        }
    }catch{
        Show-Error ('The full wrap could not be split and saved.'+[Environment]::NewLine+[Environment]::NewLine+$_.Exception.Message)
    }
}

function Initialize-LibraryBatchSplitDropIn {
    if($null -eq $tabSplit){throw 'The Split Full Cover tab is unavailable.'}

    if($null -ne $btnChooseWrap){
        try{$btnChooseWrap.Visible=$false}catch{}
    }
    if($null -ne $lblWrapDrop){
        $lblWrapDrop.Text='DROP FULL COVER IMAGE(S) HERE'
    }
    if($null -ne $lblWrapDrop2){
        $lblWrapDrop2.Text='Select one or more covers in File Explorer and drag them into this purple box'
        $lblWrapDrop2.Width=760
    }
    if($null -ne $lblWrapFile){$lblWrapFile.Width=760}

    foreach($control in @($tabSplit.Controls)){
        if($control.Name -in @('LibraryDropInBatchHost','LibraryUnifiedWrapHost','InlineBatchSplitHost','LibraryDropInBatchButton','LibraryUnifiedFullWrapButton')){
            try{$tabSplit.Controls.Remove($control);$control.Dispose()}catch{}
        }
    }

    $prev=New-Object Windows.Forms.Button
    $prev.Name='LibraryWrapQueuePrevious'
    $prev.Text='PREVIOUS'
    $prev.Location=New-Object Drawing.Point(805,190)
    $prev.Size=New-Object Drawing.Size(100,30)
    $prev.Visible=$false
    $prev.Add_Click({Save-LibraryWrapQueueUiState;Show-LibraryWrapQueueItem ($script:LibraryWrapQueueIndex-1)})
    $tabSplit.Controls.Add($prev)
    $script:LibraryWrapPrevButton=$prev

    $next=New-Object Windows.Forms.Button
    $next.Name='LibraryWrapQueueNext'
    $next.Text='NEXT'
    $next.Location=New-Object Drawing.Point(915,190)
    $next.Size=New-Object Drawing.Size(100,30)
    $next.Visible=$false
    $next.Add_Click({Save-LibraryWrapQueueUiState;Show-LibraryWrapQueueItem ($script:LibraryWrapQueueIndex+1)})
    $tabSplit.Controls.Add($next)
    $script:LibraryWrapNextButton=$next

    $label=New-Object Windows.Forms.Label
    $label.Name='LibraryWrapQueueLabel'
    $label.Text=''
    $label.Location=New-Object Drawing.Point(1025,194)
    $label.Size=New-Object Drawing.Size(135,24)
    $label.TextAlign='MiddleRight'
    $label.Visible=$false
    $tabSplit.Controls.Add($label)
    $script:LibraryWrapQueueLabel=$label

    Update-LibraryWrapQueueUi
}
"""

patcher=r"""$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Windows.Forms

$appRoot=Split-Path -Parent $PSScriptRoot
$backupDir=Join-Path $appRoot 'UpdateBackup'
$backupMain=Join-Path $backupDir 'CoverVault.ps1'
$backupVersion=Join-Path $backupDir 'AppVersion.json'
$targetMain=Join-Path $PSScriptRoot 'CoverVault.ps1'
$targetVersion=Join-Path $PSScriptRoot 'AppVersion.json'
$dropIn=Join-Path $PSScriptRoot 'BatchSplitDropIn.ps1'
$launcher=Join-Path $PSScriptRoot 'Launch Cover Vault.vbs'

function Relaunch-App {
    if(Test-Path -LiteralPath $launcher){
        Start-Process -FilePath 'wscript.exe' -ArgumentList ('"' + $launcher + '"')
    }
}

try{
    if(-not(Test-Path -LiteralPath $backupMain)){throw 'The updater backup is missing the previous Library app script.'}
    if(-not(Test-Path -LiteralPath $dropIn)){throw 'The regular splitter queue file is missing.'}

    $text=[IO.File]::ReadAllText($backupMain,[Text.Encoding]::UTF8)
    if(-not $text.Contains('function Register-CoverDropTarget')){throw 'Could not find The Library drag-and-drop handler.'}
    if(-not $text.Contains('function Set-WrapDroppedFile')){throw 'Could not find The Library regular wrap splitter.'}
    if(-not $text.Contains('Show-LibraryUnifiedWrapPaths -Paths $valid')){throw 'The v1.0.16 multi-file drop route is not installed.'}
    if(-not $text.Contains('Initialize-LibraryBatchSplitDropIn')){throw 'The drop-in startup hook is missing.'}

    [IO.File]::WriteAllText($targetMain,$text,(New-Object Text.UTF8Encoding($true)))

    @'
{
  "appId": "the-library",
  "appName": "The Library",
  "version": "1.0.17",
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
            ('The Library could not install the regular-splitter queue fix.'+[Environment]::NewLine+[Environment]::NewLine+$message+[Environment]::NewLine+[Environment]::NewLine+'The previous app version was restored.'),
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
    files.append({"path":path,"sha256":hashlib.sha256(data).hexdigest(),"contentBase64":base64.b64encode(data).decode("ascii")})

payload={"schemaVersion":1,"appId":"the-library","appName":"The Library","version":VERSION,"files":files,"delete":[]}
raw=json.dumps(payload,separators=(",",":")).encode()
name="payload-1.0.17-regular-splitter-queue.txt"
(TF/name).write_bytes(raw)
sha=hashlib.sha256(raw).hexdigest()

validation={
    "version":VERSION,
    "baseVersion":"1.0.16",
    "payload":name,
    "payloadSha256":sha,
    "requirements":{
        "bypassesBatchPanels":"function New-LibraryDropInBatchPanel" not in dropin,
        "usesRegularSplitter":"Set-WrapDroppedFile $item.Path" in dropin,
        "multiDropAliasUsesQueue":"Start-LibraryWrapQueue -Paths $Paths" in dropin,
        "queueNavigation":"LibraryWrapQueuePrevious" in dropin and "LibraryWrapQueueNext" in dropin,
        "noFullWrapRecord":"Position='Full Wrap'" not in dropin and 'Position="Full Wrap"' not in dropin,
        "allInternalHashesVerified":all(hashlib.sha256(base64.b64decode(f["contentBase64"])).hexdigest()==f["sha256"] for f in files)
    }
}
if not all(validation["requirements"].values()):
    raise SystemExit(validation)

(TF/"regular-splitter-queue-1.0.17-validation.json").write_text(json.dumps(validation,indent=2),encoding="utf-8")
vd=ROOT/".library-v117-validation"
vd.mkdir(exist_ok=True)
for f in files:
    (vd/f["path"]).write_bytes(base64.b64decode(f["contentBase64"]))
print(json.dumps(validation,indent=2))
