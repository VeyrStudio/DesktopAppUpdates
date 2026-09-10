from pathlib import Path

root = Path(__file__).resolve().parents[1]
main_rs = root / "src-tauri" / "src" / "main.rs"
text = main_rs.read_text(encoding="utf-8")
marker = '#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]'

if marker not in text:
    text = marker + "\n\n" + text
    main_rs.write_text(text, encoding="utf-8")

# Fail loudly if the release-only Windows subsystem attribute is not present.
verified = main_rs.read_text(encoding="utf-8")
if marker not in verified:
    raise SystemExit("Ledgerly Windows GUI subsystem marker was not applied.")
