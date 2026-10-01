const {contextBridge,ipcRenderer}=require('electron');
contextBridge.exposeInMainWorld('indexAPI',{
 read:()=>ipcRenderer.invoke('read'),save:data=>ipcRenderer.invoke('save',data),backup:()=>ipcRenderer.invoke('backup'),folder:()=>ipcRenderer.invoke('folder'),version:()=>ipcRenderer.invoke('version'),chooseImage:()=>ipcRenderer.invoke('choose-image'),checkUpdate:()=>ipcRenderer.invoke('check-update'),downloadUpdate:()=>ipcRenderer.invoke('download-update'),installUpdate:()=>ipcRenderer.invoke('install-update'),importData:()=>ipcRenderer.invoke('import-data'),exportData:()=>ipcRenderer.invoke('export-data'),onUpdate:callback=>ipcRenderer.on('update-status',(_ev,value)=>callback(value))
});
