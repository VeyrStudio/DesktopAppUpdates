/* Small, isolated bridge between The Index UI and its Tauri native commands. */
(()=>{
const native=window.__TAURI__?.core?.invoke;
if(!native){document.addEventListener('DOMContentLoaded',()=>{document.getElementById('screen').textContent='The Index must be launched from its Windows desktop installer.'});return;}
let downloaded=null;
const call=(cmd,args)=>native(cmd,args||{});
window.indexAPI={
 read:()=>call('read_archive'),
 save:data=>call('save_archive',{data}),
 backup:()=>call('backup_archive'),
 folder:()=>call('data_folder'),
 openBackups:()=>call('open_backups'),
 chooseImage:()=>call('choose_image'),
 importData:()=>call('import_archive'),
 exportData:()=>call('export_archive'),
 changeDataFolder:()=>call('change_folder'),
 version:()=>call('version'),
 checkUpdate:()=>call('check_update'),
 downloadUpdate:async()=>{const data=await call('download_update');downloaded=data.path;return data;},
 installUpdate:async()=>{if(!downloaded)throw Error('Download and verify an update first');const result=await call('install_update',{path:downloaded});window.close();return result},
 onUpdate:()=>{},
 exportPDF:async({type,id}={})=>{window.print();return null},
 restartApp:async()=>window.location.reload()
};
window.addEventListener('error',e=>{const el=document.getElementById('toast');if(el){el.textContent='The Index encountered an error: '+e.message;el.style.display='block';}console.error(e.error||e.message)});
window.addEventListener('unhandledrejection',e=>{const el=document.getElementById('toast');if(el){el.textContent='Action failed: '+(e.reason?.message||String(e.reason));el.style.display='block';}console.error(e.reason)});
})();