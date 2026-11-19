// OB-Sim recorder: renders a simulator log to frames (and an mp4 with ffmpeg).
// usage: node obsim_record.js logs/x.json out.mp4 [--fps 24] [--from 0] [--to 75] [--bg night|paper] [--orbit 0] [--stills t1,t2,...]
//        [--pitch deg [--pitch2 deg --t1 s --t2 s]] [--fov deg]   look from the head toward the hand's direction
const {chromium} = require('playwright'); const http = require('http'), fs = require('fs'), path = require('path');
const {execFileSync} = require('child_process');
const args = process.argv.slice(2); const opt = (k, d) => { const i = args.indexOf('--' + k); return i >= 0 ? args[i + 1] : d; };
const log = args[0], out = args[1];
const fps = +opt('fps', 24), from = +opt('from', 0), to = +opt('to', 75), bg = opt('bg', 'night'), orbit = +opt('orbit', 0);
const stills = opt('stills', '');
const w = +opt('w', 960), h = +opt('h', 540);
const root = __dirname;
const srv = http.createServer((q, s) => { const f = path.join(root, decodeURIComponent(q.url.split('?')[0]));
  const t = {'.js': 'text/javascript', '.html': 'text/html', '.json': 'application/json'}[path.extname(f)] || 'application/octet-stream';
  try { s.writeHead(200, {'Content-Type': t}); s.end(fs.readFileSync(f)); } catch (e) { s.writeHead(404); s.end(); } }).listen(0, async () => {
  const port = srv.address().port;
  const b = await chromium.launch({args: ['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist']});
  const p = await b.newPage({viewport: {width: w, height: h}});
  p.on('pageerror', e => console.log('pageerror', e.message)); p.on('console', m => { if (m.type() === 'error') console.log('console', m.text()); });
  const extra = ['pitch', 'pitch2', 't1', 't2', 'fov'].filter(k => opt(k, null) !== null).map(k => `&${k}=${opt(k, null)}`).join('');
  await p.goto(`http://localhost:${port}/render.html?log=${encodeURIComponent(log)}&bg=${bg}&w=${w}&h=${h}${extra}`);
  await p.waitForFunction('window.ready', null, {timeout: 300000});
  console.log(JSON.stringify(await p.evaluate('window.info')));
  const dir = out + '_frames'; fs.rmSync(dir, {recursive: true, force: true}); fs.mkdirSync(dir, {recursive: true});
  const times = stills ? stills.split(',').map(Number) : Array.from({length: Math.round((to - from) * fps)}, (_, i) => from + i / fps);
  const t0 = Date.now();
  for (let i = 0; i < times.length; i++) {
    const url = await p.evaluate(([t, o]) => window.renderAt(t, o), [times[i], orbit]);
    fs.writeFileSync(path.join(dir, `f${String(i).padStart(5, '0')}.jpg`), Buffer.from(url.split(',')[1], 'base64'));
    if (i % 200 === 0) console.log('frame', i, '/', times.length, ((Date.now() - t0) / 1000).toFixed(0) + 's');
  }
  await b.close(); srv.close();
  if (!stills) execFileSync('ffmpeg', ['-loglevel', 'error', '-y', '-framerate', String(fps), '-i', path.join(dir, 'f%05d.jpg'),
    '-c:v', 'libx264', '-profile:v', 'main', '-pix_fmt', 'yuv420p', '-crf', '26', '-preset', 'medium', '-movflags', '+faststart', out]);
  console.log('done', times.length, 'frames');
});
