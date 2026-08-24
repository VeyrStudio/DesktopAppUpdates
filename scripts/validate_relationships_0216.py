import base64, gzip, hashlib, json, pathlib

# Strict one-shot validation for the staged cumulative v0.2.16 Relationships release.
ROOT = pathlib.Path('.')
PAYLOAD_PATH = ROOT / 'the-files' / 'payload-0.2.16-relationships-rebuild-part-001.txt'
REPORT_PATH = ROOT / 'the-files' / 'relationships-0.2.16-validation.json'

raw = PAYLOAD_PATH.read_bytes()
text = raw.decode('utf-8')
payload = json.loads(text)
errors = []
checks = {}

def check(name, condition, detail=''):
    checks[name] = {'ok': bool(condition), 'detail': detail}
    if not condition:
        errors.append(name + (': ' + detail if detail else ''))

check('payload_json_parses', isinstance(payload, dict))
check('app_id', payload.get('appId') == 'the-files', repr(payload.get('appId')))
check('version', payload.get('version') == '0.2.16', repr(payload.get('version')))
check('schema', payload.get('schemaVersion') == 1, repr(payload.get('schemaVersion')))

files = payload.get('files') or []
paths = [str(f.get('path', '')) for f in files]
check('expected_app_files', set(paths) == {'TheFiles.ps1','TheFilesCore.ps1.gz','AppVersion.json'}, repr(paths))
check('no_user_data_payload_paths', not any(any(bad in p.lower() for bad in ['userdata','user-data','portrait','characters','characterdata']) for p in paths), repr(paths))

decoded = {}
for f in files:
    p = str(f.get('path',''))
    try:
        b = base64.b64decode(f.get('contentBase64',''), validate=True)
        decoded[p] = b
        got = hashlib.sha256(b).hexdigest()
        want = str(f.get('sha256','')).lower()
        check('internal_sha256_' + p.replace('.','_'), got == want, f'{got} != {want}')
    except Exception as e:
        check('decode_' + p.replace('.','_'), False, str(e))

launcher = decoded.get('TheFiles.ps1', b'').decode('utf-8-sig', errors='replace')
core_gz = decoded.get('TheFilesCore.ps1.gz', b'')
try:
    core = gzip.decompress(core_gz).decode('utf-8-sig')
    check('core_gzip_decompresses', True)
except Exception as e:
    core = ''
    check('core_gzip_decompresses', False, str(e))

try:
    appver = json.loads(decoded.get('AppVersion.json', b'{}').decode('utf-8-sig'))
    check('appversion_json', appver.get('version') == '0.2.16', repr(appver))
except Exception as e:
    check('appversion_json', False, str(e))

for token in ['Install-Update','payloadSha256','payloadParts','UpdateBackup','manifest.json','SHA256']:
    check('bootstrap_' + token.replace('.','_'), token in launcher, token)

required_relationship_tokens = [
    'Relationship Status','Sexuality','Gay / Homosexual','Lesbian','Bisexual','Asexual','Aromantic','Straight / Heterosexual',
    'Friends','Enemies','Mentors','Enemy Type','Threat Level','Mentor Type','Mentorship Status','Relationship Dynamic',
    'Rival','Friendly Rival','Competitive Rival','Professional Rival','Academic Rival','Athletic Rival','Romantic Rival',
    'Rival/Love Interest','Rival Turned Enemy','Personal Enemy','Former Friend','Former Lover','Enemy/Love Interest',
    'Enemy with Mutual Attraction','Political Enemy','Family Enemy','Nemesis','Betrayer','Other','Not a Rival / N/A',
    'Randomize Relationships'
]
for token in required_relationship_tokens:
    check('relationship_token_' + hashlib.sha1(token.encode()).hexdigest()[:10], token in core, token)

for token in ['Add Friend','Add Enemy','Add Mentor','Name','Gender','Status','Occupation','Notes']:
    check('relationship_structure_' + hashlib.sha1(token.encode()).hexdigest()[:10], token in core, token)

family_tokens = [
    'Parent One','Parent Two','Parent Type','Adoptive','Spouse','Siblings','Sibling Type','Age Relationship',
    'Children','Child Type','Age/Life Stage','Other Parent','Other Family','Importance','Important Family History','Randomize Family'
]
for token in family_tokens:
    check('family_preserved_' + hashlib.sha1(token.encode()).hexdigest()[:10], token in core, token)

check('core_nonempty', len(core) > 1000, str(len(core)))
check('launcher_nonempty', len(launcher) > 1000, str(len(launcher)))
check('no_encodedcommand_handoff', '-EncodedCommand' not in launcher, 'EncodedCommand must not return')

report = {
    'version': payload.get('version'),
    'payloadSha256': hashlib.sha256(raw).hexdigest(),
    'payloadBytes': len(raw),
    'checks': checks,
    'errorCount': len(errors),
    'errors': errors,
    'powershellParse': 'pending-workflow-step'
}
REPORT_PATH.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')

tmp = ROOT / '.relationship-validation'
tmp.mkdir(exist_ok=True)
(tmp / 'TheFiles.ps1').write_text(launcher, encoding='utf-8-sig')
(tmp / 'TheFilesCore.ps1').write_text(core, encoding='utf-8-sig')

if errors:
    print(json.dumps(report, indent=2))
    raise SystemExit(1)
print(json.dumps(report, indent=2))
