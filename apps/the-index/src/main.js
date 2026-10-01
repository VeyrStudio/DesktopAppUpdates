const { app,BrowserWindow,ipcMain,dialog,shell }=require('electron');
const path=require('node:path');
const fs=require('node:fs');
const {createStore}=require('./store');
let mainWindow,store,updater;
function setupUpdater(){
  const {createUpdater}=require('./updater');
  updater=createUpdater({app,notify:event=>mainWindow?.webContents.send('update-status',event),settings:()=>store.read().settings});
  if(app.isPackaged&&store.read().settings.autoUpdates)updater.check().catch(e=>console.error('Update check:',e.message));
}

app.whenReady().then(()=>{
  store=createStore(path.join(app.getPath('userData'),'data'));
  mainWindow=new BrowserWindow({width:1500,height:950,minWidth:1024,minHeight:650,backgroundColor:'#f8f5ed',icon:path.join(__dirname,'../assets/icon.png'),webPreferences:{preload:path.join(__dirname,'preload.js'),contextIsolation:true,nodeIntegration:false,sandbox:true}});
  mainWindow.loadFile(path.join(__dirname,'index.html'));
  setupUpdater();
  app.on('activate',()=>{if(BrowserWindow.getAllWindows().length===0){mainWindow=new BrowserWindow({width:1500,height:950,webPreferences:{preload:path.join(__dirname,'preload.js'),contextIsolation:true,nodeIntegration:false,sandbox:true}});mainWindow.loadFile(path.join(__dirname,'index.html'));}});
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
