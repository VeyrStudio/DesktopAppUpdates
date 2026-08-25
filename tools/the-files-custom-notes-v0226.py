from pathlib import Path
import base64,gzip,hashlib,json,re
ROOT=Path(__file__).resolve().parents[1]; TF=ROOT/'the-files'; VERSION='0.2.26'
m=json.loads((TF/'manifest.json').read_text(encoding='utf-8'))
if m.get('version')!='0.2.25': raise SystemExit(f"Expected 0.2.25 base, got {m.get('version')}")
b=b''.join((TF/x['url'].rsplit('/',1)[-1]).read_bytes() for x in m['payloadParts'])
if hashlib.sha256(b).hexdigest()!=m['payloadSha256']: raise SystemExit('base payload sha mismatch')
p=json.loads(b.decode('utf-8')); files={f['path']:f for f in p['files']}
for x in ('TheFiles.ps1','TheFilesCore.ps1','TheFilesCore.ps1.gz','AppVersion.json'):
    if x not in files: raise SystemExit('missing '+x)
core=base64.b64decode(files['TheFilesCore.ps1']['contentBase64']).decode('utf-8-sig')
# Notes is now fully custom-rendered; remove generic six-box field renderer.
pat=r"    'Notes' = @\(.*?\n    \)"
core,n=re.subn(pat,"    'Notes' = @()",core,count=1,flags=re.S)
if n!=1: raise SystemExit(f'Notes field block replacement count={n}')
func=r'''
# --- Custom Notes workspace -------------------------------------------------
function Split-NotesLegacyList([string]$Raw){
    if([string]::IsNullOrWhiteSpace($Raw)){return @()}
    try{$j=$Raw|ConvertFrom-Json;if($j -is [System.Array]){return @($j|ForEach-Object{[string]$_}|Where-Object{-not [string]::IsNullOrWhiteSpace($_)})}}catch{}
    return @(($Raw -split '[;\r\n,]+')|ForEach-Object{$_.Trim()}|Where-Object{-not [string]::IsNullOrWhiteSpace($_)})
}
function Get-NotesStringArray([string]$Key){$c=Get-CurrentCharacter;if($null -eq $c){return @()};return @(Split-NotesLegacyList ([string]$c.Fields[$Key]))}
function Set-NotesStringArray([string]$Key,$Items){$c=Get-CurrentCharacter;if($null -eq $c){return};$clean=@($Items|ForEach-Object{[string]$_}|Where-Object{-not [string]::IsNullOrWhiteSpace($_)});$c.Fields[$Key]=($clean|ConvertTo-Json -Compress);Mark-CharacterChanged ([string]$c.Fields[$Key])}
function Add-NotesStringItem([string]$Key,[string]$Value){$v=$Value.Trim();if([string]::IsNullOrWhiteSpace($v)){return};Push-UndoState;$a=@(Get-NotesStringArray $Key);if(-not ($a -contains $v)){$a+=,$v};Set-NotesStringArray $Key $a;Render-CurrentCharacter}
function Remove-NotesStringItem([string]$Key,[int]$Index){Push-UndoState;$a=@(Get-NotesStringArray $Key);$n=@();for($i=0;$i -lt $a.Count;$i++){if($i -ne $Index){$n+=,$a[$i]}};Set-NotesStringArray $Key $n;Render-CurrentCharacter}

function Get-MoodBoardData {
    $c=Get-CurrentCharacter;if($null -eq $c){return [pscustomobject]@{Notes='';Images=@()}}
    $raw=[string]$c.Fields['Aesthetic'];if([string]::IsNullOrWhiteSpace($raw)){return [pscustomobject]@{Notes='';Images=@()}}
    try{$o=$raw|ConvertFrom-Json;if($null -ne $o.PSObject.Properties['Images']){return [pscustomobject]@{Notes=[string]$o.Notes;Images=@($o.Images|ForEach-Object{[string]$_})}}}catch{}
    return [pscustomobject]@{Notes=$raw;Images=@()}
}
function Set-MoodBoardData($Data){$c=Get-CurrentCharacter;if($null -eq $c){return};$c.Fields['Aesthetic']=([pscustomobject]@{Notes=[string]$Data.Notes;Images=@($Data.Images)}|ConvertTo-Json -Depth 5 -Compress);Mark-CharacterChanged ([string]$c.Fields['Aesthetic'])}
function MoodBoard-NotesChanged($Ctrl){if($script:Rendering){return};$d=Get-MoodBoardData;$d.Notes=[string]$Ctrl.Text;Set-MoodBoardData $d}
function Add-MoodBoardImages {
    $c=Get-CurrentCharacter;if($null -eq $c){return};$dlg=[System.Windows.Forms.OpenFileDialog]::new();$dlg.Title='Add images to Mood Board';$dlg.Filter='Images|*.png;*.jpg;*.jpeg;*.bmp;*.gif;*.webp|All files|*.*';$dlg.Multiselect=$true
    if($dlg.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK){$dlg.Dispose();return}
    Push-UndoState;$destRoot=Join-Path (Join-Path $script:MediaRoot 'MoodBoards') ([string]$c.Id);New-Item -ItemType Directory -Force -Path $destRoot|Out-Null;$d=Get-MoodBoardData
    foreach($src in @($dlg.FileNames)){try{$ext=[System.IO.Path]::GetExtension($src);if([string]::IsNullOrWhiteSpace($ext)){$ext='.img'};$dest=Join-Path $destRoot (([guid]::NewGuid().ToString('N'))+$ext);Copy-Item -LiteralPath $src -Destination $dest -Force;$d.Images+=,$dest}catch{}}
    $dlg.Dispose();Set-MoodBoardData $d;Render-CurrentCharacter
}
function Move-MoodBoardImage([int]$Index,[int]$Delta){$d=Get-MoodBoardData;$a=@($d.Images);$j=$Index+$Delta;if($Index -lt 0 -or $Index -ge $a.Count -or $j -lt 0 -or $j -ge $a.Count){return};Push-UndoState;$tmp=$a[$Index];$a[$Index]=$a[$j];$a[$j]=$tmp;$d.Images=$a;Set-MoodBoardData $d;Render-CurrentCharacter}
function Remove-MoodBoardImage([int]$Index){$d=Get-MoodBoardData;$a=@($d.Images);if($Index -lt 0 -or $Index -ge $a.Count){return};Push-UndoState;$old=[string]$a[$Index];$n=@();for($i=0;$i -lt $a.Count;$i++){if($i -ne $Index){$n+=,$a[$i]}};$d.Images=$n;Set-MoodBoardData $d;try{if($old -and (Test-Path -LiteralPath $old) -and $old.StartsWith((Join-Path $script:MediaRoot 'MoodBoards'),[System.StringComparison]::OrdinalIgnoreCase)){Remove-Item -LiteralPath $old -Force}}catch{};Render-CurrentCharacter}

function Get-ImportantObjectArray {
    $c=Get-CurrentCharacter;if($null -eq $c){return @()};$raw=[string]$c.Fields['ImportantObjects'];if([string]::IsNullOrWhiteSpace($raw)){return @()}
    try{$a=@($raw|ConvertFrom-Json);if($a.Count -gt 0 -and $null -ne $a[0].PSObject.Properties['Name']){return $a}}catch{}
    return @([pscustomobject]@{Name='';Notes=$raw})
}
function Set-ImportantObjectArray($Items){$c=Get-CurrentCharacter;if($null -eq $c){return};$c.Fields['ImportantObjects']=(@($Items)|ConvertTo-Json -Depth 5 -Compress);Mark-CharacterChanged ([string]$c.Fields['ImportantObjects'])}
function Add-ImportantObject {Push-UndoState;$a=@(Get-ImportantObjectArray);$a+=,[pscustomobject]@{Name='';Notes=''};Set-ImportantObjectArray $a;Render-CurrentCharacter}
function Remove-ImportantObject([int]$Index){Push-UndoState;$a=@(Get-ImportantObjectArray);$n=@();for($i=0;$i -lt $a.Count;$i++){if($i -ne $Index){$n+=,$a[$i]}};Set-ImportantObjectArray $n;Render-CurrentCharacter}
function ImportantObject-Changed($Ctrl){if($script:Rendering){return};$t=$Ctrl.Tag;$a=@(Get-ImportantObjectArray);$i=[int]$t.Index;if($i -lt 0 -or $i -ge $a.Count){return};$a[$i].([string]$t.Field)=[string]$Ctrl.Text;Set-ImportantObjectArray $a}

function Get-NotesPaletteArray {return @(Get-NotesStringArray 'ColorPalette')}
function Add-NotesColor {
    $dlg=[System.Windows.Forms.ColorDialog]::new();$dlg.FullOpen=$true
    if($dlg.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK){$hex=('#{0:X2}{1:X2}{2:X2}' -f $dlg.Color.R,$dlg.Color.G,$dlg.Color.B);Add-NotesStringItem 'ColorPalette' $hex};$dlg.Dispose()
}
function Get-SafeColor([string]$Value){try{if($Value -match '^#[0-9A-Fa-f]{6}$'){return [System.Drawing.ColorTranslator]::FromHtml($Value)};$c=[System.Drawing.Color]::FromName($Value);if($c.IsKnownColor -or $c.IsNamedColor){return $c}}catch{};return [System.Drawing.Color]::FromArgb(190,170,135)}

function Add-NotesSectionTitle($Container,[string]$Text,[int]$Y){$l=[System.Windows.Forms.Label]::new();$l.Text=$Text;$l.Font=[System.Drawing.Font]::new('Georgia',10,[System.Drawing.FontStyle]::Bold);$l.ForeColor=$script:Ink;$l.Location=[System.Drawing.Point]::new(10,$Y);$l.AutoSize=$true;$Container.Controls.Add($l);return $l}
function Render-NotesListEditor($Container,[string]$Key,[string]$Title,[int]$Y,[int]$Height){
    [void](Add-NotesSectionTitle $Container $Title $Y);$box=[System.Windows.Forms.TextBox]::new();$box.Location=[System.Drawing.Point]::new(10,$Y+28);$box.Size=[System.Drawing.Size]::new([math]::Max(120,$Container.ClientSize.Width-115),28);$box.Anchor='Top,Left,Right';$box.BackColor=[System.Drawing.Color]::FromArgb(222,194,145);$box.ForeColor=[System.Drawing.Color]::FromArgb(45,24,10);$Container.Controls.Add($box)
    $add=[System.Windows.Forms.Button]::new();$add.Text='ADD';$add.Tag=[pscustomobject]@{Key=$Key;Input=$box};$add.Location=[System.Drawing.Point]::new([math]::Max(130,$Container.ClientSize.Width-94),$Y+27);$add.Size=[System.Drawing.Size]::new(74,29);$add.Anchor='Top,Right';$add.FlatStyle='Flat';$add.BackColor=[System.Drawing.Color]::FromArgb(210,180,128);$add.ForeColor=[System.Drawing.Color]::FromArgb(45,24,10);$add.Add_Click({Add-NotesStringItem ([string]$this.Tag.Key) ([string]$this.Tag.Input.Text)});$Container.Controls.Add($add)
    $flow=[System.Windows.Forms.FlowLayoutPanel]::new();$flow.Location=[System.Drawing.Point]::new(10,$Y+64);$flow.Size=[System.Drawing.Size]::new([math]::Max(180,$Container.ClientSize.Width-30),$Height-66);$flow.Anchor='Top,Left,Right';$flow.AutoScroll=$true;$flow.WrapContents=$true;$Container.Controls.Add($flow);$a=@(Get-NotesStringArray $Key)
    for($i=0;$i -lt $a.Count;$i++){$chip=[System.Windows.Forms.Button]::new();$chip.AutoSize=$true;$chip.Height=28;$chip.Text=([string]$a[$i]+'  ×');$chip.Tag=[pscustomobject]@{Key=$Key;Index=$i};$chip.FlatStyle='Flat';$chip.BackColor=[System.Drawing.Color]::FromArgb(210,180,128);$chip.ForeColor=[System.Drawing.Color]::FromArgb(45,24,10);$chip.Add_Click({Remove-NotesStringItem ([string]$this.Tag.Key) ([int]$this.Tag.Index)});[void]$flow.Controls.Add($chip)}
    return ($Y+$Height)
}
function Render-ColorPaletteEditor($Container,[int]$Y,[int]$Height){
    [void](Add-NotesSectionTitle $Container 'COLOR PALETTE' $Y);$add=[System.Windows.Forms.Button]::new();$add.Text='+ ADD COLOR';$add.Location=[System.Drawing.Point]::new(10,$Y+28);$add.Size=[System.Drawing.Size]::new(110,29);$add.FlatStyle='Flat';$add.BackColor=[System.Drawing.Color]::FromArgb(210,180,128);$add.ForeColor=[System.Drawing.Color]::FromArgb(45,24,10);$add.Add_Click({Add-NotesColor});$Container.Controls.Add($add)
    $flow=[System.Windows.Forms.FlowLayoutPanel]::new();$flow.Location=[System.Drawing.Point]::new(10,$Y+64);$flow.Size=[System.Drawing.Size]::new([math]::Max(180,$Container.ClientSize.Width-30),$Height-66);$flow.Anchor='Top,Left,Right';$flow.AutoScroll=$true;$flow.WrapContents=$true;$Container.Controls.Add($flow);$a=@(Get-NotesPaletteArray)
    for($i=0;$i -lt $a.Count;$i++){$v=[string]$a[$i];$p=[System.Windows.Forms.Panel]::new();$p.Size=[System.Drawing.Size]::new(124,42);$p.BackColor=$script:Parchment2;$sw=[System.Windows.Forms.Panel]::new();$sw.Location=[System.Drawing.Point]::new(3,3);$sw.Size=[System.Drawing.Size]::new(34,34);$sw.BackColor=Get-SafeColor $v;$p.Controls.Add($sw);$lab=[System.Windows.Forms.Label]::new();$lab.Text=$v;$lab.Location=[System.Drawing.Point]::new(41,5);$lab.Size=[System.Drawing.Size]::new(58,28);$lab.ForeColor=$script:Ink;$p.Controls.Add($lab);$x=[System.Windows.Forms.Button]::new();$x.Text='×';$x.Tag=$i;$x.Location=[System.Drawing.Point]::new(100,7);$x.Size=[System.Drawing.Size]::new(22,26);$x.Add_Click({Remove-NotesStringItem 'ColorPalette' ([int]$this.Tag)});$p.Controls.Add($x);[void]$flow.Controls.Add($p)}
    return ($Y+$Height)
}
function Render-MoodBoardEditor($Container,[int]$Y,[int]$Height){
    [void](Add-NotesSectionTitle $Container 'MOOD BOARD' $Y);$add=[System.Windows.Forms.Button]::new();$add.Text='+ ADD IMAGES';$add.Location=[System.Drawing.Point]::new(10,$Y+28);$add.Size=[System.Drawing.Size]::new(115,29);$add.FlatStyle='Flat';$add.BackColor=[System.Drawing.Color]::FromArgb(210,180,128);$add.ForeColor=[System.Drawing.Color]::FromArgb(45,24,10);$add.Add_Click({Add-MoodBoardImages});$Container.Controls.Add($add)
    $d=Get-MoodBoardData;$notes=[System.Windows.Forms.TextBox]::new();$notes.Multiline=$true;$notes.ScrollBars='Vertical';$notes.Location=[System.Drawing.Point]::new(136,$Y+28);$notes.Size=[System.Drawing.Size]::new([math]::Max(130,$Container.ClientSize.Width-156),54);$notes.Anchor='Top,Left,Right';$notes.BackColor=[System.Drawing.Color]::FromArgb(222,194,145);$notes.ForeColor=[System.Drawing.Color]::FromArgb(45,24,10);$notes.Text=[string]$d.Notes;$notes.Add_TextChanged({MoodBoard-NotesChanged $this});$Container.Controls.Add($notes)
    $flow=[System.Windows.Forms.FlowLayoutPanel]::new();$flow.Location=[System.Drawing.Point]::new(10,$Y+92);$flow.Size=[System.Drawing.Size]::new([math]::Max(180,$Container.ClientSize.Width-30),$Height-94);$flow.Anchor='Top,Left,Right';$flow.AutoScroll=$true;$flow.WrapContents=$true;$Container.Controls.Add($flow);$imgs=@($d.Images)
    for($i=0;$i -lt $imgs.Count;$i++){$path=[string]$imgs[$i];$tile=[System.Windows.Forms.Panel]::new();$tile.Size=[System.Drawing.Size]::new(142,154);$tile.BackColor=[System.Drawing.Color]::FromArgb(210,180,128);$pic=[System.Windows.Forms.PictureBox]::new();$pic.Location=[System.Drawing.Point]::new(4,4);$pic.Size=[System.Drawing.Size]::new(134,112);$pic.SizeMode='Zoom';$pic.BackColor=[System.Drawing.Color]::FromArgb(224,204,166);if($path -and (Test-Path -LiteralPath $path)){try{$im=[System.Drawing.Image]::FromFile($path);$bmp=[System.Drawing.Bitmap]::new($im);$im.Dispose();$pic.Image=$bmp;$pic.Add_Disposed({if($null -ne $this.Image){$this.Image.Dispose()}})}catch{}};$tile.Controls.Add($pic);foreach($s in @(@('←',-1,4),@('→',1,42))){$bt=[System.Windows.Forms.Button]::new();$bt.Text=$s[0];$bt.Tag=[pscustomobject]@{Index=$i;Delta=[int]$s[1]};$bt.Location=[System.Drawing.Point]::new([int]$s[2],122);$bt.Size=[System.Drawing.Size]::new(34,26);$bt.Add_Click({Move-MoodBoardImage ([int]$this.Tag.Index) ([int]$this.Tag.Delta)});$tile.Controls.Add($bt)};$rm=[System.Windows.Forms.Button]::new();$rm.Text='REMOVE';$rm.Tag=$i;$rm.Location=[System.Drawing.Point]::new(80,122);$rm.Size=[System.Drawing.Size]::new(58,26);$rm.Add_Click({Remove-MoodBoardImage ([int]$this.Tag)});$tile.Controls.Add($rm);[void]$flow.Controls.Add($tile)}
    return ($Y+$Height)
}
function Render-ImportantObjectsEditor($Container,[int]$Y){
    [void](Add-NotesSectionTitle $Container 'IMPORTANT OBJECTS' $Y);$add=[System.Windows.Forms.Button]::new();$add.Text='+ ADD OBJECT';$add.Location=[System.Drawing.Point]::new(10,$Y+28);$add.Size=[System.Drawing.Size]::new(115,29);$add.FlatStyle='Flat';$add.BackColor=[System.Drawing.Color]::FromArgb(210,180,128);$add.ForeColor=[System.Drawing.Color]::FromArgb(45,24,10);$add.Add_Click({Add-ImportantObject});$Container.Controls.Add($add);$a=@(Get-ImportantObjectArray);$yy=$Y+66
    for($i=0;$i -lt $a.Count;$i++){$card=[System.Windows.Forms.Panel]::new();$card.Location=[System.Drawing.Point]::new(10,$yy);$card.Size=[System.Drawing.Size]::new([math]::Max(240,$Container.ClientSize.Width-30),104);$card.Anchor='Top,Left,Right';$card.BackColor=[System.Drawing.Color]::FromArgb(218,194,151);$Container.Controls.Add($card);$name=[System.Windows.Forms.TextBox]::new();$name.Tag=[pscustomobject]@{Index=$i;Field='Name'};$name.Location=[System.Drawing.Point]::new(8,8);$name.Size=[System.Drawing.Size]::new([math]::Max(120,$card.Width-50),26);$name.Anchor='Top,Left,Right';$name.BackColor=[System.Drawing.Color]::FromArgb(235,214,175);$name.ForeColor=$script:Ink;$name.Text=[string]$a[$i].Name;$name.Add_TextChanged({ImportantObject-Changed $this});$card.Controls.Add($name);$rm=[System.Windows.Forms.Button]::new();$rm.Text='X';$rm.Tag=$i;$rm.Location=[System.Drawing.Point]::new([math]::Max(125,$card.Width-38),8);$rm.Size=[System.Drawing.Size]::new(28,26);$rm.Anchor='Top,Right';$rm.BackColor=[System.Drawing.Color]::FromArgb(120,67,42);$rm.ForeColor=[System.Drawing.Color]::FromArgb(248,233,200);$rm.Add_Click({Remove-ImportantObject ([int]$this.Tag)});$card.Controls.Add($rm);$notes=[System.Windows.Forms.TextBox]::new();$notes.Tag=[pscustomobject]@{Index=$i;Field='Notes'};$notes.Multiline=$true;$notes.ScrollBars='Vertical';$notes.Location=[System.Drawing.Point]::new(8,42);$notes.Size=[System.Drawing.Size]::new([math]::Max(160,$card.Width-16),54);$notes.Anchor='Top,Left,Right';$notes.BackColor=[System.Drawing.Color]::FromArgb(235,214,175);$notes.ForeColor=$script:Ink;$notes.Text=[string]$a[$i].Notes;$notes.Add_TextChanged({ImportantObject-Changed $this});$card.Controls.Add($notes);$yy+=112}
}
function Render-NotesSection($c,$leftContainer,$rightContainer){
    $y=10;$y=Render-NotesListEditor $leftContainer 'Aliases' 'ALIASES' $y 160;$y+=10;$y=Render-NotesListEditor $leftContainer 'Tags' 'TAGS' $y 180;$y+=10;Render-ImportantObjectsEditor $leftContainer $y
    $r=10;$r=Render-MoodBoardEditor $rightContainer $r 330;$r+=10;$r=Render-NotesListEditor $rightContainer 'AestheticTags' 'AESTHETIC TAGS' $r 155;$r+=10;[void](Render-ColorPaletteEditor $rightContainer $r 170)
}
# --- End custom Notes workspace -------------------------------------------
'''
# Insert custom functions immediately before Render-EmptyState, after specialized render helpers.
needle='function Render-EmptyState {'
if needle not in core: raise SystemExit('Render-EmptyState hook missing')
core=core.replace(needle,func+'\n'+needle,1)
# Hook Notes into specialized section renderer after Powers, before generic else.
pat_hook=r"(\} elseif\(\$script:CurrentSection -eq 'Powers'\)\{\s*Render-PowersSection \$c \$leftHost \$rightHost\s*)(\} else \{)"
repl=r"\1} elseif($script:CurrentSection -eq 'Notes'){\n            Render-NotesSection $c $leftHost $rightHost\n        \2"
core,n=re.subn(pat_hook,repl,core,count=1,flags=re.S)
if n!=1: raise SystemExit(f'Notes renderer hook count={n}')
# Safety checks before packaging.
for s in ['function Render-NotesSection','function Add-MoodBoardImages',"CurrentSection -eq 'Notes'","'Notes' = @()",'MoodBoards','System.Windows.Forms.ColorDialog','function Render-ImportantObjectsEditor']:
    if s not in core: raise SystemExit('missing custom Notes marker '+s)
if 'function Add-TimelineField($host,' in core: raise SystemExit('old Timeline Host collision unexpectedly present')
# Package final bytes, then recompute every internal SHA-256.
raw=core.encode('utf-8-sig'); files['TheFilesCore.ps1']['contentBase64']=base64.b64encode(raw).decode(); files['TheFilesCore.ps1.gz']['contentBase64']=base64.b64encode(gzip.compress(raw,mtime=0)).decode()
app=json.loads(base64.b64decode(files['AppVersion.json']['contentBase64']).decode('utf-8-sig'));app['version']=VERSION;files['AppVersion.json']['contentBase64']=base64.b64encode(json.dumps(app,indent=2).encode()).decode()
for f in files.values():f['sha256']=hashlib.sha256(base64.b64decode(f['contentBase64'])).hexdigest()
p['version']=VERSION;p['files']=list(files.values());out=json.dumps(p,separators=(',',':')).encode();name='payload-0.2.26-custom-notes-part-001.txt';(TF/name).write_bytes(out);sha=hashlib.sha256(out).hexdigest()
for f in p['files']:
    if hashlib.sha256(base64.b64decode(f['contentBase64'])).hexdigest()!=f['sha256']:raise SystemExit('internal hash mismatch '+f['path'])
if gzip.decompress(base64.b64decode(files['TheFilesCore.ps1.gz']['contentBase64']))!=raw:raise SystemExit('compressed core mismatch')
val={'version':VERSION,'baseVersion':'0.2.25','payload':name,'payloadSha256':sha,'requirements':{'customNotesRenderer':True,'aliasesRepeatable':True,'tagsAsChips':True,'moodBoardImages':True,'moodBoardCopiesIntoDataMedia':True,'moodBoardReorderRemove':True,'legacyMoodBoardNotesPreserved':True,'aestheticTagsAsChips':True,'colorPaletteSwatches':True,'importantObjectsRepeatableStructured':True,'timelinePreserved':('function Render-TimelineSection' in core),'timelineHostFixPreserved':('function Add-TimelineField($container,' in core),'storyPreserved':("'Story' = @(" in core),'powersPreserved':('function Render-PowersSection' in core),'allInternalHashesVerified':True,'compressedCoreMatchesRunnableCore':True,'bootstrapUpdaterPreserved':True,'userDataSeparate':True}}
(TF/'custom-notes-0.2.26-validation.json').write_text(json.dumps(val,indent=2),encoding='utf-8');vd=ROOT/'.notes-v0226-validation';vd.mkdir(exist_ok=True);(vd/'TheFiles.ps1').write_bytes(base64.b64decode(files['TheFiles.ps1']['contentBase64']));(vd/'TheFilesCore.ps1').write_bytes(raw);print(json.dumps(val,indent=2))
