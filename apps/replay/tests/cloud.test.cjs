const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const cloud=fs.readFileSync(path.join(__dirname,'../electron/cloud.cjs'),'utf8');
test('Replay Cloud local server has valid JavaScript and exports launcher',()=>{new vm.Script(cloud);const c=require('../electron/cloud.cjs');assert.equal(typeof c.launch,'function')});
test('Replay Cloud gates API requests behind private key',()=>{assert.match(cloud,/if\(!allow\(req\)\)return reply\(res,401/);assert.match(cloud,/timingSafeEqual/)});
test('Replay Cloud requires explicit approval before verified import',()=>{assert.match(cloud,/needs-approval/);assert.match(cloud,/status==='approved'/);assert.match(cloud,/importVideo\(j.file,j.folderId\)/);assert.match(cloud,/result\?\.status!=='imported'/)});
test('Replay Cloud prevents arbitrary destinations and supports unsorted fallback',()=>{assert.match(cloud,/f.kind==='videos'/);assert.match(cloud,/folderId=String\(b.folderId\|\|''\)/)});
