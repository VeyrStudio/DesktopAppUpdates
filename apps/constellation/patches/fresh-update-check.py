from pathlib import Path

p = Path("apps/constellation/src-tauri/src/lib.rs")
s = p.read_text(encoding="utf-8")

old = '''    let response = reqwest::blocking::get(UPDATE_MANIFEST)
        .map_err(|e| format!("Could not check for updates: {e}"))?;
'''
new = '''    let cache_buster = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0);
    let manifest_url = format!("{}?t={}", UPDATE_MANIFEST, cache_buster);
    let client = reqwest::blocking::Client::builder()
        .build()
        .map_err(|e| format!("Could not prepare update check: {e}"))?;
    let response = client
        .get(&manifest_url)
        .header(reqwest::header::CACHE_CONTROL, "no-cache, no-store, max-age=0")
        .header(reqwest::header::PRAGMA, "no-cache")
        .send()
        .map_err(|e| format!("Could not check for updates: {e}"))?;
'''
if old not in s:
    raise SystemExit("Updater fetch block not found")
p.write_text(s.replace(old, new, 1), encoding="utf-8")
print("Updater cache-busting patch applied.")
