from pathlib import Path

root = Path("apps/constellation")
html = root / "src" / "index.html"
js = root / "src" / "app.js"
rust = root / "src-tauri" / "src" / "lib.rs"
cargo = root / "src-tauri" / "Cargo.toml"

# Settings UI
h = html.read_text(encoding="utf-8")
old = '''<section id="settingsView" class="view"><div class="panel settings-panel"><h2>Constellation</h2><p>Desktop app version <strong id="appVersion">—</strong></p><p id="updateStatus">Updates are checked automatically when Constellation opens.</p><button id="checkUpdateBtn" class="primary-btn">Check for Updates</button></div></section>'''
new = '''<section id="settingsView" class="view"><div class="panel settings-panel"><h2>Constellation</h2><p>Desktop app version <strong id="appVersion">—</strong></p><p id="updateStatus">Updates are checked automatically when Constellation opens.</p><button id="checkUpdateBtn" class="primary-btn">Check for Updates</button><hr style="margin:28px 0;border:0;border-top:1px solid rgba(255,255,255,.12)"><h3>Desktop Shortcut Icon</h3><p>Repair the shortcut to use Constellation’s built-in icon, or choose your own Windows .ico file.</p><div style="display:flex;gap:10px;flex-wrap:wrap"><button id="repairShortcutIconBtn" class="primary-btn" type="button">Use Constellation Icon</button><button id="chooseShortcutIconBtn" class="ghost-btn" type="button">Choose Custom .ico</button><input id="shortcutIconFile" type="file" accept=".ico,image/x-icon" hidden></div><p id="shortcutIconStatus"></p></div></section>'''
if old not in h:
    raise SystemExit("Settings panel block not found")
html.write_text(h.replace(old, new, 1), encoding="utf-8")

# Frontend commands
j = js.read_text(encoding="utf-8")
append = r'''
const shortcutIconFile=$("#shortcutIconFile");
$("#chooseShortcutIconBtn")?.addEventListener("click",()=>shortcutIconFile?.click());
shortcutIconFile?.addEventListener("change",(e)=>{
  const file=e.target.files?.[0];
  const status=$("#shortcutIconStatus");
  if(!file||!tauriInvoke)return;
  if(!file.name.toLowerCase().endsWith(".ico")){
    if(status)status.textContent="Please choose a Windows .ico file.";
    return;
  }
  const reader=new FileReader();
  reader.onload=async()=>{
    try{
      if(status)status.textContent="Changing desktop shortcut icon…";
      await tauriInvoke("set_desktop_shortcut_icon",{iconData:String(reader.result)});
      if(status)status.textContent="Desktop shortcut icon changed.";
    }catch(err){
      if(status)status.textContent=String(err);
    }finally{
      shortcutIconFile.value="";
    }
  };
  reader.readAsDataURL(file);
});
$("#repairShortcutIconBtn")?.addEventListener("click",async()=>{
  const status=$("#shortcutIconStatus");
  if(!tauriInvoke)return;
  try{
    if(status)status.textContent="Repairing desktop shortcut icon…";
    await tauriInvoke("reset_desktop_shortcut_icon");
    if(status)status.textContent="Desktop shortcut now uses the Constellation app icon.";
  }catch(err){
    if(status)status.textContent=String(err);
  }
});
'''
if 'set_desktop_shortcut_icon' not in j:
    js.write_text(j + "\n" + append, encoding="utf-8")

# Rust backend
r = rust.read_text(encoding="utf-8")
if 'use base64::Engine;' not in r:
    r = 'use base64::Engine;\n' + r

insert_before = '''#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {'''
backend = r'''
fn ps_quote(value: &str) -> String {
    format!("'{}'", value.replace('\'', "''"))
}

fn write_desktop_shortcut(icon_path: &std::path::Path) -> Result<(), String> {
    let exe = std::env::current_exe().map_err(|e| format!("Could not locate Constellation: {e}"))?;
    let exe_s = exe.to_string_lossy().to_string();
    let icon_s = icon_path.to_string_lossy().to_string();
    let script = format!(
        "$desktop=[Environment]::GetFolderPath('Desktop'); \
         $shortcut=Join-Path $desktop 'Constellation.lnk'; \
         $ws=New-Object -ComObject WScript.Shell; \
         $s=$ws.CreateShortcut($shortcut); \
         $s.TargetPath={exe}; \
         $s.WorkingDirectory=Split-Path {exe}; \
         $s.IconLocation={icon}; \
         $s.Save();",
        exe = ps_quote(&exe_s),
        icon = ps_quote(&(icon_s + ",0"))
    );
    let status = Command::new("powershell")
        .args(["-NoProfile", "-NonInteractive", "-Command", &script])
        .status()
        .map_err(|e| format!("Could not update desktop shortcut: {e}"))?;
    if !status.success() {
        return Err("Windows could not update the desktop shortcut.".into());
    }
    Ok(())
}

#[tauri::command]
fn set_desktop_shortcut_icon(icon_data: String) -> Result<(), String> {
    let encoded = icon_data
        .split_once(',')
        .map(|(_, data)| data)
        .unwrap_or(icon_data.as_str());
    let bytes = base64::engine::general_purpose::STANDARD
        .decode(encoded)
        .map_err(|e| format!("Could not read icon file: {e}"))?;
    if bytes.len() < 6 || &bytes[0..4] != [0, 0, 1, 0] {
        return Err("That file is not a valid Windows .ico file.".into());
    }
    let base = std::env::var_os("LOCALAPPDATA")
        .map(std::path::PathBuf::from)
        .unwrap_or_else(std::env::temp_dir)
        .join("VeyrStudio")
        .join("Constellation");
    fs::create_dir_all(&base).map_err(|e| format!("Could not create icon folder: {e}"))?;
    let icon = base.join("desktop-shortcut.ico");
    fs::write(&icon, bytes).map_err(|e| format!("Could not save shortcut icon: {e}"))?;
    write_desktop_shortcut(&icon)
}

#[tauri::command]
fn reset_desktop_shortcut_icon() -> Result<(), String> {
    let exe = std::env::current_exe().map_err(|e| format!("Could not locate Constellation: {e}"))?;
    write_desktop_shortcut(&exe)
}

'''
if 'fn set_desktop_shortcut_icon' not in r:
    if insert_before not in r:
        raise SystemExit("Rust run marker not found")
    r = r.replace(insert_before, backend + insert_before, 1)

old_handler = 'tauri::generate_handler![app_version, check_for_update, install_update]'
new_handler = 'tauri::generate_handler![app_version, check_for_update, install_update, set_desktop_shortcut_icon, reset_desktop_shortcut_icon]'
if old_handler in r:
    r = r.replace(old_handler, new_handler, 1)
elif new_handler not in r:
    raise SystemExit("Invoke handler block not found")
rust.write_text(r, encoding="utf-8")

# Dependency
c = cargo.read_text(encoding="utf-8")
if '\nbase64 = ' not in c:
    c += '\nbase64 = "0.22"\n'
cargo.write_text(c, encoding="utf-8")

print("Desktop shortcut icon controls applied.")
