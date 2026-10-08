from pathlib import Path
import re

root = Path("apps/constellation")
html = root / "src" / "index.html"

text = html.read_text(encoding="utf-8")

# Make every image-upload control in Constellation accept any browser-supported image.
# Keep the shortcut picker's .ico allowance.
def fix_input(match):
    tag = match.group(0)
    if 'type="file"' not in tag and "type='file'" not in tag:
        return tag
    if 'shortcutIconFile' in tag:
        if 'accept=' in tag:
            tag = re.sub(r'accept=(["\']).*?\1', 'accept="image/*,.ico"', tag)
        else:
            tag = tag[:-1] + ' accept="image/*,.ico">'
        return tag
    if 'accept=' in tag:
        tag = re.sub(r'accept=(["\']).*?\1', 'accept="image/*"', tag)
    else:
        tag = tag[:-1] + ' accept="image/*">'
    return tag

new_text, count = re.subn(r'<input\b[^>]*>', fix_input, text, flags=re.I)

if count == 0:
    raise SystemExit("No input elements found in Constellation HTML.")

html.write_text(new_text, encoding="utf-8")
print(f"Updated image picker compatibility across {count} input elements.")
