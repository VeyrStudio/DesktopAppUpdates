const {app,BrowserWindow,dialog,ipcMain,protocol,net,shell}=require('electron');
const fs=require('node:fs'), fsp=require('node:fs/promises'), path=require('node:path'),crypto=require('node:crypto');
const {pathToFileURL}=require('node:url');
protocol.registerSchemesAsPrivileged([{scheme:'replay',privileges:{standard:true,secure:true,stream:true,supportFetchAPI:true}}]);
app.setPath('userData',path.join(app.getPath('appData'),'VeyrStudio','Replay'));
const root=path.join(app.getPath('userData'),'Media'), dbfile=path.join(app.getPath('userData'),'library.json');
const initial=()=>({folders:['videos','images','gifs'].flatMap(kind=>['Dog Photos','Family','Other'].map(name=>({id:crypto.randomUUID(),kind,group:'nonfandom',name,parent:'',color:'#b58a48',pinned:false,cover:''}))),items:[],settings:{backupRoot:path.join(app.getPath('appData'),'VeyrStudio','ReplayBackup'),thumbnailSize:170,launch:'dashboard'},favorites:[]});
// Approved Replay fandom tree. Seed missing folders once, preserving all user-created folders.
const replayFandomTree=[["911",["LA","LS"]],["Arcane",[]],["Castlevania",[]],["Cobra Kai",[]],["DC",["Batman","Titans","Nightwing","Red Hood","Robin","Superman","Smallville","Superman & Lois","Supergirl","The Flash","Arrow","Legends of Tomorrow","Justice League","Doom Patrol","The Sandman","Dead Boy Detectives","Shazam!","Lucifer"]],["Eyewitness",[]],["Good Omens",[]],["Grishaverse",["Shadow and Bone","Six of Crows"]],["Hellaverse",["Hazbin Hotel","Helluva Boss"]],["Heartstopper",[]],["Heated Rivalry",[]],["Hotel Portofino",[]],["Immortal Universe",["Interview with the Vampire","The Talamasca","Armand","The Vampire Lestat"]],["Invisible Boys",[]],["Julie and the Phantoms",[]],["KPop Demon Hunters",[]],["Leviticus",[]],["Marauders",["Starchaser","Wolfstar","Modern"]],["Marvel",["The Avengers","Iron Man","Captain America","Thor","Loki","The Falcon and the Winter Soldier","Hawkeye","WandaVision","Doctor Strange","Ant-Man","Black Panther","Guardians of the Galaxy","The Marvels / Captain Marvel","Thunderbolts","Spider-Man (MCU)","The Amazing Spider-Man","Spider-Verse","X-Men","Deadpool","Wolverine","Daredevil","The Punisher","Jessica Jones","The Defenders","Moon Knight","She-Hulk","Agatha All Along","Fantastic Four","Venom"]],["Merlin",[]],["Nimona",[]],["Our Flag Means Death",[]],["Prodigal Son",[]],["Project Hail Mary",[]],["Red, White & Royal Blue",[]],["Riverdale",[]],["Roswell, New Mexico",[]],["Shadowhunters",["The Mortal Instruments","The Infernal Devices","The Dark Artifices","The Last Hours","The Eldest Curses","The Wicked Powers","The Bane Chronicles","Tales from the Shadowhunter Academy","Ghosts of the Shadow Market"]],["Shameless",[]],["Star Wars",["The Rise of Skywalker","The Mandalorian","The Book of Boba Fett","The Acolyte","Prequel Trilogy","Original Trilogy"]],["Stranger Things",[]],["Supernatural",[]],["Teen Wolf",[]],["The 100",[]],["The Gray Man",[]],["The Last of Us",[]],["The Old Guard",[]],["The Witcher",[]],["Wednesday",[]]];
function ensureApprovedFandomFolders(d){
 let added=0;
 for(const kind of ['videos','images','gifs']){
  const ensure=(name,parent='')=>{
   let f=d.folders.find(x=>x.kind===kind&&x.group==='fandom'&&(x.parent||'')===parent&&x.name.toLowerCase()===name.toLowerCase());
   if(!f){f={id:crypto.randomUUID(),kind,group:'fandom',name,parent,isSubfolder:!!parent,showInfoCard:true,autoNumberMedia:true,details:{},cover:'',color:'#b58a48',order:d.folders.length};d.folders.push(f);added++}
   return f;
  };
  for(const [name,children] of replayFandomTree){const parent=ensure(name);for(const child of children)ensure(child,parent.id)}
 }
 return added;
}
function consolidateMediaLibraries(d){
 let changes=0;
 for(const kind of ['videos','images','gifs']){
  let non=d.folders.find(f=>f.kind===kind&&f.group==='fandom'&&f.name==='Non-Fandom'&&!f.parent);
  if(!non){non={id:crypto.randomUUID(),kind,group:'fandom',name:'Non-Fandom',parent:'',color:'#b58a48',order:d.folders.length,showInfoCard:true,autoNumberMedia:true};d.folders.push(non);changes++}
  for(const f of d.folders.filter(f=>f.kind===kind&&f.group==='nonfandom')){f.group='fandom';if(!f.parent)f.parent=non.id;changes++}
  for(const item of d.items.filter(x=>x.kind===kind&&x.group==='nonfandom')){item.group='fandom';if(!item.folder)item.folder=non.id;item.fandoms=[];changes++}
 }
 return changes;
}
function enableDefaultNumberingOnce(d){
 if(d.settings?.numberingDefaultAppliedV043)return 0;
 let changed=0;
 for(const f of d.folders){
  if(!['videos','images','gifs'].includes(f.kind))continue;
  f.autoNumberMedia=true;
  f.showInfoCard=true;
  const items=d.items.filter(x=>!x.deletedAt&&x.folder===f.id&&x.kind===f.kind).sort((a,b)=>(a.order||0)-(b.order||0)||(a.added||0)-(b.added||0));
  let n=1;
  for(const item of items){item.name=safe(f.name+' '+n++);changed++}
  changed++;
 }
 d.settings=d.settings||{};
 d.settings.numberingDefaultAppliedV043=true;
 return changed+1;
}
// All three libraries share folder appearance, while media assignments remain independent.
const replayKinds=['videos','images','gifs'];
const sharedFolderFields=['name','isSubfolder','showInfoCard','autoNumberMedia','details','pinned','order','color','icon','iconImage','cover'];
function folderKey(d,f){
 const parts=[],seen=new Set();let cur=f;
 while(cur&&!seen.has(cur.id)){seen.add(cur.id);parts.unshift(cur.name.toLowerCase());cur=d.folders.find(x=>x.id===cur.parent)}
 return parts.join('/');
}
function copyFolderAppearance(source,target){
 for(const key of sharedFolderFields){
  if(source[key]!==undefined)target[key]=JSON.parse(JSON.stringify(source[key]));
  else delete target[key];
 }
}
function matchingFolderCopies(d,source){
 const key=folderKey(d,source);
 return d.folders.filter(f=>f.group===source.group&&folderKey(d,f)===key);
}
function ensureMatchingFolder(d,source,kind,seen=new Set()){
 if(source.kind===kind)return source;
 if(seen.has(source.id))throw Error('Folder hierarchy contains a cycle');
 seen.add(source.id);
 const parent=source.parent&&d.folders.find(f=>f.id===source.parent);
 const destParent=parent?ensureMatchingFolder(d,parent,kind,seen):null;
 let match=d.folders.find(f=>f.kind===kind&&f.group===source.group&&(f.parent||'')===(destParent?.id||'')&&f.name.toLowerCase()===source.name.toLowerCase());
 if(!match){
  match={id:crypto.randomUUID(),kind,group:source.group,parent:destParent?.id||'',name:source.name};
  d.folders.push(match);
 }
 return match;
}
function synchronizeFolderAppearance(d,source){
 for(const kind of replayKinds){
  const counterpart=ensureMatchingFolder(d,source,kind);
  if(counterpart!==source)copyFolderAppearance(source,counterpart);
 }
}
function synchronizeExistingVideoFoldersOnce(d){
 if(d.settings?.folderAppearanceSyncedV048)return 0;
 let changed=0;
 for(const source of d.folders.filter(f=>f.kind==='videos'&&f.group==='fandom')){
  synchronizeFolderAppearance(d,source);changed++;
 }
 d.settings.folderAppearanceSyncedV048=true;
 return changed+1;
}
async function installApprovedFandomFolders(){const d=await load();const added=ensureApprovedFandomFolders(d);const migrated=consolidateMediaLibraries(d);const numbered=enableDefaultNumberingOnce(d);const synced=synchronizeExistingVideoFoldersOnce(d);if(added||migrated||numbered||synced)await save(d);return added+migrated+numbered+synced}
// Never silently replace an unreadable or damaged existing library with an empty one.
async function load(){
 let raw;
 try{raw=await fsp.readFile(dbfile,'utf8')}catch(error){
  if(error.code==='ENOENT'&&!fs.existsSync(dbfile))return initial();
  throw new Error('Replay could not read the library. Your existing library has not been replaced: '+error.message);
 }
 let data;
 try{data=JSON.parse(raw)}catch(error){throw new Error('Replay library is not valid JSON. Your existing library has not been replaced: '+error.message)}
 if(!data||!Array.isArray(data.items)||!Array.isArray(data.folders)||!data.settings||typeof data.settings!=='object')
  throw new Error('Replay library has an invalid structure. The app will not replace it.');
 return data;
}
// Unique temp files prevent concurrent writes from deleting one another's .tmp file.
// Snapshot rollback protects the previous valid library from unexpected write failures.
let libraryWriteQueue=Promise.resolve();
async function save(d){
 const snapshot=JSON.stringify(d,null,2);
 const task=libraryWriteQueue.catch(()=>{}).then(async()=>{
  await fsp.mkdir(path.dirname(dbfile),{recursive:true});
  const tmp=dbfile+'.'+crypto.randomUUID()+'.tmp';
  try{await fsp.writeFile(tmp,snapshot);await fsp.rename(tmp,dbfile)}
  finally{await fsp.rm(tmp,{force:true}).catch(()=>{})}
 });
 libraryWriteQueue=task;
 return task;
}
const checksum=async p=>new Promise((resolve,reject)=>{const h=crypto.createHash('sha256');fs.createReadStream(p).on('data',b=>h.update(b)).on('error',reject).on('end',()=>resolve(h.digest('hex')))});
const category=f=>/\.gif$/i.test(f)?'gifs':/\.(mp4|mov|mkv|avi|webm|m4v|wmv|flv|ts)$/i.test(f)?'videos':/\.(jpg|jpeg|png|webp|bmp|heic|tif|tiff|avif)$/i.test(f)?'images':null;
async function fileCopy(src,dst){await fsp.mkdir(path.dirname(dst),{recursive:true});const tmp=dst+'.partial';await fsp.copyFile(src,tmp);if((await checksum(src))!== (await checksum(tmp))){await fsp.rm(tmp,{force:true});throw Error('Copy failed verification')}await fsp.rename(tmp,dst)}
function safe(s){return String(s).replace(/[<>:"/\\|?*\x00-\x1f]/g,'_').slice(0,90)||'Unnamed'}
async function folderPath(d,id){let f=d.folders.find(x=>x.id===id);const names=[],visited=new Set();while(f&&!visited.has(f.id)){visited.add(f.id);names.unshift(safe(f.name));f=d.folders.find(x=>x.id===f.parent)}return names.join(path.sep)}
async function backupOne(d,item){const target=d.settings.backupRoot||path.join(app.getPath('appData'),'VeyrStudio','ReplayBackup');const folders=item.group==='fandom'?[...new Set([item.folder,...(item.fandoms||[])])]:[item.folder];for(const id of folders){if(id&&!d.folders.some(f=>f.id===id&&f.kind===item.kind&&f.group===item.group))continue;const folder=await folderPath(d,id);const dir=path.join(target,item.kind,item.group==='fandom'?'Fandoms':'Non-Fandom',folder);const destination=path.join(dir,safe(item.name));try{const existing=await checksum(destination);if(existing!==item.hash)throw Error('Backup filename collision: '+item.name)}catch(error){if(error.code!=='ENOENT')throw error;await fileCopy(path.join(root,item.stored),destination)}}await fsp.mkdir(target,{recursive:true});const tmp=path.join(target,'replay-index.'+crypto.randomUUID()+'.partial');try{await fsp.writeFile(tmp,JSON.stringify(d,null,2));await fsp.rename(tmp,path.join(target,'replay-index.json'))}finally{await fsp.rm(tmp,{force:true}).catch(()=>{})}}
// Auto-numbering is opt-in per folder, including nested folders.
function numberedMediaName(d,folderId,extension,excludeId=''){
 const f=d.folders.find(x=>x.id===folderId);if(!f||!f.autoNumberMedia)return null;
 const used=new Set(d.items.filter(x=>!x.deletedAt&&x.id!==excludeId&&x.folder===folderId).map(x=>x.name.toLowerCase()));
 let number=1,name;do{name=safe(f.name+' '+number);number++}while(used.has(name.toLowerCase()));
 return name;
}
async function importFiles(arr,sender){const d=await load(),results=[];let completed=0;for(const entry of arr){completed++;sender?.send('import-progress',{completed,total:arr.length,percent:Math.round(completed/arr.length*100),status:'Importing '+path.basename(entry.path)});const src=entry.path,kind=category(src);const sourceAbsolute=path.resolve(src),archiveAbsolute=path.resolve(root);if(sourceAbsolute.startsWith(archiveAbsolute+path.sep)){results.push({name:path.basename(src),status:'error',error:'Cannot import managed archive files'});continue}if(!kind){results.push({name:path.basename(src),status:'unsupported'});continue}const hash=await checksum(src),already=d.items.find(x=>!x.deletedAt&&x.hash===hash);if(already&&!entry.keepDuplicate&&!entry.replaceDuplicate){results.push({name:path.basename(src),path:src,status:'duplicate',existing:already.id});continue}const modified=(await fsp.stat(src)).mtimeMs;const requestedFolder=d.folders.find(f=>f.id===entry.folder&&f.kind===kind);const id=crypto.randomUUID(),ext=path.extname(src),stored=path.join(kind,id+ext);let chosenName=numberedMediaName(d,requestedFolder?.id,ext)||path.basename(src);let index=2;while(d.items.some(x=>!x.deletedAt&&x.kind===kind&&x.group===(entry.group==='fandom'?'fandom':'nonfandom')&&x.folder===(requestedFolder?.id||'')&&x.name.toLowerCase()===chosenName.toLowerCase())){chosenName=path.parse(src).name+' ('+index+++')'+ext}const item={id,name:chosenName,kind,stored,hash,folder:requestedFolder?requestedFolder.id:'',group:entry.group==='fandom'?'fandom':'nonfandom',fandoms:entry.fandoms||[],favorite:false,added:Date.now(),modified,order:d.items.length,deletedAt:null};try{await fileCopy(src,path.join(root,stored));await backupOne({...d,items:[...d.items,item]},item);d.items.push(item);if(already&&entry.replaceDuplicate){already.deletedAt=Date.now();item.replaces=already.id}await save(d)}catch(e){results.push({name:item.name,status:'error',error:e.message});await fsp.rm(path.join(root,stored),{force:true});continue}try{await fsp.rm(src);results.push({name:item.name,status:'imported'})}catch(e){results.push({name:item.name,status:'imported-source-retained',error:'Media archived safely, but the original could not be removed: '+e.message})}}sender?.send('import-progress',{completed:arr.length,total:arr.length,percent:100,status:'Import completed'});return results}
async function updateItem(id,patch){const d=await load(),item=d.items.find(x=>x.id===id);if(!item)throw Error('Not found');const originalFolder=item.folder;const allowed=['favorite','order','folder','group','fandoms','deletedAt'];for(const k of allowed)if(Object.prototype.hasOwnProperty.call(patch,k))item[k]=patch[k];if(item.folder&&!d.folders.some(f=>f.id===item.folder&&f.kind===item.kind&&f.group===item.group))throw Error('Cannot move to a folder in another library');if(item.group==='fandom'&&item.fandoms?.some(id=>!d.folders.some(f=>f.id===id&&f.kind===item.kind&&f.group==='fandom')))throw Error('Invalid extra fandom folders');if(item.group==='nonfandom')item.fandoms=[];if(!['fandom','nonfandom'].includes(item.group))throw Error('Invalid collection');if(item.folder&&(item.folder!==originalFolder||patch.folder!==undefined)){const numbered=numberedMediaName(d,item.folder,path.extname(item.stored),item.id);if(numbered)item.name=numbered;}if(!item.deletedAt)await backupOne(d,item);await save(d);return d}
app.whenReady().then(async()=>{await fsp.mkdir(root,{recursive:true});if(!fs.existsSync(dbfile))await save(initial());await installApprovedFandomFolders();protocol.handle('replay',async req=>{
 const resource=new URL(req.url),id=decodeURIComponent(resource.pathname.slice(1));
 const d=await load();let file;
 if(resource.hostname==='converted'){file=compatibleVideoCache.get(id);if(!file)return new Response('Missing converted media',{status:404})}
 else{const item=d.items.find(x=>x.id===id&&!x.deletedAt);if(!item)return new Response('Missing media',{status:404});file=path.join(root,item.stored)}
 let stat;try{stat=await fsp.stat(file);if(!stat.isFile())throw Error('Not a file')}catch{return new Response('Missing media file',{status:404})}
 const total=stat.size,range=req.headers.get('range'),ext=path.extname(file).toLowerCase();
 const types={'.mp4':'video/mp4','.m4v':'video/mp4','.mov':'video/quicktime','.webm':'video/webm','.mkv':'video/x-matroska','.avi':'video/x-msvideo','.gif':'image/gif','.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg','.webp':'image/webp','.bmp':'image/bmp','.avif':'image/avif','.heic':'image/heic'};
 const headers={'Accept-Ranges':'bytes','Content-Type':types[ext]||'application/octet-stream','Cache-Control':'no-store'};
 let start=0,end=total-1,status=200;
 if(range){
  const match=/^bytes=(\d*)-(\d*)$/.exec(range.trim());
  if(!match||(!match[1]&&!match[2])||total===0){return new Response(null,{status:416,headers:{...headers,'Content-Range':'bytes */'+total}})}
  if(!match[1]){const suffix=Number(match[2]);if(!Number.isSafeInteger(suffix)||suffix<=0)return new Response(null,{status:416,headers:{...headers,'Content-Range':'bytes */'+total}});start=Math.max(0,total-suffix)}
  else{start=Number(match[1]);if(match[2])end=Number(match[2])}
  if(!Number.isSafeInteger(start)||!Number.isSafeInteger(end)||start>=total||end<start)return new Response(null,{status:416,headers:{...headers,'Content-Range':'bytes */'+total}});
  end=Math.min(end,total-1);status=206;headers['Content-Range']='bytes '+start+'-'+end+'/'+total;
 }
 headers['Content-Length']=String(Math.max(0,end-start+1));
 if(req.method==='HEAD'||total===0)return new Response(null,{status,headers});
 const stream=fs.createReadStream(file,{start,end});
 return new Response(require('node:stream').Readable.toWeb(stream),{status,headers});
});const win=new BrowserWindow({width:1320,height:850,minWidth:850,minHeight:560,backgroundColor:'#101014',webPreferences:{preload:path.join(__dirname,'preload.cjs'),contextIsolation:true,nodeIntegration:false}});win.loadFile(path.join(__dirname,'../src/index.html'))});
ipcMain.handle('open-media-window',async(_event,id)=>{const d=await load();const item=d.items.find(x=>x.id===id&&!x.deletedAt);if(!item)throw Error('Media not found');const pop=new BrowserWindow({width:960,height:720,minWidth:360,minHeight:260,backgroundColor:'#101014',title:'Replay — '+item.name,autoHideMenuBar:true,webPreferences:{preload:path.join(__dirname,'preload.cjs'),contextIsolation:true,nodeIntegration:false,backgroundThrottling:false}});await pop.loadFile(path.join(__dirname,'../src/media-window.html'),{query:{id:item.id}});return true});
ipcMain.handle('state',()=>load());
ipcMain.handle('browse',async()=>{const r=await dialog.showOpenDialog({properties:['openFile','multiSelections'],filters:[{name:'Media',extensions:['mp4','mov','mkv','webm','avi','gif','png','jpg','jpeg','webp','heic','bmp','tiff']}]});return r.canceled?[]:r.filePaths});
ipcMain.handle('browse-folder',async()=>{const r=await dialog.showOpenDialog({properties:['openDirectory']});if(r.canceled)return [];const found=[];async function crawl(dir){for(const ent of await fsp.readdir(dir,{withFileTypes:true})){const full=path.join(dir,ent.name);if(ent.isDirectory())await crawl(full);else if(ent.isFile()&&category(ent.name))found.push(full)}}await crawl(r.filePaths[0]);return found});

ipcMain.handle('import',(event,x)=>importFiles(x,event.sender));
ipcMain.handle('choose-folder-icon',async()=>{const r=await dialog.showOpenDialog({title:'Choose folder icon',properties:['openFile'],filters:[{name:'Images',extensions:['png','jpg','jpeg','webp','gif']} ]});if(r.canceled||!r.filePaths.length)return null;const p=r.filePaths[0],stat=await fsp.stat(p);if(stat.size>3*1024*1024)throw Error('Choose an image smaller than 3 MB');const ext=path.extname(p).toLowerCase();const mime=ext==='.png'?'image/png':ext==='.webp'?'image/webp':ext==='.gif'?'image/gif':'image/jpeg';return 'data:'+mime+';base64,'+(await fsp.readFile(p)).toString('base64')});
ipcMain.handle('open-ao3',async(_e,url)=>{const parsed=new URL(url);if(parsed.protocol!=='https:'||!['archiveofourown.org','www.archiveofourown.org'].includes(parsed.hostname))throw Error('Invalid AO3 link');await shell.openExternal(parsed.toString());return true});
ipcMain.handle('folder',async(_e,x)=>{const d=await load();const parent=x.parent&&d.folders.find(f=>f.id===x.parent&&f.kind===x.kind&&f.group===x.group);if(x.parent&&!parent)throw Error('Select a valid parent folder');const created={id:crypto.randomUUID(),kind:x.kind,group:x.group,name:safe(x.name),parent:parent?.id||'',isSubfolder:!!x.isSubfolder,showInfoCard:x.showInfoCard!==false,autoNumberMedia:x.autoNumberMedia!==false,details:{},cover:'',color:'#b58a48',order:d.folders.length};if(d.folders.some(f=>f.kind===x.kind&&f.group===x.group&&f.name.toLowerCase()===created.name.toLowerCase()&&(f.parent||'')===created.parent))throw Error('A folder with that name already exists here');d.folders.push(created);synchronizeFolderAppearance(d,created);await save(d);return d});
ipcMain.handle('folder-update',async(_e,id,patch)=>{const d=await load(),f=d.folders.find(x=>x.id===id);if(!f)throw Error('Not found');const peerCopies=matchingFolderCopies(d,f);if(patch.name!==undefined)f.name=safe(patch.name);if(patch.isSubfolder!==undefined)f.isSubfolder=!!patch.isSubfolder;if(patch.showInfoCard!==undefined)f.showInfoCard=!!patch.showInfoCard;const numberingWasEnabled=f.autoNumberMedia===true;if(patch.autoNumberMedia!==undefined)f.autoNumberMedia=!!patch.autoNumberMedia;if(f.autoNumberMedia&&(patch.numberExisting===true||patch.autoNumberMedia===true&&!numberingWasEnabled)){let n=1;const existing=d.items.filter(x=>!x.deletedAt&&x.folder===f.id&&x.kind===f.kind&&x.group===f.group).sort((a,b)=>(a.order||0)-(b.order||0)||(a.added||0)-(b.added||0));for(const item of existing){item.name=safe(f.name+' '+n++)}}if(patch.details!==undefined){const v=patch.details||{};const media=Array.isArray(v.sources)?v.sources.filter(x=>['Book','TV Show','Movie'].includes(x)):[];const category=['M/M','M/F','Platonic','No Relationship'].includes(v.category)?v.category:'';let ao3=String(v.ao3||'').trim();if(ao3){let parsed;try{parsed=new URL(ao3)}catch{throw Error('Enter a valid AO3 link')}if(parsed.protocol!=='https:'||!['archiveofourown.org','www.archiveofourown.org'].includes(parsed.hostname))throw Error('AO3 link must start with https://archiveofourown.org/')}f.details={pairings:String(v.pairings||'').slice(0,1200),shipName:String(v.shipName||'').slice(0,200),sources:media,category,ao3}};if(patch.pinned!==undefined)f.pinned=!!patch.pinned;if(Number.isInteger(patch.order)&&patch.order>=0)f.order=patch.order;if(/^#[0-9a-f]{6}$/i.test(patch.color||''))f.color=patch.color;if(patch.icon!==undefined)f.icon=String(patch.icon).slice(0,3);if(patch.iconImage!==undefined){if(patch.iconImage!==''&&!/^data:image\/(png|jpeg|webp|gif);base64,[a-z0-9+/=]+$/i.test(patch.iconImage))throw Error('Invalid folder icon image');if(patch.iconImage.length>4200000)throw Error('Folder icon is too large');f.iconImage=patch.iconImage}if(patch.cover!==undefined){if(patch.cover&&!d.items.some(i=>i.id===patch.cover&&i.kind==='images'&&!i.deletedAt))throw Error('Cover must be a stored image');f.cover=patch.cover}if(patch.parent!==undefined){if(patch.parent===id)throw Error('Folder cannot be parent of itself');const parent=patch.parent&&d.folders.find(x=>x.id===patch.parent);if(patch.parent&&(!parent||parent.kind!==f.kind||parent.group!==f.group))throw Error('Invalid parent');let current=parent;while(current){if(current.id===id)throw Error('Cannot move folder into its descendant');current=d.folders.find(x=>x.id===current.parent)}f.parent=patch.parent||''}for(const peer of peerCopies){if(peer===f)continue;const parent=f.parent&&d.folders.find(x=>x.id===f.parent);const counterpartParent=parent?ensureMatchingFolder(d,parent,peer.kind):null;peer.parent=counterpartParent?.id||'';copyFolderAppearance(f,peer)}synchronizeFolderAppearance(d,f);await save(d);queueFolderBackup();return d});
ipcMain.handle('item-update',async(_e,id,x)=>{const d=await updateItem(id,x);await synchronizeBackup();return d});
ipcMain.handle('item-delete',async(_e,id)=>{const d=await updateItem(id,{deletedAt:Date.now()});await synchronizeBackup();return d});
ipcMain.handle('restore',async(_e,id)=>{const d=await updateItem(id,{deletedAt:null});await synchronizeBackup();return d});
ipcMain.handle('settings',async(_e,x)=>{const d=await load();if(typeof x.backupRoot==='string'){const backup=path.resolve(x.backupRoot),archive=path.resolve(app.getPath('userData'));if(!path.isAbsolute(x.backupRoot)||backup===archive||backup.startsWith(archive+path.sep)||archive.startsWith(backup+path.sep))throw Error('Backups must be stored outside Replay application data');}Object.assign(d.settings,x);await save(d);if(x.backupRoot)await synchronizeBackup();return d});
ipcMain.handle('choose-backup',async()=>{const r=await dialog.showOpenDialog({properties:['openDirectory','createDirectory']});return r.canceled?'':r.filePaths[0]});
// Folder metadata is durable as soon as library.json is saved. Backup synchronization
// is serialized in the background, rather than blocking the Customize Folder form.
let folderBackupQueue=Promise.resolve();
function queueFolderBackup(){
 folderBackupQueue=folderBackupQueue.then(()=>synchronizeBackup()).catch(error=>{
  console.error('Replay folder backup synchronization failed:',error);
 });
}
async function synchronizeBackup(){
 const d=await load();
 const dest=d.settings.backupRoot||path.join(app.getPath('appData'),'VeyrStudio','ReplayBackup');
 const expected=new Set();
 for(const item of d.items.filter(i=>!i.deletedAt)){
  for(const id of item.group==='fandom'?[...new Set([item.folder,...(item.fandoms||[])])]:[item.folder]){const relative=path.join(item.kind,item.group==='fandom'?'Fandoms':'Non-Fandom',await folderPath(d,id),safe(item.name));if(expected.has(relative.toLowerCase()))throw Error('Backup filename collision: '+relative);expected.add(relative.toLowerCase())}
 }
 for(const item of d.items.filter(i=>!i.deletedAt))await backupOne(d,item);
 const recovery=path.join(dest,'.Replay Recovery');
 async function walk(dir,rel=''){let children=[];try{children=await fsp.readdir(dir,{withFileTypes:true})}catch(e){if(e.code==='ENOENT')return;throw e}
  for(const entry of children){if(entry.name==='.Replay Recovery'||entry.name==='replay-index.json'||entry.name.endsWith('.partial'))continue;const relative=path.join(rel,entry.name),full=path.join(dir,entry.name);if(entry.isDirectory())await walk(full,relative);else if(entry.isFile()&&!expected.has(relative.toLowerCase())){const stamped=path.join(recovery,String(Date.now()),relative);await fsp.mkdir(path.dirname(stamped),{recursive:true});await fsp.rename(full,stamped)}}
 }
 for(const kind of ['videos','images','gifs'])await walk(path.join(dest,kind),kind);
 let dates=[];try{dates=await fsp.readdir(recovery,{withFileTypes:true})}catch(e){if(e.code!=='ENOENT')throw e}
 for(const entry of dates)if(entry.isDirectory()&&/^\d+$/.test(entry.name)&&Date.now()-Number(entry.name)>30*86400000)await fsp.rm(path.join(recovery,entry.name),{recursive:true,force:true});
 return true;
}
ipcMain.handle('backup',()=>synchronizeBackup());
ipcMain.handle('empty-trash',async()=>{const d=await load(),cut=Date.now()-30*86400000;for(const item of d.items.filter(x=>x.deletedAt&&x.deletedAt<cut)){await fsp.rm(path.join(root,item.stored),{force:true})}d.items=d.items.filter(x=>!x.deletedAt||x.deletedAt>=cut);await save(d);return d});
ipcMain.handle('check-update',async()=>{const r=await fetch('https://raw.githubusercontent.com/VeyrStudio/DesktopAppUpdates/main/replay/replay.json');return r.ok?await r.json():null});

const {spawn}=require('node:child_process');
const {Readable}=require('node:stream');
const {pipeline}=require('node:stream/promises');
async function stageInstaller(manifest){
  if(!manifest || !/^https:\/\//.test(manifest.url)||!/^[a-f0-9]{64}$/i.test(manifest.sha256||'')) throw Error('Invalid update manifest');
  const response=await fetch(manifest.url,{cache:'no-store'});
  if(!response.ok||!response.body) throw Error('Installer download failed: '+response.status);
  const target=path.join(app.getPath('temp'),'ReplaySetup-'+String(manifest.version).replace(/[^a-z0-9.-]/ig,'_')+'.exe');
  const hash=crypto.createHash('sha256');
  const {Transform}=require('node:stream');
  await pipeline(Readable.fromWeb(response.body),new Transform({transform(chunk,enc,cb){hash.update(chunk);cb(null,chunk)}}),fs.createWriteStream(target));
  if(hash.digest('hex').toLowerCase()!==manifest.sha256.toLowerCase()){await fsp.rm(target,{force:true});throw Error('Installer checksum mismatch')}
  return target;
}
let readyInstaller='';
ipcMain.handle('stage-update',async(_e,manifest)=>{readyInstaller=await stageInstaller(manifest);return true});
ipcMain.handle('apply-update',async()=>{
 if(process.platform!=='win32'||!readyInstaller)throw Error('No verified Windows update ready');
 // A detached PowerShell helper survives Replay closing, waits for NSIS to
 // finish installing, then launches the updated executable only on success.
 const installedExe=process.execPath;
 const scriptPath=path.join(app.getPath('temp'),'replay-update-'+crypto.randomUUID()+'.ps1');
 const psQuote=value=>"'"+String(value).replace(/'/g,"''")+"'";
 const script=[
  '$ErrorActionPreference = "Stop"',
  '$installer = '+psQuote(readyInstaller),
  '$replayExe = '+psQuote(installedExe),
  'try {',
  '  Start-Sleep -Seconds 2',
  '  $process = Start-Process -FilePath $installer -ArgumentList "/S" -Wait -PassThru',
  '  if ($process.ExitCode -ne 0) { exit $process.ExitCode }',
  '  for ($i = 0; $i -lt 30 -and !(Test-Path -LiteralPath $replayExe); $i++) { Start-Sleep -Seconds 1 }',
  '  if (Test-Path -LiteralPath $replayExe) { Start-Process -FilePath $replayExe }',
  '} finally { Remove-Item -LiteralPath $PSCommandPath -Force -ErrorAction SilentlyContinue }'
 ].join('\n');
 await fsp.writeFile(scriptPath,script,'utf8');
 const child=spawn('powershell.exe',['-NoProfile','-NonInteractive','-WindowStyle','Hidden','-ExecutionPolicy','Bypass','-File',scriptPath],{detached:true,stdio:'ignore',windowsHide:true});
 child.unref();setImmediate(()=>app.quit());return true;
});
ipcMain.handle('version',()=>app.getVersion());

async function restoreFromBackup(selectedIds=[]){
 const d=await load(),target=d.settings.backupRoot||path.join(app.getPath('appData'),'VeyrStudio','ReplayBackup');
 const manifest=JSON.parse(await fsp.readFile(path.join(target,'replay-index.json'),'utf8'));
 if(!Array.isArray(manifest.items)||!Array.isArray(manifest.folders))throw Error('Invalid backup catalog');
 let restored=0;
 for(const item of manifest.items){
   if((item.deletedAt&&Date.now()-item.deletedAt>30*86400000) || (selectedIds.length&&!selectedIds.includes(item.id)) || d.items.some(x=>x.id===item.id))continue;
   if(!['videos','images','gifs'].includes(item.kind)||!item.name||!/^[a-f0-9]{64}$/i.test(item.hash||''))continue;
   const rel=String(item.stored||'');
   if(path.isAbsolute(rel)||rel.split(/[\\/]/).includes('..')||!rel.startsWith(item.kind+path.sep))continue;
   const chain=[];let f=manifest.folders.find(x=>x.id===item.folder);const seen=new Set();
   while(f&&!seen.has(f.id)){seen.add(f.id);chain.unshift(safe(f.name));f=manifest.folders.find(x=>x.id===f.parent)}
   const original=path.join(target,item.kind,item.group==='fandom'?'Fandoms':'Non-Fandom',...chain,safe(item.name));
   let source=original;
   try{await fsp.access(source)}catch{
     const recovery=path.join(target,'.Replay Recovery');let buckets=[];try{buckets=await fsp.readdir(recovery)}catch{}
     buckets=buckets.filter(x=>/^\d+$/.test(x)&&Date.now()-Number(x)<=30*86400000).sort((a,b)=>Number(b)-Number(a));
     for(const bucket of buckets){const candidate=path.join(recovery,bucket,item.kind,item.group==='fandom'?'Fandoms':'Non-Fandom',...chain,safe(item.name));try{await fsp.access(candidate);source=candidate;break}catch{}}
   }
   if((await checksum(source))!==item.hash)throw Error('Backup integrity failed for '+item.name);
   await fileCopy(source,path.join(root,rel));
   d.items.push({...item,deletedAt:null});restored++;
 }
 for(const f of manifest.folders)if(!d.folders.some(x=>x.id===f.id))d.folders.push(f);
 await save(d);return {restored};
}
ipcMain.handle('restore-backup',(_e,ids)=>restoreFromBackup(Array.isArray(ids)?ids:[]));
ipcMain.handle('list-backup',async()=>{const d=await load(),base=d.settings.backupRoot||path.join(app.getPath('appData'),'VeyrStudio','ReplayBackup');try{const meta=JSON.parse(await fsp.readFile(path.join(base,'replay-index.json'),'utf8'));return (meta.items||[]).map(item=>({...item,folderName:meta.folders?.find(f=>f.id===item.folder)?.name||'(Root)'}))}catch{return []}});

async function trashList(){const d=await load();return d.items.filter(x=>!!x.deletedAt)}
ipcMain.handle('list-trash',trashList);
async function purgeExpired(){const d=await load(),cutoff=Date.now()-30*86400000;let count=0;for(const item of d.items.filter(x=>x.deletedAt&&x.deletedAt<cutoff)){await fsp.rm(path.join(root,item.stored),{force:true});count++}if(count){d.items=d.items.filter(x=>!x.deletedAt||x.deletedAt>=cutoff);await save(d)}return count}
app.on('browser-window-created',()=>{purgeExpired().catch(e=>console.error('Trash cleanup failed:',e))});

const compatibleVideoCache=new Map(),transcodeJobs=new Map();
function ffmpegExecutable(){const platform=process.platform==='win32'?'ffmpeg.exe':'ffmpeg';const packaged=path.join(process.resourcesPath||'', 'ffmpeg',platform);const local=path.join(__dirname,'../node_modules/ffmpeg-static',platform);return fs.existsSync(packaged)?packaged:fs.existsSync(local)?local:null}
ipcMain.handle('compatible-video',async (_e,id)=>{
 const d=await load(),item=d.items.find(x=>x.id===id&&!x.deletedAt&&x.kind==='videos');
 if(!item)throw Error('Video not found');
 const existing=compatibleVideoCache.get(id);if(existing&&fs.existsSync(existing))return 'replay://converted/'+id;
 if(transcodeJobs.has(id))return transcodeJobs.get(id);
 const ffmpeg=ffmpegExecutable();if(!ffmpeg)throw Error('FFmpeg is not included in this build');
 const task=(async()=>{const dir=path.join(app.getPath('userData'),'Cache','Playback');await fsp.mkdir(dir,{recursive:true});const final=path.join(dir,id+'.mp4'),temp=final+'.partial.mp4';
 try{await new Promise((resolve,reject)=>{const proc=spawn(ffmpeg,['-hide_banner','-nostdin','-loglevel','error','-y','-i',path.join(root,item.stored),'-map','0:v:0','-map','0:a?','-c:v','libx264','-preset','veryfast','-pix_fmt','yuv420p','-c:a','aac','-movflags','+faststart',temp],{windowsHide:true});proc.on('error',reject);proc.on('exit',code=>code===0?resolve():reject(Error('Video conversion failed: '+code)))});await fsp.rename(temp,final);compatibleVideoCache.set(id,final);return 'replay://converted/'+id}
 finally{await fsp.rm(temp,{force:true}).catch(()=>{});transcodeJobs.delete(id)}
 })();transcodeJobs.set(id,task);return task;
});

ipcMain.handle('folder-delete',async(_e,id)=>{
 const d=await load(),target=d.folders.find(f=>f.id===id);
 if(!target)throw Error('Folder not found');
 for(const f of d.folders.filter(f=>f.parent===id))f.parent=target.parent||'';
 for(const item of d.items){
  if(item.folder===id)item.folder=target.parent||'';
  if(Array.isArray(item.fandoms))item.fandoms=item.fandoms.filter(x=>x!==id);
 }
 d.folders=d.folders.filter(f=>f.id!==id);
 await save(d);await synchronizeBackup();return d;
});
