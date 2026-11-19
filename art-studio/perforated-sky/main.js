// The Perforated Sky — a WebXR show.
// One night of the real Omani sky over Nizwa. In the aflaj (Oman's ancient water channels) the shares of water
// were timed by the rising of stars; in the kumma (the embroidered Omani cap) the hole is punched before the
// stitch. Here the stars are the holes and the falaj water is the thread: each star that rises takes its share.
// The water rises to it as a loose swarm, tightens into thread, and embroiders it into the sky: a rosette of
// lazy-daisy petals around the star, then a running stitch that passes through real faint stars, as through
// the punched holes of a kumma. The sky turns all night like a cap in the embroiderer's hands; at dawn the whole
// embroidery shows in the colours of the original drawing, then fades, and another night of the year begins.
import * as THREE from 'three';
import { STARS } from './stars.js';

// ------------------------------------------------------------------ parameters
const Q = new URLSearchParams(location.search);
const num = (k, d) => (Q.has(k) && isFinite(parseFloat(Q.get(k))) ? parseFloat(Q.get(k)) : d);
const P = {
  athar: Math.max(1.5, num('athar', 24)),   // seconds per athar (a night has 24 athars)
  start: Math.max(0, Math.floor(num('start', 0))),
  lat: 22.93, lon: 57.53,                   // Nizwa
  record: Q.has('record'),                  // frame-by-frame stepping for video capture
  look: Q.get('look') || 'east',
  date: Q.get('date'),
};
const R = 40;                     // radius of the sky (metres)
const DEG = Math.PI / 180;
const ATHARS = 24;
const NIGHT_HOURS = 10.5;         // 18:45 to 05:15, Oman time
const NIGHT_START_UT = 14.75;     // 18:45 Oman time
const RISE_ALT = 5 * DEG;         // a share begins when its star clears the eastern hills
const POOL = new THREE.Vector3(0, 0.02, -1.15);   // the distribution point of the falaj, in front of you
const DUSK = Math.max(4, 0.75 * P.athar), DAWN = Math.max(6, 1.1 * P.athar), PAUSE = Math.max(2, 0.2 * P.athar);
const NIGHT = ATHARS * P.athar;

const COL = {
  base: new THREE.Color('#c9d6ea'),         // silver thread
  water: new THREE.Color('#5fe3d2'),        // falaj turquoise
  ink: ['#D81E8C', '#7A35D6', '#9BE060', '#3F7FEA', '#EE5DB4', '#C8304F'].map(h => new THREE.Color(h)),
};

// ------------------------------------------------------------------ small vector helpers (arrays)
const v3 = (x, y, z) => [x, y, z];
const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
const add = (a, b) => [a[0] + b[0], a[1] + b[1], a[2] + b[2]];
const scl = (a, s) => [a[0] * s, a[1] * s, a[2] * s];
const nrm = a => { const l = Math.hypot(a[0], a[1], a[2]) || 1; return [a[0] / l, a[1] / l, a[2] / l]; };
const ang = (a, b) => Math.acos(Math.min(1, Math.max(-1, dot(a, b))));
const unitRD = (ra, dec) => [Math.cos(dec) * Math.cos(ra), Math.cos(dec) * Math.sin(ra), Math.sin(dec)];
const smooth = (a, b, x) => { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); };
function slerp(a, b, t) {
  const w = ang(a, b); if (w < 1e-6) return a.slice();
  const s = Math.sin(w);
  return add(scl(a, Math.sin((1 - t) * w) / s), scl(b, Math.sin(t * w) / s));
}
let seed = 7;
const rnd = () => { seed = (seed * 16807) % 2147483647; return (seed - 1) / 2147483646; };

// ------------------------------------------------------------------ the stars
const NS = STARS.length / 4;
const ST = { ra: new Float32Array(NS), dec: new Float32Array(NS), mag: new Float32Array(NS), bv: new Float32Array(NS),
             u: new Float32Array(NS * 3), name: new Array(NS).fill(null) };
for (let i = 0; i < NS; i++) {
  const ra = STARS[i * 4] / 100 * DEG, dec = STARS[i * 4 + 1] / 100 * DEG;
  ST.ra[i] = ra; ST.dec[i] = dec; ST.mag[i] = STARS[i * 4 + 2] / 100; ST.bv[i] = STARS[i * 4 + 3] / 1000;
  const u = unitRD(ra, dec); ST.u[i * 3] = u[0]; ST.u[i * 3 + 1] = u[1]; ST.u[i * 3 + 2] = u[2];
}
const su = i => [ST.u[i * 3], ST.u[i * 3 + 1], ST.u[i * 3 + 2]];
// traditional Arabic names of bright stars (classical names; the star names used for the aflaj vary from village to village)
const NAMES = [
  ['الشعرى اليمانية', 101.29, -16.72], ['سهيل', 95.99, -52.70], ['السماك الرامح', 213.92, 19.18], ['رجل قنطورس', 219.90, -60.83],
  ['النسر الواقع', 279.23, 38.78], ['العيّوق', 79.17, 46.00], ['رجل الجبار', 78.63, -8.20], ['الشعرى الشامية', 114.83, 5.22],
  ['آخر النهر', 24.43, -57.24], ['منكب الجوزاء', 88.79, 7.41], ['حضار', 210.96, -60.37], ['النسر الطائر', 297.70, 8.87],
  ['الدبران', 68.98, 16.51], ['قلب العقرب', 247.35, -26.43], ['السماك الأعزل', 201.30, -11.16], ['رأس التوأم المؤخر', 116.33, 28.03],
  ['فم الحوت', 344.41, -29.62], ['ذنب الدجاجة', 310.36, 45.28], ['قلب الأسد', 152.09, 11.97], ['العذارى', 104.66, -28.97],
  ['رأس التوأم المقدم', 113.65, 31.89], ['الشولة', 263.40, -37.10], ['الناجذ', 81.28, 6.35], ['النطح', 81.57, 28.61],
  ['النظام', 84.05, -1.20], ['النطاق', 85.19, -1.94], ['ظهر الدب', 165.93, 61.75], ['مرفق الثريا', 51.08, 49.86],
  ['الوزن', 107.10, -26.39], ['القوس', 276.04, -34.38], ['القائد', 206.89, 49.31], ['منكب ذي العنان', 89.88, 44.95],
  ['الهنعة', 99.43, 16.40], ['المرزم', 95.67, -17.96], ['الفرد', 141.90, -8.66], ['الجدي', 37.95, 89.26], ['الحمل', 31.79, 23.46],
  ['الجبهة', 154.99, 19.84], ['الضفدع الثاني', 10.90, -17.99], ['منكب قنطورس', 211.67, -36.37], ['سرة الفرس', 2.10, 29.09],
  ['المئزر', 17.43, 35.62], ['سيف الجبار', 86.94, -9.67], ['رأس الحواء', 263.73, 12.56], ['رأس الغول', 47.04, 40.96],
  ['عناق الأرض', 30.97, 42.33], ['الصرفة', 177.26, 14.57], ['متن الفرس', 346.19, 15.21], ['الثريا', 56.87, 24.11],
  ['الزبانى الجنوبي', 222.72, -16.04], ['عنق الحية', 236.07, 6.43], ['صدر الدجاجة', 305.56, 40.26], ['أنف الفرس', 326.05, 9.88],
  ['الساق', 345.94, 28.08], ['منقار الدجاجة', 292.68, 27.96], ['رأس التنين', 269.15, 51.49], ['الذراع اليمين', 319.64, 62.59],
  ['المنخر', 45.57, 4.09], ['الزبانى الشمالي', 229.25, -9.38], ['جبهة العقرب', 240.08, -22.62], ['العقرب', 241.36, -19.81],
  ['السابق', 257.59, -15.72], ['العنقاء', 6.57, -42.31], ['جناح الغراب', 183.95, -17.54], ['النير', 332.06, -46.96], ['الجناح', 3.31, 15.18],
];
for (const [name, raD, decD] of NAMES) {
  const v = unitRD(raD * DEG, decD * DEG);
  let best = -1, bd = 0.6 * DEG;
  for (let i = 0; i < NS && ST.mag[i] <= 3.8; i++) { const d = ang(v, su(i)); if (d < bd) { bd = d; best = i; } }
  if (best >= 0) ST.name[best] = name;
}

// ------------------------------------------------------------------ astronomy: one night over Nizwa
function omanDate(offsetDays = 0) {
  let t;
  if (P.date) { const [y, m, d] = P.date.split('-').map(Number); t = new Date(Date.UTC(y, m - 1, d)); }
  else t = new Date(Date.now() + 4 * 3600e3);
  t = new Date(Date.UTC(t.getUTCFullYear(), t.getUTCMonth(), t.getUTCDate()) + offsetDays * 864e5);
  return { y: t.getUTCFullYear(), m: t.getUTCMonth() + 1, d: t.getUTCDate() };
}
function lstRad(jd) {
  const h = 18.697374558 + 24.06570982441908 * (jd - 2451545.0) + P.lon / 15;
  return (((h % 24) + 24) % 24) * 15 * DEG;
}
function makeNight(date) {
  const jd0 = Date.UTC(date.y, date.m - 1, date.d) / 864e5 + 2440587.5 + NIGHT_START_UT / 24;
  return { date, lst0: lstRad(jd0), span: NIGHT_HOURS * 1.00273790935 * 15 * DEG };
}
// fraction of the night when star i clears RISE_ALT in the east (null if it never does)
function riseT(i, night) {
  const phi = P.lat * DEG, dec = ST.dec[i];
  const c = (Math.sin(RISE_ALT) - Math.sin(phi) * Math.sin(dec)) / (Math.cos(phi) * Math.cos(dec));
  if (c <= -1 || c >= 1) return null;
  let d = (ST.ra[i] - Math.acos(c) - night.lst0) % (2 * Math.PI);
  if (d < 0) d += 2 * Math.PI;
  return d / night.span;
}
// one star for each athar, in the order they truly rise tonight; brighter and named stars are preferred
function chooseShares(night) {
  const cand = [];
  for (let i = 0; i < NS && ST.mag[i] <= 3.6; i++) { const T = riseT(i, night); if (T !== null && T < 1) cand.push({ i, T }); }
  const used = new Set(), shares = [];
  let prev = -1;
  for (let k = 0; k < ATHARS; k++) {
    const target = Math.max(k / ATHARS, prev + 0.6 / ATHARS);
    let best = null, bc = 1e9;
    for (const c of cand) {
      if (used.has(c.i) || c.T < target) continue;
      const late = (c.T - target) * ATHARS;
      if (late > 1.1) continue;
      const cost = late * 1.3 + ST.mag[c.i] * 0.55 - (ST.name[c.i] ? 0.7 : 0);
      if (cost < bc) { bc = cost; best = c; }
    }
    if (!best) for (const c of cand) if (!used.has(c.i) && c.T >= target && (!best || c.T < best.T)) best = c;
    if (!best) break;
    used.add(best.i); shares.push({ star: best.i, T: best.T }); prev = best.T;
  }
  return shares;
}

// ------------------------------------------------------------------ renderer, scene, camera
const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance', preserveDrawingBuffer: P.record });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(innerWidth, innerHeight);
renderer.setClearColor(0x020309, 1);
renderer.xr.enabled = true;
renderer.xr.setReferenceSpaceType('local-floor');
document.body.appendChild(renderer.domElement);
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(68, innerWidth / innerHeight, 0.05, 200);
camera.position.set(0, 1.6, 0.35);
scene.add(camera);
addEventListener('resize', () => {
  if (P.record) return;
  camera.aspect = innerWidth / innerHeight; camera.updateProjectionMatrix(); renderer.setSize(innerWidth, innerHeight);
});

// the sky turns around the celestial pole: world = B * Rz(-LST) * (star unit vector)
const sky = new THREE.Group();
sky.matrixAutoUpdate = false;
scene.add(sky);
const phi = P.lat * DEG;
const BASIS = new THREE.Matrix4().makeBasis(
  new THREE.Vector3(Math.sin(phi), Math.cos(phi), 0),   // celestial equator on the southern meridian
  new THREE.Vector3(0, 0, -1),                          // east (you face east, where the stars rise)
  new THREE.Vector3(-Math.cos(phi), Math.sin(phi), 0)); // celestial north pole
const _rz = new THREE.Matrix4();
function setSky(lst) { sky.matrix.copy(BASIS).multiply(_rz.makeRotationZ(-lst)); sky.matrixWorldNeedsUpdate = true; }

// ------------------------------------------------------------------ sky dome (gradient), milky way, stars
const U = { time: { value: 0 }, night: { value: 0 }, dusk: { value: 0 }, dawn: { value: 0 }, pulse: { value: 0 },
            fade: { value: 1 }, px: { value: 1 } };
const domeMat = new THREE.ShaderMaterial({
  side: THREE.BackSide, depthWrite: false,
  uniforms: { uDusk: U.dusk, uDawn: U.dawn },
  vertexShader: `varying vec3 vW; void main(){ vW = (modelMatrix*vec4(position,1.0)).xyz; gl_Position = projectionMatrix*viewMatrix*vec4(vW,1.0); }`,
  fragmentShader: `uniform float uDusk; uniform float uDawn; varying vec3 vW;
    void main(){
      vec3 d = normalize(vW); float alt = d.y;
      vec3 c = mix(vec3(0.026,0.034,0.080), vec3(0.006,0.008,0.022), smoothstep(0.0, 0.55, alt));
      float low = exp(-max(alt, 0.0) * 6.0);
      float west = smoothstep(0.1, 1.0, d.z), east = smoothstep(0.1, 1.0, -d.z);
      c += vec3(0.30,0.13,0.10) * uDusk * west * low + vec3(0.05,0.07,0.17) * uDusk * (1.0 - alt);
      c += vec3(0.40,0.20,0.15) * uDawn * east * low + vec3(0.09,0.14,0.30) * uDawn * (1.0 - 0.6 * alt);
      gl_FragColor = vec4(c, 1.0);
    }`,
});
const dome = new THREE.Mesh(new THREE.SphereGeometry(R * 1.25, 48, 24), domeMat);
dome.renderOrder = -10;
scene.add(dome);

const mwMat = new THREE.ShaderMaterial({
  side: THREE.BackSide, depthWrite: false, transparent: true, blending: THREE.AdditiveBlending,
  uniforms: { uFade: U.night, uNGP: { value: new THREE.Vector3(...unitRD(192.859 * DEG, 27.128 * DEG)) },
              uGC: { value: new THREE.Vector3(...unitRD(266.405 * DEG, -28.936 * DEG)) } },
  vertexShader: `varying vec3 vL; varying float vAlt;
    void main(){ vL = normalize(position); vec4 w = modelMatrix*vec4(position,1.0); vAlt = w.y/length(w.xyz);
      gl_Position = projectionMatrix*viewMatrix*w; }`,
  fragmentShader: `uniform float uFade; uniform vec3 uNGP; uniform vec3 uGC; varying vec3 vL; varying float vAlt;
    float h(vec3 p){ p = fract(p*0.3183099 + 0.1); p *= 17.0; return fract(p.x*p.y*p.z*(p.x+p.y+p.z)); }
    float n3(vec3 x){ vec3 i = floor(x), f = fract(x); f = f*f*(3.0-2.0*f);
      return mix(mix(mix(h(i), h(i+vec3(1,0,0)), f.x), mix(h(i+vec3(0,1,0)), h(i+vec3(1,1,0)), f.x), f.y),
                 mix(mix(h(i+vec3(0,0,1)), h(i+vec3(1,0,1)), f.x), mix(h(i+vec3(0,1,1)), h(i+vec3(1,1,1)), f.x), f.y), f.z); }
    void main(){
      float sb = dot(vL, uNGP);
      float band = exp(-sb*sb/0.02);
      float core = 0.5 + 0.5*max(dot(vL, uGC), 0.0);
      if (band*core*uFade < 0.004) discard;            // most of the sky is far from the band: skip the noise there
      float n = n3(vL*7.0)*0.6 + n3(vL*19.0)*0.4;
      float lane = smoothstep(0.4, 0.8, n3(vL*12.0 + 3.0)) * exp(-sb*sb/0.004);
      float I = band * core * (0.5 + 0.7*n) * (1.0 - 0.65*lane) * smoothstep(0.0, 0.3, vAlt);
      gl_FragColor = vec4(vec3(0.55,0.62,0.86) * I * 0.09 * uFade, 1.0);
    }`,
});
sky.add(new THREE.Mesh(new THREE.SphereGeometry(R * 1.08, 64, 32), mwMat));

function bvColor(bv) {
  const S = [[-0.4, [0.62, 0.72, 1.0]], [0.0, [0.80, 0.86, 1.0]], [0.4, [1.0, 0.98, 0.95]], [0.8, [1.0, 0.9, 0.74]],
             [1.4, [1.0, 0.76, 0.52]], [2.0, [1.0, 0.62, 0.42]]];
  const t = Math.min(2, Math.max(-0.4, bv));
  for (let k = 1; k < S.length; k++) if (t <= S[k][0]) {
    const f = (t - S[k - 1][0]) / (S[k][0] - S[k - 1][0]);
    return S[k - 1][1].map((c, j) => c + (S[k][1][j] - c) * f);
  }
  return S[S.length - 1][1];
}
const starGeo = new THREE.BufferGeometry();
{
  const pos = new Float32Array(NS * 3), col = new Float32Array(NS * 3), mag = new Float32Array(NS), ph = new Float32Array(NS);
  for (let i = 0; i < NS; i++) {
    pos[i * 3] = ST.u[i * 3] * R; pos[i * 3 + 1] = ST.u[i * 3 + 1] * R; pos[i * 3 + 2] = ST.u[i * 3 + 2] * R;
    const c = bvColor(ST.bv[i]); col.set(c, i * 3); mag[i] = ST.mag[i]; ph[i] = rnd();
  }
  starGeo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  starGeo.setAttribute('aColor', new THREE.BufferAttribute(col, 3));
  starGeo.setAttribute('aMag', new THREE.BufferAttribute(mag, 1));
  starGeo.setAttribute('aPhase', new THREE.BufferAttribute(ph, 1));
  starGeo.setAttribute('aFlash', new THREE.BufferAttribute(new Float32Array(NS), 1).setUsage(THREE.DynamicDrawUsage));
}
const starMat = new THREE.ShaderMaterial({
  transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
  uniforms: { uTime: U.time, uFade: U.night, uPx: U.px },
  vertexShader: `attribute vec3 aColor; attribute float aMag; attribute float aPhase; attribute float aFlash;
    uniform float uTime; uniform float uFade; uniform float uPx; varying vec3 vCol; varying float vI;
    void main(){
      vec4 w = modelMatrix*vec4(position,1.0);
      float alt = asin(clamp(w.y/length(w.xyz), -1.0, 1.0));
      float vis = smoothstep(-0.005, 0.05, alt);
      float ext = 1.0 - 0.6*exp(-alt/0.11);
      float tw = 1.0 + 0.22*sin(uTime*(2.0 + aPhase*5.0) + aPhase*60.0)*(1.0 - smoothstep(0.0, 0.8, alt));
      float b = pow(10.0, -0.4*(aMag - 1.5));
      float fadeIn = smoothstep(aMag*0.13 - 0.1, aMag*0.13 + 0.25, uFade);   // bright stars appear first at dusk
      vI = (clamp(b, 0.11, 3.0)*ext*tw*fadeIn + aFlash*2.2) * vis;
      vCol = mix(aColor, vec3(1.0, 0.96, 0.88), clamp(aFlash, 0.0, 1.0));
      gl_Position = projectionMatrix*viewMatrix*w;
      gl_PointSize = clamp(uPx*(1.5 + 2.4*sqrt(b))*(1.0 + aFlash*1.6), 1.4, 18.0);
    }`,
  fragmentShader: `varying vec3 vCol; varying float vI;
    void main(){ vec2 c = gl_PointCoord - 0.5; float r2 = dot(c,c)*4.0;
      float I = exp(-r2*6.0) + exp(-r2*1.8)*0.22; gl_FragColor = vec4(vCol*vI*I, 1.0); }`,
});
sky.add(new THREE.Points(starGeo, starMat));
const flash = starGeo.getAttribute('aFlash');
const flashing = new Set();
function flashStar(i, a = 1) { flash.array[i] = Math.max(flash.array[i], a); flashing.add(i); }

// holes the needle pricks where no star is (they stay as faint new stars until dawn)
const PRICKS = 900;
const prickGeo = new THREE.BufferGeometry();
prickGeo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(PRICKS * 3), 3).setUsage(THREE.DynamicDrawUsage));
prickGeo.setAttribute('aBirth', new THREE.BufferAttribute(new Float32Array(PRICKS).fill(1e9), 1).setUsage(THREE.DynamicDrawUsage));
prickGeo.setDrawRange(0, 0);
let nPricks = 0;
const prickMat = new THREE.ShaderMaterial({
  transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
  uniforms: { uTime: U.time, uFade: U.fade, uPx: U.px },
  vertexShader: `attribute float aBirth; uniform float uTime; uniform float uFade; uniform float uPx; varying float vI;
    void main(){ vec4 w = modelMatrix*vec4(position,1.0); float a = uTime - aBirth;
      vI = a < 0.0 ? 0.0 : (0.32 + 2.5*exp(-a*2.5)) * uFade * smoothstep(-0.005, 0.05, w.y/length(w.xyz));
      gl_Position = projectionMatrix*viewMatrix*w; gl_PointSize = clamp(uPx*(1.6 + 2.0*exp(-a*2.5)), 1.2, 9.0); }`,
  fragmentShader: `varying float vI; void main(){ vec2 c = gl_PointCoord - 0.5; float r2 = dot(c,c)*4.0;
    gl_FragColor = vec4(vec3(0.85,0.95,1.0)*vI*exp(-r2*5.0), 1.0); }`,
});
sky.add(new THREE.Points(prickGeo, prickMat));
function addPrick(u, birth) {
  if (nPricks >= PRICKS) return;
  prickGeo.attributes.position.array.set([u[0] * R, u[1] * R, u[2] * R], nPricks * 3);
  prickGeo.attributes.aBirth.array[nPricks] = birth;
  nPricks++;
  prickGeo.attributes.position.needsUpdate = true; prickGeo.attributes.aBirth.needsUpdate = true;
  prickGeo.setDrawRange(0, nPricks);
}

// ------------------------------------------------------------------ the land: hills, ground, falaj, pool
{
  // horizon hills: the Jebel Akhdar massif rises high to the north of Nizwa, lower hills elsewhere
  const N = 360, rad = 34, pos = [], col = [], idx = [];
  const noise = a => 0.55 * Math.sin(a * 3 + 1.1) + 0.3 * Math.sin(a * 7.3 + 0.4) + 0.15 * Math.sin(a * 17.1 + 2.3);
  for (let j = 0; j <= N; j++) {
    const az = j / N * 2 * Math.PI;                        // from north toward east
    const dN = Math.min(Math.abs(az), Math.abs(az - 2 * Math.PI));
    const hDeg = 2.2 + 1.2 * noise(az) + 9 * Math.exp(-(dN * dN) / (2 * 0.55 * 0.55));
    const x = -Math.cos(az) * rad, z = -Math.sin(az) * rad, y = rad * Math.tan(Math.max(0.6, hDeg) * DEG);
    pos.push(x, -1, z, x, y, z);
    col.push(0.003, 0.003, 0.006, 0.009, 0.011, 0.024);
    if (j < N) { const a = j * 2; idx.push(a, a + 1, a + 2, a + 1, a + 3, a + 2); }
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute('color', new THREE.Float32BufferAttribute(col, 3));
  g.setIndex(idx);
  scene.add(new THREE.Mesh(g, new THREE.MeshBasicMaterial({ vertexColors: true, side: THREE.DoubleSide })));
  const ground = new THREE.Mesh(new THREE.CircleGeometry(34.5, 96), new THREE.MeshBasicMaterial({ color: 0x050509 }));
  ground.rotation.x = -Math.PI / 2;
  scene.add(ground);
}
// the falaj channel: it comes from the hills in the east and ends in a small pool in front of you
const CH = (() => {
  const raw = [];
  for (let k = 0; k <= 400; k++) {
    const z = -33 + (POOL.z + 33) * k / 400;
    const w = Math.pow(Math.min(1, Math.max(0, (-z + POOL.z - 0.4) / 4.5)), 2);
    raw.push(new THREE.Vector3((1.4 * Math.sin(0.09 * z) + 0.5 * Math.sin(0.27 * z + 1.3)) * w, 0, z));
  }
  const cum = [0];
  for (let k = 1; k < raw.length; k++) cum.push(cum[k - 1] + raw[k].distanceTo(raw[k - 1]));
  const L = cum[cum.length - 1], M = 1200, pts = [], side = [];
  let j = 0;
  for (let m = 0; m < M; m++) {
    const s = L * m / (M - 1);
    while (j < raw.length - 2 && cum[j + 1] < s) j++;
    const f = (s - cum[j]) / (cum[j + 1] - cum[j]);
    pts.push(raw[j].clone().lerp(raw[j + 1], f));
  }
  for (let m = 0; m < M; m++) {
    const a = pts[Math.max(0, m - 1)], b = pts[Math.min(M - 1, m + 1)];
    side.push(new THREE.Vector3(b.z - a.z, 0, -(b.x - a.x)).normalize());
  }
  return { L, M, pts, side, at(s, out) { const f = Math.min(1, Math.max(0, s / L)) * (M - 1), i = Math.floor(f), t = f - i;
    return out.copy(pts[i]).lerp(pts[Math.min(M - 1, i + 1)], t); }, sideAt(s) { return side[Math.round(Math.min(1, Math.max(0, s / L)) * (M - 1))]; } };
})();
const waterMat = new THREE.ShaderMaterial({
  side: THREE.DoubleSide,
  uniforms: { uTime: U.time },
  vertexShader: `attribute float aS; attribute float aSide; varying float vS; varying float vSide;
    void main(){ vS = aS; vSide = aSide; gl_Position = projectionMatrix*modelViewMatrix*vec4(position,1.0); }`,
  fragmentShader: `uniform float uTime; varying float vS; varying float vSide;
    void main(){
      float a = sin(vS*7.3 - uTime*2.9 + vSide*4.0 + sin(vS*1.3)*2.0);
      float b = sin(vS*3.1 - uTime*1.7 - vSide*3.0 + sin(vS*0.7 + uTime*0.4)*1.5);
      float g = pow(max(a*b, 0.0), 6.0);
      vec3 c = vec3(0.006,0.03,0.036) + vec3(0.05,0.24,0.22)*g*0.6;
      gl_FragColor = vec4(c*(1.0 - 0.7*vSide*vSide), 1.0); }`,
});
{
  const mk = (width, y, mat) => {
    const pos = [], aS = [], aSide = [], idx = [];
    for (let m = 0; m < CH.M; m++) {
      const p = CH.pts[m], s = CH.side[m];
      pos.push(p.x + s.x * width / 2, y, p.z + s.z * width / 2, p.x - s.x * width / 2, y, p.z - s.z * width / 2);
      const d = CH.L * m / (CH.M - 1); aS.push(d, d); aSide.push(1, -1);
      if (m < CH.M - 1) { const a = m * 2; idx.push(a, a + 2, a + 1, a + 1, a + 2, a + 3); }
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
    g.setAttribute('aS', new THREE.Float32BufferAttribute(aS, 1));
    g.setAttribute('aSide', new THREE.Float32BufferAttribute(aSide, 1));
    g.setIndex(idx);
    return new THREE.Mesh(g, mat);
  };
  scene.add(mk(0.5, 0.003, new THREE.MeshBasicMaterial({ color: 0x0b0b12, side: THREE.DoubleSide })));   // the stone banks
  scene.add(mk(0.24, 0.006, waterMat));                                         // the water
  const pool = new THREE.Mesh(new THREE.CircleGeometry(0.46, 48), waterMat.clone());
  pool.material.uniforms = { uTime: U.time };
  const pg = pool.geometry, n = pg.attributes.position.count, aS = new Float32Array(n), aSide = new Float32Array(n);
  for (let i = 0; i < n; i++) { const x = pg.attributes.position.getX(i), y = pg.attributes.position.getY(i); aS[i] = Math.hypot(x, y) * 4; aSide[i] = 0; }
  pg.setAttribute('aS', new THREE.BufferAttribute(aS, 1)); pg.setAttribute('aSide', new THREE.BufferAttribute(aSide, 1));
  pool.rotation.x = -Math.PI / 2; pool.position.copy(POOL).setY(0.008);
  scene.add(pool);
  const rim = new THREE.Mesh(new THREE.RingGeometry(0.46, 0.6, 48), new THREE.MeshBasicMaterial({ color: 0x0d0d15 }));
  rim.rotation.x = -Math.PI / 2; rim.position.copy(POOL).setY(0.005);
  scene.add(rim);
}

// ------------------------------------------------------------------ stitches: soft ribbons of thread on the sky
class Stitches {
  constructor(maxV) {
    this.max = maxV; this.n = 0; this.ni = 0;
    const g = this.geo = new THREE.BufferGeometry();
    const A = (k, s) => new THREE.BufferAttribute(new Float32Array(maxV * s), s).setUsage(THREE.DynamicDrawUsage);
    g.setAttribute('position', A('p', 3)); g.setAttribute('aU', A('u', 1)); g.setAttribute('aSide', A('s', 1));
    g.setAttribute('aTb', A('t', 1)); g.setAttribute('aSpeed', A('v', 1)); g.setAttribute('aCol', A('c', 3));
    g.setIndex(new THREE.BufferAttribute(new Uint32Array(maxV * 3), 1).setUsage(THREE.DynamicDrawUsage));
    g.setDrawRange(0, 0);
    g.boundingSphere = new THREE.Sphere(new THREE.Vector3(), R * 1.2);
    this.mat = new THREE.ShaderMaterial({
      transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide,
      uniforms: { uTime: U.time, uPulse: U.pulse, uFade: U.fade, uBase: { value: COL.base } },
      vertexShader: `attribute float aU; attribute float aSide; attribute float aTb; attribute float aSpeed; attribute vec3 aCol;
        varying float vU; varying float vSide; varying float vTb; varying float vSpeed; varying vec3 vCol; varying float vAlt;
        void main(){ vU = aU; vSide = aSide; vTb = aTb; vSpeed = aSpeed; vCol = aCol;
          vec4 w = modelMatrix*vec4(position,1.0); vAlt = w.y/length(w.xyz); gl_Position = projectionMatrix*viewMatrix*w; }`,
      fragmentShader: `uniform float uTime; uniform float uPulse; uniform float uFade; uniform vec3 uBase;
        varying float vU; varying float vSide; varying float vTb; varying float vSpeed; varying vec3 vCol; varying float vAlt;
        void main(){
          float head = (uTime - vTb)*vSpeed;
          if (vU > head) discard;
          float age = (head - vU)/max(vSpeed, 1e-5);
          float lay = smoothstep(0.0, 0.15, age);
          float tip = exp(-age*5.0);
          float glow = max(exp(-age*0.5), uPulse);
          float across = 1.0 - vSide*vSide;
          float floss = 0.8 + 0.2*cos(vSide*9.42 + vU*260.0);
          vec3 c = mix(uBase, vCol, 0.28 + 0.72*glow)*(0.40 + 1.0*glow) + vec3(1.0,0.97,0.9)*tip*1.3;
          gl_FragColor = vec4(c*across*floss*lay*uFade*smoothstep(-0.01, 0.04, vAlt), 1.0);
        }`,
    });
    this.mesh = new THREE.Mesh(g, this.mat);
    this.mesh.frustumCulled = false;
  }
  // pts: unit vectors along the thread; u0: where it starts on the needle's path; laid from time tb at speed (rad/s)
  add(pts, u0, tb, speed, col, width) {
    const n = pts.length;
    if (n < 2 || this.n + n * 2 > this.max) return;
    const g = this.geo, PA = g.attributes.position.array, AU = g.attributes.aU.array, AS = g.attributes.aSide.array,
          AT = g.attributes.aTb.array, AV = g.attributes.aSpeed.array, AC = g.attributes.aCol.array, I = g.index.array;
    let u = u0;
    const base = this.n;
    for (let k = 0; k < n; k++) {
      if (k > 0) u += ang(pts[k - 1], pts[k]);
      const p = pts[k], t = nrm(k < n - 1 ? add(pts[k + 1], scl(p, -1)) : add(p, scl(pts[k - 1], -1)));
      const s = nrm(cross(t, p));
      for (const side of [1, -1]) {
        const v = this.n++;
        PA[v * 3] = p[0] * R + s[0] * side * width / 2; PA[v * 3 + 1] = p[1] * R + s[1] * side * width / 2; PA[v * 3 + 2] = p[2] * R + s[2] * side * width / 2;
        AU[v] = u; AS[v] = side; AT[v] = tb; AV[v] = speed; AC[v * 3] = col.r; AC[v * 3 + 1] = col.g; AC[v * 3 + 2] = col.b;
      }
      if (k < n - 1) { const a = base + k * 2; I.set([a, a + 2, a + 1, a + 1, a + 2, a + 3], this.ni); this.ni += 6; }
    }
    for (const k of ['position', 'aU', 'aSide', 'aTb', 'aSpeed', 'aCol']) g.attributes[k].needsUpdate = true;
    g.index.needsUpdate = true;
    g.setDrawRange(0, this.ni);
  }
  clear() { this.n = 0; this.ni = 0; this.geo.setDrawRange(0, 0); }
}
const stitches = new Stitches(60000);
sky.add(stitches.mesh);

// shapes of the stitches
function tangentBasis(s) {
  const e1 = nrm(cross(Math.abs(s[2]) < 0.9 ? [0, 0, 1] : [1, 0, 0], s));
  return [e1, cross(s, e1)];
}
function petal(s, psi, L, W) {                       // a lazy-daisy loop, out from the star and back
  const [e1, e2] = tangentBasis(s);
  const d = add(scl(e1, Math.cos(psi)), scl(e2, Math.sin(psi))), n = add(scl(e1, -Math.sin(psi)), scl(e2, Math.cos(psi)));
  const pts = [];
  for (let j = 0; j <= 26; j++) {
    const a = j / 26 * 2 * Math.PI, r = (1 - Math.cos(a)) / 2;
    pts.push(nrm(add(s, add(scl(d, L * Math.pow(r, 0.85)), scl(n, W * Math.sin(a) * r * 1.15)))));
  }
  const tip = add(s, scl(d, L * 1.02));
  const tack = [nrm(add(tip, scl(n, -W * 0.45))), nrm(add(tip, scl(d, W * 0.18))), nrm(add(tip, scl(n, W * 0.45)))];
  return { pts, tack };
}
// the holes a running stitch passes through between two stars: it follows a gently curving vine, and its holes
// are real faint stars near the vine (or new pricks where there is none), like the punched holes of a kumma
function holesBetween(a, b, bend) {
  const total = ang(a, b), side = nrm(cross(a, b)), G = 64, guide = [], gc = [0];
  for (let j = 0; j <= G; j++) { const t = j / G; guide.push(nrm(add(slerp(a, b, t), scl(side, bend * total * Math.sin(Math.PI * t) * (1 + 0.35 * Math.sin(2 * Math.PI * t)))))); }
  for (let j = 1; j <= G; j++) gc.push(gc[j - 1] + ang(guide[j - 1], guide[j]));
  const glen = gc[G], list = [], cosMax = Math.cos(1.5 * DEG), lo = [], hi = [];
  for (let j = 0; j <= G; j++) lo.push(guide[j]);
  for (let i = 0; i < NS; i++) {
    if (ST.mag[i] < 2.4) continue;
    const v = su(i);
    if (dot(v, a) < Math.cos(total + 0.2) && dot(v, b) < Math.cos(total + 0.2)) continue;
    let best = -1, bd = cosMax;
    for (let j = 0; j <= G; j++) { const d = dot(v, guide[j]); if (d > bd) { bd = d; best = j; } }
    if (best < 0) continue;
    const along = gc[best];
    if (along > 0.9 * DEG && along < glen - 0.9 * DEG) list.push({ i, along, v });
  }
  void hi;
  list.sort((p, q) => p.along - q.along);
  const at = x => { let j = 1; while (j < G && gc[j] < x) j++; const f = (x - gc[j - 1]) / Math.max(1e-9, gc[j] - gc[j - 1]); return nrm(add(scl(guide[j - 1], 1 - f), scl(guide[j], f))); };
  const chain = [{ v: a, along: 0, i: -1 }];
  let last = 0;
  const total0 = total; void total0;
  const fill = upto => { while (upto - last > 3.6 * DEG) { last += 2.5 * DEG; chain.push({ v: at(last), along: last, i: -2 }); } };
  for (const h of list) {
    if (h.along - last < 1.4 * DEG) continue;
    fill(h.along);
    if (h.along - last < 1.4 * DEG) continue;
    chain.push(h); last = h.along;
  }
  fill(glen);
  chain.push({ v: b, along: glen, i: -1 });
  return chain;
}
function arc(a, b, bulge, n) {                        // a slightly sagging thread between two holes
  const pts = [], side = nrm(cross(a, b)), w = ang(a, b);
  for (let j = 0; j <= n; j++) { const t = j / n; pts.push(nrm(add(slerp(a, b, t), scl(side, bulge * w * Math.sin(Math.PI * t))))); }
  return pts;
}

// ------------------------------------------------------------------ particles: the falaj water and the thread
function pointsMaterial(color, minPx) {
  return new THREE.ShaderMaterial({
    transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
    uniforms: { uCol: { value: color }, uPx: U.px, uMin: { value: minPx } },
    vertexShader: `attribute float aB; attribute float aSize; uniform float uPx; uniform float uMin; varying float vB;
      void main(){ vB = aB; vec4 mv = modelViewMatrix*vec4(position,1.0); gl_Position = projectionMatrix*mv;
        gl_PointSize = clamp(aSize*uPx*900.0/max(-mv.z, 0.05), uMin*uPx, 14.0); }`,
    fragmentShader: `uniform vec3 uCol; varying float vB;
      void main(){ if (vB <= 0.002) discard; vec2 c = gl_PointCoord - 0.5; float r2 = dot(c,c)*4.0;
        gl_FragColor = vec4(mix(uCol, vec3(1.0), clamp(vB - 1.0, 0.0, 0.6))*vB*(exp(-r2*4.5) + 0.15*exp(-r2)), 1.0); }`,
  });
}
function makeCloud(n, color, minPx = 1.3) {
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(n * 3), 3).setUsage(THREE.DynamicDrawUsage));
  g.setAttribute('aB', new THREE.BufferAttribute(new Float32Array(n), 1).setUsage(THREE.DynamicDrawUsage));
  const sz = new Float32Array(n); for (let i = 0; i < n; i++) sz[i] = 0.004 + 0.008 * rnd();
  g.setAttribute('aSize', new THREE.BufferAttribute(sz, 1));
  const p = new THREE.Points(g, pointsMaterial(color, minPx));
  p.frustumCulled = false;
  scene.add(p);
  return { n, g, pos: g.attributes.position.array, b: g.attributes.aB.array, disp: new Float32Array(n * 3), stir: new Float32Array(n) };
}
const NW = 1500, NP = 260, NT = 2200;
const water = makeCloud(NW + NP, COL.water);
const thread = makeCloud(NT, new THREE.Color('#d8f4f0'), 2.1);
thread.g.attributes.aSize.array.forEach((_, i, a) => { a[i] = 0.005 + 0.012 * rnd(); });
const WS = Array.from({ length: NW }, () => ({ s: rnd() * CH.L, l: (rnd() - 0.5) * 0.18, v: 0.45 + 0.4 * rnd(), ph: rnd() * 6.28 }));
const PS = Array.from({ length: NP }, () => ({ a: rnd() * 6.28, r: Math.sqrt(rnd()) * 0.42, w: 0.2 + 0.4 * rnd(), ph: rnd() * 6.28 }));
const TS = Array.from({ length: NT }, () => ({ lag: rnd() * 0.55, o1: rnd() * 6.28, o2: rnd() * 6.28, f: 0.6 + 1.4 * rnd(),
                                             tr: Math.pow(rnd(), 1.8), j: rnd() * 6.28, vx: 0, vy: 0, vz: 0, x: 0, y: 0, z: 0 }));
let poolGlow = 0;

// ------------------------------------------------------------------ labels (Arabic star names)
function makeLabel(text) {
  const c = document.createElement('canvas'); c.width = 1024; c.height = 192;
  const x = c.getContext('2d');
  x.direction = 'rtl'; x.textAlign = 'center'; x.textBaseline = 'middle';
  x.font = '600 96px "Noto Naskh Arabic", "Geeza Pro", "DejaVu Sans", serif';
  x.shadowColor = 'rgba(120,220,210,0.6)'; x.shadowBlur = 18;
  x.fillStyle = '#efe9da'; x.fillText(text, 512, 96);
  const tex = new THREE.CanvasTexture(c); tex.colorSpace = THREE.SRGBColorSpace;
  const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, transparent: true, depthWrite: false, opacity: 0 }));
  s.scale.set(8.4, 1.58, 1);
  return s;
}
const label = { sprite: null, star: -1, t0: 0, t1: 0 };

// ------------------------------------------------------------------ sound: water, night air, maqam tones
const RAST = [0, 2, 3.5, 5, 7, 9, 10.5, 12];           // maqam Rast, with its three-quarter tones
const deg = (d, base) => base * Math.pow(2, (RAST[((d % 7) + 7) % 7] + 12 * Math.floor(d / 7)) / 12);
const sound = {
  ctx: null, on: true,
  start() {
    if (P.record) return;
    if (this.ctx) { this.ctx.resume(); return; }
    const AC = window.AudioContext || window.webkitAudioContext; if (!AC) return;
    const ctx = this.ctx = new AC();
    this.master = ctx.createGain(); this.master.gain.value = this.on ? 0.9 : 0; this.master.connect(ctx.destination);
    this.verb = ctx.createConvolver(); this.verb.buffer = this.impulse(3.4);
    const vg = ctx.createGain(); vg.gain.value = 0.4; this.verb.connect(vg); vg.connect(this.master);
    this.waterPan = this.panner(); this.waterPan.connect(this.master);
    this.waterGain = ctx.createGain(); this.waterGain.gain.value = 0.0; this.waterGain.connect(this.waterPan);
    const ws = ctx.createBufferSource(); ws.buffer = this.trickle(9); ws.loop = true; ws.connect(this.waterGain); ws.start();
    const ns = ctx.createBufferSource(); ns.buffer = this.noise(7); ns.loop = true;
    const lp = ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 300;
    this.airGain = ctx.createGain(); this.airGain.gain.value = 0.0; ns.connect(lp); lp.connect(this.airGain); this.airGain.connect(this.master); ns.start();
  },
  setOn(on) { this.on = on; if (this.master) this.master.gain.setTargetAtTime(on ? 0.9 : 0, this.ctx.currentTime, 0.2); },
  panner() { const p = this.ctx.createPanner(); p.panningModel = 'HRTF'; p.distanceModel = 'inverse'; p.refDistance = 2; p.rolloffFactor = 0.5; return p; },
  noise(sec) { const c = this.ctx, b = c.createBuffer(1, c.sampleRate * sec, c.sampleRate), d = b.getChannelData(0);
    for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1; return b; },
  impulse(sec) { const c = this.ctx, n = c.sampleRate * sec, b = c.createBuffer(2, n, c.sampleRate);
    for (let ch = 0; ch < 2; ch++) { const d = b.getChannelData(ch); for (let i = 0; i < n; i++) d[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / n, 2.6); } return b; },
  trickle(sec) {                                      // many tiny bubbles over a soft hiss: water running in a channel
    const c = this.ctx, sr = c.sampleRate, n = sr * sec, b = c.createBuffer(1, n, sr), d = b.getChannelData(0);
    for (let i = 0; i < n; i++) d[i] = (Math.random() * 2 - 1) * 0.02;
    for (let e = 0; e < sec * 55; e++) {
      const t0 = Math.floor(Math.random() * n), f0 = 500 + Math.random() * 1700, tau = 0.006 + Math.random() * 0.03, a = 0.05 + Math.random() * 0.12;
      for (let k = 0; k < tau * 5 * sr && t0 + k < n; k++) { const t = k / sr; d[t0 + k] += a * Math.exp(-t / tau) * Math.sin(2 * Math.PI * f0 * t * (1 + 0.9 * t / tau)); }
    }
    let lp = 0; for (let i = 0; i < n; i++) { lp += (d[i] - lp) * 0.55; d[i] = lp; }
    const fade = sr * 0.05; for (let i = 0; i < fade; i++) { d[i] *= i / fade; d[n - 1 - i] *= i / fade; }
    return b;
  },
  tone(freq, dir, gain, attack, decay, bright = 1) {  // a soft bell-like tone that comes from a direction
    if (!this.ctx || !this.on) return;
    const c = this.ctx, t = c.currentTime, g = c.createGain(), p = this.panner();
    p.positionX.value = dir.x * 7; p.positionY.value = dir.y * 7; p.positionZ.value = dir.z * 7;
    g.gain.setValueAtTime(0.0001, t); g.gain.linearRampToValueAtTime(gain, t + attack); g.gain.exponentialRampToValueAtTime(0.0001, t + attack + decay);
    g.connect(p); p.connect(this.master); g.connect(this.verb);
    for (const [m, a] of [[1, 1], [2, 0.22 * bright], [3.01, 0.07 * bright]]) {
      const o = c.createOscillator(), og = c.createGain(); o.frequency.value = freq * m; og.gain.value = a;
      o.connect(og); og.connect(g); o.start(t); o.stop(t + attack + decay + 0.1);
    }
  },
  listen(cam) {
    if (!this.ctx) return;
    const L = this.ctx.listener, e = cam.matrixWorld.elements;
    if (L.positionX) {
      L.positionX.value = e[12]; L.positionY.value = e[13]; L.positionZ.value = e[14];
      L.forwardX.value = -e[8]; L.forwardY.value = -e[9]; L.forwardZ.value = -e[10];
      L.upX.value = e[4]; L.upY.value = e[5]; L.upZ.value = e[6];
    } else { L.setPosition(e[12], e[13], e[14]); L.setOrientation(-e[8], -e[9], -e[10], e[4], e[5], e[6]); }
    if (this.waterPan.positionX) { this.waterPan.positionX.value = POOL.x; this.waterPan.positionY.value = 0.1; this.waterPan.positionZ.value = POOL.z; }
  },
};

// ------------------------------------------------------------------ the show: dusk, 24 athars, dawn
const show = {
  t: 0, cycle: 0, night: null, shares: [], k: -1, events: [], pulses: [], needle: [], mode: 'idle',
  cur: null,                                          // the athar being sewn
  startNight(cycle) {
    this.cycle = cycle;
    this.night = makeNight(omanDate(cycle * 14));
    this.shares = chooseShares(this.night);
    this.k = -1; this.events = []; this.pulses = []; this.needle = []; this.mode = 'idle'; this.cur = null;
    stitches.clear(); nPricks = 0; prickGeo.setDrawRange(0, 0);
    seed = 7 + cycle * 101;
  },
  tNight(T) { return DUSK + T * NIGHT; },             // show time (within the cycle) of a night fraction
  sharesEnd(k) { return k + 1 < this.shares.length ? this.shares[k + 1].T : Math.min(1, this.shares[k].T + 1.2 / ATHARS); },
};

function starWorld(i, out) { return out.set(ST.u[i * 3] * R, ST.u[i * 3 + 1] * R, ST.u[i * 3 + 2] * R).applyMatrix4(sky.matrixWorld); }

// build everything the needle will do in athar k, starting at show time ts (cycle time) and lasting D seconds
function sewAthar(k, ts, D, instant) {
  const sh = show.shares[k], si = sh.star, s = su(si);
  const ink = COL.ink[k % COL.ink.length], ink2 = COL.ink[(k + 2) % COL.ink.length];
  const nPet = ST.mag[si] < 1.0 ? 8 : ST.mag[si] < 2.2 ? 7 : 6;
  const L = (1.75 + 0.6 * Math.min(1, Math.max(0, (2.5 - ST.mag[si]) / 4))) * DEG, W = L * 0.42;
  const tb = instant ? -1e5 : 0;                     // instant: laid long ago (when starting the show midway)
  const plan = [];
  // the rosette around the share star
  const tPet0 = ts + 0.22 * D, dPet = 0.30 * D / nPet, psi0 = rnd() * Math.PI;
  for (let p = 0; p < nPet; p++) {
    const { pts, tack } = petal(s, psi0 + p * 2 * Math.PI / nPet, L, W);
    let len = 0; for (let j = 1; j < pts.length; j++) len += ang(pts[j - 1], pts[j]);
    const t0 = tPet0 + p * dPet, speed = len / (dPet * 0.82);
    stitches.add(pts, 0, instant ? tb : t0, speed, ink, 0.16);
    stitches.add(tack, 0, instant ? tb : t0 + dPet * 0.84, (ang(tack[0], tack[1]) * 2) / (dPet * 0.14), ink, 0.1);
    plan.push({ pts, t0, t1: t0 + dPet * 0.82, vis: null, holes: null, kind: 'petal', deg: p });
  }
  // running stitches: to the previous share star, and now and then to an older one nearby
  const partners = [];
  if (k > 0) {
    const order = [];
    for (let j = 0; j < k; j++) order.push({ st: show.shares[j].star, d: ang(s, su(show.shares[j].star)) });
    order.sort((p, q) => p.d - q.d);
    partners.push(order[0].st);
    const prev = show.shares[k - 1].star;
    if (k % 3 === 0 && prev !== order[0].st && ang(s, su(prev)) < 48 * DEG) partners.push(prev);
    else if (k % 2 === 0 && order.length > 1 && order[1].d < 42 * DEG) partners.push(order[1].st);
  }
  const chains = partners.map((pj, c) => holesBetween(s, su(pj), ((k + c) % 2 ? 1 : -1) * (0.10 + 0.08 * rnd())));
  const lens = chains.map(c => c[c.length - 1].along);
  const totalLen = lens.reduce((a, b) => a + b, 0) || 1;
  let tRun = ts + 0.52 * D;
  chains.forEach((chain, c) => {
    const dur = 0.30 * D * lens[c] / totalLen, speed = lens[c] / dur;
    const path = [], vis = [], holes = [];
    let u = 0;
    for (let h = 0; h < chain.length - 1; h++) {
      const a = chain[h].v, b = chain[h + 1].v, w = ang(a, b), seg = arc(a, b, (h % 2 ? -1 : 1) * 0.04, Math.max(3, Math.ceil(w / (0.4 * DEG))));
      if (h % 2 === 0) stitches.add(seg, u, instant ? tb : tRun, speed, h % 4 === 0 ? ink2 : ink, 0.15);
      for (let j = (h ? 1 : 0); j < seg.length; j++) { path.push(seg[j]); vis.push(h % 2 === 0); }
      holes.push({ at: u + w, i: chain[h + 1].i, v: chain[h + 1].v });
      u += w;
      if (chain[h + 1].i === -2) {
        if (instant) addPrick(chain[h + 1].v, -1e5);
        else show.events.push({ t: tRun + u / speed, fn: () => addPrick(chain[h + 1].v, show.t) });
      }
    }
    plan.push({ pts: path, t0: tRun, t1: tRun + dur, vis, holes, kind: 'run', deg: c });
    tRun += dur;
  });
  if (instant) return;
  // what happens when, in this athar
  const dir = new THREE.Vector3();
  show.events.push({ t: ts, fn: () => {
    flashStar(si, 1.2);
    sound.tone(deg([0, 4, 2, 5, 3, 4, 1, 4][k % 8], 130.81), starWorld(si, dir).normalize(), 0.11, 1.6, 9, 0.6);
    if (ST.name[si]) {
      if (label.sprite) { scene.remove(label.sprite); label.sprite.material.map.dispose(); label.sprite.material.dispose(); }
      label.sprite = makeLabel(ST.name[si]); label.star = si; label.t0 = ts; label.t1 = ts + 0.55 * D;
      scene.add(label.sprite);
    }
  } });
  plan.forEach(p => {
    show.events.push({ t: p.t1, fn: () => {
      const tip = p.pts[p.kind === 'petal' ? Math.floor(p.pts.length / 2) : p.pts.length - 1];
      dir.set(tip[0], tip[1], tip[2]).applyMatrix4(sky.matrixWorld).normalize();
      if (p.kind === 'petal') sound.tone(deg(p.deg + (k % 3), 523.25), dir, 0.045, 0.02, 2.6, 0.4);
      else sound.tone(deg(7 - p.deg * 2 - (k % 4), 261.63), dir, 0.05, 0.05, 4.0, 0.5);
    } });
  });
  const big = k % 6 === 5;
  show.pulses.push({ t0: ts + 0.82 * D, dur: (big ? 0.16 : 0.1) * D + 1.5, amp: big ? 1.0 : 0.55 });
  show.events.push({ t: ts + 0.82 * D, fn: () => {
    const up = new THREE.Vector3(0, 1, 0);
    for (const d of big ? [0, 2, 4, 7] : [0, 2, 4]) sound.tone(deg(d, 261.63), up, big ? 0.05 : 0.035, 1.2, big ? 8 : 5, 0.3);
  } });
  show.cur = { k, si, ts, D, plan, tRise0: ts + 0.06 * D, tRise1: ts + 0.22 * D, tRel: ts + 0.9 * D };
}

// ------------------------------------------------------------------ per-frame motion of water and thread
const _a = new THREE.Vector3(), _b = new THREE.Vector3(), _c = new THREE.Vector3(), _d = new THREE.Vector3(), _e = new THREE.Vector3();
const handPts = [];
function bez(p0, p1, p2, p3, t, out) {
  const u = 1 - t;
  return out.set(0, 0, 0).addScaledVector(p0, u * u * u).addScaledVector(p1, 3 * u * u * t).addScaledVector(p2, 3 * u * t * t).addScaledVector(p3, t * t * t);
}
function stirAt(cloud, i, x, y, z, dt) {             // a hand moving through the water pushes it and wakes its light
  let sx = cloud.disp[i * 3], sy = cloud.disp[i * 3 + 1], sz = cloud.disp[i * 3 + 2];
  const k = Math.exp(-dt * 1.6); sx *= k; sy *= k; sz *= k; cloud.stir[i] *= Math.exp(-dt * 1.2);
  for (const h of handPts) {
    const dx = x + sx - h.x, dy = y + sy - h.y, dz = z + sz - h.z, d = Math.hypot(dx, dy, dz);
    if (d < 0.3 && d > 1e-4) {
      const f = (0.3 - d) / 0.3;
      sx += (dx / d * 0.5 - dz / d * 0.8) * f * dt * 3; sy += dy / d * f * dt * 1.2; sz += (dz / d * 0.5 + dx / d * 0.8) * f * dt * 3;
      cloud.stir[i] = Math.min(2.5, cloud.stir[i] + f * dt * 6);
    }
  }
  cloud.disp[i * 3] = sx; cloud.disp[i * 3 + 1] = sy; cloud.disp[i * 3 + 2] = sz;
  return cloud.stir[i];
}
function updateWater(t, dt) {
  const pos = water.pos, b = water.b;
  for (let i = 0; i < NW; i++) {
    const w = WS[i];
    w.s += w.v * dt; if (w.s > CH.L) w.s -= CH.L;
    CH.at(w.s, _a); const sd = CH.sideAt(w.s);
    const x = _a.x + sd.x * w.l, y = 0.012 + 0.004 * Math.sin(t * 3 + w.ph), z = _a.z + sd.z * w.l;
    const st = handPts.length ? stirAt(water, i, x, y, z, dt) : 0;
    pos[i * 3] = x + water.disp[i * 3]; pos[i * 3 + 1] = y + water.disp[i * 3 + 1]; pos[i * 3 + 2] = z + water.disp[i * 3 + 2];
    const near = Math.exp(-Math.max(0, -z - 2) / 9);
    b[i] = (0.25 + 0.5 * Math.pow(0.5 + 0.5 * Math.sin(t * (2 + w.v * 3) + w.ph * 7), 6)) * (0.25 + 0.75 * near) * show.water + st;
  }
  for (let j = 0; j < NP; j++) {
    const p = PS[j], i = NW + j;
    p.a += p.w * dt * (1 + poolGlow * 2);
    const x = POOL.x + Math.cos(p.a) * p.r, z = POOL.z + Math.sin(p.a) * p.r, y = 0.014 + 0.006 * Math.sin(t * 2.3 + p.ph);
    const st = handPts.length ? stirAt(water, i, x, y, z, dt) : 0;
    pos[i * 3] = x + water.disp[i * 3]; pos[i * 3 + 1] = y + water.disp[i * 3 + 1]; pos[i * 3 + 2] = z + water.disp[i * 3 + 2];
    b[i] = (0.35 + 0.4 * Math.pow(0.5 + 0.5 * Math.sin(t * 3 + p.ph * 5), 4) + poolGlow * 0.8) * show.water + st;
  }
  water.g.attributes.position.needsUpdate = true; water.g.attributes.aB.needsUpdate = true;
}
// where the needle is on a path at time t: point (local unit vector), and whether that bit of thread is on top
function onPath(p, t, out) {
  const f = Math.min(1, Math.max(0, (t - p.t0) / (p.t1 - p.t0)));
  if (!p.cum) { p.cum = [0]; for (let j = 1; j < p.pts.length; j++) p.cum.push(p.cum[j - 1] + ang(p.pts[j - 1], p.pts[j])); }
  const target = f * p.cum[p.cum.length - 1];
  let lo = 1, hi = p.cum.length - 1;
  while (lo < hi) { const mid = (lo + hi) >> 1; if (p.cum[mid] < target) lo = mid + 1; else hi = mid; }
  const j = lo;
  const a = p.pts[j - 1], b2 = p.pts[j], s = (target - p.cum[j - 1]) / Math.max(1e-9, p.cum[j] - p.cum[j - 1]);
  out.set(a[0] + (b2[0] - a[0]) * s, a[1] + (b2[1] - a[1]) * s, a[2] + (b2[2] - a[2]) * s).normalize();
  return p.vis ? p.vis[j - 1] : true;
}
function updateThread(t, dt) {
  const pos = thread.pos, b = thread.b, cur = show.cur;
  poolGlow *= Math.exp(-dt * 0.8);
  if (!cur) { for (let i = 0; i < NT; i++) b[i] = 0; thread.g.attributes.aB.needsUpdate = true; return; }
  const M = sky.matrixWorld;
  starWorld(cur.si, _d);
  // rising: the water climbs from the pool in a loose swarm and arcs toward the star
  if (t < cur.tRise1 + 0.5) {
    const q = (t - cur.tRise0) / (cur.tRise1 - cur.tRise0);
    if (q > 0 && q < 1.2) poolGlow = Math.max(poolGlow, 0.9);
    const p0 = _a.copy(POOL).setY(0.05), p1 = _b.set(POOL.x, 3.3, POOL.z), p2 = _c.copy(_d).multiplyScalar(0.45).setY(Math.max(6.5, _d.y * 0.45 + 4));
    for (let i = 0; i < NT; i++) {
      const s = TS[i], sg = Math.min(1, Math.max(0, q * 1.55 - s.lag));
      if (sg <= 0 || q < 0) { b[i] = 0; continue; }
      bez(p0, p1, p2, _d, sg, _e);
      const A = (0.05 + 1.5 * Math.pow(sg, 1.2)) * Math.pow(Math.sin(Math.PI * Math.min(sg, 0.999)), 0.85);
      const x = _e.x + A * Math.sin(t * s.f + s.o1) * 0.7, y = _e.y + A * Math.sin(t * s.f * 0.8 + s.o2) * 0.5, z = _e.z + A * Math.cos(t * s.f * 1.1 + s.o1 + s.o2) * 0.7;
      const st = (handPts.length && sg < 0.3) ? stirAt(thread, i, x, y, z, dt) : 0;
      s.x = x + thread.disp[i * 3]; s.y = y + thread.disp[i * 3 + 1]; s.z = z + thread.disp[i * 3 + 2];
      pos[i * 3] = s.x; pos[i * 3 + 1] = s.y; pos[i * 3 + 2] = s.z;
      b[i] = (0.55 + 0.45 * Math.sin(t * 6 + s.j)) * (sg < 1 ? 1 : 0.6) + st;
    }
  } else if (t < cur.tRel) {
    // sewing: the thread gathers behind the needle, bright on top of the sky, faint where it passes behind
    let p = cur.plan.find(pl => t >= pl.t0 && t < pl.t1);
    if (!p) { // between two stitches: the needle rests at the star
      for (let i = 0; i < NT; i++) {
        const s = TS[i];
        _e.copy(_d).addScaledVector(_a.set(Math.sin(s.o1 * 3 + t), Math.cos(s.o2 * 2 + t * 0.7), Math.sin(s.o1 + s.o2 + t * 0.9)), 0.12 + 0.5 * s.tr);
        s.x += (_e.x - s.x) * Math.min(1, dt * 4); s.y += (_e.y - s.y) * Math.min(1, dt * 4); s.z += (_e.z - s.z) * Math.min(1, dt * 4);
        pos[i * 3] = s.x; pos[i * 3 + 1] = s.y; pos[i * 3 + 2] = s.z; b[i] = 0.4 + 0.3 * Math.sin(t * 5 + s.j);
      }
    } else {
      const trail = (p.kind === 'petal' ? 1.4 : 4.5) * DEG, span = p.t1 - p.t0;
      onPath(p, t, _e);                               // also builds p.cum
      const total = p.cum[p.cum.length - 1];
      for (let i = 0; i < NT; i++) {
        const s = TS[i];
        const back = s.tr * trail;
        const tt = t - back / Math.max(1e-6, total / span);
        const top = onPath(p, Math.max(p.t0, tt), _e);
        _e.multiplyScalar(R * 0.995).applyMatrix4(M);
        const jit = 0.05 + 0.25 * s.tr;
        const x = _e.x + jit * Math.sin(t * 3 * s.f + s.o1), y = _e.y + jit * Math.sin(t * 2.6 * s.f + s.o2), z = _e.z + jit * Math.cos(t * 3.3 * s.f + s.o1);
        s.x += (x - s.x) * Math.min(1, dt * 9); s.y += (y - s.y) * Math.min(1, dt * 9); s.z += (z - s.z) * Math.min(1, dt * 9);
        pos[i * 3] = s.x; pos[i * 3 + 1] = s.y; pos[i * 3 + 2] = s.z;
        b[i] = (tt < p.t0 ? 0.25 : top ? 0.9 + 0.5 * (1 - s.tr) : 0.07) * (0.7 + 0.3 * Math.sin(t * 7 + s.j));
      }
      if (p.holes) for (const h of p.holes) if (h.i >= 0 && !h.done && (t - p.t0) / span * total >= h.at) { h.done = true; flashStar(h.i, 0.9); }
    }
  } else {
    // release: the thread loosens and falls back like spray, while the water returns to the falaj
    const r = (t - cur.tRel) / (cur.D * 0.1);
    for (let i = 0; i < NT; i++) {
      const s = TS[i];
      if (r < 0.05) { s.vx = (Math.random() - 0.5) * 0.6; s.vy = -0.2 - Math.random() * 0.6; s.vz = (Math.random() - 0.5) * 0.6; }
      s.vy -= dt * 0.35; s.x += s.vx * dt; s.y += s.vy * dt; s.z += s.vz * dt;
      pos[i * 3] = s.x; pos[i * 3 + 1] = s.y; pos[i * 3 + 2] = s.z;
      b[i] = Math.max(0, 1 - r) * (0.35 + 0.3 * Math.sin(t * 6 + s.j));
    }
  }
  thread.g.attributes.position.needsUpdate = true; thread.g.attributes.aB.needsUpdate = true;
}

// ------------------------------------------------------------------ hands and controllers
const hands = [renderer.xr.getHand(0), renderer.xr.getHand(1)];
const ctrls = [renderer.xr.getController(0), renderer.xr.getController(1)];
hands.forEach(h => scene.add(h)); ctrls.forEach(c => scene.add(c));
const TIPS = ['thumb-tip', 'index-finger-tip', 'middle-finger-tip', 'ring-finger-tip', 'pinky-finger-tip'];
const tipCloud = makeCloud(10, new THREE.Color('#bfeee8'));
function updateHands() {
  handPts.length = 0;
  let n = 0;
  for (const h of hands) for (const name of TIPS) {
    const j = h.joints && h.joints[name];
    if (j && j.visible) {
      j.getWorldPosition(_a);
      if (name === 'index-finger-tip' || name === 'middle-finger-tip') handPts.push(_a.clone());
      tipCloud.pos.set([_a.x, _a.y, _a.z], n * 3); tipCloud.b[n] = 0.35; n++;
    }
  }
  if (!handPts.length) for (const c of ctrls) if (c.visible) { c.getWorldPosition(_a); handPts.push(_a.clone()); if (n < 10) { tipCloud.pos.set([_a.x, _a.y, _a.z], n * 3); tipCloud.b[n] = 0.35; n++; } }
  for (let i = n; i < 10; i++) tipCloud.b[i] = 0;
  tipCloud.g.attributes.position.needsUpdate = true; tipCloud.g.attributes.aB.needsUpdate = true;
}

// ------------------------------------------------------------------ the clock
show.water = 1;
const cycleLen = () => DUSK + NIGHT + DAWN + PAUSE;
let cycleStart = 0;
function begin() {
  show.startNight(0);
  cycleStart = 0;
  const s = Math.min(P.start, show.shares.length - 1);
  if (s > 0) {
    for (let k = 0; k < s; k++) sewAthar(k, show.tNight(show.shares[k].T), (show.sharesEnd(k) - show.shares[k].T) * NIGHT, true);
    show.k = s - 1;
    show.t = show.tNight(show.shares[s].T) - 1.5;
  } else show.t = 0;
}
function step(dt) {
  show.t += dt;
  let ct = show.t - cycleStart;
  if (ct >= cycleLen()) { cycleStart += cycleLen(); ct = show.t - cycleStart; show.startNight(show.cycle + 1); }
  const T = (ct - DUSK) / NIGHT;
  setSky(show.night.lst0 + T * show.night.span);
  scene.updateMatrixWorld();
  // light of the night
  const nightF = ct < DUSK ? smooth(0, DUSK, ct) : ct < DUSK + NIGHT ? 1 : ct < DUSK + NIGHT + DAWN ? 1 - smooth(DUSK + NIGHT, DUSK + NIGHT + DAWN * 0.85, ct) : 0;
  U.night.value = nightF;
  U.dusk.value = ct < DUSK + 0.3 * NIGHT / ATHARS ? 1 - smooth(0, DUSK * 1.2, ct) : 0;
  U.dawn.value = ct > DUSK + NIGHT ? smooth(DUSK + NIGHT, DUSK + NIGHT + DAWN, ct) : 0;
  U.fade.value = ct < DUSK + NIGHT + DAWN * 0.35 ? 1 : 1 - smooth(DUSK + NIGHT + DAWN * 0.35, DUSK + NIGHT + DAWN * 0.95, ct);
  show.water = 0.35 + 0.65 * Math.max(nightF, U.fade.value * 0.5);
  // a new athar begins when its star clears the hills
  while (show.k + 1 < show.shares.length && T >= show.shares[show.k + 1].T) {
    show.k++;
    const k = show.k, ts = show.tNight(show.shares[k].T), D = Math.max(0.6 * P.athar, (show.sharesEnd(k) - show.shares[k].T) * NIGHT);
    sewAthar(k, ts, D, false);
  }
  if (ct > DUSK + NIGHT && !show.dawnDone) {
    show.dawnDone = true;
    show.pulses.push({ t0: DUSK + NIGHT, dur: DAWN * 0.75, amp: 1.25 });
    for (const d of [0, 2, 4, 7, 9]) sound.tone(deg(d, 196), new THREE.Vector3(0, 0.4, -1).normalize(), 0.035, 2.5, 10, 0.25);
    show.cur = null;
  }
  if (ct < DUSK) show.dawnDone = false;
  // events, in time order
  show.events.sort((a, b) => a.t - b.t);
  while (show.events.length && show.events[0].t <= ct) show.events.shift().fn();
  // pulses of clarity: the whole embroidery shows its colours for a moment
  let pulse = 0;
  for (const p of show.pulses) pulse = Math.max(pulse, p.amp * smooth(p.t0, p.t0 + 0.8, ct) * (1 - smooth(p.t0 + p.dur * 0.45, p.t0 + p.dur, ct)));
  U.pulse.value = pulse;
  U.time.value = ct;
  // star flashes fade
  if (flashing.size) {
    for (const i of flashing) { flash.array[i] *= Math.exp(-dt * 1.4); if (flash.array[i] < 0.01) { flash.array[i] = 0; flashing.delete(i); } }
    flash.needsUpdate = true;
  }
  // the label hangs under its star, then fades
  if (label.sprite) {
    starWorld(label.star, _a).multiplyScalar(0.96); _a.y -= 2.4;
    label.sprite.position.copy(_a);
    label.sprite.material.opacity = 0.85 * smooth(label.t0, label.t0 + 1.5, ct) * (1 - smooth(label.t1 - 2, label.t1, ct)) * U.fade.value;
  }
  if (sound.ctx) {
    sound.waterGain.gain.setTargetAtTime(0.12 * show.water + Math.min(0.25, handStir() * 0.08), sound.ctx.currentTime, 0.3);
    sound.airGain.gain.setTargetAtTime(0.02 * nightF, sound.ctx.currentTime, 1);
  }
  updateHands();
  updateWater(ct, dt);
  updateThread(ct, dt);
  updateClock(T);
}
function handStir() { let s = 0; for (let i = 0; i < NW + NP; i += 7) s += water.stir[i]; return s / ((NW + NP) / 7) * 20; }

// ------------------------------------------------------------------ the page: enter, preview, record
const ui = document.getElementById('ui'), hud = document.getElementById('hud'), clock = document.getElementById('clock');
const btnEnter = document.getElementById('enter'), btnPreview = document.getElementById('preview'), btnMute = document.getElementById('mute');
const note = document.getElementById('note');
const AR = new Intl.NumberFormat('ar-OM'), AR2 = new Intl.NumberFormat('ar-OM', { minimumIntegerDigits: 2 });
function updateClock(T) {
  if (P.record || !hud.classList.contains('on')) return;
  const mins = Math.round((18.75 + Math.max(0, Math.min(1, T)) * NIGHT_HOURS) * 60) % 1440;
  const hh = AR2.format(Math.floor(mins / 60)), mm = AR2.format(mins % 60);
  const k = show.k, sh = show.shares[k];
  const nm = sh && ST.name[sh.star] ? ' · ' + ST.name[sh.star] : '';
  const d = show.night.date;
  clock.textContent = T < 0 ? 'الغروب' : T > 1 ? 'الفجر' :
    `الأثر ${AR.format(Math.max(1, k + 1))} من ${AR.format(ATHARS)}${nm} · ${hh}:${mm} · ليلة ${AR.format(d.d)}/${AR.format(d.m)}`;
}
let yaw = 0, pitch = 12 * DEG, dragging = false, lx = 0, ly = 0, previewing = false, running = false;
function aimCamera() { camera.rotation.set(pitch, yaw, 0, 'YXZ'); }
renderer.domElement.addEventListener('pointerdown', e => { dragging = true; lx = e.clientX; ly = e.clientY; });
addEventListener('pointerup', () => { dragging = false; });
addEventListener('pointermove', e => {
  if (!dragging || renderer.xr.isPresenting) return;
  yaw += (e.clientX - lx) * 0.004; pitch = Math.max(-0.3, Math.min(1.45, pitch + (e.clientY - ly) * 0.004)); lx = e.clientX; ly = e.clientY;
});
btnMute.addEventListener('click', () => { sound.setOn(!sound.on); btnMute.textContent = sound.on ? 'إيقاف الصوت' : 'تشغيل الصوت'; });
btnPreview.addEventListener('click', () => { sound.start(); previewing = true; running = true; ui.classList.add('hidden'); hud.classList.add('on'); });
let session = null;
btnEnter.addEventListener('click', async () => {
  sound.start();
  try {
    session = await navigator.xr.requestSession('immersive-vr', { optionalFeatures: ['local-floor', 'hand-tracking'] });
    session.addEventListener('end', () => { session = null; ui.classList.remove('hidden'); });
    await renderer.xr.setSession(session);
    if (renderer.xr.setFoveation) renderer.xr.setFoveation(0.5);
    running = true;
    ui.classList.add('hidden');
  } catch (err) { note.textContent = 'تعذّر الدخول: ' + (err && err.message ? err.message : err); }
});
if (navigator.xr && navigator.xr.isSessionSupported) {
  navigator.xr.isSessionSupported('immersive-vr').then(ok => {
    btnEnter.disabled = !ok;
    note.textContent = ok ? 'ضع النظارة، ثم اضغط «ادخل». قف أو اجلس ووجهك نحو الأمام: هناك الشرق، ومنه تطلع النجوم.'
                          : 'لتدخل العرض افتح هذه الصفحة من متصفح نظارة Meta Quest. وهنا يمكنك مشاهدته على الشاشة.';
  });
} else note.textContent = 'لتدخل العرض افتح هذه الصفحة من متصفح نظارة Meta Quest. وهنا يمكنك مشاهدته على الشاشة.';

if (document.fonts && document.fonts.load) document.fonts.load('600 96px "Noto Naskh Arabic"').catch(() => {});
begin();
aimCamera();
let last = performance.now();
function frame(dt) {
  U.px.value = renderer.xr.isPresenting ? 1.7 : Math.max(1.0, renderer.domElement.height / 620);
  step(dt);
  if (!renderer.xr.isPresenting) {
    if (P.record) {
      const ct = show.t;
      if (P.look === 'up') { yaw = 0.15 * Math.sin(ct * 0.02); pitch = 52 * DEG; }
      else if (P.look === 'tour') {      // from the horizon, up into the embroidery, and back down to the dawn
        const T = (ct - cycleStart - DUSK) / NIGHT;
        yaw = 0.18 * Math.sin(ct * 0.045);
        pitch = (9 + 50 * smooth(0.12, 0.8, T) - 42 * smooth(0.97, 1.06, T)) * DEG;
      }
      else { yaw = 0.22 * Math.sin(ct * 0.031); pitch = (10 + 14 * (0.5 - 0.5 * Math.cos(ct * 0.017))) * DEG; }
    }
    aimCamera();
  }
  sound.listen(renderer.xr.isPresenting ? renderer.xr.getCamera() : camera);
  renderer.render(scene, camera);
}
if (P.record) {
  ui.style.display = 'none';
  window.__frame = dt => frame(dt);
  window.__info = () => ({ shares: show.shares.map(s => ({ T: +s.T.toFixed(3), name: ST.name[s.star], mag: ST.mag[s.star] })), t: show.t });
  window.__ready = true;
} else {
  renderer.setAnimationLoop(() => {
    const now = performance.now(), dt = Math.min(0.05, (now - last) / 1000); last = now;
    if (running || renderer.xr.isPresenting) frame(dt);
  });
}
