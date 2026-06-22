import { chromium } from "playwright";
import { fileURLToPath } from "node:url";
import path from "node:path";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.resolve(__dirname, "../assets/screenshots");
const BASE = "http://127.0.0.1:5173";

async function main() {
  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: { width: 1440, height: 1000 },
    deviceScaleFactor: 2,
  });
  await context.addInitScript(() => {
    try { localStorage.setItem("finex_session", "demo"); } catch (e) {}
  });
  const page = await context.newPage();
  await page.goto(BASE, { waitUntil: "networkidle" });
  await page.waitForTimeout(1200);
  await page.getByRole("button", { name: /Explorar demo interactiva/i }).first().click();
  await page.waitForTimeout(1500);
  await page.getByRole("button", { name: /^Movimientos$/i }).first().click();
  await page.waitForLoadState("networkidle").catch(() => {});
  await page.waitForTimeout(1500);

  // Select the internal transfer type in the "Tipo" dropdown of the new-movement form.
  const typeSelect = page.locator("select", { has: page.locator("option", { hasText: "Traspaso entre mis cuentas" }) }).first();
  await typeSelect.selectOption({ label: "Traspaso entre mis cuentas" });
  await page.waitForTimeout(600);

  // Expand the "Detalles opcionales" section to reveal origin/destination accounts.
  await page.getByText("Detalles opcionales", { exact: false }).first().click();
  await page.waitForTimeout(900);

  // Try to pick an origin and a destination account to make the capture meaningful.
  const selects = page.locator(".panel select");
  const count = await selects.count();
  // Heuristic: find selects whose options reference account names and set them.
  for (let i = 0; i < count; i++) {
    const sel = selects.nth(i);
    const optText = await sel.locator("option").allTextContents();
    const joined = optText.join(" ").toLowerCase();
    if (joined.includes("cuenta corriente bci")) {
      await sel.selectOption({ index: 1 }).catch(() => {});
      await page.waitForTimeout(300);
    }
  }
  await page.waitForTimeout(800);

  await page.screenshot({ path: path.join(OUT, "08-internal-transfer.png") });
  console.log("captured 08-internal-transfer.png");

  await browser.close();
}

main().catch((e) => { console.error(e); process.exit(1); });
