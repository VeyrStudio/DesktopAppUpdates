const { chromium } = require("playwright");
const path = require("node:path");

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 });
  const errors = [];
  page.on("console", (message) => { if (message.type() === "error") errors.push(message.text()); });
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("http://127.0.0.1:4173/src/index.html", { waitUntil: "networkidle" });
  await page.screenshot({ path: path.join(process.cwd(), ".qa", "today.png"), fullPage: true });
  const labels = await page.locator(".nav-item").allTextContents();
  for (const view of ["Classes", "Notebook", "Review", "Search", "Settings"]) {
    await page.getByRole("button", { name: view, exact: true }).click();
    await page.waitForTimeout(80);
  }
  await page.screenshot({ path: path.join(process.cwd(), ".qa", "settings.png"), fullPage: true });
  const result = {
    title: await page.title(),
    labels: labels.map((value) => value.trim()),
    currentHeading: await page.locator("#page-title").textContent(),
    bodyWidth: await page.locator("body").evaluate((node) => node.scrollWidth),
    viewportWidth: await page.evaluate(() => window.innerWidth),
    errors
  };
  console.log(JSON.stringify(result, null, 2));
  await browser.close();
  if (errors.length || result.bodyWidth > result.viewportWidth) process.exitCode = 1;
})();
