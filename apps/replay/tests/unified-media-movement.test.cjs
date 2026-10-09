const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const main=fs.readFileSync(path.join(__dirname,'../electron/main.cjs'),'utf8'),ui=fs.readFileSync(path.join(__dirname,'../src/app.js'),'utf8');
test('renderer and backend parse',()=>{new vm.Script(ui);new vm.Script(main)});
test('sidebar only displays Dashboard, Videos, Images, GIFs and Favorites',()=>{const s=ui.match(/const sections=(\[[^;]+);/)[1];assert.ok(!s.includes("'fandoms'")&&!s.includes("'nonfandom'"));for(const name of ['dashboard','videos','images','gifs','favorites'])assert.ok(s.includes("'"+name+"'"))});
test('migration makes one Non-Fandom root in each library and preserves existing items',()=>{
 const start=main.indexOf('function consolidateMediaLibraries(d){'),end=main.indexOf('async function installApprovedFandomFolders()',start);
 assert.ok(start>0&&end>start);
 const fn=vm.runInNewContext(main.slice(start,end)+';consolidateMediaLibraries',{crypto:require('node:crypto')});
 const d={folders:[{id:'old-folder',kind:'videos',group:'nonfandom',name:'Other',parent:''}],items:[{id:'i',kind:'videos',group:'nonfandom',folder:'old-folder'},{id:'j',kind:'videos',group:'nonfandom',folder:''}]};
 assert.ok(fn(d)>0);assert.equal(fn(d),0);
 assert.equal(d.folders.filter(f=>f.name==='Non-Fandom').length,3);
 const nf=d.folders.find(f=>f.kind==='videos'&&f.name==='Non-Fandom');
 assert.equal(d.folders.find(f=>f.id==='old-folder').parent,nf.id);
 assert.equal(d.items[0].folder,'old-folder');assert.equal(d.items[1].folder,nf.id);
 assert.equal(d.items[0].group,'fandom');
});
test('Move dialog is immediate-level only',()=>{assert.match(ui,/const nearby=folders\.filter/);assert.match(ui,/const children=current\?folders\.filter/);assert.ok(!ui.includes("for(const groupName of ['fandom','nonfandom'])"))});
