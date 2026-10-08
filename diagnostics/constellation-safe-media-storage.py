from pathlib import Path

app = Path("apps/constellation/src/app.js")
text = app.read_text(encoding="utf-8")

if "CONSTELLATION_MEDIA_DB_V2" in text:
    print("Safe media storage patch already applied.")
    raise SystemExit(0)

old_save = '''function save() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(entries));
}
'''

new_save = r'''const CONSTELLATION_MEDIA_DB_V2 = "constellation_media_v2";
const CONSTELLATION_MEDIA_STORE = "entry_images";
const CONSTELLATION_BACKUP_STORE = "migration_backups";
let mediaReady = Promise.resolve();

function openMediaDb() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(CONSTELLATION_MEDIA_DB_V2, 1);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains(CONSTELLATION_MEDIA_STORE)) {
        db.createObjectStore(CONSTELLATION_MEDIA_STORE, { keyPath: "id" });
      }
      if (!db.objectStoreNames.contains(CONSTELLATION_BACKUP_STORE)) {
        db.createObjectStore(CONSTELLATION_BACKUP_STORE, { keyPath: "key" });
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error || new Error("Could not open Constellation media storage."));
  });
}

async function putMediaImage(id, data) {
  const db = await openMediaDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(CONSTELLATION_MEDIA_STORE, "readwrite");
    tx.objectStore(CONSTELLATION_MEDIA_STORE).put({ id: String(id), data });
    tx.oncomplete = () => { db.close(); resolve(); };
    tx.onerror = () => { const err = tx.error; db.close(); reject(err || new Error("Could not save image.")); };
    tx.onabort = () => { const err = tx.error; db.close(); reject(err || new Error("Could not save image.")); };
  });
}

async function getMediaImage(id) {
  const db = await openMediaDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(CONSTELLATION_MEDIA_STORE, "readonly");
    const req = tx.objectStore(CONSTELLATION_MEDIA_STORE).get(String(id));
    req.onsuccess = () => { const row = req.result; db.close(); resolve(row?.data || null); };
    req.onerror = () => { const err = req.error; db.close(); reject(err || new Error("Could not load image.")); };
  });
}

async function deleteMediaImage(id) {
  const db = await openMediaDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(CONSTELLATION_MEDIA_STORE, "readwrite");
    tx.objectStore(CONSTELLATION_MEDIA_STORE).delete(String(id));
    tx.oncomplete = () => { db.close(); resolve(); };
    tx.onerror = () => { const err = tx.error; db.close(); reject(err || new Error("Could not remove image.")); };
    tx.onabort = () => { const err = tx.error; db.close(); reject(err || new Error("Could not remove image.")); };
  });
}

async function putMigrationBackup(payload) {
  const db = await openMediaDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(CONSTELLATION_BACKUP_STORE, "readwrite");
    tx.objectStore(CONSTELLATION_BACKUP_STORE).put({
      key: "pre-media-migration-v1",
      payload,
      createdAt: new Date().toISOString()
    });
    tx.oncomplete = () => { db.close(); resolve(); };
    tx.onerror = () => { const err = tx.error; db.close(); reject(err || new Error("Could not create migration backup.")); };
    tx.onabort = () => { const err = tx.error; db.close(); reject(err || new Error("Could not create migration backup.")); };
  });
}

function serializableEntries() {
  return entries.map((entry) => {
    const copy = { ...entry };
    delete copy.image;
    return copy;
  });
}

function save() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(serializableEntries()));
  } catch (err) {
    console.error("Constellation could not save metadata.", err);
    alert("Constellation could not save your changes. Your existing data has not been intentionally cleared. Please leave the app open and report this error before making more changes.");
    const wrapped = new Error("Constellation could not save changes.");
    wrapped.constellationSaveFailure = true;
    wrapped.cause = err;
    throw wrapped;
  }
}

async function initializeMediaStorage() {
  const legacyImages = entries.filter((entry) => typeof entry.image === "string" && entry.image.length > 0);

  if (legacyImages.length) {
    const legacySnapshot = JSON.stringify(entries);
    await putMigrationBackup(legacySnapshot);

    for (const entry of legacyImages) {
      await putMediaImage(entry.id, entry.image);
    }

    // Only remove large image payloads from localStorage after every legacy image
    // has been copied successfully into IndexedDB.
    save();
  }

  for (const entry of entries) {
    if (!entry.image) {
      const stored = await getMediaImage(entry.id);
      if (stored) entry.image = stored;
    }
  }

  render();
}
'''

if old_save not in text:
    raise SystemExit("Could not find Constellation save() function.")
text = text.replace(old_save, new_save, 1)

old_fav = '''document.addEventListener("click",(e)=>{
  const fav = e.target.closest("[data-fav]");
  if(!fav) return;
  const id = Number(fav.dataset.fav);
  const x = entries.find(x=>x.id===id);
  if(x){x.favorite=!x.favorite; save(); render();}
});
'''
new_fav = '''document.addEventListener("click",(e)=>{
  const fav = e.target.closest("[data-fav]");
  if(!fav) return;
  const id = Number(fav.dataset.fav);
  const x = entries.find(x=>x.id===id);
  if(x){
    x.favorite=!x.favorite;
    try{
      save();
    }catch(_){
      x.favorite=!x.favorite;
      return;
    }
    render();
  }
});
'''
if old_fav not in text:
    raise SystemExit("Could not find favorite save handler.")
text = text.replace(old_fav, new_fav, 1)

old_add = '''  entries.push(item);
  save();
  $("#addForm").reset();
'''
new_add = '''  entries.push(item);
  try {
    save();
  } catch (_) {
    entries = entries.filter(x => x.id !== item.id);
    return;
  }
  $("#addForm").reset();
'''
if old_add not in text:
    raise SystemExit("Could not find add-entry save block.")
text = text.replace(old_add, new_add, 1)

old_open = '''function openEdit(id) {
  const x = entries.find(x => x.id === id);
'''
new_open = '''async function openEdit(id) {
  await mediaReady;
  const x = entries.find(x => x.id === id);
'''
if old_open not in text:
    raise SystemExit("Could not find openEdit().")
text = text.replace(old_open, new_open, 1)

old_edit = '''$("#editForm").addEventListener("submit", (e) => {
  const submitter = e.submitter;
  if (submitter && submitter.value === "cancel") return;

  e.preventDefault();

  const id = Number($("#editId").value);
  const x = entries.find(x => x.id === id);
  if (!x) return;

  x.category = $("#editCategory").value;
  x.a = $("#editA").value.trim();
  x.b = $("#editB").value.trim();
  x.fandom = $("#editFandom").value.trim();
  x.favorite = $("#editFavorite").checked;

  if (x.category === "romantic") {
    x.type = $("#editType").value;
  } else {
    delete x.type;
  }

  if (removeExistingImage) {
    delete x.image;
  } else if (editImageData) {
    x.image = editImageData;
  }

  save();
  editDlg.close();
  render();
});
'''

new_edit = '''$("#editForm").addEventListener("submit", async (e) => {
  const submitter = e.submitter;
  if (submitter && submitter.value === "cancel") return;

  e.preventDefault();
  await mediaReady;

  const id = Number($("#editId").value);
  const x = entries.find(x => x.id === id);
  if (!x) return;

  const before = { ...x };

  x.category = $("#editCategory").value;
  x.a = $("#editA").value.trim();
  x.b = $("#editB").value.trim();
  x.fandom = $("#editFandom").value.trim();
  x.favorite = $("#editFavorite").checked;

  if (x.category === "romantic") {
    x.type = $("#editType").value;
  } else {
    delete x.type;
  }

  if (removeExistingImage) {
    delete x.image;
  } else if (editImageData) {
    x.image = editImageData;
  }

  try {
    if (removeExistingImage) {
      await deleteMediaImage(id);
    } else if (editImageData) {
      await putMediaImage(id, editImageData);
    }

    save();
  } catch (err) {
    Object.keys(x).forEach((key) => delete x[key]);
    Object.assign(x, before);

    try {
      if (before.image) await putMediaImage(id, before.image);
      else await deleteMediaImage(id);
    } catch (_) {}

    if (!err?.constellationSaveFailure) {
      console.error("Constellation could not save the edited image.", err);
      alert("Constellation could not save that image. Nothing was intentionally deleted; the previous version of this entry has been kept.");
    }
    return;
  }

  editDlg.close();
  render();
});
'''

if old_edit not in text:
    raise SystemExit("Could not find edit save handler.")
text = text.replace(old_edit, new_edit, 1)

old_delete = '''$("#deleteEntryBtn").addEventListener("click", () => {
  const id = Number($("#editId").value);
  const x = entries.find(x => x.id === id);
  if (!x) return;

  const ok = confirm(`Delete "${shipLabel(x)}"?`);
  if (!ok) return;

  entries = entries.filter(item => item.id !== id);
  save();
  editDlg.close();
  render();
});
'''

new_delete = '''$("#deleteEntryBtn").addEventListener("click", async () => {
  await mediaReady;

  const id = Number($("#editId").value);
  const x = entries.find(x => x.id === id);
  if (!x) return;

  const ok = confirm(`Delete "${shipLabel(x)}"?`);
  if (!ok) return;

  const previousEntries = entries;
  entries = entries.filter(item => item.id !== id);

  try {
    save();
  } catch (_) {
    entries = previousEntries;
    return;
  }

  try {
    await deleteMediaImage(id);
  } catch (err) {
    console.warn("Constellation left an orphaned media record after deletion.", err);
  }

  editDlg.close();
  render();
});
'''

if old_delete not in text:
    raise SystemExit("Could not find delete handler.")
text = text.replace(old_delete, new_delete, 1)

old_start = '''render();

// --- Desktop app update support (Tauri) ---
'''
new_start = '''render();

mediaReady = initializeMediaStorage().catch((err) => {
  console.error("Constellation media migration/hydration failed.", err);
  alert("Constellation could not finish preparing safe image storage. Your existing saved data was not intentionally cleared. Please avoid replacing images until this is fixed.");
});

// --- Desktop app update support (Tauri) ---
'''

if old_start not in text:
    raise SystemExit("Could not find startup render block.")
text = text.replace(old_start, new_start, 1)

app.write_text(text, encoding="utf-8")
print("Constellation safe media storage patch applied.")
