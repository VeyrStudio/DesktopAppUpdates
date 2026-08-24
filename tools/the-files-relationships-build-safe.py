from pathlib import Path
import base64, gzip, hashlib, json, re, shutil

ROOT = Path(__file__).resolve().parents[1]
TF = ROOT / 'the-files'
MANIFEST = TF / 'manifest.json'
VERSION = '0.2.16'
PREFIX = f'payload-{VERSION}-relationships-safe-part-'

manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
if manifest.get('version') != '0.2.15':
    raise SystemExit(f"Expected live Family base 0.2.15, found {manifest.get('version')}")
parts = []
for p in manifest['payloadParts']:
    name = p['url'].rsplit('/',1)[-1]
    b = (TF / name).read_bytes()
    got = hashlib.sha256(b).hexdigest()
    if got.lower() != str(p['sha256']).lower():
        raise SystemExit(f'Base part SHA mismatch: {name}')
    parts.append(b.decode('utf-8'))
base_text = ''.join(parts)
if hashlib.sha256(base_text.encode('utf-8')).hexdigest().lower() != str(manifest['payloadSha256']).lower():
    raise SystemExit('Base combined payload SHA mismatch')
base = json.loads(base_text)
files = {f['path']: f for f in base['files']}
if 'TheFiles.ps1' not in files or 'TheFilesCore.ps1.gz' not in files:
    raise SystemExit('Base app files missing')

launcher_bytes = base64.b64decode(files['TheFiles.ps1']['contentBase64'])
if hashlib.sha256(launcher_bytes).hexdigest() != files['TheFiles.ps1']['sha256'].lower():
    raise SystemExit('Base launcher SHA mismatch')
launcher = launcher_bytes.decode('utf-8-sig')
core_gz = base64.b64decode(files['TheFilesCore.ps1.gz']['contentBase64'])
if hashlib.sha256(core_gz).hexdigest() != files['TheFilesCore.ps1.gz']['sha256'].lower():
    raise SystemExit('Base core SHA mismatch')
core = gzip.decompress(core_gz).decode('utf-8-sig')

relationships_defs = r'''    'Relationships' = @(
        @{Key='Partner';Label='Partner / Love Interest';Type='Text'},
        @{Key='RelationshipStatus';Label='Relationship Status';Type='Choice';Options=@('Single','Dating','In a Relationship','Engaged','Married','Separated','Divorced','Widowed','Open Relationship','Polyamorous Relationship','It''s Complicated','Unknown','Other / Custom')},
        @{Key='Sexuality';Label='Sexuality';Type='Choice';Options=@('Gay / Homosexual','Lesbian','Bisexual','Asexual','Aromantic','Straight / Heterosexual','Questioning / Unsure','Unknown','Other / Custom')},
        @{Key='Friends';Label='Friends';Type='RelationshipJson'},
        @{Key='Enemies';Label='Enemies';Type='RelationshipJson'},
        @{Key='Mentors';Label='Mentors';Type='RelationshipJson'}
    )
'''
pat = re.compile(r"    'Relationships' = @\(\n.*?\n    \)\n(?=    'Skills' = @\()", re.S)
core, n = pat.subn(relationships_defs, core, count=1)
if n != 1:
    raise SystemExit(f'Relationship definitions replacement count={n}')

helper = r'''
# ---------------- RELATIONSHIPS AUDIT -----------------------------------------
$script:RelationshipStatusOptions=@('Single','Dating','In a Relationship','Engaged','Married','Separated','Divorced','Widowed','Open Relationship','Polyamorous Relationship','It''s Complicated','Unknown','Other / Custom')
$script:SexualityOptions=@('Gay / Homosexual','Lesbian','Bisexual','Asexual','Aromantic','Straight / Heterosexual','Questioning / Unsure','Unknown','Other / Custom')
$script:RelationshipGenderOptions=@('Man','Woman','Nonbinary','Genderfluid','Agender','Unknown','Other / Custom')
$script:RelationshipPersonStatusOptions=@('Alive','Dead','Missing','Estranged','Unknown','Other / Custom')
$script:RelationshipOccupationOptions=$script:FamilyOccupationOptions
$script:RelationshipDynamicOptions=$script:FamilyDynamicOptions
$script:FriendTypeOptions=@('Best Friend','Close Friend','Friend','Childhood Friend','Family Friend','Work Friend','School Friend','Online Friend','Former Friend Reconnected','Found Family','Other / Custom','Unknown')
$script:ClosenessOptions=@('Acquaintance','Casual','Moderate','Close','Very Close','Best Friend','Complicated','Distant','Estranged','Unknown')
$script:EnemyTypeOptions=@('Not a Rival / N/A','Rival','Friendly Rival','Competitive Rival','Professional Rival','Academic Rival','Athletic Rival','Romantic Rival','Rival/Love Interest','Rival Turned Enemy','Personal Enemy','Former Friend','Former Lover','Enemy/Love Interest','Enemy with Mutual Attraction','Political Enemy','Family Enemy','Nemesis','Betrayer','Other')
$script:ThreatLevelOptions=@('None','Low','Moderate','High','Severe','Extreme','Unknown')
$script:MentorTypeOptions=@('Teacher','Academic Mentor','Professional Mentor','Combat Mentor','Magic / Power Mentor','Religious / Spiritual Mentor','Life Mentor','Parental Mentor','Informal Mentor','Former Mentor','Other / Custom','Unknown')
$script:MentorshipStatusOptions=@('Active','Former','Occasional','Estranged','Ended Well','Ended Badly','Mentor Deceased','Mentor Missing','Unknown','Other / Custom')
$script:RelationshipFoldState=@{Friends=$true;Enemies=$true;Mentors=$true}
$script:RelationshipEntryFoldState=@{}

function Get-RelationshipArray([string]$Key){
    $c=Get-CurrentCharacter;if($null -eq $c){return @()}
    $raw=[string]$c.Fields[$Key];if([string]::IsNullOrWhiteSpace($raw)){return @()}
    try{$obj=$raw|ConvertFrom-Json;if($null -eq $obj){return @()};return @($obj)}catch{
        if($Key -eq 'Friends'){return @([pscustomobject]@{Name='';Gender='';FriendType='';Status='';Occupation='';RelationshipDynamic='';Closeness='';Notes=$raw})}
        if($Key -eq 'Enemies'){return @([pscustomobject]@{Name='';Gender='';EnemyType='';Status='';Occupation='';RelationshipDynamic='';ThreatLevel='';Notes=$raw})}
        if($Key -eq 'Mentors'){return @([pscustomobject]@{Name='';Gender='';MentorType='';Status='';Occupation='';RelationshipDynamic='';MentorshipStatus='';Notes=$raw})}
        return @()
    }
}
function Set-RelationshipArray([string]$Key,$Items){$c=Get-CurrentCharacter;if($null -eq $c){return};$json=ConvertTo-Json -InputObject @($Items) -Depth 8 -Compress;$c.Fields[$Key]=$json;Mark-CharacterChanged $json}
function Toggle-RelationshipFold([string]$Key){if(-not $script:RelationshipFoldState.ContainsKey($Key)){$script:RelationshipFoldState[$Key]=$false};$script:RelationshipFoldState[$Key]=-not [bool]$script:RelationshipFoldState[$Key];Render-CurrentCharacter}
function Get-RelationshipEntryFoldKey([string]$DataKey,[int]$Index){return ($DataKey+'|'+$Index)}
function Toggle-RelationshipEntryFold([string]$DataKey,[int]$Index){$k=Get-RelationshipEntryFoldKey $DataKey $Index;if(-not $script:RelationshipEntryFoldState.ContainsKey($k)){$script:RelationshipEntryFoldState[$k]=$false};$script:RelationshipEntryFoldState[$k]=-not [bool]$script:RelationshipEntryFoldState[$k];Render-CurrentCharacter}
function Add-RelationshipHeader($page,[string]$Title,[string]$StateKey,[int]$Y){$open=[bool]$script:RelationshipFoldState[$StateKey];$b=New-Object System.Windows.Forms.Button;$b.Text=if($open){'[-]  '+$Title}else{'[+]  '+$Title};$b.Tag=$StateKey;$b.Height=34;$b.Location=New-Object System.Drawing.Point(8,$Y);$b.Width=[math]::Max(190,$page.ClientSize.Width-22);$b.Anchor='Top,Left,Right';$b.TextAlign='MiddleLeft';$b.Font=New-Object System.Drawing.Font('Georgia',9,[System.Drawing.FontStyle]::Bold);$b.FlatStyle='Flat';$b.FlatAppearance.BorderColor=[System.Drawing.Color]::FromArgb(132,91,51);$b.BackColor=[System.Drawing.Color]::FromArgb(227,202,159);$b.ForeColor=$script:Ink;$b.Add_Click({Toggle-RelationshipFold ([string]$this.Tag)});$page.Controls.Add($b);return 40}
function Get-RelationshipRepeaterFields([string]$Kind){
    if($Kind -eq 'Friend'){return @(
        [pscustomobject]@{Field='Name';Label='Name';Type='Text';Options=@()},
        [pscustomobject]@{Field='Gender';Label='Gender';Type='Choice';Options=$script:RelationshipGenderOptions},
        [pscustomobject]@{Field='FriendType';Label='Friend Type';Type='Choice';Options=$script:FriendTypeOptions},
        [pscustomobject]@{Field='Status';Label='Status';Type='Choice';Options=$script:RelationshipPersonStatusOptions},
        [pscustomobject]@{Field='Occupation';Label='Occupation';Type='EditChoice';Options=$script:RelationshipOccupationOptions},
        [pscustomobject]@{Field='RelationshipDynamic';Label='Relationship Dynamic';Type='MultiChoice';Options=$script:RelationshipDynamicOptions},
        [pscustomobject]@{Field='Closeness';Label='Closeness';Type='Choice';Options=$script:ClosenessOptions},
        [pscustomobject]@{Field='Notes';Label='Notes';Type='Multi';Options=@()}
    )}
    if($Kind -eq 'Enemy'){return @(
        [pscustomobject]@{Field='Name';Label='Name';Type='Text';Options=@()},
        [pscustomobject]@{Field='Gender';Label='Gender';Type='Choice';Options=$script:RelationshipGenderOptions},
        [pscustomobject]@{Field='EnemyType';Label='Enemy Type';Type='Choice';Options=$script:EnemyTypeOptions},
        [pscustomobject]@{Field='Status';Label='Status';Type='Choice';Options=$script:RelationshipPersonStatusOptions},
        [pscustomobject]@{Field='Occupation';Label='Occupation';Type='EditChoice';Options=$script:RelationshipOccupationOptions},
        [pscustomobject]@{Field='RelationshipDynamic';Label='Relationship Dynamic';Type='MultiChoice';Options=$script:RelationshipDynamicOptions},
        [pscustomobject]@{Field='ThreatLevel';Label='Threat Level';Type='Choice';Options=$script:ThreatLevelOptions},
        [pscustomobject]@{Field='Notes';Label='Notes';Type='Multi';Options=@()}
    )}
    return @(
        [pscustomobject]@{Field='Name';Label='Name';Type='Text';Options=@()},
        [pscustomobject]@{Field='Gender';Label='Gender';Type='Choice';Options=$script:RelationshipGenderOptions},
        [pscustomobject]@{Field='MentorType';Label='Mentor Type';Type='Choice';Options=$script:MentorTypeOptions},
        [pscustomobject]@{Field='Status';Label='Status';Type='Choice';Options=$script:RelationshipPersonStatusOptions},
        [pscustomobject]@{Field='Occupation';Label='Occupation';Type='EditChoice';Options=$script:RelationshipOccupationOptions},
        [pscustomobject]@{Field='RelationshipDynamic';Label='Relationship Dynamic';Type='MultiChoice';Options=$script:RelationshipDynamicOptions},
        [pscustomobject]@{Field='MentorshipStatus';Label='Mentorship Status';Type='Choice';Options=$script:MentorshipStatusOptions},
        [pscustomobject]@{Field='Notes';Label='Notes';Type='Multi';Options=@()}
    )
}
function New-RelationshipEntry([string]$Kind){$o=[ordered]@{};foreach($d in @(Get-RelationshipRepeaterFields $Kind)){$o[[string]$d.Field]=''};return [pscustomobject]$o}
function Set-RelationshipEntryValue([string]$DataKey,[int]$Index,[string]$Field,[string]$Value){$items=@(Get-RelationshipArray $DataKey);if($Index -lt 0 -or $Index -ge $items.Count){return};$obj=$items[$Index];$obj|Add-Member -NotePropertyName $Field -NotePropertyValue $Value -Force;Set-RelationshipArray $DataKey $items}
function Relationship-EntryChanged($ctrl){if($script:Rendering){return};$t=$ctrl.Tag;if($null -eq $t){return};Set-RelationshipEntryValue ([string]$t.DataKey) ([int]$t.Index) ([string]$t.Field) ([string]$ctrl.Text)}
function Set-RelationshipEntryMultiChoice([string]$DataKey,[int]$Index,[string]$Field,[string]$Option,[bool]$Selected){$items=@(Get-RelationshipArray $DataKey);if($Index -lt 0 -or $Index -ge $items.Count){return};$cur=[string]$items[$Index].$Field;$vals=New-Object System.Collections.Generic.List[string];foreach($v in @(Split-MultiChoiceValue $cur)){[void]$vals.Add([string]$v)};if($Selected){if(-not $vals.Contains($Option)){[void]$vals.Add($Option)}}else{[void]$vals.Remove($Option)};Set-RelationshipEntryValue $DataKey $Index $Field (Join-MultiChoiceValue $vals);Render-CurrentCharacter}
function Get-RelationshipEntryRandomValue([string]$Field,[string]$Kind){
    if($Field -eq 'Name'){if($script:RandomPools.ContainsKey('FullName')){return [string](Get-Random -InputObject $script:RandomPools.FullName)};return 'Alex Morgan'}
    if($Field -eq 'Gender'){return [string](Get-Random -InputObject $script:RelationshipGenderOptions)}
    if($Field -eq 'Status'){return [string](Get-Random -InputObject $script:RelationshipPersonStatusOptions)}
    if($Field -eq 'Occupation'){return [string](Get-Random -InputObject $script:RelationshipOccupationOptions)}
    if($Field -eq 'RelationshipDynamic'){return ((Get-Random -InputObject $script:RelationshipDynamicOptions -Count (Get-Random -Minimum 1 -Maximum 4)) -join '; ')}
    if($Field -eq 'FriendType'){return [string](Get-Random -InputObject $script:FriendTypeOptions)}
    if($Field -eq 'Closeness'){return [string](Get-Random -InputObject $script:ClosenessOptions)}
    if($Field -eq 'EnemyType'){return [string](Get-Random -InputObject $script:EnemyTypeOptions)}
    if($Field -eq 'ThreatLevel'){return [string](Get-Random -InputObject $script:ThreatLevelOptions)}
    if($Field -eq 'MentorType'){return [string](Get-Random -InputObject $script:MentorTypeOptions)}
    if($Field -eq 'MentorshipStatus'){return [string](Get-Random -InputObject $script:MentorshipStatusOptions)}
    if($Field -eq 'Notes'){return [string](Get-Random -InputObject @('Their history with the character is complicated.','This relationship changes significantly over the course of the story.','They are an important influence on the character.','There is unresolved tension between them.'))}
    return ''
}
function Randomize-RelationshipEntryField($Tag){$v=Get-RelationshipEntryRandomValue ([string]$Tag.Field) ([string]$Tag.Kind);if(-not [string]::IsNullOrWhiteSpace($v)){Push-UndoState;Set-RelationshipEntryValue ([string]$Tag.DataKey) ([int]$Tag.Index) ([string]$Tag.Field) $v;Render-CurrentCharacter}}
function Get-RandomRelationshipStructuredValue([string]$Key){$kind=if($Key -eq 'Friends'){'Friend'}elseif($Key -eq 'Enemies'){'Enemy'}else{'Mentor'};$obj=New-RelationshipEntry $kind;foreach($d in @(Get-RelationshipRepeaterFields $kind)){$obj|Add-Member -NotePropertyName ([string]$d.Field) -NotePropertyValue (Get-RelationshipEntryRandomValue ([string]$d.Field) $kind) -Force};return (ConvertTo-Json -InputObject @($obj) -Depth 6 -Compress)}
function Add-RelationshipEntryField($page,[string]$DataKey,[int]$Index,[string]$Kind,$Def,[int]$Y){
    $items=@(Get-RelationshipArray $DataKey);if($Index -ge $items.Count){return 0};$obj=$items[$Index];$field=[string]$Def.Field;$type=[string]$Def.Type;$w=[math]::Max(320,$page.ClientSize.Width-26);$labelW=[math]::Min(126,[int]($w*0.32));$inputX=$labelW+28;$inputW=[math]::Max(105,$w-$inputX-48)
    $lbl=New-Object System.Windows.Forms.Label;$lbl.Text=[string]$Def.Label;$lbl.Font=$script:FontSmall;$lbl.ForeColor=$script:Ink;$lbl.Location=New-Object System.Drawing.Point(20,$Y);$lbl.Size=New-Object System.Drawing.Size($labelW,36);$page.Controls.Add($lbl)
    $tag=[pscustomobject]@{DataKey=$DataKey;Index=$Index;Field=$field;Kind=$Kind};$control=$null;$height=42;$value=[string]$obj.$field
    if($type -eq 'Choice' -or $type -eq 'EditChoice'){$control=New-Object System.Windows.Forms.ComboBox;$control.DropDownStyle=if($type -eq 'EditChoice'){'DropDown'}else{'DropDownList'};[void]$control.Items.AddRange([object[]]$Def.Options);$control.Text=$value;$control.Add_SelectedIndexChanged({Relationship-EntryChanged $this});if($type -eq 'EditChoice'){$control.Add_TextChanged({Relationship-EntryChanged $this})}}
    elseif($type -eq 'MultiChoice'){$control=New-Object System.Windows.Forms.Button;$control.Height=29;$control.FlatStyle='Flat';$control.TextAlign='MiddleLeft';$control.AutoEllipsis=$true;$control.Text=Get-MultiChoiceSummary $value;$menu=New-Object System.Windows.Forms.ContextMenuStrip;$menu.ShowCheckMargin=$true;$menu.Add_Closing({param($s,$e);if($e.CloseReason -eq [System.Windows.Forms.ToolStripDropDownCloseReason]::ItemClicked){$e.Cancel=$true}});$selected=@(Split-MultiChoiceValue $value);foreach($opt in @($Def.Options)){$mi=New-Object System.Windows.Forms.ToolStripMenuItem;$mi.Text=[string]$opt;$mi.CheckOnClick=$true;$mi.Checked=($selected -contains [string]$opt);$mi.Tag=[pscustomobject]@{DataKey=$DataKey;Index=$Index;Field=$field;Option=[string]$opt};$mi.Add_Click({$x=$this.Tag;Set-RelationshipEntryMultiChoice ([string]$x.DataKey) ([int]$x.Index) ([string]$x.Field) ([string]$x.Option) ([bool]$this.Checked)});[void]$menu.Items.Add($mi)};$control.ContextMenuStrip=$menu;$control.Add_Click({try{$this.ContextMenuStrip.Show($this,(New-Object System.Drawing.Point(0,$this.Height)))}catch{}})}
    else{$control=New-Object System.Windows.Forms.TextBox;$control.BorderStyle='FixedSingle';$control.Text=$value;if($type -eq 'Multi'){$control.Multiline=$true;$control.ScrollBars='Vertical';$control.Height=58;$height=70};$control.Add_TextChanged({Relationship-EntryChanged $this})}
    $control.Tag=$tag;$control.Location=New-Object System.Drawing.Point($inputX,($Y-3));$control.Width=$inputW;$control.Font=$script:FontSmall;$control.BackColor=[System.Drawing.Color]::FromArgb(247,233,202);$control.ForeColor=$script:Ink;$control.Anchor='Top,Left,Right';$page.Controls.Add($control);[void](Add-FamilySmallDice $page $tag ($w-36) ($Y-3) {Randomize-RelationshipEntryField $this.Tag});return $height
}
function Render-RelationshipEntry($page,[string]$DataKey,[int]$Index,[string]$Kind,[int]$Y){$items=@(Get-RelationshipArray $DataKey);if($Index -ge $items.Count){return 0};$obj=$items[$Index];$fk=Get-RelationshipEntryFoldKey $DataKey $Index;if(-not $script:RelationshipEntryFoldState.ContainsKey($fk)){$script:RelationshipEntryFoldState[$fk]=$false};$open=[bool]$script:RelationshipEntryFoldState[$fk];$name=[string]$obj.Name;if([string]::IsNullOrWhiteSpace($name)){$name="$Kind $($Index+1)"};$w=[math]::Max(320,$page.ClientSize.Width-26);$head=New-Object System.Windows.Forms.Button;$head.Text=if($open){'[-]  '+$name}else{'[+]  '+$name};$head.Tag=[pscustomobject]@{DataKey=$DataKey;Index=$Index};$head.Location=New-Object System.Drawing.Point(18,$Y);$head.Size=New-Object System.Drawing.Size([math]::Max(150,$w-86),30);$head.Anchor='Top,Left,Right';$head.TextAlign='MiddleLeft';$head.FlatStyle='Flat';$head.FlatAppearance.BorderColor=[System.Drawing.Color]::FromArgb(150,112,67);$head.BackColor=[System.Drawing.Color]::FromArgb(240,220,184);$head.ForeColor=$script:Ink;$head.Font=$script:FontSmall;$head.Add_Click({$t=$this.Tag;Toggle-RelationshipEntryFold ([string]$t.DataKey) ([int]$t.Index)});$page.Controls.Add($head);$rm=New-Object System.Windows.Forms.Button;$rm.Text='×';$rm.Tag=[pscustomobject]@{DataKey=$DataKey;Index=$Index};$rm.Location=New-Object System.Drawing.Point(($w-48),$Y);$rm.Size=New-Object System.Drawing.Size(30,30);$rm.Anchor='Top,Right';$rm.FlatStyle='Flat';$rm.ForeColor=[System.Drawing.Color]::FromArgb(145,58,43);$rm.Add_Click({Remove-RelationshipEntry $this.Tag});$page.Controls.Add($rm);$used=36;if(-not $open){return $used};$yy=$Y+38;foreach($d in @(Get-RelationshipRepeaterFields $Kind)){$dh=Add-RelationshipEntryField $page $DataKey $Index $Kind $d $yy;$yy+=$dh;$used+=$dh};return ($used+8)}
function Add-RelationshipEntryButton($page,[string]$DataKey,[string]$Kind,[int]$Y){$b=New-Object System.Windows.Forms.Button;$b.Text=('+ ADD '+$Kind.ToUpper());$b.Tag=[pscustomobject]@{DataKey=$DataKey;Kind=$Kind};$b.Location=New-Object System.Drawing.Point(18,$Y);$b.Size=New-Object System.Drawing.Size(140,29);$b.FlatStyle='Flat';$b.FlatAppearance.BorderColor=[System.Drawing.Color]::FromArgb(132,91,51);$b.BackColor=[System.Drawing.Color]::FromArgb(219,190,142);$b.ForeColor=$script:Ink;$b.Font=$script:FontSmall;$b.Add_Click({Add-RelationshipEntry $this.Tag});$page.Controls.Add($b);return 36}
function Add-RelationshipEntry($Tag){$items=New-Object System.Collections.Generic.List[object];foreach($x in @(Get-RelationshipArray ([string]$Tag.DataKey))){[void]$items.Add($x)};$obj=New-RelationshipEntry ([string]$Tag.Kind);[void]$items.Add($obj);Set-RelationshipArray ([string]$Tag.DataKey) @($items);$k=Get-RelationshipEntryFoldKey ([string]$Tag.DataKey) ($items.Count-1);$script:RelationshipEntryFoldState[$k]=$true;Render-CurrentCharacter}
function Remove-RelationshipEntry($Tag){$old=@(Get-RelationshipArray ([string]$Tag.DataKey));$new=New-Object System.Collections.Generic.List[object];for($i=0;$i -lt $old.Count;$i++){if($i -ne [int]$Tag.Index){[void]$new.Add($old[$i])}};Set-RelationshipArray ([string]$Tag.DataKey) @($new);Render-CurrentCharacter}
function Add-RelationshipRepeater($page,[string]$DataKey,[string]$Title,[string]$Kind,[int]$Y){$h=Add-RelationshipHeader $page $Title $DataKey $Y;$Y+=$h;if(-not [bool]$script:RelationshipFoldState[$DataKey]){return $h};$add=Add-RelationshipEntryButton $page $DataKey $Kind $Y;$Y+=$add;$used=$h+$add;$items=@(Get-RelationshipArray $DataKey);for($i=0;$i -lt $items.Count;$i++){$dh=Render-RelationshipEntry $page $DataKey $i $Kind $Y;$Y+=$dh;$used+=$dh};return ($used+8)}
function Render-RelationshipsSection($c,$leftHost,$rightHost){
    $defs=@($script:FieldDefs['Relationships']);$top=@('Partner','RelationshipStatus','Sexuality');$y=12
    foreach($key in $top){$d=$defs|Where-Object{$_.Key -eq $key}|Select-Object -First 1;if($null -ne $d){$h=Add-FieldControl $leftHost $d $y;$y+=$h}}
    $rb=New-Object System.Windows.Forms.Button;$rb.Text='🎲  RANDOMIZE RELATIONSHIPS';$rb.Location=New-Object System.Drawing.Point(18,$y);$rb.Size=New-Object System.Drawing.Size([math]::Max(190,$leftHost.ClientSize.Width-40),32);$rb.Anchor='Top,Left,Right';$rb.FlatStyle='Flat';$rb.FlatAppearance.BorderColor=[System.Drawing.Color]::FromArgb(132,91,51);$rb.BackColor=[System.Drawing.Color]::FromArgb(219,190,142);$rb.ForeColor=$script:Ink;$rb.Font=$script:FontSmall;$rb.Add_Click({Randomize-Section});$leftHost.Controls.Add($rb);$y+=42
    $h=Add-RelationshipRepeater $leftHost 'Friends' 'Friends' 'Friend' $y;$y+=$h
    $y=12;$h=Add-RelationshipRepeater $rightHost 'Enemies' 'Enemies' 'Enemy' $y;$y+=$h;$h=Add-RelationshipRepeater $rightHost 'Mentors' 'Mentors' 'Mentor' $y;$y+=$h
}
# ---------------- END RELATIONSHIPS AUDIT -------------------------------------
'''
anchor = "# ---------------- END FAMILY AUDIT -------------------------------------------\n\nfunction Add-FieldControl"
if anchor not in core:
    raise SystemExit('Family audit anchor missing')
core = core.replace(anchor, "# ---------------- END FAMILY AUDIT -------------------------------------------\n" + helper + "\nfunction Add-FieldControl", 1)

old_route = "        } elseif($script:CurrentSection -eq 'Family'){\n            Render-FamilySection $c $leftHost $rightHost\n        } else {"
new_route = "        } elseif($script:CurrentSection -eq 'Family'){\n            Render-FamilySection $c $leftHost $rightHost\n        } elseif($script:CurrentSection -eq 'Relationships'){\n            Render-RelationshipsSection $c $leftHost $rightHost\n        } else {"
if old_route not in core:
    raise SystemExit('Render route anchor missing')
core = core.replace(old_route, new_route, 1)

rand_anchor = "    if ($Key -eq 'MainGoal') {"
rand_insert = "    if ($Key -eq 'RelationshipStatus') { return [string](Get-Random -InputObject @('Single','Dating','In a Relationship','Engaged','Married','Separated','Divorced','Widowed','Open Relationship','Polyamorous Relationship','It''s Complicated','Unknown')) }\n    if ($Key -eq 'Sexuality') { return [string](Get-Random -InputObject @('Gay / Homosexual','Lesbian','Bisexual','Asexual','Aromantic','Straight / Heterosexual','Questioning / Unsure','Unknown')) }\n    if ($Key -eq 'Partner') { if($script:RandomPools.ContainsKey('FullName')){return [string](Get-Random -InputObject $script:RandomPools.FullName)} }\n    if ($Key -eq 'Friends' -or $Key -eq 'Enemies' -or $Key -eq 'Mentors') { return Get-RandomRelationshipStructuredValue $Key }\n"
if rand_anchor not in core:
    raise SystemExit('Randomization anchor missing')
core = core.replace(rand_anchor, rand_insert + rand_anchor, 1)

launcher = launcher.replace('v0.2.15', 'v0.2.16').replace('0.2.15', '0.2.16')
launcher_out = launcher.encode('utf-8-sig')
core_out = gzip.compress(core.encode('utf-8-sig'), compresslevel=9, mtime=0)
app_version = json.dumps({
    'appId':'the-files','appName':'The Files','version':VERSION,
    'manifestUrl':'https://raw.githubusercontent.com/VeyrStudio/DesktopAppUpdates/main/the-files/manifest.json'
}, indent=2).encode('utf-8') + b'\n'

out_files = []
for path, data in [('TheFiles.ps1',launcher_out),('TheFilesCore.ps1.gz',core_out),('AppVersion.json',app_version)]:
    out_files.append({'path':path,'sha256':hashlib.sha256(data).hexdigest(),'contentBase64':base64.b64encode(data).decode('ascii')})
payload = {'schemaVersion':1,'appId':'the-files','appName':'The Files','version':VERSION,'files':out_files,'delete':[]}
payload_text = json.dumps(payload, ensure_ascii=False, separators=(',',':'))
payload_bytes = payload_text.encode('utf-8')

# Clean only obsolete generated safe parts for this exact version; never user data.
for p in TF.glob(f'{PREFIX}*.txt'):
    p.unlink()
chunk_chars = 12000
part_info=[]
for i in range(0,len(payload_text),chunk_chars):
    chunk=payload_text[i:i+chunk_chars]
    name=f'{PREFIX}{(i//chunk_chars)+1:03d}.txt'
    b=chunk.encode('utf-8')
    (TF/name).write_bytes(b)
    part_info.append({'name':name,'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)})

required = [
 'Relationship Status','Sexuality','Gay / Homosexual','Lesbian','Bisexual','Asexual','Aromantic','Straight / Heterosexual',
 'Friends','Enemies','Mentors','Enemy Type','Threat Level','Mentor Type','Mentorship Status','Relationship Dynamic',
 'Rival','Friendly Rival','Competitive Rival','Professional Rival','Academic Rival','Athletic Rival','Romantic Rival','Rival/Love Interest',
 'Rival Turned Enemy','Personal Enemy','Former Friend','Former Lover','Enemy/Love Interest','Enemy with Mutual Attraction','Political Enemy','Family Enemy','Nemesis','Betrayer','Other','Not a Rival / N/A','RANDOMIZE RELATIONSHIPS',
 'Parent One','Parent Two','Parent Type','Adoptive Parent','Spouse','Siblings','Sibling Type','Age Relationship','Children','Child Type','Age / Life Stage','Other Parent','Other Family','Important Family History','Render-FamilySection',
 'Install-Update','payloadSha256','payloadParts','UpdateBackup','manifest.json','SHA256'
]
combined = ''.join((TF/p['name']).read_text(encoding='utf-8') for p in part_info)
if combined != payload_text:
    raise SystemExit('Generated parts do not reassemble exactly')
if json.loads(combined)['version'] != VERSION:
    raise SystemExit('Reassembled payload version invalid')
missing=[x for x in required if x not in (core+launcher)]
if missing:
    raise SystemExit('Missing required tokens: '+repr(missing))
if '-EncodedCommand' in launcher:
    raise SystemExit('Unsafe EncodedCommand handoff returned')
if any(any(bad in f['path'].lower() for bad in ['userdata','user-data','portrait','characterdata','media/']) for f in out_files):
    raise SystemExit('Payload contains forbidden user-data path')

report={
 'version':VERSION,'baseVersion':'0.2.15','combinedPayloadSha256':hashlib.sha256(payload_bytes).hexdigest(),
 'combinedPayloadBytes':len(payload_bytes),'parts':part_info,
 'internalFiles':[{'path':f['path'],'sha256':f['sha256']} for f in out_files],
 'requiredTokenCount':len(required),'missingRequiredTokens':missing,'forbiddenUserDataPaths':False,
 'encodedCommandPresent':False,'jsonRoundTrip':True,'powershellParse':'pending'
}
(TF/f'relationships-{VERSION}-build-validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
val=ROOT/'.relationship-safe-validation';shutil.rmtree(val,ignore_errors=True);val.mkdir()
(val/'TheFiles.ps1').write_bytes(launcher_out)
(val/'TheFilesCore.ps1').write_text(core,encoding='utf-8-sig')
print(json.dumps(report,indent=2))
