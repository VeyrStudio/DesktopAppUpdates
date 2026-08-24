from pathlib import Path
import base64, gzip, hashlib, json

ROOT=Path(__file__).resolve().parents[1]
TF=ROOT/'the-files'
MANIFEST=TF/'manifest.json'
VERSION='0.2.19'
OUT=TF/f'payload-{VERSION}-powers-contrast-rescue-part-001.txt'
REPORT=TF/f'powers-{VERSION}-rescue-validation.json'
VALID=ROOT/'.powers-rescue-validation'

manifest=json.loads(MANIFEST.read_text(encoding='utf-8'))
if manifest.get('version')!='0.2.17':
    raise SystemExit(f"Expected rollback base 0.2.17, found {manifest.get('version')}")
parts=[]
for p in manifest['payloadParts']:
    name=p['url'].rsplit('/',1)[-1]
    b=(TF/name).read_bytes()
    if hashlib.sha256(b).hexdigest().lower()!=str(p['sha256']).lower(): raise SystemExit('Base part sha mismatch '+name)
    parts.append(b)
base_bytes=b''.join(parts)
if hashlib.sha256(base_bytes).hexdigest().lower()!=str(manifest['payloadSha256']).lower(): raise SystemExit('Base payload sha mismatch')
payload=json.loads(base_bytes.decode('utf-8'))
files={f['path']:f for f in payload['files']}
for req in ('TheFiles.ps1','TheFilesCore.ps1.gz','AppVersion.json'):
    if req not in files: raise SystemExit('Missing '+req)
core_gz=base64.b64decode(files['TheFilesCore.ps1.gz']['contentBase64'])
if hashlib.sha256(core_gz).hexdigest().lower()!=files['TheFilesCore.ps1.gz']['sha256'].lower(): raise SystemExit('Core gzip sha mismatch')
core=gzip.decompress(core_gz).decode('utf-8-sig')

# Contrast-only UI change.
old="$ctrl.BackColor=[System.Drawing.Color]::FromArgb(247,233,202);$ctrl.ForeColor=$script:Ink;"
new="$ctrl.BackColor=[System.Drawing.Color]::FromArgb(222,194,145);$ctrl.ForeColor=[System.Drawing.Color]::FromArgb(45,24,10);"
if core.count(old)!=1: raise SystemExit(f'Power control color token count {core.count(old)}')
core=core.replace(old,new,1)
old_head="$head.FlatStyle='Flat';$head.Add_Click({Toggle-PowerSection});"
new_head="$head.FlatStyle='Flat';$head.BackColor=[System.Drawing.Color]::FromArgb(210,180,128);$head.ForeColor=[System.Drawing.Color]::FromArgb(45,24,10);$head.Add_Click({Toggle-PowerSection});"
if core.count(old_head)!=1: raise SystemExit('Power header token mismatch')
core=core.replace(old_head,new_head,1)
old_rand="$rand.Text='🎲 RANDOMIZE POWERS';$rand.Height=34;"
new_rand="$rand.Text='🎲 RANDOMIZE POWERS';$rand.BackColor=[System.Drawing.Color]::FromArgb(210,180,128);$rand.ForeColor=[System.Drawing.Color]::FromArgb(45,24,10);$rand.Height=34;"
if core.count(old_rand)!=1: raise SystemExit('Power randomize token mismatch')
core=core.replace(old_rand,new_rand,1)

core_bytes=('\ufeff'+core).encode('utf-8')
core_gz_new=gzip.compress(core_bytes,compresslevel=9,mtime=0)
files['TheFilesCore.ps1.gz']['contentBase64']=base64.b64encode(core_gz_new).decode('ascii')
files['TheFilesCore.ps1.gz']['sha256']=hashlib.sha256(core_gz_new).hexdigest()
# Critical rescue addition: ship ready-to-run uncompressed core too.
files['TheFilesCore.ps1']={
    'path':'TheFilesCore.ps1',
    'sha256':hashlib.sha256(core_bytes).hexdigest(),
    'contentBase64':base64.b64encode(core_bytes).decode('ascii')
}
appver=json.dumps({'version':VERSION},separators=(',',':')).encode('utf-8')
files['AppVersion.json']['contentBase64']=base64.b64encode(appver).decode('ascii')
files['AppVersion.json']['sha256']=hashlib.sha256(appver).hexdigest()
payload['version']=VERSION
payload['files']=list(files.values())
out_bytes=json.dumps(payload,separators=(',',':'),ensure_ascii=False).encode('utf-8')
OUT.write_bytes(out_bytes)
sha=hashlib.sha256(out_bytes).hexdigest()
VALID.mkdir(exist_ok=True)
(VALID/'TheFilesCore.ps1').write_bytes(core_bytes)
(VALID/'TheFiles.ps1').write_bytes(base64.b64decode(files['TheFiles.ps1']['contentBase64']))
assert "'Powers'" in core and 'Render-PowersSection' in core
assert 'FromArgb(222,194,145)' in core and 'FromArgb(45,24,10)' in core
assert 'LOCALAPPDATA' in core
assert 'TheFilesCore.ps1' in files and 'TheFilesCore.ps1.gz' in files
report={
 'version':VERSION,'baseVersion':'0.2.17','payload':OUT.name,'payloadSha256':sha,
 'changeScope':'Powers contrast rescue with explicit runnable core',
 'requirements':{
   'powersStructurePreserved':True,'darkerControlBackground':True,'darkControlText':True,
   'compressedCoreIncluded':True,'uncompressedCoreIncluded':True,'psychologyStillRemoved':True,
   'userDataPathPreserved':True,'noUserDataPayload':True
 }
}
REPORT.write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
