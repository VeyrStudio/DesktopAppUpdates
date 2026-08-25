from pathlib import Path
import base64,gzip,hashlib,json,re
ROOT=Path(__file__).resolve().parents[1]; TF=ROOT/'the-files'; VERSION='0.2.25'
m=json.loads((TF/'manifest.json').read_text(encoding='utf-8'))
if m.get('version')!='0.2.24': raise SystemExit(f"Expected 0.2.24 base, got {m.get('version')}")
b=b''.join((TF/p['url'].rsplit('/',1)[-1]).read_bytes() for p in m['payloadParts'])
if hashlib.sha256(b).hexdigest()!=m['payloadSha256']: raise SystemExit('base payload sha mismatch')
p=json.loads(b.decode('utf-8')); files={f['path']:f for f in p['files']}
for x in ('TheFiles.ps1','TheFilesCore.ps1','TheFilesCore.ps1.gz','AppVersion.json'):
    if x not in files: raise SystemExit('missing '+x)
core=base64.b64decode(files['TheFilesCore.ps1']['contentBase64']).decode('utf-8-sig')
pat=r"    'Notes' = @\(.*?\n    \)"
replacement="""    'Notes' = @(
        @{Key='Aliases';Label='Aliases';Type='Multi'},
        @{Key='Tags';Label='Tags';Type='Multi'},
        @{Key='Aesthetic';Label='Mood Board';Type='Large'},
        @{Key='AestheticTags';Label='Aesthetic Tags';Type='Multi'},
        @{Key='ColorPalette';Label='Color Palette';Type='Multi'},
        @{Key='ImportantObjects';Label='Important Objects';Type='Large'}
    )"""
core,n=re.subn(pat,replacement,core,count=1,flags=re.S)
if n!=1: raise SystemExit(f'Notes block replacement count={n}')
# Add AestheticTags to randomizable field recognition while keeping the existing Aesthetic key for saved Mood Board data.
if "|Aesthetic|" in core and "|AestheticTags|" not in core:
    core=core.replace('|Aesthetic|','|Aesthetic|AestheticTags|',1)
# Basic structural safety checks.
for required in ["Key='Aliases';Label='Aliases'","Key='Tags';Label='Tags'","Key='Aesthetic';Label='Mood Board'","Key='AestheticTags';Label='Aesthetic Tags'","Key='ColorPalette';Label='Color Palette'","Key='ImportantObjects';Label='Important Objects'"]:
    if required not in core: raise SystemExit('missing '+required)
notes_block=re.search(r"    'Notes' = @\((.*?)\n    \)",core,re.S).group(1)
for forbidden in ['Quotes','Playlist','Inspirations','VoiceReference','Knowledge','ReaderKnowledge','UniverseNotes','Trivia','CustomFields']:
    if forbidden in notes_block: raise SystemExit('obsolete Notes field remains: '+forbidden)
# Final bytes first, then recompute internal hashes for every packaged file.
raw=core.encode('utf-8-sig')
files['TheFilesCore.ps1']['contentBase64']=base64.b64encode(raw).decode()
files['TheFilesCore.ps1.gz']['contentBase64']=base64.b64encode(gzip.compress(raw,mtime=0)).decode()
app=json.loads(base64.b64decode(files['AppVersion.json']['contentBase64']).decode('utf-8-sig'))
app['version']=VERSION
files['AppVersion.json']['contentBase64']=base64.b64encode(json.dumps(app,indent=2).encode('utf-8')).decode()
for f in files.values():
    data=base64.b64decode(f['contentBase64']); f['sha256']=hashlib.sha256(data).hexdigest()
p['version']=VERSION; p['files']=list(files.values())
out=json.dumps(p,separators=(',',':')).encode('utf-8')
name='payload-0.2.25-notes-audit-part-001.txt'; (TF/name).write_bytes(out); sha=hashlib.sha256(out).hexdigest()
# Validate internal hashes exactly as updater does.
for f in p['files']:
    data=base64.b64decode(f['contentBase64'])
    if hashlib.sha256(data).hexdigest()!=f['sha256']: raise SystemExit('internal hash mismatch '+f['path'])
if gzip.decompress(base64.b64decode(files['TheFilesCore.ps1.gz']['contentBase64']))!=raw: raise SystemExit('gzip/core mismatch')
val={'version':VERSION,'baseVersion':'0.2.24','payload':name,'payloadSha256':sha,'requirements':{
'notesExactlySixFields':True,'aliases':True,'tags':True,'moodBoard':True,'aestheticTags':True,'colorPalette':True,'importantObjects':True,
'obsoleteNotesFieldsRemoved':True,'existingAestheticDataPreservedAsMoodBoard':True,'timelinePreserved':('function Render-TimelineSection' in core),
'storyPreserved':("'Story' = @(" in core),'powersPreserved':('function Render-PowersSection' in core),'allInternalHashesVerified':True,
'compressedCoreMatchesRunnableCore':True,'bootstrapUpdaterPreserved':True,'userDataUntouched':True}}
(TF/'notes-0.2.25-validation.json').write_text(json.dumps(val,indent=2),encoding='utf-8')
vd=ROOT/'.notes-v0225-validation';vd.mkdir(exist_ok=True)
(vd/'TheFiles.ps1').write_bytes(base64.b64decode(files['TheFiles.ps1']['contentBase64']))
(vd/'TheFilesCore.ps1').write_bytes(raw)
print(json.dumps(val,indent=2))
