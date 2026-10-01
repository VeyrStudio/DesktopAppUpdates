/* The Index — native, non-blocking creation dialogs. No browser prompt() calls. */
function indexForm({title,description,fields,submitText='Create',onSave}){
 const root=document.getElementById('index-modal-root');
 return new Promise(resolve=>{
  const mask=document.createElement('div');mask.className='index-modal-mask';
  const dialog=document.createElement('section');dialog.className='index-modal';dialog.setAttribute('role','dialog');dialog.setAttribute('aria-modal','true');dialog.setAttribute('aria-label',title);
  const top=document.createElement('div');top.className='index-modal-title';top.innerHTML='<span class="eyebrow">THE INDEX · NEW RECORD</span><h2>'+esc(title)+'</h2><p class="sub">'+esc(description||'')+'</p>';
  const form=document.createElement('form');form.className='index-modal-form';
  for(const f of fields){
   const row=document.createElement('label');row.className='index-modal-field';row.textContent=f.label;
   let input;if(f.type==='select'){input=document.createElement('select');for(const o of f.options||[]){const opt=document.createElement('option');opt.value=o;opt.textContent=o;input.appendChild(opt)}}else if(f.type==='textarea'){input=document.createElement('textarea');input.rows=3;}else{input=document.createElement('input');input.type=f.type||'text'}
   input.name=f.name;input.value=f.value||'';input.placeholder=f.placeholder||'';input.required=Boolean(f.required);row.appendChild(input);form.appendChild(row);
  }
  const actions=document.createElement('div');actions.className='index-modal-actions';
  const cancel=document.createElement('button');cancel.type='button';cancel.className='btn';cancel.textContent='Cancel';
  const save=document.createElement('button');save.type='submit';save.className='btn primary';save.textContent=submitText;
  actions.append(cancel,save);form.append(actions);dialog.append(top,form);mask.appendChild(dialog);root.replaceChildren(mask);
  let closed=false;
  function dismiss(v){if(closed)return;closed=true;document.removeEventListener('keydown',escHandler);mask.remove();resolve(v)}
  function escHandler(e){if(e.key==='Escape'){e.preventDefault();dismiss(null)}}
  document.addEventListener('keydown',escHandler);
  cancel.addEventListener('click',()=>dismiss(null));
  mask.addEventListener('mousedown',e=>{if(e.target===mask)dismiss(null)});
  form.addEventListener('submit',async e=>{e.preventDefault();const data=Object.fromEntries(new FormData(form).entries());if(fields.some(f=>f.required&&!String(data[f.name]||'').trim()))return;save.disabled=true;save.textContent='Saving…';
   try{await onSave(data);dismiss(data)}catch(error){save.disabled=false;save.textContent=submitText;const feedback=form.querySelector('.index-modal-error')||document.createElement('p');feedback.className='index-modal-error';feedback.textContent='Could not save: '+error.message;form.insertBefore(feedback,actions);}
  });
  queueMicrotask(()=>form.querySelector('[name]')?.focus());
 });
}
addCharacter=async function(){
 return indexForm({title:'Create a Character',description:'Start a new profile. You can fill in every detail later.',submitText:'Create Character',fields:[
 {name:'name',label:'Character Name',value:'',placeholder:'Enter their name',required:true},
 {name:'story',label:'Story',type:'select',options:['Unassigned',...db.stories.map(s=>s.name)]},
 {name:'status',label:'Profile Progress',type:'select',options:['Blank','In Progress','Existing']}
 ],onSave:async v=>{const c={id:uid(),name:v.name.trim(),story:v.story==='Unassigned'?'':v.story,status:v.status,fields:{'Full Name':v.name.trim(),'Story Title':v.story==='Unassigned'?'':v.story},portrait:null,created:Date.now(),updated:Date.now(),relationships:[],events:[],powers:[],moodImages:[]};
 indexRemember();db.characters.push(c);selectedId=c.id;await api.save(db);section='Characters';profileId=c.id;profileTab='Overview';render();toast('Character created');}});
};
addCollection=async function(key){
 const story=key==='stories';
 return indexForm({title:story?'Create a Story':'Create a Worldbuilding Entry',description:story?'Add a story, then link characters and notes.':'Create a location, culture, species, item or another piece of lore.',submitText:story?'Create Story':'Create Entry',fields:[
 {name:'name',label:story?'Story Title':'Entry Name',placeholder:story?'Title of your story':'Name of the location, species, or item',required:true},
 {name:'category',label:story?'Writing Status':'Entry Category',type:'select',options:story?['Planning','Outlining','Writing','Revising','Complete','Published','On Hold']:['Location','Species','Culture','Organization','Item','History','Magic System','Religion','Language','Technology','Environment','Other']},
 {name:'description',label:'Description (optional)',type:'textarea',placeholder:'A short description'}
 ],onSave:async v=>{const x={id:uid(),name:v.name.trim(),description:v.description,created:Date.now(),updated:Date.now(),image:null,tags:'',...(story?{status:v.category,genre:'',setting:''}:{category:v.category})};
 indexRemember();db[key].push(x);if(story){storyId=x.id;section='Stories'}else{worldId=x.id;section='Worldbuilding'}await api.save(db);render();toast((story?'Story':'Entry')+' created');}});
};
addTag=async function(){return indexForm({title:'Create a Tag',description:'Tags can be reused across characters, stories, notes, and worldbuilding.',submitText:'Create Tag',fields:[
 {name:'name',label:'Tag Name',placeholder:'e.g. Found Family',required:true},
 {name:'category',label:'Category',type:'select',options:['Custom','Characters','Stories','Worldbuilding','Notebook','Tropes','Content']},
 {name:'color',label:'Color',type:'color',value:'#b99b5d'}
 ],onSave:async v=>{if(db.tags.some(t=>t.name.toLowerCase()===v.name.trim().toLowerCase()))throw Error('A tag with this name already exists');const t={id:uid(),name:v.name.trim(),category:v.category,color:v.color,description:'',notes:''};
 indexRemember();db.tags.push(t);tagId=t.id;section='Tags';await api.save(db);render();toast('Tag created');}});
};
indexNewNote=async function(){return indexForm({title:'Create a Note',description:'Keep research, ideas, and story notes together.',submitText:'Create Note',fields:[
 {name:'name',label:'Note Title',placeholder:'Untitled Note',required:true},
 {name:'category',label:'Category',type:'select',options:['General','Character','Story','Worldbuilding','Research','Idea','Writing','Lore','Timeline','Other']}
 ],onSave:async v=>{const n={id:uid(),name:v.name.trim(),body:'',richHtml:'',category:v.category,attachments:[],created:Date.now(),updated:Date.now()};indexRemember();db.notes.push(n);noteId=n.id;section='Notebook';await api.save(db);render();toast('Note created');}});
};
addNote=indexNewNote;
indexPrintNote=function(id){const n=db.notes.find(x=>x.id===id);if(!n)return;const title=n.name||'The Index Note';const body=n.richHtml||esc(n.body||'').replace(/\n/g,'<br>');const win=window.open('','_blank','width=820,height=900');if(!win){toast('Allow the print window to open, then choose Print to PDF');return}win.document.write('<!doctype html><html><head><title>'+esc(title)+'</title><style>body{font:16px Georgia,serif;line-height:1.6;color:#203b30;margin:45px}h1{border-bottom:2px solid #b2965e;padding-bottom:20px}</style></head><body><h1>'+esc(title)+'</h1>'+body+'</body></html>');win.document.close();win.focus();win.print()};
checkUpdate=async function(){try{const data=await api.checkUpdate();if(data.status==='available'){updateState='available';updateStatus='The Index '+data.version+' is ready to download';render()}else toast('The Index is up to date')}catch(e){toast('Update check failed: '+e.message)}};
downloadUpdate=async function(){try{const r=await api.downloadUpdate();updateState='downloaded';updateStatus='The Index '+r.version+' is ready to install';render()}catch(e){toast('Download failed: '+e.message)}};
installUpdate=async function(){try{await api.installUpdate();toast('Starting installer…')}catch(e){toast('Installation failed: '+e.message)}};
const _indexRenderForSidebar=render;
render=function(){_indexRenderForSidebar();const box=document.getElementById('recent-characters');if(box){box.innerHTML='<div class="sidebar-heading">RECENT</div>'+db.characters.slice(-5).reverse().map(c=>'<button class="sidebar-character" onclick="openProfile(\''+esc(c.id)+'\')">'+(c.portrait?img(c.portrait,'sidebar-avatar'):'<span class="sidebar-avatar empty-avatar">✦</span>')+'<span>'+esc(c.name||'Untitled')+'</span></button>').join('')+(db.characters.length?'':'<p class="recent-empty">Your characters will appear here.</p>')}};
