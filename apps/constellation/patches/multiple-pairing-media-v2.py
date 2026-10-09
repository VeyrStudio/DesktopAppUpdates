from pathlib import Path

root = Path("apps/constellation")
app = root / "src" / "app.js"
css = root / "src" / "styles.css"

app_text = app.read_text(encoding="utf-8")

if "CONSTELLATION_EXTRA_MEDIA_DB" in app_text:
    print("Multiple pairing media v2 already applied.")
    raise SystemExit(0)

old = '''    <article class="ship-card">
      <div class="card-art ${x.image ? "has-image" : ""}">${artHTML}</div>
'''
new = '''    <article class="ship-card" data-entry-id="${esc(String(x.id ?? ""))}">
      <div class="card-art ${x.image ? "has-image" : ""}">${artHTML}</div>
'''
if old not in app_text:
    raise SystemExit("Could not find ship-card markup for multiple media patch.")
app_text = app_text.replace(old, new, 1)

addon = r'''
/* --- Multiple images / GIFs / videos per pairing --- */
/* Reuse the v0.1.16 database name so any extra images already added there reappear. */
const CONSTELLATION_EXTRA_MEDIA_DB = "constellation-media-v1";
const CONSTELLATION_EXTRA_MEDIA_STORE = "pairing_images";

function openConstellationExtraMediaDb(){
  return new Promise((resolve,reject)=>{
    const req=indexedDB.open(CONSTELLATION_EXTRA_MEDIA_DB,1);
    req.onupgradeneeded=()=>{
      const db=req.result;
      if(!db.objectStoreNames.contains(CONSTELLATION_EXTRA_MEDIA_STORE)){
        const store=db.createObjectStore(CONSTELLATION_EXTRA_MEDIA_STORE,{keyPath:"key"});
        store.createIndex("entryId","entryId",{unique:false});
      }
    };
    req.onsuccess=()=>resolve(req.result);
    req.onerror=()=>reject(req.error||new Error("Could not open pairing media storage."));
  });
}

async function getPairingExtraMedia(entryId){
  const db=await openConstellationExtraMediaDb();
  return new Promise((resolve,reject)=>{
    const tx=db.transaction(CONSTELLATION_EXTRA_MEDIA_STORE,"readonly");
    const store=tx.objectStore(CONSTELLATION_EXTRA_MEDIA_STORE);
    const index=store.index("entryId");
    const req=index.getAll(String(entryId));
    req.onsuccess=()=>{
      const rows=(req.result||[]).sort((a,b)=>(a.createdAt||0)-(b.createdAt||0));
      db.close();
      resolve(rows);
    };
    req.onerror=()=>{
      const err=req.error;
      db.close();
      reject(err||new Error("Could not load pairing media."));
    };
  });
}

async function addPairingExtraMedia(entryId,files){
  const db=await openConstellationExtraMediaDb();
  return new Promise((resolve,reject)=>{
    const tx=db.transaction(CONSTELLATION_EXTRA_MEDIA_STORE,"readwrite");
    const store=tx.objectStore(CONSTELLATION_EXTRA_MEDIA_STORE);
    const now=Date.now();
    [...files].forEach((file,i)=>{
      store.put({
        key:String(entryId)+":"+now+":"+i+":"+Math.random().toString(36).slice(2),
        entryId:String(entryId),
        name:file.name||("media-"+(i+1)),
        type:file.type||"",
        blob:file,
        createdAt:now+i
      });
    });
    tx.oncomplete=()=>{db.close();resolve();};
    tx.onerror=()=>{const err=tx.error;db.close();reject(err||new Error("Could not save pairing media."));};
    tx.onabort=()=>{const err=tx.error;db.close();reject(err||new Error("Could not save pairing media."));};
  });
}

async function removePairingExtraMedia(key){
  const db=await openConstellationExtraMediaDb();
  return new Promise((resolve,reject)=>{
    const tx=db.transaction(CONSTELLATION_EXTRA_MEDIA_STORE,"readwrite");
    tx.objectStore(CONSTELLATION_EXTRA_MEDIA_STORE).delete(key);
    tx.oncomplete=()=>{db.close();resolve();};
    tx.onerror=()=>{const err=tx.error;db.close();reject(err||new Error("Could not remove pairing media."));};
    tx.onabort=()=>{const err=tx.error;db.close();reject(err||new Error("Could not remove pairing media."));};
  });
}

function revokeConstellationExtraObjectUrls(card){
  const urls=card._constellationExtraObjectUrls||[];
  urls.forEach(url=>{try{URL.revokeObjectURL(url)}catch{}});
  card._constellationExtraObjectUrls=[];
}

function pairingMediaKind(item){
  const type=String(item?.type||"").toLowerCase();
  if(type.startsWith("video/"))return "video";
  const name=String(item?.name||"").toLowerCase();
  if(/\.(mp4|webm|mov|m4v|ogv|ogg)$/i.test(name))return "video";
  return "image";
}

function setPairingCardMedia(art,current){
  art.querySelector(".card-art-image")?.remove();
  art.querySelector(".card-art-video")?.remove();

  if(current.kind==="video"){
    const video=document.createElement("video");
    video.className="card-art-video";
    video.src=current.src;
    video.muted=true;
    video.loop=true;
    video.autoplay=true;
    video.playsInline=true;
    video.controls=true;
    video.preload="metadata";
    art.prepend(video);
    video.play().catch(()=>{});
  }else{
    const img=document.createElement("img");
    img.className="card-art-image";
    img.src=current.src;
    img.alt="";
    art.prepend(img);
  }
  art.classList.add("has-image");
}

async function refreshPairingMediaCarousel(card,keepIndex=true){
  const entryId=card?.dataset?.entryId;
  const art=card?.querySelector?.(".card-art");
  if(!entryId||!art)return;

  revokeConstellationExtraObjectUrls(card);

  const entry=entries.find(x=>String(x.id)===String(entryId));
  const primary=entry?.image||"";
  const extras=await getPairingExtraMedia(entryId);
  const objectUrls=extras.map(x=>URL.createObjectURL(x.blob));
  card._constellationExtraObjectUrls=objectUrls;

  const media=[];
  if(primary)media.push({src:primary,key:null,primary:true,kind:"image"});
  extras.forEach((x,i)=>media.push({
    src:objectUrls[i],
    key:x.key,
    primary:false,
    kind:pairingMediaKind(x),
    name:x.name||"",
    type:x.type||""
  }));

  if(!media.length){
    art.querySelector(".pairing-media-controls")?.remove();
    art.querySelector(".card-art-image")?.remove();
    art.querySelector(".card-art-video")?.remove();
    art.classList.remove("has-image");
    return;
  }

  let index=keepIndex?Number(card.dataset.pairingMediaIndex||0):0;
  if(!Number.isFinite(index)||index<0)index=0;
  if(index>=media.length)index=media.length-1;
  card.dataset.pairingMediaIndex=String(index);

  let controls=art.querySelector(".pairing-media-controls");
  if(!controls){
    controls=document.createElement("div");
    controls.className="pairing-media-controls";
    controls.innerHTML='<button type="button" class="pairing-media-nav pairing-media-prev" title="Previous media" aria-label="Previous media">‹</button><span class="pairing-media-count"></span><button type="button" class="pairing-media-nav pairing-media-next" title="Next media" aria-label="Next media">›</button><button type="button" class="pairing-media-add" title="Add images, GIFs, or videos" aria-label="Add images, GIFs, or videos">+</button><button type="button" class="pairing-media-remove" title="Remove this extra media" aria-label="Remove this extra media">×</button><input class="pairing-media-input" type="file" accept="image/*,video/*" multiple hidden>';
    art.appendChild(controls);

    const stop=e=>e.stopPropagation();
    controls.addEventListener("click",stop);
    controls.addEventListener("dblclick",stop);

    controls.querySelector(".pairing-media-prev")?.addEventListener("click",async(e)=>{
      e.preventDefault();
      const n=Number(card.dataset.pairingMediaCount||1);
      let i=Number(card.dataset.pairingMediaIndex||0);
      card.dataset.pairingMediaIndex=String((i-1+n)%n);
      await refreshPairingMediaCarousel(card,true);
    });
    controls.querySelector(".pairing-media-next")?.addEventListener("click",async(e)=>{
      e.preventDefault();
      const n=Number(card.dataset.pairingMediaCount||1);
      let i=Number(card.dataset.pairingMediaIndex||0);
      card.dataset.pairingMediaIndex=String((i+1)%n);
      await refreshPairingMediaCarousel(card,true);
    });

    const input=controls.querySelector(".pairing-media-input");
    controls.querySelector(".pairing-media-add")?.addEventListener("click",(e)=>{
      e.preventDefault();
      input?.click();
    });

    input?.addEventListener("change",async(e)=>{
      const files=[...(e.target.files||[])].filter(file=>{
        const t=String(file.type||"").toLowerCase();
        return t.startsWith("image/")||t.startsWith("video/");
      });
      if(files.length){
        try{
          const oldCount=Number(card.dataset.pairingMediaCount||0);
          await addPairingExtraMedia(entryId,files);
          card.dataset.pairingMediaIndex=String(Math.max(0,oldCount));
          await refreshPairingMediaCarousel(card,true);
        }catch(err){
          console.error("Could not add pairing media.",err);
          alert("Constellation could not save that media. Your existing pairing media was left alone.");
        }
      }
      e.target.value="";
    });

    controls.querySelector(".pairing-media-remove")?.addEventListener("click",async(e)=>{
      e.preventDefault();
      const currentKey=card._constellationCurrentExtraKey;
      if(!currentKey)return;
      try{
        await removePairingExtraMedia(currentKey);
        card.dataset.pairingMediaIndex="0";
        await refreshPairingMediaCarousel(card,false);
      }catch(err){
        console.error("Could not remove pairing media.",err);
        alert("Constellation could not remove that media.");
      }
    });
  }

  const current=media[index];
  setPairingCardMedia(art,current);
  card._constellationCurrentExtraKey=current.key;
  card.dataset.pairingMediaCount=String(media.length);

  const count=controls.querySelector(".pairing-media-count");
  if(count)count.textContent=media.length>1?String(index+1)+"/"+String(media.length):"";
  const prev=controls.querySelector(".pairing-media-prev");
  const next=controls.querySelector(".pairing-media-next");
  if(prev)prev.hidden=media.length<2;
  if(next)next.hidden=media.length<2;
  const remove=controls.querySelector(".pairing-media-remove");
  if(remove)remove.hidden=current.primary||!current.key;
}

function enhanceConstellationPairingMedia(root=document){
  root.querySelectorAll?.(".ship-card[data-entry-id]").forEach(card=>{
    if(card.dataset.pairingMediaReady==="1")return;
    card.dataset.pairingMediaReady="1";
    Promise.resolve(mediaReady).then(()=>refreshPairingMediaCarousel(card,false)).catch(err=>{
      console.error("Could not load pairing media.",err);
    });
  });
}

document.addEventListener("DOMContentLoaded",()=>{
  enhanceConstellationPairingMedia();
  const observer=new MutationObserver(mutations=>{
    for(const m of mutations){
      for(const node of m.addedNodes){
        if(node.nodeType!==1)continue;
        if(node.matches?.(".ship-card[data-entry-id]")){
          enhanceConstellationPairingMedia(node.parentElement||document);
        }else{
          enhanceConstellationPairingMedia(node);
        }
      }
    }
  });
  observer.observe(document.body,{childList:true,subtree:true});
});
'''

app_text += "\n" + addon + "\n"
app.write_text(app_text, encoding="utf-8")

css_text = css.read_text(encoding="utf-8")
styles = r'''
.card-art{position:relative}
.card-art-video{
  width:100%;
  height:100%;
  display:block;
  object-fit:cover;
  background:#14081d;
}
.pairing-media-controls{
  position:absolute;
  inset:0;
  pointer-events:none;
  z-index:4;
}
.pairing-media-controls button,.pairing-media-count{pointer-events:auto}
.pairing-media-nav{
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
.pairing-media-prev{left:8px}
.pairing-media-next{right:8px}
.card-art:hover .pairing-media-nav{opacity:1}
.pairing-media-count{
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
.pairing-media-add,.pairing-media-remove{
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
.pairing-media-add{right:7px}
.pairing-media-remove{right:41px;font-size:18px}
.pairing-media-add:hover,.pairing-media-remove:hover,.pairing-media-nav:hover{background:rgba(54,18,81,.95)}
'''
if ".pairing-media-controls{" not in css_text:
    css_text += "\n" + styles + "\n"
css.write_text(css_text, encoding="utf-8")

print("Multiple pairing media v2 enabled.")
