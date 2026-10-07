use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::{fs, process::Command};
use tauri::{AppHandle, Manager};

const UPDATE_MANIFEST: &str = "https://raw.githubusercontent.com/VeyrStudio/DesktopAppUpdates/main/constellation/latest.json";

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct UpdateManifest {
    version: String,
    url: String,
    sha256: String,
    notes: Option<String>,
    published_at: Option<String>,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
struct UpdateCheck {
    current_version: String,
    available: bool,
    update: Option<UpdateManifest>,
}

#[tauri::command]
fn app_version(app: AppHandle) -> String {
    app.package_info().version.to_string()
}

#[tauri::command]
fn check_for_update(app: AppHandle) -> Result<UpdateCheck, String> {
    let current = app.package_info().version.clone();
    let response = reqwest::blocking::get(UPDATE_MANIFEST)
        .map_err(|e| format!("Could not check for updates: {e}"))?;
    if !response.status().is_success() {
        return Err(format!("Update server returned {}", response.status()));
    }
    let manifest: UpdateManifest = response
        .json()
        .map_err(|e| format!("Could not read update information: {e}"))?;
    let newest = semver::Version::parse(&manifest.version)
        .map_err(|e| format!("Invalid update version: {e}"))?;
    Ok(UpdateCheck {
        current_version: current.to_string(),
        available: newest > current,
        update: if newest > current { Some(manifest) } else { None },
    })
}

#[tauri::command]
fn install_update(app: AppHandle, url: String, sha256: String) -> Result<(), String> {
    let response = reqwest::blocking::get(&url)
        .map_err(|e| format!("Could not download update: {e}"))?;
    if !response.status().is_success() {
        return Err(format!("Update download returned {}", response.status()));
    }
    let bytes = response.bytes().map_err(|e| format!("Could not read update: {e}"))?;
    let actual = hex::encode(Sha256::digest(&bytes));
    if actual.to_lowercase() != sha256.trim().to_lowercase() {
        return Err("The downloaded update failed its integrity check.".into());
    }

    let installer = std::env::temp_dir().join("ConstellationUpdate.exe");
    fs::write(&installer, &bytes).map_err(|e| format!("Could not save update: {e}"))?;

    Command::new(&installer)
        .arg("/S")
        .spawn()
        .map_err(|e| format!("Could not start updater: {e}"))?;

    app.exit(0);
    Ok(())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![app_version, check_for_update, install_update])
        .run(tauri::generate_context!())
        .expect("error while running Constellation");
}
