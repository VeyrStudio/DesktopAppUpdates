const test=require('node:test');const assert=require('node:assert/strict');const fs=require('node:fs');const path=require('node:path');const vm=require('node:vm');
const root=path.resolve(__dirname,'..');const read=p=>fs.readFileSync(path.join(root,p),'utf8');
const scripts=['electron/main.cjs','electron/preload.cjs','src/app.js'];
for(const p of scripts)test('JavaScript syntax: '+p,()=>{new vm.Script(read(p),{filename:p})});
const cases=[
['secure Electron renderer', 'electron/main.cjs', 'contextIsolation:true'],
['media content hashed before importing','electron/main.cjs','const hash=await checksum(src)'],
['original deletion after verified backup','electron/main.cjs','await backupOne({...d,items:[...d.items,item]},item)'],
['backup location safety guard','electron/main.cjs','Backups must be stored outside Replay application data'],
['automatic backup synchronization','electron/main.cjs','async function synchronizeBackup()'],
['recoverable backup history','electron/main.cjs','.Replay Recovery'],
['30 day expiration','electron/main.cjs','30*86400000'],
['restore backup integrity validation','electron/main.cjs','Backup integrity failed'],
['video codec fallback','electron/main.cjs','compatible-video'],
['drag-and-drop media import','src/app.js',"document.addEventListener('drop'"],
['thumbnail gallery reordering','src/app.js','ondragstart'],
['image zoom and pan','src/app.js','onpointermove'],
['GIF pause','src/app.js','Pause GIF'],
['pinned collections','src/app.js','pinned-collections'],
['gallery sorting','src/app.js','sortByFolder'],
['multiple fandom assignment','src/app.js','fandoms:raw.split'],
['backup restore controls','src/app.js','Restore from Backup'],
['update integrity verification','electron/main.cjs','Installer checksum mismatch']
];
for(const [name,file,needle] of cases)test('Source contract: '+name,()=>assert.ok(read(file).includes(needle),name));
test('NSIS Windows installer configured',()=>{const pkg=JSON.parse(read('package.json'));assert.ok(pkg.build.win.target.includes('nsis'));assert.ok(pkg.scripts['build:win'])});
