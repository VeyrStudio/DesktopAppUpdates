import {
  blankState,
  mergeState,
  uid,
  toLocalDateKey,
  formatLongDate,
  formatTime,
  isNewerVersion,
  makeLectureTitle,
  classesForDate,
  currentOrNextClass,
  searchLedger,
  removeLecture,
  applySpeakerMarks
} from "../core/ledger-core.mjs";

const DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const COLORS = ["#6f3d60", "#57725e", "#506984", "#8d4d42", "#7b6540", "#5d5680"];
const SPEAKER_ROLES = ["Professor", "Me", "Student", "Guest Speaker"];

const appRoot = document.querySelector("#app");
const viewRoot = document.querySelector("#view");
const pageTitle = document.querySelector("#page-title");
const pageSubtitle = document.querySelector("#page-subtitle");
const modalBackdrop = document.querySelector("#modal-backdrop");
const modalRoot = document.querySelector("#modal");
const notificationPanel = document.querySelector("#notification-panel");
const notificationBadge = document.querySelector("#notification-badge");
const notificationList = document.querySelector("#notification-list");
const statusAnnouncer = document.querySelector("#status-announcer");

let state = blankState();
let currentView = "today";
let selectedClassId = null;
let selectedLectureId = null;
let settingsTab = "audio";
let searchQuery = "";
let reviewClassFilter = "";
let saveTimer = null;
let recording = null;
let recordingClock = null;
let elapsedSeconds = 0;
let appInfo = { version: "0.1.0", packaged: false };

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function demoState() {
  const now = new Date();
  const today = toLocalDateKey(now);
  const day = now.getDay();
  const classes = [
    { id: "demo-psych", name: "Introduction to Psychology", code: "PSY 101", professor: "Professor Morgan", room: "Room 204", days: [day], startTime: "09:00", endTime: "10:15", color: COLORS[0] },
    { id: "demo-history", name: "World History", code: "HIST 112", professor: "Professor Lee", room: "Room 305", days: [day], startTime: "13:30", endTime: "14:45", color: COLORS[2] }
  ];
  const lectureDate = new Date(now.getTime() - 86400000 * 2);
  const date = toLocalDateKey(lectureDate);
  const lectures = [{
    id: "demo-lecture",
    classId: classes[0].id,
    date,
    time: "09:00",
    title: makeLectureTitle({ date, time: "09:00", className: classes[0].name }),
    status: "ready",
    notes: "The professor emphasized that memory is reconstructive rather than a perfect recording.",
    markers: [{ type: "important", seconds: 634 }],
    originalTranscript: "Today we are going to talk about how memory is encoded, stored, and retrieved. Memory is reconstructive rather than a perfect recording of an event.",
    cleanedTranscript: "Today we are going to discuss how memory is encoded, stored, and retrieved. Memory is reconstructive rather than a perfect recording of an event.",
    transcriptSegments: [
      { start: 0, speaker: "Professor Morgan", text: "Today we are going to discuss how memory is encoded, stored, and retrieved." },
      { start: 18, speaker: "Professor Morgan", text: "Memory is reconstructive rather than a perfect recording of an event." }
    ],
    review: {
      summary: "An introduction to memory encoding, storage, retrieval, and the reconstructive nature of recall.",
      keyConcepts: ["Encoding", "Storage", "Retrieval", "Reconstructive memory"],
      definitions: [{ term: "Encoding", definition: "The process of converting information into a form that can be stored." }],
      assignments: [{ text: "Read Chapter 4", due: today }],
      testMaterial: ["Three stages of memory", "Why recall can be inaccurate"],
      unclearTopics: ["Difference between recall and recognition"]
    }
  }];
  return mergeState({ ...blankState(), classes, lectures });
}

function browserFallback() {
  let cache = JSON.parse(localStorage.getItem("the-ledger-preview") || "null") || demoState();
  return {
    loadState: async () => cache,
    saveState: async (next) => {
      cache = next;
      localStorage.setItem("the-ledger-preview", JSON.stringify(next));
      return { ok: true };
    },
    chooseImport: async () => [],
    copyImport: async () => ({ ok: false }),
    exportLecture: async () => ({ ok: false, canceled: true }),
    startRecording: async (metadata) => ({ ok: true, sessionId: uid("session"), path: `preview/${metadata.lectureId}.webm` }),
    appendRecording: async () => ({ ok: true }),
    finishRecording: async () => ({ ok: true, path: "preview/lecture.webm" }),
    processLecture: async () => ({ ok: false, unavailable: true, message: "Local engine is not part of the browser preview." }),
    deleteLectureFiles: async () => ({ ok: true }),
    checkForUpdates: async () => ({ ok: true, currentVersion: "0.1.0", manifest: { version: "0.1.0" } }),
    stageUpdate: async () => ({ ok: false, message: "Updates are available in the packaged Windows app." }),
    applyStagedUpdate: async () => ({ ok: false, message: "Updates are available in the packaged Windows app." }),
    closeAfterRecording: async () => ({ ok: true }),
    setPreventSleep: async () => ({ ok: true }),
    getAppInfo: async () => ({ version: "0.1.0", packaged: false, platform: "browser-preview" }),
    onRecordingError: () => {},
    onProcessingProgress: () => {},
    onFinishAndClose: () => {}
  };
}

const api = window.ledgerAPI || browserFallback();

async function initialize() {
  state = mergeState(await api.loadState());
  appInfo = await api.getAppInfo();
  appRoot.dataset.size = state.settings.textSize;
  document.body.classList.toggle("reduce-motion", state.settings.reduceMotion);
  document.querySelector("#sidebar-version").textContent = `v${appInfo.version}`;
  bindShell();
  updateNotificationBadge();
  render();
  checkAutomaticUpdate();
}

function bindShell() {
  document.querySelector("#main-nav").addEventListener("click", (event) => {
    const button = event.target.closest("[data-view]");
    if (!button) return;
    navigate(button.dataset.view);
  });
  document.querySelector("#quick-search").addEventListener("click", () => navigate("search"));
  document.querySelector("#notification-button").addEventListener("click", openNotifications);
  document.querySelector("[data-close-drawer]").addEventListener("click", closeNotifications);
  document.querySelector("#mark-all-read").addEventListener("click", async () => {
    state.notifications.forEach((item) => { item.read = true; });
    await persist();
    renderNotifications();
    updateNotificationBadge();
  });
  modalBackdrop.addEventListener("click", (event) => {
    if (event.target === modalBackdrop) closeModal();
  });
  window.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeModal();
      closeNotifications();
    }
    if (event.ctrlKey && event.key.toLowerCase() === "f") {
      event.preventDefault();
      navigate("search");
      queueMicrotask(() => document.querySelector("#ledger-search")?.focus());
    }
  });
  api.onRecordingError?.((message) => recordingError(message));
  api.onProcessingProgress?.(({ lectureId, message }) => {
    const lecture = lectureById(lectureId);
    if (lecture) lecture.processingMessage = message;
    if (selectedLectureId === lectureId) document.querySelector("#sidebar-status").textContent = message;
  });
  api.onFinishAndClose?.(async () => {
    if (recording) await finishLecture(true);
    else await api.closeAfterRecording();
  });
}

function navigate(view) {
  currentView = view;
  selectedClassId = view === "classes" ? selectedClassId : null;
  document.querySelectorAll(".nav-item").forEach((item) => item.classList.toggle("active", item.dataset.view === view));
  render();
  viewRoot.focus({ preventScroll: true });
}

function setHeader(title, subtitle = "") {
  pageTitle.textContent = title;
  pageSubtitle.textContent = subtitle;
}

function render() {
  if (currentView === "today") renderToday();
  if (currentView === "classes") renderClasses();
  if (currentView === "notebook") renderNotebook();
  if (currentView === "review") renderReview();
  if (currentView === "search") renderSearch();
  if (currentView === "settings") renderSettings();
}

function renderToday() {
  const now = new Date();
  const longDay = new Intl.DateTimeFormat("en-US", { weekday: "long", month: "long", day: "numeric", year: "numeric" }).format(now);
  setHeader("Today", longDay);
  const schedule = classesForDate(state.classes, now);
  const current = currentOrNextClass(state.classes, now);
  const recent = [...state.lectures].sort((a, b) => `${b.date}T${b.time}`.localeCompare(`${a.date}T${a.time}`)).slice(0, 5);
  const reviewItems = state.lectures.flatMap((lecture) => {
    const classItem = classById(lecture.classId);
    return [
      ...(lecture.review?.testMaterial || []).map((text) => ({ text, label: "Possible test material", className: classItem?.name })),
      ...(lecture.review?.unclearTopics || []).map((text) => ({ text, label: "Needs clarification", className: classItem?.name })),
      ...(lecture.review?.assignments || []).map((item) => ({ text: item.text, label: item.due ? `Due ${formatLongDate(item.due)}` : "Assignment", className: classItem?.name }))
    ];
  }).slice(0, 5);

  if (!state.classes.length) {
    viewRoot.innerHTML = `<section class="card empty-state">
      <div class="book-mark">▤</div><h2>Your ledger is ready</h2>
      <p>Add your first class. The Ledger will use its meeting time to prepare lecture titles automatically while keeping every class completely separate.</p>
      <button id="today-add-class" class="primary-button" type="button">Add First Class</button>
    </section>`;
    document.querySelector("#today-add-class").addEventListener("click", () => showClassModal());
    return;
  }

  viewRoot.innerHTML = `<div class="view-grid">
    <div class="stack">
      ${current ? currentClassCard(current) : `<section class="card empty-state"><h2>No class scheduled right now</h2><p>You can still open the Notebook and begin an unscheduled lecture.</p><button class="primary-button" id="open-notebook">Open Notebook</button></section>`}
      <section class="card">
        <div class="card-header"><h2>Today's Schedule</h2><button class="text-button" id="edit-classes">Manage classes</button></div>
        <div class="schedule-list">${schedule.length ? schedule.map(scheduleRow).join("") : `<div class="card-body"><p class="row-subtitle">No classes are scheduled today.</p></div>`}</div>
      </section>
    </div>
    <div class="stack">
      <section class="card">
        <div class="card-header"><h2>Recent Lectures</h2><button class="text-button" data-go="notebook">View all</button></div>
        <div class="lecture-list">${recent.length ? recent.map(lectureRow).join("") : `<div class="card-body"><p class="row-subtitle">Saved lectures will appear here.</p></div>`}</div>
      </section>
      <section class="card">
        <div class="card-header"><h2>Things to Review</h2><button class="text-button" data-go="review">View all</button></div>
        <div class="review-list">${reviewItems.length ? reviewItems.map((item) => `<div class="review-row"><div><div class="row-title">${escapeHtml(item.text)}</div><div class="row-subtitle">${escapeHtml(item.className || "Class")} • ${escapeHtml(item.label)}</div></div></div>`).join("") : `<div class="card-body"><p class="row-subtitle">Important material extracted from lectures will appear here.</p></div>`}</div>
      </section>
    </div>
  </div>`;
  document.querySelector("#start-current")?.addEventListener("click", () => startLecture(current.id));
  document.querySelector("#open-notebook")?.addEventListener("click", () => navigate("notebook"));
  document.querySelector("#edit-classes")?.addEventListener("click", () => navigate("classes"));
  bindLectureRows();
  bindGoButtons();
}

function currentClassCard(item) {
  return `<section class="card current-class" style="--class-color:${escapeHtml(item.color || COLORS[0])}">
    <div class="card-body">
      <span class="eyebrow">Current or Next Class</span>
      <h2>${escapeHtml(item.name)}</h2>
      <div class="class-details">
        <div class="class-detail"><span>◷</span><span>${escapeHtml(formatTime(item.startTime))} – ${escapeHtml(formatTime(item.endTime))}</span></div>
        <div class="class-detail"><span>⌾</span><span>${escapeHtml(item.room || "Location not set")}</span></div>
        <div class="class-detail"><span>♙</span><span>${escapeHtml(item.professor || "Professor not set")}</span></div>
      </div>
      <div class="button-row"><button id="start-current" class="primary-button" type="button">Start Notes</button></div>
    </div>
  </section>`;
}

function scheduleRow(item) {
  return `<div class="schedule-row" style="--class-color:${escapeHtml(item.color || COLORS[0])}">
    <div class="schedule-time">${escapeHtml(formatTime(item.startTime))}<br><span class="row-subtitle">${escapeHtml(formatTime(item.endTime))}</span></div>
    <div><div class="row-title">${escapeHtml(item.name)}</div><div class="row-subtitle">${escapeHtml(item.room || "No location")} • ${escapeHtml(item.professor || "No professor")}</div></div>
  </div>`;
}

function lectureRow(lecture) {
  return `<button class="lecture-row" data-lecture-id="${escapeHtml(lecture.id)}" type="button">
    <span class="file-icon">▧</span>
    <span><span class="row-title">${escapeHtml(lecture.title)}</span><span class="row-subtitle">${escapeHtml(lecture.review?.summary || statusText(lecture.status))}</span></span>
    <span class="row-chevron">›</span>
  </button>`;
}

function renderClasses() {
  if (selectedClassId) return renderClassDetail();
  setHeader("Classes", `${state.classes.length} class${state.classes.length === 1 ? "" : "es"} in your ledger`);
  viewRoot.innerHTML = `<div class="section-heading">
    <div><h2>Your Classes</h2><p>Each class keeps its lectures, notes, files, and professor voice profile together.</p></div>
    <div class="toolbar"><button id="add-class" class="primary-button" type="button">Add Class</button></div>
  </div>
  ${state.classes.length ? `<div class="class-grid">${state.classes.map(classCard).join("")}</div>` : `<section class="card empty-state"><div class="book-mark">▤</div><h2>No classes yet</h2><p>Add a class manually to begin.</p><button id="empty-add-class" class="primary-button">Add Class</button></section>`}`;
  document.querySelector("#add-class")?.addEventListener("click", () => showClassModal());
  document.querySelector("#empty-add-class")?.addEventListener("click", () => showClassModal());
  document.querySelectorAll("[data-class-id]").forEach((button) => button.addEventListener("click", () => {
    selectedClassId = button.dataset.classId;
    renderClasses();
  }));
}

function classCard(item) {
  const lectures = state.lectures.filter((lecture) => lecture.classId === item.id);
  const newest = [...lectures].sort((a, b) => b.date.localeCompare(a.date))[0];
  return `<button class="card class-card" style="--class-color:${escapeHtml(item.color || COLORS[0])}" data-class-id="${escapeHtml(item.id)}" type="button">
    <div class="card-body">
      <span class="course-code">${escapeHtml(item.code || "COURSE")}</span>
      <h3>${escapeHtml(item.name)}</h3>
      <div class="row-subtitle">${escapeHtml(item.professor || "Professor not set")}</div>
      <dl><dt>Schedule</dt><dd>${escapeHtml((item.days || []).map((day) => DAYS[day]).join(", ") || "Not set")} • ${escapeHtml(formatTime(item.startTime))}</dd>
      <dt>Lectures</dt><dd>${lectures.length}</dd>
      <dt>Most recent</dt><dd>${newest ? escapeHtml(formatLongDate(newest.date)) : "None yet"}</dd></dl>
    </div>
  </button>`;
}

function renderClassDetail() {
  const item = classById(selectedClassId);
  if (!item) { selectedClassId = null; return renderClasses(); }
  setHeader(item.name, [item.code, item.professor].filter(Boolean).join(" • "));
  const lectures = state.lectures.filter((lecture) => lecture.classId === item.id).sort((a, b) => `${b.date}${b.time}`.localeCompare(`${a.date}${a.time}`));
  const assignments = lectures.flatMap((lecture) => (lecture.review?.assignments || []).map((assignment) => ({ ...assignment, lecture })));
  viewRoot.innerHTML = `<div class="section-heading"><div><button id="back-classes" class="text-button">‹ All classes</button></div><div class="toolbar"><button id="edit-class" class="secondary-button">Edit Class</button><button id="class-start" class="primary-button">Start Notes</button></div></div>
  <div class="view-grid">
    <div class="stack">
      <section class="card"><div class="card-header"><h2>Lectures</h2></div><div class="lecture-list">${lectures.length ? lectures.map(lectureRow).join("") : `<div class="card-body"><p class="row-subtitle">No lectures saved for this class.</p></div>`}</div></section>
      <section class="card"><div class="card-header"><h2>Assignments</h2></div><div class="review-list">${assignments.length ? assignments.map((item) => `<div class="review-row"><div><div class="row-title">${escapeHtml(item.text)}</div><div class="row-subtitle">${item.due ? `Due ${escapeHtml(formatLongDate(item.due))}` : "No due date"} • ${escapeHtml(item.lecture.title)}</div></div></div>`).join("") : `<div class="card-body"><p class="row-subtitle">Assignments detected in lectures will appear here.</p></div>`}</div></section>
    </div>
    <div class="stack">
      <section class="card"><div class="card-header"><h2>Overview</h2></div><div class="card-body class-details">
        <div class="class-detail"><span>◷</span><span>${escapeHtml((item.days || []).map((day) => DAYS[day]).join(", "))} • ${escapeHtml(formatTime(item.startTime))} – ${escapeHtml(formatTime(item.endTime))}</span></div>
        <div class="class-detail"><span>⌾</span><span>${escapeHtml(item.room || "Location not set")}</span></div>
        <div class="class-detail"><span>♙</span><span>${escapeHtml(item.professor || "Professor not set")}</span></div>
      </div></section>
      <section class="card"><div class="card-header"><h2>Speaker Labels</h2></div><div class="card-body"><p class="row-subtitle">During an active lecture, use Identify Voice in the Notebook to mark the Professor, Me, a Student, or a Guest Speaker.</p></div></section>
      <section class="card"><div class="card-header"><h2>Files</h2></div><div class="card-body"><p class="row-subtitle">Attach handouts, slides, readings, and reference documents from the Notebook import menu.</p></div></section>
    </div>
  </div>`;
  document.querySelector("#back-classes").addEventListener("click", () => { selectedClassId = null; renderClasses(); });
  document.querySelector("#edit-class").addEventListener("click", () => showClassModal(item));
  document.querySelector("#class-start").addEventListener("click", () => startLecture(item.id));
  bindLectureRows();
}

function renderNotebook() {
  setHeader("Notebook", "");
  const lecture = selectedLectureId ? lectureById(selectedLectureId) : null;
  if (!lecture) return renderNotebookStart();
  const classItem = classById(lecture.classId);
  const segments = lecture.transcriptSegments || transcriptToSegments(lecture.cleanedTranscript || lecture.originalTranscript);
  const currentSpeaker = [...(lecture.speakerMarks || [])].sort((a, b) => a.seconds - b.seconds).at(-1)?.speaker;
  viewRoot.innerHTML = `<div class="notebook-layout">
    <section class="card notebook-page">
      <div class="notebook-header"><div><span class="eyebrow">${escapeHtml(classItem?.code || "LECTURE")}</span><h2>${escapeHtml(lecture.title)}</h2></div>${recording ? `<span id="active-indicator" class="active-indicator">Active</span>` : `<span class="status-pill ${lecture.status === "recovered" ? "error" : ""}">${escapeHtml(statusText(lecture.status))}</span>`}</div>
      <div class="transcript-area" id="transcript-area">${segments.length ? segments.map(transcriptSegment).join("") : `<div class="empty-state"><div class="book-mark">▧</div><h2>${recording ? "Listening" : "No transcript yet"}</h2><p>${recording ? "The original audio is being saved safely. Live text will appear when the local transcription engine is available." : "Import or process audio to create a transcript. Your original recording remains available."}</p></div>`}</div>
    </section>
    <section class="card notes-panel">
      <div class="card-header"><h2>Your Notes</h2><span class="status-pill">Autosaved</span></div>
      <textarea id="lecture-notes" placeholder="Type your own notes here…">${escapeHtml(lecture.notes || "")}</textarea>
      <div class="marker-toolbar ${recording ? "has-voice-control" : ""}"><button data-marker="important">◆ Important</button><button data-marker="assignment">▣ Assignment</button><button data-marker="test">◇ Test Material</button>${recording ? `<button id="identify-voice">♙ ${currentSpeaker ? `Voice: ${escapeHtml(currentSpeaker)}` : "Identify Voice"}</button>` : ""}</div>
    </section>
  </div>
  <div class="notebook-controls">
    <div class="toolbar"><button id="notebook-back" class="secondary-button">All Lectures</button><button id="export-lecture" class="secondary-button">Export</button>${recording ? "" : `<button id="delete-lecture" class="danger-button">Delete Lecture</button>`}</div>
    ${recording ? `<div class="toolbar"><span id="lecture-timer" class="timer">00:00:00</span><button id="pause-recording" class="secondary-button">Pause</button><button id="finish-recording" class="danger-button">Finish</button></div>` : `<div class="toolbar"><button id="listen-audio" class="secondary-button" ${lecture.audioPath ? "" : "disabled"}>Play Audio</button></div>`}
  </div>`;
  document.querySelector("#lecture-notes").addEventListener("input", (event) => {
    lecture.notes = event.target.value;
    schedulePersist();
  });
  document.querySelectorAll("[data-marker]").forEach((button) => button.addEventListener("click", () => addMarker(lecture, button.dataset.marker)));
  document.querySelector("#identify-voice")?.addEventListener("click", () => showIdentifyVoiceModal(lecture, elapsedSeconds));
  document.querySelector("#notebook-back").addEventListener("click", () => { selectedLectureId = null; renderNotebook(); });
  document.querySelector("#export-lecture").addEventListener("click", () => exportLecture(lecture));
  document.querySelector("#delete-lecture")?.addEventListener("click", () => confirmDeleteLecture(lecture));
  document.querySelector("#pause-recording")?.addEventListener("click", pauseOrResumeRecording);
  document.querySelector("#finish-recording")?.addEventListener("click", () => finishLecture(false));
  document.querySelector("#listen-audio")?.addEventListener("click", () => toast("Audio playback controls will open from the packaged recording file."));
  updateTimerDisplay();
}

function renderNotebookStart() {
  const recent = [...state.lectures].sort((a, b) => `${b.date}${b.time}`.localeCompare(`${a.date}${a.time}`));
  viewRoot.innerHTML = `<div class="view-grid">
    <div class="stack">
      <section class="card"><div class="card-header"><h2>Begin a Lecture</h2></div><div class="card-body">
        ${state.classes.length ? `<div class="form-group"><label for="notebook-class">Class</label><select id="notebook-class" class="field">${state.classes.map((item) => `<option value="${escapeHtml(item.id)}">${escapeHtml(item.name)}</option>`).join("")}</select></div><div class="button-row"><button id="begin-notes" class="primary-button">Start Notes</button><button id="import-recording" class="secondary-button">Import Notes or Lecture</button></div>` : `<div class="empty-state"><h2>Add a class first</h2><p>The Ledger needs a class to title and file each lecture.</p><button id="notebook-add-class" class="primary-button">Add Class</button></div>`}
      </div></section>
      <section class="card"><div class="card-header"><h2>Saved Lectures</h2></div><div class="lecture-list">${recent.length ? recent.map(lectureRow).join("") : `<div class="card-body"><p class="row-subtitle">No saved lectures yet.</p></div>`}</div></section>
    </div>
    <details class="card before-class-card"><summary class="card-header"><h2>Before Class</h2><span class="details-chevron" aria-hidden="true">⌄</span></summary><div class="card-body class-details">
      <div class="class-detail"><span>1</span><span>Choose the class.</span></div><div class="class-detail"><span>2</span><span>Check that the correct microphone is selected.</span></div><div class="class-detail"><span>3</span><span>Select Start Notes. Your lecture is saved continuously in small chunks.</span></div>
    </div></details>
  </div>`;
  document.querySelector("#begin-notes")?.addEventListener("click", () => startLecture(document.querySelector("#notebook-class").value));
  document.querySelector("#import-recording")?.addEventListener("click", () => importRecording(document.querySelector("#notebook-class").value));
  document.querySelector("#notebook-add-class")?.addEventListener("click", () => showClassModal());
  bindLectureRows();
}

async function startLecture(classId) {
  const classItem = classById(classId);
  if (!classItem) return toast("Add or choose a class first.", true);
  if (recording) return toast("A lecture is already active.", true);
  const now = new Date();
  const date = toLocalDateKey(now);
  const time = `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}`;
  const lecture = {
    id: uid("lecture"), classId, date, time,
    title: makeLectureTitle({ date, time, className: classItem.name }),
    status: "starting", notes: "", markers: [], speakerMarks: [], originalTranscript: "", cleanedTranscript: "", transcriptSegments: [], review: {}
  };
  state.lectures.unshift(lecture);
  selectedLectureId = lecture.id;
  currentView = "notebook";
  document.querySelectorAll(".nav-item").forEach((item) => item.classList.toggle("active", item.dataset.view === "notebook"));
  await persist();
  renderNotebook();
  try {
    const constraints = state.settings.microphoneId && state.settings.microphoneId !== "default"
      ? { audio: { deviceId: { exact: state.settings.microphoneId }, echoCancellation: true, noiseSuppression: true } }
      : { audio: { echoCancellation: true, noiseSuppression: true } };
    const stream = await navigator.mediaDevices.getUserMedia(constraints);
    const mimeType = ["audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus"].find((type) => MediaRecorder.isTypeSupported(type)) || "";
    const mediaRecorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream);
    const session = await api.startRecording({ lectureId: lecture.id, classId, title: lecture.title, date, time, mimeType: mediaRecorder.mimeType });
    let writeChain = Promise.resolve();
    mediaRecorder.addEventListener("dataavailable", (event) => {
      if (!event.data.size) return;
      writeChain = writeChain.then(async () => {
        const bytes = new Uint8Array(await event.data.arrayBuffer());
        return api.appendRecording(session.sessionId, bytes);
      }).catch((error) => recordingError(error.message));
    });
    mediaRecorder.addEventListener("error", (event) => recordingError(event.error?.message || "The microphone stopped unexpectedly."));
    recording = { mediaRecorder, stream, sessionId: session.sessionId, writeChain, startedAt: Date.now(), pausedAt: null, totalPaused: 0 };
    Object.defineProperty(recording, "writeChain", { get: () => writeChain, set: (value) => { writeChain = value; } });
    lecture.status = "active";
    lecture.audioPath = session.path;
    elapsedSeconds = 0;
    await api.setPreventSleep(true);
    mediaRecorder.start(2000);
    startClock();
    await persist();
    renderNotebook();
  } catch (error) {
    lecture.status = "audio-error";
    addNotification("Microphone unavailable", error.message || "The Ledger could not start the microphone.", "error");
    await persist();
    renderNotebook();
    toast("The microphone could not be started.", true);
  }
}

function startClock() {
  clearInterval(recordingClock);
  recordingClock = setInterval(() => {
    elapsedSeconds += 1;
    updateTimerDisplay();
  }, 1000);
}

function updateTimerDisplay() {
  const element = document.querySelector("#lecture-timer");
  if (!element) return;
  const h = String(Math.floor(elapsedSeconds / 3600)).padStart(2, "0");
  const m = String(Math.floor((elapsedSeconds % 3600) / 60)).padStart(2, "0");
  const s = String(elapsedSeconds % 60).padStart(2, "0");
  element.textContent = `${h}:${m}:${s}`;
}

function pauseOrResumeRecording() {
  if (!recording) return;
  const button = document.querySelector("#pause-recording");
  if (recording.mediaRecorder.state === "recording") {
    recording.mediaRecorder.pause();
    clearInterval(recordingClock);
    button.textContent = "Resume";
    document.querySelector("#active-indicator").textContent = "Paused";
  } else if (recording.mediaRecorder.state === "paused") {
    recording.mediaRecorder.resume();
    startClock();
    button.textContent = "Pause";
    document.querySelector("#active-indicator").textContent = "Active";
  }
}

async function finishLecture(closeAfter = false) {
  if (!recording) return;
  const lecture = lectureById(selectedLectureId);
  const current = recording;
  clearInterval(recordingClock);
  try {
    await new Promise((resolve) => {
      current.mediaRecorder.addEventListener("stop", resolve, { once: true });
      current.mediaRecorder.stop();
    });
    await current.writeChain;
    const result = await api.finishRecording(current.sessionId);
    current.stream.getTracks().forEach((track) => track.stop());
    recording = null;
    await api.setPreventSleep(false);
    lecture.status = "saved";
    lecture.audioPath = result.path || lecture.audioPath;
    lecture.durationSeconds = elapsedSeconds;
    addNotification("Lecture saved", lecture.title, "success");
    await persist();
    renderNotebook();
    toast("Lecture saved safely.");
    processSavedLecture(lecture);
    if (closeAfter) await api.closeAfterRecording();
  } catch (error) {
    recordingError(error.message);
  }
}

function recordingError(message) {
  clearInterval(recordingClock);
  const lecture = lectureById(selectedLectureId);
  if (lecture) lecture.status = "audio-error";
  document.querySelector("#active-indicator")?.classList.add("error");
  addNotification("Recording needs attention", message || "The microphone stopped unexpectedly.", "error");
  persist();
  toast(message || "Recording error.", true);
}

async function importRecording(classId) {
  const paths = await api.chooseImport();
  if (!paths.length) return;
  const classItem = classById(classId);
  const now = new Date();
  for (const sourcePath of paths) {
    const date = toLocalDateKey(now);
    const time = `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}`;
    const lecture = { id: uid("lecture"), classId, date, time, title: makeLectureTitle({ date, time, className: classItem.name }), status: "importing", notes: "", markers: [], originalTranscript: "", cleanedTranscript: "", review: {} };
    const copied = await api.copyImport(sourcePath, lecture.id);
    lecture.importName = sourcePath.split(/[\\/]/).pop();
    lecture.audioPath = copied.path;
    lecture.status = "saved";
    state.lectures.unshift(lecture);
    selectedLectureId = lecture.id;
  }
  addNotification("Import complete", `${paths.length} file${paths.length === 1 ? "" : "s"} added to ${classItem.name}.`, "success");
  await persist();
  renderNotebook();
  for (const lecture of state.lectures.filter((item) => paths.some((sourcePath) => item.importName === sourcePath.split(/[\\/]/).pop()))) processSavedLecture(lecture);
}

async function processSavedLecture(lecture) {
  if (!lecture?.audioPath || lecture.status === "processing" || lecture.status === "ready") return;
  lecture.status = "processing";
  await persist();
  if (selectedLectureId === lecture.id) renderNotebook();
  const result = await api.processLecture(lecture.id, lecture.audioPath);
  if (!result.ok) {
    lecture.status = result.unavailable ? "saved" : "processing-error";
    if (!result.unavailable) addNotification("Lecture processing failed", result.message || lecture.title, "error");
    await persist();
    if (selectedLectureId === lecture.id) renderNotebook();
    return;
  }
  lecture.originalTranscript = result.originalTranscript;
  lecture.cleanedTranscript = result.cleanedTranscript;
  lecture.transcriptSegments = applySpeakerMarks(result.transcriptSegments, lecture.speakerMarks);
  lecture.review = result.review;
  lecture.status = "ready";
  lecture.processingMessage = "";
  addNotification("Lecture ready", lecture.title, "success");
  document.querySelector("#sidebar-status").textContent = "Ready";
  await persist();
  if (selectedLectureId === lecture.id) renderNotebook();
}

function addMarker(lecture, type) {
  lecture.markers ||= [];
  lecture.markers.push({ id: uid("marker"), type, seconds: elapsedSeconds, createdAt: new Date().toISOString() });
  schedulePersist();
  toast(`${type === "test" ? "Possible test material" : type[0].toUpperCase() + type.slice(1)} marked at ${formatDuration(elapsedSeconds)}.`);
}

function showIdentifyVoiceModal(lecture, atSeconds) {
  showModal(`<div class="modal-header"><div><span class="eyebrow">IDENTIFY VOICE</span><h2>Who is speaking?</h2></div><button class="icon-button" data-close-modal type="button">×</button></div>
    <div class="modal-body"><p>Select the person speaking now. The transcript will use this label until you identify someone else.</p><div class="speaker-choice-grid">${SPEAKER_ROLES.map((role) => `<button class="speaker-choice" data-speaker-role="${escapeHtml(role)}" type="button">${escapeHtml(role)}</button>`).join("")}</div></div>
    <div class="modal-footer"><button class="secondary-button" data-close-modal type="button">Cancel</button></div>`);
  document.querySelectorAll("[data-speaker-role]").forEach((button) => button.addEventListener("click", async () => {
    const speaker = button.dataset.speakerRole;
    lecture.speakerMarks ||= [];
    lecture.speakerMarks.push({ id: uid("speaker"), speaker, seconds: atSeconds, createdAt: new Date().toISOString() });
    await persist();
    closeModal();
    renderNotebook();
    toast(`${speaker} identified at ${formatDuration(atSeconds)}.`);
  }));
}

async function exportLecture(lecture) {
  const result = await api.exportLecture(lecture.id, lecture);
  if (result.ok) toast("Lecture exported.");
}

function confirmDeleteLecture(lecture) {
  if (recording && selectedLectureId === lecture.id) return toast("Finish the active lecture before deleting it.", true);
  if (lecture.status === "processing") return toast("Wait for this lecture to finish processing before deleting it.", true);
  showModal(`<div class="modal-header"><div><span class="eyebrow">CONFIRM DELETION</span><h2>Delete this lecture?</h2></div><button class="icon-button" data-close-modal type="button">×</button></div>
    <div class="modal-body"><p><strong>${escapeHtml(lecture.title)}</strong></p><p>This permanently removes its transcript, notes, extracted information, and locally stored audio. This cannot be undone.</p><p id="delete-lecture-error" class="row-subtitle"></p></div>
    <div class="modal-footer"><button class="secondary-button" data-close-modal type="button">Cancel</button><button id="confirm-delete-lecture" class="danger-button" type="button">Delete Lecture</button></div>`);
  document.querySelector("#confirm-delete-lecture").addEventListener("click", async (event) => {
    const button = event.currentTarget;
    button.disabled = true;
    button.textContent = "Deleting…";
    const result = await api.deleteLectureFiles(lecture.id, lecture.audioPath || "");
    if (!result.ok) {
      const error = document.querySelector("#delete-lecture-error");
      error.textContent = result.message || "The lecture could not be deleted.";
      error.classList.add("error");
      button.disabled = false;
      button.textContent = "Delete Lecture";
      return;
    }
    state = removeLecture(state, lecture.id);
    selectedLectureId = null;
    await persist();
    closeModal();
    renderNotebook();
    toast("Lecture deleted.");
  });
}

function renderReview() {
  setHeader("Review", "Lecture material organized for reference");
  const lectures = state.lectures.filter((lecture) => !reviewClassFilter || lecture.classId === reviewClassFilter);
  const withReview = lectures.filter((lecture) => lecture.review && Object.values(lecture.review).some((value) => Array.isArray(value) ? value.length : Boolean(value)));
  viewRoot.innerHTML = `<div class="section-heading"><div><h2>Review Material</h2><p>Summaries and extracted information only—study tools remain separate.</p></div><div class="toolbar"><select id="review-filter" class="field"><option value="">All classes</option>${state.classes.map((item) => `<option value="${escapeHtml(item.id)}" ${item.id === reviewClassFilter ? "selected" : ""}>${escapeHtml(item.name)}</option>`).join("")}</select></div></div>
  ${withReview.length ? `<div class="stack">${withReview.map(reviewCard).join("")}</div>` : `<section class="card empty-state"><div class="book-mark">◇</div><h2>No review material yet</h2><p>After a lecture is processed, its summary, concepts, definitions, assignments, and possible test material will appear here.</p></section>`}`;
  document.querySelector("#review-filter").addEventListener("change", (event) => { reviewClassFilter = event.target.value; renderReview(); });
  bindLectureRows();
}

function reviewCard(lecture) {
  const review = lecture.review || {};
  const list = (items, empty = "None detected") => items?.length ? `<ul>${items.map((item) => `<li>${escapeHtml(typeof item === "string" ? item : item.text)}</li>`).join("")}</ul>` : `<p class="row-subtitle">${empty}</p>`;
  return `<section class="card"><div class="card-header"><h2>${escapeHtml(lecture.title)}</h2><button class="text-button" data-lecture-id="${escapeHtml(lecture.id)}">Open lecture</button></div><div class="card-body">
    ${review.summary ? `<h3>Summary</h3><p>${escapeHtml(review.summary)}</p>` : ""}
    <div class="class-grid">
      <div><h3>Key Concepts</h3>${list(review.keyConcepts)}</div>
      <div><h3>Assignments</h3>${list(review.assignments)}</div>
      <div><h3>Possible Test Material</h3>${list(review.testMaterial)}</div>
      <div><h3>Needs Clarification</h3>${list(review.unclearTopics)}</div>
    </div>
  </div></section>`;
}

function renderSearch() {
  setHeader("Search", "Search every lecture, transcript, note, and extracted item");
  const results = searchLedger(state, searchQuery);
  viewRoot.innerHTML = `<div class="search-bar"><input id="ledger-search" class="search-input" type="search" value="${escapeHtml(searchQuery)}" placeholder="Search The Ledger…"><button id="run-search" class="primary-button">Search</button></div>
  <div class="search-results">${searchQuery ? (results.length ? results.map(searchResult).join("") : `<section class="card empty-state"><h2>No results</h2><p>Try another word or a broader spelling.</p></section>`) : `<section class="card empty-state"><div class="book-mark">⌕</div><h2>Find anything said in class</h2><p>Search original and cleaned transcripts, your notes, summaries, concepts, assignments, and possible test material.</p></section>`}</div>`;
  const input = document.querySelector("#ledger-search");
  const run = () => { searchQuery = input.value.trim(); renderSearch(); queueMicrotask(() => document.querySelector("#ledger-search")?.focus()); };
  document.querySelector("#run-search").addEventListener("click", run);
  input.addEventListener("keydown", (event) => { if (event.key === "Enter") run(); });
  bindLectureRows();
}

function searchResult(result) {
  return `<button class="card search-result" data-lecture-id="${escapeHtml(result.lectureId)}" type="button"><span class="result-meta">${escapeHtml(result.className)} • ${escapeHtml(result.type)}</span><h3>${escapeHtml(result.title)}</h3><p>${highlight(result.excerpt, searchQuery)}</p></button>`;
}

function highlight(value, query) {
  const safe = escapeHtml(value);
  if (!query) return safe;
  const escapedQuery = query.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return safe.replace(new RegExp(`(${escapedQuery})`, "ig"), "<mark>$1</mark>");
}

function renderSettings() {
  setHeader("Settings", "Audio, transcription, storage, appearance, privacy, and updates");
  const tabs = [
    ["audio", "Audio & Transcription"], ["classes", "Classes & Schedule"], ["processing", "Processing"],
    ["privacy", "Storage & Privacy"], ["appearance", "Appearance"], ["updates", "Updates"]
  ];
  viewRoot.innerHTML = `<div class="settings-layout">
    <aside class="card settings-menu">${tabs.map(([id, label]) => `<button class="${settingsTab === id ? "active" : ""}" data-settings-tab="${id}">${label}</button>`).join("")}</aside>
    <section class="card settings-content">${settingsContent()}</section>
  </div>`;
  document.querySelectorAll("[data-settings-tab]").forEach((button) => button.addEventListener("click", () => { settingsTab = button.dataset.settingsTab; renderSettings(); }));
  bindSettingsControls();
}

function settingsContent() {
  const s = state.settings;
  if (settingsTab === "audio") return `<span class="eyebrow">AUDIO & TRANSCRIPTION</span><h2>Lecture Audio</h2>
    ${settingSelect("microphoneId", "Microphone", "Choose the input used for lecture capture.", [["default", "System Default"]])}
    ${settingToggle("hideLiveTranscript", "Hide live transcript", "Keep the Notebook visually quiet while audio continues safely.")}
    ${settingSelect("transcriptionMode", "Local model", "Choose the balance between speed and accuracy.", [["fast","Fast"],["balanced","Balanced (Recommended)"],["accurate","Highest Accuracy"]])}
    <div class="setting-row"><div><h3>Microphone test</h3><p>Confirm that The Ledger can hear the selected input before class.</p></div><button id="test-microphone" class="secondary-button">Run Test</button></div>`;
  if (settingsTab === "classes") return `<span class="eyebrow">CLASSES & SCHEDULE</span><h2>Class Management</h2>
    <div class="setting-row"><div><h3>Classes are independent</h3><p>The Ledger does not connect to or import from other applications.</p></div><button id="manage-classes" class="secondary-button">Manage Classes</button></div>
    ${settingToggle("suggestCurrentClass", "Suggest current class", "Use the schedules entered directly in The Ledger to select the likely class.")}`;
  if (settingsTab === "processing") return `<span class="eyebrow">PROCESSING</span><h2>After Each Lecture</h2>
    ${settingToggle("localOnly", "Local-only processing", "Never upload lecture audio. This remains enabled by default.")}
    ${settingToggle("autoClean", "Clean transcripts automatically", "Preserve the original while creating a readable corrected copy.")}
    ${settingToggle("autoExtract", "Extract lecture information", "Create summaries, concepts, definitions, assignments, and possible test material.")}`;
  if (settingsTab === "privacy") return `<span class="eyebrow">STORAGE & PRIVACY</span><h2>Your Data</h2>
    ${settingSelect("keepAudio", "Original audio", "Choose how long untouched lecture recordings are retained.", [["manual","Keep until I delete it"],["reviewed","Delete after transcript review"],["30","Delete after 30 days"],["90","Delete after 90 days"]])}
    ${settingToggle("lockWhenMinimized", "Lock when minimized", "Require your selected app lock method when reopening.")}
    <div class="setting-row"><div><h3>Data location</h3><p>${escapeHtml(appInfo.dataPath || "VeyrStudio\\TheLedger")}</p></div><span class="status-pill">Protected from updates</span></div>`;
  if (settingsTab === "appearance") return `<span class="eyebrow">APPEARANCE</span><h2>Reading Comfort</h2>
    ${settingSelect("textSize", "Text size", "Adjust the interface, transcript, and typed-note sizes together.", [["small","Small"],["medium","Medium (Recommended)"],["large","Large"]])}
    ${settingToggle("reduceMotion", "Reduce motion", "Disable nonessential interface movement.")}
    <div class="setting-row"><div><h3>Theme</h3><p>Modern dark academia using ink black, aubergine, ivory, and antique gold.</p></div><span class="status-pill">Dark Academia</span></div>`;
  return `<span class="eyebrow">UPDATES</span><h2>The Ledger ${escapeHtml(appInfo.version)}</h2>
    ${settingToggle("autoUpdate", "Automatic updates", "Check, verify, and apply new versions without touching lecture data.")}
    <div class="setting-row"><div><h3>Force Update</h3><p>Check the update channel immediately instead of waiting for the automatic schedule.</p></div><button id="force-update" class="primary-button">Force Update</button></div>
    <div id="update-result" class="setting-row"><div><h3>Update channel</h3><p>ledger • Independent version and payload</p></div><span class="status-pill">Ready</span></div>`;
}

function settingToggle(key, title, description) {
  return `<div class="setting-row"><div><h3>${escapeHtml(title)}</h3><p>${escapeHtml(description)}</p></div><label class="toggle"><input type="checkbox" data-setting="${escapeHtml(key)}" ${state.settings[key] ? "checked" : ""}><span></span></label></div>`;
}

function settingSelect(key, title, description, options) {
  return `<div class="setting-row"><div><h3>${escapeHtml(title)}</h3><p>${escapeHtml(description)}</p></div><select class="field" data-setting="${escapeHtml(key)}">${options.map(([value, label]) => `<option value="${escapeHtml(value)}" ${state.settings[key] === value ? "selected" : ""}>${escapeHtml(label)}</option>`).join("")}</select></div>`;
}

function bindSettingsControls() {
  document.querySelectorAll("[data-setting]").forEach((input) => input.addEventListener("change", async () => {
    state.settings[input.dataset.setting] = input.type === "checkbox" ? input.checked : input.value;
    if (input.dataset.setting === "textSize") appRoot.dataset.size = input.value;
    if (input.dataset.setting === "reduceMotion") document.body.classList.toggle("reduce-motion", input.checked);
    await persist();
  }));
  document.querySelector("#manage-classes")?.addEventListener("click", () => navigate("classes"));
  document.querySelector("#test-microphone")?.addEventListener("click", testMicrophone);
  document.querySelector("#force-update")?.addEventListener("click", forceUpdate);
}

async function testMicrophone() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const context = new AudioContext();
    const source = context.createMediaStreamSource(stream);
    const analyser = context.createAnalyser();
    source.connect(analyser);
    await new Promise((resolve) => setTimeout(resolve, 1000));
    const values = new Uint8Array(analyser.frequencyBinCount);
    analyser.getByteFrequencyData(values);
    const level = values.reduce((sum, value) => sum + value, 0) / values.length;
    stream.getTracks().forEach((track) => track.stop());
    await context.close();
    toast(level > 0 ? "Microphone test passed." : "The microphone connected, but no sound was detected.", level === 0);
  } catch (error) { toast(`Microphone test failed: ${error.message}`, true); }
}

async function forceUpdate() {
  const button = document.querySelector("#force-update");
  button.disabled = true;
  button.textContent = "Checking…";
  const result = await api.checkForUpdates(true);
  button.disabled = false;
  button.textContent = "Force Update";
  const target = document.querySelector("#update-result .status-pill");
  if (!result.ok) {
    target.textContent = "Could not check";
    target.classList.add("error");
    addNotification("Update check could not complete", result.message, "warning");
    await persist();
    return;
  }
  if (!result.manifest?.version || !isNewerVersion(result.manifest.version, result.currentVersion)) {
    target.textContent = "Latest version";
    toast("You already have the latest version.");
  } else {
    target.textContent = `Downloading ${result.manifest.version}`;
    const staged = await api.stageUpdate(result.manifest);
    if (!staged.ok) {
      target.textContent = "Update failed";
      target.classList.add("error");
      addNotification("Update could not be prepared", staged.message, "error");
      await persist();
      return;
    }
    target.textContent = "Installing…";
    addNotification("Update verified", `The Ledger ${result.manifest.version} will install now.`, "update");
    await persist();
    const applied = await api.applyStagedUpdate();
    if (!applied.ok) toast(applied.message, true);
  }
}

async function checkAutomaticUpdate() {
  if (!state.settings.autoUpdate || !appInfo.packaged || recording) return;
  const result = await api.checkForUpdates(false);
  if (!result.ok || !result.manifest?.version || !isNewerVersion(result.manifest.version, result.currentVersion)) return;
  const staged = await api.stageUpdate(result.manifest);
  if (!staged.ok) {
    addNotification("Automatic update needs attention", staged.message, "warning");
    await persist();
    return;
  }
  addNotification("Update ready", `The Ledger ${result.manifest.version} was downloaded and verified. It will install when you close the app.`, "update");
  await persist();
}

function showClassModal(existing = null) {
  const item = existing || { color: COLORS[state.classes.length % COLORS.length], days: [] };
  showModal(`<div class="modal-header"><div><span class="eyebrow">THE LEDGER</span><h2>${existing ? "Edit Class" : "Add Class"}</h2></div><button class="icon-button" data-close-modal>×</button></div>
    <form id="class-form"><div class="modal-body"><div class="form-grid">
      <div class="form-group full"><label>Class Name</label><input class="field" name="name" required value="${escapeHtml(item.name || "")}" placeholder="Introduction to Psychology"></div>
      <div class="form-group"><label>Course Code</label><input class="field" name="code" value="${escapeHtml(item.code || "")}" placeholder="PSY 101"></div>
      <div class="form-group"><label>Professor</label><input class="field" name="professor" value="${escapeHtml(item.professor || "")}" placeholder="Professor Morgan"></div>
      <div class="form-group"><label>Room or Location</label><input class="field" name="room" value="${escapeHtml(item.room || "")}" placeholder="Room 204"></div>
      <div class="form-group"><label>Class Color</label><input class="field" type="color" name="color" value="${escapeHtml(item.color || COLORS[0])}"></div>
      <div class="form-group full"><label>Meeting Days</label><div class="days">${DAYS.map((day, index) => `<label class="day-chip"><input type="checkbox" name="day" value="${index}" ${(item.days || []).includes(index) ? "checked" : ""}><span>${day[0]}</span></label>`).join("")}</div></div>
      <div class="form-group"><label>Start Time</label><input class="field" type="time" name="startTime" required value="${escapeHtml(item.startTime || "09:00")}"></div>
      <div class="form-group"><label>End Time</label><input class="field" type="time" name="endTime" required value="${escapeHtml(item.endTime || "10:15")}"></div>
    </div></div><div class="modal-footer">${existing ? `<button class="danger-button" id="delete-class" type="button">Delete Class</button>` : ""}<button class="secondary-button" data-close-modal type="button">Cancel</button><button class="primary-button" type="submit">Save Class</button></div></form>`);
  document.querySelector("#class-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const next = {
      ...item,
      id: item.id || uid("class"),
      name: form.get("name").trim(), code: form.get("code").trim(), professor: form.get("professor").trim(), room: form.get("room").trim(), color: form.get("color"),
      days: form.getAll("day").map(Number), startTime: form.get("startTime"), endTime: form.get("endTime")
    };
    if (existing) state.classes[state.classes.findIndex((value) => value.id === existing.id)] = next;
    else state.classes.push(next);
    await persist();
    closeModal();
    if (currentView === "classes") { selectedClassId = existing ? next.id : null; renderClasses(); } else render();
  });
  document.querySelector("#delete-class")?.addEventListener("click", () => confirmDeleteClass(item));
}

function confirmDeleteClass(item) {
  const lectureCount = state.lectures.filter((lecture) => lecture.classId === item.id).length;
  showModal(`<div class="modal-header"><div><span class="eyebrow">CONFIRM</span><h2>Remove ${escapeHtml(item.name)}?</h2></div><button class="icon-button" data-close-modal>×</button></div><div class="modal-body"><p>${lectureCount ? `This class has ${lectureCount} lecture${lectureCount === 1 ? "" : "s"}. They will be kept and marked as unassigned.` : "This class has no saved lectures."}</p></div><div class="modal-footer"><button class="secondary-button" data-close-modal>Cancel</button><button id="confirm-delete-class" class="danger-button">Remove Class</button></div>`);
  document.querySelector("#confirm-delete-class").addEventListener("click", async () => {
    state.classes = state.classes.filter((value) => value.id !== item.id);
    state.lectures.forEach((lecture) => { if (lecture.classId === item.id) lecture.classId = null; });
    selectedClassId = null;
    await persist(); closeModal(); renderClasses();
  });
}

function showModal(content) {
  modalRoot.innerHTML = content;
  modalBackdrop.hidden = false;
  modalRoot.querySelectorAll("[data-close-modal]").forEach((button) => button.addEventListener("click", closeModal));
  queueMicrotask(() => modalRoot.querySelector("input,select,button")?.focus());
}

function closeModal() { modalBackdrop.hidden = true; modalRoot.innerHTML = ""; }

function openNotifications() {
  notificationPanel.hidden = false;
  renderNotifications();
}
function closeNotifications() { notificationPanel.hidden = true; }

function renderNotifications() {
  notificationList.innerHTML = state.notifications.length ? state.notifications.map((item) => `<article class="notification-item ${item.read ? "" : "unread"}" data-notification-id="${escapeHtml(item.id)}"><h3>${escapeHtml(item.title)}</h3><p>${escapeHtml(item.message)}</p><time>${escapeHtml(new Date(item.createdAt).toLocaleString())}</time></article>`).join("") : `<div class="empty-state"><h2>All clear</h2><p>The Ledger has nothing requiring your attention.</p></div>`;
  state.notifications.forEach((item) => { item.read = true; });
  persist();
  updateNotificationBadge();
}

function addNotification(title, message, kind = "info") {
  state.notifications.unshift({ id: uid("notification"), title, message, kind, createdAt: new Date().toISOString(), read: false });
  state.notifications = state.notifications.slice(0, 100);
  updateNotificationBadge();
}

function updateNotificationBadge() {
  const unread = state.notifications.filter((item) => !item.read).length;
  notificationBadge.hidden = unread === 0;
  notificationBadge.textContent = unread > 99 ? "99+" : String(unread);
}

function toast(message, error = false) {
  const status = document.querySelector("#sidebar-status");
  status.textContent = message;
  status.classList.toggle("error", error);
  statusAnnouncer.textContent = message;
  window.setTimeout(() => {
    if (status.textContent === message) {
      status.textContent = recording ? "Recording" : "Ready";
      status.classList.remove("error");
    }
  }, 4000);
}

function bindLectureRows() {
  document.querySelectorAll("[data-lecture-id]").forEach((button) => button.addEventListener("click", () => {
    selectedLectureId = button.dataset.lectureId;
    currentView = "notebook";
    document.querySelectorAll(".nav-item").forEach((item) => item.classList.toggle("active", item.dataset.view === "notebook"));
    renderNotebook();
  }));
}

function bindGoButtons() {
  document.querySelectorAll("[data-go]").forEach((button) => button.addEventListener("click", () => navigate(button.dataset.go)));
}

function classById(id) { return state.classes.find((item) => item.id === id); }
function lectureById(id) { return state.lectures.find((item) => item.id === id); }

function transcriptToSegments(text) {
  if (!text) return [];
  return text.split(/\n{2,}/).filter(Boolean).map((value, index) => ({ start: index * 30, speaker: "Professor", text: value }));
}

function transcriptSegment(segment) {
  return `<div class="transcript-line"><button class="timestamp text-button" type="button">${escapeHtml(formatDuration(segment.start || 0))}</button><div><span class="speaker">${escapeHtml(segment.speaker || "Unknown Speaker")}</span>${escapeHtml(segment.text)}</div></div>`;
}

function formatDuration(seconds = 0) {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

function statusText(status) {
  return ({ active: "Active", starting: "Starting", saved: "Saved", queued: "Queued", processing: "Processing", ready: "Ready", recovered: "Recovered", "audio-error": "Audio issue", "processing-error": "Processing issue", importing: "Importing" })[status] || "Saved";
}

function schedulePersist() {
  clearTimeout(saveTimer);
  saveTimer = setTimeout(persist, 350);
}

async function persist() {
  await api.saveState(state);
}

initialize().catch((error) => {
  console.error(error);
  viewRoot.innerHTML = `<section class="card empty-state"><h2>The Ledger could not open</h2><p>${escapeHtml(error.message)}</p></section>`;
});
