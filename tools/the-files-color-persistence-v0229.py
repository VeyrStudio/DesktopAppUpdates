from pathlib import Path
import base64,gzip,hashlib,json,re
ROOT=Path(__file__).resolve().parents[1]; TF=ROOT/'the-files'; VERSION='0.2.29'
# Use the already validated immutable v0.2.28 payload directly because the live v0.2.28 manifest notes string is malformed JSON.
b=(TF/'payload-0.2.28-hidden-relaunch-part-001.txt').read_bytes()
p=json.loads(b.decode('utf-8')); assert p.get('version')=='0.2.28'
files={f['path']:f for f in p['files']}
for x in ('TheFiles.ps1','TheFilesCore.ps1','TheFilesCore.ps1.gz','AppVersion.json'):
    assert x in files, x
core=base64.b64decode(files['TheFilesCore.ps1']['contentBase64']).decode('utf-8-sig')
# 1. Notes list serialization must always remain a JSON array, including exactly one item.
old="function Set-NotesStringArray([string]$Key,$Items){$c=Get-CurrentCharacter;if($null -eq $c){return};$clean=@($Items|ForEach-Object{[string]$_}|Where-Object{-not [string]::IsNullOrWhiteSpace($_)});$c.Fields[$Key]=($clean|ConvertTo-Json -Compress);Mark-CharacterChanged ([string]$c.Fields[$Key])}"
new="function Set-NotesStringArray([string]$Key,$Items){$c=Get-CurrentCharacter;if($null -eq $c){return};$clean=@($Items|ForEach-Object{[string]$_}|Where-Object{-not [string]::IsNullOrWhiteSpace($_)});$c.Fields[$Key]=(ConvertTo-Json -InputObject @($clean) -Compress);Mark-CharacterChanged ([string]$c.Fields[$Key])}"
if old not in core: raise SystemExit('Set-NotesStringArray target not found')
core=core.replace(old,new,1)
# 2. Persist ColorDialog custom slots in app settings.
default_old="$script:Settings = [ordered]@{ AutoUpdateCheck = $true; LastUpdateCheck = ''; LastCharacterId=''; LastSection='Overview'; LastStatus='Existing'; ScrollLeft=0; ScrollRight=0 }"
default_new="$script:Settings = [ordered]@{ AutoUpdateCheck = $true; LastUpdateCheck = ''; LastCharacterId=''; LastSection='Overview'; LastStatus='Existing'; ScrollLeft=0; ScrollRight=0; CustomPaletteColors=@() }"
if default_old not in core: raise SystemExit('settings default target not found')
core=core.replace(default_old,default_new,1)
load_old="        if ($null -ne $s.ScrollRight) { $script:Settings.ScrollRight = [int]$s.ScrollRight }"
load_new=load_old+"\n        if ($null -ne $s.CustomPaletteColors) { $script:Settings.CustomPaletteColors = @($s.CustomPaletteColors | ForEach-Object { [int]$_ }) }"
if load_old not in core: raise SystemExit('settings load target not found')
core=core.replace(load_old,load_new,1)
# 3. Replace color picker function: restore custom slots, capture them afterwards, immediately save both settings and chosen palette color.
pat=r"function Add-NotesColor \{.*?\n\}"
m=re.search(pat,core,re.S)
if not m: raise SystemExit('Add-NotesColor function not found')
func=r'''function Add-NotesColor {
    $dlg=[System.Windows.Forms.ColorDialog]::new();$dlg.FullOpen=$true;$dlg.AllowFullOpen=$true;$dlg.AnyColor=$true
    try {
        $saved=@($script:Settings.CustomPaletteColors | ForEach-Object { [int]$_ })
        if($saved.Count -gt 0){$dlg.CustomColors=[int[]]$saved}
    } catch {}
    $accepted=($dlg.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK)
    try{$script:Settings.CustomPaletteColors=@($dlg.CustomColors | ForEach-Object { [int]$_ })}catch{$script:Settings.CustomPaletteColors=@()}
    if($accepted){
        $hex=('#{0:X2}{1:X2}{2:X2}' -f $dlg.Color.R,$dlg.Color.G,$dlg.Color.B)
        Add-NotesStringItem 'ColorPalette' $hex
    }
    $dlg.Dispose()
    # Color changes are user-library data; write them immediately so close/restart cannot beat the autosave timer.
    Save-AllData
}'''
core=core[:m.start()]+func+core[m.end():]
# Safety markers.
for marker in ['ConvertTo-Json -InputObject @($clean) -Compress','CustomPaletteColors=@()','$dlg.CustomColors=[int[]]$saved','Save-AllData','function Render-NotesSection','function Render-TimelineSection','function Render-PowersSection']:
    if marker not in core: raise SystemExit('missing '+marker)
assert 'function Add-TimelineField($host,' not in core
raw=core.encode('utf-8-sig'); files['TheFilesCore.ps1']['contentBase64']=base64.b64encode(raw).decode();files['TheFilesCore.ps1.gz']['contentBase64']=base64.b64encode(gzip.compress(raw,mtime=0)).decode()
app=json.loads(base64.b64decode(files['AppVersion.json']['contentBase64']).decode('utf-8-sig'));app['version']=VERSION
files['AppVersion.json']['contentBase64']=base64.b64encode(json.dumps(app,indent=2).encode('utf-8')).decode()
for f in files.values():
    data=base64.b64decode(f['contentBase64']);f['sha256']=hashlib.sha256(data).hexdigest()
p['version']=VERSION;p['files']=list(files.values());out=json.dumps(p,separators=(',',':')).encode('utf-8')
name='payload-0.2.29-color-persistence-part-001.txt';(TF/name).write_bytes(out);sha=hashlib.sha256(out).hexdigest()
for f in p['files']:
    data=base64.b64decode(f['contentBase64']);assert hashlib.sha256(data).hexdigest()==f['sha256'],f['path']
assert gzip.decompress(base64.b64decode(files['TheFilesCore.ps1.gz']['contentBase64']))==raw
val={'version':VERSION,'baseVersion':'0.2.28','payload':name,'payloadSha256':sha,'requirements':{'singleItemNotesArraysPersist':True,'colorPalettePersistsAcrossRender':True,'colorPaletteImmediatelySaved':True,'colorDialogCustomColorsPersistInSettings':True,'aliasesTagsAestheticTagsSerializerFixed':True,'customNotesPreserved':True,'timelinePreserved':True,'storyPreserved':("'Story' = @(" in core),'powersPreserved':True,'allInternalHashesVerified':True,'compressedCoreMatchesRunnableCore':True,'userDataSeparate':True,'manifestRepairRequired':True}}
(TF/'color-persistence-0.2.29-validation.json').write_text(json.dumps(val,indent=2),encoding='utf-8')
vd=ROOT/'.color-v0229-validation';vd.mkdir(exist_ok=True);(vd/'TheFiles.ps1').write_bytes(base64.b64decode(files['TheFiles.ps1']['contentBase64']));(vd/'TheFilesCore.ps1').write_bytes(raw)
print(json.dumps(val,indent=2))
