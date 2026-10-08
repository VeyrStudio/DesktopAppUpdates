from pathlib import Path

root = Path("apps/constellation")
html = root / "src" / "index.html"
js = root / "src" / "app.js"
css = root / "src" / "styles.css"

h = html.read_text(encoding="utf-8")
old = '''<hr style="margin:28px 0;border:0;border-top:1px solid rgba(255,255,255,.12)"><h3>Desktop Shortcut Icon</h3><p>Repair the shortcut to use Constellation’s built-in icon, or choose your own Windows .ico file.</p><div style="display:flex;gap:10px;flex-wrap:wrap"><button id="repairShortcutIconBtn" class="primary-btn" type="button">Use Constellation Icon</button><button id="chooseShortcutIconBtn" class="ghost-btn" type="button">Choose Custom .ico</button><input id="shortcutIconFile" type="file" accept=".ico,image/x-icon" hidden></div><p id="shortcutIconStatus"></p>'''
new = '''<div class="settings-divider"></div><section class="settings-section"><div class="settings-section-copy"><h3>Desktop Shortcut Icon</h3><p>Use Constellation’s built-in icon, or drop a Windows <strong>.ico</strong> file below to use your own.</p></div><div class="shortcut-icon-controls"><button id="repairShortcutIconBtn" class="primary-btn" type="button">Use Constellation Icon</button><div id="shortcutIconDropZone" class="shortcut-icon-drop" role="button" tabindex="0" aria-label="Drop a custom icon file or browse for one"><div class="shortcut-icon-drop-mark">✦</div><div><strong>Drop a custom .ico here</strong><span>or click to browse</span></div></div><button id="chooseShortcutIconBtn" class="ghost-btn shortcut-browse-btn" type="button">Browse for .ico</button><input id="shortcutIconFile" type="file" accept=".ico,image/x-icon" hidden></div><p id="shortcutIconStatus" class="shortcut-icon-status" aria-live="polite"></p></section>'''
if old not in h:
    raise SystemExit("Current shortcut icon settings block not found")
html.write_text(h.replace(old, new, 1), encoding="utf-8")

j = js.read_text(encoding="utf-8")
start = j.find('const shortcutIconFile=$("#shortcutIconFile");')
if start < 0:
    raise SystemExit("Shortcut icon JS start not found")
replacement = r'''const shortcutIconFile=$("#shortcutIconFile");
const shortcutIconDropZone=$("#shortcutIconDropZone");

async function applyShortcutIconFile(file){
  const status=$("#shortcutIconStatus");
  if(!file||!tauriInvoke)return;
  if(!file.name.toLowerCase().endsWith(".ico")){
    if(status)status.textContent="Please use a Windows .ico file.";
    return;
  }
  const reader=new FileReader();
  reader.onload=async()=>{
    try{
      if(status)status.textContent="Changing desktop shortcut icon…";
      await tauriInvoke("set_desktop_shortcut_icon",{iconData:String(reader.result)});
      if(status)status.textContent="Desktop shortcut icon changed to " + file.name + ".";
    }catch(err){
      if(status)status.textContent=String(err);
    }finally{
      if(shortcutIconFile)shortcutIconFile.value="";
      shortcutIconDropZone?.classList.remove("drag-over");
    }
  };
  reader.readAsDataURL(file);
}

$("#chooseShortcutIconBtn")?.addEventListener("click",()=>shortcutIconFile?.click());
shortcutIconDropZone?.addEventListener("click",()=>shortcutIconFile?.click());
shortcutIconDropZone?.addEventListener("keydown",(e)=>{
  if(e.key==="Enter"||e.key===" "){e.preventDefault();shortcutIconFile?.click();}
});
["dragenter","dragover"].forEach(type=>shortcutIconDropZone?.addEventListener(type,(e)=>{
  e.preventDefault();e.stopPropagation();shortcutIconDropZone.classList.add("drag-over");
}));
["dragleave","drop"].forEach(type=>shortcutIconDropZone?.addEventListener(type,(e)=>{
  e.preventDefault();e.stopPropagation();shortcutIconDropZone.classList.remove("drag-over");
}));
shortcutIconDropZone?.addEventListener("drop",(e)=>applyShortcutIconFile(e.dataTransfer?.files?.[0]));
shortcutIconFile?.addEventListener("change",(e)=>applyShortcutIconFile(e.target.files?.[0]));

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
j = j[:start] + replacement
js.write_text(j, encoding="utf-8")

c = css.read_text(encoding="utf-8")
old_css = '.settings-panel{max-width:700px}.settings-panel p{color:#735C7C}'
new_css = '''.settings-panel{max-width:980px;padding:28px 30px}.settings-panel>h2{font-size:30px}.settings-panel p{color:#735C7C;line-height:1.55}.settings-divider{height:1px;background:var(--line);margin:28px 0}.settings-section{display:grid;grid-template-columns:minmax(240px,.75fr) minmax(380px,1.25fr);gap:32px;align-items:start}.settings-section-copy h3{margin:0 0 8px;color:#55127E;font-size:22px}.settings-section-copy p{margin:0}.shortcut-icon-controls{display:grid;grid-template-columns:1fr;gap:12px}.shortcut-icon-drop{min-height:150px;border:2px dashed #CDB5D9;border-radius:16px;background:linear-gradient(180deg,#FFF,#FAF5FC);display:flex;align-items:center;justify-content:center;gap:14px;text-align:left;padding:24px;color:#5A2D6B;transition:.15s;outline:none}.shortcut-icon-drop:hover,.shortcut-icon-drop:focus,.shortcut-icon-drop.drag-over{border-color:#8E4CC2;background:#F4E9FA;box-shadow:0 0 0 4px rgba(142,76,194,.08)}.shortcut-icon-drop-mark{width:46px;height:46px;border-radius:50%;display:grid;place-items:center;background:#EEE0F7;color:#6E1294;font-size:24px;flex:0 0 auto}.shortcut-icon-drop strong{display:block;font-size:17px}.shortcut-icon-drop span{display:block;margin-top:4px;color:#8A6B95;font-size:13px}.shortcut-browse-btn{justify-self:start}.shortcut-icon-status{margin:12px 0 0;min-height:24px;font-family:"Courier New",monospace;font-size:13px}'''
if old_css not in c:
    raise SystemExit("Settings CSS block not found")
c = c.replace(old_css, new_css, 1)
c += '\n@media(max-width:900px){.settings-section{grid-template-columns:1fr}.settings-panel{padding:22px}.shortcut-icon-drop{min-height:130px}}\n'
css.write_text(c, encoding="utf-8")

print("Settings layout and drag/drop shortcut icon control applied.")
