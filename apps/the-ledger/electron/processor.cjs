const { spawn } = require("node:child_process");
const fs = require("node:fs");
const fsp = require("node:fs/promises");
const path = require("node:path");
const os = require("node:os");

const NON_SPEECH_CAPTION_PATTERN = /\[(?:MUSIC(?: PLAYING)?|SIDE CONVERSATION|BLANK[_ ]AUDIO|BACKGROUND NOISE|CROSSTALK|NOISE|LAUGHTER|APPLAUSE|SILENCE|INAUDIBLE)\]/gi;

function resourcesRoot() {
  const { app } = require("electron");
  return app.isPackaged
    ? path.join(process.resourcesPath, "resources")
    : path.join(__dirname, "..", "resources");
}

function firstExisting(paths) {
  return paths.find((candidate) => fs.existsSync(candidate)) || null;
}

function enginePaths() {
  const root = resourcesRoot();
  const bin = path.join(root, "bin");
  const models = path.join(root, "models");
  return {
    ffmpeg: firstExisting([path.join(bin, "ffmpeg.exe"), path.join(bin, "ffmpeg"), "ffmpeg"]),
    whisper: firstExisting([path.join(bin, "whisper-cli.exe"), path.join(bin, "whisper-cli")]),
    model: firstExisting([
      path.join(models, "ggml-small.en-q5_1.bin"),
      path.join(models, "ggml-small.en.bin"),
      path.join(models, "ggml-base.en.bin")
    ])
  };
}

function run(command, args, onOutput = () => {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, { windowsHide: true });
    let stderr = "";
    child.stdout.on("data", (chunk) => onOutput(chunk.toString()));
    child.stderr.on("data", (chunk) => {
      const value = chunk.toString();
      stderr += value;
      onOutput(value);
    });
    child.on("error", reject);
    child.on("close", (code) => code === 0 ? resolve() : reject(new Error(stderr.trim() || `${path.basename(command)} exited with code ${code}.`)));
  });
}

function timestampSeconds(value) {
  if (typeof value === "number") return value > 10000 ? value / 1000 : value;
  if (typeof value !== "string") return 0;
  const parts = value.replace(/[[\]]/g, "").split(":").map(Number);
  if (parts.some(Number.isNaN)) return 0;
  return parts.reduce((total, part) => total * 60 + part, 0);
}

function cleanWhisperText(value) {
  return String(value || "")
    .replace(NON_SPEECH_CAPTION_PATTERN, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function assessTranscriptQuality(rawTexts, cleanedSegments) {
  const captionCount = rawTexts.reduce((total, value) => total + (String(value).match(NON_SPEECH_CAPTION_PATTERN) || []).length, 0);
  const spokenText = cleanedSegments.map((segment) => segment.text).join(" ").trim();
  const wordCount = spokenText.match(/[A-Za-z0-9]+(?:['’-][A-Za-z0-9]+)*/g)?.length || 0;
  const normalizedSegments = rawTexts
    .map((value) => cleanWhisperText(value).toLowerCase().replace(/[^a-z0-9 ]/g, "").replace(/\s+/g, " ").trim())
    .filter((value) => value.length >= 4);
  const repetitions = new Map();
  for (const value of normalizedSegments) repetitions.set(value, (repetitions.get(value) || 0) + 1);
  const largestRepetition = Math.max(0, ...repetitions.values());
  const captionLoop = captionCount >= 8 && captionCount > Math.max(4, Math.ceil(wordCount / 3));
  const textLoop = largestRepetition >= 8 && largestRepetition >= Math.ceil(Math.max(1, normalizedSegments.length) * 0.35);
  return {
    reliable: wordCount > 0 && !captionLoop && !textLoop,
    captionCount,
    wordCount,
    largestRepetition
  };
}

function parseWhisperJson(json) {
  const rawSegments = json.transcription || json.segments || json.result?.segments || [];
  const rawTexts = rawSegments.map((segment) => String(segment.text || ""));
  const segments = rawSegments.map((segment) => ({
      start: timestampSeconds(segment.timestamps?.from ?? segment.start ?? segment.offsets?.from),
      end: timestampSeconds(segment.timestamps?.to ?? segment.end ?? segment.offsets?.to),
      speaker: "Unidentified Speaker",
      text: cleanWhisperText(segment.text)
    }))
    .filter((segment) => segment.text);
  const text = segments.map((segment) => segment.text).join(" ").replace(/\s+/g, " ").trim();
  return { segments, text, quality: assessTranscriptQuality(rawTexts, segments) };
}

function extractReview(text) {
  const sentences = String(text || "").split(/(?<=[.!?])\s+/).map((item) => item.trim()).filter(Boolean);
  const assignments = sentences.filter((sentence) => /\b(assignment|homework|read|chapter|due|submit|paper|project)\b/i.test(sentence)).slice(0, 12).map((sentence) => ({ text: sentence, due: "" }));
  const testMaterial = sentences.filter((sentence) => /\b(test|exam|quiz|remember|important|will be on)\b/i.test(sentence)).slice(0, 12);
  const definitions = [];
  for (const sentence of sentences) {
    const match = sentence.match(/^([A-Z][A-Za-z0-9 -]{2,45})\s+(?:is|means|refers to)\s+(.{8,180})/);
    if (match) definitions.push({ term: match[1].trim(), definition: match[2].trim() });
    if (definitions.length >= 12) break;
  }
  const concepts = [...new Set(definitions.map((item) => item.term))];
  return {
    summary: sentences.slice(0, 4).join(" "),
    keyConcepts: concepts,
    definitions,
    assignments,
    testMaterial,
    unclearTopics: []
  };
}

async function processLecture(audioPath, onProgress = () => {}) {
  const engines = enginePaths();
  if (!engines.whisper || !engines.model) {
    return { ok: false, unavailable: true, message: "The local transcription engine is not installed in this build." };
  }
  const workDir = await fsp.mkdtemp(path.join(os.tmpdir(), "the-ledger-"));
  const wavPath = path.join(workDir, "lecture.wav");
  const outputPrefix = path.join(workDir, "transcript");
  try {
    onProgress({ stage: "audio", message: "Preparing lecture audio" });
    if (engines.ffmpeg && engines.ffmpeg !== "ffmpeg") {
      await run(engines.ffmpeg, ["-hide_banner", "-loglevel", "error", "-y", "-i", audioPath, "-vn", "-af", "highpass=f=70,loudnorm=I=-16:TP=-1.5:LRA=11", "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", wavPath]);
    } else {
      await run(engines.ffmpeg || "ffmpeg", ["-hide_banner", "-loglevel", "error", "-y", "-i", audioPath, "-vn", "-af", "highpass=f=70,loudnorm=I=-16:TP=-1.5:LRA=11", "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", wavPath]);
    }
    onProgress({ stage: "transcription", message: "Creating local transcript" });
    await run(engines.whisper, ["-m", engines.model, "-f", wavPath, "-l", "en", "-oj", "-of", outputPrefix, "-sns"]);
    const parsed = parseWhisperJson(JSON.parse(await fsp.readFile(`${outputPrefix}.json`, "utf8")));
    if (!parsed.quality.reliable) {
      return {
        ok: false,
        unreliable: true,
        message: "The Ledger could not create a reliable transcript from this lecture. The saved lecture was kept so you can try Re-transcribe."
      };
    }
    return {
      ok: true,
      originalTranscript: parsed.text,
      cleanedTranscript: parsed.text,
      transcriptSegments: parsed.segments,
      review: extractReview(parsed.text)
    };
  } finally {
    await fsp.rm(workDir, { recursive: true, force: true });
  }
}

module.exports = { processLecture, enginePaths, parseWhisperJson, extractReview, cleanWhisperText, assessTranscriptQuality };
