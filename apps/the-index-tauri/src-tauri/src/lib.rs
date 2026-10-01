use tauri::Manager;
use serde_json::{json,Value};
use std::{fs,io,io::Write,path::{Path,PathBuf},process::Command};
use chrono::Utc;
use base64::Engine;
use sha2::{Sha256,Digest};

fn root(app:&tauri::AppHandle)->Result<PathBuf,String>{
 let base=app.path().app_data_dir().map_err(|e|e.to_string())?;
 fs::create_dir_all(&base).map_err(|e|e.to_string())?;
 let loc=base.join("location.json");
 if let Ok(b)=fs::read_to_string(loc){
   if let Ok(v)=serde_json::from_str::<Value>(&b){
     if let Some(p)=v.get("path").and_then(Value::as_str){return Ok(PathBuf::from(p));}
   }
 }
 Ok(base)
}
fn archive_path(app:&tauri::AppHandle)->Result<PathBuf,String>{Ok(root(app)?.join("archive.json"))}
fn initial()->Value{json!({"schema":1,"characters":[],"stories":[],"worldbuilding":[],"notes":[],"tags":[],"events":[],"settings":{"theme":"Forest","accent":"#12392c","font":"Typewriter","scale":"Medium","autoUpdates":true}})}
fn save_atomic(path:&Path,data:&[u8])->Result<(),String>{
 if let Some(parent)=path.parent(){fs::create_dir_all(parent).map_err(|e|e.to_string())?;}
 let temp=path.with_extension("json.tmp");
 {let mut file=fs::File::create(&temp).map_err(|e|e.to_string())?;file.write_all(data).and_then(|_|file.sync_all()).map_err(|e|e.to_string())?;}
 fs::rename(&temp,path).map_err(|e|e.to_string())
}
fn migrate_from_electron(app:&tauri::AppHandle,path:&Path)->Result<(),String>{
 if path.exists(){return Ok(())}
 if let Ok(roaming)=std::env::var("APPDATA"){
  for app_name in ["the-index","The Index","the-index-desktop"]{
   let old=PathBuf::from(&roaming).join(app_name).join("data").join("archive.json");
   if let Ok(bytes)=fs::read(&old){
    if let Ok(value)=serde_json::from_slice::<Value>(&bytes){
      if value.get("characters").and_then(Value::as_array).is_some(){
       save_atomic(path,&bytes)?;
       let folder=app.path().app_data_dir().map_err(|e|e.to_string())?;
       fs::write(folder.join("migrated-from-electron.txt"),format!("Copied from {}\nOriginal preserved.",old.display())).map_err(|e|e.to_string())?;
       return Ok(());
      }
    }
   }
  }
 }
 save_atomic(path,serde_json::to_vec_pretty(&initial()).map_err(|e|e.to_string())?.as_slice())
}
#[tauri::command]
fn read_archive(app:tauri::AppHandle)->Result<Value,String>{
 let path=archive_path(&app)?;
 migrate_from_electron(&app,&path)?;
 let bytes=fs::read(&path).map_err(|e|e.to_string())?;
 serde_json::from_slice(&bytes).map_err(|e|format!("Archive could not be read: {e}. The original file was not changed."))
}
#[tauri::command]
fn save_archive(app:tauri::AppHandle,data:Value)->Result<Value,String>{
 if !data.get("characters").is_some_and(Value::is_array){return Err("Invalid archive: missing characters array".into())}
 if !data.get("stories").is_some_and(Value::is_array){return Err("Invalid archive: missing stories array".into())}
 let path=archive_path(&app)?;
 let bytes=serde_json::to_vec_pretty(&data).map_err(|e|e.to_string())?;
 save_atomic(&path,&bytes)?;
 Ok(data)
}
fn backup_existing(app:&tauri::AppHandle)->Result<String,String>{
 let path=archive_path(app)?;
 migrate_from_electron(app,&path)?;
 let folder=root(app)?.join("backups");
 fs::create_dir_all(&folder).map_err(|e|e.to_string())?;
 let filename=format!("the-index-{}.json",Utc::now().format("%Y%m%d-%H%M%S-%3f"));
 let target=folder.join(filename);
 fs::copy(&path,&target).map_err(|e|e.to_string())?;
 Ok(target.to_string_lossy().to_string())
}
#[tauri::command]fn backup_archive(app:tauri::AppHandle)->Result<String,String>{backup_existing(&app)}
#[tauri::command]fn data_folder(app:tauri::AppHandle)->Result<String,String>{let folder=root(&app)?;#[cfg(target_os="windows")]Command::new("explorer").arg(&folder).spawn().map_err(|e|e.to_string())?;Ok(folder.to_string_lossy().to_string())}
#[tauri::command]fn open_backups(app:tauri::AppHandle)->Result<String,String>{let folder=root(&app)?.join("backups");fs::create_dir_all(&folder).map_err(|e|e.to_string())?;#[cfg(target_os="windows")]Command::new("explorer").arg(&folder).spawn().map_err(|e|e.to_string())?;Ok(folder.to_string_lossy().to_string())}
#[tauri::command]
fn choose_image()->Result<Option<String>,String>{
 let path=rfd::FileDialog::new().add_filter("Images",&["png","jpg","jpeg","webp","gif"]).pick_file();
 let Some(p)=path else{return Ok(None)};
 let bytes=fs::read(&p).map_err(|e|e.to_string())?;
 if bytes.len()>12*1024*1024{return Err("Images must be under 12 MB. Please resize this picture.".into());}
 let ext=p.extension().and_then(|x|x.to_str()).unwrap_or("").to_lowercase();
 let mime=match ext.as_str(){"png"=>"image/png","webp"=>"image/webp","gif"=>"image/gif",_=>"image/jpeg"};
 Ok(Some(format!("data:{};base64,{}",mime,base64::engine::general_purpose::STANDARD.encode(bytes))))
}
#[tauri::command]
fn export_archive(app:tauri::AppHandle)->Result<Option<String>,String>{
 let path=archive_path(&app)?;
 migrate_from_electron(&app,&path)?;
 let target=rfd::FileDialog::new().add_filter("JSON Archive",&["json"]).set_file_name("The-Index-Backup.json").save_file();
 let Some(target)=target else{return Ok(None)};
 fs::copy(path,&target).map_err(|e|e.to_string())?;
 Ok(Some(target.to_string_lossy().to_string()))
}
#[tauri::command]
fn import_archive(app:tauri::AppHandle)->Result<Option<Value>,String>{
 let Some(path)=rfd::FileDialog::new().add_filter("JSON Archive",&["json"]).pick_file()else{return Ok(None)};
 let bytes=fs::read(path).map_err(|e|e.to_string())?;
 let value:Value=serde_json::from_slice(&bytes).map_err(|e|format!("Invalid JSON archive: {e}"))?;
 for key in ["characters","stories","worldbuilding","notes","tags"]{if !value.get(key).is_some_and(Value::is_array){return Err(format!("Archive missing {} records",key))}}
 backup_existing(&app)?;
 save_atomic(&archive_path(&app)?,&bytes)?;
 Ok(Some(value))
}
#[tauri::command]
fn change_folder(app:tauri::AppHandle)->Result<Option<String>,String>{
 let Some(dir)=rfd::FileDialog::new().pick_folder()else{return Ok(None)};
 let current=archive_path(&app)?;
 migrate_from_electron(&app,&current)?;
 let dest=dir.join("The Index Data");
 if dest.join("archive.json").exists(){return Err("This folder already contains a character archive. Select a different folder.".into())}
 fs::create_dir_all(&dest).map_err(|e|e.to_string())?;
 fs::copy(&current,dest.join("archive.json")).map_err(|e|e.to_string())?;
 let base=app.path().app_data_dir().map_err(|e|e.to_string())?;
 save_atomic(&base.join("location.json"),serde_json::to_vec(&json!({"path":dest.to_string_lossy()})).map_err(|e|e.to_string())?.as_slice())?;
 Ok(Some(dest.to_string_lossy().to_string()))
}
#[tauri::command]fn version()->String{env!("CARGO_PKG_VERSION").into()}
#[tauri::command]
fn check_update()->Result<Value,String>{
 let url="https://raw.githubusercontent.com/VeyrStudio/DesktopAppUpdates/main/the-index/latest.json";
 let response=ureq::get(url).set("User-Agent","TheIndex-Tauri/0.3").call().map_err(|e|format!("Cannot connect to update server: {e}"))?;
 let manifest:Value=response.into_json().map_err(|e|e.to_string())?;
 let version=manifest.get("version").and_then(Value::as_str);
 let Some(remote)=version else{return Ok(json!({"status":"up-to-date"}))};
 let parse=|s:&str|->Vec<u64>{s.split('.').map(|p|p.parse().unwrap_or(0)).collect()};
 if parse(remote).as_slice()<=parse(env!("CARGO_PKG_VERSION")).as_slice(){return Ok(json!({"status":"up-to-date"}))}
 if manifest.get("appId").and_then(Value::as_str)!=Some("the-index"){return Err("Update manifest identifies a different app".into())}
 Ok(json!({"status":"available","version":remote}))
}
#[tauri::command]
fn download_update()->Result<Value,String>{
 let url="https://raw.githubusercontent.com/VeyrStudio/DesktopAppUpdates/main/the-index/latest.json";
 let manifest:Value=ureq::get(url).set("User-Agent","TheIndex-Tauri/0.3").call().map_err(|e|e.to_string())?.into_json().map_err(|e|e.to_string())?;
 let v=manifest.get("version").and_then(Value::as_str).ok_or("No published update")?;
 if !v.chars().all(|c|c.is_ascii_digit()||c=='.'){return Err("Invalid release version".into())}
 let url=format!("https://github.com/VeyrStudio/DesktopAppUpdates/releases/download/the-index-v{v}/TheIndexSetup-{v}.exe");
 if manifest.get("url").and_then(Value::as_str)!=Some(url.as_str()){return Err("Update download URL mismatch".into())}
 let expected=manifest.get("sha256").and_then(Value::as_str).ok_or("Missing update checksum")?;
 let response=ureq::get(&url).set("User-Agent","TheIndex-Tauri/0.3").call().map_err(|e|e.to_string())?;
 let mut bytes=Vec::new();response.into_reader().take(200*1024*1024).read_to_end(&mut bytes).map_err(|e|e.to_string())?;
 let actual=format!("{:x}",Sha256::digest(&bytes));
 if actual!=expected.to_lowercase(){return Err("Installer checksum mismatch; installation cancelled".into())}
 let dest=std::env::temp_dir().join(format!("TheIndexSetup-{v}.exe"));
 fs::write(&dest,bytes).map_err(|e|e.to_string())?;
 Ok(json!({"status":"downloaded","version":v,"path":dest.to_string_lossy()}))
}
#[tauri::command]
fn install_update(path:String)->Result<Value,String>{
 let p=PathBuf::from(path);
 if !p.starts_with(std::env::temp_dir())||p.extension().and_then(|x|x.to_str())!=Some("exe")||!p.file_name().and_then(|x|x.to_str()).unwrap_or("").starts_with("TheIndexSetup-"){return Err("Invalid update installer".into())}
 Command::new(&p).spawn().map_err(|e|e.to_string())?;
 Ok(json!({"status":"installing"}))
}
pub fn run(){
 tauri::Builder::default()
 .invoke_handler(tauri::generate_handler![read_archive,save_archive,backup_archive,data_folder,open_backups,choose_image,export_archive,import_archive,change_folder,version,check_update,download_update,install_update])
 .run(tauri::generate_context!())
 .expect("error while launching The Index");
}
