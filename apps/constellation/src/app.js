const STORAGE_KEY = "constellation_entries_v4_editable";
let entries = JSON.parse(localStorage.getItem(STORAGE_KEY) || "null") || window.CONSTELLATION_SEED;
let currentView = "dashboard";
let activeFandomPage = null;

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => [...document.querySelectorAll(sel)];

function save() { localStorage.setItem(STORAGE_KEY, JSON.stringify(entries)); }
function esc(s="") { return String(s).replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[m])); }
function shipLabel(x) { return `${x.a} ${x.category === "platonic" ? "&" : "×"} ${x.b}`; }
function uniqueSorted(values) { return [...new Set(values.filter(Boolean))].sort((a,b)=>a.localeCompare(b)); }

function refreshFilters() {
  const fandoms = uniqueSorted(entries.map(x=>x.fandom));
  const chars = uniqueSorted(entries.flatMap(x=>[x.a, x.b]));
  const fandomSel = $("#fandomFilter"), charSel = $("#characterFilter");
  const oldF = fandomSel.value, oldC = charSel.value;
  fandomSel.innerHTML = `<option value="">All fandoms</option>` + fandoms.map(x=>`<option>${esc(x)}</option>`).join("");
  charSel.innerHTML = `<option value="">All characters</option>` + chars.map(x=>`<option>${esc(x)}</option>`).join("");
  if (fandoms.includes(oldF)) fandomSel.value = oldF;
  if (chars.includes(oldC)) charSel.value = oldC;
}

function getFiltered(base=entries) {
  const q = $("#searchInput").value.trim().toLowerCase(), fandom = $("#fandomFilter").value, type = $("#typeFilter").value, character = $("#characterFilter").value;
  return base.filter(x => {
    const hay = `${x.a} ${x.b} ${x.fandom} ${x.type||""}`.toLowerCase();
    return (!q || hay.includes(q)) && (!fandom || x.fandom === fandom) && (!type || x.type === type) && (!character || x.a === character || x.b === character);
  });
}

function cardHTML(x) {
  const cat = x.category === "platonic" ? "Platonic" : "Romantic";
  const artStyle = x.image ? `style="background-image:url('${x.image.replace(/'/g, "%27")}')"` : "";
  return `
    <article class="ship-card">
      <div class="card-art ${x.image ? "has-image" : ""}" ${artStyle}></div>
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
    cur.ships++; cur[x.category]++; map.set(x.fandom, cur);
  });
  return [...map.values()].sort((a,b)=>a.name.localeCompare(b.name));
}
function fandomHTML(f) {
  return `
    <article class="fandom-card" data-open-fandom="${esc(f.name)}" tabindex="0" role="button" aria-label="Open ${esc(f.name)}">
      <div><div class="fandom-name">${esc(f.name)}</div><div class="chips" style="margin-top:10px">
        ${f.romantic ? `<span class="chip romantic">${f.romantic} romantic</span>` : ""}
        ${f.platonic ? `<span class="chip platonic">${f.platonic} platonic</span>` : ""}
      </div></div>
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
  if (currentView === "fandomDetail" && activeFandomPage) base = entries.filter(x=>x.fandom === activeFandomPage);
  const filtered = getFiltered(base);
  $("#fandomPageBar").classList.toggle("hidden", currentView !== "fandomDetail");
  if (currentView === "fandomDetail") $("#fandomPageName").textContent = activeFandomPage || "";
  $("#listHeading").textContent = currentView === "romantic" ? "Romantic Ships" : currentView === "platonic" ? "Platonic Relationships" : currentView === "favorites" ? "Favorites" : currentView === "fandomDetail" ? `${activeFandomPage} Ships & Relationships` : "Ships";
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
  activeFandomPage = name; currentView = "fandomDetail"; $("#fandomFilter").value = "";
  $$(".view").forEach(v=>v.classList.remove("active"));
  $$(".nav-item").forEach(n=>n.classList.toggle("active", n.dataset.view === "fandoms"));
  $("#listView").classList.add("active");
  $("#pageTitle").textContent = name; $("#pageSubtitle").textContent = `Everything in ${name}.`; render();
}
function setView(view) {
  currentView = view; if (view !== "fandomDetail") activeFandomPage = null;
  $$(".view").forEach(v=>v.classList.remove("active")); $$(".nav-item").forEach(n=>n.classList.toggle("active",n.dataset.view===view));
  if (view === "dashboard") { $("#dashboardView").classList.add("active"); $("#pageTitle").textContent = "Dashboard"; $("#pageSubtitle").textContent = "A home for the fandoms and ships you love."; }
  else if (view === "settings") { $("#settingsView").classList.add("active"); $("#pageTitle").textContent = "Settings"; $("#pageSubtitle").textContent = "Manage Constellation and check for updates."; }
  else if (view === "fandoms") { $("#fandomView").classList.add("active"); $("#pageTitle").textContent = "Fandoms"; $("#pageSubtitle").textContent = "Browse everything by fandom."; }
  else {
    $("#listView").classList.add("active");
    $("#pageTitle").textContent = view === "romantic" ? "Romantic" : view === "platonic" ? "Platonic" : view === "favorites" ? "Favorites" : "Ships";
    $("#pageSubtitle").textContent = view === "romantic" ? "All of your romantic ships in one place." : view === "platonic" ? "Family, friendship, and other platonic relationships." : "Your pinned favorites.";
  }
  render();
}
function render() {
  refreshFilters();
  const selectedFandom = $("#fandomFilter").value;
  $("#openFandomBtn").classList.toggle("hidden", !selectedFandom);
  $("#openFandomBtn").textContent = selectedFandom ? `Open ${selectedFandom} →` : "Open Fandom →";
  renderDashboard(); renderList(); renderFandoms();
}

$$(".nav-item").forEach(btn=>btn.addEventListener("click",()=>setView(btn.dataset.view)));
$$("[data-view-jump]").forEach(btn=>btn.addEventListener("click",()=>setView(btn.dataset.viewJump)));
$$(".side-link").forEach(btn=>btn.addEventListener("click",()=>{
  const mode = btn.dataset.browse;
  if(mode==="fandom") setView("fandoms");
  else { setView("romantic"); setTimeout(()=>{ if(mode==="type") $("#typeFilter").focus(); if(mode==="character") $("#characterFilter").focus(); },0); }
}));
["searchInput","fandomFilter","typeFilter","characterFilter"].forEach(id=>$("#"+id).addEventListener(id==="searchInput" ? "input" : "change", render));
$("#clearFilters").addEventListener("click",()=>{ $("#searchInput").value=""; $("#fandomFilter").value=""; $("#typeFilter").value=""; $("#characterFilter").value=""; render(); });
document.addEventListener("click",(e)=>{ const fav = e.target.closest("[data-fav]"); if(!fav) return; const x = entries.find(x=>x.id===Number(fav.dataset.fav)); if(x){x.favorite=!x.favorite; save(); render();} });
document.addEventListener("click", (e) => { const t=e.target.closest("[data-open-fandom]"); if(!t)return; e.preventDefault(); e.stopPropagation(); openFandom(t.dataset.openFandom); });
document.addEventListener("keydown", (e) => { const t=e.target.closest?.("[data-open-fandom]"); if(!t||(e.key!=="Enter"&&e.key!==" "))return; e.preventDefault(); openFandom(t.dataset.openFandom); });
$("#openFandomBtn").addEventListener("click",()=>{const f=$("#fandomFilter").value;if(f)openFandom(f);});
$("#backToFandomsBtn").addEventListener("click",()=>setView("fandoms"));

const dlg=$("#addDialog");
$("#addNewBtn").addEventListener("click",()=>dlg.showModal());
$("#newCategory").addEventListener("change",()=>{$("#newTypeWrap").style.display=$("#newCategory").value==="romantic"?"":"none";});
$("#addForm").addEventListener("submit",(e)=>{
  if(e.submitter?.value==="cancel")return; e.preventDefault();
  const category=$("#newCategory").value;
  const item={id:Math.max(0,...entries.map(x=>x.id))+1,a:$("#newA").value.trim(),b:$("#newB").value.trim(),fandom:$("#newFandom").value.trim(),category,favorite:$("#newFavorite").checked};
  if(category==="romantic")item.type=$("#newType").value;
  if(!item.a||!item.b||!item.fandom)return;
  entries.push(item); save(); $("#addForm").reset(); $("#newTypeWrap").style.display=""; dlg.close(); setView(category);
});

const editDlg=$("#editDialog"); let editImageData=null, removeExistingImage=false;
function openEdit(id){
  const x=entries.find(x=>x.id===id); if(!x)return;
  $("#editId").value=x.id; $("#editCategory").value=x.category; $("#editA").value=x.a; $("#editB").value=x.b; $("#editFandom").value=x.fandom; $("#editType").value=x.type||"M/M"; $("#editFavorite").checked=!!x.favorite;
  $("#editTypeWrap").style.display=x.category==="romantic"?"":"none"; editImageData=null; removeExistingImage=false; $("#editImage").value="";
  if(x.image){$("#editImagePreview").src=x.image;$("#editImagePreviewWrap").classList.remove("hidden");}else{$("#editImagePreview").removeAttribute("src");$("#editImagePreviewWrap").classList.add("hidden");}
  editDlg.showModal();
}
$("#editCategory").addEventListener("change",()=>{$("#editTypeWrap").style.display=$("#editCategory").value==="romantic"?"":"none";});
$("#editImage").addEventListener("change",(e)=>{const file=e.target.files?.[0];if(!file)return;const reader=new FileReader();reader.onload=()=>{editImageData=reader.result;removeExistingImage=false;$("#editImagePreview").src=editImageData;$("#editImagePreviewWrap").classList.remove("hidden");};reader.readAsDataURL(file);});
$("#removeImageBtn").addEventListener("click",()=>{editImageData=null;removeExistingImage=true;$("#editImage").value="";$("#editImagePreview").removeAttribute("src");$("#editImagePreviewWrap").classList.add("hidden");});
$("#editForm").addEventListener("submit",(e)=>{
  if(e.submitter?.value==="cancel")return;e.preventDefault();
  const x=entries.find(x=>x.id===Number($("#editId").value));if(!x)return;
  x.category=$("#editCategory").value;x.a=$("#editA").value.trim();x.b=$("#editB").value.trim();x.fandom=$("#editFandom").value.trim();x.favorite=$("#editFavorite").checked;
  if(x.category==="romantic")x.type=$("#editType").value;else delete x.type;
  if(removeExistingImage)delete x.image;else if(editImageData)x.image=editImageData;
  save();editDlg.close();render();
});
$("#deleteEntryBtn").addEventListener("click",()=>{const id=Number($("#editId").value),x=entries.find(x=>x.id===id);if(!x)return;if(!confirm(`Delete "${shipLabel(x)}"?`))return;entries=entries.filter(item=>item.id!==id);save();editDlg.close();render();});
document.addEventListener("click",(e)=>{const edit=e.target.closest("[data-edit]");if(edit)openEdit(Number(edit.dataset.edit));});
render();

const tauriInvoke=window.__TAURI__?.core?.invoke;
async function refreshDesktopVersion(){if(!tauriInvoke)return;try{const version=await tauriInvoke("app_version");const el=$("#appVersion");if(el)el.textContent=version;}catch(_){}}
async function checkDesktopUpdate({automatic=false}={}){
  if(!tauriInvoke)return;const status=$("#updateStatus"),button=$("#checkUpdateBtn");
  try{
    if(button)button.disabled=true;if(status&&!automatic)status.textContent="Checking for updates…";
    const result=await tauriInvoke("check_for_update");
    if(!result.available||!result.update){if(status)status.textContent=`Constellation is up to date (v${result.currentVersion}).`;return;}
    const update=result.update;if(status)status.textContent=`Constellation ${update.version} is available.`;
    const install=confirm(`Constellation ${update.version} is available. Install it now?${update.notes ? `\n\n${update.notes}` : ""}`);
    if(install){if(status)status.textContent="Downloading and installing update…";await tauriInvoke("install_update",{url:update.url,sha256:update.sha256});}
  }catch(err){if(status&&!automatic)status.textContent=String(err);}finally{if(button)button.disabled=false;}
}
$("#checkUpdateBtn")?.addEventListener("click",()=>checkDesktopUpdate());
window.addEventListener("DOMContentLoaded",()=>{refreshDesktopVersion();if(tauriInvoke)setTimeout(()=>checkDesktopUpdate({automatic:true}),1400);});
