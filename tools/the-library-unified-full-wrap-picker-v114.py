from pathlib import Path
import base64, hashlib, json, re

ROOT = Path(__file__).resolve().parents[1]
TF = ROOT / "the-library"
VERSION = "1.0.14"

m=json.loads((TF/"manifest.json").read_text(encoding="utf-8"))
if m.get("version")!="1.0.13":
    raise SystemExit(f"Expected live base 1.0.13, got {m.get('version')}")

prior=(ROOT/"tools/the-library-batch-split-drop-in-v113.py").read_text(encoding="utf-8")
match=re.search(r'dropin = r"""(.*?)"""\n\npatcher = r"""',prior,re.S)
if not match:
    raise SystemExit("Could not extract v1.0.13 Batch Split drop-in.")
dropin=match.group(1)

override=r'''
# UNIFIED FULL WRAP PICKER v1.0.14
function Get-LibraryAllChildControls($Root){
    $list=@()
    if($null -eq $Root){return $list}
    foreach($control in @($Root.Controls)){
        $list += $control
        if($null -ne $control.Controls -and $control.Controls.Count -gt 0){
            $list += @(Get-LibraryAllChildControls $control)
        }
    }
    return $list
}

function Remove-LibraryUnifiedWrapHost {
    if($null -eq $tabSplit){return}
    foreach($control in @(Get-LibraryAllChildControls $tabSplit)){
        if($control.Name -in @('LibraryUnifiedWrapHost','LibraryDropInBatchHost','InlineBatchSplitHost')){
            try{
                foreach($panel in @($control.Controls)){
                    $st=$panel.Tag
                    if($null -ne $st -and $null -ne $st.PSObject -and $null -ne $st.PSObject.Properties['Bitmap'] -and $null -ne $st.Bitmap){
                        if($null -ne $st.Pic){$st.Pic.Image=$null}
                        try{$st.Bitmap.Dispose()}catch{}
                        $st.Bitmap=$null
                    }elseif($null -ne $panel.Tag -and $panel.Tag -is [Drawing.Image]){
                        try{$panel.Tag.Dispose()}catch{}
                    }
                }
            }catch{}
            try{
                if($null -ne $control.Parent){$control.Parent.Controls.Remove($control)}
                $control.Dispose()
            }catch{}
        }
    }
    $script:LibraryDropInBatchHost=$null
    $script:LibraryUnifiedWrapHost=$null
}

function Show-LibraryUnifiedWrapPaths([string[]]$Paths){
    $paths=@($Paths|Where-Object{-not [string]::IsNullOrWhiteSpace($_)})
    if($paths.Count -eq 0){return}

    Remove-LibraryUnifiedWrapHost

    $host=New-Object Windows.Forms.FlowLayoutPanel
    $host.Name='LibraryUnifiedWrapHost'
    $host.FlowDirection='TopDown'
    $host.WrapContents=$false
    $host.AutoScroll=$true
    $host.Location=New-Object Drawing.Point(10,56)
    $host.Size=New-Object Drawing.Size(
        [math]::Max(300,$tabSplit.ClientSize.Width-20),
        [math]::Max(220,$tabSplit.ClientSize.Height-66)
    )
    $host.Anchor='Top,Bottom,Left,Right'
    $host.Padding=New-Object Windows.Forms.Padding(8)
    $host.BackColor=$tabSplit.BackColor
    $script:LibraryUnifiedWrapHost=$host
    $tabSplit.Controls.Add($host)
    $host.BringToFront()

    if($null -ne $script:LibraryUnifiedFullWrapButton){
        $script:LibraryUnifiedFullWrapButton.BringToFront()
    }

    $failed=New-Object Collections.Generic.List[string]
    $ordinal=0
    foreach($path in $paths){
        try{
            $ordinal++
            $panel=New-LibraryDropInBatchPanel $path $ordinal $paths.Count
            if($null -eq $panel){throw 'The cover panel was not created.'}
            $host.Controls.Add($panel)
        }catch{
            $ordinal--
            $failed.Add(([IO.Path]::GetFileName($path)+': '+$_.Exception.Message))
        }
    }

    if($host.Controls.Count -eq 0){
        $tabSplit.Controls.Remove($host)
        $host.Dispose()
        $script:LibraryUnifiedWrapHost=$null
        $detail=if($failed.Count -gt 0){[Environment]::NewLine+[Environment]::NewLine+(@($failed|Select-Object -First 8)-join [Environment]::NewLine)}else{''}
        [Windows.Forms.MessageBox]::Show(('None of those files could be opened as cover images.'+$detail),'Split Full Cover')|Out-Null
        return
    }

    if($failed.Count -gt 0){
        [Windows.Forms.MessageBox]::Show(
            ("Some covers could not be opened: $($failed.Count)"+[Environment]::NewLine+[Environment]::NewLine+(@($failed|Select-Object -First 8)-join [Environment]::NewLine)),
            'Split Full Cover'
        )|Out-Null
    }
}

function Start-LibraryUnifiedFullWrap {
    $pick=New-Object Windows.Forms.OpenFileDialog
    $pick.Title='Choose full cover wrap(s)'
    $pick.Filter='Image files|*.png;*.jpg;*.jpeg;*.bmp;*.tif;*.tiff|All files|*.*'
    $pick.Multiselect=$true
    if($pick.ShowDialog() -ne [Windows.Forms.DialogResult]::OK){return}

    $paths=@($pick.FileNames)
    if($paths.Count -eq 0){return}
    Show-LibraryUnifiedWrapPaths $paths
}

function Find-LibraryRegularFullWrapButton {
    $buttons=@(Get-LibraryAllChildControls $tabSplit | Where-Object{$_ -is [Windows.Forms.Button]})
    $regular=@(
        $buttons | Where-Object{
            $t=[string]$_.Text
            $upper=$t.ToUpperInvariant()
            $looksLikeWrap=(($upper.Contains('FULL') -and $upper.Contains('COVER')) -or ($upper.Contains('FULL') -and $upper.Contains('WRAP')))
            $isBatch=($upper.Contains('MULTIPLE') -or $upper.Contains('BATCH'))
            $looksLikeWrap -and -not $isBatch
        }
    )

    if($regular.Count -gt 0){return $regular[0]}

    $fallback=@(
        $buttons | Where-Object{
            $upper=([string]$_.Text).ToUpperInvariant()
            $isBatch=($upper.Contains('MULTIPLE') -or $upper.Contains('BATCH'))
            (-not $isBatch) -and $upper.Contains('COVER') -and ($upper.Contains('CHOOSE') -or $upper.Contains('SELECT') -or $upper.Contains('ADD') -or $upper.Contains('LOAD'))
        }
    )
    if($fallback.Count -gt 0){return $fallback[0]}
    return $null
}

function Initialize-LibraryBatchSplitDropIn {
    if($null -eq $tabSplit){throw 'The Split tab is unavailable.'}

    # Remove every separate batch/multiple button. There should be only one full-wrap chooser now.
    foreach($control in @(Get-LibraryAllChildControls $tabSplit)){
        if($control -is [Windows.Forms.Button]){
            $upper=([string]$control.Text).ToUpperInvariant()
            if($control.Name -eq 'LibraryDropInBatchButton' -or $upper.Contains('MULTIPLE') -or $upper.Contains('BATCH SPLIT')){
                try{
                    if($null -ne $control.Parent){$control.Parent.Controls.Remove($control)}
                    $control.Dispose()
                }catch{}
            }
        }
    }

    $original=Find-LibraryRegularFullWrapButton
    if($null -eq $original){
        throw 'Could not find the regular full-cover button to enable multi-select.'
    }

    $parent=$original.Parent
    if($null -eq $parent){throw 'The regular full-cover button has no parent container.'}

    $button=New-Object Windows.Forms.Button
    $button.Name='LibraryUnifiedFullWrapButton'
    $button.Text=$original.Text
    $button.Bounds=$original.Bounds
    $button.Anchor=$original.Anchor
    $button.Dock=$original.Dock
    $button.Font=$original.Font
    $button.BackColor=$original.BackColor
    $button.ForeColor=$original.ForeColor
    $button.FlatStyle=$original.FlatStyle
    $button.Enabled=$original.Enabled
    $button.Visible=$original.Visible
    $button.TabIndex=$original.TabIndex
    try{$button.Padding=$original.Padding}catch{}
    try{
        $button.FlatAppearance.BorderSize=$original.FlatAppearance.BorderSize
        $button.FlatAppearance.BorderColor=$original.FlatAppearance.BorderColor
        $button.FlatAppearance.MouseOverBackColor=$original.FlatAppearance.MouseOverBackColor
        $button.FlatAppearance.MouseDownBackColor=$original.FlatAppearance.MouseDownBackColor
    }catch{}

    $index=$parent.Controls.GetChildIndex($original)
    $parent.Controls.Remove($original)
    try{$original.Dispose()}catch{}
    $parent.Controls.Add($button)
    try{$parent.Controls.SetChildIndex($button,$index)}catch{}

    $button.Add_Click({Start-LibraryUnifiedFullWrap})
    $script:LibraryUnifiedFullWrapButton=$button
}
'''

dropin = dropin + override

patcher=r"""$ErrorActionPreference='Stop'
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
    if(-not(Test-Path -LiteralPath $dropIn)){throw 'The unified full-wrap component is missing.'}

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
  "version": "1.0.14",
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
            ('The Library could not install the unified full-wrap picker.'+[Environment]::NewLine+[Environment]::NewLine+$message+[Environment]::NewLine+[Environment]::NewLine+'The previous app version was restored.'),
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
    ("BatchSplitDropIn.ps1",dropin.encode("utf-8-sig")),
    ("AppVersion.json",appver),
]:
    files.append({"path":path,"sha256":hashlib.sha256(data).hexdigest(),"contentBase64":base64.b64encode(data).decode("ascii")})

payload={"schemaVersion":1,"appId":"the-library","appName":"The Library","version":VERSION,"files":files,"delete":[]}
raw=json.dumps(payload,separators=(",",":")).encode()
name="payload-1.0.14-unified-full-wrap-picker.txt"
(TF/name).write_bytes(raw)
sha=hashlib.sha256(raw).hexdigest()

validation={
    "version":VERSION,
    "baseVersion":"1.0.13",
    "payload":name,
    "payloadSha256":sha,
    "requirements":{
        "multiselectOnRegularFlow":"$pick.Multiselect=$true" in dropin and "Start-LibraryUnifiedFullWrap" in dropin,
        "removesSeparateBatchButtons":"MULTIPLE" in dropin and "BATCH SPLIT" in dropin,
        "findsRegularButton":"Find-LibraryRegularFullWrapButton" in dropin,
        "preservesRegularButtonText":"$button.Text=$original.Text" in dropin,
        "oneOrManySamePath":"Show-LibraryUnifiedWrapPaths $paths" in dropin,
        "persistentPanelState":"$panel.Tag=$state" in dropin,
        "allInternalHashesVerified":all(hashlib.sha256(base64.b64decode(f["contentBase64"])).hexdigest()==f["sha256"] for f in files)
    }
}
if not all(validation["requirements"].values()):
    raise SystemExit(validation)

(TF/"unified-full-wrap-picker-1.0.14-validation.json").write_text(json.dumps(validation,indent=2),encoding="utf-8")
vd=ROOT/".library-v114-validation"
vd.mkdir(exist_ok=True)
for f in files:
    (vd/f["path"]).write_bytes(base64.b64decode(f["contentBase64"]))
print(json.dumps(validation,indent=2))
