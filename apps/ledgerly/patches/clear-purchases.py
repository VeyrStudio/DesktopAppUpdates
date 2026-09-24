from pathlib import Path

root = Path(__file__).resolve().parents[1]
html = root / "src" / "index.html"
js = root / "src" / "app.js"

html_text = html.read_text(encoding="utf-8")
button_id = 'id="clear-purchases-data"'
settings_anchor = '<section class="page" id="page-settings">'

panel = '''
        <article class="panel section-gap" id="clear-purchases-panel">
          <div class="panel-head">
            <div>
              <h2>Clear Purchases &amp; Spending</h2>
              <p>Start fresh without wiping your paycheck, pay settings, bills, savings goals, or app settings.</p>
            </div>
          </div>
          <div class="advice-box">
            This clears all expense entries, grocery items, and future purchases.
          </div>
          <button class="tiny-btn danger" id="clear-purchases-data" type="button" style="margin-top:12px">Clear Purchases &amp; Spending</button>
        </article>
'''

if button_id not in html_text:
    if settings_anchor not in html_text:
        raise SystemExit("Could not find the Ledgerly Settings page.")
    html_text = html_text.replace(settings_anchor, settings_anchor + panel, 1)

html.write_text(html_text, encoding="utf-8")

js_text = js.read_text(encoding="utf-8")
marker = "Clear all expenses, grocery items, and future purchases?"

listener = r'''
document.addEventListener("click", (event) => {
  const target = event.target;
  if (!target || target.id !== "clear-purchases-data") return;

  const okay = confirm("Clear all expenses, grocery items, and future purchases? This cannot be undone. Your paycheck, pay settings, bills, savings goals, and app settings will stay.");
  if (!okay) return;

  state.expenses = [];
  state.groceries = [];
  state.futurePurchases = [];
  saveState();
  renderAll();
});
'''

if marker not in js_text:
    js_text = js_text.rstrip() + "\n\n" + listener + "\n"

js.write_text(js_text, encoding="utf-8")

if button_id not in html.read_text(encoding="utf-8"):
    raise SystemExit("Clear Purchases button was not applied.")
if marker not in js.read_text(encoding="utf-8"):
    raise SystemExit("Clear Purchases logic was not applied.")
