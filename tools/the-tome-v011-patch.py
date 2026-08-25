from pathlib import Path
import json

root = Path('tome-build')
main = root / 'main.js'
pkg = root / 'package.json'

s = main.read_text(encoding='utf-8')
s = s.replace("const APP_VERSION = '0.1.0';", "const APP_VERSION = '0.1.1';")
s = s.replace('let mainWindow;', 'let mainWindow;\nlet startupUpdateRunning = false;')

old = '''async function fetchJson(url) {\n  return new Promise((resolve, reject) => {\n    const https = require('https');\n    https.get(url, { headers: { 'User-Agent': 'TheTome-Updater' } }, res => {\n      if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) return resolve(fetchJson(res.headers.location));\n      let data=''; res.on('data', c=>data+=c); res.on('end',()=>{ try{ resolve(JSON.parse(data)); }catch(e){reject(e);} });\n    }).on('error', reject);\n  });\n}\n'''

new = r'''async function fetchJson(url) {
  return new Promise((resolve, reject) => {
    const https = require('https');
    const req = https.get(url, { headers: { 'User-Agent': `TheTome/${APP_VERSION}` } }, res => {
      if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
        res.resume();
        return resolve(fetchJson(new URL(res.headers.location, url).toString()));
      }
      if (res.statusCode !== 200) {
        res.resume();
        return reject(new Error(`Update server returned HTTP ${res.statusCode}.`));
      }
      let data='';
      res.setEncoding('utf8');
      res.on('data', c=>data+=c);
      res.on('end',()=>{ try{ resolve(JSON.parse(data)); }catch(e){reject(new Error('Update manifest could not be read.'));} });
    });
    req.setTimeout(12000, () => req.destroy(new Error('Update check timed out.')));
    req.on('error', reject);
  });
}

async function downloadToFile(url, destination) {
  return new Promise((resolve, reject) => {
    const https = require('https');
    const request = (target) => {
      const req = https.get(target, { headers: { 'User-Agent': `TheTome/${APP_VERSION}` } }, res => {
        if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
          res.resume();
          return request(new URL(res.headers.location, target).toString());
        }
        if (res.statusCode !== 200) {
          res.resume();
          return reject(new Error(`Update download returned HTTP ${res.statusCode}.`));
        }
        const out = fs.createWriteStream(destination);
        res.pipe(out);
        out.on('finish', () => out.close(() => resolve(destination)));
        out.on('error', reject);
      });
      req.setTimeout(30000, () => req.destroy(new Error('Update download timed out.')));
      req.on('error', reject);
    };
    request(url);
  });
}

async function startAutomaticUpdateCheck() {
  if (startupUpdateRunning || !app.isPackaged) return;
  startupUpdateRunning = true;
  try {
    const manifest = await fetchJson(UPDATE_MANIFEST);
    if (!manifest.version || semverCmp(manifest.version, APP_VERSION) <= 0) return;
    if (!manifest.url || !manifest.sha256) throw new Error('Update manifest is incomplete.');

    const tempDir = await fsp.mkdtemp(path.join(os.tmpdir(), 'the-tome-update-'));
    const installerPath = path.join(tempDir, `The_Tome_Setup_${manifest.version}.exe`);
    await downloadToFile(manifest.url, installerPath);
    const actualHash = await fileHash(installerPath);
    if (actualHash.toLowerCase() !== String(manifest.sha256).toLowerCase()) {
      await fsp.rm(tempDir, { recursive:true, force:true }).catch(()=>{});
      throw new Error('Downloaded update failed SHA-256 verification.');
    }

    const helperPath = path.join(tempDir, 'apply-update.ps1');
    const currentExe = process.execPath;
    const pid = process.pid;
    const ps = [
      '$ErrorActionPreference = "SilentlyContinue"',
      `Wait-Process -Id ${pid}`,
      `Start-Process -FilePath ${JSON.stringify(installerPath)} -ArgumentList '/S' -Wait`,
      'Start-Sleep -Milliseconds 800',
      `if (Test-Path ${JSON.stringify(currentExe)}) { Start-Process -FilePath ${JSON.stringify(currentExe)} }`,
      `Remove-Item -LiteralPath ${JSON.stringify(tempDir)} -Recurse -Force`
    ].join('\r\n');
    await fsp.writeFile(helperPath, ps, 'utf8');

    const { spawn } = require('child_process');
    const child = spawn('powershell.exe', ['-NoProfile','-ExecutionPolicy','Bypass','-WindowStyle','Hidden','-File', helperPath], { detached:true, windowsHide:true, stdio:'ignore' });
    child.unref();
    setTimeout(() => app.quit(), 250);
  } catch (e) {
    console.warn('[The Tome updater]', e.message);
  } finally {
    startupUpdateRunning = false;
  }
}
'''

if old not in s:
    raise SystemExit('Could not find old updater function to replace')
s = s.replace(old, new)
s = s.replace("  createWindow();\n  app.on('activate'", "  createWindow();\n  setTimeout(() => startAutomaticUpdateCheck(), 1800);\n  app.on('activate'")
main.write_text(s, encoding='utf-8')

p = json.loads(pkg.read_text(encoding='utf-8'))
p['version'] = '0.1.1'
pkg.write_text(json.dumps(p, indent=2) + '\n', encoding='utf-8')

print('Patched The Tome to v0.1.1 with automatic startup updates.')
