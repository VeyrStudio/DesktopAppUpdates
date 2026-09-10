from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
html = root / 'src/index.html'
s = html.read_text(encoding='utf-8')

new_categories = ['Gifts', 'Cash', 'Clothing', 'School']

# Find the expense category select specifically. Ledgerly's source has used both
# expense-category and exp-category naming during development, so support both.
pattern = re.compile(r'(<select[^>]+id=["\'](?:expense-category|exp-category)["\'][^>]*>)(.*?)(</select>)', re.I | re.S)
match = pattern.search(s)
if not match:
    raise SystemExit('Could not find the expense category selector.')

body = match.group(2)
for category in new_categories:
    if re.search(rf'<option(?:\s+[^>]*)?>\s*{re.escape(category)}\s*</option>', body, re.I):
        continue
    option = f'<option>{category}</option>'
    other = re.search(r'<option(?:\s+[^>]*)?>\s*Other\s*</option>', body, re.I)
    if other:
        body = body[:other.start()] + option + body[other.start():]
    else:
        body += option

s = s[:match.start()] + match.group(1) + body + match.group(3) + s[match.end():]
html.write_text(s, encoding='utf-8')

# Validate all requested categories landed in the actual expense selector.
updated = pattern.search(s)
if not updated:
    raise SystemExit('Expense category selector disappeared after patching.')
for category in new_categories:
    if category not in updated.group(2):
        raise SystemExit(f'Missing expense category after patch: {category}')
