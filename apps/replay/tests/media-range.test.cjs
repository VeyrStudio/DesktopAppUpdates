const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const main=fs.readFileSync(path.join(__dirname,'../electron/main.cjs'),'utf8');
test('main process JavaScript parses',()=>new vm.Script(main));
test('media protocol advertises byte range support',()=>{
 assert.match(main,/Accept-Ranges.*bytes/);
 assert.match(main,/Content-Range/);
 assert.match(main,/status=206/);
 assert.match(main,/status:416/);
 assert.match(main,/createReadStream\(file,\{start,end\}\)/);
});
test('media supports seeking in original and converted videos',()=>{
 assert.match(main,/compatibleVideoCache\.get\(id\)/);
 assert.match(main,/file=path\.join\(root,item\.stored\)/);
 assert.match(main,/req\.headers\.get\('range'\)/);
});

test('media URLs preserve the original item identifier',()=>{assert.match(main,/resource\.pathname\.slice\(1\)/)});
