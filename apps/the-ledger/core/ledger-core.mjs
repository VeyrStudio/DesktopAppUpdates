const dateFormatter = new Intl.DateTimeFormat("en-US", {
  month: "long",
  day: "numeric",
  year: "numeric"
});

const timeFormatter = new Intl.DateTimeFormat("en-US", {
  hour: "numeric",
  minute: "2-digit"
});

export function toLocalDateKey(value = new Date()) {
  const date = value instanceof Date ? value : new Date(value);
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

export function formatLongDate(value) {
  const date = typeof value === "string" && /^\d{4}-\d{2}-\d{2}$/.test(value)
    ? new Date(`${value}T12:00:00`)
    : new Date(value);
  return dateFormatter.format(date);
}

export function formatTime(value) {
  if (!value) return "";
  if (/^\d{2}:\d{2}$/.test(value)) {
    const [hour, minute] = value.split(":").map(Number);
    const date = new Date(2000, 0, 1, hour, minute);
    return timeFormatter.format(date);
  }
  return timeFormatter.format(new Date(value));
}

export function makeLectureTitle({ date, time, className }) {
  return `${formatLongDate(date)} • ${formatTime(time)} • ${className || "Unassigned Class"}`;
}

export function isNewerVersion(candidate, current) {
  const parse = (value) => String(value || "")
    .split("-")[0]
    .split(".")
    .map((part) => Number.parseInt(part, 10))
    .map((part) => Number.isFinite(part) ? part : 0);
  const next = parse(candidate);
  const installed = parse(current);
  const length = Math.max(next.length, installed.length, 3);
  for (let index = 0; index < length; index += 1) {
    const difference = (next[index] || 0) - (installed[index] || 0);
    if (difference !== 0) return difference > 0;
  }
  return false;
}

export function uid(prefix = "item") {
  if (globalThis.crypto?.randomUUID) return `${prefix}-${globalThis.crypto.randomUUID()}`;
  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function minutesFromTime(value) {
  if (!/^\d{2}:\d{2}$/.test(value || "")) return Number.POSITIVE_INFINITY;
  const [h, m] = value.split(":").map(Number);
  return h * 60 + m;
}

export function classesForDate(classes, value = new Date()) {
  const day = value instanceof Date ? value.getDay() : new Date(value).getDay();
  return (classes || [])
    .filter((item) => (item.days || []).includes(day))
    .sort((a, b) => minutesFromTime(a.startTime) - minutesFromTime(b.startTime));
}

export function currentOrNextClass(classes, value = new Date()) {
  const now = value instanceof Date ? value : new Date(value);
  const currentMinutes = now.getHours() * 60 + now.getMinutes();
  const today = classesForDate(classes, now);
  return today.find((item) => minutesFromTime(item.endTime) >= currentMinutes) || today[0] || null;
}

export function searchLedger(state, rawQuery, filters = {}) {
  const query = String(rawQuery || "").trim().toLocaleLowerCase();
  if (!query) return [];
  const results = [];
  for (const lecture of state.lectures || []) {
    if (filters.classId && lecture.classId !== filters.classId) continue;
    const classItem = (state.classes || []).find((item) => item.id === lecture.classId);
    const fields = [
      ["title", lecture.title],
      ["original transcript", lecture.originalTranscript],
      ["cleaned transcript", lecture.cleanedTranscript],
      ["notes", lecture.notes],
      ["summary", lecture.review?.summary],
      ["key concepts", (lecture.review?.keyConcepts || []).join(" ")],
      ["definitions", (lecture.review?.definitions || []).map((x) => `${x.term} ${x.definition}`).join(" ")],
      ["assignments", (lecture.review?.assignments || []).map((x) => `${x.text} ${x.due || ""}`).join(" ")],
      ["possible test material", (lecture.review?.testMaterial || []).join(" ")]
    ];
    for (const [type, value] of fields) {
      const content = String(value || "");
      const index = content.toLocaleLowerCase().indexOf(query);
      if (index < 0) continue;
      const start = Math.max(0, index - 70);
      const end = Math.min(content.length, index + query.length + 110);
      results.push({
        lectureId: lecture.id,
        classId: lecture.classId,
        className: classItem?.name || "Unassigned Class",
        title: lecture.title,
        type,
        excerpt: `${start ? "…" : ""}${content.slice(start, end)}${end < content.length ? "…" : ""}`
      });
    }
  }
  return results;
}

export function removeLecture(state, lectureId) {
  return {
    ...state,
    lectures: (state?.lectures || []).filter((lecture) => lecture.id !== lectureId)
  };
}

export function applySpeakerMarks(segments, speakerMarks) {
  const marks = [...(speakerMarks || [])]
    .filter((mark) => Number.isFinite(Number(mark.seconds)) && mark.speaker)
    .sort((a, b) => Number(a.seconds) - Number(b.seconds));
  let markIndex = 0;
  let activeSpeaker = null;
  return (segments || []).map((segment) => {
    const segmentBoundary = Number(segment.end ?? segment.start ?? 0);
    while (markIndex < marks.length && Number(marks[markIndex].seconds) <= segmentBoundary) {
      activeSpeaker = marks[markIndex].speaker;
      markIndex += 1;
    }
    return activeSpeaker ? { ...segment, speaker: activeSpeaker } : { ...segment };
  });
}

export function setSegmentSpeaker(segments, segmentIndex, speaker) {
  return (segments || []).map((segment, index) => index === segmentIndex ? { ...segment, speaker } : { ...segment });
}

export function blankState() {
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

export function mergeState(input) {
  const base = blankState();
  return {
    ...base,
    ...(input || {}),
    classes: Array.isArray(input?.classes) ? input.classes : [],
    lectures: Array.isArray(input?.lectures) ? input.lectures : [],
    notifications: Array.isArray(input?.notifications) ? input.notifications : [],
    settings: { ...base.settings, ...(input?.settings || {}) }
  };
}
