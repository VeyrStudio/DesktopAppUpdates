from pathlib import Path

path = Path(__file__).resolve().parents[1] / 'catalogue.py'
source = path.read_text(encoding='utf-8')
needle = "        box.pack_propagate(False)\n"
if source.count(needle) != 1:
    raise SystemExit(f"Expected one collapsed panel declaration, found {source.count(needle)}")
source = source.replace(needle, "", 1)
path.write_text(source, encoding='utf-8')
print("Fixed Catalogue dashboard panel height propagation")
