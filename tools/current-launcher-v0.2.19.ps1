# The Files bootstrap loader — v0.2.16
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $MyInvocation.MyCommand.Path
$versionPath=Join-Path $root 'AppVersion.json'
$manifestUrl='https://raw.githubusercontent.com/VeyrStudio/DesktopAppUpdates/main/the-files/manifest.json'
$packed=Join-Path $root 'TheFilesCore.ps1.gz'
$corePath=Join-Path $root 'TheFilesCore.ps1'
$outerRoot=Split-Path -Parent $root
$backupRoot=Join-Path $outerRoot 'UpdateBackups'
function FileHash([string]$p){return ((Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash).ToLowerInvariant()}
function LocalVersion{try{if(Test-Path -LiteralPath $versionPath){$v=Get-Content -LiteralPath $versionPath -Raw -Encoding UTF8|ConvertFrom-Json;if($v.version){return [version][string]$v.version}}}catch{};return [version]'0.0.0'}
function WarnUpdate([string]$m){try{Add-Type -AssemblyName System.Windows.Forms;[System.Windows.Forms.MessageBox]::Show($m,'The Files Update',[System.Windows.Forms.MessageBoxButtons]::OK,[System.Windows.Forms.MessageBoxIcon]::Warning)|Out-Null}catch{}}
function SafeRel([string]$p){if([string]::IsNullOrWhiteSpace($p)){return $false};if([IO.Path]::IsPathRooted($p)){return $false};if($p -match '(^|[\\/])\.\.([\\/]|$)'){return $false};return $true}
function Install-Update{
    if($env:THEFILES_BOOTSTRAP_RELAUNCH -eq '1'){$env:THEFILES_BOOTSTRAP_RELAUNCH=$null;return $false}
    $temp=Join-Path ([IO.Path]::GetTempPath()) ('TheFiles-'+[guid]::NewGuid().ToString('N'));New-Item -ItemType Directory -Force -Path $temp|Out-Null
    try{
        $mf=Join-Path $temp 'manifest.json';Invoke-WebRequest -Uri $manifestUrl -OutFile $mf -UseBasicParsing -Headers @{'Cache-Control'='no-cache'};$m=Get-Content -LiteralPath $mf -Raw -Encoding UTF8|ConvertFrom-Json
        $remote=[version][string]$m.version;$local=LocalVersion;if($remote -le $local){return $false}
        if(-not $m.payloadParts -or -not $m.payloadSha256){throw 'Update manifest is incomplete.'}
        $payloadFile=Join-Path $temp 'payload.json';$out=[IO.File]::Create($payloadFile)
        try{$i=0;foreach($part in @($m.payloadParts)){$i++;$pf=Join-Path $temp ('part-'+$i+'.txt');Invoke-WebRequest -Uri ([string]$part.url) -OutFile $pf -UseBasicParsing -Headers @{'Cache-Control'='no-cache'};if((FileHash $pf) -ne ([string]$part.sha256).ToLowerInvariant()){throw "Update part $i failed SHA-256 verification."};$inp=[IO.File]::OpenRead($pf);try{$inp.CopyTo($out)}finally{$inp.Dispose()}}}finally{$out.Dispose()}
        if((FileHash $payloadFile) -ne ([string]$m.payloadSha256).ToLowerInvariant()){throw 'Combined update package failed SHA-256 verification.'}
        $p=Get-Content -LiteralPath $payloadFile -Raw -Encoding UTF8|ConvertFrom-Json;if([string]$p.appId -ne 'the-files'){throw 'Update belongs to a different app.'};if([version][string]$p.version -ne $remote){throw 'Payload version does not match manifest.'}
        $stage=Join-Path $temp 'stage';New-Item -ItemType Directory -Force -Path $stage|Out-Null
        foreach($f in @($p.files)){$rel=[string]$f.path;if(-not (SafeRel $rel)){throw "Unsafe update path: $rel"};$bytes=[Convert]::FromBase64String([string]$f.contentBase64);$sha=[Security.Cryptography.SHA256]::Create();try{$got=([BitConverter]::ToString($sha.ComputeHash($bytes))).Replace('-','').ToLowerInvariant()}finally{$sha.Dispose()};if($got -ne ([string]$f.sha256).ToLowerInvariant()){throw "Internal file verification failed: $rel"};$dest=Join-Path $stage $rel;$par=Split-Path -Parent $dest;if($par){New-Item -ItemType Directory -Force -Path $par|Out-Null};[IO.File]::WriteAllBytes($dest,$bytes)}
        $backup=Join-Path $backupRoot ((Get-Date -Format 'yyyyMMdd-HHmmss')+'-'+$local.ToString());New-Item -ItemType Directory -Force -Path $backup|Out-Null
        $applied=New-Object System.Collections.Generic.List[string]
        try{foreach($f in @($p.files)){$rel=[string]$f.path;$dest=Join-Path $root $rel;if(Test-Path -LiteralPath $dest){$bd=Join-Path $backup $rel;$bp=Split-Path -Parent $bd;if($bp){New-Item -ItemType Directory -Force -Path $bp|Out-Null};Copy-Item -LiteralPath $dest -Destination $bd -Force};$par=Split-Path -Parent $dest;if($par){New-Item -ItemType Directory -Force -Path $par|Out-Null};Copy-Item -LiteralPath (Join-Path $stage $rel) -Destination $dest -Force;[void]$applied.Add($rel)}}catch{foreach($rel in @($applied)){$dest=Join-Path $root $rel;$bd=Join-Path $backup $rel;if(Test-Path -LiteralPath $bd){Copy-Item -LiteralPath $bd -Destination $dest -Force}else{Remove-Item -LiteralPath $dest -Force -ErrorAction SilentlyContinue}};throw}
        $env:THEFILES_BOOTSTRAP_RELAUNCH='1';Start-Process powershell.exe -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File',('"'+(Join-Path $root 'TheFiles.ps1')+'"'));return $true
    }catch{WarnUpdate ('The update could not be installed. The current working version will open instead.`r`n`r`n'+$_.Exception.Message);return $false}finally{Remove-Item -LiteralPath $temp -Recurse -Force -ErrorAction SilentlyContinue}
}
if(Install-Update){exit}
try{
    if(Test-Path -LiteralPath $packed){Add-Type -AssemblyName System.IO.Compression;$src=[IO.File]::OpenRead($packed);try{$gz=New-Object IO.Compression.GzipStream($src,[IO.Compression.CompressionMode]::Decompress);try{$dst=[IO.File]::Create($corePath);try{$gz.CopyTo($dst)}finally{$dst.Dispose()}}finally{$gz.Dispose()}}finally{$src.Dispose()}}elseif(-not (Test-Path -LiteralPath $corePath)){throw 'The Files core package is missing.'}
    & $corePath
}catch{try{Add-Type -AssemblyName System.Windows.Forms;[System.Windows.Forms.MessageBox]::Show(('The Files could not start.`r`n`r`n'+$_.Exception.Message),'The Files',[System.Windows.Forms.MessageBoxButtons]::OK,[System.Windows.Forms.MessageBoxIcon]::Error)|Out-Null}catch{};exit 1}
