const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {JSDOM}=require('jsdom');
const root=path.join(__dirname,'..','src');
const scriptNames=['renderer.js','profile-enhancements.js','library-enhancements.js','settings-enhancements.js','quality-enhancements.js','productivity-enhancements.js'];
async function setup(){
 const html=fs.readFileSync(path.join(root,'index.html'),'utf8').replace(/<script[^>]*><\/script>/g,'');
 const dom=new JSDOM(html,{url:'http://localhost',runScripts:'dangerously',pretendToBeVisual:true});
 const w=dom.window;
 let data={characters:[],stories:[],worldbuilding:[],notes:[],tags:[],events:[],settings:{}};
 w.indexAPI={read:async()=>structuredClone(data),save:async next=>(data=structuredClone(JSON.parse(JSON.stringify(next))),data),version:async()=>'0.2.0',checkUpdate:async()=>({status:'up-to-date'}),chooseImage:async()=>null,backup:async()=>'/tmp/backup.json',onUpdate:()=>{}};
 w.prompt=(_question,initial)=>initial||'New Entry';
 w.confirm=()=>true;
 w.alert=()=>{};
 w.document.execCommand=()=>true;
 for(const name of scriptNames){const script=w.document.createElement('script');script.textContent=fs.readFileSync(path.join(root,name),'utf8');w.document.body.appendChild(script);}
 await new Promise(r=>setTimeout(r,40));
 return {w,dom,stored:()=>data};
}
test('all character profile tabs render with Family absent',async()=>{
 const {w,dom}=await setup();
 await w.eval('addCharacter()');
 const tabs=w.eval('PROFILE');
 assert.deepEqual(Array.from(tabs),['Overview','Appearance','Personality','Background','Relationships','Skills','Story','Timeline','Notes']);
 assert.doesNotMatch(w.document.body.textContent,/Family \u2014/);
 for(const tab of tabs){
   w.eval('setProfileTab('+JSON.stringify(tab)+')');
   assert.ok(w.document.querySelector('#screen').textContent.includes(tab),tab);
 }
 dom.window.close();
});
test('custom traits, related abilities and timeline edits save across screens',async()=>{
 const {w,dom,stored}=await setup();
 await w.eval('addCharacter()');
 await w.eval("indexMultiAdd(db.characters[0].id,'Positive Traits','Resourceful')");
 assert.ok(stored().characters[0].fields['Positive Traits'].includes('Resourceful'));
 await w.eval("addRepeat(db.characters[0].id,'powers')");
 await w.eval("changeRepeat(db.characters[0].id,'powers',0,'Power / Ability','Tracking')");
 assert.equal(stored().characters[0].powers[0]['Power / Ability'],'Tracking');
 await w.eval("addRepeat(db.characters[0].id,'events')");
 await w.eval("changeRepeat(db.characters[0].id,'events',0,'Event Name','Arrival')");
 w.eval("go('Timeline')");
 assert.ok(w.document.querySelector('#screen').textContent.includes('Arrival'));
 dom.window.close();
});
test('Notebook editor, tags and all settings categories render without placeholders',async()=>{
 const {w,dom}=await setup();
 await w.eval("indexNewNote()");
 w.eval("go('Notebook')");
 assert.ok(w.document.querySelector('#index-note-editor'));
 assert.ok(w.document.querySelector('.note-layout .third'));
 await w.eval("addTag()");
 w.eval("go('Tags')");
 assert.ok(w.document.querySelector('.note-layout'));
 w.eval("go('Settings')");
 for(const tab of w.eval('SETTINGS')){
   w.eval('selectSetting('+JSON.stringify(tab)+')');
   assert.ok(w.document.querySelector('#screen').textContent.includes(tab));
   assert.doesNotMatch(w.document.querySelector('#screen').textContent,/reserved for the next implementation pass/i);
 }
 dom.window.close();
});
test('Stories, Worldbuilding, search and archive operations are connected',async()=>{
 const {w,dom,stored}=await setup();
 await w.eval("addCollection('stories')");
 await w.eval("addCollection('worldbuilding')");
 assert.equal(stored().stories.length,1);
 assert.equal(stored().worldbuilding.length,1);
 w.eval("go('Stories')");
 assert.ok(w.document.querySelector('#screen').textContent.includes('Linked Characters'));
 w.eval("go('Worldbuilding')");
 assert.ok(w.document.querySelector('#screen').textContent.includes('Category'));
 dom.window.close();
});

test('Dashboard pin controls and searchable library sorting are functional',async()=>{
 const {w,dom,stored}=await setup();
 await w.eval("addCharacter()");
 await w.eval("indexTogglePin(db.characters[0].id)");
 assert.equal(stored().characters[0].pinned,true);
 w.eval("go('Dashboard')");
 assert.ok(w.document.querySelector('#screen').textContent.includes('Pinned Characters'));
 w.eval("go('Characters');indexCharacterSort('name')");
 assert.ok(w.document.querySelector('#screen').textContent.includes('Pinned Only'));
 dom.window.close();
});
test('Notebook sanitizes scripts from rich HTML while retaining readable formatting',async()=>{
 const {w,dom}=await setup();
 await w.eval("indexNewNote()");
 const editor=w.document.querySelector('#index-note-editor');
 editor.innerHTML='<b>Saved</b><img src=x onerror=alert(1)><script>alert(1)</script>';
 w.eval('indexCommitEditor()');
 const actual=w.eval('db.notes[0].richHtml');
 assert.match(actual,/<b>Saved<\/b>/);
 assert.doesNotMatch(actual,/onerror|<script|<img/i);
 dom.window.close();
});
