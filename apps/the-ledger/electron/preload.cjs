const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("ledgerAPI", {
  loadState: () => ipcRenderer.invoke("ledger:load-state"),
  saveState: (state) => ipcRenderer.invoke("ledger:save-state", state),
  chooseImport: () => ipcRenderer.invoke("ledger:choose-import"),
  copyImport: (sourcePath, lectureId) => ipcRenderer.invoke("ledger:copy-import", { sourcePath, lectureId }),
  exportLecture: (lectureId, payload) => ipcRenderer.invoke("ledger:export-lecture", { lectureId, payload }),
  startRecording: (metadata) => ipcRenderer.invoke("ledger:recording-start", metadata),
  appendRecording: (sessionId, bytes) => ipcRenderer.invoke("ledger:recording-append", { sessionId, bytes }),
  finishRecording: (sessionId) => ipcRenderer.invoke("ledger:recording-finish", { sessionId }),
  processLecture: (lectureId, audioPath) => ipcRenderer.invoke("ledger:process-lecture", { lectureId, audioPath }),
  deleteLectureFiles: (lectureId, audioPath) => ipcRenderer.invoke("ledger:delete-lecture-files", { lectureId, audioPath }),
  checkForUpdates: (force = false) => ipcRenderer.invoke("ledger:check-update", { force }),
  stageUpdate: (manifest) => ipcRenderer.invoke("ledger:stage-update", { manifest }),
  applyStagedUpdate: () => ipcRenderer.invoke("ledger:apply-staged-update"),
  closeAfterRecording: () => ipcRenderer.invoke("ledger:close-after-recording"),
  setPreventSleep: (enabled) => ipcRenderer.invoke("ledger:prevent-sleep", { enabled }),
  getAppInfo: () => ipcRenderer.invoke("ledger:app-info"),
  onRecordingError: (callback) => ipcRenderer.on("ledger:recording-error", (_event, message) => callback(message)),
  onProcessingProgress: (callback) => ipcRenderer.on("ledger:processing-progress", (_event, detail) => callback(detail)),
  onFinishAndClose: (callback) => ipcRenderer.on("ledger:finish-and-close", () => callback())
});
