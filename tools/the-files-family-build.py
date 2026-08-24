from pathlib import Path
import base64, gzip, hashlib, json, os, re, shutil, subprocess, tempfile

ROOT = Path(__file__).resolve().parents[1]
TF = ROOT / 'the-files'
VERSION = '0.2.15'
PREFIX = f'payload-{VERSION}-family-rebuild-part-'

# Always rebuild from the last known-good UI core, then layer only the Family audit on top.
raw = ''.join((TF / f'payload-0.2.13-personality-background-dropdown-part-{i:03d}.txt').read_text(encoding='utf-8') for i in range(1, 8))
base_payload = json.loads(raw)
assert base_payload['appId'] == 'the-files' and base_payload['version'] == '0.2.13'
base_files = {f['path']: f for f in base_payload['files']}
core = gzip.decompress(base64.b64decode(base_files['TheFilesCore.ps1.gz']['contentBase64'])).decode('utf-8-sig')

# ---- Family field schema -----------------------------------------------------
family_block = r"""
    'Family' = @(
        @{Key='Parent1Name';Label='Parent One — Name';Type='Text'},
        @{Key='Parent1Gender';Label='Parent One — Gender';Type='Choice';Options=@('Man','Woman','Nonbinary','Genderfluid','Agender','Unknown','Other / Custom')},
        @{Key='Parent1Type';Label='Parent One — Parent Type';Type='Choice';Options=@('Mother','Father','Parent','Biological Parent','Adoptive Parent','Step-Parent','Foster Parent','Guardian','Spouse','Other')},
        @{Key='Parent1Spouse';Label='Parent One — Spouse / Partner';Type='Text'},
        @{Key='Parent1Status';Label='Parent One — Status';Type='Choice';Options=@('Alive','Dead','Missing','Estranged','Unknown','Other')},
        @{Key='Parent1Occupation';Label='Parent One — Occupation';Type='EditChoice';Options=@('None / Never Employed','Student','Military','Law Enforcement','Government / Civil Service','Healthcare','Education','Research / Academia','Skilled Trade','Manual Labor','Agriculture / Farming','Hospitality / Food Service','Retail / Customer Service','Office / Administration','Business / Management','Finance','Legal','Arts / Creative','Entertainment','Media / Journalism','Technology','Science','Religious / Clergy','Security','Transportation','Caretaking / Domestic Work','Criminal / Illegal Work','Other / Custom','Unknown')},
        @{Key='Parent1Relationship';Label='Parent One — Relationship Dynamic';Type='MultiChoice';Options=@('Close','Loving','Supportive','Protective','Respectful','Warm','Complicated','Distant','Estranged','Hostile','Fearful','Abusive','Neglectful','Controlling','Dependent','Codependent','Formal','Awkward','Grieving','Reconnecting','Unknown','Other / Custom')},
        @{Key='Parent1Notes';Label='Parent One — Notes';Type='Multi'},
        @{Key='Parent2Name';Label='Parent Two — Name';Type='Text'},
        @{Key='Parent2Gender';Label='Parent Two — Gender';Type='Choice';Options=@('Man','Woman','Nonbinary','Genderfluid','Agender','Unknown','Other / Custom')},
        @{Key='Parent2Type';Label='Parent Two — Parent Type';Type='Choice';Options=@('Mother','Father','Parent','Biological Parent','Adoptive Parent','Step-Parent','Foster Parent','Guardian','Spouse','Other')},
        @{Key='Parent2Spouse';Label='Parent Two — Spouse / Partner';Type='Text'},
        @{Key='Parent2Status';Label='Parent Two — Status';Type='Choice';Options=@('Alive','Dead','Missing','Estranged','Unknown','Other')},
        @{Key='Parent2Occupation';Label='Parent Two — Occupation';Type='EditChoice';Options=@('None / Never Employed','Student','Military','Law Enforcement','Government / Civil Service','Healthcare','Education','Research / Academia','Skilled Trade','Manual Labor','Agriculture / Farming','Hospitality / Food Service','Retail / Customer Service','Office / Administration','Business / Management','Finance','Legal','Arts / Creative','Entertainment','Media / Journalism','Technology','Science','Religious / Clergy','Security','Transportation','Caretaking / Domestic Work','Criminal / Illegal Work','Other / Custom','Unknown')},
        @{Key='Parent2Relationship';Label='Parent Two — Relationship Dynamic';Type='MultiChoice';Options=@('Close','Loving','Supportive','Protective','Respectful','Warm','Complicated','Distant','Estranged','Hostile','Fearful','Abusive','Neglectful','Controlling','Dependent','Codependent','Formal','Awkward','Grieving','Reconnecting','Unknown','Other / Custom')},
        @{Key='Parent2Notes';Label='Parent Two — Notes';Type='Multi'},
        @{Key='Siblings';Label='Siblings';Type='FamilyJson'},
        @{Key='Children';Label='Children';Type='FamilyJson'},
        @{Key='OtherFamily';Label='Other Family';Type='FamilyJson'},
        @{Key='FamilyHistory';Label='Important Family History';Type='FamilyHistory'},
        @{Key='FamilyTree';Label='Family Tree / Family Structure';Type='Hidden'}
    )
""".strip('\n')

pat = re.compile(r"\n    'Family' = @\(.*?\n    \)\n    'Relationships' = @\(", re.S)
m = pat.search(core)
if not m:
    raise RuntimeError('Could not find the stable Family schema block.')
core = core[:m.start()] + '\n' + family_block + "\n    'Relationships' = @(" + core[m.end():]

# Version marker in the decompressed UI core.
core = core.replace("$script:CurrentAppVersion = '0.2.13'", f"$script:CurrentAppVersion = '{VERSION}'", 1)

family_helpers = r'''
# ---------------- FAMILY AUDIT: structured, folded, repeatable editor ----------------
if($null -eq $script:FamilyFoldState){
    $script:FamilyFoldState=@{Parent1=$false;Parent2=$false;Siblings=$false;Children=$false;OtherFamily=$false;FamilyHistory=$false}
}
if($null -eq $script:FamilyEntryFoldState){$script:FamilyEntryFoldState=@{}}
$script:FamilyGenderOptions=@('Man','Woman','Nonbinary','Genderfluid','Agender','Unknown','Other / Custom')
$script:FamilyStatusOptions=@('Alive','Dead','Missing','Estranged','Unknown','Other')
$script:FamilyOccupationOptions=@('None / Never Employed','Student','Military','Law Enforcement','Government / Civil Service','Healthcare','Education','Research / Academia','Skilled Trade','Manual Labor','Agriculture / Farming','Hospitality / Food Service','Retail / Customer Service','Office / Administration','Business / Management','Finance','Legal','Arts / Creative','Entertainment','Media / Journalism','Technology','Science','Religious / Clergy','Security','Transportation','Caretaking / Domestic Work','Criminal / Illegal Work','Other / Custom','Unknown')
$script:FamilyDynamicOptions=@('Close','Loving','Supportive','Protective','Respectful','Warm','Complicated','Distant','Estranged','Hostile','Fearful','Abusive','Neglectful','Controlling','Dependent','Codependent','Formal','Awkward','Grieving','Reconnecting','Unknown','Other / Custom')
$script:FamilyHistoryOptions=@('Adoption','Divorce / Separation','Estrangement','Death / Loss','Missing Relative','Family Secret','Abuse','Neglect','Addiction','Mental Illness','Chronic Illness','Disability','Incarceration','Crime','Poverty / Financial Hardship','Wealth / Inheritance','Immigration / Displacement','War / Conflict','Religious Conflict','Family Feud','Scandal','Supernatural Heritage','Found Family','Other / Custom')

function Get-FamilyArray([string]$Key){
    $c=Get-CurrentCharacter;if($null -eq $c){return @()}
    $raw=[string]$c.Fields[$Key];if([string]::IsNullOrWhiteSpace($raw)){return @()}
    try{$obj=$raw|ConvertFrom-Json;if($null -eq $obj){return @()};return @($obj)}catch{return @()}
}
function Set-FamilyArray([string]$Key,$Items){
    $c=Get-CurrentCharacter;if($null -eq $c){return}
    $json=ConvertTo-Json -InputObject @($Items) -Depth 8 -Compress
    $c.Fields[$Key]=$json;Mark-CharacterChanged $json
}
function Get-FamilyHistoryMap {
    $m=[ordered]@{};$c=Get-CurrentCharacter;if($null -eq $c){return $m}
    $raw=[string]$c.Fields['FamilyHistory'];if([string]::IsNullOrWhiteSpace($raw)){return $m}
    try{$o=$raw|ConvertFrom-Json;foreach($p in @($o.PSObject.Properties)){$m[[string]$p.Name]=[string]$p.Value}}catch{}
    return $m
}
function Set-FamilyHistoryMap($Map){
    $c=Get-CurrentCharacter;if($null -eq $c){return}
    $json=ConvertTo-Json -InputObject $Map -Depth 6 -Compress
    $c.Fields['FamilyHistory']=$json;Mark-CharacterChanged $json
}
function Toggle-FamilyFold([string]$Key){
    if(-not $script:FamilyFoldState.ContainsKey($Key)){$script:FamilyFoldState[$Key]=$false}
    $script:FamilyFoldState[$Key]=-not [bool]$script:FamilyFoldState[$Key];Render-CurrentCharacter
}
function Get-FamilyEntryFoldKey([string]$DataKey,[int]$Index){return ($DataKey+'|'+$Index)}
function Toggle-FamilyEntryFold([string]$DataKey,[int]$Index){
    $k=Get-FamilyEntryFoldKey $DataKey $Index
    if(-not $script:FamilyEntryFoldState.ContainsKey($k)){$script:FamilyEntryFoldState[$k]=$false}
    $script:FamilyEntryFoldState[$k]=-not [bool]$script:FamilyEntryFoldState[$k];Render-CurrentCharacter
}
function Add-FamilyHeader($page,[string]$Title,[string]$StateKey,[int]$Y){
    $open=[bool]$script:FamilyFoldState[$StateKey]
    $b=New-Object System.Windows.Forms.Button;$b.Text=if($open){'[-]  '+$Title}else{'[+]  '+$Title};$b.Tag=$StateKey;$b.Height=34;$b.Location=New-Object System.Drawing.Point(8,$Y);$b.Width=[math]::Max(190,$page.ClientSize.Width-22);$b.Anchor='Top,Left,Right';$b.TextAlign='MiddleLeft';$b.Font=New-Object System.Drawing.Font('Georgia',9,[System.Drawing.FontStyle]::Bold);$b.FlatStyle='Flat';$b.FlatAppearance.BorderColor=[System.Drawing.Color]::FromArgb(132,91,51);$b.BackColor=[System.Drawing.Color]::FromArgb(227,202,159);$b.ForeColor=$script:Ink;$b.Add_Click({Toggle-FamilyFold ([string]$this.Tag)});$page.Controls.Add($b)
    return 40
}
function Add-FamilySmallDice($page,[object]$Tag,[int]$X,[int]$Y,[scriptblock]$Handler){
    $d=New-Object System.Windows.Forms.Button;$d.Text='🎲';$d.Tag=$Tag;$d.Width=30;$d.Height=27;$d.Location=New-Object System.Drawing.Point($X,$Y);$d.Anchor='Top,Right';$d.FlatStyle='Flat';$d.FlatAppearance.BorderColor=[System.Drawing.Color]::FromArgb(146,109,65);$d.BackColor=[System.Drawing.Color]::FromArgb(227,202,159);$d.ForeColor=$script:Ink;$d.Font=New-Object System.Drawing.Font('Segoe UI Emoji',9);$d.Add_Click($Handler);$page.Controls.Add($d);$script:ToolTip.SetToolTip($d,'Randomize this field');return $d
}
function Family-DirectChanged($ctrl){
    if($script:Rendering){return};$c=Get-CurrentCharacter;if($null -eq $c){return};$key=[string]$ctrl.Tag
    $v=if($ctrl -is [System.Windows.Forms.ComboBox]){[string]$ctrl.Text}else{[string]$ctrl.Text}
    $c.Fields[$key]=$v;Mark-CharacterChanged $v
}
function Add-FamilyDirectField($page,$Def,[int]$Y){
    $key=[string]$Def.Key;$type=[string]$Def.Type;$w=[math]::Max(320,$page.ClientSize.Width-26);$labelW=[math]::Min(138,[int]($w*0.34));$inputX=$labelW+18;$inputW=[math]::Max(118,$w-$inputX-76)
    $lbl=New-Object System.Windows.Forms.Label;$lbl.Text=[string]$Def.Label;$lbl.Font=$script:FontSmall;$lbl.ForeColor=$script:Ink;$lbl.Location=New-Object System.Drawing.Point(10,$Y);$lbl.Size=New-Object System.Drawing.Size($labelW,38);$page.Controls.Add($lbl)
    $control=$null;$height=44
    if($type -eq 'Choice' -or $type -eq 'EditChoice'){
        $control=New-Object System.Windows.Forms.ComboBox;$control.DropDownStyle=if($type -eq 'EditChoice'){'DropDown'}else{'DropDownList'};[void]$control.Items.AddRange([object[]]$Def.Options);$control.Location=New-Object System.Drawing.Point($inputX,($Y-3));$control.Width=$inputW;$control.Font=$script:FontSmall;$control.Tag=$key;$control.Add_SelectedIndexChanged({Family-DirectChanged $this});if($type -eq 'EditChoice'){$control.Add_TextChanged({Family-DirectChanged $this})}
    } elseif($type -eq 'MultiChoice'){
        $control=New-Object System.Windows.Forms.Button;$control.Height=29;$control.Location=New-Object System.Drawing.Point($inputX,($Y-3));$control.Width=$inputW;$control.Font=$script:FontSmall;$control.Tag=$key;$control.FlatStyle='Flat';$control.TextAlign='MiddleLeft';$control.AutoEllipsis=$true
        $c=Get-CurrentCharacter;$value=if($null -eq $c){''}else{[string]$c.Fields[$key]};$selected=@(Split-MultiChoiceValue $value);$control.Text=Get-MultiChoiceSummary $value
        $menu=New-Object System.Windows.Forms.ContextMenuStrip;$menu.ShowCheckMargin=$true;$menu.Font=$script:FontSmall;$menu.Add_Closing({param($s,$e);if($e.CloseReason -eq [System.Windows.Forms.ToolStripDropDownCloseReason]::ItemClicked){$e.Cancel=$true}})
        foreach($opt in @($Def.Options)){$item=New-Object System.Windows.Forms.ToolStripMenuItem;$item.Text=[string]$opt;$item.CheckOnClick=$true;$item.Checked=($selected -contains [string]$opt);$item.Tag=[pscustomobject]@{Key=$key;Option=[string]$opt};$item.Add_Click({$t=$this.Tag;Set-MultiChoiceSelection ([string]$t.Key) ([string]$t.Option) ([bool]$this.Checked)});[void]$menu.Items.Add($item)}
        $control.ContextMenuStrip=$menu;$control.Add_Click({try{$this.ContextMenuStrip.Show($this,(New-Object System.Drawing.Point(0,$this.Height)))}catch{}})
    } else {
        $control=New-Object System.Windows.Forms.TextBox;$control.Location=New-Object System.Drawing.Point($inputX,($Y-3));$control.Width=$inputW;$control.Font=$script:FontSmall;$control.Tag=$key;$control.BorderStyle='FixedSingle';if($type -eq 'Multi'){$control.Multiline=$true;$control.ScrollBars='Vertical';$control.Height=62;$height=76};$control.Add_TextChanged({Family-DirectChanged $this})
    }
    $control.BackColor=[System.Drawing.Color]::FromArgb(247,233,202);$control.ForeColor=$script:Ink;$control.Anchor='Top,Left,Right';$page.Controls.Add($control);$script:FieldControls[$key]=$control
    [void](Add-FamilySmallDice $page $key ($w-68) ($Y-3) {Randomize-OneField ([string]$this.Tag)})
    $lock=New-Object System.Windows.Forms.Button;$lock.Tag=$key;$lock.Width=30;$lock.Height=27;$lock.Location=New-Object System.Drawing.Point(($w-36),($Y-3));$lock.Anchor='Top,Right';$lock.FlatStyle='Flat';$lock.FlatAppearance.BorderColor=[System.Drawing.Color]::FromArgb(146,109,65);$lock.BackColor=[System.Drawing.Color]::FromArgb(227,202,159);$lock.ForeColor=$script:Ink;$lock.Font=New-Object System.Drawing.Font('Segoe UI Emoji',9);$lock.Add_Click({Toggle-Lock ([string]$this.Tag)});$page.Controls.Add($lock)
    return $height
}
function Add-FamilyParent($page,[string]$Which,[int]$Y){
    $title=if($Which -eq 'Parent1'){'Parent One'}else{'Parent Two'};$h=Add-FamilyHeader $page $title $Which $Y;$Y+=$h;if(-not [bool]$script:FamilyFoldState[$Which]){return $h}
    $prefix=if($Which -eq 'Parent1'){'Parent1'}else{'Parent2'}
    $defs=@($script:FieldDefs['Family']|Where-Object{[string]$_.Key -like ($prefix+'*')})
    $used=$h;foreach($d in $defs){$dh=Add-FamilyDirectField $page $d $Y;$Y+=$dh;$used+=$dh};return ($used+8)
}
function Get-FamilyRepeaterFields([string]$Kind){
    if($Kind -eq 'Sibling'){
        return @(
            [pscustomobject]@{Field='Name';Label='Name';Type='Text';Options=@()},
            [pscustomobject]@{Field='Gender';Label='Gender';Type='Choice';Options=$script:FamilyGenderOptions},
            [pscustomobject]@{Field='SiblingType';Label='Sibling Type';Type='Choice';Options=@('Full Sibling','Half-Sibling','Step-Sibling','Adoptive Sibling','Foster Sibling','Chosen / Found Sibling','Unknown','Other / Custom')},
            [pscustomobject]@{Field='AgeRelationship';Label='Age Relationship';Type='Choice';Options=@('Older','Younger','Same Age / Twin','Unknown','Other / Custom')},
            [pscustomobject]@{Field='Status';Label='Status';Type='Choice';Options=$script:FamilyStatusOptions},
            [pscustomobject]@{Field='Occupation';Label='Occupation';Type='EditChoice';Options=$script:FamilyOccupationOptions},
            [pscustomobject]@{Field='RelationshipDynamic';Label='Relationship Dynamic';Type='MultiChoice';Options=$script:FamilyDynamicOptions},
            [pscustomobject]@{Field='Notes';Label='Notes';Type='Multi';Options=@()}
        )
    }
    if($Kind -eq 'Child'){
        return @(
            [pscustomobject]@{Field='Name';Label='Name';Type='Text';Options=@()},
            [pscustomobject]@{Field='Gender';Label='Gender';Type='Choice';Options=$script:FamilyGenderOptions},
            [pscustomobject]@{Field='ChildType';Label='Child Type';Type='Choice';Options=@('Biological Child','Adopted Child','Stepchild','Foster Child','Ward / Dependent','Chosen / Found Family','Unknown','Other / Custom')},
            [pscustomobject]@{Field='AgeLifeStage';Label='Age / Life Stage';Type='Choice';Options=@('Infant','Child','Preteen','Teenager','Young Adult','Adult','Middle-Aged','Older Adult','Deceased','Unknown','Other / Custom')},
            [pscustomobject]@{Field='Status';Label='Status';Type='Choice';Options=$script:FamilyStatusOptions},
            [pscustomobject]@{Field='Occupation';Label='Occupation';Type='EditChoice';Options=$script:FamilyOccupationOptions},
            [pscustomobject]@{Field='OtherParent';Label='Other Parent';Type='Text';Options=@()},
            [pscustomobject]@{Field='RelationshipDynamic';Label='Relationship Dynamic';Type='MultiChoice';Options=$script:FamilyDynamicOptions},
            [pscustomobject]@{Field='Notes';Label='Notes';Type='Multi';Options=@()}
        )
    }
    return @(
        [pscustomobject]@{Field='Name';Label='Name';Type='Text';Options=@()},
        [pscustomobject]@{Field='Gender';Label='Gender';Type='Choice';Options=$script:FamilyGenderOptions},
        [pscustomobject]@{Field='Relationship';Label='Relationship';Type='Choice';Options=@('Grandparent','Grandchild','Aunt / Uncle','Niece / Nephew','Cousin','In-Law','Guardian','Godparent','Chosen / Found Family','Distant Relative','Unknown','Other / Custom')},
        [pscustomobject]@{Field='Status';Label='Status';Type='Choice';Options=$script:FamilyStatusOptions},
        [pscustomobject]@{Field='Occupation';Label='Occupation';Type='EditChoice';Options=$script:FamilyOccupationOptions},
        [pscustomobject]@{Field='RelationshipDynamic';Label='Relationship Dynamic';Type='MultiChoice';Options=$script:FamilyDynamicOptions},
        [pscustomobject]@{Field='Importance';Label='Importance';Type='Choice';Options=@('Minor','Moderate','Important','Very Important','Central','Unknown')},
        [pscustomobject]@{Field='Notes';Label='Notes';Type='Multi';Options=@()}
    )
}
function New-FamilyEntry([string]$Kind){
    $o=[ordered]@{};foreach($d in @(Get-FamilyRepeaterFields $Kind)){$o[[string]$d.Field]=''};return [pscustomobject]$o
}
function Set-FamilyEntryValue([string]$DataKey,[int]$Index,[string]$Field,[string]$Value){
    $items=@(Get-FamilyArray $DataKey);if($Index -lt 0 -or $Index -ge $items.Count){return};$obj=$items[$Index];$obj|Add-Member -NotePropertyName $Field -NotePropertyValue $Value -Force;Set-FamilyArray $DataKey $items
}
function Family-EntryChanged($ctrl){
    if($script:Rendering){return};$t=$ctrl.Tag;if($null -eq $t){return};Set-FamilyEntryValue ([string]$t.DataKey) ([int]$t.Index) ([string]$t.Field) ([string]$ctrl.Text)
}
function Set-FamilyEntryMultiChoice([string]$DataKey,[int]$Index,[string]$Field,[string]$Option,[bool]$Selected){
    $items=@(Get-FamilyArray $DataKey);if($Index -lt 0 -or $Index -ge $items.Count){return};$cur=[string]$items[$Index].$Field;$vals=New-Object System.Collections.Generic.List[string];foreach($v in @(Split-MultiChoiceValue $cur)){[void]$vals.Add([string]$v)};if($Selected){if(-not $vals.Contains($Option)){[void]$vals.Add($Option)}}else{[void]$vals.Remove($Option)};Set-FamilyEntryValue $DataKey $Index $Field (Join-MultiChoiceValue $vals);Render-CurrentCharacter
}
function Add-FamilyEntryField($page,[string]$DataKey,[int]$Index,[string]$Kind,$Def,[int]$Y){
    $items=@(Get-FamilyArray $DataKey);if($Index -ge $items.Count){return 0};$obj=$items[$Index];$field=[string]$Def.Field;$type=[string]$Def.Type;$w=[math]::Max(320,$page.ClientSize.Width-26);$labelW=[math]::Min(126,[int]($w*0.32));$inputX=$labelW+28;$inputW=[math]::Max(105,$w-$inputX-48)
    $lbl=New-Object System.Windows.Forms.Label;$lbl.Text=[string]$Def.Label;$lbl.Font=$script:FontSmall;$lbl.ForeColor=$script:Ink;$lbl.Location=New-Object System.Drawing.Point(20,$Y);$lbl.Size=New-Object System.Drawing.Size($labelW,36);$page.Controls.Add($lbl)
    $tag=[pscustomobject]@{DataKey=$DataKey;Index=$Index;Field=$field;Kind=$Kind};$control=$null;$height=42;$value=[string]$obj.$field
    if($type -eq 'Choice' -or $type -eq 'EditChoice'){
        $control=New-Object System.Windows.Forms.ComboBox;$control.DropDownStyle=if($type -eq 'EditChoice'){'DropDown'}else{'DropDownList'};[void]$control.Items.AddRange([object[]]$Def.Options);$control.Text=$value;$control.Add_SelectedIndexChanged({Family-EntryChanged $this});if($type -eq 'EditChoice'){$control.Add_TextChanged({Family-EntryChanged $this})}
    } elseif($type -eq 'MultiChoice'){
        $control=New-Object System.Windows.Forms.Button;$control.Height=29;$control.FlatStyle='Flat';$control.TextAlign='MiddleLeft';$control.AutoEllipsis=$true;$control.Text=Get-MultiChoiceSummary $value;$menu=New-Object System.Windows.Forms.ContextMenuStrip;$menu.ShowCheckMargin=$true;$selected=@(Split-MultiChoiceValue $value);foreach($opt in @($Def.Options)){$mi=New-Object System.Windows.Forms.ToolStripMenuItem;$mi.Text=[string]$opt;$mi.CheckOnClick=$true;$mi.Checked=($selected -contains [string]$opt);$mi.Tag=[pscustomobject]@{DataKey=$DataKey;Index=$Index;Field=$field;Option=[string]$opt};$mi.Add_Click({$x=$this.Tag;Set-FamilyEntryMultiChoice ([string]$x.DataKey) ([int]$x.Index) ([string]$x.Field) ([string]$x.Option) ([bool]$this.Checked)});[void]$menu.Items.Add($mi)};$control.ContextMenuStrip=$menu;$control.Add_Click({try{$this.ContextMenuStrip.Show($this,(New-Object System.Drawing.Point(0,$this.Height)))}catch{}})
    } else {
        $control=New-Object System.Windows.Forms.TextBox;$control.BorderStyle='FixedSingle';$control.Text=$value;if($type -eq 'Multi'){$control.Multiline=$true;$control.ScrollBars='Vertical';$control.Height=58;$height=70};$control.Add_TextChanged({Family-EntryChanged $this})
    }
    $control.Tag=$tag;$control.Location=New-Object System.Drawing.Point($inputX,($Y-3));$control.Width=$inputW;$control.Font=$script:FontSmall;$control.BackColor=[System.Drawing.Color]::FromArgb(247,233,202);$control.ForeColor=$script:Ink;$control.Anchor='Top,Left,Right';$page.Controls.Add($control)
    [void](Add-FamilySmallDice $page $tag ($w-36) ($Y-3) {Randomize-FamilyEntryField $this.Tag})
    return $height
}
function Add-FamilyEntry([System.Windows.Forms.Panel]$page,[string]$DataKey,[int]$Index,[string]$Kind,[int]$Y){
    $items=@(Get-FamilyArray $DataKey);if($Index -ge $items.Count){return 0};$obj=$items[$Index];$fk=Get-FamilyEntryFoldKey $DataKey $Index;if(-not $script:FamilyEntryFoldState.ContainsKey($fk)){$script:FamilyEntryFoldState[$fk]=$false};$open=[bool]$script:FamilyEntryFoldState[$fk]
    $name=[string]$obj.Name;if([string]::IsNullOrWhiteSpace($name)){$name="$Kind $($Index+1)"}
    $w=[math]::Max(320,$page.ClientSize.Width-26);$head=New-Object System.Windows.Forms.Button;$head.Text=if($open){'[-]  '+$name}else{'[+]  '+$name};$head.Tag=[pscustomobject]@{DataKey=$DataKey;Index=$Index};$head.Location=New-Object System.Drawing.Point(18,$Y);$head.Size=New-Object System.Drawing.Size([math]::Max(150,$w-86),30);$head.Anchor='Top,Left,Right';$head.TextAlign='MiddleLeft';$head.FlatStyle='Flat';$head.FlatAppearance.BorderColor=[System.Drawing.Color]::FromArgb(150,112,67);$head.BackColor=[System.Drawing.Color]::FromArgb(240,220,184);$head.ForeColor=$script:Ink;$head.Font=$script:FontSmall;$head.Add_Click({$t=$this.Tag;Toggle-FamilyEntryFold ([string]$t.DataKey) ([int]$t.Index)});$page.Controls.Add($head)
    $rm=New-Object System.Windows.Forms.Button;$rm.Text='×';$rm.Tag=[pscustomobject]@{DataKey=$DataKey;Index=$Index};$rm.Location=New-Object System.Drawing.Point(($w-48),$Y);$rm.Size=New-Object System.Drawing.Size(30,30);$rm.Anchor='Top,Right';$rm.FlatStyle='Flat';$rm.ForeColor=[System.Drawing.Color]::FromArgb(145,58,43);$rm.Add_Click({Remove-FamilyEntry $this.Tag});$page.Controls.Add($rm)
    $used=36;if(-not $open){return $used};$yy=$Y+38;foreach($d in @(Get-FamilyRepeaterFields $Kind)){$dh=Add-FamilyEntryField $page $DataKey $Index $Kind $d $yy;$yy+=$dh;$used+=$dh};return ($used+8)
}
function Add-FamilyEntryButton($page,[string]$DataKey,[string]$Kind,[int]$Y){
    $b=New-Object System.Windows.Forms.Button;$b.Text=('+ ADD '+$Kind.ToUpper());$b.Tag=[pscustomobject]@{DataKey=$DataKey;Kind=$Kind};$b.Location=New-Object System.Drawing.Point(18,$Y);$b.Size=New-Object System.Drawing.Size(130,29);$b.FlatStyle='Flat';$b.FlatAppearance.BorderColor=[System.Drawing.Color]::FromArgb(132,91,51);$b.BackColor=[System.Drawing.Color]::FromArgb(219,190,142);$b.ForeColor=$script:Ink;$b.Font=$script:FontSmall;$b.Add_Click({Add-FamilyEntry $this.Tag});$page.Controls.Add($b);return 36
}
function Add-FamilyEntry($Tag){$items=New-Object System.Collections.Generic.List[object];foreach($x in @(Get-FamilyArray ([string]$Tag.DataKey))){[void]$items.Add($x)};$obj=New-FamilyEntry ([string]$Tag.Kind);[void]$items.Add($obj);Set-FamilyArray ([string]$Tag.DataKey) @($items);$k=Get-FamilyEntryFoldKey ([string]$Tag.DataKey) ($items.Count-1);$script:FamilyEntryFoldState[$k]=$true;Render-CurrentCharacter}
function Remove-FamilyEntry($Tag){$old=@(Get-FamilyArray ([string]$Tag.DataKey));$new=New-Object System.Collections.Generic.List[object];for($i=0;$i -lt $old.Count;$i++){if($i -ne [int]$Tag.Index){[void]$new.Add($old[$i])}};Set-FamilyArray ([string]$Tag.DataKey) @($new);Render-CurrentCharacter}
function Add-FamilyRepeater($page,[string]$DataKey,[string]$Title,[string]$Kind,[int]$Y){$h=Add-FamilyHeader $page $Title $DataKey $Y;$Y+=$h;if(-not [bool]$script:FamilyFoldState[$DataKey]){return $h};$add=Add-FamilyEntryButton $page $DataKey $Kind $Y;$Y+=$add;$used=$h+$add;$items=@(Get-FamilyArray $DataKey);for($i=0;$i -lt $items.Count;$i++){$dh=Add-FamilyEntry $page $DataKey $i $Kind $Y;$Y+=$dh;$used+=$dh};return ($used+8)}
function Set-FamilyHistorySelection([string]$Category,[bool]$Selected){$m=Get-FamilyHistoryMap;if($Selected){if(-not $m.Contains($Category)){$m[$Category]=''}}else{$m.Remove($Category)};Set-FamilyHistoryMap $m;Render-CurrentCharacter}
function Set-FamilyHistoryNote([string]$Category,[string]$Value){$m=Get-FamilyHistoryMap;if(-not $m.Contains($Category)){$m[$Category]=''};$m[$Category]=$Value;Set-FamilyHistoryMap $m}
function Randomize-FamilyHistoryCategory([string]$Category){$m=Get-FamilyHistoryMap;if(-not $m.Contains($Category)){$m[$Category]=''};$m[$Category]=[string](Get-Random -InputObject @('A defining event for this branch of the family.','Kept quiet for years and still affects current relationships.','Changed how the family relates to one another.','The full details are known by only a few relatives.'));Set-FamilyHistoryMap $m;Render-CurrentCharacter}
function Add-FamilyHistory($page,[int]$Y){
    $h=Add-FamilyHeader $page 'Important Family History' 'FamilyHistory' $Y;$Y+=$h;if(-not [bool]$script:FamilyFoldState['FamilyHistory']){return $h};$w=[math]::Max(320,$page.ClientSize.Width-26);$m=Get-FamilyHistoryMap;$btn=New-Object System.Windows.Forms.Button;$btn.Location=New-Object System.Drawing.Point(18,$Y);$btn.Size=New-Object System.Drawing.Size([math]::Max(150,$w-74),29);$btn.Anchor='Top,Left,Right';$btn.FlatStyle='Flat';$btn.TextAlign='MiddleLeft';$btn.Text=if($m.Count -eq 0){'Select family-history categories...  ▼'}else{('{0} selected  ▼' -f $m.Count)};$menu=New-Object System.Windows.Forms.ContextMenuStrip;$menu.ShowCheckMargin=$true;foreach($opt in $script:FamilyHistoryOptions){$mi=New-Object System.Windows.Forms.ToolStripMenuItem;$mi.Text=$opt;$mi.CheckOnClick=$true;$mi.Checked=$m.Contains($opt);$mi.Tag=$opt;$mi.Add_Click({Set-FamilyHistorySelection ([string]$this.Tag) ([bool]$this.Checked)});[void]$menu.Items.Add($mi)};$btn.ContextMenuStrip=$menu;$btn.Add_Click({try{$this.ContextMenuStrip.Show($this,(New-Object System.Drawing.Point(0,$this.Height)))}catch{}});$page.Controls.Add($btn);[void](Add-FamilySmallDice $page 'FamilyHistory' ($w-36) $Y {Randomize-OneField 'FamilyHistory'});$used=$h+38;$Y+=38
    foreach($cat in @($m.Keys)){$lbl=New-Object System.Windows.Forms.Label;$lbl.Text=([string]$cat+' — notes');$lbl.Location=New-Object System.Drawing.Point(20,$Y);$lbl.Size=New-Object System.Drawing.Size([math]::Max(140,$w-70),20);$lbl.Font=New-Object System.Drawing.Font('Georgia',8,[System.Drawing.FontStyle]::Bold);$lbl.ForeColor=$script:Muted;$page.Controls.Add($lbl);$tb=New-Object System.Windows.Forms.TextBox;$tb.Multiline=$true;$tb.ScrollBars='Vertical';$tb.Location=New-Object System.Drawing.Point(20,($Y+20));$tb.Size=New-Object System.Drawing.Size([math]::Max(140,$w-70),58);$tb.Anchor='Top,Left,Right';$tb.Text=[string]$m[$cat];$tb.Tag=$cat;$tb.Font=$script:FontSmall;$tb.BackColor=[System.Drawing.Color]::FromArgb(247,233,202);$tb.ForeColor=$script:Ink;$tb.Add_TextChanged({if($script:Rendering){return};Set-FamilyHistoryNote ([string]$this.Tag) ([string]$this.Text)});$page.Controls.Add($tb);[void](Add-FamilySmallDice $page $cat ($w-36) ($Y+20) {Randomize-FamilyHistoryCategory ([string]$this.Tag)});$Y+=86;$used+=86};return ($used+8)
}
function Get-FamilyEntryRandomValue([string]$Field,[string]$Kind){
    if($Field -eq 'Name' -or $Field -eq 'OtherParent'){if($script:RandomPools.ContainsKey('FullName')){return [string](Get-Random -InputObject $script:RandomPools.FullName)};return 'Alex Morgan'}
    if($Field -eq 'Gender'){return [string](Get-Random -InputObject $script:FamilyGenderOptions)}
    if($Field -eq 'Status'){return [string](Get-Random -InputObject $script:FamilyStatusOptions)}
    if($Field -eq 'Occupation'){return [string](Get-Random -InputObject $script:FamilyOccupationOptions)}
    if($Field -eq 'RelationshipDynamic'){return ((Get-Random -InputObject $script:FamilyDynamicOptions -Count (Get-Random -Minimum 1 -Maximum 4)) -join '; ')}
    if($Field -eq 'SiblingType'){return [string](Get-Random -InputObject @('Full Sibling','Half-Sibling','Step-Sibling','Adoptive Sibling','Foster Sibling','Chosen / Found Sibling'))}
    if($Field -eq 'AgeRelationship'){return [string](Get-Random -InputObject @('Older','Younger','Same Age / Twin','Unknown'))}
    if($Field -eq 'ChildType'){return [string](Get-Random -InputObject @('Biological Child','Adopted Child','Stepchild','Foster Child','Ward / Dependent','Chosen / Found Family'))}
    if($Field -eq 'AgeLifeStage'){return [string](Get-Random -InputObject @('Infant','Child','Preteen','Teenager','Young Adult','Adult','Middle-Aged','Older Adult'))}
    if($Field -eq 'Relationship'){return [string](Get-Random -InputObject @('Grandparent','Grandchild','Aunt / Uncle','Niece / Nephew','Cousin','In-Law','Guardian','Godparent','Chosen / Found Family','Distant Relative'))}
    if($Field -eq 'Importance'){return [string](Get-Random -InputObject @('Minor','Moderate','Important','Very Important','Central'))}
    if($Field -eq 'Notes'){return [string](Get-Random -InputObject @('Important to the character, but the details still need development.','Their history is complicated and changes over the course of the story.','A reliable source of support during difficult periods.','There is unresolved tension between them.'))}
    return ''
}
function Randomize-FamilyEntryField($Tag){$v=Get-FamilyEntryRandomValue ([string]$Tag.Field) ([string]$Tag.Kind);if(-not [string]::IsNullOrWhiteSpace($v)){Push-UndoState;Set-FamilyEntryValue ([string]$Tag.DataKey) ([int]$Tag.Index) ([string]$Tag.Field) $v;Render-CurrentCharacter}}
function Get-RandomFamilyStructuredValue([string]$Key){
    if($Key -eq 'FamilyHistory'){$m=[ordered]@{};$opts=Get-Random -InputObject $script:FamilyHistoryOptions -Count (Get-Random -Minimum 1 -Maximum 4);foreach($o in @($opts)){$m[[string]$o]=[string](Get-Random -InputObject @('A major event that still shapes the family.','The details are complicated and not openly discussed.','This changed several relationships in the family.'))};return (ConvertTo-Json -InputObject $m -Depth 5 -Compress)}
    $kind=if($Key -eq 'Siblings'){'Sibling'}elseif($Key -eq 'Children'){'Child'}else{'Other'};$obj=New-FamilyEntry $kind;foreach($d in @(Get-FamilyRepeaterFields $kind)){$obj|Add-Member -NotePropertyName ([string]$d.Field) -NotePropertyValue (Get-FamilyEntryRandomValue ([string]$d.Field) $kind) -Force};return (ConvertTo-Json -InputObject @($obj) -Depth 6 -Compress)
}
function Render-FamilySection($c,$leftHost,$rightHost){
    $y=12;$h=Add-FamilyParent $leftHost 'Parent1' $y;$y+=$h;$h=Add-FamilyParent $leftHost 'Parent2' $y;$y+=$h
    $y=12;$h=Add-FamilyRepeater $rightHost 'Siblings' 'Siblings' 'Sibling' $y;$y+=$h;$h=Add-FamilyRepeater $rightHost 'Children' 'Children' 'Child' $y;$y+=$h;$h=Add-FamilyRepeater $rightHost 'OtherFamily' 'Other Family' 'Other' $y;$y+=$h;$h=Add-FamilyHistory $rightHost $y;$y+=$h
}
# ---------------- END FAMILY AUDIT -------------------------------------------
'''

needle = 'function Add-FieldControl([System.Windows.Forms.Panel]$page,$def,[int]$y,[int]$height=48) {'
if needle not in core:
    raise RuntimeError('Could not locate Add-FieldControl insertion point.')
core = core.replace(needle, family_helpers + '\n' + needle, 1)

# Route only Family through the new composite renderer. Everything else remains on the stable renderer.
render_needle = "        } else {\n            $split=[math]::Ceiling($defs.Count/2);$leftDefs=@($defs|Select-Object -First $split);$rightDefs=@($defs|Select-Object -Skip $split)"
render_repl = "        } elseif($script:CurrentSection -eq 'Family'){\n            Render-FamilySection $c $leftHost $rightHost\n        } else {\n            $split=[math]::Ceiling($defs.Count/2);$leftDefs=@($defs|Select-Object -First $split);$rightDefs=@($defs|Select-Object -Skip $split)"
if render_needle not in core:
    raise RuntimeError('Could not locate Render-CurrentCharacter section split.')
core = core.replace(render_needle, render_repl, 1)

# Add randomization support for the new direct and structured Family fields.
random_needle = "    if ($Key -match 'Parent[12]Name') { return [string](Get-Random -InputObject $script:RandomPools.FullName) }"
random_repl = random_needle + r'''
    if ($Key -match '^Parent[12]Spouse$') { return [string](Get-Random -InputObject $script:RandomPools.FullName) }
    if ($Key -match '^Parent[12]Occupation$') { return [string](Get-Random -InputObject $script:FamilyOccupationOptions) }
    if ($Key -match '^Parent[12]Notes$') { return [string](Get-Random -InputObject @('Their history with the character is complicated.','A major influence on the character’s early life.','They remain an important part of the family dynamic.','The relationship changed significantly after a major family event.')) }
    if ($Key -eq 'Siblings' -or $Key -eq 'Children' -or $Key -eq 'OtherFamily' -or $Key -eq 'FamilyHistory') { return Get-RandomFamilyStructuredValue $Key }'''
if random_needle not in core:
    raise RuntimeError('Could not locate Family randomization insertion point.')
core = core.replace(random_needle, random_repl, 1)

# Clean bootstrap loader: update check happens before the UI is decompressed/executed.
loader = rf'''# The Files bootstrap loader — v{VERSION}
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $MyInvocation.MyCommand.Path
$versionPath=Join-Path $root 'AppVersion.json'
$manifestUrl='https://raw.githubusercontent.com/VeyrStudio/DesktopAppUpdates/main/the-files/manifest.json'
$packed=Join-Path $root 'TheFilesCore.ps1.gz'
$corePath=Join-Path $root 'TheFilesCore.ps1'
$outerRoot=Split-Path -Parent $root
$backupRoot=Join-Path $outerRoot 'UpdateBackups'
function FileHash([string]$p){{return ((Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash).ToLowerInvariant()}}
function LocalVersion{{try{{if(Test-Path -LiteralPath $versionPath){{$v=Get-Content -LiteralPath $versionPath -Raw -Encoding UTF8|ConvertFrom-Json;if($v.version){{return [version][string]$v.version}}}}}}catch{{}};return [version]'0.0.0'}}
function WarnUpdate([string]$m){{try{{Add-Type -AssemblyName System.Windows.Forms;[System.Windows.Forms.MessageBox]::Show($m,'The Files Update',[System.Windows.Forms.MessageBoxButtons]::OK,[System.Windows.Forms.MessageBoxIcon]::Warning)|Out-Null}}catch{{}}}}
function SafeRel([string]$p){{if([string]::IsNullOrWhiteSpace($p)){{return $false}};if([IO.Path]::IsPathRooted($p)){{return $false}};if($p -match '(^|[\\/])\.\.([\\/]|$)'){{return $false}};return $true}}
function Install-Update{{
    if($env:THEFILES_BOOTSTRAP_RELAUNCH -eq '1'){{$env:THEFILES_BOOTSTRAP_RELAUNCH=$null;return $false}}
    $temp=Join-Path ([IO.Path]::GetTempPath()) ('TheFiles-'+[guid]::NewGuid().ToString('N'));New-Item -ItemType Directory -Force -Path $temp|Out-Null
    try{{
        $mf=Join-Path $temp 'manifest.json';Invoke-WebRequest -Uri $manifestUrl -OutFile $mf -UseBasicParsing -Headers @{{'Cache-Control'='no-cache'}};$m=Get-Content -LiteralPath $mf -Raw -Encoding UTF8|ConvertFrom-Json
        $remote=[version][string]$m.version;$local=LocalVersion;if($remote -le $local){{return $false}}
        if(-not $m.payloadParts -or -not $m.payloadSha256){{throw 'Update manifest is incomplete.'}}
        $payloadFile=Join-Path $temp 'payload.json';$out=[IO.File]::Create($payloadFile)
        try{{$i=0;foreach($part in @($m.payloadParts)){{$i++;$pf=Join-Path $temp ('part-'+$i+'.txt');Invoke-WebRequest -Uri ([string]$part.url) -OutFile $pf -UseBasicParsing -Headers @{{'Cache-Control'='no-cache'}};if((FileHash $pf) -ne ([string]$part.sha256).ToLowerInvariant()){{throw "Update part $i failed SHA-256 verification."}};$inp=[IO.File]::OpenRead($pf);try{{$inp.CopyTo($out)}}finally{{$inp.Dispose()}}}}}}finally{{$out.Dispose()}}
        if((FileHash $payloadFile) -ne ([string]$m.payloadSha256).ToLowerInvariant()){{throw 'Combined update package failed SHA-256 verification.'}}
        $p=Get-Content -LiteralPath $payloadFile -Raw -Encoding UTF8|ConvertFrom-Json;if([string]$p.appId -ne 'the-files'){{throw 'Update belongs to a different app.'}};if([version][string]$p.version -ne $remote){{throw 'Payload version does not match manifest.'}}
        $stage=Join-Path $temp 'stage';New-Item -ItemType Directory -Force -Path $stage|Out-Null
        foreach($f in @($p.files)){{$rel=[string]$f.path;if(-not (SafeRel $rel)){{throw "Unsafe update path: $rel"}};$bytes=[Convert]::FromBase64String([string]$f.contentBase64);$sha=[Security.Cryptography.SHA256]::Create();try{{$got=([BitConverter]::ToString($sha.ComputeHash($bytes))).Replace('-','').ToLowerInvariant()}}finally{{$sha.Dispose()}};if($got -ne ([string]$f.sha256).ToLowerInvariant()){{throw "Internal file verification failed: $rel"}};$dest=Join-Path $stage $rel;$par=Split-Path -Parent $dest;if($par){{New-Item -ItemType Directory -Force -Path $par|Out-Null}};[IO.File]::WriteAllBytes($dest,$bytes)}}
        $backup=Join-Path $backupRoot ((Get-Date -Format 'yyyyMMdd-HHmmss')+'-'+$local.ToString());New-Item -ItemType Directory -Force -Path $backup|Out-Null
        $applied=New-Object System.Collections.Generic.List[string]
        try{{foreach($f in @($p.files)){{$rel=[string]$f.path;$dest=Join-Path $root $rel;if(Test-Path -LiteralPath $dest){{$bd=Join-Path $backup $rel;$bp=Split-Path -Parent $bd;if($bp){{New-Item -ItemType Directory -Force -Path $bp|Out-Null}};Copy-Item -LiteralPath $dest -Destination $bd -Force}};$par=Split-Path -Parent $dest;if($par){{New-Item -ItemType Directory -Force -Path $par|Out-Null}};Copy-Item -LiteralPath (Join-Path $stage $rel) -Destination $dest -Force;[void]$applied.Add($rel)}}}}catch{{foreach($rel in @($applied)){{$dest=Join-Path $root $rel;$bd=Join-Path $backup $rel;if(Test-Path -LiteralPath $bd){{Copy-Item -LiteralPath $bd -Destination $dest -Force}}else{{Remove-Item -LiteralPath $dest -Force -ErrorAction SilentlyContinue}}}};throw}}
        $env:THEFILES_BOOTSTRAP_RELAUNCH='1';Start-Process powershell.exe -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File',('"'+(Join-Path $root 'TheFiles.ps1')+'"'));return $true
    }}catch{{WarnUpdate ('The update could not be installed. The current working version will open instead.`r`n`r`n'+$_.Exception.Message);return $false}}finally{{Remove-Item -LiteralPath $temp -Recurse -Force -ErrorAction SilentlyContinue}}
}}
if(Install-Update){{exit}}
try{{
    if(Test-Path -LiteralPath $packed){{Add-Type -AssemblyName System.IO.Compression;$src=[IO.File]::OpenRead($packed);try{{$gz=New-Object IO.Compression.GzipStream($src,[IO.Compression.CompressionMode]::Decompress);try{{$dst=[IO.File]::Create($corePath);try{{$gz.CopyTo($dst)}}finally{{$dst.Dispose()}}}}finally{{$gz.Dispose()}}}}finally{{$src.Dispose()}}}}elseif(-not (Test-Path -LiteralPath $corePath)){{throw 'The Files core package is missing.'}}
    & $corePath
}}catch{{try{{Add-Type -AssemblyName System.Windows.Forms;[System.Windows.Forms.MessageBox]::Show(('The Files could not start.`r`n`r`n'+$_.Exception.Message),'The Files',[System.Windows.Forms.MessageBoxButtons]::OK,[System.Windows.Forms.MessageBoxIcon]::Error)|Out-Null}}catch{{}};exit 1}}
'''

app_version = json.dumps({
    'appId':'the-files','appName':'The Files','version':VERSION,
    'manifestUrl':'https://raw.githubusercontent.com/VeyrStudio/DesktopAppUpdates/main/the-files/manifest.json'
}, indent=2) + '\n'

# Static checks on the edited PowerShell before packaging.
assert core.count("'Family' = @(") == 1
assert "Render-FamilySection $c $leftHost $rightHost" in core
for required in ['Parent1Gender','Parent2Gender','Adoptive Parent','Siblings','Children','OtherFamily','FamilyHistory','RelationshipDynamic','AgeRelationship','AgeLifeStage','Importance','Randomize-FamilyEntryField']:
    assert required in core, required
assert "$script:DataRoot = Join-Path $env:LOCALAPPDATA 'TheFiles\\Data'" in core
assert f"$script:CurrentAppVersion = '{VERSION}'" in core

# Parse syntax with PowerShell if available on the runner (parser only; this is not Windows runtime testing).
with tempfile.TemporaryDirectory() as td:
    cpath=Path(td)/'TheFilesCore.ps1'; lpath=Path(td)/'TheFiles.ps1';cpath.write_text(core,encoding='utf-8-sig');lpath.write_text(loader,encoding='utf-8-sig')
    pwsh=shutil.which('pwsh') or shutil.which('powershell')
    if pwsh:
        check = r'''param($p);$t=$null;$e=$null;[System.Management.Automation.Language.Parser]::ParseFile($p,[ref]$t,[ref]$e)|Out-Null;if($e.Count){$e|ForEach-Object{Write-Error $_.Message};exit 1}'''
        for path in (cpath,lpath):
            subprocess.run([pwsh,'-NoProfile','-Command',check,'-p',str(path)],check=True)

core_gz = gzip.compress(core.encode('utf-8-sig'), compresslevel=9, mtime=0)
files_out = {
    'TheFiles.ps1': loader.encode('utf-8-sig'),
    'TheFilesCore.ps1.gz': core_gz,
    'AppVersion.json': app_version.encode('utf-8')
}
payload = {'schemaVersion':1,'appId':'the-files','appName':'The Files','version':VERSION,'files':[],'delete':[]}
for path,data in files_out.items():
    payload['files'].append({'path':path,'sha256':hashlib.sha256(data).hexdigest(),'contentBase64':base64.b64encode(data).decode('ascii')})

payload_text = json.dumps(payload,separators=(',',':'),ensure_ascii=True)
# Verify payload decodes exactly before splitting.
roundtrip=json.loads(payload_text);assert roundtrip['version']==VERSION
for f in roundtrip['files']:
    data=base64.b64decode(f['contentBase64']);assert hashlib.sha256(data).hexdigest()==f['sha256'];assert f['path'] in ('TheFiles.ps1','TheFilesCore.ps1.gz','AppVersion.json')
assert all('Data' not in f['path'] and 'Portrait' not in f['path'] and 'Media' not in f['path'] for f in roundtrip['files'])

# Fresh payload filenames; keep chunks small and deterministic.
for old in TF.glob(PREFIX+'*.txt'):
    old.unlink()
chunk_size=42000
parts=[payload_text[i:i+chunk_size] for i in range(0,len(payload_text),chunk_size)]
part_meta=[]
for i,text in enumerate(parts,1):
    name=f'{PREFIX}{i:03d}.txt';(TF/name).write_text(text,encoding='utf-8',newline='');sha=hashlib.sha256(text.encode('utf-8')).hexdigest();part_meta.append({'url':f'https://raw.githubusercontent.com/VeyrStudio/DesktopAppUpdates/main/the-files/{name}','sha256':sha})
combined_sha=hashlib.sha256(payload_text.encode('utf-8')).hexdigest()
# Recombine from on-disk parts and verify exact bytes/JSON.
recombined=''.join((TF/f'{PREFIX}{i:03d}.txt').read_text(encoding='utf-8') for i in range(1,len(parts)+1))
assert recombined==payload_text and hashlib.sha256(recombined.encode('utf-8')).hexdigest()==combined_sha
json.loads(recombined)

manifest={
    'schemaVersion':1,'appId':'the-files','appName':'The Files','version':VERSION,
    'payloadSha256':combined_sha,'payloadParts':part_meta,
    'notes':'Family-only cumulative rebuild from the last known-good v0.2.13 UI core, preserving the pre-UI verified bootstrap updater. Reintroduces folded Parent One/Two, repeatable Siblings/Children/Other Family, Important Family History notes, Family randomization, and preserves separate user data.'
}
(TF/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
(TF/'family-build-validation.txt').write_text(
    f'The Files {VERSION} Family rebuild validation\n'
    f'Payload parts: {len(parts)}\nPayload SHA-256: {combined_sha}\n'
    'Source UI core: stable v0.2.13\nBootstrap: pre-UI manifest/version/SHA-256 verification + backup/rollback\n'
    'Family-only schema/render route applied; non-Family section definitions preserved from stable source.\n'
    'PowerShell static parse: attempted when pwsh is available on runner.\n'
    'No Windows runtime test claimed.\nNo user-data, Media, or portrait paths included in payload.\n',encoding='utf-8')
print(f'Built The Files {VERSION}: {len(parts)} payload parts; SHA-256 {combined_sha}')
