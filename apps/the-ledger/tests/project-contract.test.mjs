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
