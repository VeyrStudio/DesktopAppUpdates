from pathlib import Path
import re

root = Path("apps/constellation")
html = root / "src" / "index.html"
js = root / "src" / "app.js"
css = root / "src" / "styles.css"

# Replace the entire Settings view so matching cannot fail on earlier wording/layout changes.
h = html.read_text(encoding="utf-8")
settings = '''<section id="settingsView" class="view"><div class="panel settings-panel"><h2>Constellation</h2><p>Desktop app version <strong id="appVersion">—</strong></p><p id="updateStatus">Updates are checked automatically when Constellation opens.</p><button id="checkUpdateBtn" class="primary-btn">Check for Updates</button><div class="settings-divider"></div><section class="settings-section"><div class="settings-section-copy"><h3>Desktop Shortcut Icon</h3><p>Use Constellation’s built-in icon, or drop almost any image file below. Constellation will convert it and create or replace the desktop shortcut for you.</p></div><div class="shortcut-icon-controls"><button id="repairShortcutIconBtn" class="primary-btn" type="button">Use Constellation Icon</button><div id="shortcutIconDropZone" class="shortcut-icon-drop" role="button" tabindex="0" aria-label="Drop a custom icon file or browse for one"><div class="shortcut-icon-drop-mark">✦</div><div><strong>Drop an image here</strong><span>PNG, JPG, JPEG, WEBP, GIF, BMP, SVG, ICO and other browser-supported images</span></div></div><button id="chooseShortcutIconBtn" class="ghost-btn shortcut-browse-btn" type="button">Browse for image</button><input id="shortcutIconFile" type="file" accept="image/*,.ico" hidden></div><p id="shortcutIconStatus" class="shortcut-icon-status" aria-live="polite"></p></section></div></section>'''
new_h, count = re.subn(r'<section id="settingsView" class="view">.*?</section>\s*</main>', settings + '\n</main>', h, count=1, flags=re.S)
if count != 1:
    raise SystemExit("Settings view not found")
html.write_text(new_h, encoding="utf-8")

# Replace the shortcut-icon JS tail with drop-zone aware handling.
j = js.read_text(encoding="utf-8")
start = j.find('const shortcutIconFile=$("#shortcutIconFile");')
if start < 0:
    raise SystemExit("Shortcut icon JS start not found")
replacement = r'''const shortcutIconFile=$("#shortcutIconFile");
const shortcutIconDropZone=$("#shortcutIconDropZone");

async function applyShortcutIconFile(file){
  const status=$("#shortcutIconStatus");
  if(!file||!tauriInvoke)return;
  try{
    if(status)status.textContent="Preparing image…";
    let iconData;
    if(file.name.toLowerCase().endsWith(".ico")){
      iconData=await new Promise((resolve,reject)=>{
        const reader=new FileReader();
        reader.onload=()=>resolve(String(reader.result));
        reader.onerror=()=>reject(new Error("Could not read that icon file."));
        reader.readAsDataURL(file);
      });
    }else{
      iconData=await new Promise((resolve,reject)=>{
        const url=URL.createObjectURL(file);
        const img=new Image();
        img.onload=()=>{
          try{
            const size=256;
            const canvas=document.createElement("canvas");
            canvas.width=size; canvas.height=size;
            const ctx=canvas.getContext("2d");
            ctx.clearRect(0,0,size,size);
            const scale=Math.min(size/img.naturalWidth,size/img.naturalHeight);
            const w=Math.max(1,Math.round(img.naturalWidth*scale));
            const h=Math.max(1,Math.round(img.naturalHeight*scale));
            const x=Math.round((size-w)/2);
            const y=Math.round((size-h)/2);
            ctx.drawImage(img,x,y,w,h);
            resolve(canvas.toDataURL("image/png"));
          }catch(err){reject(err);}
          finally{URL.revokeObjectURL(url);}
        };
        img.onerror=()=>{URL.revokeObjectURL(url);reject(new Error("That image format could not be opened."));};
        img.src=url;
      });
    }
    if(status)status.textContent="Changing desktop shortcut icon…";
    const shortcutPath=await tauriInvoke("set_desktop_shortcut_icon",{iconData});
    if(status)status.textContent="Desktop shortcut created with " + file.name + ": " + shortcutPath;
  }catch(err){
    if(status)status.textContent=String(err?.message||err);
  }finally{
    if(shortcutIconFile)shortcutIconFile.value="";
    shortcutIconDropZone?.classList.remove("drag-over");
  }
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
    const shortcutPath=await tauriInvoke("reset_desktop_shortcut_icon");
    if(status)status.textContent="Desktop shortcut recreated with the Constellation app icon: " + shortcutPath;
  }catch(err){
    if(status)status.textContent=String(err);
  }
});
'''
js.write_text(j[:start] + replacement, encoding="utf-8")

# Append overrides instead of depending on exact existing CSS text.
c = css.read_text(encoding="utf-8")
c += '''
.settings-panel{max-width:980px!important;padding:28px 30px}
.settings-panel>h2{font-size:30px}
.settings-panel p{color:#735C7C;line-height:1.55}
.settings-divider{height:1px;background:var(--line);margin:28px 0}
.settings-section{display:grid;grid-template-columns:minmax(240px,.75fr) minmax(380px,1.25fr);gap:32px;align-items:start}
.settings-section-copy h3{margin:0 0 8px;color:#55127E;font-size:22px}
.settings-section-copy p{margin:0}
.shortcut-icon-controls{display:grid;grid-template-columns:1fr;gap:12px}
.shortcut-icon-drop{min-height:150px;border:2px dashed #CDB5D9;border-radius:16px;background:linear-gradient(180deg,#FFF,#FAF5FC);display:flex;align-items:center;justify-content:center;gap:14px;text-align:left;padding:24px;color:#5A2D6B;transition:.15s;outline:none}
.shortcut-icon-drop:hover,.shortcut-icon-drop:focus,.shortcut-icon-drop.drag-over{border-color:#8E4CC2;background:#F4E9FA;box-shadow:0 0 0 4px rgba(142,76,194,.08)}
.shortcut-icon-drop-mark{width:46px;height:46px;border-radius:50%;display:grid;place-items:center;background:#EEE0F7;color:#6E1294;font-size:24px;flex:0 0 auto}
.shortcut-icon-drop strong{display:block;font-size:17px}
.shortcut-icon-drop span{display:block;margin-top:4px;color:#8A6B95;font-size:13px}
.shortcut-browse-btn{justify-self:start}
.shortcut-icon-status{margin:12px 0 0;min-height:24px;font-family:"Courier New",monospace;font-size:13px}
@media(max-width:900px){.settings-section{grid-template-columns:1fr}.settings-panel{padding:22px}.shortcut-icon-drop{min-height:130px}}
'''
css.write_text(c, encoding="utf-8")

print("Settings layout and drag/drop shortcut icon control applied.")
