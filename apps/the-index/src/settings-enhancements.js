/* The Index: appearance, productivity, backups and settings. */
const INDEX_DEFAULT_SHORTCUTS={save:'Ctrl+S',new:'Ctrl+N',search:'Ctrl+F',undo:'Ctrl+Z',print:'Ctrl+P',backup:'Ctrl+Shift+B'};
let INDEX_THEME_CSS=false;
function indexTheme(){
 const config=db.settings||{};
 const themes={
  Forest:{background:'#f9f6ef',surface:'#fffcf8',foreground:'#17382b',sidebar:'#0a2e23',border:'#e6dfd1',muted:'#84948d'},
  Nocturne:{background:'#171b1a',surface:'#242a27',foreground:'#f2eee4',sidebar:'#0b1412',border:'#46544c',muted:'#adb4a9'},
  Parchment:{background:'#f1e3c7',surface:'#fff3db',foreground:'#513d2a',sidebar:'#53412e',border:'#d9c49c',muted:'#836e56'}
 };
 const t=themes[config.theme]||themes.Forest;const s=document.documentElement.style;
 s.setProperty('--cream',t.background);s.setProperty('--surface',t.surface);s.setProperty('--green',config.accent||t.sidebar);s.setProperty('--border',t.border);s.setProperty('--text',t.foreground);s.setProperty('--muted',t.muted);
 document.body.dataset.theme=config.theme||'Forest';
 document.body.dataset.size=config.scale||'Medium';
 document.body.dataset.font=config.font||'Typewriter';
 document.body.classList.toggle('compact-sidebar',Boolean(config.compactSidebar));
 document.body.classList.toggle('without-pictures',config.portraits===false);
 document.body.classList.toggle('no-animations',config.animations===false);
 document.body.classList.toggle('no-backdrops',config.backgroundImages===false);
 document.body.classList.toggle('custom-frame',Boolean(config.customFrame));
 document.body.style.fontFamily=config.font==='Georgia'?'Georgia,serif':config.font==='Courier New'?'Courier New,monospace':'Courier New,monospace';
 document.body.style.fontSize=config.scale==='Small'?'12px':config.scale==='Large'?'16px':'14px';
}
const indexOldRender=render;
render=function(){indexOldRender();indexTheme()};
const indexOldSaveSetting=saveSetting;
saveSetting=async function(k,v){db.settings[k]=v;await api.save(db);render();toast('Setting saved')};
function indexSettingRow(label,desc,inner){return '<div class="setting-row"><div><b>'+esc(label)+'</b><div class="sub">'+esc(desc||'')+'</div></div>'+inner+'</div>'}
function indexRangeSetting(label,key,min,max,step){let v=Number(db.settings[key]||min);return indexSettingRow(label,'Current: '+v,'<input type="range" min="'+min+'" max="'+max+'" step="'+step+'" value="'+v+'" oninput="document.getElementById('+"'val-"+key+"'"+').textContent=this.value" onchange="saveSetting('+"'"+key+"'"+',Number(this.value))"><span id="val-'+key+'">'+v+'</span>')}
function indexSettingShortcuts(){
 db.settings.shortcuts??={...INDEX_DEFAULT_SHORTCUTS};
 return '<p class="sub">Click a shortcut field and press the combination you prefer. Escape cancels; each action must have a unique combination.</p>'+Object.entries(INDEX_DEFAULT_SHORTCUTS).map(([key,defaultValue])=>indexSettingRow(key[0].toUpperCase()+key.slice(1),'Default: '+defaultValue,'<input readonly class="shortcut-input" value="'+esc(db.settings.shortcuts[key]||defaultValue)+'" onkeydown="indexCaptureShortcut(event,'+"'"+key+"'"+')" placeholder="Press keys...">')).join('')+button('Restore Defaults','indexResetShortcuts()');
}
function indexCaptureShortcut(event,key){event.preventDefault();if(event.key==='Escape')return event.target.blur();if(['Control','Alt','Meta','Shift'].includes(event.key))return;const mods=[event.ctrlKey?'Ctrl':'',event.altKey?'Alt':'',event.shiftKey?'Shift':''].filter(Boolean);if(!mods.length)return toast('Include Ctrl, Alt or Shift');const value=mods.concat(event.key.length===1?event.key.toUpperCase():event.key).join('+');const shortcuts=db.settings.shortcuts||{};if(Object.entries(shortcuts).some(([k,v])=>k!==key&&v===value))return toast('Already assigned to another action');shortcuts[key]=value;db.settings.shortcuts=shortcuts;api.save(db);event.target.value=value;event.target.blur();}
async function indexResetShortcuts(){db.settings.shortcuts={...INDEX_DEFAULT_SHORTCUTS};await commit()}
document.addEventListener('keydown',function(e){if(!db?.settings)return;const combo=[e.ctrlKey?'Ctrl':'',e.altKey?'Alt':'',e.shiftKey?'Shift':''].filter(Boolean).concat(e.key.length===1?e.key.toUpperCase():e.key).join('+');if(!combo)return;const shortcuts={...INDEX_DEFAULT_SHORTCUTS,...db.settings.shortcuts};for(const [k,v] of Object.entries(shortcuts)){if(v!==combo)continue;e.preventDefault();if(k==='save'){indexCommitEditor?.();api.save(db).then(()=>toast('Archive saved'))}else if(k==='new'){if(section==='Notebook')indexNewNote();else if(section==='Stories')addCollection('stories');else if(section==='Worldbuilding')addCollection('worldbuilding');else addCharacter()}else if(k==='search'){document.querySelector('.search')?.focus()}else if(k==='undo'){if(document.activeElement?.isContentEditable||['INPUT','TEXTAREA'].includes(document.activeElement?.tagName)){document.execCommand('undo');}else indexUndo()}else if(k==='print'){api.exportPDF?.({type:profileId?'character':section==='Notebook'?'note':'archive',id:profileId||noteId}).catch(err=>toast(err.message))}else if(k==='backup')backupNow();break}});
function indexSettingPDF(){return indexSettingRow('Export to PDF','Save your archive or current record to a PDF.',button('Export to PDF','indexExportPDF()','primary'))}
async function indexExportPDF(){try{const type=profileId?'character':section==='Notebook'?'note':'archive';const id=profileId||noteId||null;let path=await api.exportPDF?.({type,id});if(path)toast('PDF saved: '+path);else if(!api.exportPDF)toast('PDF exporting is unavailable in this build')}catch(e){toast('PDF export failed: '+e.message)}}
function indexSettingBody(){
 switch(settingsTab){
 case 'Appearance':
  return '<div class="cards-3">'+['Forest','Nocturne','Parchment'].map(t=>'<button class="panel click theme-card" onclick="saveSetting('+"'theme','"+t+"'"+')"><div class="theme-strip theme-'+t.toLowerCase()+'"></div><h3>'+t+' '+(db.settings.theme===t?'✓':'')+'</h3></button>').join('')+'</div><h3>Accent Colors</h3><div class="toolbar">'+['#12392c','#853a3c','#730b0e','#112c62','#51265f','#704521','#58653b','#929292','#222222','#d0a74f'].map(c=>'<button title="'+c+'" aria-label="'+c+'" onclick="saveSetting('+"'accent','"+c+"'"+')" class="color-choice '+(db.settings.accent===c?'chosen':'')+'" style="background:'+c+'"></button>').join('')+'</div>'+settingSelect('Font','font',['Typewriter','Courier New','Georgia'])+settingSelect('Interface Size','scale',['Small','Medium','Large'])+settingCheck('Show background images','backgroundImages')+settingCheck('Use custom window frame','customFrame')+settingCheck('Enable subtle animations','animations')+settingCheck('Show character portraits','portraits')+settingCheck('Compact sidebar','compactSidebar')+settingCheck('Enable sound effects','sounds');
 case 'Writing':
  return '<p class="sub">Configure the writing experience in the Notebook and story editors.</p>'+settingCheck('Enable spellcheck','spellcheck')+settingCheck('Show live word count','wordCount')+settingCheck('Restore previous note on launch','restoreNote')+settingSelect('Default note category','defaultNoteCategory',['General','Character','Story','Worldbuilding','Research','Idea','Writing','Lore','Timeline','Other'])+indexRangeSetting('Editor line spacing','lineSpacing',1,2,0.1);
 case 'Data & Storage':
  return '<p>Character data is stored outside the application installation, so updating the program preserves your records.</p>'+indexSettingRow('Current data directory','Change the folder used for The Index’s database and media.',button('Choose Folder','indexMoveFolder()')+' '+button('Open Data Folder','openFolder()'))+'<p class="sub">Changing folders copies the current archive to the new location and restarts the application.</p>';
 case 'Backups':
  return '<p>Backups save a dated copy of your entire character and story database.</p>'+indexSettingRow('Create a backup','Backups are stored in the app data directory.',button('Create Backup Now','backupNow()','primary')+' '+button('View Backups','indexViewBackups()'))+settingCheck('Remind me to back up','backupReminder')+settingSelect('Backup reminder frequency','backupFrequency',['Daily','Weekly','Monthly']);
 case 'Updates':
  return '<p>Independent The Index update channel: <code>VeyrStudio/DesktopAppUpdates/the-index/latest.json</code>.</p>'+settingCheck('Automatically check for updates','autoUpdates')+settingCheck('Download updates in background','backgroundDownloads')+settingCheck('Notify me when an update is available','updateAlerts')+button('Check for Updates','checkUpdate()','primary')+'<p class="sub">Update packages are checked against their published SHA-256 checksum before installation.</p>';
 case 'Import / Export':
  return indexSettingRow('Export Data','Save a full JSON archive.',button('Export Data','exportData()','primary'))+indexSettingRow('Import Data','Replaces the current archive after first creating a backup.',button('Import Data','importData()'))+indexSettingPDF();
 case 'Shortcuts':return indexSettingShortcuts();
 case 'Security':
  return '<p class="sub">The Index stores records locally. A convenience screen lock can prevent casual viewing while the app is open. It is not file encryption.</p>'+settingCheck('Show confirmation before destructive actions','confirmDelete')+settingCheck('Hide story spoilers in library previews','hideSpoilers')+indexSettingRow('Lock The Index','Restrict viewing until the current session is unlocked.',button('Lock Now','indexLockNow()','primary'));
 case 'About':
  return '<h2>The Index</h2><p>A private Windows character archive in the Ledgerly-inspired style.</p><p>Version: <b id="index-version">Loading…</b></p><p>Developer: VeyrStudio</p><p>GitHub update channel: <code>the-index</code></p>';
 }
 return '<p class="sub">No settings in this category.</p>';
}
settingsBody=indexSettingBody;
const indexOldSettings=settings;
settings=function(){const html=indexOldSettings();setTimeout(()=>api.version?.().then(v=>{const el=document.getElementById('index-version');if(el)el.textContent=v}),0);return html};
async function indexMoveFolder(){try{const folder=await api.changeDataFolder?.();if(folder)toast('Data moved to '+folder)}catch(e){toast('Could not change data folder: '+e.message)}}
async function indexViewBackups(){try{await api.openBackups?.()}catch(e){toast(e.message)}}
function indexLockNow(){const pin=prompt('Choose a temporary PIN for this session (at least 4 characters):');if(pin===null)return;if(pin.length<4)return toast('Use at least 4 characters');sessionStorage.setItem('the-index-lock-pin',pin);indexShowLock()}
function indexShowLock(){let overlay=document.getElementById('index-lock-screen');if(!overlay){overlay=document.createElement('div');overlay.id='index-lock-screen';document.body.appendChild(overlay)}overlay.innerHTML='<div class="panel lock-panel"><h1>The Index</h1><p>Archive locked</p><input type="password" id="index-lock-input" placeholder="Session PIN"><button class="btn primary" id="index-unlock">Unlock</button><p class="sub" id="index-lock-hint">Convenience lock only; files are not encrypted.</p></div>';document.getElementById('index-unlock').addEventListener('click',()=>{if(document.getElementById('index-lock-input').value===sessionStorage.getItem('the-index-lock-pin')){overlay.remove();sessionStorage.removeItem('the-index-lock-pin')}else document.getElementById('index-lock-hint').textContent='Incorrect PIN'});document.getElementById('index-lock-input').focus()}
const indexOldStart=start;
start=async function(){await indexOldStart();if(!db.settings.shortcuts)db.settings.shortcuts={...INDEX_DEFAULT_SHORTCUTS};if(db.settings.lineSpacing==null)db.settings.lineSpacing=1.6;if(db.settings.confirmDelete==null)db.settings.confirmDelete=true;indexTheme();if(sessionStorage.getItem('the-index-lock-pin'))indexShowLock()};
const indexOldDeleteCharacter=deleteCharacter;
deleteCharacter=async function(id){if(db.settings.confirmDelete===false){db.characters=db.characters.filter(x=>x.id!==id);profileId=null;await commit();return;}return indexOldDeleteCharacter(id)};
