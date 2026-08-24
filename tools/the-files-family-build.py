from pathlib import Path
import base64, gzip, json

ROOT = Path(__file__).resolve().parents[1]
TF = ROOT / 'the-files'
part_names = [f'payload-0.2.13-personality-background-dropdown-part-{i:03d}.txt' for i in range(1,8)]
raw = ''.join((TF/n).read_text(encoding='utf-8') for n in part_names)
payload = json.loads(raw)
assert payload['version'] == '0.2.13'
files = {f['path']: f for f in payload['files']}
core_gz = base64.b64decode(files['TheFilesCore.ps1.gz']['contentBase64'])
core = gzip.decompress(core_gz).decode('utf-8-sig')
lines = core.splitlines()
needles = ['Family', 'Parent One', 'Parent Two', 'Sibling', 'Children', 'Important Family History']
hits = [i for i,line in enumerate(lines) if any(n.lower() in line.lower() for n in needles)]
selected=[]; seen=set()
for i in hits:
    for j in range(max(0,i-20), min(len(lines),i+35)):
        if j not in seen:
            selected.append((j+1, lines[j])); seen.add(j)
selected.sort()
out=[]; last=None
for n,line in selected:
    if last is not None and n>last+1: out.append('---')
    out.append(f'{n:05d}: {line}')
    last=n
(TF/'debug-family-context.txt').write_text('\n'.join(out), encoding='utf-8')
print(f'Extracted {len(hits)} Family-related hits from stable v0.2.13. No release files changed.')
