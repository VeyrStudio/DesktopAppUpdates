from pathlib import Path
import base64, hashlib, json

ROOT = Path(__file__).resolve().parents[1]
TF = ROOT / "the-library"
VERSION = "1.0.3"

m = json.loads((TF / "manifest.json").read_text(encoding="utf-8"))
if m.get("version") != "1.0.2":
    raise SystemExit(f"Expected live base 1.0.2, got {m.get('version')}")

patcher = r"""$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Windows.Forms
$appRoot=Split-Path -Parent $PSScriptRoot
$backupDir=Join-Path $appRoot 'UpdateBackup'
$backupMain=Join-Path $backupDir 'CoverVault.ps1'
$backupVersion=Join-Path $backupDir 'AppVersion.json'
$targetMain=Join-Path $PSScriptRoot 'CoverVault.ps1'
$targetVersion=Join-Path $PSScriptRoot 'AppVersion.json'
$launcher=Join-Path $PSScriptRoot 'Launch Cover Vault.vbs'
function Relaunch-App { if(Test-Path -LiteralPath $launcher){Start-Process 'wscript.exe' -ArgumentList ('"'+$launcher+'"')} }
try{
 if(-not(Test-Path -LiteralPath $backupMain)){throw 'The updater backup is missing the previous Library app script.'}
 $text=[IO.File]::ReadAllText($backupMain,[Text.Encoding]::UTF8)
 if(-not $text.Contains('# PORTABLE LIBRARY BACKUP v1.0.3')){
  if(-not $text.Contains('$tabBackup')){throw 'Could not find The Library Backup tab.'}
  $feature=@'
# PORTABLE LIBRARY BACKUP v1.0.3
Add-Type -AssemblyName System.IO.Compression.FileSystem
$portableDataDir=Join-Path $appRoot 'Data'
$portableRestoreHelper=Join-Path $PSScriptRoot 'RestoreLibrary.ps1'

function New-LibraryPortableBackup([string]$Destination){
 if([string]::IsNullOrWhiteSpace($Destination)){return}
 if(-not(Test-Path -LiteralPath $portableDataDir)){New-Item -ItemType Directory -Force -Path $portableDataDir|Out-Null}
 $temp=Join-Path ([IO.Path]::GetTempPath()) ('TheLibraryBackup-'+[guid]::NewGuid().ToString('N'))
 try{
  $bundle=Join-Path $temp 'bundle';$bundleData=Join-Path $bundle 'Data'
  New-Item -ItemType Directory -Force -Path $bundleData|Out-Null
  Get-ChildItem -LiteralPath $portableDataDir -Force -ErrorAction SilentlyContinue|ForEach-Object{Copy-Item -LiteralPath $_.FullName -Destination $bundleData -Recurse -Force}
  [ordered]@{schemaVersion=1;appId='the-library';appName='The Library';createdAt=(Get-Date).ToString('o');includes=@('Data')}|ConvertTo-Json -Depth 4|Set-Content -LiteralPath (Join-Path $bundle 'backup-manifest.json') -Encoding UTF8
  if(Test-Path -LiteralPath $Destination){Remove-Item -LiteralPath $Destination -Force}
  [IO.Compression.ZipFile]::CreateFromDirectory($bundle,$Destination,[IO.Compression.CompressionLevel]::Optimal,$false)
 }finally{if(Test-Path -LiteralPath $temp){Remove-Item -LiteralPath $temp -Recurse -Force -ErrorAction SilentlyContinue}}
}

function Test-LibraryPortableBackup([string]$BackupPath){
 $probe=Join-Path ([IO.Path]::GetTempPath()) ('TheLibraryProbe-'+[guid]::NewGuid().ToString('N'))
 try{
  [IO.Compression.ZipFile]::ExtractToDirectory($BackupPath,$probe)
  $mp=Join-Path $probe 'backup-manifest.json';$dp=Join-Path $probe 'Data'
  if(-not(Test-Path -LiteralPath $mp)){throw 'This is not a valid The Library backup.'}
  $bm=Get-Content -LiteralPath $mp -Raw|ConvertFrom-Json
  if([string]$bm.appId -ne 'the-library'){throw 'This backup belongs to a different app.'}
  if(-not(Test-Path -LiteralPath $dp)){throw 'This Library backup does not contain its Data folder.'}
 }finally{if(Test-Path -LiteralPath $probe){Remove-Item -LiteralPath $probe -Recurse -Force -ErrorAction SilentlyContinue}}
}

$portableTitle=New-Object Windows.Forms.Label
$portableTitle.Text='PORTABLE LIBRARY BACKUP';$portableTitle.AutoSize=$true
$portableTitle.Font=New-Object Drawing.Font('Segoe UI',11,[Drawing.FontStyle]::Bold)
$portableTitle.Location=New-Object Drawing.Point(28,28);$tabBackup.Controls.Add($portableTitle)

$portableHint=New-Object Windows.Forms.Label
$portableHint.Text='Create one file containing your Library data and cover images for another PC.'
$portableHint.AutoSize=$true;$portableHint.Location=New-Object Drawing.Point(28,55);$tabBackup.Controls.Add($portableHint)

$portableBackupBtn=New-Object Windows.Forms.Button
$portableBackupBtn.Text='BACKUP LIBRARY';$portableBackupBtn.Size=New-Object Drawing.Size(155,36);$portableBackupBtn.Location=New-Object Drawing.Point(28,84)
$portableBackupBtn.Add_Click({
 try{
  $d=New-Object Windows.Forms.SaveFileDialog;$d.Filter='The Library Backup (*.librarybackup)|*.librarybackup';$d.DefaultExt='librarybackup';$d.AddExtension=$true;$d.FileName=('The Library Backup '+(Get-Date -Format 'yyyy-MM-dd')+'.librarybackup')
  if($d.ShowDialog() -eq [Windows.Forms.DialogResult]::OK){New-LibraryPortableBackup $d.FileName;[Windows.Forms.MessageBox]::Show(('Backup created successfully.'+[Environment]::NewLine+[Environment]::NewLine+$d.FileName),'The Library Backup')|Out-Null}
 }catch{[Windows.Forms.MessageBox]::Show(('Backup could not be created.'+[Environment]::NewLine+[Environment]::NewLine+$_.Exception.Message),'The Library Backup')|Out-Null}
})
$tabBackup.Controls.Add($portableBackupBtn)

$portableRestoreBtn=New-Object Windows.Forms.Button
$portableRestoreBtn.Text='RESTORE LIBRARY';$portableRestoreBtn.Size=New-Object Drawing.Size(155,36);$portableRestoreBtn.Location=New-Object Drawing.Point(195,84)
$portableRestoreBtn.Add_Click({
 try{
  $d=New-Object Windows.Forms.OpenFileDialog;$d.Filter='The Library Backup (*.librarybackup)|*.librarybackup|All files (*.*)|*.*'
  if($d.ShowDialog() -ne [Windows.Forms.DialogResult]::OK){return}
  Test-LibraryPortableBackup $d.FileName
  $q=[Windows.Forms.MessageBox]::Show('Restore this backup? Your current Library will be saved automatically first.','Restore The Library',[Windows.Forms.MessageBoxButtons]::YesNo,[Windows.Forms.MessageBoxIcon]::Question)
  if($q -ne [Windows.Forms.DialogResult]::Yes){return}
  $recoveryDir=Join-Path $appRoot 'Recovery Backups';New-Item -ItemType Directory -Force -Path $recoveryDir|Out-Null
  $recovery=Join-Path $recoveryDir ('Before Restore '+(Get-Date -Format 'yyyy-MM-dd HH-mm-ss')+'.librarybackup');New-LibraryPortableBackup $recovery
  if(-not(Test-Path -LiteralPath $portableRestoreHelper)){throw 'Restore helper is missing.'}
  $args=@('-NoProfile','-ExecutionPolicy','Bypass','-WindowStyle','Hidden','-File',('"'+$portableRestoreHelper+'"'),'-BackupPath',('"'+$d.FileName+'"'),'-DataDir',('"'+$portableDataDir+'"'),'-Launcher',('"'+(Join-Path $PSScriptRoot 'Launch Cover Vault.vbs')+'"'),'-ParentPid',[string]$PID)
  Start-Process 'powershell.exe' -ArgumentList $args -WindowStyle Hidden
  $form.Close()
 }catch{[Windows.Forms.MessageBox]::Show(('Restore could not start.'+[Environment]::NewLine+[Environment]::NewLine+$_.Exception.Message),'The Library Restore')|Out-Null}
})
$tabBackup.Controls.Add($portableRestoreBtn)
'@
  $patterns=@('(?m)^\s*\[void\]\s*\$form\.ShowDialog\(\)\s*$','(?m)^\s*\$form\.ShowDialog\(\)\s*\|\s*Out-Null\s*$','(?m)^\s*\$form\.ShowDialog\(\)\s*$')
  $match=$null
  foreach($pat in $patterns){$rx=New-Object Text.RegularExpressions.Regex($pat);$m=$rx.Match($text);if($m.Success){$match=$m;break}}
  if($null -eq $match){throw 'Could not find The Library window startup point.'}
  $text=$text.Substring(0,$match.Index)+$feature+[Environment]::NewLine+$text.Substring($match.Index)
 }
 [IO.File]::WriteAllText($targetMain,$text,(New-Object Text.UTF8Encoding($true)))
 @'
{
  "appId":"the-library",
  "appName":"The Library",
  "version":"1.0.3",
  "manifestUrl":"https://raw.githubusercontent.com/VeyrStudio/DesktopAppUpdates/main/the-library/manifest.json"
}
'@|Set-Content -LiteralPath $targetVersion -Encoding UTF8
 Relaunch-App
}catch{
 $message=$_.Exception.Message
 try{if(Test-Path -LiteralPath $backupMain){Copy-Item -LiteralPath $backupMain -Destination $targetMain -Force}}catch{}
 try{if(Test-Path -LiteralPath $backupVersion){Copy-Item -LiteralPath $backupVersion -Destination $targetVersion -Force}}catch{}
 try{[Windows.Forms.MessageBox]::Show(('The Library could not install the portable backup update.'+[Environment]::NewLine+[Environment]::NewLine+$message+[Environment]::NewLine+[Environment]::NewLine+'The previous app version was restored.'),'The Library Update')|Out-Null}catch{}
 Relaunch-App
}
"""

restore = r"""param(
 [Parameter(Mandatory=$true)][string]$BackupPath,
 [Parameter(Mandatory=$true)][string]$DataDir,
 [Parameter(Mandatory=$true)][string]$Launcher,
 [Parameter(Mandatory=$true)][int]$ParentPid
)
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.IO.Compression.FileSystem
try{
 try{Wait-Process -Id $ParentPid -Timeout 30 -ErrorAction SilentlyContinue}catch{}
 Start-Sleep -Milliseconds 500
 $tmp=Join-Path ([IO.Path]::GetTempPath()) ('TheLibraryRestore-'+[guid]::NewGuid().ToString('N'))
 try{
  [IO.Compression.ZipFile]::ExtractToDirectory($BackupPath,$tmp)
  $mp=Join-Path $tmp 'backup-manifest.json';$src=Join-Path $tmp 'Data'
  if(-not(Test-Path -LiteralPath $mp)){throw 'Backup manifest is missing.'}
  $bm=Get-Content -LiteralPath $mp -Raw|ConvertFrom-Json
  if([string]$bm.appId -ne 'the-library'){throw 'This backup belongs to a different app.'}
  if(-not(Test-Path -LiteralPath $src)){throw 'Backup Data folder is missing.'}
  if(Test-Path -LiteralPath $DataDir){Remove-Item -LiteralPath $DataDir -Recurse -Force}
  New-Item -ItemType Directory -Force -Path $DataDir|Out-Null
  Get-ChildItem -LiteralPath $src -Force|ForEach-Object{Copy-Item -LiteralPath $_.FullName -Destination $DataDir -Recurse -Force}
 }finally{if($tmp -and(Test-Path -LiteralPath $tmp)){Remove-Item -LiteralPath $tmp -Recurse -Force -ErrorAction SilentlyContinue}}
 if(Test-Path -LiteralPath $Launcher){Start-Process 'wscript.exe' -ArgumentList ('"'+$Launcher+'"')}
}catch{
 [Windows.Forms.MessageBox]::Show(('Restore failed.'+[Environment]::NewLine+[Environment]::NewLine+$_.Exception.Message),'The Library Restore')|Out-Null
}
"""

appver = json.dumps({
    "appId":"the-library",
    "appName":"The Library",
    "version":VERSION,
    "manifestUrl":"https://raw.githubusercontent.com/VeyrStudio/DesktopAppUpdates/main/the-library/manifest.json"
}, indent=2)

files=[]
for path,data in [
    ("CoverVault.ps1",patcher.encode("utf-8-sig")),
    ("RestoreLibrary.ps1",restore.encode("utf-8-sig")),
    ("AppVersion.json",appver.encode("utf-8")),
]:
    files.append({"path":path,"sha256":hashlib.sha256(data).hexdigest(),"contentBase64":base64.b64encode(data).decode("ascii")})

payload={"schemaVersion":1,"appId":"the-library","appName":"The Library","version":VERSION,"files":files,"delete":[]}
raw=json.dumps(payload,separators=(",",":")).encode("utf-8")
name="payload-1.0.3-portable-backup.txt"
(TF/name).write_bytes(raw)
sha=hashlib.sha256(raw).hexdigest()

validation={
 "version":VERSION,"baseVersion":"1.0.2","payload":name,"payloadSha256":sha,
 "requirements":{
  "portableBackupMarker":"# PORTABLE LIBRARY BACKUP v1.0.3" in patcher,
  "backsUpEntireDataFolder":"Get-ChildItem -LiteralPath $portableDataDir" in patcher,
  "backupManifestValidation":"backup-manifest.json" in patcher and "backup-manifest.json" in restore,
  "restoreCreatesRecoveryBackup":"Recovery Backups" in patcher,
  "restoreWaitsForAppExit":"Wait-Process -Id $ParentPid" in restore,
  "restoreRelaunchesApp":"wscript.exe" in restore,
  "rollbackPreserved":"previous app version was restored" in patcher,
  "allInternalHashesVerified":all(hashlib.sha256(base64.b64decode(f["contentBase64"])).hexdigest()==f["sha256"] for f in files)
 }
}
if not all(validation["requirements"].values()): raise SystemExit(validation)
(TF/"portable-backup-1.0.3-validation.json").write_text(json.dumps(validation,indent=2),encoding="utf-8")
vd=ROOT/".library-v103-validation";vd.mkdir(exist_ok=True)
(vd/"CoverVault.ps1").write_bytes(base64.b64decode(files[0]["contentBase64"]))
(vd/"RestoreLibrary.ps1").write_bytes(base64.b64decode(files[1]["contentBase64"]))
print(json.dumps(validation,indent=2))
