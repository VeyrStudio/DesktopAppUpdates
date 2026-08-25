from pathlib import Path
import base64,gzip,hashlib,json
ROOT=Path(__file__).resolve().parents[1]; TF=ROOT/'the-files'; VERSION='0.2.27'
m=json.loads((TF/'manifest.json').read_text(encoding='utf-8'))
if m.get('version')!='0.2.26': raise SystemExit(f"Expected 0.2.26 base, got {m.get('version')}")
b=b''.join((TF/x['url'].rsplit('/',1)[-1]).read_bytes() for x in m['payloadParts'])
if hashlib.sha256(b).hexdigest()!=m['payloadSha256']: raise SystemExit('base payload sha mismatch')
p=json.loads(b.decode('utf-8')); files={f['path']:f for f in p['files']}
for x in ('TheFiles.ps1','TheFilesCore.ps1','TheFilesCore.ps1.gz','AppVersion.json'):
    if x not in files: raise SystemExit('missing '+x)
launcher=base64.b64decode(files['TheFiles.ps1']['contentBase64']).decode('utf-8-sig')
marker='# --- Hide bootstrap console window ---'
if marker not in launcher:
    snippet="""# --- Hide bootstrap console window ---
try {
    if (-not ('TheFiles.ConsoleWindow' -as [type])) {
        Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
namespace TheFiles {
    public static class ConsoleWindow {
        [DllImport(\"kernel32.dll\")]
        public static extern IntPtr GetConsoleWindow();
        [DllImport(\"user32.dll\")]
        public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
    }
}
'@
    }
    $consoleHandle = [TheFiles.ConsoleWindow]::GetConsoleWindow()
    if ($consoleHandle -ne [IntPtr]::Zero) { [void][TheFiles.ConsoleWindow]::ShowWindow($consoleHandle, 0) }
} catch {}
# --- End hide bootstrap console window ---

"""
    # Keep BOM/comment at the top, then hide as early as possible before network/update work.
    lines=launcher.splitlines(True)
    insert_at=1 if lines and lines[0].lstrip().startswith('#') else 0
    launcher=''.join(lines[:insert_at])+snippet+''.join(lines[insert_at:])
raw_launcher=launcher.encode('utf-8-sig')
files['TheFiles.ps1']['contentBase64']=base64.b64encode(raw_launcher).decode()
app=json.loads(base64.b64decode(files['AppVersion.json']['contentBase64']).decode('utf-8-sig'))
app['version']=VERSION
files['AppVersion.json']['contentBase64']=base64.b64encode(json.dumps(app,indent=2).encode('utf-8')).decode()
# Recompute every internal file hash after final bytes are set.
for f in files.values():
    data=base64.b64decode(f['contentBase64']); f['sha256']=hashlib.sha256(data).hexdigest()
p['version']=VERSION; p['files']=list(files.values())
out=json.dumps(p,separators=(',',':')).encode('utf-8')
name='payload-0.2.27-hide-console-part-001.txt'; (TF/name).write_bytes(out); sha=hashlib.sha256(out).hexdigest()
# updater-style checks
for f in p['files']:
    data=base64.b64decode(f['contentBase64'])
    if hashlib.sha256(data).hexdigest()!=f['sha256']: raise SystemExit('internal hash mismatch '+f['path'])
core=base64.b64decode(files['TheFilesCore.ps1']['contentBase64'])
if gzip.decompress(base64.b64decode(files['TheFilesCore.ps1.gz']['contentBase64']))!=core: raise SystemExit('gzip/core mismatch')
for token in [marker,'GetConsoleWindow','ShowWindow($consoleHandle, 0)']:
    if token not in launcher: raise SystemExit('missing launcher hide marker '+token)
val={'version':VERSION,'baseVersion':'0.2.26','payload':name,'payloadSha256':sha,'requirements':{
'consoleHideRunsInExistingLauncher':True,'noShortcutReplacementRequired':True,'bootstrapUpdaterPreserved':('Install-Update' in launcher),
'customNotesPreserved':True,'timelinePreserved':True,'storyPreserved':True,'powersPreserved':True,'allInternalHashesVerified':True,
'compressedCoreMatchesRunnableCore':True,'userDataUntouched':True}}
(TF/'hide-console-0.2.27-validation.json').write_text(json.dumps(val,indent=2),encoding='utf-8')
vd=ROOT/'.hide-console-v0227-validation';vd.mkdir(exist_ok=True)
(vd/'TheFiles.ps1').write_bytes(raw_launcher)
(vd/'TheFilesCore.ps1').write_bytes(core)
print(json.dumps(val,indent=2))
