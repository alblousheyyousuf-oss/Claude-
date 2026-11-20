// The Luminous Sea — a WebXR light show.
// On some nights the sea along the beaches of Muscat glows turquoise wherever the water moves: tiny plankton
// (Noctiluca scintillans) flash when they are disturbed. Here one living mass of that light floats in front of you,
// room-sized, fast as a school of fish: it stretches, curls, splits and comes back together, startles and
// regathers. It is almost dark while it glides; every sudden turn, every wave that runs through it and every
// touch of your hand makes it flash. No lines, no symbols: only organic light.
import * as THREE from 'three';
import { GPUComputationRenderer } from 'three/addons/misc/GPUComputationRenderer.js';

// ------------------------------------------------------------------ parameters
const Q = new URLSearchParams(location.search);
const num = (k, d) => (Q.has(k) && isFinite(parseFloat(Q.get(k))) ? parseFloat(Q.get(k)) : d);
const P = {
  n: Math.max(64, Math.min(512, Math.round(num('n', 256)))),   // particles = n * n
  speed: Math.max(0.3, Math.min(2.5, num('speed', 1))),
  glow: Math.max(0.3, Math.min(3, num('glow', 1))),
  record: Q.has('record'),
  look: Q.get('look') || 'orbit',
};
const SIM = P.n, N = SIM * SIM;
const CENTER = new THREE.Vector3(0, 1.35, -2.6);     // where the mass lives: in front of you, about room-sized
const smooth = (a, b, x) => { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); };
let seed = 11;
const rnd = () => { seed = (seed * 16807) % 2147483647; return (seed - 1) / 2147483646; };

// ------------------------------------------------------------------ renderer, scene, camera
const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance', preserveDrawingBuffer: P.record });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(innerWidth, innerHeight);
renderer.setClearColor(0x010207, 1);
renderer.xr.enabled = true;
renderer.xr.setReferenceSpaceType('local-floor');
document.body.appendChild(renderer.domElement);
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(70, innerWidth / innerHeight, 0.05, 100);
camera.position.set(0, 1.6, 1.2);
scene.add(camera);
addEventListener('resize', () => {
  if (P.record) return;
  camera.aspect = innerWidth / innerHeight; camera.updateProjectionMatrix(); renderer.setSize(innerWidth, innerHeight);
});
const mass = new THREE.Group();
mass.position.copy(CENTER);
scene.add(mass);

// ------------------------------------------------------------------ the simulation, on the graphics card
const gpu = new GPUComputationRenderer(SIM, SIM, renderer);
gpu.setDataType(THREE.HalfFloatType);                   // safe on the headset
const pos0 = gpu.createTexture(), vel0 = gpu.createTexture();
for (let i = 0; i < N; i++) {
  // at first the light lies scattered on the dark water below, then it gathers into one mass
  const a = rnd() * Math.PI * 2, r = 1.2 + 3.4 * Math.sqrt(rnd());
  pos0.image.data.set([Math.cos(a) * r, -1.3 + 0.15 * rnd(), Math.sin(a) * r, rnd()], i * 4);
  vel0.image.data.set([0, 0, 0, 0], i * 4);
}
const NOISE = /* glsl */`
vec4 permute(vec4 x){return mod(((x*34.0)+1.0)*x,289.0);}
vec4 taylorInvSqrt(vec4 r){return 1.79284291400159-0.85373472095314*r;}
float snoise(vec3 v){const vec2 C=vec2(1.0/6.0,1.0/3.0);const vec4 D=vec4(0.0,0.5,1.0,2.0);
vec3 i=floor(v+dot(v,C.yyy));vec3 x0=v-i+dot(i,C.xxx);vec3 g=step(x0.yzx,x0.xyz);vec3 l=1.0-g;
vec3 i1=min(g.xyz,l.zxy);vec3 i2=max(g.xyz,l.zxy);vec3 x1=x0-i1+C.xxx;vec3 x2=x0-i2+2.0*C.xxx;vec3 x3=x0-1.0+3.0*C.xxx;
i=mod(i,289.0);vec4 p=permute(permute(permute(i.z+vec4(0.0,i1.z,i2.z,1.0))+i.y+vec4(0.0,i1.y,i2.y,1.0))+i.x+vec4(0.0,i1.x,i2.x,1.0));
float n_=1.0/7.0;vec3 ns=n_*D.wyz-D.xzx;vec4 j=p-49.0*floor(p*ns.z*ns.z);vec4 x_=floor(j*ns.z);vec4 y_=floor(j-7.0*x_);
vec4 x=x_*ns.x+ns.yyyy;vec4 y=y_*ns.x+ns.yyyy;vec4 h=1.0-abs(x)-abs(y);vec4 b0=vec4(x.xy,y.xy);vec4 b1=vec4(x.zw,y.zw);
vec4 s0=floor(b0)*2.0+1.0;vec4 s1=floor(b1)*2.0+1.0;vec4 sh=-step(h,vec4(0.0));vec4 a0=b0.xzyw+s0.xzyw*sh.xxyy;vec4 a1=b1.xzyw+s1.xzyw*sh.zzww;
vec3 p0=vec3(a0.xy,h.x);vec3 p1=vec3(a0.zw,h.y);vec3 p2=vec3(a1.xy,h.z);vec3 p3=vec3(a1.zw,h.w);
vec4 norm=taylorInvSqrt(vec4(dot(p0,p0),dot(p1,p1),dot(p2,p2),dot(p3,p3)));p0*=norm.x;p1*=norm.y;p2*=norm.z;p3*=norm.w;
vec4 m=max(0.6-vec4(dot(x0,x0),dot(x1,x1),dot(x2,x2),dot(x3,x3)),0.0);m=m*m;
return 42.0*dot(m*m,vec4(dot(p0,x0),dot(p1,x1),dot(p2,x2),dot(p3,x3)));}
vec3 snoise3(vec3 p){return vec3(snoise(p),snoise(p+vec3(31.4,-17.2,9.1)),snoise(p+vec3(-7.7,23.3,51.9)));}
vec3 curl(vec3 p){const float e=0.1;
 vec3 dx=vec3(e,0,0),dy=vec3(0,e,0),dz=vec3(0,0,e);
 vec3 px0=snoise3(p-dx),px1=snoise3(p+dx),py0=snoise3(p-dy),py1=snoise3(p+dy),pz0=snoise3(p-dz),pz1=snoise3(p+dz);
 return vec3(py1.z-py0.z-pz1.y+pz0.y, pz1.x-pz0.x-px1.z+px0.z, px1.y-px0.y-py1.x+py0.x)/(2.0*e);}
`;
const velShader = /* glsl */`
uniform float uTime, uDt, uForm, uFlow, uFreq, uSwirl, uDecay, uThr, uGain, uWaveGain, uHandGain, uEdgeGain, uStartle;
uniform vec3 uL[4]; uniform vec3 uLV[4]; uniform vec3 uDrift; uniform vec3 uStartleAt;
uniform vec4 uWave[3];
uniform vec4 uHand[4]; uniform vec3 uHandV[4];
${NOISE}
void main(){
  vec2 uv = gl_FragCoord.xy / resolution.xy;
  vec4 Pp = texture2D(texturePosition, uv); vec4 V = texture2D(textureVelocity, uv);
  vec3 p = Pp.xyz, v = V.xyz; float flash = V.w, s = Pp.w;
  int j = int(floor(s * 3.999));
  vec3 L = uL[0], lv = uLV[0];
  if (j == 1) { L = uL[1]; lv = uLV[1]; } else if (j == 2) { L = uL[2]; lv = uLV[2]; } else if (j == 3) { L = uL[3]; lv = uLV[3]; }
  float spd = length(lv); vec3 md = spd > 1e-3 ? lv / spd : vec3(0.0, 0.0, 1.0);
  vec3 rel = p - L;
  // like a school of fish, each lobe stretches along its way: the particles gather around a spine, not a point
  float along = clamp(dot(rel, md), -1.2, 1.2) * (0.45 + 0.55 * smoothstep(0.15, 1.0, spd));
  vec3 toT = L + md * along - p; float d = length(toT) + 1e-4;
  // ride the water: organic currents that curl and stretch
  vec3 flow = curl(p * uFreq + vec3(uTime * 0.13, uTime * 0.08, -uTime * 0.1)) * uFlow;
  vec3 acc = (flow + uDrift - v) * 2.0;
  // one mass, in up to four lobes that part and rejoin; each lobe rolls around its spine as it goes
  acc += toT * (2.4 + 7.0 * smoothstep(0.3, 1.1, d)) * uForm;
  acc += cross(md, toT) / (d + 0.35) * uSwirl * uForm;
  // the startle of a school of fish: everyone darts away from one point, then the mass regathers
  vec3 ds = p - uStartleAt; float dsl = length(ds) + 1e-3;
  acc += ds / dsl * uStartle * (8.0 + 6.0 * s) * exp(-dsl * 0.6);
  // stay in the room
  float r = length(p); acc -= p / max(r, 1e-3) * max(r - 2.5, 0.0) * 7.0;
  acc.y += max(-1.15 - p.y, 0.0) * 30.0;                      // the light never sinks into the water below
  // the hand stirs the water
  float hn = 0.0;
  for (int k = 0; k < 4; k++) {
    vec3 dh = p - uHand[k].xyz; float dd = length(dh);
    float f = uHand[k].w * (1.0 - smoothstep(0.0, 0.42, dd));
    acc += (uHandV[k] * 10.0 + dh / max(dd, 1e-3) * 2.5) * f;
    hn += f;
  }
  vec3 vn = v + acc * uDt;
  float sp = length(vn); if (sp > 7.5) vn *= 7.5 / sp;
  // the light of the plankton: a flash when the water is disturbed (a sudden change of motion),
  // where a wave runs through, and under the hand; then it fades back into the dark
  float jerk = length(vn - v) / max(uDt, 1e-3);
  // the front of a lobe pushing fast through the water
  float edge = smoothstep(0.35, 1.25, dot(rel, md)) * smoothstep(0.35, 1.3, spd);
  // and, here and there, a single plankton sparks for no reason at all
  float spark = step(0.9988, fract(sin(dot(uv + floor(uTime * 9.0) * 0.173, vec2(12.9898, 78.233))) * 43758.5453));
  float wave = 0.0;
  for (int k = 0; k < 3; k++) {
    float dw = abs(length(p - uWave[k].xyz) - uWave[k].w);
    wave += step(0.0, uWave[k].w) * exp(-dw * dw * 22.0);
  }
  flash = flash * exp(-uDt * uDecay) + (smoothstep(uThr, uThr * 2.5, jerk) * uGain + wave * uWaveGain + hn * uHandGain + edge * uEdgeGain) * uDt + spark * 0.9;
  gl_FragColor = vec4(vn, min(flash, 3.0));
}`;
const posShader = /* glsl */`
uniform float uDt;
void main(){ vec2 uv = gl_FragCoord.xy / resolution.xy;
  vec4 P = texture2D(texturePosition, uv); vec4 V = texture2D(textureVelocity, uv);
  gl_FragColor = vec4(P.xyz + V.xyz * uDt, P.w); }`;
const velVar = gpu.addVariable('textureVelocity', velShader, vel0);
const posVar = gpu.addVariable('texturePosition', posShader, pos0);
gpu.setVariableDependencies(velVar, [posVar, velVar]);
gpu.setVariableDependencies(posVar, [posVar, velVar]);
const VU = velVar.material.uniforms, PU = posVar.material.uniforms;
Object.assign(VU, {
  uTime: { value: 0 }, uDt: { value: 1 / 72 }, uForm: { value: 0 }, uFlow: { value: 0.8 }, uFreq: { value: 0.85 },
  uSwirl: { value: 2.4 }, uDecay: { value: 3.2 }, uThr: { value: 11.0 }, uGain: { value: 7.0 }, uWaveGain: { value: 16.0 },
  uHandGain: { value: 30.0 }, uEdgeGain: { value: 7.0 }, uStartle: { value: 0 }, uStartleAt: { value: new THREE.Vector3() }, uDrift: { value: new THREE.Vector3() },
  uL: { value: [0, 1, 2, 3].map(() => new THREE.Vector3()) }, uLV: { value: [0, 1, 2, 3].map(() => new THREE.Vector3()) },
  uWave: { value: [0, 1, 2].map(() => new THREE.Vector4(0, 0, 0, -1)) },
  uHand: { value: [0, 1, 2, 3].map(() => new THREE.Vector4(0, 0, 0, 0)) }, uHandV: { value: [0, 1, 2, 3].map(() => new THREE.Vector3()) },
});
PU.uDt = { value: 1 / 72 };
const gpuErr = gpu.init();
if (gpuErr) console.error(gpuErr);

// ------------------------------------------------------------------ drawing the light (and its reflection on the water)
const geo = new THREE.BufferGeometry();
{
  const ref = new Float32Array(N * 2);
  for (let i = 0; i < N; i++) { ref[i * 2] = (i % SIM + 0.5) / SIM; ref[i * 2 + 1] = (Math.floor(i / SIM) + 0.5) / SIM; }
  geo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(N * 3), 3));
  geo.setAttribute('ref', new THREE.BufferAttribute(ref, 2));
  geo.boundingSphere = new THREE.Sphere(new THREE.Vector3(), 50);
}
const LU = { tPos: { value: null }, tVel: { value: null }, uPx: { value: 800 }, uFade: { value: 0 }, uGlow: { value: P.glow } };
function lightMaterial(mirror) {
  return new THREE.ShaderMaterial({
    transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
    uniforms: { ...LU, uMirror: { value: mirror ? 1 : 0 } },
    vertexShader: /* glsl */`
      attribute vec2 ref; uniform sampler2D tPos, tVel; uniform float uPx, uFade, uGlow, uMirror;
      varying vec3 vCol; varying float vI;
      void main(){
        vec4 P = texture2D(tPos, ref); vec4 V = texture2D(tVel, ref);
        float f = clamp(V.w, 0.0, 3.0), s = P.w;
        vec4 w = modelMatrix * vec4(P.xyz, 1.0);
        if (uMirror > 0.5) w.y = -w.y;                      // seen again in the dark water below
        vec4 mv = viewMatrix * w;
        gl_Position = projectionMatrix * mv;
        vec3 deep = mix(vec3(0.03, 0.13, 0.26), vec3(0.05, 0.26, 0.36), s);
        vec3 glow = mix(vec3(0.08, 0.62, 1.0), vec3(0.7, 0.97, 1.0), smoothstep(1.2, 2.7, f));
        vCol = mix(deep, glow, smoothstep(0.0, 0.5, f));
        vI = (1.0 + 2.4 * f * uGlow) * uFade * (uMirror > 0.5 ? 0.14 : 1.0);
        gl_PointSize = clamp((0.006 + 0.004 * s + 0.013 * f) * uPx / max(-mv.z, 0.05), 1.0, 22.0);
      }`,
    fragmentShader: /* glsl */`
      varying vec3 vCol; varying float vI;
      void main(){ vec2 c = gl_PointCoord - 0.5; float r2 = dot(c, c) * 4.0; if (r2 > 1.0) discard;
        gl_FragColor = vec4(vCol * vI * exp(-r2 * 3.0), 1.0); }`,
  });
}
const light = new THREE.Points(geo, lightMaterial(false));
light.frustumCulled = false;
mass.add(light);
const reflection = new THREE.Points(geo, lightMaterial(true));
reflection.frustumCulled = false;
mass.add(reflection);
// the dark water under your feet (just enough to feel it)
{
  const water = new THREE.Mesh(new THREE.CircleGeometry(30, 64), new THREE.MeshBasicMaterial({ color: 0x02050a, depthWrite: false }));
  water.rotation.x = -Math.PI / 2; water.position.y = -0.002; water.renderOrder = -1;   // the reflection shows through it
  scene.add(water);
}

// ------------------------------------------------------------------ the choreography: no beginning, no end
const tmp = new THREE.Vector3(), tmp2 = new THREE.Vector3();
const UP = new THREE.Vector3(0, 1, 0);
function base(t, out) {
  return out.set(0.8 * Math.sin(0.71 * t) + 0.36 * Math.sin(1.53 * t + 1),
                 0.32 * Math.sin(0.57 * t + 2) + 0.18 * Math.sin(1.31 * t),
                 0.5 * Math.sin(0.49 * t + 0.5) + 0.26 * Math.sin(1.19 * t + 2));
}
const prevL = [0, 1, 2, 3].map(() => new THREE.Vector3()), haveL = { ok: false };
const waves = [{ t0: -99, o: new THREE.Vector3() }, { t0: -99, o: new THREE.Vector3() }, { t0: -99, o: new THREE.Vector3() }];
let nextWave = 3, nextStartle = 9, startleT = -99, waveIdx = 0;
const audio = { level: 0 };
function choreograph(t, dt) {
  VU.uTime.value = t;
  VU.uForm.value = smooth(0.5, 7, t);
  LU.uFade.value = smooth(0, 2.5, t);
  base(t, tmp);
  // the mass parts into lobes and rejoins, again and again
  const split = smooth(0.2, 0.9, 0.5 + 0.5 * Math.sin(0.27 * t + 1.2)) * (0.65 + 0.35 * Math.sin(0.11 * t));
  const d0 = tmp2.set(Math.cos(0.31 * t), 0.35 * Math.sin(0.23 * t), Math.sin(0.31 * t)).normalize();
  const d2 = new THREE.Vector3().crossVectors(d0, UP).normalize();
  const dirs = [d0, d0.clone().negate(), d2.clone().multiplyScalar(0.6), d2.clone().multiplyScalar(-0.6)];
  for (let j = 0; j < 4; j++) {
    // each lobe also wanders on its own, so the mass curls and its parts overtake one another
    const own = new THREE.Vector3(0.25 * Math.sin(1.7 * t + j * 1.9), 0.18 * Math.sin(1.3 * t + j * 2.7), 0.25 * Math.cos(1.5 * t + j * 1.3));
    const Lj = VU.uL.value[j].copy(tmp).addScaledVector(dirs[j], split * 0.8).add(own);
    if (haveL.ok && dt > 0) VU.uLV.value[j].lerp(Lj.clone().sub(prevL[j]).divideScalar(dt), 0.2);
    prevL[j].copy(Lj);
  }
  haveL.ok = true;
  // the whole mass glides like a school (its particles carry this motion)
  const b2 = base(t + 0.05, new THREE.Vector3());
  VU.uDrift.value.copy(b2).sub(tmp).multiplyScalar(20 * 0.8);
  // waves of light that run through the mass
  if (t > nextWave) {
    const w = waves[waveIdx++ % 3];
    w.t0 = t; w.o.copy(tmp).add(new THREE.Vector3(rnd() - 0.5, rnd() - 0.5, rnd() - 0.5).normalize().multiplyScalar(1.3));
    nextWave = t + 0.7 + 1.0 * rnd();
    sound.swish(w.o, 0.5);
  }
  waves.forEach((w, k) => { const age = t - w.t0; VU.uWave.value[k].set(w.o.x, w.o.y, w.o.z, age < 1.3 ? age * 3.4 : -1); });
  // now and then the school startles: it bursts apart in a flash and gathers again
  if (t > nextStartle) {
    startleT = t;
    VU.uStartleAt.value.copy(tmp).add(new THREE.Vector3(rnd() - 0.5, rnd() - 0.5, rnd() - 0.5).multiplyScalar(1.2));
    nextStartle = t + 7 + 8 * rnd();
    sound.swish(VU.uStartleAt.value, 1.0);
  }
  const st = t - startleT;
  VU.uStartle.value = st >= 0 && st < 0.6 ? Math.sin(Math.PI * st / 0.6) : 0;
  audio.level = 0.3 + 0.7 * VU.uStartle.value + 0.3 * split;
}

// ------------------------------------------------------------------ hands and controllers
const hands = [renderer.xr.getHand(0), renderer.xr.getHand(1)];
const ctrls = [renderer.xr.getController(0), renderer.xr.getController(1)];
hands.forEach(h => scene.add(h)); ctrls.forEach(c => scene.add(c));
const prevHand = [0, 1, 2, 3].map(() => ({ p: new THREE.Vector3(), ok: false, v: new THREE.Vector3() }));
function updateHands(dt) {
  const pts = [];
  for (const h of hands) for (const name of ['index-finger-tip', 'middle-finger-tip']) {
    const j = h.joints && h.joints[name];
    if (j && j.visible) pts.push(j.getWorldPosition(new THREE.Vector3()));
  }
  if (!pts.length) for (const c of ctrls) if (c.visible) pts.push(c.getWorldPosition(new THREE.Vector3()));
  let stir = 0;
  for (let k = 0; k < 4; k++) {
    const H = VU.uHand.value[k], HV = VU.uHandV.value[k], ph = prevHand[k];
    if (k < pts.length) {
      const local = pts[k].clone().sub(CENTER);
      if (ph.ok && dt > 0) ph.v.lerp(local.clone().sub(ph.p).divideScalar(dt), 0.5);
      ph.p.copy(local); ph.ok = true;
      H.set(local.x, local.y, local.z, 1); HV.copy(ph.v).clampLength(0, 4);
      stir += Math.min(1, ph.v.length() * 0.5);
    } else { H.w = 0; HV.set(0, 0, 0); ph.ok = false; }
  }
  return stir;
}

// ------------------------------------------------------------------ sound: the sea at night, and its sparkle
const sound = {
  ctx: null, on: true,
  start() {
    if (P.record) return;
    if (this.ctx) { this.ctx.resume(); return; }
    const AC = window.AudioContext || window.webkitAudioContext; if (!AC) return;
    const c = this.ctx = new AC();
    this.master = c.createGain(); this.master.gain.value = this.on ? 0.8 : 0; this.master.connect(c.destination);
    const noise = this.noise(6);
    // the sea: low rolling noise that swells slowly
    const sea = c.createBufferSource(); sea.buffer = noise; sea.loop = true;
    const lp = c.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 420;
    this.seaGain = c.createGain(); this.seaGain.gain.value = 0;
    sea.connect(lp); lp.connect(this.seaGain); this.seaGain.connect(this.master); sea.start();
    // the sparkle of the light: a soft fizz that follows how much the mass is flashing
    const fz = c.createBufferSource(); fz.buffer = noise; fz.loop = true; fz.playbackRate.value = 1.3;
    const hp = c.createBiquadFilter(); hp.type = 'highpass'; hp.frequency.value = 3800;
    this.fizzGain = c.createGain(); this.fizzGain.gain.value = 0;
    fz.connect(hp); hp.connect(this.fizzGain); this.fizzGain.connect(this.master); fz.start();
  },
  setOn(on) { this.on = on; if (this.master) this.master.gain.setTargetAtTime(on ? 0.8 : 0, this.ctx.currentTime, 0.2); },
  noise(sec) { const c = this.ctx, b = c.createBuffer(1, c.sampleRate * sec, c.sampleRate), d = b.getChannelData(0);
    let last = 0; for (let i = 0; i < d.length; i++) { const w = Math.random() * 2 - 1; last = (last + 0.02 * w) / 1.02; d[i] = w * 0.6 + last * 6; } return b; },
  swish(local, amp) {                                  // a wave of light passing: a soft rush from where it starts
    if (!this.ctx || !this.on) return;
    const c = this.ctx, t = c.currentTime, s = c.createBufferSource(); s.buffer = this.noise(2);
    const bp = c.createBiquadFilter(); bp.type = 'bandpass'; bp.frequency.setValueAtTime(600, t); bp.frequency.exponentialRampToValueAtTime(2600, t + 0.9); bp.Q.value = 0.7;
    const g = c.createGain(); g.gain.setValueAtTime(0.0001, t); g.gain.linearRampToValueAtTime(0.05 * amp, t + 0.25); g.gain.exponentialRampToValueAtTime(0.0001, t + 1.6);
    const pn = c.createPanner(); pn.panningModel = 'HRTF';
    const w = local.clone().add(CENTER); pn.positionX.value = w.x; pn.positionY.value = w.y; pn.positionZ.value = w.z;
    s.connect(bp); bp.connect(g); g.connect(pn); pn.connect(this.master); s.start(t); s.stop(t + 1.8);
  },
  update(level, stir, cam) {
    if (!this.ctx) return;
    const t = this.ctx.currentTime;
    this.seaGain.gain.setTargetAtTime(0.05 * (0.7 + 0.3 * Math.sin(t * 0.4)), t, 0.5);
    this.fizzGain.gain.setTargetAtTime(Math.min(0.06, 0.012 * level + 0.05 * stir), t, 0.15);
    const L = this.ctx.listener, e = cam.matrixWorld.elements;
    if (L.positionX) {
      L.positionX.value = e[12]; L.positionY.value = e[13]; L.positionZ.value = e[14];
      L.forwardX.value = -e[8]; L.forwardY.value = -e[9]; L.forwardZ.value = -e[10]; L.upX.value = e[4]; L.upY.value = e[5]; L.upZ.value = e[6];
    }
  },
};

// ------------------------------------------------------------------ one step of the show
let simT = 0;
function step(dt) {
  dt = Math.min(dt, 1 / 30) * P.speed;
  simT += dt;
  choreograph(simT, dt);
  const stir = updateHands(dt);
  VU.uDt.value = dt; PU.uDt.value = dt;
  // compute the water with XR switched off for a moment (otherwise the headset camera would be used for it)
  const xrOn = renderer.xr.enabled;
  renderer.xr.enabled = false;
  gpu.compute();
  renderer.xr.enabled = xrOn;
  LU.tPos.value = gpu.getCurrentRenderTarget(posVar).texture;
  LU.tVel.value = gpu.getCurrentRenderTarget(velVar).texture;
  sound.update(audio.level, stir, renderer.xr.isPresenting ? renderer.xr.getCamera() : camera);
}

// ------------------------------------------------------------------ the page: enter, preview, record
const ui = document.getElementById('ui'), hud = document.getElementById('hud'), clock = document.getElementById('clock');
const btnEnter = document.getElementById('enter'), btnPreview = document.getElementById('preview'), btnMute = document.getElementById('mute');
const note = document.getElementById('note');
let running = false, yaw = 0, pitch = 0, dragging = false, lx = 0, ly = 0;
const follow = new THREE.Vector3();
function aim() {
  base(simT, tmp2).multiplyScalar(0.85).add(CENTER);
  follow.lerp(tmp2, 0.08);
  camera.position.set(follow.x + Math.sin(yaw) * 4.2, 1.6, follow.z + Math.cos(yaw) * 4.2);
  camera.lookAt(follow.x, follow.y + pitch, follow.z);
}
renderer.domElement.addEventListener('pointerdown', e => { dragging = true; lx = e.clientX; ly = e.clientY; });
addEventListener('pointerup', () => { dragging = false; });
addEventListener('pointermove', e => {
  if (!dragging || renderer.xr.isPresenting) return;
  yaw -= (e.clientX - lx) * 0.005; pitch = Math.max(-1.2, Math.min(1.5, pitch + (e.clientY - ly) * 0.004)); lx = e.clientX; ly = e.clientY;
});
btnMute.addEventListener('click', () => { sound.setOn(!sound.on); btnMute.textContent = sound.on ? 'إيقاف الصوت' : 'تشغيل الصوت'; });
btnPreview.addEventListener('click', () => { sound.start(); running = true; ui.classList.add('hidden'); hud.classList.add('on'); clock.textContent = 'اسحب لتدور حول الكتلة'; });
btnEnter.addEventListener('click', async () => {
  sound.start();
  try {
    const session = await navigator.xr.requestSession('immersive-vr', { optionalFeatures: ['local-floor', 'hand-tracking'] });
    session.addEventListener('end', () => { ui.classList.remove('hidden'); });
    await renderer.xr.setSession(session);
    if (renderer.xr.setFoveation) renderer.xr.setFoveation(0.4);
    running = true;
    ui.classList.add('hidden');
  } catch (err) { note.textContent = 'تعذّر الدخول: ' + (err && err.message ? err.message : err); }
});
const NOTE_NO_XR = 'لتدخل العرض افتح هذه الصفحة من متصفح نظارة Meta Quest. وهنا يمكنك مشاهدته على الشاشة.';
if (navigator.xr && navigator.xr.isSessionSupported) {
  navigator.xr.isSessionSupported('immersive-vr').then(ok => {
    btnEnter.disabled = !ok;
    note.textContent = ok ? 'ضع النظارة واضغط «ادخل». الكتلة أمامك، ويمكنك أن تمشي حولها وتمدّ يدك فيها.' : NOTE_NO_XR;
  });
} else note.textContent = NOTE_NO_XR;

follow.copy(CENTER);
aim();
let last = performance.now();
function frame(dt) {
  LU.uPx.value = renderer.xr.isPresenting ? 950 : renderer.domElement.height / (2 * Math.tan(camera.fov * Math.PI / 360));
  step(dt);
  if (!renderer.xr.isPresenting && P.record) {
    if (P.look === 'orbit') { yaw = 0.55 * Math.sin(simT * 0.05); pitch = 0.05; }
    else if (P.look === 'close') { yaw = 0.25 * Math.sin(simT * 0.07); pitch = 0; camera.fov = 62; camera.updateProjectionMatrix(); }
  }
  if (!renderer.xr.isPresenting) aim();
  renderer.render(scene, camera);
}
if (P.record) {
  ui.style.display = 'none';
  window.__frame = dt => frame(dt);
  window.__info = () => ({ n: N, t: simT });
  window.__sync = () => { const gl = renderer.getContext(), px = new Uint8Array(4); gl.readPixels(0, 0, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, px); };
  window.__ready = !gpuErr;
} else {
  renderer.setAnimationLoop(() => {
    const now = performance.now(), dt = Math.min(0.05, (now - last) / 1000); last = now;
    if (running || renderer.xr.isPresenting) frame(dt);
  });
}
