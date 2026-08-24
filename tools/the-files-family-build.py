from pathlib import Path
import base64, gzip, json
ROOT=Path(__file__).resolve().parents[1]; TF=ROOT/'the-files'
raw=''.join((TF/f'payload-0.2.13-personality-background-dropdown-part-{i:03d}.txt').read_text(encoding='utf-8') for i in range(1,8))
payload=json.loads(raw); files={f['path']:f for f in payload['files']}
core=gzip.decompress(base64.b64decode(files['TheFilesCore.ps1.gz']['contentBase64'])).decode('utf-8-sig')
lines=core.splitlines()
start,end=1320,1585
out='\n'.join(f'{i+1:05d}: {lines[i]}' for i in range(start-1,min(end,len(lines))))
(TF/'debug-family-context.txt').write_text(out,encoding='utf-8')
print(f'Extracted renderer lines {start}-{end} from stable v0.2.13.')
