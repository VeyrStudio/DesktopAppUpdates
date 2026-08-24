import json, base64, gzip, pathlib, re
root=pathlib.Path('.')
manifest=json.loads((root/'the-files/manifest.json').read_text(encoding='utf-8'))
parts=[]
for p in manifest['payloadParts']:
    name=p['url'].rsplit('/',1)[-1]
    parts.append((root/'the-files'/name).read_text(encoding='utf-8'))
payload=json.loads(''.join(parts))
core_entry=next(f for f in payload['files'] if f['path']=='TheFilesCore.ps1.gz')
core=gzip.decompress(base64.b64decode(core_entry['contentBase64'])).decode('utf-8-sig')
lines=core.splitlines()
terms=['Relationship','Relationships','relationship','sexuality','Friends','Enemies','Mentors','Rivals','Romantic']
hits=[]
for i,line in enumerate(lines):
    if any(t in line for t in terms): hits.append(i)
print('VERSION',payload['version'],'LINES',len(lines),'HITS',len(hits))
seen=set()
for i in hits:
    a=max(0,i-8); b=min(len(lines),i+18)
    key=(a,b)
    if key in seen: continue
    seen.add(key)
    print(f'\n--- CONTEXT {a+1}-{b} ---')
    for j in range(a,b): print(f'{j+1:05d}: {lines[j]}')
