import { createHash } from "node:crypto";
import { readFile, writeFile } from "node:fs/promises";
import { basename, join } from "node:path";

const packageJson = JSON.parse(await readFile(new URL("../package.json", import.meta.url), "utf8"));
const version = process.env.npm_package_version || packageJson.version;
if (!version) throw new Error("The Ledger version could not be determined.");
const repository = process.env.GITHUB_REPOSITORY || "VeyrStudio/DesktopAppUpdates";
const installer = process.argv[2] || join("dist", `TheLedgerSetup-${version}.exe`);
const bytes = await readFile(installer);
const sha256 = createHash("sha256").update(bytes).digest("hex");
const fileName = basename(installer);
const manifest = {
  app: "The Ledger",
  channel: "ledger",
  version,
  url: `https://github.com/${repository}/releases/download/ledger-v${version}/${fileName}`,
  sha256,
  publishedAt: new Date().toISOString(),
  notes: "See the release notes for this version."
};
await writeFile(join("dist", "ledger.json"), `${JSON.stringify(manifest, null, 2)}\n`, "utf8");
console.log(`Created ledger.json for ${fileName}`);
