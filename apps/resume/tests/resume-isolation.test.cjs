const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const root=path.join(__dirname,'..');const read=p=>fs.readFileSync(path.join(root,p),'utf8');
const main=read('electron/main.cjs'),ui=read('src/app.js'),detached=read('src/media-window.js'),pkg=JSON.parse(read('package.json'));
test('Resume scripts are valid JavaScript',()=>{new vm.Script(main);new vm.Script(ui);new vm.Script(detached)});
test('Resume uses its own Windows identity, storage and URL scheme',()=>{
 assert.equal(pkg.build.appId,'studio.veyr.resume');assert.equal(pkg.build.productName,'Resume');
 assert.match(main,/scheme:'resume'/);assert.match(main,/'VeyrStudio','Resume'/);assert.match(main,/'ResumeBackup'/);
 assert.doesNotMatch(main,/app\.setPath\('userData'[^\n]*'Replay'/);assert.doesNotMatch(main,/scheme:'replay'/);assert.doesNotMatch(main,/protocol\.handle\('replay'/);assert.match(main,/protocol\.handle\('resume'/);
 assert.doesNotMatch(ui,/replay:\/\//);assert.match(ui,/resume:\/\//);
});
test('navigation is photo-only',()=>{assert.match(ui,/\['images','▧ Photos'\]/);assert.doesNotMatch(ui,/\['videos','▷ Videos'\]/);assert.doesNotMatch(ui,/\['gifs','◇ GIFs'\]/)});
test('only recognized photo formats can be imported',()=>{const line=main.split('\n').find(x=>x.startsWith('const category=f=>'));assert.match(line,/jpg\|jpeg\|png/);assert.doesNotMatch(line,/mp4\|mov/);assert.doesNotMatch(line,/gif\$|\\.gif/);});
test('Resume has own update channel',()=>{assert.match(main,/main\/resume\/resume\.json/);assert.doesNotMatch(main,/main\/replay\/replay\.json/)});

test('migration copies and verifies without deleting Replay photos',()=>{const start=main.indexOf("ipcMain.handle('migrate-replay-photos'");const end=main.indexOf("ipcMain.handle('choose-folder-icon'",start);const body=main.slice(start,end);assert.ok(start>0&&end>start);assert.match(body,/await fileCopy\(src,dest\)/);assert.match(body,/verifiedHash!==photoHash/);assert.doesNotMatch(body,/fsp\.rm\(src/);assert.doesNotMatch(body,/fsp\.rename\(src/)});
test('photo editor preserves original bytes in separate Originals folder',()=>{assert.match(main,/ipcMain\.handle\('save-photo-edit'/);assert.match(main,/Originals/);assert.match(ui,/edit-crop/);assert.match(ui,/edit-rotate/)});
