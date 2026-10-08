const {app,BrowserWindow,dialog,ipcMain,protocol,net}=require('electron');
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
const sectionName={videos:'Videos',images:'Images',gifs:'GIFs'};
function assignmentIds(item){return [...new Set((item.folderIds?.length?item.folderIds:[item.folder]).filter(Boolean))]}
function validateAssignments(d,kind,ids,group){const folders=ids.map(id=>d.folders.find(f=>f.id===id));if(folders.some(f=>!f||f.kind!==kind||f.group!==group))throw Error('Folder does not belong to this media library');if(group==='nonfandom'&&ids.length>1)throw Error('Choose one non-fandom folder only')}
function backupPaths(d,item){const ids=assignmentIds(item),folders=ids.length?ids.map(id=>d.folders.find(f=>f.id===id)).filter(Boolean):[null];return Promise.all(folders.map(async f=>{const dir=path.join(d.settings.backupRoot||path.join(app.getPath('appData'),'VeyrStudio','ReplayBackup'),sectionName[item.kind],item.group==='fandom'?'Fandoms':'Non-Fandom',f?await folderPath(d,f.id):'Uncategorized');return path.join(dir,safe(item.name))}))}
async function writeBackupIndex(d){const target=d.settings.backupRoot||path.join(app.getPath('appData'),'VeyrStudio','ReplayBackup');await fsp.mkdir(target,{recursive:true});const temp=path.join(target,'replay-index.json.partial');await fsp.writeFile(temp,JSON.stringify(d,null,2));await fsp.rename(temp,path.join(target,'replay-index.json'))}
async function backupOne(d,item){for(const destination of await backupPaths(d,item))await fileCopy(path.join(root,item.stored),destination);await writeBackupIndex(d)}
async function backupAll(d){for(const item of d.items.filter(i=>!i.deletedAt))await backupOne(d,item);await writeBackupIndex(d)}
async function importFiles(arr,sender){const d=await load(),results=[];let completed=0;for(const entry of arr){completed++;sender?.send('import-progress',{completed,total:arr.length,percent:Math.round(completed/arr.length*100),status:'Importing '+path.basename(entry.path)});const src=entry.path,kind=category(src);if(!kind){results.push({name:path.basename(src),status:'unsupported'});continue}const hash=await checksum(src),already=d.items.find(x=>!x.deletedAt&&x.hash===hash);if(already&&!entry.keepDuplicate){results.push({name:path.basename(src),status:'duplicate',existing:already.id});continue}const assigned=[...new Set((entry.folderIds||[entry.folder]).filter(Boolean))];const selectedGroup=entry.group==='fandom'?'fandom':'nonfandom';try{validateAssignments(d,kind,assigned,selectedGroup)}catch(e){results.push({name:path.basename(src),status:'error',error:e.message});continue}const id=crypto.randomUUID(),ext=path.extname(src),stored=path.join(kind,id+ext),item={id,name:path.basename(src),kind,stored,hash,folder:assigned[0]||'',folderIds:assigned,group:selectedGroup,favorite:false,added:Date.now(),order:d.items.length,deletedAt:null};try{await fileCopy(src,path.join(root,stored));await backupOne({...d,items:[...d.items,item]},item);d.items.push(item);await save(d)}catch(e){results.push({name:item.name,status:'error',error:e.message});await fsp.rm(path.join(root,stored),{force:true});continue}try{await fsp.rm(src);results.push({name:item.name,status:'imported'})}catch(e){results.push({name:item.name,status:'imported-source-retained',error:'Media archived safely, but the original could not be removed: '+e.message})}}sender?.send('import-progress',{completed:arr.length,total:arr.length,percent:100,status:'Import completed'});return results}
async function updateItem(id,patch){const d=await load(),item=d.items.find(x=>x.id===id);if(!item)throw Error('Not found');if(patch.folderIds){const ids=[...new Set(patch.folderIds)];validateAssignments(d,item.kind,ids,patch.group||item.group);patch.folder=ids[0]||''}Object.assign(item,patch);await save(d);if(!item.deletedAt)await backupOne(d,item);else await writeBackupIndex(d);return d}
app.whenReady().then(async()=>{await fsp.mkdir(root,{recursive:true});if(!fs.existsSync(dbfile))await save(initial());protocol.handle('replay',req=>{const id=decodeURIComponent(new URL(req.url).pathname.replace(/^\//,''));return load().then(d=>{const item=d.items.find(x=>x.id===id);if(!item)throw Error('Missing media');return net.fetch(pathToFileURL(path.join(root,item.stored)).toString())})});const win=new BrowserWindow({width:1320,height:850,minWidth:850,minHeight:560,backgroundColor:'#101014',webPreferences:{preload:path.join(__dirname,'preload.cjs'),contextIsolation:true,nodeIntegration:false}});win.loadFile(path.join(__dirname,'../src/index.html'))});
ipcMain.handle('state',()=>load());
ipcMain.handle('browse',async()=>{const r=await dialog.showOpenDialog({properties:['openFile','multiSelections'],filters:[{name:'Media',extensions:['mp4','mov','mkv','webm','avi','gif','png','jpg','jpeg','webp','heic','bmp','tiff']}]});return r.canceled?[]:r.filePaths});
ipcMain.handle('import',(event,x)=>importFiles(x,event.sender));
ipcMain.handle('folder',async(_e,x)=>{const d=await load();const parent=d.folders.find(f=>f.id===x.parent);if(x.parent&&(!parent||parent.kind!==x.kind||parent.group!==x.group))throw Error('Invalid parent folder');d.folders.push({id:crypto.randomUUID(),kind:x.kind,group:x.group,name:safe(x.name),parent:x.parent||'',cover:'',color:'#b58a48',icon:'▤',pinned:false});await save(d);await writeBackupIndex(d);return d});
ipcMain.handle('folder-update',async(_e,id,patch)=>{const d=await load(),f=d.folders.find(x=>x.id===id);if(!f)throw Error('Not found');if(patch.name!==undefined)patch.name=safe(patch.name);Object.assign(f,patch);await save(d);await backupAll(d);return d});
ipcMain.handle('item-update',(_e,id,x)=>updateItem(id,x));
ipcMain.handle('item-delete',(_e,id)=>updateItem(id,{deletedAt:Date.now()}));
ipcMain.handle('restore',(_e,id)=>updateItem(id,{deletedAt:null}));
ipcMain.handle('settings',async(_e,x)=>{const d=await load();Object.assign(d.settings,x);await save(d);return d});
ipcMain.handle('choose-backup',async()=>{const r=await dialog.showOpenDialog({properties:['openDirectory','createDirectory']});return r.canceled?'':r.filePaths[0]});
ipcMain.handle('backup',async()=>{const d=await load();await backupAll(d);return true});
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

ipcMain.handle('browse-folder',async()=>{const r=await dialog.showOpenDialog({properties:['openDirectory']});return r.canceled?'':r.filePaths[0]});
ipcMain.handle('scan-folder',async(_e,dir)=>{const paths=[];async function walk(p,depth){if(depth>20||paths.length>20000)return;for(const entry of await fsp.readdir(p,{withFileTypes:true})){const target=path.join(p,entry.name);if(entry.isDirectory())await walk(target,depth+1);else if(entry.isFile()&&category(target))paths.push(target)}}await walk(dir,0);return paths});
ipcMain.handle('restore-backup',async(_e,selected)=>{const d=await load();const base=d.settings.backupRoot;const external=JSON.parse(await fsp.readFile(path.join(base,'replay-index.json'),'utf8'));if(!Array.isArray(external.items)||!Array.isArray(external.folders))throw Error('Invalid backup index');let restored=0;const wanted=selected?.length?external.items.filter(i=>selected.includes(i.id)):external.items.filter(i=>!i.deletedAt);for(const item of wanted){if(!sectionName[item.kind]||!/^[a-f0-9-]{36}$/i.test(item.id)||!/^[a-f0-9]{64}$/i.test(item.hash))continue;if(d.items.some(x=>x.id===item.id&&fs.existsSync(path.join(root,x.stored))))continue;const candidatePaths=await backupPaths(external,item);let src='';for(const candidate of candidatePaths){if(fs.existsSync(candidate)&&await checksum(candidate)===item.hash){src=candidate;break}}if(!src)continue;const destination=path.join(root,item.stored);await fileCopy(src,destination);d.items=d.items.filter(x=>x.id!==item.id);d.items.push({...item,deletedAt:null});restored++}for(const f of external.folders)if(!d.folders.some(x=>x.id===f.id))d.folders.push(f);await save(d);return {restored}});
ipcMain.handle('inspect-backup',async()=>{const d=await load();const f=path.join(d.settings.backupRoot,'replay-index.json');try{const b=JSON.parse(await fsp.readFile(f,'utf8'));return {count:b.items?.length||0,items:b.items||[]}}catch{return {count:0,items:[]}}});
ipcMain.handle('empty-trash-now',async()=>{const d=await load();for(const item of d.items.filter(i=>i.deletedAt))await fsp.rm(path.join(root,item.stored),{force:true});d.items=d.items.filter(i=>!i.deletedAt);await save(d);await writeBackupIndex(d);return d});
