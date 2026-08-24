import json, base64, gzip, pathlib
root=pathlib.Path('.')

def decode_payload_text(text):
    p=json.loads(text)
    e=next(f for f in p['files'] if f['path']=='TheFilesCore.ps1.gz')
    return p,gzip.decompress(base64.b64decode(e['contentBase64'])).decode('utf-8-sig')

def show(label,core,terms,radius=10):
    lines=core.splitlines(); print('\n###',label,'LINES',len(lines))
    hits=[]
    for i,line in enumerate(lines):
        if any(t in line for t in terms): hits.append(i)
    seen=[]
    for i in hits:
        a=max(0,i-radius);b=min(len(lines),i+radius+1)
        if any(a>=x and a<=y for x,y in seen): continue
        seen.append((a,b))
        print(f'\n--- {a+1}-{b} ---')
        for j in range(a,b): print(f'{j+1:05d}: {lines[j]}')

m=json.loads((root/'the-files/manifest.json').read_text(encoding='utf-8'))
cur=''.join((root/'the-files'/x['url'].rsplit('/',1)[-1]).read_text(encoding='utf-8') for x in m['payloadParts'])
p,core=decode_payload_text(cur)
print('CURRENT VERSION',p['version'])
show('CURRENT RENDER/RANDOMIZE',core,['Render-FamilySection','Randomize-Section','Randomize-OneField','ActiveSection','SectionOrder','FamilyJson'],14)

old=(root/'the-files/payload-0.3.1-startup-fix-part-001.txt').read_text(encoding='utf-8')
op,ocore=decode_payload_text(old)
print('\nHISTORICAL VERSION',op['version'])
show('HISTORICAL RELATIONSHIPS',ocore,["'Relationships' = @(",'RELATIONSHIP AUDIT','RelationshipJson','EnemyType','MentorshipStatus','FriendType','Render-Relationship','Get-Relationship'],18)
print('\nINSPECTION_3_COMPLETE')
