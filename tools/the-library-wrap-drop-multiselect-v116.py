from pathlib import Path
import base64, hashlib, json

ROOT=Path(__file__).resolve().parents[1]
TF=ROOT/"the-library"
VERSION="1.0.16"

m=json.loads((TF/"manifest.json").read_text(encoding="utf-8"))
if m.get("version")!="1.0.15":
    raise SystemExit(f"Expected live base 1.0.15, got {m.get('version')}")

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

    $marker='# WRAP DROP MULTISELECT FIX v1.0.16'
    if(-not $text.Contains($marker)){
        if(-not $text.Contains('function Register-CoverDropTarget')){throw 'Could not find The Library drag-and-drop handler.'}

        $new=@'
    # WRAP DROP MULTISELECT FIX v1.0.16
    $Control.Add_DragDrop({
        param($sender,$e)
        $files = @([string[]]$e.Data.GetData([System.Windows.Forms.DataFormats]::FileDrop))
        if ($sender.Tag -eq "single") {
            $panelSingleDrop.BackColor = [System.Drawing.Color]::FromArgb(64, 18, 96)
            if ($files.Count -gt 0) { Set-SingleDroppedFile $files[0] }
        } else {
            $panelWrapDrop.BackColor = [System.Drawing.Color]::FromArgb(64, 18, 96)

            $valid = @(
                $files | Where-Object {
                    if ([string]::IsNullOrWhiteSpace($_) -or -not (Test-Path -LiteralPath $_ -PathType Leaf)) { return $false }
                    $ext=[System.IO.Path]::GetExtension($_).ToLowerInvariant()
                    return $ext -in @(".png",".jpg",".jpeg",".bmp",".tif",".tiff")
                }
            )

            if ($valid.Count -eq 1) {
                Set-WrapDroppedFile $valid[0]
            }
            elseif ($valid.Count -gt 1) {
                if (Get-Command Show-LibraryUnifiedWrapPaths -ErrorAction SilentlyContinue) {
                    Show-LibraryUnifiedWrapPaths -Paths $valid
                }
                else {
                    Show-Error "The multi-cover splitter is unavailable. Close and reopen The Library, then try the drop again."
                }
            }
            elseif ($files.Count -gt 0) {
                Show-Info "Drop image files only: PNG, JPG, BMP, TIF, or TIFF."
            }
        }
    })
'@

        $functionStart=$text.IndexOf('function Register-CoverDropTarget')
        $dragStart=$text.IndexOf('$Control.Add_DragDrop({',$functionStart)
        if($functionStart -lt 0 -or $dragStart -lt 0){throw 'Could not find the current drag-and-drop event block.'}

        $dragClose=$text.IndexOf('    })',$dragStart)
        if($dragClose -lt 0){
            $dragClose=$text.IndexOf('})',$dragStart)
        }
        if($dragClose -lt 0){throw 'Could not find the end of the current drag-and-drop event block.'}

        $dragEnd=$dragClose
        while($dragEnd -lt $text.Length -and $text[$dragEnd] -ne [char]10){$dragEnd++}
        if($dragEnd -lt $text.Length){$dragEnd++}

        $text=$text.Substring(0,$dragStart)+$new.TrimStart()+$text.Substring($dragEnd)
    }

    [IO.File]::WriteAllText($targetMain,$text,(New-Object Text.UTF8Encoding($true)))

    @'
{
  "appId": "the-library",
  "appName": "The Library",
  "version": "1.0.16",
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
            ('The Library could not install the multi-file drop fix.'+[Environment]::NewLine+[Environment]::NewLine+$message+[Environment]::NewLine+[Environment]::NewLine+'The previous app version was restored.'),
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
name="payload-1.0.16-wrap-drop-multiselect.txt"
(TF/name).write_bytes(raw)
sha=hashlib.sha256(raw).hexdigest()

validation={
    "version":VERSION,
    "baseVersion":"1.0.15",
    "payload":name,
    "payloadSha256":sha,
    "requirements":{
        "targetsActualDropHandler":"function Register-CoverDropTarget" in patcher,
        "removesFilesZeroOnlyBehavior":"Set-WrapDroppedFile $files[0]" not in patcher.split("$new=@'")[1] if "$new=@'" in patcher else True,
        "routesMultipleToBatch":"Show-LibraryUnifiedWrapPaths -Paths $valid" in patcher,
        "keepsSingleDrop":"Set-WrapDroppedFile $valid[0]" in patcher,
        "filtersImageTypes":"$ext -in @(\".png\",\".jpg\",\".jpeg\",\".bmp\",\".tif\",\".tiff\")" in patcher,
        "allInternalHashesVerified":all(hashlib.sha256(base64.b64decode(f["contentBase64"])).hexdigest()==f["sha256"] for f in files)
    }
}
if not all(validation["requirements"].values()):
    raise SystemExit(validation)

(TF/"wrap-drop-multiselect-1.0.16-validation.json").write_text(json.dumps(validation,indent=2),encoding="utf-8")
vd=ROOT/".library-v116-validation"
vd.mkdir(exist_ok=True)
(vd/"CoverVault.ps1").write_bytes(base64.b64decode(files[0]["contentBase64"]))
print(json.dumps(validation,indent=2))
