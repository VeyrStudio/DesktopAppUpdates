from pathlib import Path
import base64, hashlib, json

ROOT = Path(__file__).resolve().parents[1]
TF = ROOT / "the-library"
VERSION = "1.0.9"

m=json.loads((TF/"manifest.json").read_text(encoding="utf-8"))
if m.get("version")!="1.0.8":
    raise SystemExit(f"Expected live base 1.0.8, got {m.get('version')}")

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

try {
    if(-not(Test-Path -LiteralPath $backupMain)){throw 'The updater backup is missing the previous Library app script.'}
    $text=[IO.File]::ReadAllText($backupMain,[Text.Encoding]::UTF8)

    $marker='# FULL WRAPS ARE TEMPORARY SOURCES v1.0.9'
    if(-not $text.Contains($marker)){
        if(-not $text.Contains('function Add-LibraryRecord')){throw 'Could not find The Library record function.'}
        if(-not $text.Contains('function Get-AutoSplit')){throw 'Could not find the split-function boundary.'}

        $text=$text.Replace('function Add-LibraryRecord','function Add-LibraryRecordCore')

        $guard=@'
# FULL WRAPS ARE TEMPORARY SOURCES v1.0.9
function Add-LibraryRecord {
    param(
        $OriginalName,
        $StoredName,
        $Position,
        $Project,
        $Ship,
        $Fandom,
        $Tags
    )

    $positionText=[string]$Position
    $normalized=($positionText -replace '[^A-Za-z]','').ToLowerInvariant()

    if($normalized -in @('fullwrap','fullcover','wrap','completewrap','completecover')){
        try{
            if(-not [string]::IsNullOrWhiteSpace([string]$StoredName)){
                $dataRoot=Join-Path $appRoot 'Data'
                if(Test-Path -LiteralPath $dataRoot){
                    $leaf=[IO.Path]::GetFileName([string]$StoredName)
                    if(-not [string]::IsNullOrWhiteSpace($leaf)){
                        Get-ChildItem -LiteralPath $dataRoot -File -Recurse -ErrorAction SilentlyContinue |
                            Where-Object { $_.Name -eq $leaf } |
                            ForEach-Object {
                                try{Remove-Item -LiteralPath $_.FullName -Force -ErrorAction Stop}catch{}
                            }
                    }
                }
            }
        }catch{}
        return $null
    }

    $forward=@{
        OriginalName=$OriginalName
        StoredName=$StoredName
        Position=$Position
        Project=$Project
        Ship=$Ship
        Fandom=$Fandom
        Tags=$Tags
    }
    return Add-LibraryRecordCore @forward
}

'@
        $text=$text.Replace('function Get-AutoSplit',$guard+'function Get-AutoSplit')
    }

    [IO.File]::WriteAllText($targetMain,$text,(New-Object Text.UTF8Encoding($true)))

    @'
{
  "appId": "the-library",
  "appName": "The Library",
  "version": "1.0.9",
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
            ('The Library could not install the full-wrap temporary-source update.'+[Environment]::NewLine+[Environment]::NewLine+$message+[Environment]::NewLine+[Environment]::NewLine+'The previous app version was restored.'),
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
name="payload-1.0.9-full-wrap-temporary.txt"
(TF/name).write_bytes(raw)
sha=hashlib.sha256(raw).hexdigest()

validation={
    "version":VERSION,
    "baseVersion":"1.0.8",
    "payload":name,
    "payloadSha256":sha,
    "requirements":{
        "recordFunctionWrapped":"function Add-LibraryRecordCore" in patcher and "function Add-LibraryRecord {" in patcher,
        "fullWrapSuppressed":"'fullwrap'" in patcher,
        "fullCoverSuppressed":"'fullcover'" in patcher,
        "wrapSuppressed":"'wrap'" in patcher,
        "sourceCleanup":"Remove-Item -LiteralPath $_.FullName" in patcher,
        "cleanupLimitedToData":"$dataRoot=Join-Path $appRoot 'Data'" in patcher,
        "normalRecordsForwarded":"return Add-LibraryRecordCore @forward" in patcher,
        "allInternalHashesVerified":all(hashlib.sha256(base64.b64decode(f["contentBase64"])).hexdigest()==f["sha256"] for f in files)
    }
}
if not all(validation["requirements"].values()):
    raise SystemExit(validation)

(TF/"full-wrap-temporary-1.0.9-validation.json").write_text(json.dumps(validation,indent=2),encoding="utf-8")
vd=ROOT/".library-v109-validation"
vd.mkdir(exist_ok=True)
(vd/"CoverVault.ps1").write_bytes(base64.b64decode(files[0]["contentBase64"]))
print(json.dumps(validation,indent=2))
