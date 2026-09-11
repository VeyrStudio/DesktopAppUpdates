from pathlib import Path

root = Path(__file__).resolve().parents[1]
html = root / "src" / "index.html"
js = root / "src" / "app.js"

html_text = html.read_text(encoding="utf-8")
old_card = '<div><span>Current Paycheck</span><strong id="stat-paycheck">$0.00</strong><small id="stat-paycheck-note">Enter your pay schedule</small></div>'
new_card = '<div><span>Current Paycheck</span><strong id="stat-paycheck">$0.00</strong><small id="stat-paycheck-note">Enter your pay schedule</small><button class="tiny-btn" id="edit-current-paycheck" type="button" style="margin-top:8px">Change Amount</button></div>'
if old_card not in html_text and 'id="edit-current-paycheck"' not in html_text:
    raise SystemExit("Could not find the Current Paycheck dashboard card.")
if 'id="edit-current-paycheck"' not in html_text:
    html_text = html_text.replace(old_card, new_card, 1)
html.write_text(html_text, encoding="utf-8")

js_text = js.read_text(encoding="utf-8")
listener = '''\n  document.getElementById("edit-current-paycheck").addEventListener("click", () => {\n    const current = currentPaycheck();\n    const entered = prompt("Set the current paycheck amount:", current ? current.toFixed(2) : "");\n    if (entered === null) return;\n    const amount = Number(entered);\n    if (!Number.isFinite(amount) || amount < 0) {\n      alert("Enter a valid paycheck amount.");\n      return;\n    }\n    state.budgetStart = amount;\n    saveState();\n    renderAll();\n  });\n'''
anchor = '  document.getElementById("budget-start-form").addEventListener("submit", e => {\n    e.preventDefault(); state.budgetStart = Number(document.getElementById("budget-start").value || 0); saveState(); renderAll();\n  });\n'
if 'document.getElementById("edit-current-paycheck").addEventListener' not in js_text:
    if anchor not in js_text:
        raise SystemExit("Could not find the paycheck budget form listener.")
    js_text = js_text.replace(anchor, anchor + listener, 1)
js.write_text(js_text, encoding="utf-8")

# Verify the feature was actually applied.
if 'id="edit-current-paycheck"' not in html.read_text(encoding="utf-8"):
    raise SystemExit("Current paycheck edit button was not applied.")
if 'Set the current paycheck amount:' not in js.read_text(encoding="utf-8"):
    raise SystemExit("Current paycheck edit logic was not applied.")
