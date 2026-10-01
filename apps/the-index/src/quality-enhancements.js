/* The Index: integration polish and interaction accessibility. */
const indexRenderBeforePolish=render;
render=function(){
 const active=document.activeElement,searching=active?.classList?.contains('search'),position=searching?active.selectionStart:null;
 indexRenderBeforePolish();
 if(searching){const next=document.querySelector('.search');if(next){next.focus();if(typeof position==='number')try{next.setSelectionRange(position,position)}catch{}}}
 document.documentElement.style.setProperty('--editor-spacing',String(db?.settings?.lineSpacing||1.65));
 const editor=document.getElementById('index-note-editor');
 if(editor){editor.spellcheck=db.settings.spellcheck!==false;if(db.settings.wordCount!==false){
  const count=document.createElement('div');count.className='sub word-count';count.id='index-word-count';count.textContent='Words: '+(editor.innerText||'').trim().split(/\s+/).filter(Boolean).length;
  editor.insertAdjacentElement('afterend',count);
 }}
};
const originalIndexSaveEditor=indexSaveEditor;
indexSaveEditor=function(){originalIndexSaveEditor();const node=document.getElementById('index-note-editor');const target=document.getElementById('index-word-count');if(node&&target)target.textContent='Words: '+(node.innerText||'').trim().split(/\s+/).filter(Boolean).length};
const oldCharacterTile=characterTile;
characterTile=function(c){let html=oldCharacterTile(c);if(db.settings?.hideSpoilers){html=html.replace(/<small>[^<]*<\/small>/,'<small>Story hidden</small>')}return html};
const previousIndexRepeat=indexRepeatCard;
indexRepeatCard=function(c,key,item,i,labels){
 let html=previousIndexRepeat(c,key,item,i,labels);
 if(key==='events')html=html.replace('class="panel fields-card"','class="panel fields-card draggable-event" draggable="true" ondragstart="indexDragEvent(event,\''+esc(c.id)+'\','+i+')" ondragover="event.preventDefault()" ondrop="indexDropEvent(event,\''+esc(c.id)+'\','+i+')"');
 return html;
};
function indexDragEvent(event,id,index){event.dataTransfer.setData('text/plain',JSON.stringify({id,index}));event.dataTransfer.effectAllowed='move'}
async function indexDropEvent(event,id,target){event.preventDefault();let parsed;try{parsed=JSON.parse(event.dataTransfer.getData('text/plain'))}catch{return}if(parsed.id!==id||parsed.index===target)return;let c=db.characters.find(x=>x.id===id);if(!c?.events?.[parsed.index])return;indexRemember();const [eventItem]=c.events.splice(parsed.index,1);c.events.splice(target,0,eventItem);await commit()}
const oldAddRepeat=addRepeat;
addRepeat=async function(id,key){indexRemember();return oldAddRepeat(id,key)};
const oldDelRepeat=delRepeat;
delRepeat=async function(id,key,i){if(db.settings?.confirmDelete!==false&&!confirm('Remove this '+(key==='events'?'event':key==='powers'?'power':'relationship')+'?'))return;indexRemember();return oldDelRepeat(id,key,i)};
const oldAddCharacter=addCharacter;
addCharacter=async function(){indexRemember();return oldAddCharacter()};
const oldNoteImage=noteImage;
noteImage=async function(id){indexCommitEditor?.();return oldNoteImage(id)};
const oldDeleteNote=deleteNote;
deleteNote=async function(id){if(db.settings?.confirmDelete===false){db.notes=db.notes.filter(x=>x.id!==id);noteId=null;await commit();return}return oldDeleteNote(id)};
const oldDeleteCollection=deleteCollection;
deleteCollection=async function(key,id){if(db.settings?.confirmDelete===false){db[key]=db[key].filter(x=>x.id!==id);await commit();return}return oldDeleteCollection(key,id)};
const backupNowOriginal=backupNow;
backupNow=async function(){try{const result=await api.backup();db.settings.lastBackupAt=Date.now();await api.save(db);toast('Backup saved: '+result)}catch(e){toast('Backup failed: '+e.message)}};
const indexStartBeforePolish=start;
start=async function(){await indexStartBeforePolish();if(db.settings?.restoreNote&&db.settings.lastNoteId)noteId=db.settings.lastNoteId;db.settings.spellcheck??=true;db.settings.wordCount??=true;db.settings.defaultNoteCategory??='General';render();if(db.settings.backupReminder){let interval=db.settings.backupFrequency==='Daily'?864e5:db.settings.backupFrequency==='Monthly'?2592e6:6048e5;if(Date.now()-(db.settings.lastBackupAt||0)>interval){setTimeout(()=>toast('Backup reminder: consider backing up The Index'),1300)}}};
const prevIndexNotePick=indexNotePick;
indexNotePick=function(id){db.settings.lastNoteId=id;api.save(db);return prevIndexNotePick(id)};
const prevIndexNewNote=indexNewNote;
indexNewNote=async function(){await prevIndexNewNote();if(noteId){const n=db.notes.find(x=>x.id===noteId);if(n)n.category=db.settings.defaultNoteCategory||'General';await api.save(db);render()}};
