const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const main=fs.readFileSync(path.join(__dirname,'../electron/main.cjs'),'utf8');
const ui=fs.readFileSync(path.join(__dirname,'../src/app.js'),'utf8');
test('Replay scripts parse',()=>{new vm.Script(main);new vm.Script(ui)});
test('folder naming is optional in both creation and editing',()=>{
 assert.match(ui,/name="autoNumberMedia"/);
 assert.match(main,/autoNumberMedia:!!x\.autoNumberMedia/);
 assert.match(main,/f\.autoNumberMedia=!!patch\.autoNumberMedia/);
});
test('imports and folder transfers both apply sequential naming',()=>{
 assert.match(main,/numberedMediaName\(d,requestedFolder\?\.id,ext\)/);
 assert.match(main,/item\.folder!==originalFolder/);
 assert.match(main,/numberedMediaName\(d,item\.folder,path\.extname\(item\.name\),item\.id\)/);
});
test('numbering respects other occupied names and preserves extension',()=>{
 assert.match(main,/used\.has\(name\.toLowerCase\(\)\)/);
 assert.match(main,/safe\(f\.name\+' '\+number\)\+extension/);
});
