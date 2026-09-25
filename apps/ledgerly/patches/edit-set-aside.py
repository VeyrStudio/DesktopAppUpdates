from pathlib import Path

root = Path(__file__).resolve().parents[1]
html = root / "src" / "index.html"
js = root / "src" / "app.js"

h = html.read_text(encoding="utf-8")
s = js.read_text(encoding="utf-8")

if "permanentSetAside" not in s:
    s = s.replace("  groceryBudget: 0,", "  groceryBudget: 0,\n  permanentSetAside: 50,", 1)

candidates = [
    "setText(\"stat-set-aside\", money(50));",
    "setText('stat-set-aside', money(50));",
    'document.getElementById("stat-set-aside").textContent = money(50);',
]
changed = False
for old in candidates:
    if old in s:
        s = s.replace("money(50)", "money(Number(state.permanentSetAside ?? 50))", 1)
        changed = True
        break

if not changed and "stat-set-aside" in s:
    pos = s.index("stat-set-aside")
    start = max(0, pos - 500)
    end = min(len(s), pos + 500)
    block = s[start:end]
    if "50" in block:
        block2 = block.replace("50", "Number(state.permanentSetAside ?? 50)", 1)
        s = s[:start] + block2 + s[end:]
        changed = True

if not changed:
    raise SystemExit("Set Aside calculation not found.")

if 'id="permanent-set-aside-form"' not in h:
    anchor = '<section class="page" id="page-settings">'
    panel = '''<article class="panel section-gap"><div class="panel-head"><div><h2>Permanent Set Aside</h2><p>Change this whenever your budget changes.</p></div></div><form class="form-grid" id="permanent-set-aside-form"><label>Permanent Set Aside<input id="permanent-set-aside-amount" type="number" min="0" step="0.01" value="50.00"></label><button class="primary-btn" type="submit">Save Set Aside</button></form></article>'''
    h = h.replace(anchor, anchor + panel, 1)

s += '''
function syncPermanentSetAsideSetting(){
  const x=document.getElementById("permanent-set-aside-amount");
  if(x)x.value=Number(state.permanentSetAside??50).toFixed(2);
}
document.addEventListener("submit",e=>{
  if(e.target?.id!=="permanent-set-aside-form")return;
  e.preventDefault();
  const v=Number(document.getElementById("permanent-set-aside-amount").value);
  if(!Number.isFinite(v)||v<0)return alert("Enter a valid set-aside amount.");
  state.permanentSetAside=v; saveState(); renderAll(); syncPermanentSetAsideSetting();
});
setTimeout(syncPermanentSetAsideSetting,0);
'''

html.write_text(h,encoding="utf-8")
js.write_text(s,encoding="utf-8")
