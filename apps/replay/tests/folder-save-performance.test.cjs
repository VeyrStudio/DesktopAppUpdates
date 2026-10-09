const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const main=fs.readFileSync(path.join(__dirname,'../electron/main.cjs'),'utf8');
test('Replay main process parses',()=>new vm.Script(main));
test('folder update persists first and queues rather than awaits backup synchronization',()=>{
 const start=main.indexOf("ipcMain.handle('folder-update'");
 const end=main.indexOf("ipcMain.handle('item-update'",start);
 const handler=main.slice(start,end);
 assert.ok(handler.includes('await save(d);queueFolderBackup();return d'));
 assert.ok(!handler.includes('await synchronizeBackup()'));
});
test('folder backups are serialized with explicit error reporting',()=>{
 assert.match(main,/let folderBackupQueue=Promise\.resolve\(\)/);
 assert.match(main,/folderBackupQueue=folderBackupQueue\.then\(\(\)=>synchronizeBackup\(\)\)\.catch/);
 assert.match(main,/Replay folder backup synchronization failed:/);
});
