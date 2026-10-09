const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const ui=fs.readFileSync(path.join(__dirname,'../src/app.js'),'utf8');
test('Replay renderer parses',()=>new vm.Script(ui));
test('internal Move picker shows immediate parent and siblings or children only',()=>{
 assert.match(ui,/function moveMediaPicker\(item,folders\)/);
 assert.match(ui,/const parentId=current/);
 assert.match(ui,/const nearby=folders\.filter/);
 assert.match(ui,/const children=current\?folders\.filter/);
 assert.match(ui,/folder:destination\.folder,group:destination\.group/);
});
test('moving can be cancelled without changing an item',()=>{
 assert.match(ui,/cancel\.onclick=\(\)=>\{overlay\.remove\(\);resolve\(null\)\}/);
 assert.match(ui,/if\(destination\)await replay\.itemUpdate/);
});
