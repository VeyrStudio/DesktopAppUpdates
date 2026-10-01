/* The Index: character detail sidebar, linked navigation and reference gallery. */
const indexProfileWithoutAside=profile;
profile=function(){
 const existing=indexProfileWithoutAside();
 if(!profileId)return existing;
 const c=db.characters.find(x=>x.id===profileId);
 if(!c)return existing;
 const marker='<div class="panel editor-panel">';
 const at=existing.lastIndexOf(marker);
 if(at<0)return existing;
 const quick=[
  ['Character Role',fieldValue(c,'Character Role')],
  ['Age',fieldValue(c,'Age')],
  ['Species',fieldValue(c,'Species')],
  ['Occupation',fieldValue(c,'Occupation')],
  ['Residence',fieldValue(c,'Residence')],
  ['Pronouns',fieldValue(c,'Pronouns')],
  ['Status',fieldValue(c,'Status')],
  ['Love Interest',fieldValue(c,'Love Interest')]
 ];
 const links=(c.relationships||[]).map(item=>{const related=db.characters.find(p=>p.id===item['Linked Character']);if(!related)return '';return '<button class="related-character" onclick="openProfile(\''+esc(related.id)+'\')">'+(related.portrait?img(related.portrait,'side-avatar'):'<span class="side-avatar placeholder">✧</span>')+'<span><b>'+esc(related.name)+'</b><small>'+esc(item['Relationship Type']||'Linked Character')+'</small></span> →</button>'}).join('');
 const story=db.stories.find(s=>s.name===c.story);
 const aside='<aside class="profile-aside"><div class="panel"><h3>Quick Facts</h3><dl class="details">'+quick.map(([name,value])=>'<dt>'+esc(name)+'</dt><dd>'+esc(value||'—')+'</dd>').join('')+'</dl></div><div class="panel"><h3>Profile Progress</h3>'+pill(c.status||'Blank',c.status==='Existing'?'green':'orange')+'<div class="toolbar">'+pill((c.powers||[]).length+' Powers')+pill((c.events||[]).length+' Events')+pill((c.relationships||[]).length+' Relationships')+'</div></div><div class="panel"><h3>Story</h3>'+(story?'<p>'+esc(story.name)+'</p>'+button('Open Story',"go('Stories');selectCollection('stories','"+esc(story.id)+"')",'primary'):'<p class="sub">'+esc(c.story||'No story linked')+'</p>')+'</div><div class="panel"><h3>Linked Characters</h3>'+(links||'<p class="sub">Connect another character in Relationships.</p>')+'</div><div class="panel"><div class="section-header"><h3>Reference Gallery</h3>'+button('+ Add',"indexAddMood('"+esc(c.id)+"')")+'</div><div class="mini-gallery">'+(c.moodImages||[]).slice(0,6).map(image=>img(image,'gallery-thumb')).join('')+(c.portrait?img(c.portrait,'gallery-thumb'):'')+'</div></div></aside>';
 return existing.slice(0,at)+'<div class="profile-workspace"><div class="profile-editor">'+existing.slice(at)+'</div>'+aside+'</div>';
};
