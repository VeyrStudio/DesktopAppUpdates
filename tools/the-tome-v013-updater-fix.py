from pathlib import Path
import json

root = Path('tome-build')
main = root / 'main.js'
pkg = root / 'package.json'

s = main.read_text(encoding='utf-8')
s = s.replace("const { app, BrowserWindow, dialog, ipcMain, clipboard, nativeImage, shell } = require('electron');", "const { app, BrowserWindow, dialog, ipcMain, clipboard, nativeImage, shell, net } = require('electron');")
s = s.replace("const APP_VERSION = '0.1.2';", "const APP_VERSION = '0.1.3';")

start = s.index('async function fetchJson(url) {')
end = s.index('\nfunction createWindow()', start)
new_block = r'''async function updaterLog(message) {
  try {
    await fsp.mkdir(dataRoot(), { recursive:true });
    await fsp.appendFile(path.join(dataRoot(), 'updater.log'), `[${new Date().toISOString()}] ${message}\r\n`, 'utf8');
  } catch {}
}

function showUpdateStatus(message) {
  try {
    if (!mainWindow || mainWindow.isDestroyed()) return;
    mainWindow.setTitle(`The Tome — ${message}`);
    if (!mainWindow.webContents.isLoading()) {
      const text = JSON.stringify(message);
      mainWindow.webContents.executeJavaScript(`(() => {
        let el = document.getElementById('tome-update-status');
        if (!el) {
          el = document.createElement('div');
          el.id = 'tome-update-status';
          el.style.cssText = 'position:fixed;right:18px;bottom:18px;z-index:999999;padding:10px 15px;border:1px solid #9c7441;border-radius:8px;background:rgba(20,9,25,.96);color:#ead0a0;font:600 14px Georgia,serif;box-shadow:0 8px 26px #000b;pointer-events:none';
          document.body.appendChild(el);
        }
        el.textContent = ${text};
      })()`).catch(()=>{});
    }
  } catch {}
}

async function fetchJson(url) {
  const response = await net.fetch(url, {
    method: 'GET',
    headers: { 'User-Agent': `TheTome/${APP_VERSION}`, 'Cache-Control': 'no-cache' },
    cache: 'no-store',
    redirect: 'follow'
  });
  if (!response.ok) throw new Error(`Update server returned HTTP ${response.status}.`);
  return await response.json();
}

async function downloadToFile(url, destination) {
  const response = await net.fetch(url, {
    method: 'GET',
    headers: { 'User-Agent': `TheTome/${APP_VERSION}`, 'Cache-Control': 'no-cache' },
    cache: 'no-store',
    redirect: 'follow'
  });
  if (!response.ok) throw new Error(`Update download returned HTTP ${response.status}.`);
  const bytes = Buffer.from(await response.arrayBuffer());
  if (!bytes.length) throw new Error('Downloaded update was empty.');
  await fsp.writeFile(destination, bytes);
  return destination;
}

function cmdQuote(value) {
  return `"${String(value).replace(/"/g, '""')}"`;
}

async function startAutomaticUpdateCheck() {
  if (startupUpdateRunning || !app.isPackaged) return;
  startupUpdateRunning = true;
  try {
    await updaterLog(`startup check; current=${APP_VERSION}`);
    const manifest = await fetchJson(`${UPDATE_MANIFEST}?t=${Date.now()}`);
    await updaterLog(`manifest version=${manifest.version || 'missing'}`);
    if (!manifest.version || semverCmp(manifest.version, APP_VERSION) <= 0) {
      await updaterLog('no update required');
      return;
    }
    if (!manifest.url || !manifest.sha256) throw new Error('Update manifest is incomplete.');

    showUpdateStatus(`Updating to v${manifest.version}…`);
    const tempDir = await fsp.mkdtemp(path.join(os.tmpdir(), 'the-tome-update-'));
    const installerPath = path.join(tempDir, `The_Tome_Setup_${manifest.version}.exe`);
    await updaterLog(`downloading ${manifest.url}`);
    await downloadToFile(manifest.url, installerPath);

    showUpdateStatus('Verifying update…');
    const actualHash = await fileHash(installerPath);
    if (actualHash.toLowerCase() !== String(manifest.sha256).toLowerCase()) {
      await fsp.rm(tempDir, { recursive:true, force:true }).catch(()=>{});
      throw new Error(`Downloaded update failed SHA-256 verification (${actualHash}).`);
    }
    await updaterLog('SHA-256 verified');

    const helperPath = path.join(tempDir, 'apply-update.cmd');
    const currentExe = process.execPath;
    const pid = process.pid;
    const lines = [
      '@echo off',
      'setlocal',
      ':waitfortome',
      `tasklist /FI "PID eq ${pid}" 2>NUL | find "${pid}" >NUL`,
      'if not errorlevel 1 (',
      '  ping 127.0.0.1 -n 2 >NUL',
      '  goto waitfortome',
      ')',
      `start "" /wait ${cmdQuote(installerPath)} /S`,
      'ping 127.0.0.1 -n 2 >NUL',
      `if exist ${cmdQuote(currentExe)} start "" ${cmdQuote(currentExe)}`,
      `del /q ${cmdQuote(installerPath)} >NUL 2>&1`,
      'del /q "%~f0" >NUL 2>&1',
      'endlocal'
    ];
    await fsp.writeFile(helperPath, lines.join('\r\n'), 'ascii');
    await updaterLog(`launching updater helper ${helperPath}`);

    const { spawn } = require('child_process');
    const child = spawn('cmd.exe', ['/d','/s','/c', helperPath], {
      detached: true,
      windowsHide: true,
      stdio: 'ignore',
      cwd: tempDir
    });
    child.unref();

    showUpdateStatus('Installing update…');
    setTimeout(() => app.exit(0), 900);
  } catch (e) {
    const msg = e && e.stack ? e.stack : String(e);
    await updaterLog(`ERROR ${msg}`);
    console.warn('[The Tome updater]', e.message);
    try {
      if (mainWindow && !mainWindow.isDestroyed()) mainWindow.setTitle('The Tome');
    } catch {}
  } finally {
    startupUpdateRunning = false;
  }
}
'''
s = s[:start] + new_block + s[end:]
main.write_text(s, encoding='utf-8')

p = json.loads(pkg.read_text(encoding='utf-8'))
p['version'] = '0.1.3'
pkg.write_text(json.dumps(p, indent=2) + '\n', encoding='utf-8')

print('Patched The Tome to v0.1.3 with robust automatic updater and diagnostics.')
