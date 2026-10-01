/* The Index: working character editor controls. Runs after renderer.js. */
const INDEX_TRAITS={
 'Core Personality':['Reserved','Outgoing','Observant','Protective','Intense','Compassionate','Wary','Impulsive','Methodical','Witty','Stubborn','Patient','Brooding','Adventurous','Diplomatic','Secretive','Loyal','Pragmatic','Idealistic','Independent','Curious','Gentle','Cynical','Hopeful','Disciplined'],
 'Positive Traits':['Kind','Loyal','Patient','Resourceful','Courageous','Empathetic','Honest','Resilient','Creative','Observant','Protective','Generous','Dependable','Compassionate','Determined'],
 'Negative Traits':['Jealous','Arrogant','Possessive','Reckless','Stubborn','Guarded','Vindictive','Impatient','Distrustful','Secretive','Manipulative','Pessimistic','Insecure','Controlling'],
 'Strengths':['Combat','Intellect','Empathy','Leadership','Strategy','Survival','Tracking','Magic','Negotiation','Endurance','Creativity','Stealth','Resilience','Loyalty'],
 'Weaknesses':['Impulsiveness','Fear of Loss','Pride','Physical Limits','Distrust','Vulnerability','Isolation','Guilt','Magic Exhaustion','Lack of Control'],
 'Likes':['Nature','Quiet','Music','Reading','Travel','Animals','Touch','Rain','Coffee','Art','Winter','Summer','Adventure','Routine','Solitude'],
 'Dislikes':['Crowds','Dishonesty','Noise','Cold','Heat','Conflict','Confinement','Cruelty','Isolation','Loud Music','Change'],
 'Fears':['Abandonment','Failure','Death','Losing Loved Ones','Confinement','Water','Heights','Darkness','Being Forgotten','Loss of Control'],
 'Pet Peeves':['Interruptions','Lateness','Disorganization','Condescension','Loud Chewing','Being Watched','Unsolicited Advice','Broken Promises'],
 'Aesthetic Tags':['Dark Academia','Forest','Celestial','Gothic','Vintage','Stormy','Warm','Ethereal','Rustic','Industrial'],
 'Aliases':[],
 'Important Objects':[],
 'Tags':[]
};
Object.entries(INDEX_TRAITS).forEach(([k,v])=>{CHOICES[k]=v;MULTI.add(k)});
const INDEX_HEX={
 'Hair Color':[['Black','#1c1613'],['Brown','#67442c'],['Blond','#dfbf72'],['Red','#a44b36'],['White','#f1eee6'],['Gray','#9a999a'],['Blue','#517a9c'],['Other','#b8a187']],
 'Eye Color':[['Brown','#684633'],['Hazel','#958047'],['Blue','#638eb5'],['Green','#668d60'],['Gray','#a5a9aa'],['Amber','#c9934b'],['Red','#ae3945'],['Violet','#8769a5'],['Other','#d6c4a9']],
 'Skin Tone':[['Very Fair','#f8dfcb'],['Fair','#e9bea1'],['Light','#d9a685'],['Medium','#c58b65'],['Olive','#af825e'],['Tan','#a66c4b'],['Brown','#82553c'],['Dark','#59382c'],['Deep','#33241e'],['Other','#bb8e7b']]
};
const INDEX_DROPDOWNS={
 'Status':['Alive','Deceased','Missing','Presumed Dead','Unknown'],
 'Gender':['Man','Woman','Nonbinary','Agender','Genderfluid','Other','Unknown'],
 'Pronouns':['He/Him','She/Her','They/Them','He/They','She/They','Any','Other'],
 'Character Role':['Protagonist','Deuteragonist','Love Interest','Supporting','Antagonist','Minor','Background','Other'],
 'Social Status':['Royalty','Nobility','Wealthy','Middle Class','Working Class','Low Income','Outcast','Unknown','Other'],
 'Freedom Status':['Free','Confined','Imprisoned','Enslaved','Fugitive','Exiled','Missing','Unknown','Other'],
 'Character Tier':['Main','Major','Supporting','Minor','Cameo','Other'],
 'Education':['None','Self-Taught','Primary','Secondary','Trade / Apprenticeship','University','Graduate','Private Tutoring','Other'],
 'Past Occupation':['Student','Soldier','Healer','Scholar','Merchant','Ranger','Royalty','Artisan','Unemployed','Other'],
 'Archetype':['Hero','Antihero','Villain','Mentor','Outsider','Guardian','Trickster','Explorer','Lover','Rebel','Everyperson','Other']
};
const INDEX_TEXTAREA=new Set(['Scars','Health Notes','Full Physical Description','Secrets','Motivation','Internal Conflict','External Conflict','Fatal Flaw','Beginning State','Middle State','Ending State','Plot Relevance','Mood Board','Important Objects']);
const INDEX_LOCKS=new Set();
let INDEX_UNDO=[];
let INDEX_ZOOM=1;
function indexRemember(){INDEX_UNDO.push(JSON.stringify(db));if(INDEX_UNDO.length>50)INDEX_UNDO.shift()}
async function indexUndo(){const v=INDEX_UNDO.pop();if(!v){toast('Nothing to undo');return;}db=JSON.parse(v);await commit();toast('Last edit undone')}
function indexLock(id,name){let k=id+'|'+name;if(INDEX_LOCKS.has(k))INDEX_LOCKS.delete(k);else INDEX_LOCKS.add(k);render()}
function indexValue(c,k){let v=fieldValue(c,k);return Array.isArray(v)?v.join(', '):String(v??'')}
function indexValues(c,k){let v=fieldValue(c,k);return Array.isArray(v)?v:(typeof v==='string'?v.split(',').map(x=>x.trim()).filter(Boolean):[])}
function indexFieldSet(id,k,v){let c=db.characters.find(x=>x.id===id);if(!c||INDEX_LOCKS.has(id+'|'+k))return;indexRemember();setCharacterField(id,k,v);render()}
function indexStandardInput(c,k){
 const id=esc(c.id),val=indexValue(c,k),locked=INDEX_LOCKS.has(c.id+'|'+k);
 let control='';
 if(k==='Major Life Events'){
   const events=Array.isArray(c.fields?.[k])?c.fields[k]:[];
   control='<div class="inline-events">'+events.map((e,i)=>'<div class="panel event-note"><input aria-label="Event name" placeholder="Event title" value="'+esc(e.name)+'" onblur="indexLifeEvent('+"'"+id+"'"+','+i+','+"'name'"+',this.value)"><textarea placeholder="Notes about this event" onblur="indexLifeEvent('+"'"+id+"'"+','+i+','+"'notes'"+',this.value)">'+esc(e.notes)+'</textarea>'+button('Remove',"indexRemoveLifeEvent('"+id+"',"+i+")")+'</div>').join('')+'</div>'+button('+ Add Event',"indexAddLifeEvent('"+id+"')",'');
 }else if(INDEX_HEX[k]){
   control='<div class="swatches">'+INDEX_HEX[k].map(([name,hex])=>'<button type="button" title="'+esc(name)+'" aria-label="'+esc(name)+'" class="swatch '+(val===name?'chosen':'')+'" style="background:'+hex+'" onclick="indexFieldSet('+"'"+id+"','"+k+"','"+name+"'"+')"></button>').join('')+'</div><select onchange="indexFieldSet('+"'"+id+"','"+k+"'"+',this.value)">'+['','Other'].concat(INDEX_HEX[k].map(x=>x[0])).filter((x,i,a)=>a.indexOf(x)===i).map(x=>'<option value="'+esc(x)+'" '+(val===x?'selected':'')+'>'+esc(x||'Choose color')+'</option>').join('')+'</select>';
 }else if(MULTI.has(k)&&k!=='Major Life Events'&&!INDEX_TEXTAREA.has(k)){
   const options=(CHOICES[k]||[]).concat((db.tags||[]).filter(t=>k==='Tags').map(t=>t.name));
   control='<div class="selected-traits">'+indexValues(c,k).map(v=>'<span class="trait-chip">'+esc(v)+' <button aria-label="Remove '+esc(v)+'" onclick="indexMultiRemove('+"'"+id+"','"+k+"','"+esc(v.replace(/'/g,"&#39;"))+"'"+')">×</button></span>').join('')+'</div><div class="row"><select aria-label="Add '+esc(k)+'" onchange="if(this.value)indexMultiAdd('+"'"+id+"','"+k+"'"+',this.value)"><option value="">+ Select '+esc(k)+'</option>'+options.map(x=>'<option value="'+esc(x)+'">'+esc(x)+'</option>').join('')+'</select><input style="flex:1" placeholder="Or add custom..." onkeydown="if(event.key==='+"'Enter'"+'){event.preventDefault();indexMultiAdd('+"'"+id+"','"+k+"'"+',this.value)}"></div>';
 }else if(INDEX_TEXTAREA.has(k)){
   control='<textarea '+(locked?'disabled ':'')+'onblur="indexFieldSet('+"'"+id+"','"+k+"'"+',this.value)">'+esc(val)+'</textarea>';
 }else if(INDEX_DROPDOWNS[k]){
   control='<select '+(locked?'disabled ':'')+'onchange="indexFieldSet('+"'"+id+"','"+k+"'"+',this.value)"><option value="">Select an option</option>'+[...new Set([...INDEX_DROPDOWNS[k],val])].filter(Boolean).map(o=>'<option value="'+esc(o)+'" '+(val===o?'selected':'')+'>'+esc(o)+'</option>').join('')+'</select>'+(val==='Other'?'<input placeholder="Specify..." onblur="indexFieldSet('+"'"+id+"','"+k+"'"+',this.value)">':'');
 }else{
   control='<input '+(locked?'disabled ':'')+'type="text" list="index-list-'+k.replace(/[^a-z]/gi,'')+'" value="'+esc(val)+'" onblur="indexFieldSet('+"'"+id+"','"+k+"'"+',this.value)"><datalist id="index-list-'+k.replace(/[^a-z]/gi,'')+'">'+(CHOICES[k]||[]).map(o=>'<option value="'+esc(o)+'"></option>').join('')+'</datalist>';
 }
 return '<div class="field full-editor-field"><div class="section-header"><label>'+esc(k)+'</label><span class="row">'+(CHOICES[k]||INDEX_TRAITS[k]?'<button title="Randomize only this field" class="mini-action" onclick="indexRandom('+"'"+id+"','"+k+"'"+')">⤨</button>':'')+'<button class="mini-action" title="'+(locked?'Unlock field':'Lock field')+'" onclick="indexLock('+"'"+id+"','"+k+"'"+')">'+(locked?'🔒':'♧')+'</button></span></div>'+control+'</div>';
}
standardFields=function(c,group){return '<div class="fieldgrid">'+FIELDS[group].map(k=>indexStandardInput(c,k)).join('')+'</div>'};
async function indexMultiAdd(id,k,v){v=(v||'').trim();if(!v)return;const c=db.characters.find(x=>x.id===id);if(!c||INDEX_LOCKS.has(id+'|'+k))return;const values=indexValues(c,k);if(values.some(x=>x.toLowerCase()===v.toLowerCase()))return;indexRemember();await setCharacterField(id,k,[...values,v]);render()}
async function indexMultiRemove(id,k,v){const c=db.characters.find(x=>x.id===id);if(!c)return;indexRemember();await setCharacterField(id,k,indexValues(c,k).filter(x=>x!==v));render()}
function indexRandom(id,k){const c=db.characters.find(x=>x.id===id);if(!c||INDEX_LOCKS.has(id+'|'+k))return;const opts=CHOICES[k]||INDEX_DROPDOWNS[k]||[];if(!opts.length)return toast('No preset choices for this field');const choice=opts[Math.floor(Math.random()*opts.length)];if(MULTI.has(k))indexMultiAdd(id,k,choice);else indexFieldSet(id,k,choice)}
async function indexLifeEvent(id,i,k,v){const c=db.characters.find(x=>x.id===id);c.fields['Major Life Events'][i][k]=v;await api.save(db)}
async function indexAddLifeEvent(id){const c=db.characters.find(x=>x.id===id);indexRemember();c.fields??={};if(!Array.isArray(c.fields['Major Life Events']))c.fields['Major Life Events']=[];c.fields['Major Life Events'].push({name:'',notes:''});await commit()}
async function indexRemoveLifeEvent(id,i){const c=db.characters.find(x=>x.id===id);indexRemember();c.fields['Major Life Events'].splice(i,1);await commit()}
const INDEX_REPEAT_CHOICES={
 'Relationship Type':['Romantic Partner','Spouse','Love Interest','Friend','Best Friend','Sibling','Parent','Child','Mentor','Rival','Enemy','Acquaintance','Ally','Other'],
 'Status':['Active','Estranged','Complicated','Former','Unknown'],
 'Power Type':['Physical','Magical','Supernatural','Psychic','Biological','Technology','Learned Skill','Other'],
 'Strength Level':['None','Low','Moderate','High','Exceptional','Unmeasurable'],
 'Control Level':['Untrained','Limited','Developing','Reliable','Mastered','Uncontrollable'],
 'Visibility':['Hidden','Subtle','Obvious','Only When Used','Unknown'],
 'Importance':['Minor','Moderate','Major','Critical'],
 'Event Type':['Birth','Death','Meeting','Relationship','Conflict','Travel','Discovery','Transformation','Achievement','Trauma','Other'],
 'When Type':['Exact Date','Approximate Date','Age','Story Chapter','Relative','Unknown']
};
function indexRepeatCard(c,key,item,i,labels){
 const cid=esc(c.id),first=labels[0];let content='';
 for(const field of labels){
   let v=String(item[field]??'');
   let control='';
   if(field==='Linked Character'){
     control='<select onchange="changeRepeat('+"'"+cid+"','"+key+"',"+i+",'Linked Character'"+',this.value)"><option value="">No link</option>'+db.characters.filter(x=>x.id!==c.id).map(x=>'<option value="'+esc(x.id)+'" '+(v===x.id?'selected':'')+'>'+esc(x.name)+'</option>').join('')+'</select>';
   }else if(INDEX_REPEAT_CHOICES[field]){
     control='<select onchange="changeRepeat('+"'"+cid+"','"+key+"',"+i+",'"+field+"'"+',this.value)"><option value="">Select</option>'+[...new Set([...INDEX_REPEAT_CHOICES[field],v])].filter(Boolean).map(x=>'<option value="'+esc(x)+'" '+(v===x?'selected':'')+'>'+esc(x)+'</option>').join('')+'</select>';
   }else if(['Summary','Notes','Limitations','Weaknesses'].includes(field)){
     control='<textarea onblur="changeRepeat('+"'"+cid+"','"+key+"',"+i+",'"+field+"'"+',this.value)">'+esc(v)+'</textarea>';
   }else{
     control='<input value="'+esc(v)+'" onblur="changeRepeat('+"'"+cid+"','"+key+"',"+i+",'"+field+"'"+',this.value)">';
   }
   content+='<div class="field"><label>'+esc(field)+'</label>'+control+'</div>';
 }
 return '<div class="panel fields-card"><div class="section-header"><b>'+esc(item[first]||'New '+first)+'</b><div class="row">'+(key==='events'?button('↑',"indexMoveEvent('"+cid+"',"+i+",-1)")+' '+button('↓',"indexMoveEvent('"+cid+"',"+i+",1)"):'')+button('Remove',"delRepeat('"+cid+"','"+key+"',"+i+")")+'</div></div><div class="fieldgrid">'+content+'</div></div>';
}
repeats=function(c,key,labels){
 if(key==='relationships')labels=['Linked Character','Name','Relationship Type','Status','Summary','Notes'];
 if(key==='events')labels=['Event Name','When Type','When','End','Event Type','Importance','Notes'];
 return '<div class="section-header"><div><h2>'+esc(profileTab)+'</h2><p class="sub">'+(key==='events'?'Add dated or undated events. Drag-style ordering is available with the arrows; Zoom changes the spacing.':key==='relationships'?'Link another character record or document an unlinked person.':'Record any number of powers and abilities independently.')+'</p></div><div class="row">'+(key==='events'?button('Zoom −','indexTimelineZoom(-1)')+button('Zoom +','indexTimelineZoom(1)'):'')+button('+ Add '+(key==='powers'?'Power':key==='events'?'Event':'Relationship'),"addRepeat('"+esc(c.id)+"','"+key+"')",'primary')+'</div></div><div class="'+(key==='events'?'timeline-list':'repeats-grid')+'" style="--timeline-zoom:'+INDEX_ZOOM+'">'+(c[key]||[]).map((item,i)=>indexRepeatCard(c,key,item,i,labels)).join('')+'</div>';
};
async function indexMoveEvent(id,i,delta){const c=db.characters.find(x=>x.id===id);if(!c?.events)return;const j=i+delta;if(j<0||j>=c.events.length)return;indexRemember();[c.events[i],c.events[j]]=[c.events[j],c.events[i]];await commit()}
function indexTimelineZoom(n){INDEX_ZOOM=Math.max(.7,Math.min(1.6,INDEX_ZOOM+n*.1));render()}
const indexOriginalProfileContent=profileContent;
profileContent=function(c){
 if(profileTab==='Overview')return '<div class="section-header"><h2>Overview</h2>'+button('↶ Undo','indexUndo()')+'</div><p class="sub">Changes save automatically. Field locks and individual randomizers are available next to supported fields.</p>'+standardFields(c,'Overview');
 if(profileTab==='Notes')return '<div class="section-header"><h2>Notes & Aesthetics</h2>'+button('↶ Undo','indexUndo()')+'</div>'+standardFields(c,'Notes')+'<div class="panel"><div class="section-header"><h3>Mood Board Images</h3>'+button('+ Add Reference',"indexAddMood('"+esc(c.id)+"')",'primary')+'</div><div class="grid">'+(c.moodImages||[]).map((src,i)=>'<div class="panel">'+img(src,'cover')+button('Remove',"indexRemoveMood('"+esc(c.id)+"',"+i+")")+'</div>').join('')+'</div></div>';
 return indexOriginalProfileContent(c);
};
async function indexAddMood(id){const src=await api.chooseImage?.();if(!src)return;const c=db.characters.find(x=>x.id===id);indexRemember();c.moodImages??=[];c.moodImages.push(src);await commit()}
async function indexRemoveMood(id,i){const c=db.characters.find(x=>x.id===id);indexRemember();c.moodImages.splice(i,1);await commit()}
