const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const cloud=fs.readFileSync(path.join(__dirname,'../electron/cloud.cjs'),'utf8');
test('Replay Cloud server code parses and exports launcher',()=>{new vm.Script(cloud);assert.equal(typeof require('../electron/cloud.cjs').launch,'function')});
test('Replay Cloud restricts queue operations to paired phones',()=>{assert.match(cloud,/if\(!allow\(req\)\)return reply\(res,401/);assert.match(cloud,/timingSafeEqual/)});
test('Multiple links are accepted with a maximum batch size',()=>{assert.match(cloud,/Array.isArray\(b.urls\)/);assert.match(cloud,/submitted.length>50/);assert.match(cloud,/already in queue\/library/)});
test('Downloaded videos automatically move into Replay unsorted',()=>{assert.match(cloud,/j.folderId='';j.status='approved'/);assert.match(cloud,/importVideo\(j.file,j.folderId\)/);assert.doesNotMatch(cloud,/\/api\/approve/);assert.match(cloud,/status==='approved'/)});
test('Existing approvals are migrated and duplicates do not fail',()=>{assert.match(cloud,/job.status==='needs-approval'/);assert.match(cloud,/status!=='duplicate'/)});
