from pathlib import Path
import base64, hashlib, json

ROOT = Path(__file__).resolve().parents[1]
TF = ROOT / "the-library"
VERSION = "1.0.10"

m=json.loads((TF/"manifest.json").read_text(encoding="utf-8"))
if m.get("version")!="1.0.9":
    raise SystemExit(f"Expected live base 1.0.9, got {m.get('version')}")

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
    if(-not(Test-Path -LiteralPath $backupMain)){throw 'The updater backup is missing the previous Library app script.'}
    $text=[IO.File]::ReadAllText($backupMain,[Text.Encoding]::UTF8)

    $marker='# BATCH IMAGE LOADER SAFE FIX v1.0.10'
    if(-not $text.Contains($marker)){
        if(-not $text.Contains('# INLINE BATCH SPLIT WRAPS v1.0.8')){throw 'Could not find the current inline batch-split feature.'}
        if(-not $text.Contains('# FULL WRAPS ARE TEMPORARY SOURCES v1.0.9')){throw 'Could not find the v1.0.9 Library source marker.'}
        if(-not $text.Contains('function Add-InlineBatchSplitter')){throw 'Could not find the inline batch-splitter function.'}

        $old='$bitmap=Load-ImageUnlocked $path'
        if(-not $text.Contains($old)){throw 'Could not find the batch image-loader call that needs to be repaired.'}

        $helper=@'
# BATCH IMAGE LOADER SAFE FIX v1.0.10
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
        $graphics.DrawImage(
            $image,
            (New-Object Drawing.Rectangle(0,0,$copy.Width,$copy.Height)),
            0,0,$image.Width,$image.Height,
            [Drawing.GraphicsUnit]::Pixel
        )
        return $copy
    }
    catch{
        if($null -ne $copy){
            try{$copy.Dispose()}catch{}
            $copy=$null
        }
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
        $text=$text.Replace($old,'$bitmap=Load-InlineBatchImageSafe $path')
    }

    [IO.File]::WriteAllText($targetMain,$text,(New-Object Text.UTF8Encoding($true)))

    @'
{
  "appId": "the-library",
  "appName": "The Library",
  "version": "1.0.10",
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
            ('The Library could not install the batch image-loader repair.'+[Environment]::NewLine+[Environment]::NewLine+$message+[Environment]::NewLine+[Environment]::NewLine+'The previous app version was restored.'),
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
name="payload-1.0.10-batch-image-loader-safe.txt"
(TF/name).write_bytes(raw)
sha=hashlib.sha256(raw).hexdigest()

validation={
    "version":VERSION,
    "baseVersion":"1.0.9",
    "payload":name,
    "payloadSha256":sha,
    "requirements":{
        "keepsInlineBatchFlow":"# INLINE BATCH SPLIT WRAPS v1.0.8" in patcher,
        "keepsTemporaryFullWrapRule":"# FULL WRAPS ARE TEMPORARY SOURCES v1.0.9" in patcher,
        "addsDedicatedSafeLoader":"function Load-InlineBatchImageSafe" in patcher,
        "loadsFromBytes":"[IO.File]::ReadAllBytes($Path)" in patcher,
        "usesMemoryStream":"New-Object IO.MemoryStream(,$bytes)" in patcher,
        "validatesDecodedImage":"if($null -eq $image)" in patcher,
        "guardsDisposableObjects":"if($null -ne $image)" in patcher and "if($null -ne $stream)" in patcher and "if($null -ne $graphics)" in patcher,
        "batchUsesSafeLoader":"$bitmap=Load-InlineBatchImageSafe $path" in patcher,
        "normalSingleLoaderUntouched":"$text.Replace($old,'$bitmap=Load-InlineBatchImageSafe $path')" in patcher,
        "allInternalHashesVerified":all(hashlib.sha256(base64.b64decode(f["contentBase64"])).hexdigest()==f["sha256"] for f in files)
    }
}
if not all(validation["requirements"].values()):
    raise SystemExit(validation)

(TF/"batch-image-loader-safe-1.0.10-validation.json").write_text(json.dumps(validation,indent=2),encoding="utf-8")
vd=ROOT/".library-v110-validation"
vd.mkdir(exist_ok=True)
(vd/"CoverVault.ps1").write_bytes(base64.b64decode(files[0]["contentBase64"]))
print(json.dumps(validation,indent=2))
