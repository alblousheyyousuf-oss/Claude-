// Print an HTML file to PDF with the page size its CSS asks for.
// Run:  node docs/vase/src/html_pdf.js <in.html> <out.pdf>      (needs Playwright + Chromium)
const path = require('path');
const { chromium } = require('playwright');

(async () => {
  const [src, dest] = process.argv.slice(2);
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto('file://' + path.resolve(src), { waitUntil: 'load' });
  await page.pdf({ path: dest, printBackground: true, preferCSSPageSize: true });
  await browser.close();
  console.log(`${src} -> ${dest}`);
})();
