from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
html = root / "src" / "index.html"
js = root / "src" / "app.js"

html_text = html.read_text(encoding="utf-8")
js_text = js.read_text(encoding="utf-8")

# Find the actual state field or hard-coded calculation Ledgerly currently uses for
# the permanent $50 set-aside. Refuse to continue if we cannot identify it safely.
state_key = None
property_patterns = [
    r'(?P<key>setAside|setaside|set_aside|reserve|reserved|permanentReserve|permanentSetAside|buffer|safetyNet)\s*:\s*50\b',
]
for pat in property_patterns:
    m = re.search(pat, js_text, re.IGNORECASE)
    if m:
        state_key = m.group("key")
        break

if state_key is None:
    # Fall back to a named local constant, but only when the variable name clearly
    # identifies the set-aside/reserve behavior.
    local = re.search(
        r'(?m)^(?P<indent>\s*)(?:const|let|var)\s+(?P<name>[A-Za-z_$][\w$]*(?:setAside|setaside|reserve|reserved|buffer)[A-Za-z_$\w]*)\s*=\s*50\s*;',
        js_text,
        re.IGNORECASE,
    )
    if local:
        state_key = "permanentSetAside"
        original = local.group(0)
        replacement = re.sub(r'=\s*50\s*;', '= Number(state.permanentSetAside ?? 50);', original, count=1)
        js_text = js_text.replace(original, replacement, 1)

if state_key is None:
    # Last precise fallback: inspect lines that mention the concept and contain the
    # literal 50. Only patch if exactly one such calculation line exists.
    candidate_lines = [
        line for line in js_text.splitlines()
        if re.search(r'(set\s*aside|setaside|reserve|reserved|buffer)', line, re.IGNORECASE)
        and re.search(r'(?<![\d.])50(?:\.0+)?(?![\d.])', line)
    ]
    if len(candidate_lines) == 1:
        state_key = "permanentSetAside"
        old = candidate_lines[0]
        new = re.sub(r'(?<![\d.])50(?:\.0+)?(?![\d.])', 'Number(state.permanentSetAside ?? 50)', old, count=1)
        js_text = js_text.replace(old, new, 1)

if state_key is None:
    raise SystemExit("Could not safely identify Ledgerly's permanent $50 set-aside calculation.")

# If we had to introduce our own setting, add its default into the state object.
if state_key == "permanentSetAside" and not re.search(r'\bpermanentSetAside\s*:', js_text):
    # Anchor near another known top-level state property.
    known = re.search(r'(?m)^\s{2}groceryBudget\s*:\s*[^,]+,', js_text)
    if not known:
        raise SystemExit("Could not find a safe state-object anchor for permanentSetAside.")
    js_text = js_text[:known.end()] + '\n  permanentSetAside: 50,' + js_text[known.end():]

# Add a Settings panel with an editable permanent set-aside amount.
if 'id="permanent-set-aside-form"' not in html_text:
    settings_anchor = '<section class="page" id="page-settings">'
    if settings_anchor not in html_text:
        raise SystemExit("Could not find Ledgerly Settings page.")

    panel = f'''
        <article class="panel section-gap" id="permanent-set-aside-panel">
          <div class="panel-head">
            <div>
              <h2>Permanent Set Aside</h2>
              <p>Choose how much Ledgerly automatically keeps unavailable from each paycheck.</p>
            </div>
          </div>
          <form class="form-grid" id="permanent-set-aside-form">
            <label>Set Aside per Paycheck
              <input id="permanent-set-aside-amount" type="number" min="0" step="0.01" value="50.00" />
            </label>
            <button class="primary-btn" type="submit">Save Set Aside</button>
          </form>
        </article>
'''
    html_text = html_text.replace(settings_anchor, settings_anchor + panel, 1)

# Wire the form to the exact state key the existing calculation uses.
marker = "permanent-set-aside-form"
if marker not in js_text:
    logic = f'''
function syncPermanentSetAsideSetting() {{
  const input = document.getElementById("permanent-set-aside-amount");
  if (!input) return;
  const value = Number(state.{state_key} ?? 50);
  input.value = Number.isFinite(value) ? value.toFixed(2) : "50.00";
}}

document.addEventListener("submit", (event) => {{
  if (!event.target || event.target.id !== "permanent-set-aside-form") return;
  event.preventDefault();

  const input = document.getElementById("permanent-set-aside-amount");
  const amount = Number(input?.value ?? 0);
  if (!Number.isFinite(amount) || amount < 0) {{
    alert("Enter a valid set-aside amount.");
    return;
  }}

  state.{state_key} = amount;
  saveState();
  renderAll();
  syncPermanentSetAsideSetting();
}});

setTimeout(syncPermanentSetAsideSetting, 0);
'''
    js_text = js_text.rstrip() + "\n\n" + logic + "\n"

html.write_text(html_text, encoding="utf-8")
js.write_text(js_text, encoding="utf-8")

final_html = html.read_text(encoding="utf-8")
final_js = js.read_text(encoding="utf-8")
if 'id="permanent-set-aside-form"' not in final_html:
    raise SystemExit("Permanent Set Aside settings form was not applied.")
if "syncPermanentSetAsideSetting" not in final_js:
    raise SystemExit("Permanent Set Aside logic was not applied.")
