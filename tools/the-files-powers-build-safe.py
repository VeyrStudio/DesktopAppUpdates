from pathlib import Path
import base64, gzip, hashlib, json, re, shutil

ROOT = Path(__file__).resolve().parents[1]
TF = ROOT / 'the-files'
MANIFEST = TF / 'manifest.json'
VERSION = '0.2.17'
PREFIX = f'payload-{VERSION}-powers-safe-part-'
VALID = ROOT / '.powers-safe-validation'

manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
if manifest.get('version') != '0.2.16':
    raise SystemExit(f"Expected live Relationships base 0.2.16, found {manifest.get('version')}")
parts=[]
for p in manifest['payloadParts']:
    name=p['url'].rsplit('/',1)[-1]
    b=(TF/name).read_bytes()
    if hashlib.sha256(b).hexdigest().lower()!=str(p['sha256']).lower():
        raise SystemExit(f'Base part SHA mismatch: {name}')
    parts.append(b)
base_bytes=b''.join(parts)
if hashlib.sha256(base_bytes).hexdigest().lower()!=str(manifest['payloadSha256']).lower():
    raise SystemExit('Base combined payload SHA mismatch')
base=json.loads(base_bytes.decode('utf-8'))
files={f['path']:f for f in base['files']}
for req in ('TheFiles.ps1','TheFilesCore.ps1.gz','AppVersion.json'):
    if req not in files: raise SystemExit(f'Missing base file {req}')

launcher=base64.b64decode(files['TheFiles.ps1']['contentBase64'])
if hashlib.sha256(launcher).hexdigest()!=files['TheFiles.ps1']['sha256'].lower(): raise SystemExit('Launcher SHA mismatch')
core_gz=base64.b64decode(files['TheFilesCore.ps1.gz']['contentBase64'])
if hashlib.sha256(core_gz).hexdigest()!=files['TheFilesCore.ps1.gz']['sha256'].lower(): raise SystemExit('Core SHA mismatch')
core=gzip.decompress(core_gz).decode('utf-8-sig')

# Replace Skills + Psychology with the single audited Powers section.
powers_defs="""    'Powers' = @(\n        @{Key='Powers';Label='Powers';Type='PowerJson'}\n    )\n"""
pat=re.compile(r"    'Skills' = @\(\n.*?\n    \)\n    'Psychology' = @\(\n.*?\n    \)\n(?=    'Story' = @\()",re.S)
core,n=pat.subn(powers_defs,core,count=1)
if n!=1: raise SystemExit(f'Skills/Psychology definition replacement count={n}')

# Remove Psychology from all navigation and rename Skills to Powers.
replacements={
"$rightNames=@('Relationships','Skills','Psychology','Story','Timeline','Notes')":"$rightNames=@('Relationships','Powers','Story','Timeline','Notes')",
"$script:SectionOrder=@('Overview','Appearance','Personality','Background','Family','Relationships','Skills','Psychology','Story','Timeline','Notes')":"$script:SectionOrder=@('Overview','Appearance','Personality','Background','Family','Relationships','Powers','Story','Timeline','Notes')",
"$row2=@('Skills','Psychology','Story','Timeline','Notes')":"$row2=@('Powers','Story','Timeline','Notes')"
}
for old,new in replacements.items():
    if old not in core: raise SystemExit(f'Navigation token missing: {old}')
    core=core.replace(old,new,1)

helper=r'''
# ---------------- POWERS AUDIT -------------------------------------------------
$script:PowerFoldState=$false
$script:PowerEntryFoldState=@{}
$script:PowerAbilityOptions=@('Telepathy','Telekinesis','Empathy','Precognition','Clairvoyance','Healing','Regeneration','Super Strength','Super Speed','Enhanced Senses','Flight','Invisibility','Shapeshifting','Illusion','Mind Control','Dream Manipulation','Fear Manipulation','Shadow Manipulation','Light Manipulation','Fire Manipulation','Water Manipulation','Air Manipulation','Earth Manipulation','Ice Manipulation','Electricity Manipulation','Plant Manipulation','Animal Communication','Necromancy','Spirit Communication','Portal Creation','Teleportation','Time Manipulation','Reality Manipulation','Magic / Spellcasting','Curse / Hex','Protective Warding','Immortality','Other / Custom')
$script:PowerTypeOptions=@('Physical','Mental / Psychic','Elemental','Magical','Spiritual','Biological','Cosmic','Technological','Divine','Demonic','Fae','Reality-Altering','Other / Custom','Unknown')
$script:PowerStrengthOptions=@('Minimal','Low','Moderate','Strong','Very Strong','Extreme','Variable','Unknown')
$script:PowerControlOptions=@('Uncontrolled','Poor','Developing','Moderate','Good','Excellent','Mastered','Variable','Unknown')
$script:PowerLimitOptions=@('Requires Concentration','Limited Range','Limited Duration','Cooldown Required','Causes Exhaustion','Causes Pain','Requires Touch','Requires Line of Sight','Emotion-Dependent','Environment-Dependent','Only Works at Certain Times','Cannot Affect Self','Cannot Affect Others','Limited Uses','Unpredictable','Power Suppression Possible','Other / Custom')
$script:PowerWeaknessOptions=@('Physical Exhaustion','Mental Exhaustion','Pain','Loss of Consciousness','Specific Material','Specific Weapon','Magic','Technology','Sunlight','Darkness','Water','Fire','Cold','Heat','Sound','Emotional Distress','Fear','Injury','Power Overload','Power Dampening','Other / Custom')
$script:PowerSourceOptions=@('Innate / Born With It','Inherited','Learned','Magic','Artifact / Object','Experiment','Mutation','Technology','Divine Gift','Demonic Source','Fae Source','Curse','Contract / Pact','Unknown','Other / Custom')
$script:PowerVisibilityOptions=@('Invisible / Internal','Subtle','Visible Effect','Obvious / Dramatic','Transforms Body','Only Visible to Certain Beings','Variable','Unknown')
function Get-PowerArray {
    $c=Get-CurrentCharacter;if($null -eq $c){return @()};$raw=[string]$c.Fields['Powers'];if([string]::IsNullOrWhiteSpace($raw)){return @()}
    try{$o=$raw|ConvertFrom-Json;if($null -eq $o){return @()};return @($o)}catch{return @([pscustomobject]@{PowerAbility=$raw;PowerType='';StrengthLevel='';ControlLevel='';Limitations='';Weaknesses='';Source='';Visibility='';Notes=''})}
}
function Set-PowerArray($Items){$c=Get-CurrentCharacter;if($null -eq $c){return};$json=ConvertTo-Json -InputObject @($Items) -Depth 8 -Compress;$c.Fields['Powers']=$json;Mark-CharacterChanged $json}
function Get-PowerFields{return @(
 [pscustomobject]@{Field='PowerAbility';Label='Power / Ability';Type='EditChoice';Options=$script:PowerAbilityOptions},
 [pscustomobject]@{Field='PowerType';Label='Power Type';Type='Choice';Options=$script:PowerTypeOptions},
 [pscustomobject]@{Field='StrengthLevel';Label='Strength Level';Type='Choice';Options=$script:PowerStrengthOptions},
 [pscustomobject]@{Field='ControlLevel';Label='Control Level';Type='Choice';Options=$script:PowerControlOptions},
 [pscustomobject]@{Field='Limitations';Label='Limitations';Type='MultiChoice';Options=$script:PowerLimitOptions},
 [pscustomobject]@{Field='Weaknesses';Label='Weaknesses';Type='MultiChoice';Options=$script:PowerWeaknessOptions},
 [pscustomobject]@{Field='Source';Label='Source';Type='EditChoice';Options=$script:PowerSourceOptions},
 [pscustomobject]@{Field='Visibility';Label='Visibility';Type='Choice';Options=$script:PowerVisibilityOptions},
 [pscustomobject]@{Field='Notes';Label='Notes';Type='Multi';Options=@()}
)}
function New-PowerEntry{$o=[ordered]@{};foreach($d in @(Get-PowerFields)){$o[[string]$d.Field]=''};return [pscustomobject]$o}
function Set-PowerValue([int]$Index,[string]$Field,[string]$Value){$items=@(Get-PowerArray);if($Index -lt 0 -or $Index -ge $items.Count){return};$items[$Index]|Add-Member -NotePropertyName $Field -NotePropertyValue $Value -Force;Set-PowerArray $items}
function Power-Changed($ctrl){if($script:Rendering){return};$t=$ctrl.Tag;if($null -eq $t){return};Set-PowerValue ([int]$t.Index) ([string]$t.Field) ([string]$ctrl.Text)}
function Toggle-PowerSection{$script:PowerFoldState=-not [bool]$script:PowerFoldState;Render-CurrentCharacter}
function Toggle-PowerEntry([int]$Index){$k=[string]$Index;if(-not $script:PowerEntryFoldState.ContainsKey($k)){$script:PowerEntryFoldState[$k]=$false};$script:PowerEntryFoldState[$k]=-not [bool]$script:PowerEntryFoldState[$k];Render-CurrentCharacter}
function Set-PowerMulti([int]$Index,[string]$Field,[string]$Option,[bool]$Selected){$items=@(Get-PowerArray);if($Index -lt 0 -or $Index -ge $items.Count){return};$vals=New-Object System.Collections.Generic.List[string];foreach($v in @(Split-MultiChoiceValue ([string]$items[$Index].$Field))){[void]$vals.Add([string]$v)};if($Selected){if(-not $vals.Contains($Option)){[void]$vals.Add($Option)}}else{[void]$vals.Remove($Option)};Set-PowerValue $Index $Field (Join-MultiChoiceValue $vals);Render-CurrentCharacter}
function Get-PowerRandom([string]$Field){switch($Field){'PowerAbility'{return [string](Get-Random -InputObject $script:PowerAbilityOptions)}'PowerType'{return [string](Get-Random -InputObject $script:PowerTypeOptions)}'StrengthLevel'{return [string](Get-Random -InputObject $script:PowerStrengthOptions)}'ControlLevel'{return [string](Get-Random -InputObject $script:PowerControlOptions)}'Limitations'{return ((Get-Random -InputObject $script:PowerLimitOptions -Count (Get-Random -Minimum 1 -Maximum 4))-join '; ')}'Weaknesses'{return ((Get-Random -InputObject $script:PowerWeaknessOptions -Count (Get-Random -Minimum 1 -Maximum 4))-join '; ')}'Source'{return [string](Get-Random -InputObject $script:PowerSourceOptions)}'Visibility'{return [string](Get-Random -InputObject $script:PowerVisibilityOptions)}'Notes'{return [string](Get-Random -InputObject @('Using this power has a meaningful cost.','Control improves with practice.','The character hides this ability from most people.','The power becomes less reliable under stress.'))}default{return ''}}}
function Randomize-PowerField($Tag){Push-UndoState;$v=Get-PowerRandom ([string]$Tag.Field);Set-PowerValue ([int]$Tag.Index) ([string]$Tag.Field) $v;Render-CurrentCharacter}
function Get-RandomPowerStructuredValue{$o=New-PowerEntry;foreach($d in @(Get-PowerFields)){$o|Add-Member -NotePropertyName ([string]$d.Field) -NotePropertyValue (Get-PowerRandom ([string]$d.Field)) -Force};return (ConvertTo-Json -InputObject @($o) -Depth 6 -Compress)}
function Add-PowerField($page,[int]$Index,$Def,[int]$Y){$items=@(Get-PowerArray);if($Index -ge $items.Count){return 0};$obj=$items[$Index];$field=[string]$Def.Field;$type=[string]$Def.Type;$w=[math]::Max(320,$page.ClientSize.Width-26);$labelW=132;$inputX=150;$inputW=[math]::Max(115,$w-$inputX-76);$lbl=[System.Windows.Forms.Label]::new();$lbl.Text=[string]$Def.Label;$lbl.Font=$script:FontSmall;$lbl.ForeColor=$script:Ink;$lbl.Location=[System.Drawing.Point]::new(10,$Y);$lbl.Size=[System.Drawing.Size]::new($labelW,38);$page.Controls.Add($lbl);$tag=[pscustomobject]@{Index=$Index;Field=$field};$ctrl=$null;$height=44
 if($type -eq 'Choice' -or $type -eq 'EditChoice'){$ctrl=[System.Windows.Forms.ComboBox]::new();$ctrl.DropDownStyle=if($type -eq 'EditChoice'){'DropDown'}else{'DropDownList'};[void]$ctrl.Items.AddRange([object[]]$Def.Options);$ctrl.Location=[System.Drawing.Point]::new($inputX,$Y-3);$ctrl.Width=$inputW;$ctrl.Font=$script:FontSmall;$ctrl.Tag=$tag;$ctrl.Add_SelectedIndexChanged({Power-Changed $this});if($type -eq 'EditChoice'){$ctrl.Add_TextChanged({Power-Changed $this})};$ctrl.Text=[string]$obj.$field}
 elseif($type -eq 'MultiChoice'){$ctrl=[System.Windows.Forms.Button]::new();$ctrl.Height=29;$ctrl.Location=[System.Drawing.Point]::new($inputX,$Y-3);$ctrl.Width=$inputW;$ctrl.Font=$script:FontSmall;$ctrl.Tag=$tag;$ctrl.FlatStyle='Flat';$ctrl.TextAlign='MiddleLeft';$val=[string]$obj.$field;$ctrl.Text=Get-MultiChoiceSummary $val;$menu=[System.Windows.Forms.ContextMenuStrip]::new();$menu.ShowCheckMargin=$true;foreach($opt in @($Def.Options)){$mi=[System.Windows.Forms.ToolStripMenuItem]::new();$mi.Text=[string]$opt;$mi.CheckOnClick=$true;$mi.Checked=@(Split-MultiChoiceValue $val)-contains [string]$opt;$mi.Tag=[pscustomobject]@{Index=$Index;Field=$field;Option=[string]$opt};$mi.Add_Click({$t=$this.Tag;Set-PowerMulti ([int]$t.Index) ([string]$t.Field) ([string]$t.Option) ([bool]$this.Checked)});[void]$menu.Items.Add($mi)};$ctrl.ContextMenuStrip=$menu;$ctrl.Add_Click({$this.ContextMenuStrip.Show($this,[System.Drawing.Point]::new(0,$this.Height))})}
 else{$ctrl=[System.Windows.Forms.TextBox]::new();$ctrl.Location=[System.Drawing.Point]::new($inputX,$Y-3);$ctrl.Width=$inputW;$ctrl.Font=$script:FontSmall;$ctrl.Tag=$tag;$ctrl.Text=[string]$obj.$field;if($type -eq 'Multi'){$ctrl.Multiline=$true;$ctrl.ScrollBars='Vertical';$ctrl.Height=62;$height=76};$ctrl.Add_TextChanged({Power-Changed $this})}
 $ctrl.BackColor=[System.Drawing.Color]::FromArgb(247,233,202);$ctrl.ForeColor=$script:Ink;$ctrl.Anchor='Top,Left,Right';$page.Controls.Add($ctrl);$d=[System.Windows.Forms.Button]::new();$d.Text='🎲';$d.Tag=$tag;$d.Width=30;$d.Height=27;$d.Location=[System.Drawing.Point]::new($w-68,$Y-3);$d.Anchor='Top,Right';$d.FlatStyle='Flat';$d.Add_Click({Randomize-PowerField $this.Tag});$page.Controls.Add($d);return $height}
function Render-PowersSection($c,$leftHost,$rightHost){$head=[System.Windows.Forms.Button]::new();$head.Text=if($script:PowerFoldState){'[-]  Powers'}else{'[+]  Powers'};$head.Height=36;$head.Location=[System.Drawing.Point]::new(8,12);$head.Width=[math]::Max(190,$leftHost.ClientSize.Width-22);$head.Anchor='Top,Left,Right';$head.TextAlign='MiddleLeft';$head.Font=[System.Drawing.Font]::new('Georgia',9,[System.Drawing.FontStyle]::Bold);$head.FlatStyle='Flat';$head.Add_Click({Toggle-PowerSection});$leftHost.Controls.Add($head);$rand=[System.Windows.Forms.Button]::new();$rand.Text='🎲 RANDOMIZE POWERS';$rand.Height=34;$rand.Width=180;$rand.Location=[System.Drawing.Point]::new(8,58);$rand.Add_Click({Push-UndoState;$c=Get-CurrentCharacter;if($null -ne $c){$c.Fields['Powers']=Get-RandomPowerStructuredValue;Mark-CharacterChanged ([string]$c.Fields['Powers']);Render-CurrentCharacter}});$leftHost.Controls.Add($rand);if(-not $script:PowerFoldState){return};$items=@(Get-PowerArray);$y=104;for($i=0;$i -lt $items.Count;$i++){$k=[string]$i;$open=if($script:PowerEntryFoldState.ContainsKey($k)){[bool]$script:PowerEntryFoldState[$k]}else{$false};$b=[System.Windows.Forms.Button]::new();$nm=[string]$items[$i].PowerAbility;if([string]::IsNullOrWhiteSpace($nm)){$nm='Power '+($i+1)};$b.Text=if($open){'[-]  '+$nm}else{'[+]  '+$nm};$b.Tag=$i;$b.Height=32;$b.Location=[System.Drawing.Point]::new(8,$y);$b.Width=[math]::Max(190,$leftHost.ClientSize.Width-70);$b.Anchor='Top,Left,Right';$b.TextAlign='MiddleLeft';$b.Add_Click({Toggle-PowerEntry ([int]$this.Tag)});$leftHost.Controls.Add($b);$rm=[System.Windows.Forms.Button]::new();$rm.Text='X';$rm.Tag=$i;$rm.Width=34;$rm.Height=32;$rm.Location=[System.Drawing.Point]::new([math]::Max(200,$leftHost.ClientSize.Width-54),$y);$rm.Anchor='Top,Right';$rm.Add_Click({Push-UndoState;$a=@(Get-PowerArray);$idx=[int]$this.Tag;$n=@();for($j=0;$j -lt $a.Count;$j++){if($j -ne $idx){$n+=,$a[$j]}};Set-PowerArray $n;Render-CurrentCharacter});$leftHost.Controls.Add($rm);$y+=38;if($open){foreach($d in @(Get-PowerFields)){$h=Add-PowerField $leftHost $i $d $y;$y+=$h};$y+=8}};$add=[System.Windows.Forms.Button]::new();$add.Text='+ ADD POWER';$add.Width=150;$add.Height=32;$add.Location=[System.Drawing.Point]::new(8,$y);$add.Add_Click({Push-UndoState;$a=@(Get-PowerArray);$a+=,(New-PowerEntry);Set-PowerArray $a;Render-CurrentCharacter});$leftHost.Controls.Add($add);$hint=[System.Windows.Forms.Label]::new();$hint.Text='Powers are repeatable. Each ability keeps its own type, strength, control, limitations, weaknesses, source, visibility, and notes.';$hint.AutoSize=$false;$hint.Size=[System.Drawing.Size]::new([math]::Max(220,$rightHost.ClientSize.Width-24),120);$hint.Location=[System.Drawing.Point]::new(10,14);$hint.Font=$script:FontSmall;$hint.ForeColor=$script:Muted;$rightHost.Controls.Add($hint)}
'''
anchor='function Render-EmptyState {'
if anchor not in core: raise SystemExit('Render-EmptyState anchor missing')
core=core.replace(anchor,helper+'\n'+anchor,1)

old="""        } elseif($script:CurrentSection -eq 'Relationships'){\n            Render-RelationshipsSection $c $leftHost $rightHost\n        } else {"""
new="""        } elseif($script:CurrentSection -eq 'Relationships'){\n            Render-RelationshipsSection $c $leftHost $rightHost\n        } elseif($script:CurrentSection -eq 'Powers'){\n            Render-PowersSection $c $leftHost $rightHost\n        } else {"""
if old not in core: raise SystemExit('Render branch anchor missing')
core=core.replace(old,new,1)

old_rand="$v=if($key -eq 'Nicknames'){Get-SmartNickname}else{Get-RandomText $key}"
new_rand="$v=if($key -eq 'Powers'){Get-RandomPowerStructuredValue}elseif($key -eq 'Nicknames'){Get-SmartNickname}else{Get-RandomText $key}"
if old_rand not in core: raise SystemExit('Randomizer anchor missing')
core=core.replace(old_rand,new_rand,1)

# New version metadata, preserving bootstrap updater and user data paths.
app_version=json.dumps({'appId':'the-files','appName':'The Files','version':VERSION,'manifestUrl':'https://raw.githubusercontent.com/VeyrStudio/DesktopAppUpdates/main/the-files/manifest.json'},indent=2)+'\n'
new_core_gz=gzip.compress(core.encode('utf-8-sig'),compresslevel=9,mtime=0)
new_files=[]
for path,data in [('TheFiles.ps1',launcher),('TheFilesCore.ps1.gz',new_core_gz),('AppVersion.json',app_version.encode('utf-8'))]:
    new_files.append({'path':path,'sha256':hashlib.sha256(data).hexdigest(),'contentBase64':base64.b64encode(data).decode('ascii')})
payload={'schemaVersion':1,'appId':'the-files','appName':'The Files','version':VERSION,'files':new_files,'delete':[]}
payload_bytes=json.dumps(payload,separators=(',',':'),ensure_ascii=False).encode('utf-8')

# Split conservatively for GitHub/update transport.
chunk=180000
for p in TF.glob(PREFIX+'*.txt'): p.unlink()
out_parts=[]
for i in range(0,len(payload_bytes),chunk):
    b=payload_bytes[i:i+chunk];name=f'{PREFIX}{len(out_parts)+1:03d}.txt';(TF/name).write_bytes(b);out_parts.append({'name':name,'sha256':hashlib.sha256(b).hexdigest()})

if VALID.exists(): shutil.rmtree(VALID)
VALID.mkdir(parents=True)
(VALID/'TheFiles.ps1').write_bytes(launcher)
(VALID/'TheFilesCore.ps1').write_text(core,encoding='utf-8-sig')
report={'version':VERSION,'baseVersion':'0.2.16','parts':out_parts,'combinedPayloadSha256':hashlib.sha256(payload_bytes).hexdigest(),'requirements':{
 'skillsRemoved': all(x not in core for x in ("'Skills' = @(",'Natural Talents','Learned Skills','Combat Skills','Professional Skills',"@{Key='Languages'", "@{Key='Equipment'", "@{Key='Weapons'")),
 'psychologyRemoved': "'Psychology' = @(" not in core and "'Psychology'" not in core and "'Psychology'," not in core,
 'powersSection': "'Powers' = @(" in core and "Type='PowerJson'" in core,
 'powerFields': all(x in core for x in ('Power / Ability','Power Type','Strength Level','Control Level','Limitations','Weaknesses','Source','Visibility','Notes')),
 'bootstrapPreserved': b'Install-Update' in launcher or b'manifest' in launcher.lower(),
 'dataRootPreserved': "TheFiles\\Data" in core,
 'noDataPayload': all(not f['path'].lower().startswith(('data','media','portraits')) for f in new_files)
}}
if not all(report['requirements'].values()): raise SystemExit('Requirement validation failed: '+json.dumps(report['requirements']))
(TF/f'powers-{VERSION}-build-validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
