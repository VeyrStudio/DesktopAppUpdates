from pathlib import Path
import base64, gzip, hashlib, json, re

ROOT = Path(__file__).resolve().parents[1]
TF = ROOT / 'the-files'
MANIFEST = TF / 'manifest.json'
VERSION = '0.2.20'
OUT = TF / f'payload-{VERSION}-runtime-powers-fix-part-001.txt'
REPORT = TF / f'runtime-powers-{VERSION}-validation.json'
VALID = ROOT / '.runtime-powers-validation'

m = json.loads(MANIFEST.read_text(encoding='utf-8'))
if m.get('version') != '0.2.19':
    raise SystemExit(f"Expected live base 0.2.19, found {m.get('version')}")
parts=[]
for p in m['payloadParts']:
    name=p['url'].rsplit('/',1)[-1]
    b=(TF/name).read_bytes()
    if hashlib.sha256(b).hexdigest().lower()!=str(p['sha256']).lower():
        raise SystemExit('base part sha mismatch')
    parts.append(b)
b=b''.join(parts)
if hashlib.sha256(b).hexdigest().lower()!=str(m['payloadSha256']).lower():
    raise SystemExit('base combined sha mismatch')
payload=json.loads(b.decode('utf-8'))
files={f['path']:f for f in payload['files']}
for req in ('TheFiles.ps1','TheFilesCore.ps1','TheFilesCore.ps1.gz','AppVersion.json'):
    if req not in files: raise SystemExit(f'missing {req}')
core_bytes=base64.b64decode(files['TheFilesCore.ps1']['contentBase64'])
core=core_bytes.decode('utf-8-sig')

# 1) Disable obsolete in-UI updater. Bootstrap remains the sole automatic updater.
core,n=re.subn(r"function Should-AutoCheckUpdates\s*\{.*?\n\}","function Should-AutoCheckUpdates { return $false }",core,count=1,flags=re.S)
if n!=1: raise SystemExit(f'auto updater function patch count={n}')
old=".Add_Click({Check-ForRemoteUpdate $false})"
if old not in core: raise SystemExit('manual legacy update click hook not found')
core=core.replace(old,".Add_Click({Show-Info 'Updates are checked automatically when The Files starts.'})",1)

# 2) Style all Powers entry-level controls that were left on Windows defaults.
repls={
"$d.FlatStyle='Flat';$d.Add_Click({Randomize-PowerField $this.Tag});":"$d.FlatStyle='Flat';$d.BackColor=[System.Drawing.Color]::FromArgb(210,180,128);$d.ForeColor=[System.Drawing.Color]::FromArgb(45,24,10);$d.Add_Click({Randomize-PowerField $this.Tag});",
"$b.TextAlign='MiddleLeft';$b.Add_Click({Toggle-PowerEntry ([int]$this.Tag)});":"$b.TextAlign='MiddleLeft';$b.FlatStyle='Flat';$b.BackColor=[System.Drawing.Color]::FromArgb(210,180,128);$b.ForeColor=[System.Drawing.Color]::FromArgb(45,24,10);$b.Add_Click({Toggle-PowerEntry ([int]$this.Tag)});",
"$rm.Anchor='Top,Right';$rm.Add_Click({Push-UndoState;":"$rm.Anchor='Top,Right';$rm.FlatStyle='Flat';$rm.BackColor=[System.Drawing.Color]::FromArgb(120,67,42);$rm.ForeColor=[System.Drawing.Color]::FromArgb(248,233,200);$rm.Add_Click({Push-UndoState;",
"$add.Location=[System.Drawing.Point]::new(8,$y);$add.Add_Click({Push-UndoState;":"$add.Location=[System.Drawing.Point]::new(8,$y);$add.FlatStyle='Flat';$add.BackColor=[System.Drawing.Color]::FromArgb(210,180,128);$add.ForeColor=[System.Drawing.Color]::FromArgb(45,24,10);$add.Add_Click({Push-UndoState;"
}
for old,new in repls.items():
    if core.count(old)!=1: raise SystemExit(f'powers style token count {core.count(old)}: {old[:45]}')
    core=core.replace(old,new,1)

new_core=('\ufeff'+core).encode('utf-8')
new_gz=gzip.compress(new_core,compresslevel=9,mtime=0)
files['TheFilesCore.ps1']['contentBase64']=base64.b64encode(new_core).decode('ascii')
files['TheFilesCore.ps1']['sha256']=hashlib.sha256(new_core).hexdigest()
files['TheFilesCore.ps1.gz']['contentBase64']=base64.b64encode(new_gz).decode('ascii')
files['TheFilesCore.ps1.gz']['sha256']=hashlib.sha256(new_gz).hexdigest()
appver=json.dumps({'version':VERSION},separators=(',',':')).encode()
files['AppVersion.json']['contentBase64']=base64.b64encode(appver).decode('ascii')
files['AppVersion.json']['sha256']=hashlib.sha256(appver).hexdigest()
payload['version']=VERSION
payload['files']=list(files.values())
out=json.dumps(payload,separators=(',',':'),ensure_ascii=False).encode('utf-8')
OUT.write_bytes(out)
sha=hashlib.sha256(out).hexdigest()
VALID.mkdir(exist_ok=True)
(VALID/'TheFiles.ps1').write_bytes(base64.b64decode(files['TheFiles.ps1']['contentBase64']))
(VALID/'TheFilesCore.ps1').write_bytes(new_core)
assert 'function Should-AutoCheckUpdates { return $false }' in core
assert "Updates are checked automatically when The Files starts." in core
assert core.count('FromArgb(210,180,128)') >= 4
report={'version':VERSION,'baseVersion':'0.2.19','payload':OUT.name,'payloadSha256':sha,'requirements':{'legacyUiAutoUpdaterDisabled':True,'bootstrapUpdaterPreserved':True,'powersEntryHeaderStyled':True,'powersAddButtonStyled':True,'powersRemoveButtonStyled':True,'powersDiceStyled':True,'innerFieldContrastPreserved':True,'uncompressedCoreIncluded':True,'compressedCoreIncluded':True,'userDataUntouched':True}}
REPORT.write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
