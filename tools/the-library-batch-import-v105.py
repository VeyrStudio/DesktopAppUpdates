from pathlib import Path
import base64, hashlib, json

ROOT = Path(__file__).resolve().parents[1]
TF = ROOT / "the-library"
VERSION = "1.0.5"

m = json.loads((TF / "manifest.json").read_text(encoding="utf-8"))
if m.get("version") != "1.0.4":
    raise SystemExit(f"Expected live base 1.0.4, got {m.get('version')}")

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

    # Cumulative split-screen hardening from v1.0.4.
    $old='$form.MinimumSize = New-Object System.Drawing.Size(520,420)'
    $new='$form.MinimumSize = New-Object System.Drawing.Size(420,360)'
    if($text.Contains($old)){ $text=$text.Replace($old,$new) }

    $oldCompact='$compact = $form.ClientSize.Width -lt 820'
    $newCompact='$compact = $form.ClientSize.Width -lt 720'
    if($text.Contains($oldCompact)){ $text=$text.Replace($oldCompact,$newCompact) }

    $splitMarker='# SPLIT SCREEN HARDENING v1.0.4'
    if(-not $text.Contains($splitMarker)){
        $splitInsert=@'
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
        if($null -eq $match){throw 'Could not find the Library window startup point for split-screen hardening.'}
        $text=$text.Substring(0,$match.Index)+$splitInsert+[Environment]::NewLine+$text.Substring($match.Index)
    }

    # Batch cover import.
    $batchMarker='# BATCH COVER IMPORT v1.0.5'
    if(-not $text.Contains($batchMarker)){
        if(-not $text.Contains('function Import-SingleImage')){ throw 'Could not find the existing single-image importer.' }
        if(-not $text.Contains('function Get-AutoSplit')){ throw 'Could not find the cover-split function boundary.' }

        $batchFunction=@'
# BATCH COVER IMPORT v1.0.5
function Import-MultipleImages {
    $dlg = New-Object System.Windows.Forms.OpenFileDialog
    $dlg.Title = "Import multiple images to The Library"
    $dlg.Filter = "Image files|*.png;*.jpg;*.jpeg;*.bmp;*.tif;*.tiff|All files|*.*"
    $dlg.Multiselect = $true

    if ($dlg.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK) { return }

    $files = @($dlg.FileNames)
    if ($files.Count -eq 0) { return }

    $imported = 0
    $skipped = 0
    $failed = New-Object System.Collections.Generic.List[string]

    foreach ($source in $files) {
        try {
            if ([string]::IsNullOrWhiteSpace($source) -or -not (Test-Path -LiteralPath $source)) {
                $skipped++
                continue
            }

            $ext = [System.IO.Path]::GetExtension($source).ToLowerInvariant()
            if ($ext -notin @(".png",".jpg",".jpeg",".bmp",".tif",".tiff")) {
                $skipped++
                continue
            }

            $probe = Load-ImageUnlocked $source
            if ($null -ne $probe) { $probe.Dispose() }

            if (-not (Confirm-DuplicateImport $source)) {
                $skipped++
                continue
            }

            $originalName = [System.IO.Path]::GetFileName($source)
            $stored = Copy-Or-Move-IntoVault $source $false

            $script:PendingCoverType = $cmbSingleCoverType.Text
            Add-LibraryRecord `
                -OriginalName $originalName `
                -StoredName $stored `
                -Position $cmbSinglePosition.Text `
                -Project $txtSingleProject.Text `
                -Ship $txtSingleShip.Text `
                -Fandom $txtSingleFandom.Text `
                -Tags $txtSingleTags.Text | Out-Null

            $imported++
        }
        catch {
            $failed.Add(([System.IO.Path]::GetFileName($source) + ": " + $_.Exception.Message))
        }
    }

    Refresh-HierarchyTree
    Refresh-LibraryGrid

    $summary = "Imported $imported image"
    if ($imported -ne 1) { $summary += "s" }
    $summary += " to The Library."

    if ($skipped -gt 0) {
        $summary += [Environment]::NewLine + [Environment]::NewLine + "Skipped: $skipped"
    }

    if ($failed.Count -gt 0) {
        $summary += [Environment]::NewLine + [Environment]::NewLine + "Could not import: $($failed.Count)"
        $preview = @($failed | Select-Object -First 5)
        if ($preview.Count -gt 0) {
            $summary += [Environment]::NewLine + ($preview -join [Environment]::NewLine)
        }
        if ($failed.Count -gt 5) {
            $summary += [Environment]::NewLine + "...and $($failed.Count - 5) more."
        }
    }

    $summary += [Environment]::NewLine + [Environment]::NewLine + "Your original image files were kept."
    Show-Info $summary
}

'@
        $text=$text.Replace('function Get-AutoSplit',$batchFunction+'function Get-AutoSplit')

        $uiNeedle='$tabAdd.Controls.Add($btnImportSingle)'
        if(-not $text.Contains($uiNeedle)){ throw 'Could not find the Add-tab save button.' }

        $uiInsert=@'
$tabAdd.Controls.Add($btnImportSingle)

$btnImportMultiple = New-Button "IMPORT MULTIPLE IMAGES" 405 608 220 42
$btnImportMultiple.Add_Click({ Import-MultipleImages })
$tabAdd.Controls.Add($btnImportMultiple)
'@
        $text=$text.Replace($uiNeedle,$uiInsert)
    }

    [IO.File]::WriteAllText($targetMain,$text,(New-Object Text.UTF8Encoding($true)))

    @'
{
  "appId": "the-library",
  "appName": "The Library",
  "version": "1.0.5",
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
            ('The Library could not install the multiple-cover update.'+[Environment]::NewLine+[Environment]::NewLine+$message+[Environment]::NewLine+[Environment]::NewLine+'The previous app version was restored.'),
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
name="payload-1.0.5-batch-import.txt"
(TF/name).write_bytes(raw)
sha=hashlib.sha256(raw).hexdigest()

validation={
    "version":VERSION,
    "baseVersion":"1.0.4",
    "payload":name,
    "payloadSha256":sha,
    "requirements":{
        "batchImportFunctionPresent":"function Import-MultipleImages" in patcher,
        "multiselectEnabled":"$dlg.Multiselect = $true" in patcher,
        "usesExistingLibraryRecordPath":"Add-LibraryRecord" in patcher and "Copy-Or-Move-IntoVault" in patcher,
        "sharedExistingMetadataControls":all(x in patcher for x in ["$cmbSinglePosition.Text","$cmbSingleCoverType.Text","$txtSingleProject.Text","$txtSingleShip.Text","$txtSingleFandom.Text","$txtSingleTags.Text"]),
        "keepsOriginalBatchFiles":"Copy-Or-Move-IntoVault $source $false" in patcher,
        "batchButtonPresent":"IMPORT MULTIPLE IMAGES" in patcher,
        "splitScreenCumulative":"SPLIT SCREEN HARDENING v1.0.4" in patcher,
        "rollbackPreserved":"The previous app version was restored." in patcher,
        "allInternalHashesVerified":all(hashlib.sha256(base64.b64decode(f["contentBase64"])).hexdigest()==f["sha256"] for f in files)
    }
}
if not all(validation["requirements"].values()):
    raise SystemExit(validation)

(TF/"batch-import-1.0.5-validation.json").write_text(json.dumps(validation,indent=2),encoding="utf-8")
vd=ROOT/".library-v105-validation"
vd.mkdir(exist_ok=True)
(vd/"CoverVault.ps1").write_bytes(base64.b64decode(files[0]["contentBase64"]))
print(json.dumps(validation,indent=2))
