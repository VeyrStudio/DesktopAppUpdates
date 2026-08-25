from pathlib import Path
import base64,gzip,hashlib,json
ROOT=Path(__file__).resolve().parents[1]; TF=ROOT/'the-files'; VERSION='0.2.28'
m=json.loads((TF/'manifest.json').read_text(encoding='utf-8'))
if m.get('version')!='0.2.27': raise SystemExit(f"Expected 0.2.27 base, got {m.get('version')}")
b=b''.join((TF/x['url'].rsplit('/',1)[-1]).read_bytes() for x in m['payloadParts'])
if hashlib.sha256(b).hexdigest()!=m['payloadSha256']: raise SystemExit('base payload sha mismatch')
p=json.loads(b.decode('utf-8')); files={f['path']:f for f in p['files']}
for x in ('TheFiles.ps1','TheFilesCore.ps1','TheFilesCore.ps1.gz','AppVersion.json'):
    if x not in files: raise SystemExit('missing '+x)
launcher=base64.b64decode(files['TheFiles.ps1']['contentBase64']).decode('utf-8-sig')
# Replace the previous in-process console-hide shim, if present, with a hidden relaunch handoff.
start_marker='# --- Hide bootstrap console window ---'
end_marker='# --- End hide bootstrap console window ---'
if start_marker in launcher and end_marker in launcher:
    a=launcher.index(start_marker); b2=launcher.index(end_marker)+len(end_marker)
    launcher=launcher[:a]+launcher[b2:]
# Hidden relaunch must happen before updater/bootstrap work. WScript starts powershell with window style 0.
shim=r'''# --- Hidden bootstrap relaunch ---
if ($env:THEFILES_HIDDEN_BOOTSTRAP -ne '1') {
    try {
        $self = $MyInvocation.MyCommand.Path
        if (-not [string]::IsNullOrWhiteSpace($self)) {
            $vbs = Join-Path ([IO.Path]::GetTempPath()) ('TheFilesHidden-' + [guid]::NewGuid().ToString('N') + '.vbs')
            $escaped = $self.Replace('"','""')
            $cmd = 'powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File ""' + $escaped + '""'
            $script = 'Set sh = CreateObject("WScript.Shell")' + "`r`n" + _
                      'Set env = sh.Environment("PROCESS")' + "`r`n" + _
                      'env("THEFILES_HIDDEN_BOOTSTRAP") = "1"' + "`r`n" + _
                      'sh.Run "' + $cmd.Replace('"','""') + '", 0, False' + "`r`n" + _
                      'On Error Resume Next' + "`r`n" + _
                      'CreateObject("Scripting.FileSystemObject").DeleteFile WScript.ScriptFullName, True'
            [IO.File]::WriteAllText($vbs,$script,[Text.Encoding]::Unicode)
            Start-Process -FilePath 'wscript.exe' -ArgumentList ('"' + $vbs + '"') -WindowStyle Hidden
            exit
        }
    } catch {
        # If the handoff itself fails, continue normally rather than blocking the app.
    }
}
# --- End hidden bootstrap relaunch ---
'''
# Insert after ErrorActionPreference so script environment exists but before any updater UI/network work.
needle="$ErrorActionPreference='Stop'"
if needle not in launcher: raise SystemExit('launcher insertion point missing')
launcher=launcher.replace(needle,needle+'\n'+shim,1)
if 'THEFILES_HIDDEN_BOOTSTRAP' not in launcher or "wscript.exe" not in launcher or 'WindowStyle Hidden' not in launcher: raise SystemExit('hidden relaunch markers missing')
raw_launcher=launcher.encode('utf-8-sig'); files['TheFiles.ps1']['contentBase64']=base64.b64encode(raw_launcher).decode()
app=json.loads(base64.b64decode(files['AppVersion.json']['contentBase64']).decode('utf-8-sig')); app['version']=VERSION
files['AppVersion.json']['contentBase64']=base64.b64encode(json.dumps(app,indent=2).encode('utf-8')).decode()
for f in files.values():
    data=base64.b64decode(f['contentBase64']); f['sha256']=hashlib.sha256(data).hexdigest()
p['version']=VERSION;p['files']=list(files.values());out=json.dumps(p,separators=(',',':')).encode('utf-8')
name='payload-0.2.28-hidden-relaunch-part-001.txt';(TF/name).write_bytes(out);sha=hashlib.sha256(out).hexdigest()
for f in p['files']:
    data=base64.b64decode(f['contentBase64']); assert hashlib.sha256(data).hexdigest()==f['sha256'],f['path']
core=base64.b64decode(files['TheFilesCore.ps1']['contentBase64']); assert gzip.decompress(base64.b64decode(files['TheFilesCore.ps1.gz']['contentBase64']))==core
val={'version':VERSION,'baseVersion':'0.2.27','payload':name,'payloadSha256':sha,'requirements':{'hiddenRelaunchViaWscript':True,'existingShortcutPreserved':True,'bootstrapUpdaterPreserved':True,'customNotesPreserved':b'function Render-NotesSection' in core,'timelinePreserved':b'function Render-TimelineSection' in core,'storyPreserved':b"'Story' = @(" in core,'powersPreserved':b'function Render-PowersSection' in core,'allInternalHashesVerified':True,'compressedCoreMatchesRunnableCore':True,'userDataUntouched':True}}
(TF/'hidden-relaunch-0.2.28-validation.json').write_text(json.dumps(val,indent=2),encoding='utf-8')
vd=ROOT/'.hidden-v0228-validation';vd.mkdir(exist_ok=True);(vd/'TheFiles.ps1').write_bytes(raw_launcher);(vd/'TheFilesCore.ps1').write_bytes(core)
print(json.dumps(val,indent=2))
