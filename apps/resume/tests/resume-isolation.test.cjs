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

test('verified Replay transfer requires closed Replay and saves source recovery snapshot',()=>{
 assert.match(main,/IMAGENAME eq Replay\.exe/);
 assert.match(main,/library-before-migration\.json/);
 assert.match(main,/Replay source cleanup/);
 assert.match(main,/replayRemoved/);
 assert.match(main,/await backupOne\(ownDb,copy\)/);
});
test('source Windows photo files are removed only following independent archive and backup verification',()=>{
 const start=main.indexOf('async function importFiles(');
 const end=main.indexOf('async function updateItem(',start);
 const body=main.slice(start,end);
 assert.match(body,/checksum\(path\.join\(root,stored\)\)/);
 assert.match(body,/checksum\(backupFile\)/);
 assert.ok(body.indexOf('await fsp.rm(src)')>body.indexOf('checksum(backupFile)'));
});
test('Resume photo viewer deletes without a confirmation dialog',()=>{
 const pos=ui.indexOf("permanentDeleteButton.onclick");
 const stop=ui.indexOf("$('#move-viewed-media').onclick",pos);
 const body=ui.slice(pos,stop);
 assert.ok(pos>=0&&stop>pos);
 assert.doesNotMatch(body,/confirm\(/);
});
