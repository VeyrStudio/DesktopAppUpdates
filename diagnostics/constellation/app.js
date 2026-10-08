
const STORAGE_KEY = "constellation_entries_v4_editable";
let entries = JSON.parse(localStorage.getItem(STORAGE_KEY) || "null") || window.CONSTELLATION_SEED;
let currentView = "dashboard";
let activeFandomPage = null;

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => [...document.querySelectorAll(sel)];

const CONSTELLATION_MEDIA_DB_V2 = "constellation_media_v2";
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

async function getAllMediaImages() {
  const db = await openMediaDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(CONSTELLATION_MEDIA_STORE, "readonly");
    const req = tx.objectStore(CONSTELLATION_MEDIA_STORE).getAll();
    req.onsuccess = () => {
      const rows = req.result || [];
      db.close();
      resolve(new Map(rows.map((row) => [String(row.id), row.data])));
    };
    req.onerror = () => { const err = req.error; db.close(); reject(err || new Error("Could not load images.")); };
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

async function migrateLegacyImages(legacyImages, payload) {
  const db = await openMediaDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction([CONSTELLATION_MEDIA_STORE, CONSTELLATION_BACKUP_STORE], "readwrite");
    const imageStore = tx.objectStore(CONSTELLATION_MEDIA_STORE);
    const backupStore = tx.objectStore(CONSTELLATION_BACKUP_STORE);

    backupStore.put({
      key: "pre-media-migration-v1",
      payload,
      createdAt: new Date().toISOString()
    });

    legacyImages.forEach((entry) => {
      imageStore.put({ id: String(entry.id), data: entry.image });
    });

    tx.oncomplete = () => { db.close(); resolve(); };
    tx.onerror = () => { const err = tx.error; db.close(); reject(err || new Error("Could not migrate legacy images.")); };
    tx.onabort = () => { const err = tx.error; db.close(); reject(err || new Error("Could not migrate legacy images.")); };
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

    // Backup + image migration happen in one IndexedDB transaction. localStorage
    // is only slimmed down after that transaction completes successfully.
    await migrateLegacyImages(legacyImages, legacySnapshot);
    save();
  }

  const storedImages = await getAllMediaImages();
  for (const entry of entries) {
    if (!entry.image) {
      const stored = storedImages.get(String(entry.id));
      if (stored) entry.image = stored;
    }
  }

  render();
}

function esc(s="") {
  return String(s).replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[m]));
}

function shipLabel(x) {
  return `${x.a} ${x.category === "platonic" ? "&" : "×"} ${x.b}`;
}

function uniqueSorted(values) {
  return [...new Set(values.filter(Boolean))].sort((a,b)=>a.localeCompare(b));
}

function refreshFilters() {
  const fandoms = uniqueSorted(entries.map(x=>x.fandom));
  const chars = uniqueSorted(entries.flatMap(x=>[x.a, x.b]));
  const fandomSel = $("#fandomFilter");
  const charSel = $("#characterFilter");
  const oldF = fandomSel.value;
  const oldC = charSel.value;

  fandomSel.innerHTML = `<option value="">All fandoms</option>` + fandoms.map(x=>`<option>${esc(x)}</option>`).join("");
  charSel.innerHTML = `<option value="">All characters</option>` + chars.map(x=>`<option>${esc(x)}</option>`).join("");

  if (fandoms.includes(oldF)) fandomSel.value = oldF;
  if (chars.includes(oldC)) charSel.value = oldC;
}

function getFiltered(base=entries) {
  const q = $("#searchInput").value.trim().toLowerCase();
  const fandom = $("#fandomFilter").value;
  const type = $("#typeFilter").value;
  const character = $("#characterFilter").value;
  return base.filter(x => {
    const hay = `${x.a} ${x.b} ${x.fandom} ${x.type||""}`.toLowerCase();
    return (!q || hay.includes(q))
      && (!fandom || x.fandom === fandom)
      && (!type || x.type === type)
      && (!character || x.a === character || x.b === character);
  });
}

function cardHTML(x) {
  const cat = x.category === "platonic" ? "Platonic" : "Romantic";
  const artHTML = x.image ? `<img class="card-art-image" src="${esc(x.image)}" alt="" />` : "";
  return `
    <article class="ship-card">
      <div class="card-art ${x.image ? "has-image" : ""}">${artHTML}</div>
      <button class="edit-btn" data-edit="${x.id}" title="Edit entry">Edit</button>
      <button class="fav-btn ${x.favorite ? "on" : ""}" data-fav="${x.id}" title="Toggle favorite">${x.favorite ? "★" : "☆"}</button>
      <div class="card-body">
        <div class="card-title">${esc(shipLabel(x))}</div>
        <div class="card-fandom"><button class="fandom-link" data-open-fandom="${esc(x.fandom)}">${esc(x.fandom)}</button></div>
        <div class="chips">
          <span class="chip ${x.category}">${cat}</span>
          ${x.category === "romantic" && x.type ? `<span class="chip">${esc(x.type)}</span>` : ""}
        </div>
      </div>
    </article>`;
}

function fandomStats() {
  const map = new Map();
  entries.forEach(x => {
    const cur = map.get(x.fandom) || {name:x.fandom, ships:0, romantic:0, platonic:0};
    cur.ships++;
    cur[x.category]++;
    map.set(x.fandom, cur);
  });
  return [...map.values()].sort((a,b)=>a.name.localeCompare(b.name));
}

function fandomHTML(f) {
  return `
    <article class="fandom-card" data-open-fandom="${esc(f.name)}" tabindex="0" role="button" aria-label="Open ${esc(f.name)}">
      <div>
        <div class="fandom-name">${esc(f.name)}</div>
        <div class="chips" style="margin-top:10px">
          ${f.romantic ? `<span class="chip romantic">${f.romantic} romantic</span>` : ""}
          ${f.platonic ? `<span class="chip platonic">${f.platonic} platonic</span>` : ""}
        </div>
      </div>
      <div class="fandom-count">♡ ${f.ships} ${f.ships === 1 ? "entry" : "entries"} · Open →</div>
    </article>`;
}

function renderDashboard() {
  const favs = entries.filter(x=>x.favorite).slice(0,8);
  $("#pinnedShips").innerHTML = favs.map(cardHTML).join("") || `<div class="empty-state">No pinned ships yet.</div>`;
  $("#dashboardFandoms").innerHTML = fandomStats().slice(0,8).map(fandomHTML).join("");
}

function renderList() {
  let base = entries;

  if (currentView === "romantic") base = entries.filter(x=>x.category==="romantic");
  if (currentView === "platonic") base = entries.filter(x=>x.category==="platonic");
  if (currentView === "favorites") base = entries.filter(x=>x.favorite);
  if (currentView === "fandomDetail" && activeFandomPage) {
    base = entries.filter(x=>x.fandom === activeFandomPage);
  }

  const filtered = getFiltered(base);

  $("#fandomPageBar").classList.toggle("hidden", currentView !== "fandomDetail");
  if (currentView === "fandomDetail") {
    $("#fandomPageName").textContent = activeFandomPage || "";
  }

  $("#listHeading").textContent =
    currentView === "romantic" ? "Romantic Ships" :
    currentView === "platonic" ? "Platonic Relationships" :
    currentView === "favorites" ? "Favorites" :
    currentView === "fandomDetail" ? `${activeFandomPage} Ships & Relationships` :
    "Ships";

  $("#resultCount").textContent = `${filtered.length} ${filtered.length === 1 ? "entry" : "entries"}`;
  $("#shipGrid").innerHTML = filtered.map(cardHTML).join("");
  $("#emptyState").classList.toggle("hidden", filtered.length !== 0);
}

function renderFandoms() {
  const q = $("#searchInput").value.trim().toLowerCase();
  const stats = fandomStats().filter(f => !q || f.name.toLowerCase().includes(q));
  $("#fandomCount").textContent = `${stats.length} fandom${stats.length===1?"":"s"}`;
  $("#fandomGrid").innerHTML = stats.map(fandomHTML).join("");
}


function openFandom(name) {
  if (!name) return;
  activeFandomPage = name;
  currentView = "fandomDetail";

  // Clear only the fandom filter because the fandom page itself is the scope.
  $("#fandomFilter").value = "";

  $$(".view").forEach(v=>v.classList.remove("active"));
  $$(".nav-item").forEach(n=>n.classList.toggle("active", n.dataset.view === "fandoms"));
  $("#listView").classList.add("active");

  $("#pageTitle").textContent = name;
  $("#pageSubtitle").textContent = `Everything in ${name}.`;
  render();
}

function setView(view) {
  currentView = view;
  if (view !== "fandomDetail") activeFandomPage = null;
  $$(".view").forEach(v=>v.classList.remove("active"));
  $$(".nav-item").forEach(n=>n.classList.toggle("active",n.dataset.view===view));

  if (view === "dashboard") {
    $("#dashboardView").classList.add("active");
    $("#pageTitle").textContent = "Dashboard";
    $("#pageSubtitle").textContent = "A home for the fandoms and ships you love.";
  } else if (view === "settings") {
    $("#settingsView").classList.add("active");
    $("#pageTitle").textContent = "Settings";
    $("#pageSubtitle").textContent = "Manage Constellation and check for updates.";
  } else if (view === "fandoms") {
    $("#fandomView").classList.add("active");
    $("#pageTitle").textContent = "Fandoms";
    $("#pageSubtitle").textContent = "Browse everything by universe, series, or franchise.";
  } else {
    $("#listView").classList.add("active");
    $("#pageTitle").textContent =
      view === "romantic" ? "Romantic" :
      view === "platonic" ? "Platonic" :
      view === "favorites" ? "Favorites" : "Ships";
    $("#pageSubtitle").textContent =
      view === "romantic" ? "All of your romantic ships in one place." :
      view === "platonic" ? "Family, friendship, and other platonic relationships." :
      "Your pinned favorites.";
  }
  render();
}

function render() {
  refreshFilters();
  const selectedFandom = $("#fandomFilter").value;
  $("#openFandomBtn").classList.toggle("hidden", !selectedFandom);
  $("#openFandomBtn").textContent = selectedFandom ? `Open ${selectedFandom} →` : "Open Fandom →";
  renderDashboard();
  renderList();
  renderFandoms();
}

$$(".nav-item").forEach(btn=>btn.addEventListener("click",()=>setView(btn.dataset.view)));
$$("[data-view-jump]").forEach(btn=>btn.addEventListener("click",()=>setView(btn.dataset.viewJump)));

$$(".side-link").forEach(btn=>btn.addEventListener("click",()=>{
  const mode = btn.dataset.browse;
  if(mode==="fandom"){
    setView("fandoms");
  }else{
    setView("romantic");
    setTimeout(()=>{
      if(mode==="type") $("#typeFilter").focus();
      if(mode==="character") $("#characterFilter").focus();
    },0);
  }
}));

["searchInput","fandomFilter","typeFilter","characterFilter"].forEach(id=>{
  $("#"+id).addEventListener(id==="searchInput" ? "input" : "change", render);
});

$("#clearFilters").addEventListener("click",()=>{
  $("#searchInput").value="";
  $("#fandomFilter").value="";
  $("#typeFilter").value="";
  $("#characterFilter").value="";
  render();
});

document.addEventListener("click",(e)=>{
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


document.addEventListener("click", (e) => {
  const fandomTarget = e.target.closest("[data-open-fandom]");
  if (!fandomTarget) return;
  e.preventDefault();
  e.stopPropagation();
  openFandom(fandomTarget.dataset.openFandom);
});

document.addEventListener("keydown", (e) => {
  const fandomTarget = e.target.closest?.("[data-open-fandom]");
  if (!fandomTarget || (e.key !== "Enter" && e.key !== " ")) return;
  e.preventDefault();
  openFandom(fandomTarget.dataset.openFandom);
});

$("#openFandomBtn").addEventListener("click", () => {
  const fandom = $("#fandomFilter").value;
  if (fandom) openFandom(fandom);
});

$("#backToFandomsBtn").addEventListener("click", () => setView("fandoms"));


const dlg = $("#addDialog");
$("#addNewBtn").addEventListener("click",()=>dlg.showModal());
$("#newCategory").addEventListener("change",()=>{
  $("#newTypeWrap").style.display = $("#newCategory").value === "romantic" ? "" : "none";
});

$("#addForm").addEventListener("submit",(e)=>{
  const submitter = e.submitter;
  if(submitter && submitter.value==="cancel") return;
  e.preventDefault();
  const category = $("#newCategory").value;
  const item = {
    id: Math.max(0,...entries.map(x=>x.id))+1,
    a: $("#newA").value.trim(),
    b: $("#newB").value.trim(),
    fandom: $("#newFandom").value.trim(),
    category,
    favorite: $("#newFavorite").checked
  };
  if(category==="romantic") item.type = $("#newType").value;
  if(!item.a || !item.b || !item.fandom) return;
  entries.push(item);
  try {
    save();
  } catch (_) {
    entries = entries.filter(x => x.id !== item.id);
    return;
  }
  $("#addForm").reset();
  $("#newTypeWrap").style.display="";
  dlg.close();
  setView(category);
});


const editDlg = $("#editDialog");
let editImageData = null;
let removeExistingImage = false;

async function openEdit(id) {
  await mediaReady;
  const x = entries.find(x => x.id === id);
  if (!x) return;

  $("#editId").value = x.id;
  $("#editCategory").value = x.category;
  $("#editA").value = x.a;
  $("#editB").value = x.b;
  $("#editFandom").value = x.fandom;
  $("#editType").value = x.type || "M/M";
  $("#editFavorite").checked = !!x.favorite;
  $("#editTypeWrap").style.display = x.category === "romantic" ? "" : "none";

  editImageData = null;
  removeExistingImage = false;
  $("#editImage").value = "";

  if (x.image) {
    $("#editImagePreview").src = x.image;
    $("#editImagePreviewWrap").classList.remove("hidden");
  } else {
    $("#editImagePreview").removeAttribute("src");
    $("#editImagePreviewWrap").classList.add("hidden");
  }

  editDlg.showModal();
}

$("#editCategory").addEventListener("change", () => {
  $("#editTypeWrap").style.display = $("#editCategory").value === "romantic" ? "" : "none";
});

$("#editImage").addEventListener("change", (e) => {
  const file = e.target.files?.[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = () => {
    editImageData = reader.result;
    removeExistingImage = false;
    $("#editImagePreview").src = editImageData;
    $("#editImagePreviewWrap").classList.remove("hidden");
  };
  reader.readAsDataURL(file);
});

$("#removeImageBtn").addEventListener("click", () => {
  editImageData = null;
  removeExistingImage = true;
  $("#editImage").value = "";
  $("#editImagePreview").removeAttribute("src");
  $("#editImagePreviewWrap").classList.add("hidden");
});

$("#editForm").addEventListener("submit", async (e) => {
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

$("#deleteEntryBtn").addEventListener("click", async () => {
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

document.addEventListener("click", (e) => {
  const edit = e.target.closest("[data-edit]");
  if (!edit) return;
  openEdit(Number(edit.dataset.edit));
});


render();

mediaReady = initializeMediaStorage().catch((err) => {
  console.error("Constellation media migration/hydration failed.", err);
  alert("Constellation could not finish preparing safe image storage. Your existing saved data was not intentionally cleared. Please avoid replacing images until this is fixed.");
});

// --- Desktop app update support (Tauri) ---
const tauriInvoke = window.__TAURI__?.core?.invoke;

async function refreshDesktopVersion() {
  if (!tauriInvoke) return;
  try {
    const version = await tauriInvoke("app_version");
    const versionEl = document.querySelector("#appVersion");
    if (versionEl) versionEl.textContent = version;
  } catch (_) {}
}

async function checkDesktopUpdate({ automatic = false } = {}) {
  if (!tauriInvoke) return;
  const status = document.querySelector("#updateStatus");
  const button = document.querySelector("#checkUpdateBtn");
  try {
    if (button) button.disabled = true;
    if (status && !automatic) status.textContent = "Checking for updates…";
    const result = await tauriInvoke("check_for_update");
    if (!result.available || !result.update) {
      if (status) status.textContent = `Constellation is up to date (v${result.currentVersion}).`;
      return;
    }

    const update = result.update;
    if (status) status.textContent = `Constellation ${update.version} is available.`;
    const install = automatic
      ? confirm(`Constellation ${update.version} is available. Install it now?${update.notes ? `\n\n${update.notes}` : ""}`)
      : confirm(`Update ${update.version} is ready. Install it now?${update.notes ? `\n\n${update.notes}` : ""}`);
    if (install) {
      if (status) status.textContent = "Downloading and installing update…";
      await tauriInvoke("install_update", { url: update.url, sha256: update.sha256 });
    }
  } catch (err) {
    if (status && !automatic) status.textContent = String(err);
  } finally {
    if (button) button.disabled = false;
  }
}

const updateBtn = document.querySelector("#checkUpdateBtn");
if (updateBtn) updateBtn.addEventListener("click", () => checkDesktopUpdate());

window.addEventListener("DOMContentLoaded", () => {
  refreshDesktopVersion();
  if (tauriInvoke) setTimeout(() => checkDesktopUpdate({ automatic: true }), 1400);
});


const shortcutIconFile=$("#shortcutIconFile");
const shortcutIconDropZone=$("#shortcutIconDropZone");

async function applyShortcutIconFile(file){
  const status=$("#shortcutIconStatus");
  if(!file||!tauriInvoke)return;
  try{
    if(status)status.textContent="Preparing image…";
    let iconData;
    if(file.name.toLowerCase().endsWith(".ico")){
      iconData=await new Promise((resolve,reject)=>{
        const reader=new FileReader();
        reader.onload=()=>resolve(String(reader.result));
        reader.onerror=()=>reject(new Error("Could not read that icon file."));
        reader.readAsDataURL(file);
      });
    }else{
      iconData=await new Promise((resolve,reject)=>{
        const url=URL.createObjectURL(file);
        const img=new Image();
        img.onload=()=>{
          try{
            const size=256;
            const canvas=document.createElement("canvas");
            canvas.width=size; canvas.height=size;
            const ctx=canvas.getContext("2d");
            ctx.clearRect(0,0,size,size);
            const scale=Math.min(size/img.naturalWidth,size/img.naturalHeight);
            const w=Math.max(1,Math.round(img.naturalWidth*scale));
            const h=Math.max(1,Math.round(img.naturalHeight*scale));
            const x=Math.round((size-w)/2);
            const y=Math.round((size-h)/2);
            ctx.drawImage(img,x,y,w,h);
            resolve(canvas.toDataURL("image/png"));
          }catch(err){reject(err);}
          finally{URL.revokeObjectURL(url);}
        };
        img.onerror=()=>{URL.revokeObjectURL(url);reject(new Error("That image format could not be opened."));};
        img.src=url;
      });
    }
    if(status)status.textContent="Changing desktop shortcut icon…";
    const shortcutPath=await tauriInvoke("set_desktop_shortcut_icon",{iconData});
    if(status)status.textContent="Desktop shortcut created with " + file.name + ": " + shortcutPath;
  }catch(err){
    if(status)status.textContent=String(err?.message||err);
  }finally{
    if(shortcutIconFile)shortcutIconFile.value="";
    shortcutIconDropZone?.classList.remove("drag-over");
  }
}

$("#chooseShortcutIconBtn")?.addEventListener("click",()=>shortcutIconFile?.click());
shortcutIconDropZone?.addEventListener("click",()=>shortcutIconFile?.click());
shortcutIconDropZone?.addEventListener("keydown",(e)=>{
  if(e.key==="Enter"||e.key===" "){e.preventDefault();shortcutIconFile?.click();}
});
["dragenter","dragover"].forEach(type=>shortcutIconDropZone?.addEventListener(type,(e)=>{
  e.preventDefault();e.stopPropagation();shortcutIconDropZone.classList.add("drag-over");
}));
["dragleave","drop"].forEach(type=>shortcutIconDropZone?.addEventListener(type,(e)=>{
  e.preventDefault();e.stopPropagation();shortcutIconDropZone.classList.remove("drag-over");
}));
shortcutIconDropZone?.addEventListener("drop",(e)=>applyShortcutIconFile(e.dataTransfer?.files?.[0]));
shortcutIconFile?.addEventListener("change",(e)=>applyShortcutIconFile(e.target.files?.[0]));

$("#repairShortcutIconBtn")?.addEventListener("click",async()=>{
  const status=$("#shortcutIconStatus");
  if(!tauriInvoke)return;
  try{
    if(status)status.textContent="Repairing desktop shortcut icon…";
    const shortcutPath=await tauriInvoke("reset_desktop_shortcut_icon");
    if(status)status.textContent="Desktop shortcut recreated with the Constellation app icon: " + shortcutPath;
  }catch(err){
    if(status)status.textContent=String(err);
  }
});
