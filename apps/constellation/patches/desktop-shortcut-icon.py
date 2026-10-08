from pathlib import Path

root = Path("apps/constellation")
html = root / "src" / "index.html"
js = root / "src" / "app.js"
rust = root / "src-tauri" / "src" / "lib.rs"
cargo = root / "src-tauri" / "Cargo.toml"

# Settings UI
h = html.read_text(encoding="utf-8")
if 'id="chooseShortcutIconBtn"' not in h:
    anchor = '<button id="checkUpdateBtn" class="primary-btn">Check for Updates</button>'
    controls = '''<button id="checkUpdateBtn" class="primary-btn">Check for Updates</button><hr style="margin:28px 0;border:0;border-top:1px solid rgba(255,255,255,.12)"><h3>Desktop Shortcut Icon</h3><p>Repair the shortcut to use Constellation’s built-in icon, or choose your own Windows .ico file.</p><div style="display:flex;gap:10px;flex-wrap:wrap"><button id="repairShortcutIconBtn" class="primary-btn" type="button">Use Constellation Icon</button><button id="chooseShortcutIconBtn" class="ghost-btn" type="button">Choose Custom .ico</button><input id="shortcutIconFile" type="file" accept=".ico,image/x-icon" hidden></div><p id="shortcutIconStatus"></p>'''
    if anchor not in h:
        raise SystemExit("Check for Updates button not found")
    h = h.replace(anchor, controls, 1)
    html.write_text(h, encoding="utf-8")

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
if 'use std::os::windows::process::CommandExt;' not in r:
    r = 'use std::os::windows::process::CommandExt;\n' + r

insert_before = '''#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {'''
backend = r'''
fn ps_quote(value: &str) -> String {
    format!("'{}'", value.replace('\'', "''"))
}

fn write_desktop_shortcut(icon_path: &std::path::Path) -> Result<String, String> {
    let exe = std::env::current_exe().map_err(|e| format!("Could not locate Constellation: {e}"))?;
    let exe_s = exe.to_string_lossy().to_string();
    let icon_s = icon_path.to_string_lossy().to_string();
    let script = format!(
        "$ErrorActionPreference='Stop'; \
         $ws=New-Object -ComObject WScript.Shell; \
         $desktop=$ws.SpecialFolders.Item('Desktop'); \
         if([string]::IsNullOrWhiteSpace($desktop)){{$desktop=[Environment]::GetFolderPath('Desktop')}}; \
         if(-not (Test-Path -LiteralPath $desktop)){{New-Item -ItemType Directory -Path $desktop -Force | Out-Null}}; \
         $shortcut=Join-Path $desktop 'Constellation.lnk'; \
         if(Test-Path -LiteralPath $shortcut){{Remove-Item -LiteralPath $shortcut -Force}}; \
         $s=$ws.CreateShortcut($shortcut); \
         $s.TargetPath={exe}; \
         $s.WorkingDirectory=[System.IO.Path]::GetDirectoryName({exe}); \
         $s.IconLocation={icon}; \
         $s.Description='Constellation'; \
         $s.Save(); \
         if(-not (Test-Path -LiteralPath $shortcut)){{throw 'Shortcut file was not created.'}}; \
         Write-Output $shortcut;",
        exe = ps_quote(&exe_s),
        icon = ps_quote(&(icon_s + ",0"))
    );

    let mut command = Command::new("powershell.exe");
    command.creation_flags(0x08000000);
    let output = command
        .args([
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-WindowStyle",
            "Hidden",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            &script,
        ])
        .output()
        .map_err(|e| format!("Could not create desktop shortcut: {e}"))?;

    if !output.status.success() {
        let detail = String::from_utf8_lossy(&output.stderr).trim().to_string();
        return Err(if detail.is_empty() {
            "Windows could not create the desktop shortcut.".into()
        } else {
            format!("Windows could not create the desktop shortcut: {detail}")
        });
    }

    let shortcut = String::from_utf8_lossy(&output.stdout).trim().to_string();
    if shortcut.is_empty() {
        return Err("Windows reported success, but no shortcut path was returned.".into());
    }
    Ok(shortcut)
}

#[tauri::command]
fn set_desktop_shortcut_icon(icon_data: String) -> Result<String, String> {
    let encoded = icon_data
        .split_once(',')
        .map(|(_, data)| data)
        .unwrap_or(icon_data.as_str());
    let bytes = base64::engine::general_purpose::STANDARD
        .decode(encoded)
        .map_err(|e| format!("Could not read icon file: {e}"))?;
    let is_ico = bytes.len() >= 6 && &bytes[0..4] == [0, 0, 1, 0];
    let base = std::env::var_os("LOCALAPPDATA")
        .map(std::path::PathBuf::from)
        .unwrap_or_else(std::env::temp_dir)
        .join("VeyrStudio")
        .join("Constellation");
    fs::create_dir_all(&base).map_err(|e| format!("Could not create icon folder: {e}"))?;
    let icon = base.join("desktop-shortcut.ico");
    if is_ico {
        fs::write(&icon, bytes).map_err(|e| format!("Could not save shortcut icon: {e}"))?;
    } else {
        let decoded = image::load_from_memory(&bytes)
            .map_err(|e| format!("Could not read that image: {e}"))?;
        let rgba = decoded.to_rgba8();
        let (w, h) = rgba.dimensions();
        if w == 0 || h == 0 {
            return Err("That image has no usable dimensions.".into());
        }
        let scale = (256.0_f32 / w as f32).min(256.0_f32 / h as f32);
        let nw = ((w as f32 * scale).round() as u32).max(1);
        let nh = ((h as f32 * scale).round() as u32).max(1);
        let resized = image::imageops::resize(
            &rgba,
            nw,
            nh,
            image::imageops::FilterType::Lanczos3,
        );
        let mut canvas = image::RgbaImage::from_pixel(256, 256, image::Rgba([0, 0, 0, 0]));
        let x = ((256 - nw) / 2) as i64;
        let y = ((256 - nh) / 2) as i64;
        image::imageops::overlay(&mut canvas, &resized, x, y);
        image::DynamicImage::ImageRgba8(canvas)
            .save_with_format(&icon, image::ImageFormat::Ico)
            .map_err(|e| format!("Could not convert that image to a Windows icon: {e}"))?;
    }
    write_desktop_shortcut(&icon)
}

#[tauri::command]
fn reset_desktop_shortcut_icon() -> Result<String, String> {
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
if '\nimage = ' not in c:
    c += '\nimage = { version = "0.25", default-features = false, features = ["png", "ico"] }\n'
cargo.write_text(c, encoding="utf-8")

print("Desktop shortcut icon controls applied.")
