from pathlib import Path
import base64, hashlib, json

ROOT=Path(__file__).resolve().parents[1]
TF=ROOT/"the-library"
VERSION="1.0.21"

manifest=json.loads((TF/"manifest.json").read_text(encoding="utf-8"))
if manifest.get("version")!="1.0.20":
    raise SystemExit(f"Expected live base 1.0.20, got {manifest.get('version')}")

patcher=r"""$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Windows.Forms

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

try{
    if(-not(Test-Path -LiteralPath $backupMain)){throw 'The updater backup is missing the previous Library app script.'}
    $text=[IO.File]::ReadAllText($backupMain,[Text.Encoding]::UTF8)

    if(-not $text.Contains('$form = New-Object TheLibraryForm')){throw 'Could not find The Library main window.'}
    if(-not $text.Contains('$tabs = New-Object System.Windows.Forms.TabControl')){throw 'Could not find The Library tabs.'}

    # The old custom frameless window was the weak link for Windows Snap/Snap Layouts.
    $oldBorder='$form.FormBorderStyle = [System.Windows.Forms.FormBorderStyle]::None'
    $newBorder='$form.FormBorderStyle = [System.Windows.Forms.FormBorderStyle]::Sizable'
    if($text.Contains($oldBorder)){
        $text=$text.Replace($oldBorder,$newBorder)
    }elseif(-not $text.Contains($newBorder)){
        throw 'Could not find The Library window border setting.'
    }

    foreach($oldMin in @(
        '$form.MinimumSize = New-Object System.Drawing.Size(560,420)',
        '$form.MinimumSize = New-Object System.Drawing.Size(520,420)',
        '$form.MinimumSize = New-Object System.Drawing.Size(420,360)'
    )){
        if($text.Contains($oldMin)){
            $text=$text.Replace($oldMin,'$form.MinimumSize = New-Object System.Drawing.Size(360,320)')
            break
        }
    }
    if(-not $text.Contains('$form.MinimumSize = New-Object System.Drawing.Size(360,320)')){
        $needle='$form.Size = New-Object System.Drawing.Size(1360,920)'
        if($text.Contains($needle)){
            $text=$text.Replace($needle,$needle+[Environment]::NewLine+'$form.MinimumSize = New-Object System.Drawing.Size(360,320)')
        }else{
            throw 'Could not establish The Library minimum snap width.'
        }
    }

    # Hide the fake title bar. Windows gets the real title bar/buttons back, which
    # restores native drag-snap, Snap Assist, and Windows 11 Snap Layouts.
    $headerNeedle='$form.Controls.Add($headerPanel)'
    if($text.Contains($headerNeedle) -and -not $text.Contains('# NATIVE WINDOWS SNAP v1.0.21')){
        $headerReplacement=@'
$form.Controls.Add($headerPanel)
# NATIVE WINDOWS SNAP v1.0.21
$headerPanel.Visible = $false
'@
        $text=$text.Replace($headerNeedle,$headerReplacement.TrimEnd())
    }elseif(-not $text.Contains('# NATIVE WINDOWS SNAP v1.0.21')){
        throw 'Could not find the custom title bar.'
    }

    # Reclaim the top space that used to be occupied by the custom floral title bar.
    foreach($oldTabs in @(
        '$tabs.Location = New-Object System.Drawing.Point(18,50)',
        '$tabs.Location = New-Object System.Drawing.Point(18,52)'
    )){
        if($text.Contains($oldTabs)){
            $text=$text.Replace($oldTabs,'$tabs.Location = New-Object System.Drawing.Point(12,12)')
            break
        }
    }

    $oldAnchor='$tabs.Anchor = "Top,Left"'
    if($text.Contains($oldAnchor)){
        $text=$text.Replace($oldAnchor,'$tabs.Anchor = "Top,Bottom,Left,Right"')
    }

    # Make the native caption match The Library instead of reverting to a generic light bar.
    $showMarker='# NATIVE SNAP TITLEBAR COLOR v1.0.21'
    if(-not $text.Contains($showMarker)){
        $insert=@'
# NATIVE SNAP TITLEBAR COLOR v1.0.21
$form.Add_HandleCreated({
    try { Apply-CoverVaultTitleBar $form } catch {}
})
$form.Add_Shown({
    try {
        Apply-CoverVaultTitleBar $form
        Resize-CoverVaultLayout
        foreach($page in @($tabLibrary,$tabAdd,$tabSplit,$tabBackup)){
            if($null -ne $page){$page.AutoScroll=$true}
        }
    } catch {}
})

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
        $text=$text.Substring(0,$match.Index)+$insert+$text.Substring($match.Index)
    }

    # Resize function should work from the native client area, not reserve fake-title-bar space.
    $oldLeft='$left = 18'
    $oldRight='$right = 18'
    if($text.Contains($oldLeft)){$text=$text.Replace($oldLeft,'$left = 12')}
    if($text.Contains($oldRight)){$text=$text.Replace($oldRight,'$right = 12')}

    [IO.File]::WriteAllText($targetMain,$text,(New-Object Text.UTF8Encoding($true)))

    @'
{
  "appId": "the-library",
  "appName": "The Library",
  "version": "1.0.21",
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
            ('The Library could not install the native split-screen update.'+[Environment]::NewLine+[Environment]::NewLine+$message+[Environment]::NewLine+[Environment]::NewLine+'The previous app version was restored.'),
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
    ("AppVersion.json",appver),
]:
    files.append({"path":path,"sha256":hashlib.sha256(data).hexdigest(),"contentBase64":base64.b64encode(data).decode("ascii")})

payload={"schemaVersion":1,"appId":"the-library","appName":"The Library","version":VERSION,"files":files,"delete":[]}
raw=json.dumps(payload,separators=(",",":")).encode()
name="payload-1.0.21-native-snap.txt"
(TF/name).write_bytes(raw)
sha=hashlib.sha256(raw).hexdigest()

validation={
    "version":VERSION,
    "baseVersion":"1.0.20",
    "payload":name,
    "payloadSha256":sha,
    "requirements":{
        "nativeSizableBorder":"FormBorderStyle]::Sizable" in patcher,
        "customHeaderHidden":"$headerPanel.Visible = $false" in patcher,
        "nativeTitlebarColor":"Apply-CoverVaultTitleBar $form" in patcher,
        "narrowMinimumWidth":"Size(360,320)" in patcher,
        "tabsReclaimTitlebarSpace":"Point(12,12)" in patcher,
        "tabsAnchorAllSides":"Top,Bottom,Left,Right" in patcher,
        "allTabsAutoScroll":"foreach($page in @($tabLibrary,$tabAdd,$tabSplit,$tabBackup))" in patcher,
        "allInternalHashesVerified":all(hashlib.sha256(base64.b64decode(f["contentBase64"])).hexdigest()==f["sha256"] for f in files)
    }
}
if not all(validation["requirements"].values()):
    raise SystemExit(validation)

(TF/"native-snap-1.0.21-validation.json").write_text(json.dumps(validation,indent=2),encoding="utf-8")
vd=ROOT/".library-v121-validation"
vd.mkdir(exist_ok=True)
(vd/"CoverVault.ps1").write_bytes(base64.b64decode(files[0]["contentBase64"]))
print(json.dumps(validation,indent=2))
