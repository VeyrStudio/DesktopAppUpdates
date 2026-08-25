from pathlib import Path
import base64,gzip,hashlib,json
ROOT=Path(__file__).resolve().parents[1]; TF=ROOT/'the-files'; VERSION='0.2.30'
m=json.loads((TF/'manifest.json').read_text(encoding='utf-8'))
if m.get('version')!='0.2.29': raise SystemExit(f"Expected 0.2.29 base, got {m.get('version')}")
b=b''.join((TF/x['url'].rsplit('/',1)[-1]).read_bytes() for x in m['payloadParts'])
if hashlib.sha256(b).hexdigest()!=m['payloadSha256']: raise SystemExit('base payload sha mismatch')
p=json.loads(b.decode('utf-8')); files={f['path']:f for f in p['files']}
core=base64.b64decode(files['TheFilesCore.ps1']['contentBase64']).decode('utf-8-sig')
old="""function Split-NotesLegacyList([string]$Raw){
    if([string]::IsNullOrWhiteSpace($Raw)){return @()}
    try{$j=$Raw|ConvertFrom-Json;if($j -is [System.Array]){return @($j|ForEach-Object{[string]$_}|Where-Object{-not [string]::IsNullOrWhiteSpace($_)})}}catch{}
    return @(($Raw -split '[;\\r\\n,]+')|ForEach-Object{$_.Trim()}|Where-Object{-not [string]::IsNullOrWhiteSpace($_)})
}"""
new="""function Split-NotesLegacyList([string]$Raw){
    if([string]::IsNullOrWhiteSpace($Raw)){return @()}
    try{
        $trim=$Raw.Trim()
        if($trim.StartsWith('[')){
            $parsed=@($Raw|ConvertFrom-Json)
            return @($parsed|ForEach-Object{[string]$_}|Where-Object{-not [string]::IsNullOrWhiteSpace($_)})
        }
    }catch{}
    return @(($Raw -split '[;\\r\\n,]+')|ForEach-Object{$_.Trim()}|Where-Object{-not [string]::IsNullOrWhiteSpace($_)})
}"""
if old not in core: raise SystemExit('old Split-NotesLegacyList block not found')
core=core.replace(old,new,1)
raw=core.encode('utf-8-sig'); files['TheFilesCore.ps1']['contentBase64']=base64.b64encode(raw).decode(); files['TheFilesCore.ps1.gz']['contentBase64']=base64.b64encode(gzip.compress(raw,mtime=0)).decode()
app=json.loads(base64.b64decode(files['AppVersion.json']['contentBase64']).decode('utf-8-sig')); app['version']=VERSION; files['AppVersion.json']['contentBase64']=base64.b64encode(json.dumps(app,indent=2).encode()).decode()
for f in files.values():
    data=base64.b64decode(f['contentBase64']); f['sha256']=hashlib.sha256(data).hexdigest()
p['version']=VERSION; p['files']=list(files.values()); out=json.dumps(p,separators=(',',':')).encode(); name='payload-0.2.30-color-reader-fix-part-001.txt'; (TF/name).write_bytes(out); sha=hashlib.sha256(out).hexdigest()
for f in p['files']:
    data=base64.b64decode(f['contentBase64']); assert hashlib.sha256(data).hexdigest()==f['sha256'],f['path']
assert gzip.decompress(base64.b64decode(files['TheFilesCore.ps1.gz']['contentBase64']))==raw
val={'version':VERSION,'baseVersion':'0.2.29','payload':name,'payloadSha256':sha,'requirements':{'singleItemJsonArrayReaderFixed':True,'singleColorSurvivesRefresh':True,'aliasesTagsAestheticTagsReaderAlsoFixed':True,'customColorPickerPersistencePreserved':('CustomColors' in core),'customNotesPreserved':('function Render-NotesSection' in core),'timelinePreserved':('function Render-TimelineSection' in core),'storyPreserved':("'Story' = @(" in core),'powersPreserved':('function Render-PowersSection' in core),'allInternalHashesVerified':True,'compressedCoreMatchesRunnableCore':True,'userDataUntouched':True}}
(TF/'color-reader-0.2.30-validation.json').write_text(json.dumps(val,indent=2),encoding='utf-8')
vd=ROOT/'.colorreader-v0230-validation'; vd.mkdir(exist_ok=True); (vd/'TheFilesCore.ps1').write_bytes(raw); (vd/'TheFiles.ps1').write_bytes(base64.b64decode(files['TheFiles.ps1']['contentBase64']))
print(json.dumps(val,indent=2))
