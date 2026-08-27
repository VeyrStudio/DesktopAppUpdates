from pathlib import Path
import base64, hashlib, json, re

ROOT=Path(__file__).resolve().parents[1]
TF=ROOT/"the-library"
VERSION="1.0.20"

manifest=json.loads((TF/"manifest.json").read_text(encoding="utf-8"))
if manifest.get("version")!="1.0.19":
    raise SystemExit(f"Expected live base 1.0.19, got {manifest.get('version')}")

src=(ROOT/"tools/the-library-scroll-splitter-zoom-v118.py").read_text(encoding="utf-8")
m=re.search(r'dropin=r"""(.*?)"""\n\npatcher=r"""',src,re.S)
if not m:
    raise SystemExit("Could not extract v1.0.18 drop-in.")
dropin=m.group(1)

# Carry forward v1.0.19's simple button wording.
dropin=dropin.replace("$save.Text='SAVE BACK + SPINE + FRONT'","$save.Text='SAVE'")
dropin=dropin.replace("$btnSaveSplit.Text='SAVE BACK + SPINE + FRONT'","$btnSaveSplit.Text='SAVE'")

# Add multi-action button state.
needle="$script:RegularSplitDragWhich=''\n"
insert="$script:RegularSplitDragWhich=''\n$script:LibraryMultiSaveAllButton=$null\n$script:LibraryMultiClearAllButton=$null\n"
if needle not in dropin:
    raise SystemExit("Could not find script-state insertion point.")
dropin=dropin.replace(needle,insert,1)

# Add Save All / Clear All functions before the per-cover card builder.
anchor="function New-LibraryScrollCard([string]$Path,[int]$Ordinal,[int]$Total){"
if anchor not in dropin:
    raise SystemExit("Could not find scroll card function.")
extra=r"""function Update-LibraryMultiActionButtons {
    $states=@($script:LibraryMultiScrollStates)
    $count=$states.Count
    $unsaved=@($states|Where-Object{$null -ne $_ -and -not $_.Saved}).Count

    if($null -ne $script:LibraryMultiSaveAllButton -and -not $script:LibraryMultiSaveAllButton.IsDisposed){
        $script:LibraryMultiSaveAllButton.Visible=($count -gt 0)
        $script:LibraryMultiSaveAllButton.Enabled=($unsaved -gt 0)
    }
    if($null -ne $script:LibraryMultiClearAllButton -and -not $script:LibraryMultiClearAllButton.IsDisposed){
        $script:LibraryMultiClearAllButton.Visible=($count -gt 0)
        $script:LibraryMultiClearAllButton.Enabled=($count -gt 0)
    }
}

function Save-LibraryAllScrollCards {
    $states=@($script:LibraryMultiScrollStates)
    if($states.Count -eq 0){
        Show-Info 'There are no covers waiting to be saved.'
        return
    }

    $failures=@()
    $savedNow=0
    foreach($st in $states){
        if($null -eq $st -or $st.Saved){continue}
        try{
            Save-LibraryScrollCard $st
            $savedNow++
        }catch{
            $name=if($null -ne $st -and -not [string]::IsNullOrWhiteSpace([string]$st.Path)){[IO.Path]::GetFileName([string]$st.Path)}else{'Unknown cover'}
            $failures += ($name+': '+$_.Exception.Message)
        }
    }

    Update-LibraryMultiActionButtons

    if($failures.Count -eq 0){
        $total=$states.Count
        Close-LibraryMultiWrapScroll $true
        Show-Info ("Saved all {0} cover(s)." -f $total)
    }else{
        Show-Error (
            ("Save All saved {0} cover(s), but {1} could not be saved." -f $savedNow,$failures.Count)+
            [Environment]::NewLine+[Environment]::NewLine+
            ($failures -join [Environment]::NewLine)
        )
    }
}

function Clear-LibraryAllScrollCards([switch]$Force){
    $states=@($script:LibraryMultiScrollStates)
    if($states.Count -eq 0){return}

    if(-not $Force){
        $choice=[Windows.Forms.MessageBox]::Show(
            ("Clear all {0} cover(s) from the splitter without saving them?" -f $states.Count),
            'Clear All Covers',
            [Windows.Forms.MessageBoxButtons]::YesNo,
            [Windows.Forms.MessageBoxIcon]::Question
        )
        if($choice -ne [Windows.Forms.DialogResult]::Yes){return}
    }

    Close-LibraryMultiWrapScroll $true
}

"""
dropin=dropin.replace(anchor,extra+anchor,1)

# After a single card saves, update the Save All button state too.
old="""        $State.SaveButton.Enabled=$false
        $State.Saved=$true
"""
new="""        $State.SaveButton.Enabled=$false
        $State.Saved=$true
        Update-LibraryMultiActionButtons
"""
if old not in dropin:
    raise SystemExit("Could not find per-card save completion block.")
dropin=dropin.replace(old,new,1)

# Hide the fixed multi buttons whenever the multi-scroll area closes.
old_close="""function Close-LibraryMultiWrapScroll([bool]$RestoreRegular=$true){
    if($null -ne $script:LibraryMultiScrollHost){
"""
new_close="""function Close-LibraryMultiWrapScroll([bool]$RestoreRegular=$true){
    if($null -ne $script:LibraryMultiSaveAllButton -and -not $script:LibraryMultiSaveAllButton.IsDisposed){
        $script:LibraryMultiSaveAllButton.Visible=$false
    }
    if($null -ne $script:LibraryMultiClearAllButton -and -not $script:LibraryMultiClearAllButton.IsDisposed){
        $script:LibraryMultiClearAllButton.Visible=$false
    }

    if($null -ne $script:LibraryMultiScrollHost){
"""
if old_close not in dropin:
    raise SystemExit("Could not find Close-LibraryMultiWrapScroll.")
dropin=dropin.replace(old_close,new_close,1)

# Show action buttons after the multiple-cover states have been created.
old_states="""    $script:LibraryMultiScrollStates=@($states)

    if($states.Count -eq 0){
"""
new_states="""    $script:LibraryMultiScrollStates=@($states)
    Update-LibraryMultiActionButtons

    if($states.Count -eq 0){
"""
if old_states not in dropin:
    raise SystemExit("Could not find multi-state assignment.")
dropin=dropin.replace(old_states,new_states,1)

# Create Save All and Clear All in the fixed purple drop area.
init_anchor="""    if($null -ne $btnChooseWrap){$btnChooseWrap.Visible=$false}
    if($null -ne $lblWrapDrop){$lblWrapDrop.Text='DROP FULL COVER IMAGE(S) HERE'}
"""
init_insert="""    if($null -ne $btnChooseWrap){$btnChooseWrap.Visible=$false}

    if($null -eq $script:LibraryMultiSaveAllButton -or $script:LibraryMultiSaveAllButton.IsDisposed){
        $saveAll=New-Object Windows.Forms.Button
        $saveAll.Name='LibraryMultiSaveAll'
        $saveAll.Text='SAVE ALL'
        $saveAll.Location=New-Object Drawing.Point(830,17)
        $saveAll.Size=New-Object Drawing.Size(130,38)
        $saveAll.Visible=$false
        if($null -ne $btnSaveSplit){
            try{
                $saveAll.BackColor=$btnSaveSplit.BackColor
                $saveAll.ForeColor=$btnSaveSplit.ForeColor
                $saveAll.FlatStyle=$btnSaveSplit.FlatStyle
                $saveAll.Font=$btnSaveSplit.Font
            }catch{}
        }
        $saveAll.Add_Click({Save-LibraryAllScrollCards})
        $panelWrapDrop.Controls.Add($saveAll)
        $script:LibraryMultiSaveAllButton=$saveAll
    }

    if($null -eq $script:LibraryMultiClearAllButton -or $script:LibraryMultiClearAllButton.IsDisposed){
        $clearAll=New-Object Windows.Forms.Button
        $clearAll.Name='LibraryMultiClearAll'
        $clearAll.Text='CLEAR ALL'
        $clearAll.Location=New-Object Drawing.Point(972,17)
        $clearAll.Size=New-Object Drawing.Size(130,38)
        $clearAll.Visible=$false
        if($null -ne $btnSaveSplit){
            try{
                $clearAll.BackColor=$btnSaveSplit.BackColor
                $clearAll.ForeColor=$btnSaveSplit.ForeColor
                $clearAll.FlatStyle=$btnSaveSplit.FlatStyle
                $clearAll.Font=$btnSaveSplit.Font
            }catch{}
        }
        $clearAll.Add_Click({Clear-LibraryAllScrollCards})
        $panelWrapDrop.Controls.Add($clearAll)
        $script:LibraryMultiClearAllButton=$clearAll
    }

    if($null -ne $lblWrapDrop){$lblWrapDrop.Text='DROP FULL COVER IMAGE(S) HERE'}
"""
if init_anchor not in dropin:
    raise SystemExit("Could not find multi-button initialization point.")
dropin=dropin.replace(init_anchor,init_insert,1)

if "$save.Text='SAVE'" not in dropin or "$btnSaveSplit.Text='SAVE'" not in dropin:
    raise SystemExit("v1.0.19 Save labels were not preserved.")

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
  "version": "1.0.20",
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
            ('The Library could not install the Save All / Clear All update.'+[Environment]::NewLine+[Environment]::NewLine+$message+[Environment]::NewLine+[Environment]::NewLine+'The previous app version was restored.'),
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
name="payload-1.0.20-save-all-clear-all.txt"
(TF/name).write_bytes(raw)
sha=hashlib.sha256(raw).hexdigest()

validation={
    "version":VERSION,
    "baseVersion":"1.0.19",
    "payload":name,
    "payloadSha256":sha,
    "requirements":{
        "saveAllButton":"LibraryMultiSaveAll" in dropin and "Text='SAVE ALL'" in dropin,
        "clearAllButton":"LibraryMultiClearAll" in dropin and "Text='CLEAR ALL'" in dropin,
        "saveAllSkipsAlreadySaved":"if($null -eq $st -or $st.Saved){continue}" in dropin,
        "saveAllClosesOnSuccess":"Close-LibraryMultiWrapScroll $true" in dropin,
        "clearAllConfirmation":"'Clear All Covers'" in dropin,
        "clearAllForceForTesting":"function Clear-LibraryAllScrollCards([switch]$Force)" in dropin,
        "simpleSaveLabelsPreserved":"$save.Text='SAVE'" in dropin and "$btnSaveSplit.Text='SAVE'" in dropin,
        "allInternalHashesVerified":all(hashlib.sha256(base64.b64decode(f["contentBase64"])).hexdigest()==f["sha256"] for f in files)
    }
}
if not all(validation["requirements"].values()):
    raise SystemExit(validation)

(TF/"save-all-clear-all-1.0.20-validation.json").write_text(json.dumps(validation,indent=2),encoding="utf-8")
vd=ROOT/".library-v120-validation"
vd.mkdir(exist_ok=True)
for f in files:
    (vd/f["path"]).write_bytes(base64.b64decode(f["contentBase64"]))
print(json.dumps(validation,indent=2))
