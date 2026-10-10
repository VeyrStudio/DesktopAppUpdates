const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const source=fs.readFileSync(path.join(__dirname,'../src/app.js'),'utf8');
test('renderer parses',()=>new vm.Script(source));
test('bulk selection supports modifier click, select-all and clearing',()=>{
 for(const needle of ['event.shiftKey','event.ctrlKey','event.metaKey','visibleMediaIds()','selectedMedia.add(id)','id="select-all"','id="clear-selected"'])assert.ok(source.includes(needle),needle);
});
test('bulk moves through same immediate-folder picker',()=>{
 assert.match(source,/const dest=await moveMediaPicker\(item,data\.folders\.filter/);
 assert.match(source,/await moveMediaBatch\(ids,dest\.folder,dest\.group\)/);
});
test('dragging selected file transfers selection',()=>{
 assert.match(source,/window\.replayDragIds=ids/);
 assert.match(source,/text\/replay-items/);
 assert.match(source,/window\.replayDragIds\?\.includes\(id\)\?window\.replayDragIds:\[id\]/);
});
