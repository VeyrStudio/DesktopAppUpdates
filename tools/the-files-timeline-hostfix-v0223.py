from pathlib import Path
import base64,gzip,hashlib,json,re
ROOT=Path(__file__).resolve().parents[1]
TF=ROOT/'the-files'
VERSION='0.2.23'
m=json.loads((TF/'manifest.json').read_text(encoding='utf-8'))
if m.get('version')!='0.2.22': raise SystemExit(f"Expected 0.2.22 base, got {m.get('version')}")
b=b''.join((TF/p['url'].rsplit('/',1)[-1]).read_bytes() for p in m['payloadParts'])
if hashlib.sha256(b).hexdigest()!=m['payloadSha256']: raise SystemExit('base sha mismatch')
p=json.loads(b.decode('utf-8'))
files={f['path']:f for f in p['files']}
for x in ('TheFiles.ps1','TheFilesCore.ps1','TheFilesCore.ps1.gz','AppVersion.json'):
    if x not in files: raise SystemExit('missing '+x)
core=base64.b64decode(files['TheFilesCore.ps1']['contentBase64']).decode('utf-8-sig')
# PowerShell's automatic $Host variable is read-only and case-insensitive. Rename only the Timeline helper parameter and its references.
pat=r"function Add-TimelineField\(\$host,(.*?)\nfunction Render-TimelineSection"
mch=re.search(pat,core,re.S)
if not mch: raise SystemExit('Add-TimelineField block not found')
block=mch.group(0)
block2=block.replace('Add-TimelineField($host,','Add-TimelineField($container,').replace('$host.','$container.')
if block2==block: raise SystemExit('Timeline host rename made no changes')
core=core.replace(block,block2,1)
if 'function Add-TimelineField($host,' in core or '$host.Controls' in block2 or '$host.ClientSize' in block2:
    raise SystemExit('read-only Host variable remains in Timeline helper')
# Keep runnable and compressed core byte-identical after decompression.
raw=core.encode('utf-8-sig')
files['TheFilesCore.ps1']['contentBase64']=base64.b64encode(raw).decode()
files['TheFilesCore.ps1.gz']['contentBase64']=base64.b64encode(gzip.compress(raw,mtime=0)).decode()
app=json.loads(base64.b64decode(files['AppVersion.json']['contentBase64']).decode('utf-8-sig'))
app['version']=VERSION
files['AppVersion.json']['contentBase64']=base64.b64encode(json.dumps(app,indent=2).encode('utf-8')).decode()
p['version']=VERSION
p['files']=list(files.values())
out=json.dumps(p,separators=(',',':')).encode('utf-8')
name='payload-0.2.23-timeline-hostfix-part-001.txt'
(TF/name).write_bytes(out)
sha=hashlib.sha256(out).hexdigest()
val={
 'version':VERSION,'baseVersion':'0.2.22','payload':name,'payloadSha256':sha,
 'requirements':{
   'timelineHostParameterRenamed':True,
   'readOnlyHostCollisionRemoved':True,
   'timelinePreserved':('function Render-TimelineSection' in core),
   'storyPreserved':("'Story' = @(" in core),
   'powersPreserved':('function Render-PowersSection' in core),
   'bootstrapUpdaterPreserved':True,
   'compressedCoreIncluded':True,
   'uncompressedCoreIncluded':True,
   'userDataUntouched':True
 }
}
(TF/'timeline-0.2.23-hostfix-validation.json').write_text(json.dumps(val,indent=2),encoding='utf-8')
vd=ROOT/'.timeline-v0223-validation';vd.mkdir(exist_ok=True)
(vd/'TheFiles.ps1').write_bytes(base64.b64decode(files['TheFiles.ps1']['contentBase64']))
(vd/'TheFilesCore.ps1').write_bytes(raw)
print(json.dumps(val,indent=2))
