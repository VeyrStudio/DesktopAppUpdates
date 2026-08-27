from pathlib import Path
import re

root=Path(__file__).resolve().parents[1]
v108=(root/"tools/the-library-multi-loader-fix-v108.py").read_text(encoding="utf-8")
v110=(root/"tools/the-library-batch-image-loader-safe-v110.py").read_text(encoding="utf-8")

fm=re.search(r"feature=@'\n(.*?)\n'@",v108,re.S)
hm=re.search(r"helper=@'\n(.*?)\n'@",v110,re.S)
if not fm or not hm:
    raise SystemExit("Could not extract Library batch feature/helper")
feature=fm.group(1).replace("$bitmap=Load-ImageUnlocked $path","$bitmap=Load-InlineBatchImageSafe $path")
helper=hm.group(1)

harness=r'''$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$form=New-Object Windows.Forms.Form
$form.Size=New-Object Drawing.Size(1300,1000)
$tabSplit=New-Object Windows.Forms.TabPage
$tabSplit.Size=New-Object Drawing.Size(1200,900)
$form.Controls.Add($tabSplit)

function Add-LibraryRecord { param($OriginalName,$StoredName,$Position,$Project,$Ship,$Fandom,$Tags) }
function Copy-Or-Move-IntoVault([string]$Path,[bool]$Move){ return [IO.Path]::GetFileName($Path) }
function Load-ImageUnlocked([string]$Path){ throw 'old loader invoked' }
function Refresh-HierarchyTree {}
function Refresh-LibraryGrid {}
$script:PendingCoverType=$null
'''

tail=r'''
$test=Join-Path $env:TEMP 'the-library-batch-runtime-test.png'
$b=New-Object Drawing.Bitmap(1800,1200,[Drawing.Imaging.PixelFormat]::Format32bppArgb)
try{
    $g=[Drawing.Graphics]::FromImage($b)
    try{
        $g.Clear([Drawing.Color]::FromArgb(255,80,20,120))
    }finally{$g.Dispose()}
    $b.Save($test,[Drawing.Imaging.ImageFormat]::Png)
}finally{$b.Dispose()}

try{
    $panel=Add-InlineBatchSplitter $test 1 1
    if($null -eq $panel){throw 'Add-InlineBatchSplitter returned null.'}
    Write-Host ('PANEL OK: '+$panel.Width+'x'+$panel.Height)
}catch{
    Write-Host 'ERROR MESSAGE:'
    Write-Host $_.Exception.Message
    Write-Host 'SCRIPT STACK:'
    Write-Host $_.ScriptStackTrace
    Write-Host 'FULL ERROR:'
    Write-Host ($_ | Out-String)
    throw
}
'''

out=root/".library-batch-runtime-test.ps1"
out.write_text(harness+"\n"+helper+"\n"+feature+"\n"+tail,encoding="utf-8-sig")
print(out)
