const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const ui=fs.readFileSync(path.join(__dirname,'../src/app.js'),'utf8');
const main=fs.readFileSync(path.join(__dirname,'../electron/main.cjs'),'utf8');
test('Replay scripts parse',()=>{new vm.Script(ui);new vm.Script(main)});
test('normal clicks toggle additional items while multi-selection is active',()=>{
 assert.match(ui,/else if\(selectedMedia\.size\)\{if\(selectedMedia\.has\(id\)\)selectedMedia\.delete\(id\);else selectedMedia\.add\(id\)/);
});
test('move dialog offers direct clickable destination buttons instead of a native select',()=>{
 const start=ui.indexOf('function moveMediaPicker('),end=ui.indexOf('async function importFolderPicker(',start),picker=ui.slice(start,end);
 assert.match(picker,/button\.onclick=\(\)=>\{const target=folders\.find/);
 assert.match(picker,/destinations\.append\(button\)/);
 assert.doesNotMatch(picker,/createElement\('select'\)/);
});
test('dragging near either edge scrolls the gallery and document',()=>{
 assert.match(ui,/function replayDragAutoScroll\(event\)/);
 assert.match(ui,/window\.scrollBy\(0,direction\*speed\)/);
 assert.match(ui,/replayDragAutoScroll\(event\);/);
});
test('stale conflicting backup file is preserved in recovery instead of rejecting media move',()=>{
 assert.match(main,/if\(existing!==item\.hash\)\{/);
 assert.match(main,/await fsp\.rename\(destination,keep\)/);
 assert.doesNotMatch(main,/if\(existing!==item\.hash\)throw Error\('Backup filename collision/);
 assert.match(main,/ipcMain\.handle\('item-update',[\s\S]*?queueFolderBackup\(\);return d/);
});
