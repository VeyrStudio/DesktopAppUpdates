const { app, BrowserWindow, ipcMain, dialog, powerSaveBlocker, shell } = require("electron");
const fs = require("node:fs");
const fsp = require("node:fs/promises");
const path = require("node:path");
const crypto = require("node:crypto");
const { Readable, Transform } = require("node:stream");
const { pipeline } = require("node:stream/promises");
const { spawn } = require("node:child_process");
const { processLecture, enginePaths } = require("./processor.cjs");

const APP_DATA_ROOT = path.join(app.getPath("appData"), "VeyrStudio", "TheLedger");
app.setPath("userData", APP_DATA_ROOT);

const dataDir = path.join(APP_DATA_ROOT, "Data");
const recordingsDir = path.join(dataDir, "Recordings");
const importsDir = path.join(dataDir, "Imports");
const statePath = path.join(dataDir, "ledger-state.json");
const sessionsPath = path.join(dataDir, "recording-sessions.json");
const UPDATE_LAUNCH_ATTEMPTS = 6;
const UPDATE_LAUNCH_DELAY_MS = 2000;
const recordingSessions = new Map();
let mainWindow;
let sleepBlockerId = null;
let stagedUpdatePath = null;
let applyingUpdate = false;
let allowWindowClose = false;
let quittingForUpdate = false;

function emptyState() {
  return {
    schemaVersion: 1,
    classes: [],
    lectures: [],
    notifications: [],
    settings: {
      textSize: "medium",
      theme: "dark-academia",
      keepAudio: "manual",
      transcriptionMode: "balanced",
      localOnly: true,
      autoUpdate: true,
      hideLiveTranscript: false,
      reduceMotion: false,
      microphoneId: "default"
    }
  };
}

async function ensureDataFolders() {
  await Promise.all([
    fsp.mkdir(dataDir, { recursive: true }),
    fsp.mkdir(recordingsDir, { recursive: true }),
    fsp.mkdir(importsDir, { recursive: true })
  ]);
}

async function readJson(file, fallback) {
  try {
    return JSON.parse(await fsp.readFile(file, "utf8"));
  } catch (error) {
    if (error.code !== "ENOENT") console.error(`Could not read ${file}:`, error);
    return fallback;
  }
}

async function writeJsonAtomic(file, value) {
  const temp = `${file}.${process.pid}.tmp`;
  await fsp.writeFile(temp, JSON.stringify(value, null, 2), "utf8");
  await fsp.rename(temp, file);
}

async function loadState() {
  await ensureDataFolders();
  return readJson(statePath, emptyState());
}

async function saveState(value) {
  await ensureDataFolders();
  const normalized = {
    ...emptyState(),
    ...(value || {}),
    classes: Array.isArray(value?.classes) ? value.classes : [],
    lectures: Array.isArray(value?.lectures) ? value.lectures : [],
    notifications: Array.isArray(value?.notifications) ? value.notifications : [],
    settings: { ...emptyState().settings, ...(value?.settings || {}) }
  };
  await writeJsonAtomic(statePath, normalized);
  return { ok: true };
}

async function readSessions() {
  return readJson(sessionsPath, {});
}

async function updateSession(sessionId, patch) {
  const sessions = await readSessions();
  sessions[sessionId] = { ...(sessions[sessionId] || {}), ...patch };
  await writeJsonAtomic(sessionsPath, sessions);
}

async function recoverInterruptedRecordings() {
  const sessions = await readSessions();
  const interrupted = Object.values(sessions).filter((item) => !item.finalized && item.path && fs.existsSync(item.path));
  if (!interrupted.length) return;
  const state = await loadState();
  const existingIds = new Set(state.lectures.map((item) => item.id));
  for (const session of interrupted) {
    if (!existingIds.has(session.lectureId)) {
      state.lectures.unshift({
        id: session.lectureId,
        classId: session.classId || null,
        title: session.title || "Recovered lecture",
        date: session.date,
        time: session.time,
        status: "recovered",
        audioPath: session.path,
        notes: "",
        markers: [],
        originalTranscript: "",
        cleanedTranscript: "",
        review: {}
      });
    }
    session.finalized = true;
    session.recovered = true;
  }
  state.notifications.unshift({
    id: crypto.randomUUID(),
    kind: "warning",
    title: "Recording recovered",
    message: `${interrupted.length} interrupted lecture recording${interrupted.length === 1 ? " was" : "s were"} recovered.`,
    createdAt: new Date().toISOString(),
    read: false
  });
  await saveState(state);
  await writeJsonAtomic(sessionsPath, sessions);
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 760,
    minWidth: 900,
    minHeight: 620,
    show: false,
    backgroundColor: "#0b0b0d",
    title: "The Ledger",
    icon: path.join(__dirname, "..", "build", "icon.png"),
    autoHideMenuBar: true,
    frame: true,
    webPreferences: {
      preload: path.join(__dirname, "preload.cjs"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true
    }
  });

  mainWindow.loadFile(path.join(__dirname, "..", "src", "index.html"));
  mainWindow.once("ready-to-show", () => mainWindow.show());
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (/^https?:/i.test(url)) shell.openExternal(url);
    return { action: "deny" };
  });
  mainWindow.on("close", async (event) => {
    if (allowWindowClose || !recordingSessions.size) return;
    event.preventDefault();
    const answer = await dialog.showMessageBox(mainWindow, {
      type: "warning",
      title: "Lecture active",
      message: "The Ledger is still saving a lecture.",
      detail: "Choose whether to keep it running, finish the lecture, or return to the app.",
      buttons: ["Minimize and continue", "Finish lecture and close", "Cancel"],
      defaultId: 0,
      cancelId: 2,
      noLink: true
    });
    if (answer.response === 0) mainWindow.minimize();
    if (answer.response === 1) mainWindow.webContents.send("ledger:finish-and-close");
  });
}

app.whenReady().then(async () => {
  await ensureDataFolders();
  await recoverInterruptedRecordings();
  createWindow();
  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

app.on("before-quit", () => {
  if (sleepBlockerId !== null && powerSaveBlocker.isStarted(sleepBlockerId)) powerSaveBlocker.stop(sleepBlockerId);
  for (const session of recordingSessions.values()) {
    try { fs.closeSync(session.fd); } catch {}
  }
});

app.on("before-quit", (event) => {
  if (!stagedUpdatePath || applyingUpdate || quittingForUpdate || process.platform !== "win32") return;
  event.preventDefault();
  quittingForUpdate = true;
  void launchStagedUpdate().finally(() => {
    stagedUpdatePath = null;
    app.quit();
  });
});

function wait(delayMs) {
  return new Promise((resolve) => setTimeout(resolve, delayMs));
}

function spawnInstaller(installerPath) {
  return new Promise((resolve, reject) => {
    try {
      const child = spawn(installerPath, ["/S"], { detached: true, stdio: "ignore", windowsHide: true });
      child.once("error", reject);
      child.once("spawn", () => {
        child.unref();
        resolve();
      });
    } catch (error) {
      reject(error);
    }
  });
}

async function launchStagedUpdate() {
  if (!stagedUpdatePath || !fs.existsSync(stagedUpdatePath)) return { ok: false, message: "The verified update file is no longer available." };
  for (let attempt = 1; attempt <= UPDATE_LAUNCH_ATTEMPTS; attempt += 1) {
    try {
      await spawnInstaller(stagedUpdatePath);
      applyingUpdate = true;
      return { ok: true };
    } catch (error) {
      const canRetry = error?.code === "EBUSY" && attempt < UPDATE_LAUNCH_ATTEMPTS;
      if (!canRetry) return { ok: false, message: `The update could not start: ${error.message}` };
      await wait(UPDATE_LAUNCH_DELAY_MS);
    }
  }
  return { ok: false, message: "The update could not start." };
}

ipcMain.handle("ledger:load-state", loadState);
ipcMain.handle("ledger:save-state", (_event, state) => saveState(state));
ipcMain.handle("ledger:app-info", () => ({
  version: app.getVersion(),
  dataPath: dataDir,
  packaged: app.isPackaged,
  platform: process.platform,
  transcriptionAvailable: Boolean(enginePaths().whisper && enginePaths().model)
}));

ipcMain.handle("ledger:close-after-recording", () => {
  allowWindowClose = true;
  mainWindow.close();
  return { ok: true };
});

ipcMain.handle("ledger:process-lecture", async (event, { lectureId, audioPath }) => {
  try {
    const result = await processLecture(audioPath, (detail) => event.sender.send("ledger:processing-progress", { lectureId, ...detail }));
    return result;
  } catch (error) {
    return { ok: false, message: error.message };
  }
});

ipcMain.handle("ledger:choose-import", async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    title: "Import into The Ledger",
    properties: ["openFile", "multiSelections"],
    filters: [
      { name: "Supported files", extensions: ["mp3", "wav", "m4a", "aac", "flac", "mp4", "mov", "txt", "docx", "pdf"] },
      { name: "All files", extensions: ["*"] }
    ]
  });
  return result.canceled ? [] : result.filePaths;
});

ipcMain.handle("ledger:copy-import", async (_event, { sourcePath, lectureId }) => {
  await ensureDataFolders();
  const safeName = path.basename(sourcePath).replace(/[^a-zA-Z0-9._-]+/g, "-");
  const destination = path.join(importsDir, `${lectureId}-${safeName}`);
  await fsp.copyFile(sourcePath, destination);
  return { ok: true, path: destination, name: path.basename(sourcePath) };
});

ipcMain.handle("ledger:recording-start", async (_event, metadata) => {
  await ensureDataFolders();
  const sessionId = crypto.randomUUID();
  const extension = metadata.mimeType?.includes("ogg") ? "ogg" : "webm";
  const filePath = path.join(recordingsDir, `${metadata.lectureId}.${extension}`);
  const fd = fs.openSync(filePath, "a");
  recordingSessions.set(sessionId, { fd, path: filePath, lectureId: metadata.lectureId });
  await updateSession(sessionId, {
    ...metadata,
    sessionId,
    path: filePath,
    startedAt: new Date().toISOString(),
    finalized: false
  });
  return { ok: true, sessionId, path: filePath };
});

ipcMain.handle("ledger:recording-append", async (_event, { sessionId, bytes }) => {
  const session = recordingSessions.get(sessionId);
  if (!session) throw new Error("The recording session is no longer available.");
  const buffer = Buffer.from(bytes);
  fs.writeSync(session.fd, buffer);
  fs.fsyncSync(session.fd);
  return { ok: true, bytes: buffer.length };
});

ipcMain.handle("ledger:recording-finish", async (_event, { sessionId }) => {
  const session = recordingSessions.get(sessionId);
  if (!session) return { ok: false, message: "Recording session not found." };
  fs.fsyncSync(session.fd);
  fs.closeSync(session.fd);
  recordingSessions.delete(sessionId);
  await updateSession(sessionId, { finalized: true, finishedAt: new Date().toISOString() });
  return { ok: true, path: session.path };
});

ipcMain.handle("ledger:prevent-sleep", (_event, { enabled }) => {
  if (enabled && sleepBlockerId === null) sleepBlockerId = powerSaveBlocker.start("prevent-display-sleep");
  if (!enabled && sleepBlockerId !== null) {
    if (powerSaveBlocker.isStarted(sleepBlockerId)) powerSaveBlocker.stop(sleepBlockerId);
    sleepBlockerId = null;
  }
  return { ok: true };
});

ipcMain.handle("ledger:export-lecture", async (_event, { lectureId, payload }) => {
  const result = await dialog.showOpenDialog(mainWindow, {
    title: "Choose export folder",
    properties: ["openDirectory", "createDirectory"]
  });
  if (result.canceled || !result.filePaths[0]) return { ok: false, canceled: true };
  const safeTitle = String(payload.title || lectureId).replace(/[<>:"/\\|?*]+/g, "-").slice(0, 100);
  const folder = path.join(result.filePaths[0], safeTitle);
  await fsp.mkdir(folder, { recursive: true });
  const text = [
    payload.title,
    "",
    "CLEANED TRANSCRIPT",
    payload.cleanedTranscript || "",
    "",
    "YOUR NOTES",
    payload.notes || "",
    "",
    "SUMMARY",
    payload.review?.summary || ""
  ].join("\n");
  await Promise.all([
    fsp.writeFile(path.join(folder, "lecture.txt"), text, "utf8"),
    fsp.writeFile(path.join(folder, "lecture.json"), JSON.stringify(payload, null, 2), "utf8")
  ]);
  if (payload.audioPath && fs.existsSync(payload.audioPath)) {
    await fsp.copyFile(payload.audioPath, path.join(folder, path.basename(payload.audioPath)));
  }
  return { ok: true, folder };
});

ipcMain.handle("ledger:check-update", async (_event, { force }) => {
  const url = "https://raw.githubusercontent.com/VeyrStudio/DesktopAppUpdates/main/the-ledger/ledger.json";
  try {
    const response = await fetch(url, { cache: force ? "no-store" : "default" });
    if (!response.ok) throw new Error(`Update server returned ${response.status}.`);
    const manifest = await response.json();
    return { ok: true, currentVersion: app.getVersion(), manifest };
  } catch (error) {
    return { ok: false, currentVersion: app.getVersion(), message: error.message };
  }
});

ipcMain.handle("ledger:stage-update", async (event, { manifest }) => {
  try {
    if (recordingSessions.size) return { ok: false, message: "Finish the active lecture before updating." };
    if (!manifest?.url || !/^https:\/\//i.test(manifest.url)) throw new Error("The update manifest does not contain a secure download URL.");
    if (!/^[a-f0-9]{64}$/i.test(manifest.sha256 || "")) throw new Error("The update manifest does not contain a valid SHA-256 checksum.");
    const response = await fetch(manifest.url, { cache: "no-store" });
    if (!response.ok || !response.body) throw new Error(`Update download returned ${response.status}.`);
    const safeVersion = String(manifest.version || "update").replace(/[^a-z0-9._-]/gi, "-");
    const destination = path.join(app.getPath("temp"), `TheLedgerSetup-${safeVersion}-${process.pid}-${Date.now()}.exe`);
    const hash = crypto.createHash("sha256");
    let received = 0;
    const total = Number(response.headers.get("content-length") || 0);
    const meter = new Transform({
      transform(chunk, _encoding, callback) {
        received += chunk.length;
        hash.update(chunk);
        event.sender.send("ledger:processing-progress", { lectureId: null, stage: "update", message: total ? `Downloading update ${Math.round(received / total * 100)}%` : "Downloading update" });
        callback(null, chunk);
      }
    });
    await pipeline(Readable.fromWeb(response.body), meter, fs.createWriteStream(destination));
    const digest = hash.digest("hex");
    if (digest.toLowerCase() !== manifest.sha256.toLowerCase()) {
      await fsp.rm(destination, { force: true });
      throw new Error("The downloaded update did not pass verification.");
    }
    stagedUpdatePath = destination;
    return { ok: true, path: destination };
  } catch (error) {
    return { ok: false, message: error.message };
  }
});

ipcMain.handle("ledger:apply-staged-update", async () => {
  if (!stagedUpdatePath) return { ok: false, message: "No verified update is ready." };
  if (recordingSessions.size) return { ok: false, message: "Finish the active lecture before updating." };
  if (process.platform !== "win32") return { ok: false, message: "Updates can only be applied from the packaged Windows app." };
  const result = await launchStagedUpdate();
  if (!result.ok) return result;
  setImmediate(() => app.quit());
  return result;
});
