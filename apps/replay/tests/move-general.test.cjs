const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const ui=fs.readFileSync(path.join(__dirname,'../src/app.js'),'utf8');
test('Replay renderer parses',()=>new vm.Script(ui));
test('existing media can move into General or any subfolder',()=>{
 assert.match(ui,/function moveMediaPicker\(item,folders\)/);
 assert.match(ui,/groupName\+':'/);
 assert.match(ui,/General/);
 assert.match(ui,/chain\.join\(' \/ '\)/);
 assert.match(ui,/folder:destination\.folder,group:destination\.group/);
});
test('moving can be cancelled without changing an item',()=>{
 assert.match(ui,/cancel\.onclick=\(\)=>\{overlay\.remove\(\);resolve\(null\)\}/);
 assert.match(ui,/if\(destination\)await replay\.itemUpdate/);
});
