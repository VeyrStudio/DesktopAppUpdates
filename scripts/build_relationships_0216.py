import json,base64,gzip,hashlib,pathlib,re,subprocess,sys
ROOT=pathlib.Path('.')
OUT=ROOT/'build-out'; OUT.mkdir(exist_ok=True)
manifest=json.loads((ROOT/'the-files/manifest.json').read_text(encoding='utf-8'))
assert manifest['version']=='0.2.15', manifest['version']
payload_text=''.join((ROOT/'the-files'/p['url'].rsplit('/',1)[-1]).read_text(encoding='utf-8') for p in manifest['payloadParts'])
payload=json.loads(payload_text)
assert payload['version']=='0.2.15'
files={f['path']:f for f in payload['files']}
core=gzip.decompress(base64.b64decode(files['TheFilesCore.ps1.gz']['contentBase64'])).decode('utf-8-sig')
old_schema="""    'Relationships' = @(\n        @{Key='Partner';Label='Partner / Love Interest';Type='Text'},\n        @{Key='RelationshipStatus';Label='Relationship Status';Type='Text'},\n        @{Key='Sexuality';Label='Sexuality';Type='Text'},\n        @{Key='RomanticOrientation';Label='Romantic Orientation';Type='Text'},\n        @{Key='RomanticHistory';Label='Romantic History';Type='Large'},\n        @{Key='Attraction';Label='What Attracts Them to Someone';Type='Multi'},\n        @{Key='LoveLanguage';Label='Love Language';Type='Multi'},\n        @{Key='ShowsAffection';Label='How They Show Affection';Type='Multi'},\n        @{Key='Jealousy';Label='How They Handle Jealousy';Type='Multi'},\n        @{Key='HandlesConflict';Label='How They Handle Conflict';Type='Multi'},\n        @{Key='IntimacyNotes';Label='Intimacy Notes';Type='Large'},\n        @{Key='PartnerRelationship';Label='Relationship With Partner';Type='Large'},\n        @{Key='Friends';Label='Friends';Type='Large'},\n        @{Key='Enemies';Label='Enemies';Type='Large'},\n        @{Key='Rivals';Label='Rivals';Type='Large'},\n        @{Key='Mentors';Label='Mentors';Type='Large'},\n        @{Key='Dependents';Label='Dependents';Type='Large'},\n        @{Key='PastRelationships';Label='Important Past Relationships';Type='Large'},\n        @{Key='ImportantRelationships';Label='Other Important Relationships';Type='Large'},\n        @{Key='RelationshipNotes';Label='Relationship Notes';Type='Large'}\n    )"""
new_schema="""    'Relationships' = @(\n        @{Key='RelationshipStatus';Label='Relationship Status';Type='Choice';Options=@('Single','Dating','In a Relationship','Engaged','Married','Separated','Divorced','Widowed','It’s Complicated','Other / Custom','Unknown')},\n        @{Key='Sexuality';Label='Sexuality';Type='Choice';Options=@('Gay / Homosexual','Lesbian','Bisexual','Pansexual','Asexual','Aromantic','Straight / Heterosexual','Queer','Demisexual','Questioning','Other / Custom','Unknown')},\n        @{Key='Friends';Label='Friends';Type='RelationshipJson'},\n        @{Key='Enemies';Label='Enemies';Type='RelationshipJson'},\n        @{Key='Mentors';Label='Mentors';Type='RelationshipJson'}\n    )"""
assert old_schema in core
core=core.replace(old_schema,new_schema,1)

helper=r'''# ---------------- RELATIONSHIPS AUDIT ---------------------------------------
$script:RelationshipFoldState=@{Friends=$true;Enemies=$true;Mentors=$true}
$script:RelationshipEntryFoldState=@{}
$script:RelationshipGenderOptions=$script:FamilyGenderOptions
$script:RelationshipStatusOptions=$script:FamilyStatusOptions
$script:RelationshipOccupationOptions=$script:FamilyOccupationOptions
$script:RelationshipDynamicOptions=$script:FamilyDynamicOptions
$script:FriendTypeOptions=@('Best Friend','Close Friend','Friend','Childhood Friend','Family Friend','Work Friend','School Friend','Online Friend','Former Friend Reconciled','Found Family','Other / Custom','Unknown')
$script:FriendshipStatusOptions=@('Active','Close','Distant','Drifting Apart','Reconnecting','Complicated','Estranged','Former Friendship','Unknown','Other / Custom')
$script:EnemyTypeOptions=@('Not a Rival / N/A','Rival','Friendly Rival','Competitive Rival','Professional Rival','Academic Rival','Athletic Rival','Romantic Rival','Rival/Love Interest','Rival Turned Enemy','Personal Enemy','Former Friend','Former Lover','Enemy/Love Interest','Enemy with Mutual Attraction','Political Enemy','Family Enemy','Nemesis','Betrayer','Other')
$script:ThreatLevelOptions=@('None / N/A','Low','Moderate','High','Severe','Extreme','Unknown')
$script:MentorTypeOptions=@('Teacher','Coach','Professional Mentor','Academic Mentor','Combat Mentor','Spiritual Mentor','Guardian Mentor','Family Mentor','Peer Mentor','Former Mentor','Reluctant Mentor','Other / Custom','Unknown')
$script:MentorshipStatusOptions=@('Active','Former','Completed','Informal','Complicated','Estranged','Ended Badly','Mentor Deceased','Unknown','Other / Custom')
function Get-RelationshipArray([string]$Key){
    $c=Get-CurrentCharacter;if($null -eq $c){return @()};$raw=[string]$c.Fields[$Key];if([string]::IsNullOrWhiteSpace($raw)){return @()}
    try{$o=$raw|ConvertFrom-Json;if($null -eq $o){return @()};return @($o)}catch{
        if($Key -eq 'Friends'){return @([pscustomobject]@{FriendType='';Name='';Gender='';Status='';Occupation='';RelationshipDynamic='';FriendshipStatus='';Notes=$raw})}
        if($Key -eq 'Enemies'){return @([pscustomobject]@{Name='';Gender='';EnemyType='';Status='';Occupation='';RelationshipDynamic='';ThreatLevel='';Notes=$raw})}
        if($Key -eq 'Mentors'){return @([pscustomobject]@{Name='';Gender='';MentorType='';Status='';Occupation='';RelationshipDynamic='';MentorshipStatus='';Notes=$raw})}
        return @()
    }
}
function Set-RelationshipArray([string]$Key,$Items){$c=Get-CurrentCharacter;if($null -eq $c){return};$json=ConvertTo-Json -InputObject @($Items) -Depth 8 -Compress;$c.Fields[$Key]=$json;Mark-CharacterChanged $json}
function Get-RelationshipFields([string]$Kind){
    if($Kind -eq 'Friend'){return @(
        [pscustomobject]@{Field='FriendType';Label='Friend Type';Type='Choice';Options=$script:FriendTypeOptions},
        [pscustomobject]@{Field='Name';Label='Name';Type='Text';Options=@()},
        [pscustomobject]@{Field='Gender';Label='Gender';Type='Choice';Options=$script:RelationshipGenderOptions},
        [pscustomobject]@{Field='Status';Label='Status';Type='Choice';Options=$script:RelationshipStatusOptions},
        [pscustomobject]@{Field='Occupation';Label='Occupation';Type='EditChoice';Options=$script:RelationshipOccupationOptions},
        [pscustomobject]@{Field='RelationshipDynamic';Label='Relationship Dynamic';Type='MultiChoice';Options=$script:RelationshipDynamicOptions},
        [pscustomobject]@{Field='FriendshipStatus';Label='Friendship Status';Type='Choice';Options=$script:FriendshipStatusOptions},
        [pscustomobject]@{Field='Notes';Label='Notes';Type='Multi';Options=@()})}
    if($Kind -eq 'Enemy'){return @(
        [pscustomobject]@{Field='Name';Label='Name';Type='Text';Options=@()},
        [pscustomobject]@{Field='Gender';Label='Gender';Type='Choice';Options=$script:RelationshipGenderOptions},
        [pscustomobject]@{Field='EnemyType';Label='Enemy Type';Type='Choice';Options=$script:EnemyTypeOptions},
        [pscustomobject]@{Field='Status';Label='Status';Type='Choice';Options=$script:RelationshipStatusOptions},
        [pscustomobject]@{Field='Occupation';Label='Occupation';Type='EditChoice';Options=$script:RelationshipOccupationOptions},
        [pscustomobject]@{Field='RelationshipDynamic';Label='Relationship Dynamic';Type='MultiChoice';Options=$script:RelationshipDynamicOptions},
        [pscustomobject]@{Field='ThreatLevel';Label='Threat Level';Type='Choice';Options=$script:ThreatLevelOptions},
        [pscustomobject]@{Field='Notes';Label='Notes';Type='Multi';Options=@()})}
    return @(
        [pscustomobject]@{Field='Name';Label='Name';Type='Text';Options=@()},
        [pscustomobject]@{Field='Gender';Label='Gender';Type='Choice';Options=$script:RelationshipGenderOptions},
        [pscustomobject]@{Field='MentorType';Label='Mentor Type';Type='Choice';Options=$script:MentorTypeOptions},
        [pscustomobject]@{Field='Status';Label='Status';Type='Choice';Options=$script:RelationshipStatusOptions},
        [pscustomobject]@{Field='Occupation';Label='Occupation';Type='EditChoice';Options=$script:RelationshipOccupationOptions},
        [pscustomobject]@{Field='RelationshipDynamic';Label='Relationship Dynamic';Type='MultiChoice';Options=$script:RelationshipDynamicOptions},
        [pscustomobject]@{Field='MentorshipStatus';Label='Mentorship Status';Type='Choice';Options=$script:MentorshipStatusOptions},
        [pscustomobject]@{Field='Notes';Label='Notes';Type='Multi';Options=@()})
}
function New-RelationshipEntry([string]$Kind){$o=[ordered]@{};foreach($d in @(Get-RelationshipFields $Kind)){$o[[string]$d.Field]=''};return [pscustomobject]$o}
function Set-RelationshipEntryValue([string]$DataKey,[int]$Index,[string]$Field,[string]$Value){$items=@(Get-RelationshipArray $DataKey);if($Index -lt 0 -or $Index -ge $items.Count){return};$items[$Index]|Add-Member -NotePropertyName $Field -NotePropertyValue $Value -Force;Set-RelationshipArray $DataKey $items}
function Relationship-EntryChanged($ctrl){if($script:Rendering){return};$t=$ctrl.Tag;if($null -eq $t){return};Set-RelationshipEntryValue ([string]$t.DataKey) ([int]$t.Index) ([string]$t.Field) ([string]$ctrl.Text)}
function Set-RelationshipEntryMultiChoice([string]$DataKey,[int]$Index,[string]$Field,[string]$Option,[bool]$Selected){$items=@(Get-RelationshipArray $DataKey);if($Index -lt 0 -or $Index -ge $items.Count){return};$cur=[string]$items[$Index].$Field;$vals=New-Object System.Collections.Generic.List[string];foreach($v in @(Split-MultiChoiceValue $cur)){[void]$vals.Add([string]$v)};if($Selected){if(-not $vals.Contains($Option)){[void]$vals.Add($Option)}}else{[void]$vals.Remove($Option)};Set-RelationshipEntryValue $DataKey $Index $Field (Join-MultiChoiceValue $vals);Render-CurrentCharacter}
function Get-RelationshipFoldKey([string]$DataKey,[int]$Index){return ($DataKey+'#'+$Index)}
function Toggle-RelationshipFold([string]$DataKey){$script:RelationshipFoldState[$DataKey]=-not [bool]$script:RelationshipFoldState[$DataKey];Render-CurrentCharacter}
function Toggle-RelationshipEntryFold([string]$DataKey,[int]$Index){$k=Get-RelationshipFoldKey $DataKey $Index;$script:RelationshipEntryFoldState[$k]=-not [bool]$script:RelationshipEntryFoldState[$k];Render-CurrentCharacter}
function Add-RelationshipHeader($page,[string]$Title,[string]$Key,[int]$Y){$w=[math]::Max(320,$page.ClientSize.Width-26);$open=[bool]$script:RelationshipFoldState[$Key];$b=New-Object System.Windows.Forms.Button;$b.Text=if($open){'[-]  '+$Title}else{'[+]  '+$Title};$b.Tag=$Key;$b.Location=New-Object System.Drawing.Point(10,$Y);$b.Size=New-Object System.Drawing.Size([math]::Max(150,$w-20),32);$b.Anchor='Top,Left,Right';$b.TextAlign='MiddleLeft';$b.FlatStyle='Flat';$b.FlatAppearance.BorderColor=[System.Drawing.Color]::FromArgb(150,112,67);$b.BackColor=[System.Drawing.Color]::FromArgb(235,211,170);$b.ForeColor=$script:Ink;$b.Font=$script:FontSmall;$b.Add_Click({Toggle-RelationshipFold ([string]$this.Tag)});$page.Controls.Add($b);return 38}
function Add-RelationshipEntryField($page,[string]$DataKey,[int]$Index,[string]$Kind,$Def,[int]$Y){
    $w=[math]::Max(320,$page.ClientSize.Width-26);$labelW=[math]::Min(138,[int]($w*0.34));$inputX=$labelW+18;$inputW=[math]::Max(118,$w-$inputX-76);$type=[string]$Def.Type;$field=[string]$Def.Field
    $lbl=New-Object System.Windows.Forms.Label;$lbl.Text=[string]$Def.Label;$lbl.Font=$script:FontSmall;$lbl.ForeColor=$script:Ink;$lbl.Location=New-Object System.Drawing.Point(10,$Y);$lbl.Size=New-Object System.Drawing.Size($labelW,38);$page.Controls.Add($lbl);$height=44;$ctrl=$null
    $tag=[pscustomobject]@{DataKey=$DataKey;Index=$Index;Field=$field;Kind=$Kind}
    if($type -eq 'Choice' -or $type -eq 'EditChoice'){$ctrl=New-Object System.Windows.Forms.ComboBox;$ctrl.DropDownStyle=if($type -eq 'EditChoice'){'DropDown'}else{'DropDownList'};[void]$ctrl.Items.AddRange([object[]]$Def.Options);$ctrl.Location=New-Object System.Drawing.Point($inputX,($Y-3));$ctrl.Width=$inputW;$ctrl.Font=$script:FontSmall;$ctrl.Tag=$tag;$ctrl.Add_SelectedIndexChanged({Relationship-EntryChanged $this});if($type -eq 'EditChoice'){$ctrl.Add_TextChanged({Relationship-EntryChanged $this})}}
    elseif($type -eq 'MultiChoice'){$ctrl=New-Object System.Windows.Forms.Button;$ctrl.Height=29;$ctrl.Location=New-Object System.Drawing.Point($inputX,($Y-3));$ctrl.Width=$inputW;$ctrl.Font=$script:FontSmall;$ctrl.Tag=$tag;$ctrl.FlatStyle='Flat';$ctrl.TextAlign='MiddleLeft';$items=@(Get-RelationshipArray $DataKey);$val=if($Index -lt $items.Count){[string]$items[$Index].$field}else{''};$ctrl.Text=Get-MultiChoiceSummary $val;$selected=@(Split-MultiChoiceValue $val);$menu=New-Object System.Windows.Forms.ContextMenuStrip;$menu.ShowCheckMargin=$true;$menu.Add_Closing({param($s,$e);if($e.CloseReason -eq [System.Windows.Forms.ToolStripDropDownCloseReason]::ItemClicked){$e.Cancel=$true}});foreach($opt in @($Def.Options)){$mi=New-Object System.Windows.Forms.ToolStripMenuItem;$mi.Text=[string]$opt;$mi.CheckOnClick=$true;$mi.Checked=($selected -contains [string]$opt);$mi.Tag=[pscustomobject]@{DataKey=$DataKey;Index=$Index;Field=$field;Option=[string]$opt};$mi.Add_Click({$t=$this.Tag;Set-RelationshipEntryMultiChoice ([string]$t.DataKey) ([int]$t.Index) ([string]$t.Field) ([string]$t.Option) ([bool]$this.Checked)});[void]$menu.Items.Add($mi)};$ctrl.ContextMenuStrip=$menu;$ctrl.Add_Click({try{$this.ContextMenuStrip.Show($this,(New-Object System.Drawing.Point(0,$this.Height)))}catch{}})}
    else{$ctrl=New-Object System.Windows.Forms.TextBox;$ctrl.Location=New-Object System.Drawing.Point($inputX,($Y-3));$ctrl.Width=$inputW;$ctrl.Font=$script:FontSmall;$ctrl.Tag=$tag;$ctrl.BorderStyle='FixedSingle';if($type -eq 'Multi'){$ctrl.Multiline=$true;$ctrl.ScrollBars='Vertical';$ctrl.Height=62;$height=76};$ctrl.Add_TextChanged({Relationship-EntryChanged $this})}
    $items=@(Get-RelationshipArray $DataKey);$value=if($Index -lt $items.Count){[string]$items[$Index].$field}else{''};if($ctrl -is [System.Windows.Forms.ComboBox]){if($type -eq 'EditChoice'){$ctrl.Text=$value}elseif($ctrl.Items.Contains($value)){$ctrl.SelectedItem=$value}}elseif($type -ne 'MultiChoice'){$ctrl.Text=$value}
    $ctrl.BackColor=[System.Drawing.Color]::FromArgb(247,233,202);$ctrl.ForeColor=$script:Ink;$ctrl.Anchor='Top,Left,Right';$page.Controls.Add($ctrl);[void](Add-FamilySmallDice $page $tag ($w-68) ($Y-3) {Randomize-RelationshipEntryField $this.Tag});return $height
}
function Render-RelationshipEntry($page,[string]$DataKey,[int]$Index,[string]$Kind,[int]$Y){$items=@(Get-RelationshipArray $DataKey);if($Index -ge $items.Count){return 0};$obj=$items[$Index];$name=[string]$obj.Name;if([string]::IsNullOrWhiteSpace($name)){$name=($Kind+' '+($Index+1))};$k=Get-RelationshipFoldKey $DataKey $Index;if(-not $script:RelationshipEntryFoldState.ContainsKey($k)){$script:RelationshipEntryFoldState[$k]=$false};$open=[bool]$script:RelationshipEntryFoldState[$k];$w=[math]::Max(320,$page.ClientSize.Width-26);$head=New-Object System.Windows.Forms.Button;$head.Text=if($open){'[-]  '+$name}else{'[+]  '+$name};$head.Tag=[pscustomobject]@{DataKey=$DataKey;Index=$Index};$head.Location=New-Object System.Drawing.Point(18,$Y);$head.Size=New-Object System.Drawing.Size([math]::Max(150,$w-86),30);$head.Anchor='Top,Left,Right';$head.TextAlign='MiddleLeft';$head.FlatStyle='Flat';$head.BackColor=[System.Drawing.Color]::FromArgb(240,220,184);$head.ForeColor=$script:Ink;$head.Font=$script:FontSmall;$head.Add_Click({$t=$this.Tag;Toggle-RelationshipEntryFold ([string]$t.DataKey) ([int]$t.Index)});$page.Controls.Add($head);$rm=New-Object System.Windows.Forms.Button;$rm.Text='×';$rm.Tag=[pscustomobject]@{DataKey=$DataKey;Index=$Index};$rm.Location=New-Object System.Drawing.Point(($w-48),$Y);$rm.Size=New-Object System.Drawing.Size(30,30);$rm.Anchor='Top,Right';$rm.FlatStyle='Flat';$rm.ForeColor=[System.Drawing.Color]::FromArgb(145,58,43);$rm.Add_Click({Remove-RelationshipEntry $this.Tag});$page.Controls.Add($rm);$used=36;if(-not $open){return $used};$yy=$Y+38;foreach($d in @(Get-RelationshipFields $Kind)){$dh=Add-RelationshipEntryField $page $DataKey $Index $Kind $d $yy;$yy+=$dh;$used+=$dh};return ($used+8)}
function Add-RelationshipEntry($Tag){$items=New-Object System.Collections.Generic.List[object];foreach($x in @(Get-RelationshipArray ([string]$Tag.DataKey))){[void]$items.Add($x)};[void]$items.Add((New-RelationshipEntry ([string]$Tag.Kind)));Set-RelationshipArray ([string]$Tag.DataKey) @($items);$script:RelationshipEntryFoldState[(Get-RelationshipFoldKey ([string]$Tag.DataKey) ($items.Count-1))]=$true;Render-CurrentCharacter}
function Remove-RelationshipEntry($Tag){$old=@(Get-RelationshipArray ([string]$Tag.DataKey));$new=New-Object System.Collections.Generic.List[object];for($i=0;$i -lt $old.Count;$i++){if($i -ne [int]$Tag.Index){[void]$new.Add($old[$i])}};Set-RelationshipArray ([string]$Tag.DataKey) @($new);Render-CurrentCharacter}
function Add-RelationshipRepeater($page,[string]$DataKey,[string]$Title,[string]$Kind,[int]$Y){$h=Add-RelationshipHeader $page $Title $DataKey $Y;$Y+=$h;if(-not [bool]$script:RelationshipFoldState[$DataKey]){return $h};$b=New-Object System.Windows.Forms.Button;$b.Text=('+ ADD '+$Kind.ToUpper());$b.Tag=[pscustomobject]@{DataKey=$DataKey;Kind=$Kind};$b.Location=New-Object System.Drawing.Point(18,$Y);$b.Size=New-Object System.Drawing.Size(135,29);$b.FlatStyle='Flat';$b.BackColor=[System.Drawing.Color]::FromArgb(219,190,142);$b.ForeColor=$script:Ink;$b.Font=$script:FontSmall;$b.Add_Click({Add-RelationshipEntry $this.Tag});$page.Controls.Add($b);$Y+=36;$used=$h+36;$items=@(Get-RelationshipArray $DataKey);for($i=0;$i -lt $items.Count;$i++){$dh=Render-RelationshipEntry $page $DataKey $i $Kind $Y;$Y+=$dh;$used+=$dh};return ($used+8)}
function Get-RelationshipRandomValue([string]$Field,[string]$Kind){if($Field -eq 'Name'){return [string](Get-Random -InputObject $script:RandomPools.FullName)};if($Field -eq 'Gender'){return [string](Get-Random -InputObject $script:RelationshipGenderOptions)};if($Field -eq 'Status'){return [string](Get-Random -InputObject $script:RelationshipStatusOptions)};if($Field -eq 'Occupation'){return [string](Get-Random -InputObject $script:RelationshipOccupationOptions)};if($Field -eq 'RelationshipDynamic'){return ((Get-Random -InputObject $script:RelationshipDynamicOptions -Count (Get-Random -Minimum 1 -Maximum 4)) -join '; ')};if($Field -eq 'FriendType'){return [string](Get-Random -InputObject $script:FriendTypeOptions)};if($Field -eq 'FriendshipStatus'){return [string](Get-Random -InputObject $script:FriendshipStatusOptions)};if($Field -eq 'EnemyType'){return [string](Get-Random -InputObject $script:EnemyTypeOptions)};if($Field -eq 'ThreatLevel'){return [string](Get-Random -InputObject $script:ThreatLevelOptions)};if($Field -eq 'MentorType'){return [string](Get-Random -InputObject $script:MentorTypeOptions)};if($Field -eq 'MentorshipStatus'){return [string](Get-Random -InputObject $script:MentorshipStatusOptions)};if($Field -eq 'Notes'){return [string](Get-Random -InputObject @('Their history with the character is complicated.','They remain an important influence on the character.','Trust between them developed slowly.','There is unresolved tension in this relationship.'))};return ''}
function Randomize-RelationshipEntryField($Tag){$v=Get-RelationshipRandomValue ([string]$Tag.Field) ([string]$Tag.Kind);if(-not [string]::IsNullOrWhiteSpace($v)){Push-UndoState;Set-RelationshipEntryValue ([string]$Tag.DataKey) ([int]$Tag.Index) ([string]$Tag.Field) $v;Render-CurrentCharacter}}
function Get-RandomRelationshipStructuredValue([string]$Key){$kind=if($Key -eq 'Friends'){'Friend'}elseif($Key -eq 'Enemies'){'Enemy'}else{'Mentor'};$obj=New-RelationshipEntry $kind;foreach($d in @(Get-RelationshipFields $kind)){$obj|Add-Member -NotePropertyName ([string]$d.Field) -NotePropertyValue (Get-RelationshipRandomValue ([string]$d.Field) $kind) -Force};return (ConvertTo-Json -InputObject @($obj) -Depth 6 -Compress)}
function Render-RelationshipsSection($c,$leftHost,$rightHost){$defs=@($script:FieldDefs['Relationships']);$y=12;foreach($k in @('RelationshipStatus','Sexuality')){$d=$defs|Where-Object{[string]$_.Key -eq $k}|Select-Object -First 1;if($null -ne $d){$h=Add-FamilyDirectField $leftHost $d $y;$y+=$h}};$h=Add-RelationshipRepeater $leftHost 'Friends' 'Friends' 'Friend' $y;$y+=$h;$y=12;$h=Add-RelationshipRepeater $rightHost 'Enemies' 'Enemies' 'Enemy' $y;$y+=$h;$h=Add-RelationshipRepeater $rightHost 'Mentors' 'Mentors' 'Mentor' $y;$y+=$h}
# ---------------- END RELATIONSHIPS AUDIT -----------------------------------

'''
anchor='function Add-FieldControl([System.Windows.Forms.Panel]$page,$def,[int]$y,[int]$height=48) {'
assert anchor in core
core=core.replace(anchor,helper+anchor,1)
render_old="""        } elseif($script:CurrentSection -eq 'Family'){\n            Render-FamilySection $c $leftHost $rightHost\n        } else {"""
render_new="""        } elseif($script:CurrentSection -eq 'Family'){\n            Render-FamilySection $c $leftHost $rightHost\n        } elseif($script:CurrentSection -eq 'Relationships'){\n            Render-RelationshipsSection $c $leftHost $rightHost\n        } else {"""
assert render_old in core
core=core.replace(render_old,render_new,1)
# Structured relationship randomization before generic text fallback.
needle="    if ($Key -eq 'Parent1Relationship' -or $Key -eq 'Parent2Relationship') { return [string](Get-Random -InputObject @('Close','Complicated','Estranged','Protective','Distant','Loving but tense','Unknown')) }\n"
assert needle in core
insert=needle+"    if ($Key -eq 'Friends' -or $Key -eq 'Enemies' -or $Key -eq 'Mentors') { return Get-RandomRelationshipStructuredValue $Key }\n    if ($Key -eq 'RelationshipStatus') { return [string](Get-Random -InputObject @('Single','Dating','In a Relationship','Engaged','Married','Separated','Divorced','Widowed','It’s Complicated','Unknown')) }\n    if ($Key -eq 'Sexuality') { return [string](Get-Random -InputObject @('Gay / Homosexual','Lesbian','Bisexual','Pansexual','Asexual','Aromantic','Straight / Heterosexual','Queer','Demisexual','Questioning','Unknown')) }\n"
core=core.replace(needle,insert,1)
# Validate expected audit content and that removed relationship defs are gone from schema.
assert '# ---------------- RELATIONSHIPS AUDIT' in core
schema=core[core.index("    'Relationships' = @("):core.index("    'Skills' = @(")]
for req in ['RelationshipStatus','Sexuality','Friends','Enemies','Mentors','Gay / Homosexual','EnemyType','MentorshipStatus']:
    assert req in core,req
for old in ['RomanticOrientation','RomanticHistory','Attraction','LoveLanguage','ShowsAffection','Jealousy','HandlesConflict','IntimacyNotes','PartnerRelationship','Rivals','Dependents','PastRelationships','ImportantRelationships','RelationshipNotes']:
    assert ("Key='"+old+"'") not in schema,old
assert "'Family' = @(" in core and 'Render-FamilySection' in core and 'FamilyJson' in core
# Static PowerShell parse when pwsh is available.
(OUT/'TheFilesCore.ps1').write_text(core,encoding='utf-8-sig')
if subprocess.run(['bash','-lc','command -v pwsh >/dev/null'],check=False).returncode==0:
    check=subprocess.run(['pwsh','-NoProfile','-Command',"$e=$null;$t=$null;[System.Management.Automation.Language.Parser]::ParseFile('build-out/TheFilesCore.ps1',[ref]$t,[ref]$e)|Out-Null;if($e.Count){$e|ForEach-Object{Write-Error $_.Message};exit 1}"],text=True,capture_output=True)
    if check.returncode: print(check.stdout,check.stderr); raise SystemExit('PowerShell parser failed')
# Update packed core and per-file hashes.
core_gz=gzip.compress(core.encode('utf-8-sig'),compresslevel=9,mtime=0)
files['TheFilesCore.ps1.gz']['contentBase64']=base64.b64encode(core_gz).decode()
files['TheFilesCore.ps1.gz']['sha256']=hashlib.sha256(core_gz).hexdigest()
# Bootstrap: preserve updater; version marker only.
boot=base64.b64decode(files['TheFiles.ps1']['contentBase64']).decode('utf-8-sig')
boot=boot.replace('v0.2.15','v0.2.16',1)
boot_bytes=boot.encode('utf-8-sig');files['TheFiles.ps1']['contentBase64']=base64.b64encode(boot_bytes).decode();files['TheFiles.ps1']['sha256']=hashlib.sha256(boot_bytes).hexdigest()
appv=json.loads(base64.b64decode(files['AppVersion.json']['contentBase64']).decode('utf-8-sig'))
appv['version']='0.2.16';appv_bytes=(json.dumps(appv,indent=2,ensure_ascii=False)+'\n').encode('utf-8')
files['AppVersion.json']['contentBase64']=base64.b64encode(appv_bytes).decode();files['AppVersion.json']['sha256']=hashlib.sha256(appv_bytes).hexdigest()
payload['version']='0.2.16';payload['files']=[files[f['path']] for f in payload['files']]
# Safety: only app payload files, no user-data/portraits.
allowed={'TheFiles.ps1','TheFilesCore.ps1.gz','AppVersion.json'}
assert {f['path'] for f in payload['files']}==allowed
for f in payload['files']:
    raw=base64.b64decode(f['contentBase64']);assert hashlib.sha256(raw).hexdigest()==f['sha256']
ptext=json.dumps(payload,separators=(',',':'),ensure_ascii=False)
json.loads(ptext)
# Split into manageable fresh chunks.
chunk=8000
parts=[ptext[i:i+chunk] for i in range(0,len(ptext),chunk)]
part_meta=[]
for i,text in enumerate(parts,1):
    name=f'payload-0.2.16-relationships-rebuild-part-{i:03d}.txt';(OUT/name).write_text(text,encoding='utf-8');part_meta.append({'url':f'https://raw.githubusercontent.com/VeyrStudio/DesktopAppUpdates/main/the-files/{name}','sha256':hashlib.sha256(text.encode()).hexdigest()})
combined=hashlib.sha256(ptext.encode()).hexdigest()
candidate={'schemaVersion':1,'appId':'the-files','appName':'The Files','version':'0.2.16','payloadSha256':combined,'payloadParts':part_meta,'notes':'Relationships-only cumulative rebuild on v0.2.15 Family baseline. Adds dropdown Relationship Status and Sexuality, folded repeatable Friends/Enemies/Mentors, field and section randomization, while preserving the verified pre-UI updater and separate user data.'}
(OUT/'manifest-0.2.16-candidate.json').write_text(json.dumps(candidate,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
# Additional machine-readable validation summary.
summary={'base':'0.2.15','version':'0.2.16','parts':len(parts),'payloadSha256':combined,'coreSha256':files['TheFilesCore.ps1.gz']['sha256'],'bootstrapSha256':files['TheFiles.ps1']['sha256'],'appVersionSha256':files['AppVersion.json']['sha256'],'familyPreserved':True,'removedRelationshipKeys':True,'userDataPathsPresent':False,'requiredEnemyTypes':all(x in core for x in ['Rival','Friendly Rival','Competitive Rival','Professional Rival','Academic Rival','Athletic Rival','Romantic Rival','Rival/Love Interest','Rival Turned Enemy','Personal Enemy','Former Friend','Former Lover','Enemy/Love Interest','Enemy with Mutual Attraction','Political Enemy','Family Enemy','Nemesis','Betrayer','Other','Not a Rival / N/A'])}
assert all([summary['familyPreserved'],summary['removedRelationshipKeys'],not summary['userDataPathsPresent'],summary['requiredEnemyTypes']])
(OUT/'validation.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
