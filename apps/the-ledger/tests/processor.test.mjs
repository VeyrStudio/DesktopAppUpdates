import test from "node:test";
import assert from "node:assert/strict";
import processor from "../electron/processor.cjs";

const { parseWhisperJson, cleanWhisperText, assessTranscriptQuality } = processor;

test("known non-speech captions are removed from transcript text", () => {
  assert.equal(cleanWhisperText("[MUSIC PLAYING] [SIDE CONVERSATION] Industrial psychology begins here. [BLANK_AUDIO]"), "Industrial psychology begins here.");
});

test("a side-conversation caption loop is rejected instead of saved as a transcript", () => {
  const transcription = [
    { start: 0, end: 5, text: "I'm Professor Gargano. This is industrial organizational psychology." },
    ...Array.from({ length: 40 }, (_, index) => ({ start: 5 + index * 5, end: 10 + index * 5, text: "[SIDE CONVERSATION]" }))
  ];
  const parsed = parseWhisperJson({ transcription });
  assert.equal(parsed.quality.reliable, false);
  assert.equal(parsed.quality.captionCount, 40);
  assert.doesNotMatch(parsed.text, /SIDE CONVERSATION/);
});

test("ordinary lecture output remains reliable", () => {
  const rawTexts = ["Today we will discuss job analysis.", "The first concept is task identity."];
  const segments = rawTexts.map((text, index) => ({ start: index * 10, text }));
  assert.equal(assessTranscriptQuality(rawTexts, segments).reliable, true);
});
