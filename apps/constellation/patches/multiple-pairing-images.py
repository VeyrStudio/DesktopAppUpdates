from pathlib import Path

root = Path("apps/constellation")
app = root / "src" / "app.js"
css = root / "src" / "styles.css"

app_text = app.read_text(encoding="utf-8")

old = '''    <article class="ship-card">
      <div class="card-art ${x.image ? "has-image" : ""}">${artHTML}</div>
'''
new = '''    <article class="ship-card" data-entry-id="${esc(String(x.id ?? ""))}">
      <div class="card-art ${x.image ? "has-image" : ""}">${artHTML}</div>
'''
if old not in app_text:
    raise SystemExit("Could not find ship-card markup for multi-image patch.")
app_text = app_text.replace(old, new, 1)

addon = r'''
/* --- Multiple images per pairing --- */
const CONSTELLATION_MEDIA_DB="constellation-media-v1";
const CONSTELLATION_MEDIA_STORE="pairing_images";

function openConstellationMediaDb(){
  return new Promise((resolve,reject)=>{
    const req=indexedDB.open(CONSTELLATION_MEDIA_DB,1);
    req.onupgradeneeded=()=>{
      const db=req.result;
      if(!db.objectStoreNames.contains(CONSTELLATION_MEDIA_STORE)){
        const store=db.createObjectStore(CONSTELLATION_MEDIA_STORE,{keyPath:"key"});
        store.createIndex("entryId","entryId",{unique:false});
      }
    };
    req.onsuccess=()=>resolve(req.result);
    req.onerror=()=>reject(req.error||new Error("Could not open image storage."));
  });
}

async function getPairingExtraImages(entryId){
  const db=await openConstellationMediaDb();
  return new Promise((resolve,reject)=>{
    const tx=db.transaction(CONSTELLATION_MEDIA_STORE,"readonly");
    const index=tx.objectStore(CONSTELLATION_MEDIA_STORE).index("entryId");
    const req=index.getAll(String(entryId));
    req.onsuccess=()=>resolve((req.result||[]).sort((a,b)=>(a.createdAt||0)-(b.createdAt||0)));
    req.onerror=()=>reject(req.error||new Error("Could not load pairing images."));
  });
}

async function addPairingExtraImages(entryId,files){
  const db=await openConstellationMediaDb();
  return new Promise((resolve,reject)=>{
    const tx=db.transaction(CONSTELLATION_MEDIA_STORE,"readwrite");
    const store=tx.objectStore(CONSTELLATION_MEDIA_STORE);
    const now=Date.now();
    [...files].forEach((file,i)=>{
      store.put({
        key:String(entryId)+":"+now+":"+i+":"+Math.random().toString(36).slice(2),
        entryId:String(entryId),
        name:file.name||("image-"+(i+1)),
        type:file.type||"",
        blob:file,
        createdAt:now+i
      });
    });
    tx.oncomplete=()=>resolve();
    tx.onerror=()=>reject(tx.error||new Error("Could not save pairing images."));
  });
}

async function removePairingExtraImage(key){
  const db=await openConstellationMediaDb();
  return new Promise((resolve,reject)=>{
    const tx=db.transaction(CONSTELLATION_MEDIA_STORE,"readwrite");
    tx.objectStore(CONSTELLATION_MEDIA_STORE).delete(key);
    tx.oncomplete=()=>resolve();
    tx.onerror=()=>reject(tx.error||new Error("Could not remove image."));
  });
}

function revokeConstellationObjectUrls(card){
  const urls=card._constellationObjectUrls||[];
  urls.forEach(url=>{try{URL.revokeObjectURL(url)}catch{}});
  card._constellationObjectUrls=[];
}

async function refreshPairingImageCarousel(card,keepIndex=true){
  const entryId=card?.dataset?.entryId;
  const art=card?.querySelector?.(".card-art");
  if(!entryId||!art)return;

  revokeConstellationObjectUrls(card);

  let img=art.querySelector(".card-art-image");
  const primary=img?.dataset?.constellationPrimary || img?.getAttribute("src") || "";
  if(img && !img.dataset.constellationPrimary) img.dataset.constellationPrimary=primary;

  const extras=await getPairingExtraImages(entryId);
  const objectUrls=extras.map(x=>URL.createObjectURL(x.blob));
  card._constellationObjectUrls=objectUrls;

  const images=[];
  if(primary)images.push({src:primary,key:null,primary:true});
  extras.forEach((x,i)=>images.push({src:objectUrls[i],key:x.key,primary:false}));

  if(!images.length){
    art.querySelector(".pairing-image-controls")?.remove();
    if(img && !primary)img.remove();
    return;
  }

  if(!img){
    img=document.createElement("img");
    img.className="card-art-image";
    img.alt="";
    img.dataset.constellationPrimary="";
    art.prepend(img);
    art.classList.add("has-image");
  }

  let index=keepIndex?Number(card.dataset.pairingImageIndex||0):0;
  if(!Number.isFinite(index)||index<0)index=0;
  if(index>=images.length)index=images.length-1;
  card.dataset.pairingImageIndex=String(index);

  let controls=art.querySelector(".pairing-image-controls");
  if(!controls){
    controls=document.createElement("div");
    controls.className="pairing-image-controls";
    controls.innerHTML='<button type="button" class="pairing-image-nav pairing-image-prev" title="Previous image" aria-label="Previous image">‹</button><span class="pairing-image-count"></span><button type="button" class="pairing-image-nav pairing-image-next" title="Next image" aria-label="Next image">›</button><button type="button" class="pairing-image-add" title="Add more images" aria-label="Add more images">+</button><button type="button" class="pairing-image-remove" title="Remove this extra image" aria-label="Remove this extra image">×</button><input class="pairing-image-input" type="file" accept="image/*" multiple hidden>';
    art.appendChild(controls);

    const stop=e=>e.stopPropagation();
    controls.addEventListener("click",stop);
    controls.addEventListener("dblclick",stop);

    controls.querySelector(".pairing-image-prev")?.addEventListener("click",async(e)=>{
      e.preventDefault();
      const n=Number(card.dataset.pairingImageCount||1);
      let i=Number(card.dataset.pairingImageIndex||0);
      i=(i-1+n)%n;
      card.dataset.pairingImageIndex=String(i);
      await refreshPairingImageCarousel(card,true);
    });
    controls.querySelector(".pairing-image-next")?.addEventListener("click",async(e)=>{
      e.preventDefault();
      const n=Number(card.dataset.pairingImageCount||1);
      let i=Number(card.dataset.pairingImageIndex||0);
      i=(i+1)%n;
      card.dataset.pairingImageIndex=String(i);
      await refreshPairingImageCarousel(card,true);
    });
    const input=controls.querySelector(".pairing-image-input");
    controls.querySelector(".pairing-image-add")?.addEventListener("click",(e)=>{
      e.preventDefault();
      input?.click();
    });
    input?.addEventListener("change",async(e)=>{
      const files=e.target.files;
      if(files?.length){
        await addPairingExtraImages(entryId,files);
        card.dataset.pairingImageIndex="0";
        await refreshPairingImageCarousel(card,false);
      }
      e.target.value="";
    });
    controls.querySelector(".pairing-image-remove")?.addEventListener("click",async(e)=>{
      e.preventDefault();
      const currentKey=card._constellationCurrentExtraKey;
      if(!currentKey)return;
      await removePairingExtraImage(currentKey);
      card.dataset.pairingImageIndex="0";
      await refreshPairingImageCarousel(card,false);
    });
  }

  const current=images[index];
  img.src=current.src;
  card._constellationCurrentExtraKey=current.key;
  card.dataset.pairingImageCount=String(images.length);

  const count=controls.querySelector(".pairing-image-count");
  if(count)count.textContent=images.length>1?String(index+1)+"/"+String(images.length):"";
  const prev=controls.querySelector(".pairing-image-prev");
  const next=controls.querySelector(".pairing-image-next");
  if(prev)prev.hidden=images.length<2;
  if(next)next.hidden=images.length<2;
  const remove=controls.querySelector(".pairing-image-remove");
  if(remove)remove.hidden=current.primary || !current.key;
}

function enhanceConstellationPairingCards(root=document){
  root.querySelectorAll?.(".ship-card[data-entry-id]").forEach(card=>{
    if(card.dataset.pairingImagesReady==="1")return;
    card.dataset.pairingImagesReady="1";
    refreshPairingImageCarousel(card,false).catch(()=>{});
  });
}

document.addEventListener("DOMContentLoaded",()=>{
  enhanceConstellationPairingCards();
  const observer=new MutationObserver(mutations=>{
    for(const m of mutations){
      for(const node of m.addedNodes){
        if(node.nodeType!==1)continue;
        if(node.matches?.(".ship-card[data-entry-id]")){
          enhanceConstellationPairingCards(node.parentElement||document);
        }else{
          enhanceConstellationPairingCards(node);
        }
      }
    }
  });
  observer.observe(document.body,{childList:true,subtree:true});
});
'''
if "CONSTELLATION_MEDIA_DB" not in app_text:
    app_text += "\n" + addon + "\n"

app.write_text(app_text, encoding="utf-8")

css_text = css.read_text(encoding="utf-8")
styles = r'''
.card-art{position:relative}
.pairing-image-controls{
  position:absolute;
  inset:0;
  pointer-events:none;
  z-index:4;
}
.pairing-image-controls button,.pairing-image-count{pointer-events:auto}
.pairing-image-nav{
  position:absolute;
  top:50%;
  transform:translateY(-50%);
  width:30px;
  height:42px;
  border:0;
  border-radius:9px;
  background:rgba(20,8,29,.72);
  color:#fff;
  font-size:26px;
  line-height:1;
  display:grid;
  place-items:center;
  cursor:pointer;
  opacity:0;
  transition:.15s;
}
.pairing-image-prev{left:8px}
.pairing-image-next{right:8px}
.card-art:hover .pairing-image-nav{opacity:1}
.pairing-image-count{
  position:absolute;
  left:50%;
  bottom:7px;
  transform:translateX(-50%);
  min-width:38px;
  padding:3px 7px;
  border-radius:999px;
  background:rgba(20,8,29,.72);
  color:#fff;
  font-size:11px;
  text-align:center;
}
.pairing-image-add,.pairing-image-remove{
  position:absolute;
  top:7px;
  width:28px;
  height:28px;
  border:0;
  border-radius:50%;
  display:grid;
  place-items:center;
  cursor:pointer;
  background:rgba(20,8,29,.78);
  color:#fff;
  font-size:20px;
  line-height:1;
}
.pairing-image-add{right:7px}
.pairing-image-remove{right:41px;font-size:18px}
.pairing-image-add:hover,.pairing-image-remove:hover,.pairing-image-nav:hover{background:rgba(54,18,81,.95)}
'''
if ".pairing-image-controls{" not in css_text:
    css_text += "\n" + styles + "\n"
css.write_text(css_text, encoding="utf-8")

print("Multiple pairing images enabled.")
