from pathlib import Path
import base64,gzip,hashlib,json
ROOT=Path(__file__).resolve().parents[1]
TF=ROOT/'the-files'
VERSION='0.2.24'
m=json.loads((TF/'manifest.json').read_text(encoding='utf-8'))
if m.get('version')!='0.2.23': raise SystemExit(f"Expected 0.2.23 base, got {m.get('version')}")
b=b''.join((TF/p['url'].rsplit('/',1)[-1]).read_bytes() for p in m['payloadParts'])
if hashlib.sha256(b).hexdigest()!=m['payloadSha256']: raise SystemExit('base payload sha mismatch')
p=json.loads(b.decode('utf-8'))
files={f['path']:f for f in p['files']}
required=('TheFiles.ps1','TheFilesCore.ps1','TheFilesCore.ps1.gz','AppVersion.json')
for x in required:
    if x not in files: raise SystemExit('missing '+x)
# Keep Timeline/Story/Powers source exactly as in working v0.2.23; only bump version metadata.
app_raw=base64.b64decode(files['AppVersion.json']['contentBase64'])
app=json.loads(app_raw.decode('utf-8-sig'))
app['version']=VERSION
files['AppVersion.json']['contentBase64']=base64.b64encode(json.dumps(app,indent=2).encode('utf-8')).decode()
p['version']=VERSION
# Recompute every internal file hash only after all content bytes are final.
for f in files.values():
    raw=base64.b64decode(f['contentBase64'])
    f['sha256']=hashlib.sha256(raw).hexdigest()
p['files']=list(files.values())
# Validate runnable/compressed cores match exactly after decompression.
core=base64.b64decode(files['TheFilesCore.ps1']['contentBase64'])
gz=base64.b64decode(files['TheFilesCore.ps1.gz']['contentBase64'])
if gzip.decompress(gz)!=core: raise SystemExit('compressed core does not decompress to runnable core')
# Verify internal metadata exactly as the updater will.
for f in p['files']:
    raw=base64.b64decode(f['contentBase64'])
    actual=hashlib.sha256(raw).hexdigest()
    if actual.lower()!=str(f.get('sha256','')).lower():
        raise SystemExit(f"internal verification failed: {f['path']}")
out=json.dumps(p,separators=(',',':')).encode('utf-8')
name='payload-0.2.24-internal-hash-repair-part-001.txt'
(TF/name).write_bytes(out)
sha=hashlib.sha256(out).hexdigest()
val={
 'version':VERSION,'baseVersion':'0.2.23','payload':name,'payloadSha256':sha,
 'requirements':{
  'timelineSourcePreserved':b'function Render-TimelineSection' in core,
  'timelineHostFixPreserved':b'function Add-TimelineField($container,' in core,
  'storyPreserved':b"'Story' = @(" in core,
  'powersPreserved':b'function Render-PowersSection' in core,
  'allInternalHashesRecomputed':True,
  'allInternalHashesVerified':True,
  'compressedCoreMatchesRunnableCore':True,
  'bootstrapUpdaterPreserved':True,
  'userDataUntouched':True
 },
 'fileHashes':{f['path']:f['sha256'] for f in p['files']}
}
(TF/'v0.2.24-internal-hash-repair-validation.json').write_text(json.dumps(val,indent=2),encoding='utf-8')
vd=ROOT/'.v0224-validation';vd.mkdir(exist_ok=True)
(vd/'TheFiles.ps1').write_bytes(base64.b64decode(files['TheFiles.ps1']['contentBase64']))
(vd/'TheFilesCore.ps1').write_bytes(core)
print(json.dumps(val,indent=2))
