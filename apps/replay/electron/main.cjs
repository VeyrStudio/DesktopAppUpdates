const {app,BrowserWindow,dialog,ipcMain,protocol,net,shell}=require('electron');
const fs=require('node:fs'), fsp=require('node:fs/promises'), path=require('node:path'),crypto=require('node:crypto');
const {pathToFileURL}=require('node:url');
protocol.registerSchemesAsPrivileged([{scheme:'replay',privileges:{standard:true,secure:true,stream:true,supportFetchAPI:true}}]);
app.setPath('userData',path.join(app.getPath('appData'),'VeyrStudio','Replay'));
const root=path.join(app.getPath('userData'),'Media'), dbfile=path.join(app.getPath('userData'),'library.json');
const initial=()=>({folders:['videos','images','gifs'].flatMap(kind=>['Dog Photos','Family','Other'].map(name=>({id:crypto.randomUUID(),kind,group:'nonfandom',name,parent:'',color:'#b58a48',pinned:false,cover:''}))),items:[],settings:{backupRoot:path.join(app.getPath('appData'),'VeyrStudio','ReplayBackup'),thumbnailSize:170,launch:'dashboard'},favorites:[]});
async function load(){try{return {...initial(),...JSON.parse(await fsp.readFile(dbfile,'utf8'))}}catch{return initial()}}
async function save(d){await fsp.mkdir(path.dirname(dbfile),{recursive:true});const tmp=dbfile+'.tmp';await fsp.writeFile(tmp,JSON.stringify(d,null,2));await fsp.rename(tmp,dbfile)}
const checksum=async p=>new Promise((resolve,reject)=>{const h=crypto.createHash('sha256');fs.createReadStream(p).on('data',b=>h.update(b)).on('error',reject).on('end',()=>resolve(h.digest('hex')))});
const category=f=>/\.gif$/i.test(f)?'gifs':/\.(mp4|mov|mkv|avi|webm|m4v|wmv|flv|ts)$/i.test(f)?'videos':/\.(jpg|jpeg|png|webp|bmp|heic|tif|tiff|avif)$/i.test(f)?'images':null;
async function fileCopy(src,dst){await fsp.mkdir(path.dirname(dst),{recursive:true});const tmp=dst+'.partial';await fsp.copyFile(src,tmp);if((await checksum(src))!== (await checksum(tmp))){await fsp.rm(tmp,{force:true});throw Error('Copy failed verification')}await fsp.rename(tmp,dst)}
function safe(s){return String(s).replace(/[<>:"/\\|?*\x00-\x1f]/g,'_').slice(0,90)||'Unnamed'}
async function folderPath(d,id){let f=d.folders.find(x=>x.id===id);const names=[],visited=new Set();while(f&&!visited.has(f.id)){visited.add(f.id);names.unshift(safe(f.name));f=d.folders.find(x=>x.id===f.parent)}return names.join(path.sep)}
async function backupOne(d,item){const target=d.settings.backupRoot||path.join(app.getPath('appData'),'VeyrStudio','ReplayBackup');const folders=item.group==='fandom'?[...new Set([item.folder,...(item.fandoms||[])])]:[item.folder];for(const id of folders){if(id&&!d.folders.some(f=>f.id===id&&f.kind===item.kind&&f.group===item.group))continue;const folder=await folderPath(d,id);const dir=path.join(target,item.kind,item.group==='fandom'?'Fandoms':'Non-Fandom',folder);const destination=path.join(dir,safe(item.name));try{const existing=await checksum(destination);if(existing!==item.hash)throw Error('Backup filename collision: '+item.name)}catch(error){if(error.code!=='ENOENT')throw error;await fileCopy(path.join(root,item.stored),destination)}}await fsp.mkdir(target,{recursive:true});const tmp=path.join(target,'replay-index.json.partial');await fsp.writeFile(tmp,JSON.stringify(d,null,2));await fsp.rename(tmp,path.join(target,'replay-index.json'))}
async function importFiles(arr,sender){const d=await load(),results=[];let completed=0;for(const entry of arr){completed++;sender?.send('import-progress',{completed,total:arr.length,percent:Math.round(completed/arr.length*100),status:'Importing '+path.basename(entry.path)});const src=entry.path,kind=category(src);const sourceAbsolute=path.resolve(src),archiveAbsolute=path.resolve(root);if(sourceAbsolute.startsWith(archiveAbsolute+path.sep)){results.push({name:path.basename(src),status:'error',error:'Cannot import managed archive files'});continue}if(!kind){results.push({name:path.basename(src),status:'unsupported'});continue}const hash=await checksum(src),already=d.items.find(x=>!x.deletedAt&&x.hash===hash);if(already&&!entry.keepDuplicate){results.push({name:path.basename(src),status:'duplicate',existing:already.id});continue}const modified=(await fsp.stat(src)).mtimeMs;const requestedFolder=d.folders.find(f=>f.id===entry.folder&&f.kind===kind);const id=crypto.randomUUID(),ext=path.extname(src),stored=path.join(kind,id+ext);let chosenName=path.basename(src);let index=2;while(d.items.some(x=>!x.deletedAt&&x.kind===kind&&x.group===(entry.group==='fandom'?'fandom':'nonfandom')&&x.folder===(requestedFolder?.id||'')&&x.name.toLowerCase()===chosenName.toLowerCase())){chosenName=path.parse(src).name+' ('+index+++')'+ext}const item={id,name:chosenName,kind,stored,hash,folder:requestedFolder?requestedFolder.id:'',group:entry.group==='fandom'?'fandom':'nonfandom',fandoms:entry.fandoms||[],favorite:false,added:Date.now(),modified,order:d.items.length,deletedAt:null};try{await fileCopy(src,path.join(root,stored));await backupOne({...d,items:[...d.items,item]},item);d.items.push(item);await save(d)}catch(e){results.push({name:item.name,status:'error',error:e.message});await fsp.rm(path.join(root,stored),{force:true});continue}try{await fsp.rm(src);results.push({name:item.name,status:'imported'})}catch(e){results.push({name:item.name,status:'imported-source-retained',error:'Media archived safely, but the original could not be removed: '+e.message})}}sender?.send('import-progress',{completed:arr.length,total:arr.length,percent:100,status:'Import completed'});return results}
async function updateItem(id,patch){const d=await load(),item=d.items.find(x=>x.id===id);if(!item)throw Error('Not found');const allowed=['favorite','order','folder','group','fandoms','deletedAt'];for(const k of allowed)if(Object.prototype.hasOwnProperty.call(patch,k))item[k]=patch[k];if(item.folder&&!d.folders.some(f=>f.id===item.folder&&f.kind===item.kind&&f.group===item.group))throw Error('Cannot move to a folder in another library');if(item.group==='fandom'&&item.fandoms?.some(id=>!d.folders.some(f=>f.id===id&&f.kind===item.kind&&f.group==='fandom')))throw Error('Invalid extra fandom folders');if(item.group==='nonfandom')item.fandoms=[];if(!['fandom','nonfandom'].includes(item.group))throw Error('Invalid collection');if(!item.deletedAt)await backupOne(d,item);await save(d);return d}
app.whenReady().then(async()=>{await fsp.mkdir(root,{recursive:true});if(!fs.existsSync(dbfile))await save(initial());protocol.handle('replay',req=>{const id=decodeURIComponent(new URL(req.url).pathname.replace(/^\//,''));return load().then(d=>{if(new URL(req.url).hostname==='converted'){const file=compatibleVideoCache.get(id);if(!file)throw Error('Missing converted media');return net.fetch(pathToFileURL(file).toString())}const item=d.items.find(x=>x.id===id);if(!item)throw Error('Missing media');return net.fetch(pathToFileURL(path.join(root,item.stored)).toString())})});const win=new BrowserWindow({width:1320,height:850,minWidth:850,minHeight:560,backgroundColor:'#101014',webPreferences:{preload:path.join(__dirname,'preload.cjs'),contextIsolation:true,nodeIntegration:false}});win.loadFile(path.join(__dirname,'../src/index.html'))});
ipcMain.handle('open-media-window',async(_event,id)=>{const d=await load();const item=d.items.find(x=>x.id===id&&!x.deletedAt);if(!item)throw Error('Media not found');const pop=new BrowserWindow({width:960,height:720,minWidth:360,minHeight:260,backgroundColor:'#101014',title:'Replay — '+item.name,autoHideMenuBar:true,webPreferences:{preload:path.join(__dirname,'preload.cjs'),contextIsolation:true,nodeIntegration:false}});await pop.loadFile(path.join(__dirname,'../src/media-window.html'),{query:{id:item.id}});return true});
ipcMain.handle('state',()=>load());
ipcMain.handle('browse',async()=>{const r=await dialog.showOpenDialog({properties:['openFile','multiSelections'],filters:[{name:'Media',extensions:['mp4','mov','mkv','webm','avi','gif','png','jpg','jpeg','webp','heic','bmp','tiff']}]});return r.canceled?[]:r.filePaths});
ipcMain.handle('browse-folder',async()=>{const r=await dialog.showOpenDialog({properties:['openDirectory']});if(r.canceled)return [];const found=[];async function crawl(dir){for(const ent of await fsp.readdir(dir,{withFileTypes:true})){const full=path.join(dir,ent.name);if(ent.isDirectory())await crawl(full);else if(ent.isFile()&&category(ent.name))found.push(full)}}await crawl(r.filePaths[0]);return found});

ipcMain.handle('import',(event,x)=>importFiles(x,event.sender));
ipcMain.handle('choose-folder-icon',async()=>{const r=await dialog.showOpenDialog({title:'Choose folder icon',properties:['openFile'],filters:[{name:'Images',extensions:['png','jpg','jpeg','webp','gif']} ]});if(r.canceled||!r.filePaths.length)return null;const p=r.filePaths[0],stat=await fsp.stat(p);if(stat.size>3*1024*1024)throw Error('Choose an image smaller than 3 MB');const ext=path.extname(p).toLowerCase();const mime=ext==='.png'?'image/png':ext==='.webp'?'image/webp':ext==='.gif'?'image/gif':'image/jpeg';return 'data:'+mime+';base64,'+(await fsp.readFile(p)).toString('base64')});
ipcMain.handle('open-ao3',async(_e,url)=>{const parsed=new URL(url);if(parsed.protocol!=='https:'||!['archiveofourown.org','www.archiveofourown.org'].includes(parsed.hostname))throw Error('Invalid AO3 link');await shell.openExternal(parsed.toString());return true});
ipcMain.handle('folder',async(_e,x)=>{const d=await load();const parent=x.parent&&d.folders.find(f=>f.id===x.parent&&f.kind===x.kind&&f.group===x.group);if(x.parent&&!parent)throw Error('Select a valid parent folder');d.folders.push({id:crypto.randomUUID(),kind:x.kind,group:x.group,name:safe(x.name),parent:parent?.id||'',isSubfolder:!!x.isSubfolder,details:{},cover:'',color:'#b58a48',order:d.folders.length});await save(d);return d});
ipcMain.handle('folder-update',async(_e,id,patch)=>{const d=await load(),f=d.folders.find(x=>x.id===id);if(!f)throw Error('Not found');if(patch.name!==undefined)f.name=safe(patch.name);if(patch.isSubfolder!==undefined)f.isSubfolder=!!patch.isSubfolder;if(patch.details!==undefined){const v=patch.details||{};const media=Array.isArray(v.sources)?v.sources.filter(x=>['Book','TV Show','Movie'].includes(x)):[];const category=['M/M','M/F','Platonic','No Relationship'].includes(v.category)?v.category:'';let ao3=String(v.ao3||'').trim();if(ao3){let parsed;try{parsed=new URL(ao3)}catch{throw Error('Enter a valid AO3 link')}if(parsed.protocol!=='https:'||!['archiveofourown.org','www.archiveofourown.org'].includes(parsed.hostname))throw Error('AO3 link must start with https://archiveofourown.org/')}f.details={pairings:String(v.pairings||'').slice(0,1200),sources:media,category,ao3}};if(patch.pinned!==undefined)f.pinned=!!patch.pinned;if(Number.isInteger(patch.order)&&patch.order>=0)f.order=patch.order;if(/^#[0-9a-f]{6}$/i.test(patch.color||''))f.color=patch.color;if(patch.icon!==undefined)f.icon=String(patch.icon).slice(0,3);if(patch.iconImage!==undefined){if(patch.iconImage!==''&&!/^data:image\/(png|jpeg|webp|gif);base64,[a-z0-9+/=]+$/i.test(patch.iconImage))throw Error('Invalid folder icon image');if(patch.iconImage.length>4200000)throw Error('Folder icon is too large');f.iconImage=patch.iconImage}if(patch.cover!==undefined){if(patch.cover&&!d.items.some(i=>i.id===patch.cover&&i.kind==='images'&&!i.deletedAt))throw Error('Cover must be a stored image');f.cover=patch.cover}if(patch.parent!==undefined){if(patch.parent===id)throw Error('Folder cannot be parent of itself');const parent=patch.parent&&d.folders.find(x=>x.id===patch.parent);if(patch.parent&&(!parent||parent.kind!==f.kind||parent.group!==f.group))throw Error('Invalid parent');let current=parent;while(current){if(current.id===id)throw Error('Cannot move folder into its descendant');current=d.folders.find(x=>x.id===current.parent)}f.parent=patch.parent||''}await save(d);await synchronizeBackup();return d});
ipcMain.handle('item-update',async(_e,id,x)=>{const d=await updateItem(id,x);await synchronizeBackup();return d});
ipcMain.handle('item-delete',async(_e,id)=>{const d=await updateItem(id,{deletedAt:Date.now()});await synchronizeBackup();return d});
ipcMain.handle('restore',async(_e,id)=>{const d=await updateItem(id,{deletedAt:null});await synchronizeBackup();return d});
ipcMain.handle('settings',async(_e,x)=>{const d=await load();if(typeof x.backupRoot==='string'){const backup=path.resolve(x.backupRoot),archive=path.resolve(app.getPath('userData'));if(!path.isAbsolute(x.backupRoot)||backup===archive||backup.startsWith(archive+path.sep)||archive.startsWith(backup+path.sep))throw Error('Backups must be stored outside Replay application data');}Object.assign(d.settings,x);await save(d);if(x.backupRoot)await synchronizeBackup();return d});
ipcMain.handle('choose-backup',async()=>{const r=await dialog.showOpenDialog({properties:['openDirectory','createDirectory']});return r.canceled?'':r.filePaths[0]});
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
ipcMain.handle('apply-update',async()=>{if(process.platform!=='win32'||!readyInstaller)throw Error('No verified Windows update ready');const child=spawn(readyInstaller,['/S'],{detached:true,stdio:'ignore'});child.unref();setImmediate(()=>app.quit());return true});
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
