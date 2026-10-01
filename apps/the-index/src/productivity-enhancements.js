/* The Index: final dashboard, characters library and productivity behavior. */
let INDEX_PINNED_ONLY=false,INDEX_CHARACTER_SORT='recent';
const indexOldGo=go;
go=function(name){window.searchText='';INDEX_CATEGORY='All';INDEX_NOTE_CATEGORY='All';INDEX_TAG_CATEGORY='All';INDEX_PINNED_ONLY=false;return indexOldGo(name)};
const indexTileBeforePins=characterTile;
characterTile=function(c){let html=indexTileBeforePins(c);if(c.pinned)html=html.replace('</button>','<span class="pin-star" title="Pinned character">★</span></button>');return html};
async function indexTogglePin(id){const c=db.characters.find(x=>x.id===id);if(!c)return;indexRemember();c.pinned=!c.pinned;c.updated=Date.now();await commit()}
function indexCharacterSort(v){INDEX_CHARACTER_SORT=v;render()}
function indexPinnedFilter(){INDEX_PINNED_ONLY=!INDEX_PINNED_ONLY;render()}
const indexCharactersBeforePins=characters;
characters=function(){
 const original=db.characters;
 const sorted=[...original].sort((a,b)=>INDEX_CHARACTER_SORT==='name'?String(a.name).localeCompare(String(b.name)):INDEX_CHARACTER_SORT==='oldest'?(a.created||0)-(b.created||0):(b.updated||b.created||0)-(a.updated||a.created||0));
 db.characters=INDEX_PINNED_ONLY?sorted.filter(x=>x.pinned):sorted;
 let output;
 try{output=indexCharactersBeforePins()}finally{db.characters=original}
 const select='<select onchange="indexCharacterSort(this.value)"><option value="recent" '+(INDEX_CHARACTER_SORT==='recent'?'selected':'')+'>Recently Edited</option><option value="name" '+(INDEX_CHARACTER_SORT==='name'?'selected':'')+'>Name A–Z</option><option value="oldest" '+(INDEX_CHARACTER_SORT==='oldest'?'selected':'')+'>Oldest First</option></select>';
 const action=button(INDEX_PINNED_ONLY?'★ Pinned Only ✓':'★ Pinned Only','indexPinnedFilter()',INDEX_PINNED_ONLY?'active':'');
 output=output.replace('</div><div class="columns">',select+action+'</div><div class="columns">');
 const c=original.find(x=>x.id===selectedId)||sorted[0];
 if(c){const marker=button(c.pinned?'Unpin':'Pin Character',"indexTogglePin('"+esc(c.id)+"')");
 const duplicate=button('Duplicate',"duplicateCharacter('"+esc(c.id)+"')");
 output=output.replace(duplicate,duplicate+marker)}
 return output;
};
const indexDashboardBeforePins=dashboard;
dashboard=function(){
 const basic=indexDashboardBeforePins();
 const pinned=db.characters.filter(c=>c.pinned).slice(0,6);
 const pinnedHtml='<div class="panel" style="margin-top:14px"><div class="section-header"><h2>Pinned Characters</h2>'+button('Open Characters',"go('Characters')")+'</div>'+(pinned.length?'<div class="grid">'+pinned.map(characterTile).join('')+'</div>':'<p class="sub">Pin characters from the Characters Library to keep them here.</p>')+'</div>';
 const counts='<div class="panel" style="margin-top:14px"><h3>Workspace</h3><div class="toolbar">'+pill('Stories: '+db.stories.length)+pill('World Entries: '+db.worldbuilding.length)+pill('Notebook Notes: '+db.notes.length)+pill('Tags: '+db.tags.length)+'</div></div>';
 return (basic+pinnedHtml).replace(/onclick="pickCharacter\('/g,'onclick="openProfile(\'')+counts;
};
const indexProfileBeforePins=profile;
profile=function(){const basic=indexProfileBeforePins();if(!profileId)return basic;const c=db.characters.find(x=>x.id===profileId);if(!c)return basic;const marker=button(c.pinned?'★ Unpin Character':'☆ Pin Character',"indexTogglePin('"+esc(c.id)+"')");
 return basic.replace(button('Duplicate',"duplicateCharacter('"+esc(c.id)+"')"),button('Duplicate',"duplicateCharacter('"+esc(c.id)+"')")+marker)};
const indexSettingsSaveBeforeRestart=saveSetting;
saveSetting=async function(k,v){await indexSettingsSaveBeforeRestart(k,v);if(k==='customFrame'&&api.restartApp){toast('Applying window frame preference…');setTimeout(()=>api.restartApp(),450)}};

let INDEX_CLICK_AUDIO=null;
document.addEventListener('click',event=>{
 if(!db?.settings?.sounds||!event.target.closest('button'))return;
 try{const Sound=window.AudioContext||window.webkitAudioContext;if(!Sound)return;INDEX_CLICK_AUDIO??=new Sound();const osc=INDEX_CLICK_AUDIO.createOscillator(),gain=INDEX_CLICK_AUDIO.createGain();osc.type='sine';osc.frequency.value=610;gain.gain.value=.008;osc.connect(gain).connect(INDEX_CLICK_AUDIO.destination);const t=INDEX_CLICK_AUDIO.currentTime;osc.start(t);osc.stop(t+.025)}catch{}
});

async function indexSetProgress(id,value){
 const c=db.characters.find(x=>x.id===id);
 if(!c||!['Existing','In Progress','Blank'].includes(value))return;
 indexRemember();c.status=value;c.updated=Date.now();await commit();
}
const indexProfileBeforeProgress=profile;
profile=function(){
 const html=indexProfileBeforeProgress();
 if(!profileId)return html;
 const c=db.characters.find(x=>x.id===profileId);if(!c)return html;
 const progress='<label class="profile-progress">Profile Progress <select aria-label="Profile progress" onchange="indexSetProgress(\''+esc(c.id)+'\',this.value)">'+['Blank','In Progress','Existing'].map(v=>'<option '+(c.status===v?'selected':'')+'>'+v+'</option>').join('')+'</select></label>';
 return html.replace('<div class="section-tabs">',progress+'<div class="section-tabs">');
};
