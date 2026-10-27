// Combine templates-*.svg into one print-ready A3 PDF (1:1, no margins).
// Run:  node docs/vase/src/templates_pdf.js      (needs Playwright + Chromium)
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const OUT = path.dirname(__dirname);
const sheets = fs.readdirSync(OUT)
  .filter(f => /^templates-\d+\.svg$/.test(f))
  .sort((a, b) => parseInt(a.match(/\d+/)[0]) - parseInt(b.match(/\d+/)[0]));

const pages = sheets.map(f => `<div class="page">${fs.readFileSync(path.join(OUT, f), 'utf8')}</div>`).join('\n');
const html = `<!doctype html><html><head><meta charset="utf-8"><style>
  @page { size: 420mm 297mm; margin: 0; }
  html, body { margin: 0; padding: 0; }
  .page { width: 420mm; height: 297mm; overflow: hidden; page-break-after: always; }
  .page:last-child { page-break-after: auto; }
  .page svg { display: block; width: 420mm; height: 297mm; }
</style></head><body>${pages}</body></html>`;

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.setContent(html, { waitUntil: 'load' });
  const dest = path.join(OUT, 'templates.pdf');
  await page.pdf({ path: dest, width: '420mm', height: '297mm', printBackground: true,
                   margin: { top: 0, right: 0, bottom: 0, left: 0 }, preferCSSPageSize: true });
  await browser.close();
  console.log(`${sheets.length} sheets -> ${dest}`);
})();
