from pathlib import Path
import json

root = Path('tome-build')
main = root / 'main.js'
pkg = root / 'package.json'

s = main.read_text(encoding='utf-8')
s = s.replace("const APP_VERSION = '0.1.6';", "const APP_VERSION = '0.1.7';")

start = s.index('async function updaterLog(message) {')
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

function psQuote(value) {
  return "'" + String(value).replace(/'/g, "''") + "'";
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

    const helperPath = path.join(tempDir, 'apply-update.ps1');
    const currentExe = process.execPath;
    const pid = process.pid;

    const ps = [
      "$ErrorActionPreference = 'Stop'",
      "$mutex = New-Object System.Threading.Mutex($false, 'Local\\VeyrStudio.TheTome.Updater')",
      "$hasMutex = $false",
      "try {",
      "  $hasMutex = $mutex.WaitOne(0)",
      "  if (-not $hasMutex) { exit 0 }",
      `  $targetPid = ${pid}`,
      `  $installer = ${psQuote(installerPath)}`,
      `  $appExe = ${psQuote(currentExe)}`,
      "  $deadline = (Get-Date).AddMinutes(2)",
      "  while ((Get-Date) -lt $deadline) {",
      "    $p = Get-Process -Id $targetPid -ErrorAction SilentlyContinue",
      "    if (-not $p) { break }",
      "    Start-Sleep -Milliseconds 250",
      "  }",
      "  if (Get-Process -Id $targetPid -ErrorAction SilentlyContinue) { exit 2 }",
      "  $install = Start-Process -FilePath $installer -ArgumentList '/S' -WindowStyle Hidden -PassThru",
      "  $install.WaitForExit()",
      "  if ($install.ExitCode -ne 0) { exit $install.ExitCode }",
      "  Start-Sleep -Milliseconds 700",
      "  if (Test-Path -LiteralPath $appExe) {",
      "    Start-Process -FilePath $appExe -WindowStyle Hidden",
      "  }",
      "} finally {",
      "  if ($hasMutex) { try { $mutex.ReleaseMutex() } catch {} }",
      "  if ($mutex) { $mutex.Dispose() }",
      "}"
    ].join("\r\n");

    await fsp.writeFile(helperPath, ps, 'utf8');
    await updaterLog(`launching hidden updater helper ${helperPath}`);

    const { spawn } = require('child_process');
    const child = spawn('powershell.exe', [
      '-NoProfile',
      '-NonInteractive',
      '-ExecutionPolicy', 'Bypass',
      '-WindowStyle', 'Hidden',
      '-File', helperPath
    ], {
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
p['version'] = '0.1.7'
pkg.write_text(json.dumps(p, indent=2) + '\n', encoding='utf-8')

print('Patched The Tome to v0.1.7 with hidden single-instance updater helper.')
