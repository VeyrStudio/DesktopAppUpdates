from pathlib import Path
import base64, hashlib, json

ROOT = Path(__file__).resolve().parents[1]
TF = ROOT / "the-library"
VERSION = "1.0.4"

m = json.loads((TF / "manifest.json").read_text(encoding="utf-8"))
if m.get("version") != "1.0.3":
    raise SystemExit(f"Expected live base 1.0.3, got {m.get('version')}")

patcher = r"""$ErrorActionPreference='Stop'
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

try {
    if(-not(Test-Path -LiteralPath $backupMain)){ throw 'The updater backup is missing the previous Library app script.' }
    $text=[IO.File]::ReadAllText($backupMain,[Text.Encoding]::UTF8)

    $old='$form.MinimumSize = New-Object System.Drawing.Size(520,420)'
    $new='$form.MinimumSize = New-Object System.Drawing.Size(420,360)'
    if($text.Contains($old)){
        $text=$text.Replace($old,$new)
    } elseif(-not $text.Contains($new)) {
        throw 'Could not find the current minimum-window-size setting.'
    }

    $oldCompact='$compact = $form.ClientSize.Width -lt 820'
    $newCompact='$compact = $form.ClientSize.Width -lt 720'
    if($text.Contains($oldCompact)){
        $text=$text.Replace($oldCompact,$newCompact)
    } elseif(-not $text.Contains($newCompact)) {
        throw 'Could not find the current compact-width breakpoint.'
    }

    $marker='# SPLIT SCREEN HARDENING v1.0.4'
    if(-not $text.Contains($marker)){
        $insert=@'
# SPLIT SCREEN HARDENING v1.0.4
$form.Add_Resize({
    try {
        Resize-CoverVaultLayout
        foreach($page in @($tabLibrary,$tabAdd,$tabSplit,$tabBackup)){
            if($null -ne $page){ $page.AutoScroll=$true }
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
        foreach($pat in $patterns){
            $rx=New-Object Text.RegularExpressions.Regex($pat)
            $m=$rx.Match($text)
            if($m.Success){$match=$m;break}
        }
        if($null -eq $match){throw 'Could not find the Library window startup point.'}
        $text=$text.Substring(0,$match.Index)+$insert+[Environment]::NewLine+$text.Substring($match.Index)
    }

    [IO.File]::WriteAllText($targetMain,$text,(New-Object Text.UTF8Encoding($true)))
    @'
{
  "appId": "the-library",
  "appName": "The Library",
  "version": "1.0.4",
  "manifestUrl": "https://raw.githubusercontent.com/VeyrStudio/DesktopAppUpdates/main/the-library/manifest.json"
}
'@ | Set-Content -LiteralPath $targetVersion -Encoding UTF8
    Relaunch-App
}
catch {
    $message=$_.Exception.Message
    try{if(Test-Path -LiteralPath $backupMain){Copy-Item -LiteralPath $backupMain -Destination $targetMain -Force}}catch{}
    try{if(Test-Path -LiteralPath $backupVersion){Copy-Item -LiteralPath $backupVersion -Destination $targetVersion -Force}}catch{}
    try{[Windows.Forms.MessageBox]::Show(('The Library could not install the split-screen update.'+[Environment]::NewLine+[Environment]::NewLine+$message),'The Library Update')|Out-Null}catch{}
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
    ("CoverVault.ps1", patcher.encode("utf-8-sig")),
    ("AppVersion.json", appver),
]:
    files.append({
        "path":path,
        "sha256":hashlib.sha256(data).hexdigest(),
        "contentBase64":base64.b64encode(data).decode("ascii")
    })

payload={"schemaVersion":1,"appId":"the-library","appName":"The Library","version":VERSION,"files":files,"delete":[]}
raw=json.dumps(payload,separators=(",",":")).encode()
name="payload-1.0.4-split-screen.txt"
(TF/name).write_bytes(raw)
sha=hashlib.sha256(raw).hexdigest()

validation={
    "version":VERSION,
    "baseVersion":"1.0.3",
    "payload":name,
    "payloadSha256":sha,
    "requirements":{
        "minimumWidthReduced": "Size(420,360)" in patcher,
        "compactBreakpointReduced": "Width -lt 720" in patcher,
        "allTabsAutoScroll": "foreach($page in @($tabLibrary,$tabAdd,$tabSplit,$tabBackup))" in patcher,
        "backupRestorePreservedByPatchingCurrentSource": True,
        "allInternalHashesVerified": all(hashlib.sha256(base64.b64decode(f["contentBase64"])).hexdigest()==f["sha256"] for f in files)
    }
}
if not all(validation["requirements"].values()):
    raise SystemExit(validation)
(TF/"split-screen-1.0.4-validation.json").write_text(json.dumps(validation,indent=2),encoding="utf-8")
vd=ROOT/".library-v104-validation"
vd.mkdir(exist_ok=True)
(vd/"CoverVault.ps1").write_bytes(base64.b64decode(files[0]["contentBase64"]))
print(json.dumps(validation,indent=2))
