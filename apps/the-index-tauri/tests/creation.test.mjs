import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {JSDOM} from 'jsdom';
const dir=path.dirname(fileURLToPath(import.meta.url));
const root=path.join(dir,'..','src');
const modules=['renderer.js','profile-enhancements.js','library-enhancements.js','settings-enhancements.js','quality-enhancements.js','productivity-enhancements.js','profile-layout.js','creation-fixes.js'];
function fresh(){
 let stored={schema:1,characters:[],stories:[],worldbuilding:[],notes:[],tags:[],events:[],settings:{}};
 const markup=fs.readFileSync(path.join(root,'index.html'),'utf8').replace(/<script[^>]*><\/script>/g,'');
 const dom=new JSDOM(markup,{url:'http://localhost',runScripts:'dangerously',pretendToBeVisual:true});
 const w=dom.window;
 w.indexAPI={read:async()=>structuredClone(stored),save:async x=>(stored=JSON.parse(JSON.stringify(x)),structuredClone(stored)),version:async()=> '0.3.0',backup:async()=> 'backup.json',onUpdate:()=>{},chooseImage:async()=>null,checkUpdate:async()=>({status:'up-to-date'})};
 w.confirm=()=>true;
 w.document.execCommand=()=>true;
 for(const name of modules){const el=w.document.createElement('script');el.textContent=fs.readFileSync(path.join(root,name),'utf8');w.document.body.appendChild(el);}
 return {w,dom,get:()=>stored};
}
async function ready(w){await new Promise(ok=>setTimeout(ok,65));}
async function submit(w,fn,name,extra={}){
 await w.eval(fn);
 const form=w.document.querySelector('.index-modal-form');
 assert.ok(form,fn+' should open an in-app dialog');
 const field=form.querySelector('[name="name"]');
 assert.ok(field);
 field.value=name;
 for(const [key,v]of Object.entries(extra)){const el=form.querySelector('[name="'+key+'"]');assert.ok(el);el.value=v;}
 form.dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));
 await ready(w);
 assert.equal(w.document.querySelector('.index-modal-form'),null,'dialog should close after saving');
}
test('Add Character opens real dialog, persists and opens profile',async()=>{const {w,dom,get}=fresh();await ready(w);await submit(w,'addCharacter()','Kieran');assert.equal(get().characters[0].name,'Kieran');assert.ok(w.document.getElementById('screen').textContent.includes('Kieran'));assert.ok(w.document.querySelector('.profile-aside'));dom.window.close();});
test('Add Story and Add Worldbuilding Entry work, preserving separate libraries',async()=>{const {w,dom,get}=fresh();await ready(w);await submit(w,"addCollection('stories')",'The Midnight Visitor',{category:'Writing'});await submit(w,"addCollection('worldbuilding')",'Thorn Valley',{category:'Location'});assert.equal(get().stories[0].name,'The Midnight Visitor');assert.equal(get().stories[0].status,'Writing');assert.equal(get().worldbuilding[0].name,'Thorn Valley');dom.window.close();});
test('Add Note and Add Tag work',async()=>{const {w,dom,get}=fresh();await ready(w);await submit(w,"indexNewNote()",'Research');await submit(w,"addTag()",'Found Family');assert.equal(get().notes[0].name,'Research');assert.equal(get().tags[0].name,'Found Family');dom.window.close();});
test('Cancel new record leaves data untouched',async()=>{const {w,dom,get}=fresh();await ready(w);await w.eval('addCharacter()');w.document.querySelector('.index-modal-actions button').click();assert.equal(get().characters.length,0);assert.equal(w.document.querySelector('.index-modal'),null);dom.window.close();});
test('Storage and edit features maintain data across screens',async()=>{const {w,dom,get}=fresh();await ready(w);await submit(w,'addCharacter()','Elias');await w.eval("indexMultiAdd(db.characters[0].id,'Positive Traits','Loyal')");assert.ok(get().characters[0].fields['Positive Traits'].includes('Loyal'));await w.eval("addRepeat(db.characters[0].id,'events')");assert.equal(get().characters[0].events.length,1);dom.window.close();});
test('Approved profile tabs remain present and Family excluded',async()=>{const {w,dom}=fresh();await ready(w);await submit(w,'addCharacter()','Thomas');const tabs=Array.from(w.eval('PROFILE'));assert.deepEqual(tabs,['Overview','Appearance','Personality','Background','Relationships','Skills','Story','Timeline','Notes']);assert.ok(w.document.querySelector('#recent-characters'));dom.window.close();});
