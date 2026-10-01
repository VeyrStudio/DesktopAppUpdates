const fs = require('node:fs');
const path = require('node:path');
const DEFAULT = {schema:1,characters:[],stories:[],worldbuilding:[],notes:[],tags:[],events:[],settings:{theme:'Forest',accent:'#12392c',font:'Typewriter',scale:'Medium',backgroundImages:true,customFrame:true,animations:true,portraits:true,compactSidebar:false,sounds:false,autoUpdates:true,backgroundDownloads:false,updateAlerts:true,backupReminder:true,backupFrequency:'Weekly'}};
function normalize(data){return {...structuredClone(DEFAULT),...data,settings:{...DEFAULT.settings,...(data?.settings||{})}};}
function createStore(dir){
  fs.mkdirSync(dir,{recursive:true}); const filename=path.join(dir,'archive.json');
  let data=structuredClone(DEFAULT);
  if(fs.existsSync(filename)){ try {data=normalize(JSON.parse(fs.readFileSync(filename,'utf8')));}catch(e){fs.copyFileSync(filename,filename+'.damaged-'+Date.now());} }
  function save(next){ data=normalize(next); const tmp=filename+'.tmp';fs.writeFileSync(tmp,JSON.stringify(data,null,2));fs.renameSync(tmp,filename);return data;}
  if(!fs.existsSync(filename))save(data);
  function backup(){const dir2=path.join(dir,'backups');fs.mkdirSync(dir2,{recursive:true});const name='the-index-'+new Date().toISOString().replace(/[:.]/g,'-')+'.json';const target=path.join(dir2,name);fs.copyFileSync(filename,target);return target;}
  return {read:()=>structuredClone(data),save,backup,filename,dir};
}
module.exports={createStore,normalize,DEFAULT};
