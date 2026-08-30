import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

test("approved navigation and discreet controls remain present", async () => {
  const html = await readFile(new URL("../src/index.html", import.meta.url), "utf8");
  for (const label of ["Today", "Classes", "Notebook", "Review", "Search", "Settings"]) assert.match(html, new RegExp(`>${label}<`));
  assert.doesNotMatch(html, /microphone icon|waveform/i);
  assert.doesNotMatch(html, /toast-region/);
  assert.match(html, /notification-badge/);
});

test("installer remains a normal Windows app with a desktop shortcut", async () => {
  const pkg = JSON.parse(await readFile(new URL("../package.json", import.meta.url), "utf8"));
  assert.equal(pkg.build.productName, "The Ledger");
  assert.equal(pkg.build.nsis.createDesktopShortcut, true);
  assert.equal(pkg.build.nsis.oneClick, false);
  assert.equal(pkg.devDependencies["electron-builder"], "26.15.7");
});

test("renderer is isolated from direct Node access", async () => {
  const main = await readFile(new URL("../electron/main.cjs", import.meta.url), "utf8");
  assert.match(main, /contextIsolation:\s*true/);
  assert.match(main, /nodeIntegration:\s*false/);
  assert.match(main, /sandbox:\s*true/);
});

test("update manifests resolve the package version outside npm", async () => {
  const script = await readFile(new URL("../scripts/build-manifest.mjs", import.meta.url), "utf8");
  assert.match(script, /packageJson\.version/);
  assert.match(script, /version could not be determined/);
});

test("the window keeps a visible, stable main scrollbar", async () => {
  const css = await readFile(new URL("../src/styles.css", import.meta.url), "utf8");
  assert.match(css, /#view\s*\{[^}]*min-height:\s*0[^}]*overflow-y:\s*scroll[^}]*scrollbar-gutter:\s*stable/s);
  assert.match(css, /#view::\-webkit-scrollbar/);
  assert.match(css, /\.workspace\s*\{[^}]*min-height:\s*0[^}]*overflow:\s*hidden/s);
});

test("the Windows updater retries a temporarily busy installer without crashing", async () => {
  const main = await readFile(new URL("../electron/main.cjs", import.meta.url), "utf8");
  assert.match(main, /UPDATE_LAUNCH_ATTEMPTS\s*=\s*6/);
  assert.match(main, /error\?\.code\s*===\s*"EBUSY"/);
  assert.match(main, /await wait\(UPDATE_LAUNCH_DELAY_MS\)/);
  assert.match(main, /Date\.now\(\)/);
  assert.match(main, /launchStagedUpdate\(\)\.finally/);
});

test("lecture deletion is confirmed in the UI and restricted to private app storage", async () => {
  const [renderer, preload, main] = await Promise.all([
    readFile(new URL("../src/app.js", import.meta.url), "utf8"),
    readFile(new URL("../electron/preload.cjs", import.meta.url), "utf8"),
    readFile(new URL("../electron/main.cjs", import.meta.url), "utf8")
  ]);
  assert.match(renderer, /Delete Lecture/);
  assert.match(renderer, /This cannot be undone/);
  assert.match(preload, /ledger:delete-lecture-files/);
  assert.match(main, /\[recordingsDir, importsDir\]/);
  assert.match(main, /path\.relative/);
});

test("the Notebook has no subtitle and uses a collapsed Before Class checklist", async () => {
  const [renderer, css] = await Promise.all([
    readFile(new URL("../src/app.js", import.meta.url), "utf8"),
    readFile(new URL("../src/styles.css", import.meta.url), "utf8")
  ]);
  assert.match(renderer, /setHeader\("Notebook", ""\)/);
  assert.doesNotMatch(renderer, /Lecture capture, transcript, and your notes/);
  assert.doesNotMatch(renderer, /Record lectures, create transcripts, and take notes/);
  assert.match(renderer, /Import Notes or Lecture/);
  assert.match(renderer, /Your lecture is saved continuously in small chunks/);
  assert.match(renderer, /<details class="card before-class-card">/);
  assert.doesNotMatch(renderer, /<details class="card before-class-card"\s+open/);
  assert.match(css, /\.before-class-card\[open\] \.details-chevron/);
});

test("active lectures can identify the approved speaker roles from the Notebook", async () => {
  const renderer = await readFile(new URL("../src/app.js", import.meta.url), "utf8");
  assert.match(renderer, /Identify Voice/);
  assert.match(renderer, /Who is speaking\?/);
  assert.match(renderer, /\["Professor", "Me", "Student", "Guest Speaker"\]/);
  assert.match(renderer, /applySpeakerMarks\(result\.transcriptSegments, lecture\.speakerMarks\)/);
});
