import { chromium } from "playwright";
import fs from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.resolve(__dirname, "../docs/screenshots");
const BASE = "http://127.0.0.1:5173";

const navTargets = [
  ["Dashboard", "dashboard"],
  ["Movimientos", "movements"],
  ["Obligaciones", "obligations"],
  ["Importar", "import"],
  ["Correos", "mailbox"],
  ["Cuentas", "accounts"],
  ["Configuracion", "settings"],
];

async function main() {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 2,
  });
  // Force demo session before any app code runs.
  await context.addInitScript(() => {
    try {
      localStorage.setItem("finex_session", "demo");
    } catch (e) {}
  });
  const page = await context.newPage();

  // Landing page
  await page.goto(BASE, { waitUntil: "networkidle" });
  await page.waitForTimeout(1500);
  await page.screenshot({ path: path.join(OUT, "00-landing.png") });
  console.log("captured landing");

  // Enter demo
  await page.getByRole("button", { name: /Ver demo/i }).first().click();
  await page.waitForTimeout(2000);

  let index = 1;
  for (const [label, view] of navTargets) {
    try {
      await page.getByRole("button", { name: new RegExp(`^${label}$`, "i") }).first().click({ timeout: 5000 });
    } catch (e) {
      // fallback: some labels may be partial
      await page.getByRole("button", { name: new RegExp(label, "i") }).first().click({ timeout: 5000 });
    }
    await page.waitForLoadState("networkidle").catch(() => {});
    await page.waitForTimeout(1800);
    const file = `${String(index).padStart(2, "0")}-${view}.png`;
    await page.screenshot({ path: path.join(OUT, file) });
    console.log("captured", file);
    index += 1;
  }

  await browser.close();
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
