from pathlib import Path
import json,re
root=Path('tome-build')
r=root/'renderer.js'; m=root/'main.js'; p=root/'package.json'
s=r.read_text(encoding='utf-8')
# Replace card helpers + renderLibrary with spine/bookcase rendering.
start=s.index('function bookCard(b)')
end=s.index('function bindCards()', start)
new=r'''function spineSeed(text=''){let h=2166136261;for(const c of String(text)){h^=c.charCodeAt(0);h=Math.imul(h,16777619)}return h>>>0;}
const spinePalettes=[
  ['#171313','#3a2922','#76542f'],['#241411','#51271f','#8b5e36'],['#15151a','#30313a','#8e7547'],
  ['#281324','#512642','#9a6b48'],['#17100e','#3b261b','#75502e'],['#201516','#4a2528','#8a5f3e']
];
function bookSpine(b,index=0){
  const seed=spineSeed((b.id||'')+(b.title||'')+index), pal=spinePalettes[seed%spinePalettes.length];
  const h=196+(seed%43), w=42+((seed>>>5)%23), lean=((seed>>>9)%5)-2;
  const style=`--spine-h:${h}px;--spine-w:${w}px;--spine-lean:${lean}deg;--leather1:${pal[0]};--leather2:${pal[1]};--metal:${pal[2]}`;
  return `<button class="book-spine" data-book="${b.id}" style="${style}" title="${escapeHtml(b.title)} — ${escapeHtml(b.author||'Unknown author')}">${b.favorite?'<span class="spine-heart">♥</span>':''}<span class="spine-cap top"></span><span class="spine-title">${escapeHtml(b.title)}</span><span class="spine-flourish">◆</span><span class="spine-cap bottom"></span></button>`;
}
function seriesSpineGroup(name,books){
  const sorted=[...books].sort(seriesSort);
  return `<div class="series-spine-group"><div class="series-book-row">${sorted.map((b,i)=>bookSpine(b,i)).join('')}</div><button class="series-plaque" data-series="${escapeHtml(name)}">${escapeHtml(name)} <span>· ${books.length}</span></button></div>`;
}
function bookCard(b){return bookSpine(b,0);}
function seriesCard(name,books){return seriesSpineGroup(name,books);}
function renderLibrary(){
  const books=filteredBooks();
  $('#statsRow').innerHTML=`<span class="stat-chip">${state.books.length} books</span><span class="stat-chip">${new Set(state.books.filter(b=>b.series).map(b=>b.series)).size} series</span>`;
  const recent=[...books].sort((a,b)=>b.addedAt.localeCompare(a.addedAt)).slice(0,10);
  $('#recentShelf').innerHTML=recent.length?recent.map((b,i)=>bookSpine(b,i)).join(''):`<div class="empty-shelf-message">No books added yet.</div>`;
  $('#recentShelf').classList.toggle('hidden',!!settings.recentlyAddedCollapsed);
  $('#recentToggle span').textContent=settings.recentlyAddedCollapsed?'›':'⌄';
  let html='';
  if(libraryViewMode==='all') html=books.map((b,i)=>bookSpine(b,i)).join('');
  else {
    const groups=new Map();
    books.forEach(b=>{if(b.series){if(!groups.has(b.series))groups.set(b.series,[]);groups.get(b.series).push(b);}});
    html=[...groups.keys()].sort().map(n=>seriesSpineGroup(n,groups.get(n))).join('');
  }
  if(!html)html=`<div class="empty-shelf-message"><span class="moon">☾</span>${libraryViewMode==='all'?'No books match this view.':'No series on this shelf yet.'}</div>`;
  $('#mainShelf').innerHTML=html;
  $('#mainShelfLabel').textContent=libraryViewMode==='all'?'All Books':'Series';
  bindCards();
}
'''
s=s[:start]+new+s[end:]
# prevent series group click from swallowing spine clicks
s=s.replace("document.querySelectorAll('[data-book]').forEach(el=>el.onclick=()=>openDetails(el.dataset.book));", "document.querySelectorAll('[data-book]').forEach(el=>el.onclick=(e)=>{e.stopPropagation();openDetails(el.dataset.book)});")
r.write_text(s,encoding='utf-8')
mm=m.read_text(encoding='utf-8')
if "const APP_VERSION = '0.1.4';" not in mm: raise SystemExit('v0.1.4 marker missing')
mm=mm.replace("const APP_VERSION = '0.1.4';","const APP_VERSION = '0.1.5';",1);m.write_text(mm,encoding='utf-8')
pkg=json.loads(p.read_text(encoding='utf-8'));pkg['version']='0.1.5';p.write_text(json.dumps(pkg,indent=2)+'\n',encoding='utf-8')
print('Applied v0.1.5 realistic bookcase and spine library.')
