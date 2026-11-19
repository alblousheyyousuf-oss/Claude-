"""OB-Sim runner: plays an Open Brush plugin frame by frame with the emulated API and writes a log for the renderer.
usage: python3 obsim_run.py PLUGIN.lua OUT.json --seconds 75 [--scale 1] [--set size=0.55 ...]"""
import argparse, json, math, random, sys
from pathlib import Path
from lupa import LuaRuntime

ap = argparse.ArgumentParser()
ap.add_argument("plugin"); ap.add_argument("out")
ap.add_argument("--seconds", type=float, default=75); ap.add_argument("--fps", type=float, default=72)
ap.add_argument("--sample", type=float, default=30); ap.add_argument("--scale", type=float, default=1.0)
ap.add_argument("--seed", type=int, default=3); ap.add_argument("--set", action="append", default=[])
ap.add_argument("--trigger-at", type=float, default=-1)
ap.add_argument("--no-dwb", action="store_true", help="emulate an older Open Brush without Path:DrawWithBrush")
ap.add_argument("--count", action="store_true", help="count the Lua VM instructions the plugin runs per frame (sampled)")
a = ap.parse_args()
random.seed(a.seed)
lua = LuaRuntime(unpack_returned_tuples=True)
lua.globals().SIMRAND = random.random
lua.execute((Path(__file__).parent / "api.lua").read_text())
G = lua.globals()
# the user: hand in front of the chest, pointing forward and slightly down (canvas units, 10 = 1 m at scale 1)
G.SIM.scale = a.scale
hand = (0.0, 12.0, 0.0)
yaw = math.radians(15)
direction = (math.sin(yaw), -0.15, math.cos(yaw))
lua.execute(f"HAND.pos = Vector3:New({hand[0]}, {hand[1]}, {hand[2]})")
lua.execute(f"HAND.rot = Rotation:LookRotation(Vector3:New({-direction[0]}, {-direction[1]}, {-direction[2]}), Vector3.up)")
if a.no_dwb: lua.execute("Path.DrawWithBrush = function() error('no such method') end")
src = Path(a.plugin).read_text()
G.load(src, "=plugin")()
lua.execute("for k, v in pairs(Parameters or {}) do Parameters[k] = v.default end")
for kv in a.set:
    k, v = kv.split("="); lua.execute(f"Parameters.{k} = {v}")
lua.execute("""
VMC = {all = 0, plugin = 0}
function VMC_on()
    debug.sethook(function()
        VMC.all = VMC.all + 1
        local info = debug.getinfo(2, "S")
        if info and info.source == "=plugin" then VMC.plugin = VMC.plugin + 1 end
    end, "", 50)
end
function VMC_off() debug.sethook() end
""")
safe = lua.eval("function(f) local ok, err = pcall(f); if not ok then LOG.errors[#LOG.errors + 1] = tostring(err) end end")
if G.Start: safe(G.Start)
frames = int(a.seconds * a.fps)
samples, perf, vm = [], [], []
next_sample = 0.0
for f in range(frames):
    t = f / a.fps
    G.SIM.time = t; G.SIM.frame = f
    G.HAND.trigger = (a.trigger_at >= 0 and abs(t - a.trigger_at) < 0.5 / a.fps)
    G.SIM.strokesThisFrame = 0; p0 = G.SIM.points or 0
    if a.count:
        c0 = G.VMC.plugin; G.VMC_on(); safe(G.Main); G.VMC_off(); vm.append((t, (G.VMC.plugin - c0) * 50))
    else:
        safe(G.Main)
    perf.append((G.SIM.strokesThisFrame or 0, (G.SIM.points or 0) - p0))
    if t + 1e-9 >= next_sample:
        snap = G.SIM_SNAPSHOT()
        samples.append({"t": t, "L": [[float(x) for x in row.values()] for row in snap.values()]})
        next_sample += 1.0 / a.sample
def col(c):
    try: return [float(c.r), float(c.g), float(c.b)]
    except Exception: return None
def rot(q):
    try: return [float(q.x), float(q.y), float(q.z), float(q.w)]
    except Exception: return None
lights = {"ambient": col(G.Sketch.ambientLightColor), "main": col(G.Sketch.mainLightColor), "second": col(G.Sketch.secondaryLightColor),
          "mainRot": rot(G.Sketch.mainLightRotation), "secondRot": rot(G.Sketch.secondaryLightRotation)}
if G.End: safe(G.End)
def tolist(tbl): return [tbl[i] for i in range(1, len(tbl) + 1)]
strokes = [{"t": s.t, "layer": int(s.layer), "brush": s.brush, "size": float(s.size), "color": [float(c) for c in s.color.values()],
            "cps": [[float(v) for v in cp.values()] for cp in s.cps.values()]} for s in tolist(G.LOG.strokes)]
events = [dict(e.items()) for e in tolist(G.LOG.events)]
errors = [str(e) for e in tolist(G.LOG.errors)]
layers = {int(k): {"created": float(v.created), "deleted": (float(v.deleted) if v.deleted is not None else None),
                   "pivot": ([float(x) for x in v.pivot.values()] if v.pivot is not None else None),
                   "pivotTime": (float(v.pivotTime) if v.pivotTime is not None else None)} for k, v in G.LOG.layers.items()}
user_head = [hand[0] - direction[0] * 3.0, hand[1] + 2.0, hand[2] - direction[2] * 3.0]
out = {"lights": lights, "meta": {"fps": a.fps, "seconds": a.seconds, "scale": a.scale, "hand": hand, "direction": direction, "head": user_head},
       "strokes": strokes, "layers": layers, "samples": samples, "events": events, "errors": errors}
json.dump(out, open(a.out, "w"))
sp = [s for s, p in perf]; pp = [p for s, p in perf]
secs = {}
for i, (s, p) in enumerate(perf): secs.setdefault(int(i / a.fps), [0, 0]); secs[int(i / a.fps)][0] += s; secs[int(i / a.fps)][1] += p
print(f"strokes: {len(strokes)}  control points: {sum(len(s['cps']) for s in strokes)}  layers created: {len(layers) - 1}")
print(f"per frame: max strokes {max(sp)}, max points {max(pp)} | worst second: {max(v[0] for v in secs.values())} strokes, {max(v[1] for v in secs.values())} points")
print("live layers at end:", sum(1 for v in layers.values() if v['deleted'] is None) - 1)
for e in events[:6]: print("event:", e)
print("errors:", len(errors)); [print("  ", e) for e in sorted(set(errors))[:8]]

if a.count and vm:
    import statistics
    late = [v for (t, v) in vm if t > a.seconds * 0.5]
    print(f"plugin VM instructions per frame (2nd half): median {statistics.median(late):.0f}, max {max(late):.0f}")
