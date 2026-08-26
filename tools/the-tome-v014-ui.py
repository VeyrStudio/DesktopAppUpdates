from pathlib import Path
import json

root = Path('tome-build')
renderer = root / 'renderer.js'
main = root / 'main.js'
pkg = root / 'package.json'

s = renderer.read_text(encoding='utf-8')
anchor = "function escapeHtml(s=''){return String(s).replace(/[&<>'\"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',\"'\":'&#39;','\"':'&quot;'}[c]));}"
if anchor not in s:
    raise SystemExit('renderer anchor not found')
helper = anchor + "\nfunction formatPublicationDate(value){if(!value)return '—';const d=new Date(value);if(Number.isNaN(d.getTime()))return String(value);return d.toLocaleDateString(undefined,{year:'numeric',month:'long',day:'numeric'});}"
s = s.replace(anchor, helper, 1)
old_meta = "$('#detailDescription').textContent=currentBook.description||'No description.'; $('#detailMeta').innerHTML=`<span><b>Published:</b> ${escapeHtml(currentBook.publicationDate||'—')}</span><span><b>Publisher:</b> ${escapeHtml(currentBook.publisher||'—')}</span><span><b>Language:</b> English</span><span><b>Format:</b> ${escapeHtml(currentBook.format)}</span>`; $('#detailNotes').innerHTML=currentBook.notes||'';"
new_meta = "$('#detailDescription').textContent=currentBook.description||'No description.'; $('#detailMeta').innerHTML=`<span><b>Published</b>${escapeHtml(formatPublicationDate(currentBook.publicationDate))}</span><span><b>Publisher</b>${escapeHtml(currentBook.publisher||'—')}</span><span><b>Language</b>${escapeHtml(currentBook.language||'English')}</span><span><b>Format</b>${escapeHtml(currentBook.format)}</span>`; $('#detailNotes').innerHTML=currentBook.notes||'';"
if old_meta not in s:
    raise SystemExit('detail metadata block not found')
s = s.replace(old_meta, new_meta, 1)
renderer.write_text(s, encoding='utf-8')

m = main.read_text(encoding='utf-8')
if "const APP_VERSION = '0.1.3';" not in m:
    raise SystemExit('v0.1.3 version marker not found')
m = m.replace("const APP_VERSION = '0.1.3';", "const APP_VERSION = '0.1.4';", 1)
main.write_text(m, encoding='utf-8')

p = json.loads(pkg.read_text(encoding='utf-8'))
p['version'] = '0.1.4'
pkg.write_text(json.dumps(p, indent=2) + '\n', encoding='utf-8')
print('Applied The Tome v0.1.4 UI/data-format polish.')
