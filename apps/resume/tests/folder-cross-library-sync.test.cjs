const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const main=fs.readFileSync(path.join(__dirname,'../electron/main.cjs'),'utf8');
test('main process parses',()=>new vm.Script(main));
const start=main.indexOf('const replayKinds='),end=main.indexOf('async function installApprovedFandomFolders()',start);
const code=main.slice(start,end);
function setup(folders,items=[]){const context={crypto:{randomUUID:(()=>{let n=0;return ()=>String(++n)})()},JSON,Error};vm.createContext(context);vm.runInContext(code,context);const d={folders,items,settings:{}};return {d,context}}
test('first run copies video customizations without changing any media records',()=>{
 const folders=['videos','images','gifs'].map((kind,i)=>({id:String(i+10),kind,group:'fandom',parent:'',name:'Invisible Boys',color:kind==='videos'?'#123456':'#abcdef',details:kind==='videos'?{pairings:'Matt × Charlie'}:{},iconImage:kind==='videos'?'data:image/png;base64,aaaa':''}));
 const items=[{id:'media1',kind:'videos',folder:'10',name:'Video'}];
 const {d,context}=setup(folders,items);const before=JSON.stringify(items);
 vm.runInContext('synchronizeExistingVideoFoldersOnce(d)',Object.assign(context,{d}));
 assert.equal(d.folders.filter(f=>f.name==='Invisible Boys').length,3);
 for(const f of d.folders){assert.equal(f.color,'#123456');assert.equal(f.details.pairings,'Matt × Charlie');assert.equal(f.iconImage,'data:image/png;base64,aaaa')}
 assert.equal(JSON.stringify(d.items),before);
 assert.equal(d.settings.folderAppearanceSyncedV048,true);
});
test('nested folders are matched under their category-specific parent',()=>{
 const {d,context}=setup([{id:'v',kind:'videos',group:'fandom',parent:'',name:'DC',color:'#123456'},{id:'s',kind:'videos',group:'fandom',parent:'v',name:'Batman',icon:'B'}]);
 context.d=d;vm.runInContext('synchronizeExistingVideoFoldersOnce(d)',context);
 assert.equal(d.folders.length,6);
 for(const kind of ['images','gifs']){const parent=d.folders.find(f=>f.kind===kind&&f.name==='DC');const child=d.folders.find(f=>f.kind===kind&&f.name==='Batman');assert.equal(child.parent,parent.id);assert.equal(child.icon,'B')}
});
test('re-running initial synchronization preserves subsequent edits',()=>{const {d,context}=setup([{id:'v',kind:'videos',group:'fandom',parent:'',name:'Test',color:'#123456'},{id:'i',kind:'images',group:'fandom',parent:'',name:'Test',color:'#abcdef'}]);context.d=d;vm.runInContext('synchronizeExistingVideoFoldersOnce(d)',context);d.folders[1].color='#ffffff';vm.runInContext('synchronizeExistingVideoFoldersOnce(d)',context);assert.equal(d.folders[1].color,'#ffffff')});
test('folder create and edit handlers synchronize across media libraries',()=>{assert.match(main,/d\.folders\.push\(created\);synchronizeFolderAppearance\(d,created\)/);assert.match(main,/const peerCopies=matchingFolderCopies\(d,f\)/);assert.match(main,/copyFolderAppearance\(f,peer\)/)});
