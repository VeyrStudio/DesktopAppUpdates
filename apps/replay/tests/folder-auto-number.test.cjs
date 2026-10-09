const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const main=fs.readFileSync(path.join(__dirname,'../electron/main.cjs'),'utf8');
const ui=fs.readFileSync(path.join(__dirname,'../src/app.js'),'utf8');
test('Replay scripts parse',()=>{new vm.Script(main);new vm.Script(ui)});
test('folder naming is optional in both creation and editing',()=>{
 assert.match(ui,/name="autoNumberMedia"/);
 assert.match(main,/autoNumberMedia:x\.autoNumberMedia!==false/);
 assert.match(main,/f\.autoNumberMedia=!!patch\.autoNumberMedia/);
});
test('imports and folder transfers both apply sequential naming',()=>{
 assert.match(main,/numberedMediaName\(d,requestedFolder\?\.id,ext\)/);
 assert.match(main,/item\.folder!==originalFolder/);
 assert.match(main,/numberedMediaName\(d,item\.folder,path\.extname\(item\.stored\),item\.id\)/);
});
test('numbering respects other occupied names and preserves extension',()=>{
 assert.match(main,/used\.has\(name\.toLowerCase\(\)\)/);
 assert.match(main,/safe\(f\.name\+' '\+number\)/);
});

test('enabling numbering immediately names existing files',()=>{assert.match(main,/!numberingWasEnabled/);assert.match(main,/item\.name=safe\(f\.name\+' '\+n\+\+\)/)});

test('display names omit extensions while actual stored media remains unchanged',()=>{assert.match(main,/name=safe\(f\.name\+' '\+number\)/);assert.match(main,/item\.name=safe\(f\.name\+' '\+n\+\+\)/);assert.match(main,/const id=crypto\.randomUUID\(\),ext=path\.extname\(src\),stored=path\.join\(kind,id\+ext\)/)});
test('dropping into an already selected numbered folder also corrects the name',()=>{assert.match(main,/patch\.folder!==undefined/)});

test('upgrade enables and renumbers folders once, preserving subsequent user choices',()=>{const start=main.indexOf('function enableDefaultNumberingOnce(d){'),end=main.indexOf('async function installApprovedFandomFolders()',start);assert.ok(start>0&&end>start);const fn=vm.runInNewContext(main.slice(start,end)+';enableDefaultNumberingOnce',{safe:x=>x});const d={folders:[{id:'f',kind:'videos',name:'Invisible Boys',autoNumberMedia:false}],items:[{id:'a',folder:'f',kind:'videos',name:'original.mp4',order:0},{id:'b',folder:'f',kind:'videos',name:'original2.mp4',order:1}],settings:{}};assert.ok(fn(d)>0);assert.equal(d.folders[0].autoNumberMedia,true);assert.equal(d.items[0].name,'Invisible Boys 1');assert.equal(d.items[1].name,'Invisible Boys 2');d.folders[0].autoNumberMedia=false;assert.equal(fn(d),0);assert.equal(d.folders[0].autoNumberMedia,false)});
