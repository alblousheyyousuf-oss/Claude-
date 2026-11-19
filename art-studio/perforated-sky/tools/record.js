// Records the Perforated Sky page frame by frame (record mode) for preview videos.
// Serve the folder first: python3 -m http.server 8765  (from art-studio/perforated-sky), then:
// NODE_PATH=$(npm root -g) node tools/record.js "athar=3&look=tour" frames_dir --fps 20 --seconds 92
// usage: node record.js "<query>" out_dir --fps 24 --seconds 10 [--every 1] [--w 960 --h 540] [--warm 0]
const { chromium } = require('playwright');
const fs = require('fs');
const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf('--' + k); return i >= 0 ? args[i + 1] : d; };
const query = args[0], out = args[1];
const fps = +opt('fps', 24), secs = +opt('seconds', 10), every = +opt('every', 1), W = +opt('w', 960), H = +opt('h', 540), warm = +opt('warm', 0);
(async () => {
  fs.mkdirSync(out, { recursive: true });
  const b = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const p = await b.newPage({ viewport: { width: W, height: H } });
  const errs = [];
  p.on('console', m => { if (m.type() === 'error' || m.type() === 'warning') errs.push(m.type() + ': ' + m.text()); });
  p.on('pageerror', e => errs.push('pageerror: ' + e.message));
  await p.goto('http://localhost:8765/index.html?record&' + query, { waitUntil: 'load' });
  await p.waitForFunction(() => window.__ready === true, null, { timeout: 60000 });
  console.log(JSON.stringify(await p.evaluate(() => window.__info())));
  const dt = 1 / fps;
  if (warm > 0) await p.evaluate(([n, d]) => { for (let i = 0; i < n; i++) window.__frame(d); }, [Math.round(warm * fps), dt]);
  const n = Math.round(secs * fps);
  let k = 0;
  const t0 = Date.now();
  for (let i = 0; i < n; i++) {
    await p.evaluate(d => window.__frame(d), dt);
    if (i % every === 0) await p.screenshot({ path: `${out}/f${String(k++).padStart(5, '0')}.jpg`, type: 'jpeg', quality: 88 });
  }
  console.log('frames', k, 'in', ((Date.now() - t0) / 1000).toFixed(1), 's');
  if (errs.length) console.log(errs.slice(0, 15).join('\n'));
  await b.close();
})();
