from pathlib import Path
import base64, json

root=Path('tome-build')
assets=root/'assets'; assets.mkdir(parents=True,exist_ok=True)
encoded=json.loads(Path('tools/the-tome-v016-assets.json').read_text(encoding='utf-8'))
for name,data in encoded.items():
    (assets/name).write_bytes(base64.b64decode(data))

renderer=root/'renderer.js'; main=root/'main.js'; pkg=root/'package.json'
s=renderer.read_text(encoding='utf-8')
addon=r'''
// The Tome v0.1.6 — supplied-image bookshelf renderer
function tomeEmptySpines(count=18){return Array.from({length:count},(_,i)=>`<span class="empty-spine" aria-hidden="true" data-empty-index="${i}"></span>`).join('');}
function bookSpine(b,index=0){
  return `<button class="book-spine" data-book="${b.id}" title="${escapeHtml(b.title)} — ${escapeHtml(b.author||'Unknown author')}">${b.favorite?'<span class="spine-heart">♥</span>':''}<span class="spine-title">${escapeHtml(b.title)}</span></button>`;
}
function seriesSpineGroup(name,books){
  const sorted=[...books].sort(seriesSort);
  return `<div class="series-spine-group"><div class="series-book-row">${sorted.map((b,i)=>bookSpine(b,i)).join('')}</div><button class="series-plaque" data-series="${escapeHtml(name)}">${escapeHtml(name)} <span>· ${books.length}</span></button></div>`;
}
function renderLibrary(){
  const books=filteredBooks();
  $('#statsRow').innerHTML=`<span class="stat-chip">${state.books.length} books</span><span class="stat-chip">${new Set(state.books.filter(b=>b.series).map(b=>b.series)).size} series</span>`;
  const recent=[...books].sort((a,b)=>b.addedAt.localeCompare(a.addedAt)).slice(0,10);
  $('#recentShelf').innerHTML=(recent.length?recent.map((b,i)=>bookSpine(b,i)).join(''):'')+tomeEmptySpines(recent.length?18:22);
  $('#recentShelf').classList.toggle('hidden',!!settings.recentlyAddedCollapsed);
  $('#recentToggle span').textContent=settings.recentlyAddedCollapsed?'›':'⌄';
  let html='';
  if(libraryViewMode==='all') html=books.map((b,i)=>bookSpine(b,i)).join('');
  else {
    const groups=new Map();
    books.forEach(b=>{if(b.series){if(!groups.has(b.series))groups.set(b.series,[]);groups.get(b.series).push(b);}});
    html=[...groups.keys()].sort().map(n=>seriesSpineGroup(n,groups.get(n))).join('');
  }
  $('#mainShelf').innerHTML=html+tomeEmptySpines(html?18:22);
  $('#mainShelfLabel').textContent=libraryViewMode==='all'?'All Books':'Series';
  bindCards();
}
'''
s += addon
renderer.write_text(s,encoding='utf-8')

m=main.read_text(encoding='utf-8')
if "const APP_VERSION = '0.1.5';" not in m: raise SystemExit('v0.1.5 version marker missing')
m=m.replace("const APP_VERSION = '0.1.5';","const APP_VERSION = '0.1.6';",1)
main.write_text(m,encoding='utf-8')

p=json.loads(pkg.read_text(encoding='utf-8')); p['version']='0.1.6'; pkg.write_text(json.dumps(p,indent=2)+'\n',encoding='utf-8')
print('Applied The Tome v0.1.6 supplied-art bookshelf update.')
