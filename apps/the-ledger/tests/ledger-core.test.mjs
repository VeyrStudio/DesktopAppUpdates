import test from "node:test";
import assert from "node:assert/strict";
import {
  applySpeakerMarks,
  blankState,
  classesForDate,
  currentOrNextClass,
  formatTime,
  isNewerVersion,
  makeLectureTitle,
  mergeState,
  removeLecture,
  searchLedger,
  setSegmentSpeaker,
  cleanTranscriptCaptions,
  cleanSavedTranscriptCaptions,
  toLocalDateKey
} from "../core/ledger-core.mjs";

test("lecture title uses date, time, and class in the approved order", () => {
  assert.equal(
    makeLectureTitle({ date: "2026-08-27", time: "09:00", className: "Introduction to Psychology" }),
    "August 27, 2026 • 9:00 AM • Introduction to Psychology"
  );
});

test("local date keys do not shift through UTC", () => {
  assert.equal(toLocalDateKey(new Date(2026, 7, 27, 23, 45)), "2026-08-27");
});

test("classes are sorted by their start time", () => {
  const monday = new Date(2026, 7, 24, 8, 0);
  const classes = [
    { id: "b", days: [1], startTime: "13:30", endTime: "14:45" },
    { id: "a", days: [1], startTime: "09:00", endTime: "10:15" }
  ];
  assert.deepEqual(classesForDate(classes, monday).map((item) => item.id), ["a", "b"]);
  assert.equal(currentOrNextClass(classes, monday).id, "a");
});

test("search covers transcript, notes, and extracted assignments", () => {
  const state = mergeState({
    ...blankState(),
    classes: [{ id: "psych", name: "Psychology" }],
    lectures: [{
      id: "l1", classId: "psych", title: "Lecture One", originalTranscript: "Memory is reconstructive.", notes: "Check retrieval practice.", review: { assignments: [{ text: "Read chapter four" }] }
    }]
  });
  assert.equal(searchLedger(state, "reconstructive")[0].type, "original transcript");
  assert.equal(searchLedger(state, "retrieval")[0].type, "notes");
  assert.equal(searchLedger(state, "chapter four")[0].type, "assignments");
});

test("time formatting is user-facing", () => {
  assert.equal(formatTime("13:05"), "1:05 PM");
});

test("updates only move to a newer version", () => {
  assert.equal(isNewerVersion("0.2.0", "0.1.9"), true);
  assert.equal(isNewerVersion("0.1.0", "0.1.0"), false);
  assert.equal(isNewerVersion("0.0.9", "0.1.0"), false);
});

test("deleting a lecture leaves its class and every other lecture intact", () => {
  const state = mergeState({
    classes: [{ id: "history", name: "History" }],
    lectures: [{ id: "delete-me", classId: "history" }, { id: "keep-me", classId: "history" }]
  });
  const next = removeLecture(state, "delete-me");
  assert.deepEqual(next.lectures.map((lecture) => lecture.id), ["keep-me"]);
  assert.deepEqual(next.classes, state.classes);
});

test("speaker marks label transcript segments until the next identified voice", () => {
  const segments = [
    { start: 0, end: 8, text: "Opening" },
    { start: 8, end: 18, text: "Lecture" },
    { start: 18, end: 28, text: "Question" },
    { start: 28, end: 40, text: "Answer" }
  ];
  const marks = [{ seconds: 10, speaker: "Professor" }, { seconds: 24, speaker: "Me" }];
  assert.deepEqual(applySpeakerMarks(segments, marks).map((segment) => segment.speaker || null), [null, "Professor", "Me", "Me"]);
});

test("an individual transcript speaker can be corrected without changing other sections", () => {
  const segments = [{ speaker: "Professor", text: "One" }, { speaker: "Student", text: "Two" }];
  const next = setSegmentSpeaker(segments, 1, "Me");
  assert.deepEqual(next.map((segment) => segment.speaker), ["Professor", "Me"]);
  assert.deepEqual(segments.map((segment) => segment.speaker), ["Professor", "Student"]);
});

test("old non-speech captions are removed without changing real lecture words", () => {
  assert.equal(
    cleanTranscriptCaptions("[MUSIC PLAYING] The professor begins. [SIDE CONVERSATION] The lecture continues. [BLANK_AUDIO]"),
    "The professor begins. The lecture continues."
  );
});

test("saved transcripts, visible segments, and summaries are cleaned together", () => {
  const input = {
    lectures: [{
      id: "lecture-1",
      notes: "Keep [SIDE CONVERSATION] exactly as typed in personal notes.",
      originalTranscript: "[SIDE CONVERSATION] Real sentence.",
      cleanedTranscript: "Real sentence. [SIDE CONVERSATION]",
      transcriptSegments: [{ start: 0, text: "[SIDE CONVERSATION]" }, { start: 5, text: "Real sentence." }],
      review: { summary: "[SIDE CONVERSATION] Real summary.", assignments: [], definitions: [], keyConcepts: [], testMaterial: [], unclearTopics: [] }
    }]
  };
  const result = cleanSavedTranscriptCaptions(input);
  assert.equal(result.changed, true);
  assert.equal(result.state.lectures[0].cleanedTranscript, "Real sentence.");
  assert.deepEqual(result.state.lectures[0].transcriptSegments.map((segment) => segment.text), ["Real sentence."]);
  assert.equal(result.state.lectures[0].review.summary, "Real summary.");
  assert.equal(result.state.lectures[0].notes, input.lectures[0].notes);
});
