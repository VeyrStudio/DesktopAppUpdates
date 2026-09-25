from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
html = root / "src" / "index.html"
js = root / "src" / "app.js"

h = html.read_text(encoding="utf-8")
s = js.read_text(encoding="utf-8")

if "permanentSetAside" not in s:
    s = s.replace("  groceryBudget: 0,", "  groceryBudget: 0,\n  permanentSetAside: 50,", 1)

changed = False
summary_line = "  const setAside = exp.planned + groceries.now + bills.upcoming;"
if summary_line in s:
    s = s.replace(
        summary_line,
        "  const setAside = exp.planned + groceries.now + bills.upcoming + Number(state.permanentSetAside ?? 50);",
        1,
    )
    changed = True

if not changed:
    raise SystemExit("Set Aside summary calculation not found.")

if 'id="edit-permanent-set-aside"' not in h:
    pattern = r'(<strong\s+id="stat-setaside">[^<]*</strong>)'
    if not re.search(pattern, h):
        raise SystemExit("Could not find Set Aside dashboard card.")
    h = re.sub(
        pattern,
        r'\1<button class="tiny-btn" id="edit-permanent-set-aside" type="button" style="margin-top:8px">Change Amount</button>',
        h,
        count=1,
    )

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
  state.permanentSetAside=(v===0 ? "0" : v); saveState(); renderAll(); syncPermanentSetAsideSetting();
});
setTimeout(syncPermanentSetAsideSetting,0);

document.addEventListener("click",e=>{
  if(e.target?.id!=="edit-permanent-set-aside")return;
  const current=Number(state.permanentSetAside??50);
  const entered=prompt("Set the permanent set-aside amount:",current.toFixed(2));
  if(entered===null)return;
  const amount=Number(entered);
  if(!Number.isFinite(amount)||amount<0)return alert("Enter a valid set-aside amount.");
  state.permanentSetAside=amount;
  saveState();
  renderAll();
  syncPermanentSetAsideSetting();
});
'''

html.write_text(h,encoding="utf-8")
js.write_text(s,encoding="utf-8")
