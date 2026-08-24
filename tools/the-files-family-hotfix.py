from pathlib import Path

builder = Path(__file__).resolve().with_name('the-files-family-build.py')
src = builder.read_text(encoding='utf-8')

# 1) Avoid PowerShell function-name collision between rendering an entry and adding one.
old = "function Add-FamilyEntry([System.Windows.Forms.Panel]$page,[string]$DataKey,[int]$Index,[string]$Kind,[int]$Y){"
new = "function Render-FamilyEntry([System.Windows.Forms.Panel]$page,[string]$DataKey,[int]$Index,[string]$Kind,[int]$Y){"
if old not in src:
    raise RuntimeError('Render-entry function signature not found')
src = src.replace(old, new, 1)
old_call = "for($i=0;$i -lt $items.Count;$i++){$dh=Add-FamilyEntry $page $DataKey $i $Kind $Y;$Y+=$dh;$used+=$dh}"
new_call = "for($i=0;$i -lt $items.Count;$i++){$dh=Render-FamilyEntry $page $DataKey $i $Kind $Y;$Y+=$dh;$used+=$dh}"
if old_call not in src:
    raise RuntimeError('Render-entry call site not found')
src = src.replace(old_call, new_call, 1)

# 2) Preserve legacy free-text Siblings/Children/Other Family values by importing them into Notes.
old = "try{$obj=$raw|ConvertFrom-Json;if($null -eq $obj){return @()};return @($obj)}catch{return @()}"
new = """try{$obj=$raw|ConvertFrom-Json;if($null -eq $obj){return @()};return @($obj)}catch{
        if($Key -eq 'Siblings'){return @([pscustomobject]@{Name='';Gender='';SiblingType='';AgeRelationship='';Status='';Occupation='';RelationshipDynamic='';Notes=$raw})}
        if($Key -eq 'Children'){return @([pscustomobject]@{Name='';Gender='';ChildType='';AgeLifeStage='';Status='';Occupation='';OtherParent='';RelationshipDynamic='';Notes=$raw})}
        if($Key -eq 'OtherFamily'){return @([pscustomobject]@{Name='';Gender='';Relationship='';Status='';Occupation='';RelationshipDynamic='';Importance='';Notes=$raw})}
        return @()
    }"""
if old not in src:
    raise RuntimeError('Legacy family-array migration hook not found')
src = src.replace(old, new, 1)

# 3) Preserve legacy free-text Important Family History as Other / Custom notes.
old = "try{$o=$raw|ConvertFrom-Json;foreach($p in @($o.PSObject.Properties)){$m[[string]$p.Name]=[string]$p.Value}}catch{}"
new = "try{$o=$raw|ConvertFrom-Json;foreach($p in @($o.PSObject.Properties)){$m[[string]$p.Name]=[string]$p.Value}}catch{$m['Other / Custom']=$raw}"
if old not in src:
    raise RuntimeError('Legacy family-history migration hook not found')
src = src.replace(old, new, 1)

# 4) Keep multi-select menus open while selecting several Relationship Dynamic values.
old = "$menu=New-Object System.Windows.Forms.ContextMenuStrip;$menu.ShowCheckMargin=$true;$selected=@(Split-MultiChoiceValue $value);foreach($opt in @($Def.Options))"
new = "$menu=New-Object System.Windows.Forms.ContextMenuStrip;$menu.ShowCheckMargin=$true;$menu.Add_Closing({param($s,$e);if($e.CloseReason -eq [System.Windows.Forms.ToolStripDropDownCloseReason]::ItemClicked){$e.Cancel=$true}});$selected=@(Split-MultiChoiceValue $value);foreach($opt in @($Def.Options))"
if old not in src:
    raise RuntimeError('Entry multi-select menu hook not found')
src = src.replace(old, new, 1)
old = "$menu=New-Object System.Windows.Forms.ContextMenuStrip;$menu.ShowCheckMargin=$true;foreach($opt in $script:FamilyHistoryOptions)"
new = "$menu=New-Object System.Windows.Forms.ContextMenuStrip;$menu.ShowCheckMargin=$true;$menu.Add_Closing({param($s,$e);if($e.CloseReason -eq [System.Windows.Forms.ToolStripDropDownCloseReason]::ItemClicked){$e.Cancel=$true}});foreach($opt in $script:FamilyHistoryOptions)"
if old not in src:
    raise RuntimeError('Family-history multi-select menu hook not found')
src = src.replace(old, new, 1)

# 5) Fix static PowerShell parser invocation. Use an actual .ps1 file with a named Path parameter.
old = """        check = r'''param($p);$t=$null;$e=$null;[System.Management.Automation.Language.Parser]::ParseFile($p,[ref]$t,[ref]$e)|Out-Null;if($e.Count){$e|ForEach-Object{Write-Error $_.Message};exit 1}'''
        for path in (cpath,lpath):
            subprocess.run([pwsh,'-NoProfile','-Command',check,'-p',str(path)],check=True)"""
new = """        parser=Path(td)/'parse.ps1'
        parser.write_text(\"param([string]$Path)`n$t=$null;$e=$null;[System.Management.Automation.Language.Parser]::ParseFile($Path,[ref]$t,[ref]$e)|Out-Null;if($e.Count){$e|ForEach-Object{Write-Error $_.Message};exit 1}`n\",encoding='utf-8')
        for path in (cpath,lpath):
            subprocess.run([pwsh,'-NoProfile','-File',str(parser),'-Path',str(path)],check=True)"""
if old not in src:
    raise RuntimeError('PowerShell parser invocation block not found')
src = src.replace(old, new, 1)

# Execute the corrected builder without mutating the source file in the checkout.
ns = {'__name__':'__main__','__file__':str(builder)}
exec(compile(src, str(builder), 'exec'), ns, ns)
