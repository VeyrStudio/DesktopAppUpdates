from pathlib import Path

app = Path("apps/constellation/src/app.js")
text = app.read_text(encoding="utf-8")

if "STORAGE_BACKUP_KEY" in text and 'currentView === "platonic"' in text and "Platonic view ignores romantic type filter" in text:
    print("Platonic filter/data backup patch already applied.")
    raise SystemExit(0)

old_boot = '''const STORAGE_KEY = "constellation_entries_v4_editable";
let entries = JSON.parse(localStorage.getItem(STORAGE_KEY) || "null") || window.CONSTELLATION_SEED;
let currentView = "dashboard";
'''
new_boot = '''const STORAGE_KEY = "constellation_entries_v4_editable";
const STORAGE_BACKUP_KEY = "constellation_entries_v4_editable_backup";

function loadConstellationEntries() {
  const tryParse = (raw) => {
    if (!raw) return null;
    try {
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed : null;
    } catch (_) {
      return null;
    }
  };

  const primary = tryParse(localStorage.getItem(STORAGE_KEY));
  if (primary) return primary;

  const backup = tryParse(localStorage.getItem(STORAGE_BACKUP_KEY));
  if (backup) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(backup));
    } catch (_) {}
    return backup;
  }

  return window.CONSTELLATION_SEED;
}

let entries = loadConstellationEntries();
let currentView = "dashboard";
'''
if old_boot not in text:
    raise SystemExit("Could not find Constellation storage bootstrap.")
text = text.replace(old_boot, new_boot, 1)

old_save = '''function save() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(serializableEntries()));
  } catch (err) {
'''
new_save = '''function save() {
  try {
    const next = JSON.stringify(serializableEntries());
    const previous = localStorage.getItem(STORAGE_KEY);

    // Keep one last-known-good metadata snapshot before every overwrite.
    if (previous) {
      try {
        const parsed = JSON.parse(previous);
        if (Array.isArray(parsed)) {
          localStorage.setItem(STORAGE_BACKUP_KEY, previous);
        }
      } catch (_) {}
    }

    localStorage.setItem(STORAGE_KEY, next);
  } catch (err) {
'''
if old_save not in text:
    raise SystemExit("Could not find Constellation safe save() function.")
text = text.replace(old_save, new_save, 1)

old_filter = '''    return (!q || hay.includes(q))
      && (!fandom || x.fandom === fandom)
      && (!type || x.type === type)
      && (!character || x.a === character || x.b === character);
'''
new_filter = '''    // Platonic entries do not have M/M or F/M values. Never let the
    // romantic type filter make the entire Platonic tab appear empty.
    const typeMatches = currentView === "platonic" ? true : (!type || x.type === type);
    return (!q || hay.includes(q))
      && (!fandom || x.fandom === fandom)
      && typeMatches
      && (!character || x.a === character || x.b === character);
'''
if old_filter not in text:
    raise SystemExit("Could not find relationship filter logic.")
text = text.replace(old_filter, new_filter, 1)

old_setview = '''function setView(view) {
  currentView = view;
  if (view !== "fandomDetail") activeFandomPage = null;
'''
new_setview = '''function setView(view) {
  currentView = view;
  if (view !== "fandomDetail") activeFandomPage = null;

  // Platonic view ignores romantic type filter.
  if (view === "platonic") {
    const typeFilter = $("#typeFilter");
    if (typeFilter) typeFilter.value = "";
  }
'''
if old_setview not in text:
    raise SystemExit("Could not find setView().")
text = text.replace(old_setview, new_setview, 1)

app.write_text(text, encoding="utf-8")
print("Fixed Platonic filtering and added last-known-good metadata backup.")
