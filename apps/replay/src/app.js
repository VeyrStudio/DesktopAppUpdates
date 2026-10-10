const $=s=>document.querySelector(s),escape=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));let data={folders:[],items:[],settings:{}},view='dashboard',folder='',kind='videos',group='fandom',size=170,filter='',sort='custom',initialLoad=true;const sections=[['dashboard','▣ Dashboard'],['videos','▷ Videos'],['images','▧ Images'],['gifs','◇ GIFs'],['favorites','♡ Favorites'],['trash','♧ Trash']];const folderOf=id=>data.folders.find(x=>x.id===id);const activeItems=()=>data.items.filter(x=>!x.deletedAt&&x.kind===kind&&(!folder||x.folder===folder||(x.fandoms||[]).includes(folder)));const redraw=async()=>{data=await replay.state();size=data.settings.thumbnailSize||170;if(initialLoad){initialLoad=false;if(data.settings.launch==='last'&&sections.some(([k])=>k===data.settings.lastView))view=data.settings.lastView}render()};function nav(){ $('#nav').innerHTML=sections.map(([key,label])=>'<button data-view="'+key+'" class="'+(view===key?'active':'')+'">'+label+'</button>').join('');$('#nav').querySelectorAll('button').forEach(b=>b.onclick=()=>{view=b.dataset.view;folder='';filter='';replay.settings({lastView:view});render()})}function header(t,s){$('#heading').textContent=t;$('#subheading').textContent=s}function foldersFor(){return data.folders.filter(f=>f.kind===kind&&f.group==='fandom'&&(filter?f.name.toLowerCase().includes(filter.toLowerCase()):f.parent===folder)).sort((a,b)=>(a.order||0)-(b.order||0))}function tile(item){const video=item.kind==='videos',gif=item.kind==='gifs';return '<div class="tile '+(item.favorite?'favorite':'')+'" draggable="true" data-item="'+item.id+'"><div class="thumb">'+(video?'<video muted playsinline loop preload="none" data-preview-id="'+item.id+'"></video>':'<img loading="lazy" src="replay://media/'+item.id+'">')+'</div><div class="name">'+escape(item.name)+'</div><div class="row"><button class="move-media" title="Move to folder or General">Move</button><button class="fav" title="Favorite">'+(item.favorite?'♥':'♡')+'</button><button class="delete" title="Move to trash">⌫</button></div></div>'}
let replayPreviewObserver;
function replayPreparePreviews(container){
 if(replayPreviewObserver)replayPreviewObserver.disconnect();
 const videos=[...container.querySelectorAll('video[data-preview-id]')];
 let queue=[],active=0;
 const pump=()=>{
  while(active<2&&queue.length){
   const video=queue.shift();
   if(!video.isConnected||video.dataset.started)continue;
   video.dataset.started='1';active++;
   const finish=()=>{active--;pump()};
   video.addEventListener('loadeddata',finish,{once:true});
   video.addEventListener('error',finish,{once:true});
   video.src='replay://media/'+video.dataset.previewId;
   video.load();
  }
 };
 replayPreviewObserver=new IntersectionObserver(entries=>{
  for(const entry of entries)if(entry.isIntersecting&&!entry.target.dataset.started){
   queue.push(entry.target);replayPreviewObserver.unobserve(entry.target);
  }
  pump();
 },{rootMargin:'80px'});
 videos.forEach(video=>replayPreviewObserver.observe(video));
}
function folderIconMarkup(f){return f.iconImage?'<img alt="" style="width:90%;height:90%;object-fit:contain" src="'+escape(f.iconImage)+'">':'<span class="folder-icon">'+escape(f.icon||'▤')+'</span>'}
async function customizeFolder(id){
 const f=folderOf(id);if(!f)return;document.querySelector('#folder-editor')?.remove();
 const panel=document.createElement('form');panel.id='folder-editor';panel.className='panel';
 const options=data.folders.filter(x=>x.id!==id&&x.kind===f.kind&&x.group===f.group);
 const inputField=(label,name,value,type='text')=>'<label class="folder-field"><span>'+label+'</span><input type="'+type+'" name="'+name+'" value="'+escape(value||'')+'"></label>';
 panel.innerHTML='<h2>Customize Folder: '+escape(f.name)+'</h2><label>Name <input name="name" required maxlength="90" value="'+escape(f.name)+'"></label><label>Color <input type="color" name="color" value="'+escape(/^#[0-9a-f]{6}$/i.test(f.color||'')?f.color:'#b58a48')+'"></label><div class="row"><button type="button" id="choose-icon">Upload Custom Icon</button><button type="button" id="remove-icon">Remove Icon</button><span id="icon-status">'+(f.iconImage?'Custom icon selected':'Default icon')+'</span></div><label><input type="checkbox" name="subfolder" '+(f.isSubfolder?'checked':'')+'> This is a subfolder</label><label><input type="checkbox" name="showInfoCard" '+(f.showInfoCard===true?'checked':'')+'> Show Information Card</label><label><input type="checkbox" name="autoNumberMedia" '+(f.autoNumberMedia===true?'checked':'')+'> Automatically name and number files in this folder (including existing files when first enabled)</label><label><input type="checkbox" name="numberExisting" checked> Renumber all files already in this folder again</label><label>Parent folder <select name="parent"><option value="">Library root</option>'+options.map(x=>'<option value="'+x.id+'" '+(f.parent===x.id?'selected':'')+'>'+escape(x.name)+'</option>').join('')+'</select></label><h3 class="folder-section-title">Folder Information</h3><div class="folder-form-fields"><label class="folder-field"><span>Main pairing(s)</span><textarea name="pairings">'+escape(f.details?.pairings||'')+'</textarea></label><label class="folder-field"><span>Ship Name (optional)</span><input name="shipName" value="'+escape(f.details?.shipName||'')+'"></label><div class="folder-field"><span>Media source</span><div class="folder-checks">'+['Book','TV Show','Movie'].map(x=>'<label><input name="source" type="checkbox" value="'+x+'" '+((f.details?.sources||[]).includes(x)?'checked':'')+'> '+x+'</label>').join(' ')+'</div></div><label class="folder-field"><span>Category</span><select name="category">'+['','M/M','M/F','Platonic','No Relationship'].map(x=>'<option value="'+x+'" '+(f.details?.category===x?'selected':'')+'>'+escape(x||'Not selected')+'</option>').join('')+'</select></label><label class="folder-field"><span>AO3 link</span><input name="ao3" type="url" placeholder="https://archiveofourown.org/..." value="'+escape(f.details?.ao3||'')+'"></label></div><div class="row"><button type="submit" class="primary">Save Folder</button><button type="button" id="cancel-folder">Cancel</button></div>';
 document.querySelector('#content').prepend(panel);let iconImage=f.iconImage||'';
 panel.querySelector('#choose-icon').onclick=async()=>{try{const i=await replay.chooseFolderIcon();if(i){iconImage=i;panel.querySelector('#icon-status').textContent='Custom icon selected'}}catch(e){alert(e.message)}};
 panel.querySelector('#remove-icon').onclick=()=>{iconImage='';panel.querySelector('#icon-status').textContent='Default icon'};
 panel.querySelector('#cancel-folder').onclick=()=>panel.remove();
 panel.onsubmit=async e=>{e.preventDefault();const v=new FormData(panel),button=panel.querySelector('[type="submit"]');button.disabled=true;try{await replay.folderUpdate(id,{name:v.get('name'),color:v.get('color'),iconImage,isSubfolder:v.has('subfolder'),showInfoCard:v.has('showInfoCard'),autoNumberMedia:v.has('autoNumberMedia'),numberExisting:v.has('numberExisting'),parent:v.get('parent'),details:{pairings:v.get('pairings'),shipName:v.get('shipName'),sources:v.getAll('source'),category:v.get('category'),ao3:v.get('ao3')}});await redraw()}catch(err){button.disabled=false;alert(err.message)}};
 panel.scrollIntoView({block:'start'});
}
function showSubfolderInfo(){
 document.querySelector('#subfolder-information')?.remove();
 const f=folderOf(folder);
 if(!f||f.showInfoCard!==true)return; // Folder info card is optional, independent of subfolder status.
 const d=f.details||{},panel=document.createElement('section');
 panel.id='subfolder-information';
 panel.className='subfolder-info-card';
 const section=(label,value)=>'<div class="subfolder-info-field"><div class="subfolder-info-label">'+label+'</div><div class="subfolder-info-value">'+escape(value||'Not specified')+'</div></div>';
 panel.innerHTML='<div class="subfolder-info-heading"><div><div class="subfolder-info-eyebrow">REPLAY COLLECTION</div><h3>Folder Information</h3></div><button type="button" id="edit-subfolder" title="Edit information">Edit ✎</button></div>'+section('MAIN PAIRING(S)',d.pairings)+(d.shipName?section('SHIP NAME',d.shipName):'')+section('MEDIA SOURCE',(d.sources||[]).join(' · '))+section('RELATIONSHIP',d.category)+(d.ao3?'<button type="button" class="subfolder-ao3" id="subfolder-ao3">AO3 ↗</button>':'');
 const gallery=document.querySelector('#gallery');
 if(!gallery)return;
 const layout=document.createElement('div');layout.className='media-with-information';gallery.before(layout);layout.append(gallery,panel); // Info card sits beside, not above, the media grid.
 panel.querySelector('#edit-subfolder').onclick=()=>customizeFolder(f.id);
 panel.querySelector('#subfolder-ao3')?.addEventListener('click',()=>replay.openAO3(d.ao3).catch(e=>alert(e.message)));
}

const selectedMedia=new Set();let selectionAnchor='';
function visibleMediaIds(){return [...document.querySelectorAll('#gallery [data-item]')].map(e=>e.dataset.item)}
function selectionUI(){
 const visible=new Set(visibleMediaIds());
 for(const id of [...selectedMedia])if(!visible.has(id))selectedMedia.delete(id);
 document.querySelectorAll('#gallery [data-item]').forEach(e=>{const chosen=selectedMedia.has(e.dataset.item);e.classList.toggle('bulk-selected',chosen);e.setAttribute('aria-selected',String(chosen))});
 const bar=document.querySelector('#bulk-selection');
 if(bar){bar.querySelector('#selection-count').textContent=selectedMedia.size+' selected';bar.querySelector('#move-selected').disabled=!selectedMedia.size;bar.querySelector('#clear-selected').disabled=!selectedMedia.size;bar.querySelector('#select-all').disabled=!visible.size}
}
function selectMedia(event,id){
 const ids=visibleMediaIds();
 if(event.shiftKey&&selectionAnchor&&ids.includes(selectionAnchor)){
  const a=ids.indexOf(selectionAnchor),b=ids.indexOf(id);
  if(!event.ctrlKey&&!event.metaKey)selectedMedia.clear();
  for(const key of ids.slice(Math.min(a,b),Math.max(a,b)+1))selectedMedia.add(key);
 }else if(event.ctrlKey||event.metaKey){if(selectedMedia.has(id))selectedMedia.delete(id);else selectedMedia.add(id);selectionAnchor=id}
 else if(selectedMedia.size){if(selectedMedia.has(id))selectedMedia.delete(id);else selectedMedia.add(id);selectionAnchor=id}else{selectedMedia.clear();selectedMedia.add(id);selectionAnchor=id}
 selectionUI();
}
async function moveMediaBatch(ids,targetFolder,targetGroup){
 const destination=targetFolder?folderOf(targetFolder):null;
 const unique=[...new Set(ids)].filter(id=>data.items.some(it=>it.id===id&&!it.deletedAt));
 if(destination&&unique.some(id=>data.items.find(x=>x.id===id).kind!==destination.kind))throw Error('This destination cannot hold the selected media.');
 let moved=0,errors=[];
 for(const id of unique){try{await replay.itemUpdate(id,{folder:destination?.id||'',group:destination?.group||targetGroup||'fandom',fandoms:[]});moved++}catch(e){errors.push(e.message)}}
 selectedMedia.clear();selectionAnchor='';await redraw();
 if(errors.length)alert(moved+' moved; '+errors.length+' failed. '+errors[0]);
}
function cards(){const folders=foldersFor();let items=activeItems().filter(x=>x.name&&x.folder===(folder||''));if(filter)items=[];if(filter)items=[];if(sort==='added')items.sort((a,b)=>b.added-a.added);else if(sort==='name')items.sort((a,b)=>a.name.localeCompare(b.name));else if(sort==='name-desc')items.sort((a,b)=>b.name.localeCompare(a.name));else if(sort==='file-date')items.sort((a,b)=>(b.modified||b.added)-(a.modified||a.added));else if(sort==='file-date-old')items.sort((a,b)=>(a.modified||a.added)-(b.modified||b.added));else items.sort((a,b)=>a.order-b.order);$('#gallery').classList.toggle('folder-icons',data.settings.folderView==='icons');$('#gallery').innerHTML=folders.map(f=>'<div draggable="true" class="tile" data-folder="'+f.id+'" style="border-color:'+escape(f.color||'#b58a48')+'"><div class="thumb">'+folderIconMarkup(f)+'</div><div class="name">'+escape(f.name)+'</div><button class="edit-folder" data-edit-folder="'+f.id+'">Customize</button></div>').join('')+items.map(tile).join('');selectionUI();replayPreparePreviews($('#gallery'));$('#gallery').querySelectorAll('[data-edit-folder]').forEach(b=>{b.onclick=e=>{e.stopPropagation();customizeFolder(b.dataset.editFolder)};b.ondblclick=e=>e.stopPropagation()});$('#gallery').querySelectorAll('[data-folder]').forEach(e=>{e.ondblclick=()=>{folder=e.dataset.folder;render()};e.ondragstart=event=>{event.dataTransfer.setData('text/replay-folder',e.dataset.folder)};e.ondragover=event=>{if(event.dataTransfer.types.includes('text/replay-item'))event.preventDefault()};e.ondrop=async event=>{const folderId=event.dataTransfer.getData('text/replay-folder');if(folderId&&folderId!==e.dataset.folder){event.preventDefault();const order=foldersFor().map(f=>f.id),from=order.indexOf(folderId),to=order.indexOf(e.dataset.folder);if(from>=0&&to>=0){order.splice(from,1);order.splice(to,0,folderId);for(let n=0;n<order.length;n++)await replay.folderUpdate(order[n],{order:n});await redraw()}return}const id=event.dataTransfer.getData('text/replay-item');if(!id)return;event.preventDefault();const target=folderOf(e.dataset.folder);try{await moveMediaBatch(window.replayDragIds?.includes(id)?window.replayDragIds:[id],target.id,target.group)}catch(error){alert(error.message)}};e.oncontextmenu=async event=>{event.preventDefault();const id=e.dataset.folder;const current=folderOf(id);const choice=prompt('Folder action: rename, pin, color, icon, cover, move, delete, or unpin','rename');if(!choice)return;try{if(choice==='rename'){const name=prompt('New name',current.name);if(name?.trim())await replay.folderUpdate(id,{name:name.trim()})}else if(choice==='pin'||choice==='unpin')await replay.folderUpdate(id,{pinned:choice==='pin'});else if(choice==='color'){const color=prompt('Hex color, e.g. #b58a48',current.color);if(/^#[0-9a-f]{6}$/i.test(color||''))await replay.folderUpdate(id,{color})}else if(choice==='icon'){const icon=prompt('Folder symbol (up to 3 characters)',current.icon||'▤');if(icon)await replay.folderUpdate(id,{icon:icon.slice(0,3)})}else if(choice==='cover'){const options=data.items.filter(x=>x.kind==='images'&&!x.deletedAt);const selected=prompt('Cover image ID (blank clears)\n'+options.map(x=>x.name+' ['+x.id+']').join('\n'),current.cover||'');if(selected!==null&&(selected===''||options.some(x=>x.id===selected)))await replay.folderUpdate(id,{cover:selected})}else if(choice==='move'){const dest=prompt('Parent folder ID (blank for library root)','');await replay.folderUpdate(id,{parent:dest||''})}else if(choice==='delete'){if(confirm('Delete folder? Media will be moved to its parent, not deleted.'))await replay.folderDelete(id)}await redraw()}catch(error){alert(error.message)}}});$('#gallery').querySelectorAll('[data-item]').forEach(e=>{e.ondragstart=event=>{const ids=selectedMedia.has(e.dataset.item)?[...selectedMedia]:[e.dataset.item];window.replayDragId=e.dataset.item;window.replayDragIds=ids;event.dataTransfer.effectAllowed='move';event.dataTransfer.setData('text/replay-item',e.dataset.item);event.dataTransfer.setData('text/replay-items',JSON.stringify(ids))};e.ondragover=event=>{if(event.dataTransfer.types.includes('text/replay-item'))event.preventDefault()};e.ondrop=async event=>{const dragged=event.dataTransfer.getData('text/replay-item');if(!dragged||dragged===e.dataset.item)return;event.preventDefault();const order=activeItems().filter(x=>x.group===group).sort((a,b)=>a.order-b.order).map(x=>x.id);const pos=order.indexOf(dragged),target=order.indexOf(e.dataset.item);if(pos<0||target<0)return;order.splice(pos,1);order.splice(target,0,dragged);for(let i=0;i<order.length;i++)await replay.itemUpdate(order[i],{order:i});await redraw()};let it=data.items.find(x=>x.id===e.dataset.item);e.oncontextmenu=async event=>{event.preventDefault();const choices=data.folders.filter(f=>f.kind===it.kind);const action=prompt('Item action: move, fandoms, or favorite','move');if(!action)return;try{if(action==='favorite')await replay.itemUpdate(it.id,{favorite:!it.favorite});else if(action==='move'){const destination=await moveMediaPicker(it,choices);if(destination){if(destination.trash)await replay.itemDelete(it.id);else await replay.itemUpdate(it.id,{folder:destination.folder,group:destination.group,fandoms:[]})}}else if(action==='fandoms'&&it.group==='fandom'){const fs=choices.filter(f=>f.group==='fandom');const raw=prompt('Extra fandom IDs, comma-separated\n'+fs.map(f=>f.name+' ['+f.id+']').join('\n'),(it.fandoms||[]).join(','));if(raw!==null)await replay.itemUpdate(it.id,{fandoms:raw.split(',').map(x=>x.trim()).filter(Boolean)})}await redraw()}catch(error){alert(error.message)}};e.querySelector('.move-media').onclick=async ev=>{ev.stopPropagation();try{const ids=selectedMedia.has(it.id)?[...selectedMedia]:[it.id];const destination=await moveMediaPicker(it,data.folders.filter(f=>f.kind===it.kind));if(destination){if(destination.trash){for(const id of ids)await replay.itemDelete(id);selectedMedia.clear();await redraw()}else await moveMediaBatch(ids,destination.folder,destination.group)}}catch(error){alert('Could not move media: '+error.message)}};e.querySelector('.fav').onclick=async ev=>{ev.stopPropagation();await replay.itemUpdate(it.id,{favorite:!it.favorite});redraw()};e.querySelector('.delete').onclick=async ev=>{ev.stopPropagation();if(confirm('Move to 30-day Trash?')){await replay.itemDelete(it.id);redraw()}};e.onclick=event=>{if(event.ctrlKey||event.metaKey||event.shiftKey||selectedMedia.size){selectMedia(event,it.id);return}openItem(it)};const v=e.querySelector('video');if(v){e.onmouseenter=async()=>{if(!$('#overlay').classList.contains('hidden'))return;v.dataset.hovered='1';v.muted=true;v.volume=0;v.loop=true;v.playbackRate=1;try{await v.play()}catch(error){if(v.dataset.hovered!=='1'||v.dataset.fallback==='1')return;v.dataset.fallback='1';try{const url=await replay.compatibleVideo(it.id);if(v.dataset.hovered==='1'){v.src=url;v.load();await v.play()}}catch(failure){console.warn('Thumbnail preview unavailable:',failure.message)}}};e.onmouseleave=()=>{v.dataset.hovered='0';v.muted=true;v.pause();try{v.currentTime=0}catch{}}}})}function gallery(){header(kind[0].toUpperCase()+kind.slice(1),'Your media collections');let crumbs=[];let cur=folder;while(cur){let f=folderOf(cur);if(!f)break;crumbs.unshift(f);cur=f.parent}$('#content').innerHTML='<div class="toolbar"><button id="add-media" class="primary">+ Add Media</button><button id="import-folder">Import Folder</button><button id="new-folder">+ New Folder</button><span class="spacer"></span><input id="search" placeholder="Search folders / fandoms" value="'+escape(filter)+'"></div><div class="toolbar"><button id="back">← Back</button><div class="crumb"><button id="root" title="Drop media here to move to library root">' + kind[0].toUpperCase()+kind.slice(1)+' — Root</button>'+crumbs.map(f=>' › <button class="pathcrumb" data-folder="'+f.id+'">'+escape(f.name)+'</button>').join('')+'</div><span class="spacer"></span><button id="toggle-view">Folder View</button><button id="small">Small</button><button id="medium">Medium</button><button id="large">Large</button><input id="size" type="range" min="90" max="250" value="'+size+'"><select id="sort"><option value="custom">Custom order</option><option value="added">Newest added</option><option value="name">Filename A–Z</option><option value="name-desc">Filename Z–A</option><option value="file-date">File date newest</option><option value="file-date-old">File date oldest</option></select></div><div class="toolbar" id="bulk-selection"><strong id="selection-count">0 selected</strong><button id="select-all">Select All</button><button id="move-selected" disabled>Move Selected</button><button id="clear-selected" disabled>Clear Selection</button></div><div class="grid" id="gallery" style="--tile:'+size+'px"></div>';$('#select-all').onclick=()=>{selectedMedia.clear();for(const id of visibleMediaIds())selectedMedia.add(id);selectionUI()};$('#clear-selected').onclick=()=>{selectedMedia.clear();selectionAnchor='';selectionUI()};$('#move-selected').onclick=async()=>{const ids=[...selectedMedia],item=data.items.find(x=>x.id===ids[0]);if(!item)return;const dest=await moveMediaPicker(item,data.folders.filter(f=>f.kind===item.kind));if(dest)try{if(dest.trash){for(const id of ids)await replay.itemDelete(id);selectedMedia.clear();await redraw()}else await moveMediaBatch(ids,dest.folder,dest.group)}catch(e){alert(e.message)}};$('#search').oninput=e=>{filter=e.target.value;cards()};$('#toggle-view').onclick=async()=>{const folderView=data.settings.folderView==='icons'?'cards':'icons';await replay.settings({folderView});data.settings.folderView=folderView;cards()};$('#add-media').onclick=()=>importMedia();$('#import-folder').onclick=async()=>{const paths=await replay.browseFolder();if(paths.length)await importMedia(paths)};$('#new-folder').onclick=createFolder;$('#back').onclick=()=>{folder=folderOf(folder)?.parent||'';render()};$('#root').onclick=()=>{folder='';render()};document.querySelectorAll('.pathcrumb').forEach(b=>b.onclick=()=>{folder=b.dataset.folder;render()});
 // Drag a media tile onto the General breadcrumb or an ancestor folder.
 const dropTargets=[document.querySelector('#root'),...document.querySelectorAll('.pathcrumb')];
 for(const target of dropTargets){
  target.ondragover=event=>{if(event.dataTransfer.types.includes('text/replay-item')){event.preventDefault();event.dataTransfer.dropEffect='move'}};
  target.ondrop=async event=>{const id=event.dataTransfer.getData('text/replay-item');if(!id)return;event.preventDefault();event.stopPropagation();const item=data.items.find(x=>x.id===id&&!x.deletedAt);if(!item)return;const targetFolder=target.dataset.folder||'';const destination=targetFolder?folderOf(targetFolder):null;if(destination&&destination.kind!==item.kind){alert('This folder cannot hold that media type');return}try{await moveMediaBatch(window.replayDragIds?.includes(id)?window.replayDragIds:[id],targetFolder,destination?.group||group)}catch(error){alert('Could not move media: '+error.message)}};
 }for(const [n,v] of [['small',110],['medium',170],['large',230]])$('#'+n).onclick=()=>resize(v);$('#size').oninput=e=>resize(+e.target.value);const sortKey=kind+':'+group+':'+folder;sort=data.settings.sortByFolder?.[sortKey]||'custom';showSubfolderInfo();$('#sort').value=sort;$('#sort').onchange=async e=>{sort=e.target.value;await replay.settings({sortByFolder:{...(data.settings.sortByFolder||{}),[sortKey]:sort}});cards()};cards()}async function resize(n){size=n;$('#gallery').style.setProperty('--tile',n+'px');$('#size').value=n;await replay.settings({thumbnailSize:n})}function render(){nav();if(view==='dashboard'){header('Dashboard','Your private collection');$('#content').innerHTML='<div class="panel"><h2>Pinned Collections</h2><div id="pinned-collections" class="grid"></div></div><div class="panel"><h2>Add Media</h2><p>Import videos, images and GIFs to your private library.</p><button id="add-media" class="primary">+ Add Media</button></div>';$('#add-media').onclick=importMedia;const pins=data.folders.filter(f=>f.pinned);$('#pinned-collections').innerHTML=pins.length?pins.map(f=>'<button data-pin="'+f.id+'">▤ '+escape(f.name)+'</button>').join(''):'<p>No pinned collections yet. Right-click a folder to pin it.</p>';$('#pinned-collections').querySelectorAll('[data-pin]').forEach(b=>b.onclick=()=>{const f=folderOf(b.dataset.pin);kind=f.kind;group=f.group;folder=f.id;view=f.kind;render()})}else if(['videos','images','gifs'].includes(view)){kind=view;group='fandom';gallery()}else if(view==='trash'){
 header('Trash','Recover files within 30 days, or permanently delete everything');
 const deleted=data.items.filter(x=>x.deletedAt).sort((a,b)=>b.deletedAt-a.deletedAt);
 $('#content').innerHTML='<div class="panel"><h2>Trash ('+deleted.length+')</h2><p>Files remain recoverable for 30 days unless permanently deleted. Delete All cannot be undone.</p><button id="delete-all-trash" class="primary" '+(!deleted.length?'disabled':'')+'>Delete All</button></div><div id="trash-contents" class="panel"></div>';
 $('#trash-contents').innerHTML=deleted.length?deleted.map(it=>'<div class="row" style="justify-content:space-between;gap:12px;padding:10px;border-bottom:1px solid #6b5160"><span>'+escape(it.name)+' ('+escape(it.kind)+')</span><button data-restore-trash="'+it.id+'">Restore</button></div>').join(''):'<p>Trash is empty.</p>';
 $('#trash-contents').querySelectorAll('[data-restore-trash]').forEach(b=>b.onclick=async()=>{try{await replay.restore(b.dataset.restoreTrash);await redraw()}catch(e){alert('Restore failed: '+e.message)}});
 $('#delete-all-trash').onclick=async()=>{const count=deleted.length;if(!count)return;if(!confirm('Permanently delete all '+count+' files in Trash? This cannot be undone.'))return;try{const result=await replay.deleteAllTrash();await redraw();alert('Permanently deleted '+result.deleted+' files.')}catch(e){alert('Delete All failed: '+e.message)}};
 }else if(view==='favorites'){header('Favorites','Golden-bordered favorites');const all=data.items.filter(x=>x.favorite&&!x.deletedAt);$('#content').innerHTML='<div class="grid" style="--tile:'+size+'px">'+all.map(tile).join('')+'</div>';replayPreparePreviews($('#content'));$('#content').querySelectorAll('[data-item]').forEach(e=>{const it=data.items.find(x=>x.id===e.dataset.item);e.ondragstart=event=>{window.replayDragId=it.id;event.dataTransfer.effectAllowed='move';event.dataTransfer.setData('text/replay-item',it.id)};e.onclick=()=>openItem(it);e.querySelector('.move-media').onclick=async event=>{event.stopPropagation();try{const destination=await moveMediaPicker(it,data.folders.filter(f=>f.kind===it.kind));if(destination){await replay.itemUpdate(it.id,{folder:destination.folder,group:destination.group,fandoms:[]});await redraw()}}catch(error){alert('Could not move media: '+error.message)}}})}else settings()}async function createFolder(){document.querySelector('#new-folder-form')?.remove();const panel=document.createElement('form');panel.id='new-folder-form';panel.className='panel';const options=data.folders.filter(f=>f.kind===kind&&f.group===group);panel.innerHTML='<h3>Create Folder</h3><label>Name <input name="name" required maxlength="90"></label><label><input name="subfolder" type="checkbox"> This is a subfolder</label><label><input name="showInfoCard" type="checkbox" checked> Show Information Card</label><label><input name="autoNumberMedia" type="checkbox" checked> Number incoming media by folder name (1, 2, 3…)</label><label>Parent folder <select name="parent"><option value="">Library root</option>'+options.map(f=>'<option value="'+f.id+'" '+(folder===f.id?'selected':'')+'>'+escape(f.name)+'</option>').join('')+'</select></label><div class="row"><button class="primary" type="submit">Create Folder</button><button type="button" id="cancel-new-folder">Cancel</button></div>';document.querySelector('#content').prepend(panel);panel.querySelector('[name="name"]').focus();panel.querySelector('#cancel-new-folder').onclick=()=>panel.remove();panel.onsubmit=async e=>{e.preventDefault();const v=new FormData(panel),name=String(v.get('name')||'').trim();if(!name)return;try{await replay.folder({name,kind,group,parent:v.get('parent'),isSubfolder:v.has('subfolder'),showInfoCard:v.has('showInfoCard'),autoNumberMedia:v.has('autoNumberMedia')});await redraw()}catch(err){alert(err.message)}}}
async function importOption(title,message,choices){
 return new Promise(resolve=>{
  document.querySelector('#import-choice-dialog')?.remove();
  const overlay=document.createElement('div');overlay.id='import-choice-dialog';overlay.className='import-dialog-backdrop';
  overlay.innerHTML='<div class="import-dialog"><h2>'+escape(title)+'</h2><p>'+escape(message)+'</p><div class="import-dialog-actions"></div></div>';
  const bar=overlay.querySelector('.import-dialog-actions');
  for(const choice of choices){const button=document.createElement('button');button.type='button';button.textContent=choice.label;button.onclick=()=>{overlay.remove();resolve(choice.value)};bar.append(button)}
  document.body.append(overlay);
 });
}
async function importMedia(providedPaths){
 const paths=Array.isArray(providedPaths)?providedPaths:await replay.browse();if(!paths.length)return;
 const routing=await importOption('Organize imported media','Where should Replay put these files? You can use this folder or choose a destination for each file.',[{label:'Use Current Folder',value:'current'},{label:'Choose Folders Per File',value:'custom'},{label:'Cancel Import',value:'cancel'}]);
 if(routing==='cancel')return;
 const entries=[];
 for(const filePath of paths){
  const ext=filePath.split('.').pop().toLowerCase();
  const fileKind=ext==='gif'?'gifs':/^(mp4|mov|mkv|avi|webm|m4v|wmv|flv|ts)$/.test(ext)?'videos':'images';
  let selected=folder,targetGroup=group;
  if(routing==='custom'){
   const options=data.folders.filter(f=>f.kind===fileKind&&f.group==='fandom');
   const chosen=await importFolderPicker(filePath,options,folder);
   if(chosen===null)continue;
   const target=options.find(f=>f.id===chosen);
   selected=target?.id||'';targetGroup=target?.group||group;
  }else if(selected&&!data.folders.some(f=>f.id===selected&&f.kind===fileKind))selected='';
  entries.push({path:filePath,folder:selected,group:targetGroup,fandoms:[]});
 }
 if(!entries.length)return;
 let notice=document.querySelector('#import-progress');
 if(!notice){notice=document.createElement('div');notice.id='import-progress';notice.className='panel';document.querySelector('#content').prepend(notice)}
 notice.innerHTML='<strong>Importing media</strong> <progress value="0" max="100" style="width:100%"></progress><p class="import-detail">Starting '+entries.length+' file(s)…</p>';
 let results=await replay.import(entries);
 const duplicates=results.filter(x=>x.status==='duplicate');
 let allChoice='';
 if(duplicates.length>1)allChoice=await importOption('Duplicate files found',duplicates.length+' files already exist in Replay. Choose one action for all, or review each file separately.',[{label:'Keep Existing',value:'existing'},{label:'Use Incoming Instead',value:'replace'},{label:'Keep Both Copies',value:'both'},{label:'Review Individually',value:'each'}]);
 for(const item of duplicates){
  const choice=allChoice&&allChoice!=='each'?allChoice:await importOption('Duplicate: '+item.name,'An identical file is already in Replay. Keep Existing skips the import. Use Incoming Instead archives the new copy and moves the older entry into 30-day Trash. Keep Both creates another copy.',[{label:'Keep Existing',value:'existing'},{label:'Use Incoming Instead',value:'replace'},{label:'Keep Both Copies',value:'both'}]);
  if(choice==='existing')continue;
  const entry=entries.find(x=>x.path===item.path);
  if(entry)results.push(...await replay.import([{...entry,keepDuplicate:choice==='both',replaceDuplicate:choice==='replace'}]));
 }
 notice.querySelector('progress').value=100;
 const imported=results.filter(x=>x.status==='imported').length;
 notice.querySelector('.import-detail').textContent=imported+' files imported. '+duplicates.length+' duplicates reviewed. '+results.filter(x=>x.status==='error').length+' errors.';
 const failures=results.filter(x=>x.status==='error'||x.status==='unsupported'||x.status==='imported-source-retained');
 if(failures.length)alert(failures.map(x=>x.name+': '+x.status+(x.error?' — '+x.error:'')).join('\\n'));
 await redraw();
}
// Move existing media between any folder/subfolder and the General (root) sections.
function moveMediaPicker(item,folders,allDestinations=false){
 return new Promise(resolve=>{
  document.querySelector('#move-media-dialog')?.remove();
  const current=folders.find(f=>f.id===item.folder);
  const parentId=current?(current.parent||''):'';
  // Immediate siblings plus the parent, or direct children when at a parent.
  const nearby=folders.filter(f=>f.kind===item.kind&&f.group==='fandom'&&(f.parent||'')===(current?parentId:''));
  const children=current?folders.filter(f=>f.kind===item.kind&&f.group==='fandom'&&(f.parent||'')===current.id):folders.filter(f=>f.kind===item.kind&&f.group==='fandom'&&!f.parent);
  const choices=new Map();
  const add=(id,label)=>{if(id!==item.folder)choices.set(id,label)};
  if(allDestinations){
   add('','General (Library root)');
   const pathFor=f=>{const names=[f.name],seen=new Set([f.id]);let p=folders.find(x=>x.id===f.parent);while(p&&!seen.has(p.id)){seen.add(p.id);names.unshift(p.name);p=folders.find(x=>x.id===p.parent)}return names.join(' / ')};
   for(const f of folders.filter(f=>f.kind===item.kind&&f.group==='fandom').sort((x,y)=>pathFor(x).localeCompare(pathFor(y))))add(f.id,pathFor(f));
  }else{
  if(current)add(parentId,parentId?(folders.find(f=>f.id===parentId)?.name||'Parent folder'):'Library root');
  else add('', 'Library root');
  for(const f of current?(current.parent?nearby:children):children)add(f.id,f.name);
  if(current&&!current.parent){for(const f of children)add(f.id,f.name)}
  }
  const overlay=document.createElement('div');overlay.id='move-media-dialog';overlay.className='import-dialog-backdrop';
  const panel=document.createElement('div');panel.className='import-dialog';
  const title=document.createElement('h2');title.textContent='Move Media';
  const description=document.createElement('p');description.textContent='Move '+item.name+' to '+(allDestinations?'any folder':'a nearby folder')+' in '+item.kind+'.';
  choices.set('__trash__','Trash (recoverable for 30 days)');
  const destinations=document.createElement('div');destinations.className='replay-move-destinations';destinations.style.cssText='display:grid;gap:8px;max-height:50vh;overflow-y:auto;padding:5px';
  for(const [id,label] of choices){
   const button=document.createElement('button');button.type='button';
   button.textContent=label;button.style.cssText='text-align:left;padding:12px;white-space:normal';
   button.onclick=()=>{const target=folders.find(f=>f.id===id);overlay.remove();resolve(id==='__trash__'?{trash:true}:{group:target?.group||'fandom',folder:id})};
   destinations.append(button);
  }
  const actions=document.createElement('div');actions.className='import-dialog-actions';
  const cancel=document.createElement('button');cancel.type='button';cancel.textContent='Cancel';cancel.onclick=()=>{overlay.remove();resolve(null)};
  if(!choices.size)description.textContent='No nearby destinations available.';
  actions.append(cancel);panel.append(title,description,destinations,actions);overlay.append(panel);document.body.append(overlay);destinations.querySelector('button')?.focus();
 });
}
async function importFolderPicker(filePath,folders,defaultFolder){
 return new Promise(resolve=>{
  const overlay=document.createElement('div');overlay.className='import-dialog-backdrop';overlay.id='import-choice-dialog';
  const panel=document.createElement('div');panel.className='import-dialog';
  const title=document.createElement('h2');title.textContent='Choose Destination';
  const description=document.createElement('p');description.textContent=filePath.split(/[\\/]/).pop();
  const select=document.createElement('select');select.className='import-folder-select';
  const rootOption=document.createElement('option');rootOption.value='';rootOption.textContent='Library Root';select.append(rootOption);
  for(const folder of folders){const opt=document.createElement('option');opt.value=folder.id;opt.textContent=folder.name;select.append(opt)}
  select.value=folders.some(x=>x.id===defaultFolder)?defaultFolder:'';
  const actions=document.createElement('div');actions.className='import-dialog-actions';
  const use=document.createElement('button');use.textContent='Use Selected Folder';use.onclick=()=>{overlay.remove();resolve(select.value)};
  const skip=document.createElement('button');skip.textContent='Skip This File';skip.onclick=()=>{overlay.remove();resolve(null)};
  actions.append(use,skip);panel.append(title,description,select,actions);overlay.append(panel);document.body.append(overlay);select.focus();
 });
}

// Global Explorer-style internal dragging: sections, folders, empty gallery and breadcrumbs.
async function transferMedia(id,targetFolder,targetGroup){
 const item=data.items.find(x=>x.id===id&&!x.deletedAt);if(!item)return;
 const destination=targetFolder?folderOf(targetFolder):null;
 if(destination&&destination.kind!==item.kind)throw Error('This folder holds '+destination.kind+', not '+item.kind);
 await moveMediaBatch(window.replayDragIds?.includes(id)?window.replayDragIds:[id],targetFolder,targetGroup);
}
const isMediaDrag=event=>event.dataTransfer?.types?.includes('text/replay-item');
function dropDestination(element){
 if(!element)return null;
 const folderTile=element.closest('[data-folder]');if(folderTile)return {folder:folderTile.dataset.folder};
 const crumb=element.closest('.pathcrumb');if(crumb)return {folder:crumb.dataset.folder};
 const pin=element.closest('[data-pin]');if(pin)return {folder:pin.dataset.pin};
 const navItem=element.closest('#nav [data-view]');
 if(navItem){const destination=navItem.dataset.view;if(['videos','images','gifs'].includes(destination))return {folder:'',group:'fandom',kind:destination};return null}
 if(element.closest('#root'))return {folder:'',group};
 if(element.closest('#gallery'))return {folder,group};
 return null;
}
// Dragging near the viewport edge scrolls through the complete collection.
let replayDragScrollLast=0;
function replayDragAutoScroll(event){
 if(!isMediaDrag(event))return;
 const now=Date.now();if(now-replayDragScrollLast<25)return;
 replayDragScrollLast=now;
 const margin=100,y=event.clientY,h=window.innerHeight;
 const direction=y<margin?-1:y>h-margin?1:0;
 if(!direction)return;
 const speed=Math.max(12,Math.round(35*(direction<0?(margin-y)/margin:(y-(h-margin))/margin)));
 let el=event.target;
 while(el&&el!==document.body){
  if(el.scrollHeight>el.clientHeight+10&&getComputedStyle(el).overflowY!=='hidden'){
   const before=el.scrollTop;el.scrollTop+=direction*speed;
   if(el.scrollTop!==before)return;
  }
  el=el.parentElement;
 }
 window.scrollBy(0,direction*speed);
}
document.addEventListener('dragover',event=>{
 if(!isMediaDrag(event))return;
 replayDragAutoScroll(event);
 const target=dropDestination(event.target);
 if(!target)return;
 const id=window.replayDragId;
 const item=data.items.find(x=>x.id===id);
 const dest=target.folder?folderOf(target.folder):null;
 if(item&&((target.kind&&target.kind!==item.kind)||(dest&&dest.kind!==item.kind)))return;
 event.preventDefault();event.dataTransfer.dropEffect='move';
},true);
document.addEventListener('drop',async event=>{
 if(!isMediaDrag(event))return;
 const target=dropDestination(event.target);if(!target)return;
 event.preventDefault();event.stopImmediatePropagation();
 const id=event.dataTransfer.getData('text/replay-item')||window.replayDragId;
 try{await transferMedia(id,target.folder||'',target.group||group)}catch(error){alert('Could not move media: '+error.message)}
},true);
document.addEventListener('dragend',()=>{window.replayDragId=null;window.replayDragIds=null},true);
document.addEventListener('dragover',event=>{if(event.dataTransfer?.types?.includes('Files'))event.preventDefault()});
document.addEventListener('drop',event=>{if(!event.dataTransfer?.types?.includes('Files'))return;event.preventDefault();const files=[...event.dataTransfer.files];const paths=files.map(f=>replay.filePath(f)).filter(Boolean);if(paths.length)importMedia(paths).catch(e=>alert('Import failed: '+e.message))});
replay.onImportProgress(info=>{const progress=document.querySelector('#import-progress');if(progress){progress.querySelector('progress').value=info.percent;progress.querySelector('.import-detail').textContent=info.status+' — '+info.completed+'/'+info.total+' ('+info.percent+'%)'}});

let viewerNext=null;
function openItem(it){
 // Stop and silence gallery previews before the audible viewer starts.
 document.querySelectorAll('#content video').forEach(preview=>{preview.muted=true;preview.pause()});
 $('#overlay').classList.remove('hidden');
 let current=it,scale=1,panX=0,panY=0;
 const peers=data.items.filter(x=>!x.deletedAt&&x.kind===it.kind&&(view==='favorites'?x.favorite:true)&&(folder?(x.folder===folder||(x.fandoms||[]).includes(folder)):true));
 const move=offset=>{const index=peers.findIndex(x=>x.id===current.id);if(index<0||!peers.length)return;current=peers[(index+offset+peers.length)%peers.length];display()};
 viewerNext=move;
 function display(){
  // Release the prior player completely before navigating to another item.
  const previous=$('#player video');if(previous){previous.muted=true;previous.pause();previous.removeAttribute('src');previous.load()}
  scale=1;panX=0;panY=0;
  const url='replay://media/'+current.id;
  $('#player').innerHTML=current.kind==='videos'?'<video src="'+url+'" controls autoplay loop></video>':'<img draggable="false" src="'+url+'">';
  $('#controls').innerHTML='<button id="previous-media">← Previous</button><button id="next-media">Next →</button><button id="move-viewed-media">Move</button><button id="separate-media">Open in New Window ↗</button><button id="full-media">Fullscreen</button>'+(current.kind==='videos'?'<button id="loop-media">Loop: on</button><button id="mute-media">Mute</button><select id="speed-media"><option value="0.5">0.5×</option><option value="1" selected>1×</option><option value="1.5">1.5×</option><option value="2">2×</option></select>':current.kind==='images'?'<button id="zoom-out">−</button><button id="zoom-in">+</button><button id="fit-image">Fit</button>':current.kind==='gifs'?'<button id="pause-gif">Pause GIF</button>':'');
  $('#previous-media').onclick=()=>move(-1);$('#next-media').onclick=()=>move(1);
  $('#move-viewed-media').onclick=async()=>{
   const moving=current;
   const destination=await moveMediaPicker(moving,data.folders.filter(f=>f.kind===moving.kind),true);
   if(!destination)return;
   const control=$('#move-viewed-media');control.disabled=true;
   try{
    // Keep the original viewer sequence, even when a move removes this file from General.
    const oldIndex=peers.findIndex(x=>x.id===moving.id);
    const next=peers.slice(oldIndex+1).find(x=>x.id!==moving.id&&!x.deletedAt&&x.folder===moving.folder)
      ||peers.slice(0,Math.max(0,oldIndex)).find(x=>x.id!==moving.id&&!x.deletedAt&&x.folder===moving.folder);
    const updated=destination.trash?await replay.itemDelete(moving.id):await replay.itemUpdate(moving.id,{folder:destination.folder,group:destination.group,fandoms:[]});
    data=updated;
    await redraw();
    if(next){current=data.items.find(x=>x.id===next.id)||next;display()}
    else{current=data.items.find(x=>x.id===moving.id)||moving;display()}
   }catch(error){alert('Could not move media: '+error.message);control.disabled=false}
  };

  $('#separate-media').onclick=async()=>{try{await replay.openMediaWindow(current.id);$('#close').click()}catch(e){alert('Could not open media window: '+e.message)}};$('#full-media').onclick=()=>$('#player').requestFullscreen?.();
  const video=$('#player video'),img=$('#player img');
  if(video){
   video.muted=data.settings.muteVideosByDefault===true;
   $('#mute-media').textContent=video.muted?'Unmute':'Mute';
   video.addEventListener('error',async()=>{if(video.dataset.fallback)return;video.dataset.fallback='yes';try{video.src=await replay.compatibleVideo(current.id);await video.play()}catch(error){alert('Could not play video: '+error.message)}});
   $('#loop-media').onclick=()=>{video.loop=!video.loop;$('#loop-media').textContent='Loop: '+(video.loop?'on':'off')};
   $('#mute-media').onclick=()=>{video.muted=!video.muted;$('#mute-media').textContent=video.muted?'Unmute':'Mute'};
   $('#speed-media').onchange=event=>{video.playbackRate=Number(event.target.value)};
  }
  if(img&&current.kind==='images'){
   const transform=()=>{img.style.transform='translate('+panX+'px,'+panY+'px) scale('+scale+')'};
   $('#zoom-in').onclick=()=>{scale=Math.min(8,scale*1.25);transform()};
   $('#zoom-out').onclick=()=>{scale=Math.max(.25,scale/1.25);transform()};
   $('#fit-image').onclick=()=>{scale=1;panX=0;panY=0;transform()};
   img.onwheel=event=>{event.preventDefault();scale=Math.min(8,Math.max(.25,scale*(event.deltaY<0?1.13:.88)));transform()};
   let origin=null;img.onpointerdown=event=>{origin={x:event.clientX-panX,y:event.clientY-panY};img.setPointerCapture(event.pointerId)};img.onpointermove=event=>{if(!origin)return;panX=event.clientX-origin.x;panY=event.clientY-origin.y;transform()};img.onpointerup=()=>origin=null;
  }
  if(img&&current.kind==='gifs'){
   let paused=false,canvas=null;
   $('#pause-gif').onclick=()=>{
    if(!paused){canvas=document.createElement('canvas');canvas.width=img.naturalWidth||1;canvas.height=img.naturalHeight||1;canvas.getContext('2d').drawImage(img,0,0);img.style.display='none';$('#player').append(canvas);canvas.style.maxWidth='88vw';canvas.style.maxHeight='76vh';paused=true}
    else{canvas.remove();img.style.display='';img.src=url+'?resume='+Date.now();paused=false}
    $('#pause-gif').textContent=paused?'Resume GIF':'Pause GIF'
   };
  }
 }
 display();
}
$('#close').onclick=()=>{const player=$('#player video');if(player){player.muted=true;player.pause();player.removeAttribute('src');player.load()}$('#overlay').classList.add('hidden');$('#player').innerHTML='';viewerNext=null};document.addEventListener('keydown',e=>{if(e.key==='Escape')$('#close').click();if(!$('#overlay').classList.contains('hidden')&&viewerNext){if(e.key==='ArrowRight')viewerNext(1);if(e.key==='ArrowLeft')viewerNext(-1)}});$('#settings').onclick=()=>{view='settings';settings()};function settings(){header('Settings','Storage, backups and recovery');$('#content').innerHTML='<div class="panel"><h2>Playback</h2><label for="default-audio">Video audio on opening</label><select id="default-audio"><option value="on">Unmuted (default)</option><option value="off">Muted</option></select><p class="muted">Thumbnail hover previews always stay silent.</p></div><div class="panel"><h2>Automatic Backups</h2><p>Choose where Replay saves a second copy of your media.</p><p class="muted">'+escape(data.settings.backupRoot||'No backup location configured — source imports still require a verified backup for protection')+'</p><button id="location">Choose Backup Location</button> <button id="runbackup">Back Up Now</button></div><div class="panel"><h2>On Launch</h2><select id="launch"><option value="dashboard">Open dashboard</option><option value="last">Open last location</option></select></div><div class="panel"><h2>Trash</h2><p>Deleted media is retained for 30 days.</p><button id="trash">Purge expired files</button></div><div class="panel"><h2>Updates</h2><button id="checkupdate">Check GitHub for updates</button><p id="updateresult" class="muted"></p></div>';$('#default-audio').value=data.settings.muteVideosByDefault===true?'off':'on';$('#default-audio').onchange=async e=>{const muteVideosByDefault=e.target.value==='off';await replay.settings({muteVideosByDefault});data.settings.muteVideosByDefault=muteVideosByDefault};$('#location').onclick=async()=>{const p=await replay.chooseBackup();if(p){await replay.settings({backupRoot:p});try{await replay.backup()}catch(error){alert('Backup location changed, but initial sync failed: '+error.message)}redraw()}};$('#runbackup').onclick=async()=>{try{await replay.backup();alert('Backup complete')}catch(e){alert(e.message)}};const restoreButton=document.createElement('button');restoreButton.textContent='Restore from Backup';$('#runbackup').after(restoreButton);restoreButton.onclick=async()=>{try{const files=await replay.listBackup();if(!files.length){alert('No backed-up files found');return}const response=prompt('Restore all '+files.length+' backed-up files? Type ALL, a filename, or FOLDER: followed by a collection name.','ALL');if(!response)return;const selectFolder=response.trim().toUpperCase().startsWith('FOLDER:');const lookup=(selectFolder?response.trim().slice(7):response.trim()).toLowerCase();const selected=response.trim().toUpperCase()==='ALL'?[]:files.filter(x=>(selectFolder?x.folderName:x.name).toLowerCase().includes(lookup)).map(x=>x.id);if(response.trim().toUpperCase()!=='ALL'&&!selected.length){alert('No matching backup files');return}const result=await replay.restoreBackup(selected);alert('Restored '+result.restored+' files');await redraw()}catch(e){alert('Restore failed: '+e.message)}};$('#launch').value=data.settings.launch||'dashboard';$('#launch').onchange=e=>replay.settings({launch:e.target.value});$('#trash').onclick=async()=>{if(confirm('Permanently delete files whose 30-day recovery period has expired?')){await replay.emptyTrash();redraw()}};const trashList=document.createElement('div');trashList.className='field';$('#trash').before(trashList);replay.listTrash().then(items=>{trashList.innerHTML=items.length?items.map(i=>'<div class="row"><span>'+escape(i.name)+' ('+Math.max(0,30-Math.floor((Date.now()-i.deletedAt)/86400000))+' days left)</span><button data-restore="'+i.id+'">Restore</button></div>').join(''):'<p>Trash is empty.</p>';trashList.querySelectorAll('[data-restore]').forEach(b=>b.onclick=async()=>{await replay.restore(b.dataset.restore);await redraw()})}).catch(()=>{trashList.textContent='Could not load Trash'});$('#checkupdate').onclick=async()=>{try{const r=await replay.checkUpdate(),v=await replay.version();if(!r){$('#updateresult').textContent='No update manifest published yet';return}if(!isReplayNewer(r.version,v)){$('#updateresult').textContent='Replay is up to date ('+v+')';return}$('#updateresult').textContent='Installing verified update '+r.version+'…';await replay.stageUpdate(r);await replay.applyUpdate()}catch(e){$('#updateresult').textContent='Update failed: '+e.message}}}redraw();
// Check for updates without silently closing Replay. Installation is always user-initiated.
setTimeout(async()=>{try{const [manifest,version]=await Promise.all([replay.checkUpdate(),replay.version()]);if(manifest?.version&&isReplayNewer(manifest.version,version)){const notice=document.createElement('div');notice.className='panel';notice.id='replay-update-notice';notice.innerHTML='<strong>Replay update '+escape(manifest.version)+' available</strong><p>You can install it when you are ready. Replay will restart after installation.</p><button id="replay-install-update">Install Update</button><button id="replay-dismiss-update">Later</button>';document.querySelector('#content')?.prepend(notice);notice.querySelector('#replay-dismiss-update').onclick=()=>notice.remove();notice.querySelector('#replay-install-update').onclick=async()=>{const btn=notice.querySelector('#replay-install-update');btn.disabled=true;btn.textContent='Installing…';try{await replay.stageUpdate(manifest);await replay.applyUpdate()}catch(e){btn.disabled=false;btn.textContent='Try Again';alert('Update failed: '+e.message)}}}}catch(e){console.warn('Update check unavailable:',e.message)}},6500);
function isReplayNewer(a,b){const parts=v=>String(v||'0').split('.').map(x=>Number(x)||0);const x=parts(a),y=parts(b);for(let i=0;i<3;i++){if((x[i]||0)!==(y[i]||0))return (x[i]||0)>(y[i]||0)}return false}
