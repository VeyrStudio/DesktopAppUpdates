const { app,BrowserWindow,ipcMain,dialog,shell }=require('electron');
const path=require('node:path');
const fs=require('node:fs');
const {createStore}=require('./store');
let mainWindow,store,updater;
function desktopFrameOptions(){if(process.platform!=='win32'||!store?.read().settings.customFrame)return {};return {titleBarStyle:'hidden',titleBarOverlay:{color:'#0a2e23',symbolColor:'#f7f0dd',height:34}};}
function dataFolder(){const fallback=path.join(app.getPath('userData'),'data');const config=path.join(app.getPath('userData'),'data-location.json');try{const candidate=JSON.parse(fs.readFileSync(config,'utf8')).path;if(typeof candidate==='string'&&path.isAbsolute(candidate)&&fs.existsSync(candidate))return candidate;}catch{}return fallback;}
function htmlEscape(v){return String(v??'').replace(/[&<>\"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}[c]));}
function setupUpdater(){
  const {createUpdater}=require('./updater');
  updater=createUpdater({app,notify:event=>mainWindow?.webContents.send('update-status',event),settings:()=>store.read().settings});
  if(app.isPackaged&&store.read().settings.autoUpdates)updater.check().catch(e=>console.error('Update check:',e.message));
}

app.whenReady().then(()=>{
  store=createStore(dataFolder());
  mainWindow=new BrowserWindow({width:1500,height:950,minWidth:1024,minHeight:650,backgroundColor:'#f8f5ed',...desktopFrameOptions(),icon:path.join(__dirname,'../assets/icon.png'),webPreferences:{preload:path.join(__dirname,'preload.js'),contextIsolation:true,nodeIntegration:false,sandbox:true}});
  mainWindow.loadFile(path.join(__dirname,'index.html'));
  setupUpdater();
  app.on('activate',()=>{if(BrowserWindow.getAllWindows().length===0){mainWindow=new BrowserWindow({width:1500,height:950,...desktopFrameOptions(),webPreferences:{preload:path.join(__dirname,'preload.js'),contextIsolation:true,nodeIntegration:false,sandbox:true}});mainWindow.loadFile(path.join(__dirname,'index.html'));}});
});
app.on('window-all-closed',()=>{if(process.platform!=='darwin')app.quit();});
ipcMain.handle('read',()=>store.read());
ipcMain.handle('save',(_ev,data)=>store.save(data));
ipcMain.handle('backup',()=>store.backup());
ipcMain.handle('folder',()=>shell.openPath(store.dir));
ipcMain.handle('version',()=>app.getVersion());
ipcMain.handle('choose-image',async()=>{const r=await dialog.showOpenDialog(mainWindow,{properties:['openFile'],filters:[{name:'Images',extensions:['png','jpg','jpeg','webp','gif']} ]});if(r.canceled)return null;const source=r.filePaths[0];const media=path.join(store.dir,'media');fs.mkdirSync(media,{recursive:true});const dest=path.join(media,Date.now()+'-'+path.basename(source).replace(/[^\w.-]/g,'_'));fs.copyFileSync(source,dest);const mime=dest.endsWith('.png')?'image/png':dest.endsWith('.webp')?'image/webp':dest.endsWith('.gif')?'image/gif':'image/jpeg';return 'data:'+mime+';base64,'+fs.readFileSync(dest).toString('base64');});
ipcMain.handle('check-update',async()=>updater.check());
ipcMain.handle('download-update',async()=>updater.download());
ipcMain.handle('install-update',()=>updater.install());
ipcMain.handle('import-data',async()=>{const r=await dialog.showOpenDialog(mainWindow,{filters:[{name:'JSON',extensions:['json']}],properties:['openFile']});if(r.canceled)return null;const d=JSON.parse(fs.readFileSync(r.filePaths[0],'utf8'));if(!Array.isArray(d.characters))throw Error('Not a valid The Index archive.');store.backup();return store.save(d);});
ipcMain.handle('export-data',async()=>{const r=await dialog.showSaveDialog(mainWindow,{defaultPath:'The-Index-backup.json',filters:[{name:'JSON',extensions:['json']}]});if(r.canceled)return null;fs.copyFileSync(store.filename,r.filePath);return r.filePath;});

ipcMain.handle('open-backups',async()=>{const folder=path.join(store.dir,'backups');fs.mkdirSync(folder,{recursive:true});return shell.openPath(folder)});
ipcMain.handle('change-data-folder',async()=>{
 const r=await dialog.showOpenDialog(mainWindow,{title:'Choose The Index data location',properties:['openDirectory','createDirectory']});if(r.canceled)return null;
 const target=path.join(r.filePaths[0],'The Index Data');
 if(path.resolve(target)===path.resolve(store.dir))return target;
 if(fs.existsSync(path.join(target,'archive.json')))throw Error('That location already has an archive. Choose another folder to avoid overwriting it.');
 fs.mkdirSync(target,{recursive:true});
 fs.cpSync(store.dir,target,{recursive:true,force:false,errorOnExist:true});
 if(!fs.existsSync(path.join(target,'archive.json')))throw Error('The archive could not be copied to the new folder.');
 const settingsPath=path.join(app.getPath('userData'),'data-location.json');
 fs.writeFileSync(settingsPath+'.tmp',JSON.stringify({path:target}));
 fs.renameSync(settingsPath+'.tmp',settingsPath);
 store=createStore(target);
 mainWindow.webContents.reload();
 return target;
});
ipcMain.handle('export-pdf',async(_event,request={})=>{
 const snapshot=store.read();
 const kind=String(request.type||'archive');
 const id=String(request.id||'');
 let heading='The Index Archive',sections=[];
 const block=(name,value)=>'<section><h2>'+htmlEscape(name)+'</h2><div>'+htmlEscape(typeof value==='string'?value:JSON.stringify(value,null,2)).replace(/\n/g,'<br>')+'</div></section>';
 const title=x=>htmlEscape(x.name||x.fields?.['Full Name']||'Untitled');
 if(kind==='character'){
   const record=snapshot.characters.find(x=>x.id===id);if(!record)throw Error('Character not found');
   heading=title(record);
   sections.push(block('Overview',record.fields?.['Full Name']||record.name||''));
   for(const [key,value] of Object.entries(record.fields||{}))sections.push(block(key,value));
   for(const [key,label] of [['relationships','Relationships'],['powers','Powers and Abilities'],['events','Timeline']]){
     for(const item of record[key]||[])sections.push(block(label, Object.entries(item).map(([k,v])=>k+': '+v).join('\n')));
   }
 }else if(kind==='note'){
   const record=snapshot.notes.find(x=>x.id===id);if(!record)throw Error('Note not found');
   heading=title(record);sections.push(block('Note',record.body||''));sections.push(block('Category',record.category||'General'));sections.push(block('Tags',record.tags||''));
 }else{
   for(const [key,label] of [['stories','Stories'],['characters','Characters'],['worldbuilding','Worldbuilding'],['notes','Notebook'],['tags','Tags']]){
     sections.push('<section><h2>'+label+'</h2>'+(snapshot[key]||[]).map(x=>'<p><b>'+title(x)+'</b> — '+htmlEscape((x.description||x.body||'').slice(0,200))+'</p>').join('')+'</section>');
   }
 }
 const html='<!doctype html><html><head><meta charset="utf-8"><style>@page{margin:18mm}body{font:12px Georgia,serif;color:#213b2d}header{border-bottom:3px solid #b89652;padding-bottom:12px}h1{font:28px Georgia,serif;margin:0}h2{font:16px Georgia,serif;color:#315442;margin-bottom:7px}section{page-break-inside:avoid;border-bottom:1px solid #ddd;padding:10px 0}div{line-height:1.5}p{line-height:1.5}</style></head><body><header><h1>'+heading+'</h1><small>THE INDEX • CHARACTER ARCHIVE</small></header>'+sections.join('')+'</body></html>';
 const result=await dialog.showSaveDialog(mainWindow,{defaultPath:'The-Index-'+kind+'.pdf',filters:[{name:'PDF',extensions:['pdf']}]});if(result.canceled)return null;
 const window=new BrowserWindow({show:false,webPreferences:{sandbox:true,nodeIntegration:false,contextIsolation:true}});
 try{await window.loadURL('data:text/html;charset=utf-8,'+encodeURIComponent(html));const pdf=await window.webContents.printToPDF({printBackground:true,pageSize:'A4'});fs.writeFileSync(result.filePath,pdf);return result.filePath;}finally{window.destroy();}
});

ipcMain.handle('restart-app',async()=>{app.relaunch();app.quit();return true});
