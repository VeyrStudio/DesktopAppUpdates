from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
html = root / "src" / "index.html"
js = root / "src" / "app.js"

html_text = html.read_text(encoding="utf-8")

# Find the app's existing next-payday calendar field so the shortcut writes through
# the same form/state logic Ledgerly already uses.
label_pattern = re.compile(
    r'(<label[^>]*>)(.*?(?:Next\s+(?:Expected\s+)?Pay(?:day|check)|Next\s+Pay\s*Date).*?)(</label>)',
    re.IGNORECASE | re.DOTALL,
)
match = label_pattern.search(html_text)
if not match:
    raise SystemExit("Could not find Ledgerly's existing Next Payday field.")

label_html = match.group(0)
input_match = re.search(r'<input\b[^>]*>', label_html, re.IGNORECASE)
if not input_match:
    raise SystemExit("Next Payday label does not contain an input.")

input_tag = input_match.group(0)
if re.search(r'\bid\s*=\s*["\']([^"\']+)["\']', input_tag, re.IGNORECASE):
    source_id = re.search(r'\bid\s*=\s*["\']([^"\']+)["\']', input_tag, re.IGNORECASE).group(1)
else:
    source_id = "ledgerly-source-next-payday"
    input_tag_new = input_tag[:-1] + f' id="{source_id}">'
    label_html = label_html.replace(input_tag, input_tag_new, 1)
    html_text = html_text.replace(match.group(0), label_html, 1)
    input_tag = input_tag_new

# Make sure the original field itself is a proper calendar picker.
if not re.search(r'\btype\s*=\s*["\']date["\']', input_tag, re.IGNORECASE):
    if re.search(r'\btype\s*=\s*["\'][^"\']*["\']', input_tag, re.IGNORECASE):
        fixed = re.sub(r'\btype\s*=\s*["\'][^"\']*["\']', 'type="date"', input_tag, count=1, flags=re.IGNORECASE)
    else:
        fixed = input_tag[:-1] + ' type="date">'
    html_text = html_text.replace(input_tag, fixed, 1)

# Add a convenient calendar directly under Current Paycheck.
picker_id = 'id="expected-payday-calendar"'
if picker_id not in html_text:
    anchor = '<button class="tiny-btn" id="edit-current-paycheck" type="button" style="margin-top:8px">Change Amount</button>'
    if anchor not in html_text:
        raise SystemExit("Could not find the Current Paycheck Change Amount button.")
    calendar = anchor + f'''<label style="display:block;margin-top:10px">Expected payday
      <input id="expected-payday-calendar" type="date" data-source-payday-id="{source_id}" style="margin-top:5px;width:100%" />
    </label>'''
    html_text = html_text.replace(anchor, calendar, 1)

html.write_text(html_text, encoding="utf-8")

js_text = js.read_text(encoding="utf-8")
marker = "expected-payday-calendar"
if marker not in js_text:
    logic = r'''
function syncExpectedPaydayCalendar() {
  const picker = document.getElementById("expected-payday-calendar");
  if (!picker) return;
  const sourceId = picker.dataset.sourcePaydayId;
  const source = sourceId ? document.getElementById(sourceId) : null;
  if (source && source.value) picker.value = source.value;
}

document.addEventListener("change", (event) => {
  const picker = event.target;
  if (!picker || picker.id !== "expected-payday-calendar") return;

  const sourceId = picker.dataset.sourcePaydayId;
  const source = sourceId ? document.getElementById(sourceId) : null;
  if (!source) {
    alert("Ledgerly could not find the saved payday field.");
    return;
  }

  source.value = picker.value;
  source.dispatchEvent(new Event("input", { bubbles: true }));
  source.dispatchEvent(new Event("change", { bubbles: true }));

  const form = source.closest("form");
  if (form) {
    if (typeof form.requestSubmit === "function") form.requestSubmit();
    else form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
  }

  setTimeout(syncExpectedPaydayCalendar, 0);
});

setTimeout(syncExpectedPaydayCalendar, 0);
'''
    js_text = js_text.rstrip() + "\n\n" + logic + "\n"

js.write_text(js_text, encoding="utf-8")

final_html = html.read_text(encoding="utf-8")
final_js = js.read_text(encoding="utf-8")
if 'id="expected-payday-calendar"' not in final_html:
    raise SystemExit("Expected payday calendar was not applied.")
if 'type="date"' not in final_html:
    raise SystemExit("No calendar date input was found after patching.")
if "syncExpectedPaydayCalendar" not in final_js:
    raise SystemExit("Expected payday calendar logic was not applied.")
