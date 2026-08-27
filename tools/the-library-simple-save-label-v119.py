from pathlib import Path
import base64, hashlib, json, re

ROOT=Path(__file__).resolve().parents[1]
TF=ROOT/"the-library"
VERSION="1.0.19"

manifest=json.loads((TF/"manifest.json").read_text(encoding="utf-8"))
if manifest.get("version")!="1.0.18":
    raise SystemExit(f"Expected live base 1.0.18, got {manifest.get('version')}")

src=(ROOT/"tools/the-library-scroll-splitter-zoom-v118.py").read_text(encoding="utf-8")
m=re.search(r'dropin=r"""(.*?)"""\n\npatcher=r"""',src,re.S)
if not m:
    raise SystemExit("Could not extract v1.0.18 drop-in.")
dropin=m.group(1)

dropin=dropin.replace("$save.Text='SAVE BACK + SPINE + FRONT'","$save.Text='SAVE'")
dropin=dropin.replace("$btnSaveSplit.Text='SAVE BACK + SPINE + FRONT'","$btnSaveSplit.Text='SAVE'")

if "SAVE BACK + SPINE + FRONT" in dropin:
    raise SystemExit("Old save-button wording still exists in drop-in.")

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
    if(-not(Test-Path -LiteralPath $dropIn)){throw 'The Split Full Cover component is missing.'}

    $text=[IO.File]::ReadAllText($backupMain,[Text.Encoding]::UTF8)
    if(-not $text.Contains('Initialize-LibraryBatchSplitDropIn')){throw 'The Split Full Cover startup hook is missing.'}

    [IO.File]::WriteAllText($targetMain,$text,(New-Object Text.UTF8Encoding($true)))

    @'
{
  "appId": "the-library",
  "appName": "The Library",
  "version": "1.0.19",
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
            ('The Library could not install the save-label update.'+[Environment]::NewLine+[Environment]::NewLine+$message+[Environment]::NewLine+[Environment]::NewLine+'The previous app version was restored.'),
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
name="payload-1.0.19-simple-save-label.txt"
(TF/name).write_bytes(raw)
sha=hashlib.sha256(raw).hexdigest()

validation={
    "version":VERSION,
    "baseVersion":"1.0.18",
    "payload":name,
    "payloadSha256":sha,
    "requirements":{
        "singleSaveButtonIsSave":"$btnSaveSplit.Text='SAVE'" in dropin,
        "multiSaveButtonIsSave":"$save.Text='SAVE'" in dropin,
        "oldSaveButtonWordingGone":"SAVE BACK + SPINE + FRONT" not in dropin,
        "allInternalHashesVerified":all(hashlib.sha256(base64.b64decode(f["contentBase64"])).hexdigest()==f["sha256"] for f in files)
    }
}
if not all(validation["requirements"].values()):
    raise SystemExit(validation)

(TF/"simple-save-label-1.0.19-validation.json").write_text(json.dumps(validation,indent=2),encoding="utf-8")
vd=ROOT/".library-v119-validation"
vd.mkdir(exist_ok=True)
for f in files:
    (vd/f["path"]).write_bytes(base64.b64decode(f["contentBase64"]))
print(json.dumps(validation,indent=2))
