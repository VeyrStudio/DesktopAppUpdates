from pathlib import Path
import json

root = Path('tome-build')
main = root / 'main.js'
renderer = root / 'renderer.js'
styles = root / 'styles.css'
pkg = root / 'package.json'

s = main.read_text(encoding='utf-8')
s = s.replace("const APP_VERSION = '0.1.7';", "const APP_VERSION = '0.1.8';")

# Keep the repaired updater and make manual checks visibly reusable.
needle = "async function startAutomaticUpdateCheck() {"
if needle not in s:
    raise SystemExit('v0.1.7 updater function not found')
s = s.replace(needle, "async function startAutomaticUpdateCheck(manual = false) {", 1)

old_guard = "  if (startupUpdateRunning || !app.isPackaged) return;"
new_guard = """  if (startupUpdateRunning) {
    if (manual) showUpdateStatus('An update check is already running…');
    return;
  }
  if (!app.isPackaged) {
    if (manual) showUpdateStatus('Update checks are available in the installed app.');
    return;
  }"""
s = s.replace(old_guard, new_guard, 1)

old_no_update = """    if (!manifest.version || semverCmp(manifest.version, APP_VERSION) <= 0) {
      await updaterLog('no update required');
      return;
    }"""
new_no_update = """    if (!manifest.version || semverCmp(manifest.version, APP_VERSION) <= 0) {
      await updaterLog('no update required');
      if (manual) {
        showUpdateStatus('The Tome is already up to date.');
        setTimeout(() => {
          try {
            if (mainWindow && !mainWindow.isDestroyed()) mainWindow.setTitle('The Tome');
          } catch {}
        }, 2600);
      }
      return;
    }"""
if old_no_update not in s:
    raise SystemExit('no-update block not found')
s = s.replace(old_no_update, new_no_update, 1)

# Add a safe renderer->main manual-update signal using a console message.
create_marker = "function createWindow()"
idx = s.index(create_marker)
# Patch after mainWindow is created by listening globally on webContents after did-finish-load registration point.
# Use app-level web-contents-created so no dependency on createWindow internals.
listener = r'''
app.on('web-contents-created', (_event, contents) => {
  contents.on('console-message', (_event2, _level, message) => {
    if (message === '__TOME_FORCE_UPDATE__') {
      startAutomaticUpdateCheck(true).catch(() => {});
    }
  });
});

'''
s = s[:idx] + listener + s[idx:]
main.write_text(s, encoding='utf-8')

r = renderer.read_text(encoding='utf-8')
manual_ui = r'''

// v0.1.8 manual update control
function ensureTomeUpdateNowButton() {
  if (document.getElementById('tome-update-now')) return;

  const button = document.createElement('button');
  button.id = 'tome-update-now';
  button.type = 'button';
  button.className = 'tome-update-now';
  button.textContent = 'Update Now';
  button.title = 'Check for and install The Tome updates now';
  button.addEventListener('click', () => {
    button.disabled = true;
    const previous = button.textContent;
    button.textContent = 'Checking…';
    console.log('__TOME_FORCE_UPDATE__');
    setTimeout(() => {
      if (document.body.contains(button)) {
        button.disabled = false;
        button.textContent = previous;
      }
    }, 3500);
  });

  const gear = Array.from(document.querySelectorAll('button')).find(b => {
    const t = ((b.getAttribute('title') || '') + ' ' + (b.getAttribute('aria-label') || '') + ' ' + (b.textContent || '')).toLowerCase();
    return t.includes('setting') || t.trim() === '⚙' || t.trim() === '⚙️';
  });

  if (gear && gear.parentElement) {
    gear.parentElement.insertBefore(button, gear);
  } else {
    button.classList.add('tome-update-now-floating');
    document.body.appendChild(button);
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', ensureTomeUpdateNowButton, { once:true });
} else {
  ensureTomeUpdateNowButton();
}
setTimeout(ensureTomeUpdateNowButton, 800);
setTimeout(ensureTomeUpdateNowButton, 2200);
'''
renderer.write_text(r + manual_ui, encoding='utf-8')

css = r'''

/* v0.1.8 manual update button */
.tome-update-now {
  appearance: none;
  border: 1px solid rgba(193, 156, 94, .72);
  border-radius: 8px;
  background: linear-gradient(180deg, rgba(74, 35, 92, .96), rgba(39, 18, 51, .98));
  color: #f0ddb7;
  padding: 8px 13px;
  margin: 0 7px;
  font: 600 13px "Cormorant Garamond", Georgia, serif;
  letter-spacing: .02em;
  cursor: pointer;
  box-shadow: inset 0 1px rgba(255,255,255,.06), 0 3px 10px rgba(0,0,0,.24);
}
.tome-update-now:hover:not(:disabled) {
  filter: brightness(1.12);
  border-color: rgba(220, 186, 119, .92);
}
.tome-update-now:disabled {
  opacity: .62;
  cursor: wait;
}
.tome-update-now-floating {
  position: fixed;
  top: 72px;
  right: 18px;
  z-index: 99990;
}
'''
styles.write_text(styles.read_text(encoding='utf-8') + css, encoding='utf-8')

p = json.loads(pkg.read_text(encoding='utf-8'))
p['version'] = '0.1.8'
pkg.write_text(json.dumps(p, indent=2) + '\n', encoding='utf-8')

print('Patched The Tome to v0.1.8 with manual Update Now button plus automatic updates.')
