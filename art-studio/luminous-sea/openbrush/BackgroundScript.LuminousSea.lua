-- The Luminous Sea for Open Brush (Background Plugin).
-- On some nights the sea along the beaches of Muscat glows wherever the water moves: tiny plankton flash when they
-- are disturbed. Here one living mass of that light swims in front of you, room-sized and fast as a school of fish:
-- it stretches, curls, splits and comes back together, startles and regathers. Its glow is deep sea blue; every
-- wave that runs through it, every startle, every sudden turn and every pass of your hand makes it flash cyan.
--
-- Built only on what is safe in every recent Open Brush: it draws everything once (a few strokes per frame), then
-- only moves, scales, shows and hides layers. If something goes wrong, the reason is shown on the back of your
-- brush controller. If the headset stutters, set Density to 1.
--
-- How to use: Extras > Plugins and Scripts > Background: pick LuminousSea, press the eye button, then the big
-- button of the row. Point your hand forward and wait 3 seconds (or press the trigger).

Settings = {
    description = "Luminous Sea: a living mass of sea light that flashes when disturbed",
    space = "canvas"
}

Parameters = {
    size = {label = "Size", type = "float", min = 0.2, max = 2, default = 1},
    distance = {label = "Distance (m)", type = "float", min = 1, max = 8, default = 3.4},
    speed = {label = "Speed", type = "float", min = 0.3, max = 2.5, default = 1.2},
    density = {label = "Density 1 light 2 3 rich", type = "int", min = 1, max = 3, default = 2},
    lights = {label = "Set the lights 0 no 1 yes", type = "int", min = 0, max = 1, default = 0},
}

local UNITS = 10
local TAU = 2 * Math.pi

-- ---------- small math ----------
local function norm(a)
    local l = Math:Sqrt(a[1] * a[1] + a[2] * a[2] + a[3] * a[3])
    if l < 1e-9 then return {0, 0, 1} end
    return {a[1] / l, a[2] / l, a[3] / l}
end
local function cross(a, b) return {a[2] * b[3] - a[3] * b[2], a[3] * b[1] - a[1] * b[3], a[1] * b[2] - a[2] * b[1]} end
local function add(a, b) return {a[1] + b[1], a[2] + b[2], a[3] + b[3]} end
local function sub(a, b) return {a[1] - b[1], a[2] - b[2], a[3] - b[3]} end
local function mul(a, s) return {a[1] * s, a[2] * s, a[3] * s} end
local function smooth(x)
    if x < 0 then x = 0 elseif x > 1 then x = 1 end
    return x * x * (3 - 2 * x)
end
local function ramp(t, a, b) return smooth((t - a) / (b - a)) end
local function springy(x)                       -- grows with a small organic overshoot
    if x <= 0 then return 0 end
    if x >= 1 then return 1 end
    return 1 - (1 - x) ^ 3 + 0.18 * Math:Sin(Math.pi * x) * (1 - x)
end
-- quaternions {x, y, z, w}
local function qAxis(ax, deg)
    local a = norm(ax)
    local h = deg * Math.pi / 360
    local s = Math:Sin(h)
    return {a[1] * s, a[2] * s, a[3] * s, Math:Cos(h)}
end
local function qMul(a, b)
    return {a[4] * b[1] + a[1] * b[4] + a[2] * b[3] - a[3] * b[2],
            a[4] * b[2] - a[1] * b[3] + a[2] * b[4] + a[3] * b[1],
            a[4] * b[3] + a[1] * b[2] - a[2] * b[1] + a[3] * b[4],
            a[4] * b[4] - a[1] * b[1] - a[2] * b[2] - a[3] * b[3]}
end
local function qRot(q, v)
    local x, y, z, w = q[1], q[2], q[3], q[4]
    local tx, ty, tz = 2 * (y * v[3] - z * v[2]), 2 * (z * v[1] - x * v[3]), 2 * (x * v[2] - y * v[1])
    return {v[1] + w * tx + (y * tz - z * ty), v[2] + w * ty + (z * tx - x * tz), v[3] + w * tz + (x * ty - y * tx)}
end
local Q0 = {0, 0, 0, 1}

-- ---------- the work's frame: local meters (x right, y up, z toward the viewer) -> canvas ----------
local C = {0, 0, 0}
local RIGHT, UPV, FWD = {1, 0, 0}, {0, 1, 0}, {0, 0, 1}
local S_UNITS = 10
local ZOOM = 1
local function dir(v) return {v[1] * RIGHT[1] + v[2] * UPV[1] + v[3] * FWD[1], v[1] * RIGHT[2] + v[2] * UPV[2] + v[3] * FWD[2],
                              v[1] * RIGHT[3] + v[2] * UPV[3] + v[3] * FWD[3]} end
local function canvas(p) return add(C, mul(dir(p), S_UNITS)) end


-- ---------- drawing: once, a few strokes per frame ----------
local useDWB = nil
local saved = {}
local VIEWROT = nil
local stats = {strokes = 0, points = 0}
local function brushes() return "Shiny Hull", "Matte Hull" end

local function drawInto(rec, pts, brush, sizeM, color, pressures)
    local n = #pts
    if n < 2 then return end
    local list = {}
    for i = 1, n do
        local c = canvas(pts[i])
        local pr = 1
        if pressures then pr = pressures[i] end
        list[i] = Transform:New(Vector3:New(c[1], c[2], c[3]), VIEWROT, pr)
    end
    list[n + 1] = list[n]                                   -- Open Brush skips the last point of a path
    local path = Path:New(list)
    local size = sizeM * UNITS * Parameters.size / ZOOM
    local col = Color:New(color)
    if useDWB ~= false then
        local ok = pcall(function() path:DrawWithBrush(brush, size, col, 0, rec.layer) end)
        useDWB = ok
    end
    if useDWB == false then                                 -- older versions: the pointer's brush, on the active layer
        Sketch.layers.active = rec.layer
        Brush.type = brush
        if not pcall(function() Brush.sizeAbsolute = size end) then Brush.size = 0.5 end
        Brush.colorRgb = col
        path:Draw()
    end
    -- remember the content's bounds (to turn the layer around the right points later)
    for i = 1, n do
        local c = canvas(pts[i])
        local b = rec.bounds
        if not b then rec.bounds = {c[1], c[2], c[3], c[1], c[2], c[3]}
        else
            for k = 1, 3 do
                if c[k] < b[k] then b[k] = c[k] end
                if c[k] > b[k + 3] then b[k + 3] = c[k] end
            end
        end
    end
    stats.strokes = stats.strokes + 1
    stats.points = stats.points + n
end

-- ---------- the parts (each one a layer) ----------
local recs, queue = {}, {}
local function part(kind, jobsFn, extra)
    local rec = {kind = kind, jobsFn = jobsFn, ready = false}
    if extra then for k, v in pairs(extra) do rec[k] = v end end
    recs[#recs + 1] = rec
    queue[#queue + 1] = rec
    return rec
end
local function J(pts, brush, size, color, pressures) return {pts = pts, brush = brush, size = size, color = color, pr = pressures} end


-- ---------- preparation ----------
local budget = 2
local function prepare(dt)
    if dt > 1 / 45 then budget = Math:Max(1, budget - 1) elseif dt < 1 / 66 then budget = Math:Min(6, budget + 0.2) end
    local done = 0
    while #queue > 0 and done < Math:Floor(budget) do
        local rec = queue[1]
        if not rec.layer then
            rec.layer = Layer:New()
            Sketch.layers.active = saved.layer
            if rec.kind ~= "pistil" then rec.layer:Hide() end
            rec.jobs = rec.jobsFn()
            rec.j = 1
        end
        if rec.j > #rec.jobs then
            -- move the pivot to the content's center; from now on the layer only moves, turns and scales
            if rec.kind ~= "flash" then rec.layer:Show() end
            rec.layer:CenterPivot()
            rec.layer.scale = 0.002                            -- tiny until its moment comes
            rec.shown = true
            local p = rec.layer.position
            rec.base = {p.x, p.y, p.z}
            local b = rec.bounds or {0, 0, 0, 0, 0, 0}
            rec.center = {(b[1] + b[4]) / 2, (b[2] + b[5]) / 2, (b[3] + b[6]) / 2}
            rec.ready = true
            table.remove(queue, 1)
        else
            local jb = rec.jobs[rec.j]
            drawInto(rec, jb.pts, jb.brush, jb.size, jb.color, jb.pr)
            rec.j = rec.j + 1
            done = done + 1
        end
    end
    if useDWB == false then Sketch.layers.active = saved.layer end
end



-- ---------- colours: the glow of the sea at night, and the flash of the plankton ----------
local GLOW = {"#0E5470", "#126A86", "#1A7F9A", "#0D4566", "#1C88A6", "#145E86"}
local FLASH = {"#4FE6FF", "#7FF0FF", "#BFF8FF", "#E8FFFF", "#3FC8FF", "#9AF3FF"}
local function pick(t) return t[1 + Math:Floor(Random.value * #t)] end
local function rnd(a, b) return a + (b - a) * Random.value end
local function randUnit()
    local d
    repeat d = {rnd(-1, 1), rnd(-1, 1), rnd(-1, 1)} until d[1] * d[1] + d[2] * d[2] + d[3] * d[3] <= 1
    return d
end

-- an irregular pebble: noisy points around an ellipsoid; a Hull brush wraps them in a soft organic volume
local function pebble(c, r, n)
    local pts = {}
    local ax = {rnd(0.7, 1.3), rnd(0.65, 1.2), rnd(0.6, 1.15)}
    local ph = {rnd(0, TAU), rnd(0, TAU), rnd(0, TAU)}
    n = n or 26
    local ga = Math.pi * (3 - Math:Sqrt(5))
    for i = 0, n - 1 do
        local y = 1 - 2 * (i + 0.5) / n
        local rr = Math:Sqrt(1 - y * y)
        local a = ga * i
        local v = {rr * Math:Cos(a), y, rr * Math:Sin(a)}
        local bump = 1 + 0.22 * Math:Sin(3 * v[1] + ph[1]) * Math:Sin(2 * v[2] + ph[2]) + 0.12 * Math:Sin(4 * v[3] + ph[3])
        pts[#pts + 1] = add(c, {v[1] * ax[1] * r * bump, v[2] * ax[2] * r * bump, v[3] * ax[3] * r * bump})
    end
    return pts
end

-- ---------- the swarm: clouds of glowing grains; each one has a bright twin, hidden until it flashes ----------
local function buildParts()
    local d = Parameters.density
    local NCL = 18 + 12 * d                                     -- density 1 = 30 clouds, 2 = 42, 3 = 54
    for i = 1, NCL do
        local home = mul(randUnit(), 1.4)
        local R = rnd(0.22, 0.42)
        local grains = {}
        for k = 1, 10 + 4 * d do
            local big = k <= 2
            grains[k] = {c = add(home, mul(randUnit(), big and R * 0.4 or R)), r = big and rnd(0.035, 0.06) or rnd(0.012, 0.03),
                         g = pick(GLOW), f = pick(FLASH), d = norm(randUnit())}
        end
        local twin = part("flash", function()
            local j = {}
            for _, g in ipairs(grains) do j[#j + 1] = J({sub(g.c, mul(g.d, g.r)), g.c, add(g.c, mul(g.d, g.r))}, "Dots", g.r * 2.6, g.f) end
            return j
        end, {home = home})
        part("glow", function()
            local j = {}
            for _, g in ipairs(grains) do j[#j + 1] = J({sub(g.c, mul(g.d, g.r)), g.c, add(g.c, mul(g.d, g.r))}, "Dots", g.r * 2.0, g.g) end
            return j
        end, {home = home, ph = rnd(0, TAU), roll = rnd(-1, 1), core = (i <= 8) and 1.5 or 1, twin = twin})
    end
end

-- ---------- the flock: every cloud follows its neighbours and a wandering guide ----------
-- Written for speed (Open Brush runs Lua in an interpreter): plain numbers instead of vector tables, Lua's own math,
-- and each cloud looks at its neighbours only once every few frames.
local sin = (math and math.sin) or function(x) return Math:Sin(x) end
local cos = (math and math.cos) or function(x) return Math:Cos(x) end
local sqrt = (math and math.sqrt) or function(x) return Math:Sqrt(x) end
local abs = (math and math.abs) or function(x) return Math:Abs(x) end
local exp = (math and math.exp) or function(x) return Math:Exp(x) end
local acos = (math and math.acos) or function(x) return Math:Acos(x) end
local DEG = 180 / Math.pi

local function qFromTo(a, b)
    local c = cross(a, b)
    local w = 1 + a[1] * b[1] + a[2] * b[2] + a[3] * b[3]
    if w < 1e-6 then return {0, 1, 0, 0} end
    local l = Math:Sqrt(c[1] * c[1] + c[2] * c[2] + c[3] * c[3] + w * w)
    return {c[1] / l, c[2] / l, c[3] / l, w / l}
end

local NB = 0
local PX, PY, PZ, VX, VY, VZ = {}, {}, {}, {}, {}, {}
local SX, SY, SZ, AX, AY, AZ, AN = {}, {}, {}, {}, {}, {}, {}   -- what the neighbours say (refreshed in turns)
local NX, NY, NZ = {}, {}, {}                                   -- its own restless wandering (refreshed in turns)
local QX, QY, QZ, QW = {}, {}, {}, {}                           -- how each cloud is turned (work frame)
local WX, WY, WZ, WW = {}, {}, {}, {}                           -- how it wants to be turned
local BIRTH, BORN, CORE, PH, ROLL, REC = {}, {}, {}, {}, {}, {}
local TWIN, FL, ON = {}, {}, {}                                -- the bright twin, how much it flashes, is it shown
local ROT = {}                                                  -- its turn as an Open Brush rotation (kept between updates)
local SEP = 0.86
local SLICES = 10
local frameNo = 0
local flockReady = false
local fastT = nil                                               -- can a layer take its whole pose at once?
local SEED = {0, -0.1, 0.2}

local function initFlock()
    local glow = {}
    for _, r in ipairs(recs) do if r.kind == "glow" then glow[#glow + 1] = r end end
    NB = #glow
    for i = 1, NB do
        local rec = glow[i]
        TWIN[i], FL[i], ON[i] = rec.twin, 0, false
        -- every cloud is born from the same seed, one after another, and bursts out into the flock
        local o = norm(randUnit())
        local sp = rnd(0.9, 1.5)
        PX[i], PY[i], PZ[i] = SEED[1] + o[1] * 0.08, SEED[2] + o[2] * 0.08, SEED[3] + o[3] * 0.08
        VX[i], VY[i], VZ[i] = o[1] * sp, o[2] * sp, o[3] * sp
        SX[i], SY[i], SZ[i], AX[i], AY[i], AZ[i], AN[i] = 0, 0, 0, 0, 0, 0, 0
        NX[i], NY[i], NZ[i] = 0, 0, 0
        QX[i], QY[i], QZ[i], QW[i] = 0, 0, 0, 1
        WX[i], WY[i], WZ[i], WW[i] = 0, 0, 0, 1
        BIRTH[i] = 0.3 + 4.2 * ((i - 1) / NB) ^ 1.3 + rnd(0, 0.25)
        BORN[i] = false
        ROT[i] = nil
        CORE[i], PH[i], ROLL[i], REC[i] = rec.core, rec.ph, rec.roll, rec
    end
    frameNo = 0
    flockReady = true
end

local function neighbours(i, T)
    local px, py, pz = PX[i], PY[i], PZ[i]
    local sx, sy, sz, ax, ay, az, an = 0, 0, 0, 0, 0, 0, 0
    local sep, sep2 = SEP, SEP * SEP
    local r2 = sep2
    if r2 < 1 then r2 = 1 end
    for j = 1, NB do
        if j ~= i and BORN[j] then
            local dx, dy, dz = px - PX[j], py - PY[j], pz - PZ[j]
            local d2 = dx * dx + dy * dy + dz * dz
            if d2 < r2 then
                ax = ax + VX[j]; ay = ay + VY[j]; az = az + VZ[j]; an = an + 1
                if d2 < sep2 then                               -- a soft spring keeps the clouds apart
                    local dd = sqrt(d2) + 0.01
                    local k = (sep - dd) / dd
                    sx = sx + dx * k; sy = sy + dy * k; sz = sz + dz * k
                end
            end
        end
    end
    SX[i], SY[i], SZ[i], AN[i] = sx, sy, sz, an
    local ph = PH[i]
    NX[i], NY[i], NZ[i] = 0.9 * sin(1.7 * T + ph), 0.7 * sin(1.3 * T + 2 * ph), 0.9 * sin(1.5 * T + 3 * ph)
    if an > 0 then AX[i], AY[i], AZ[i] = ax / an, ay / an, az / an end
    -- each cloud turns to face where it flies, with a little roll, like a fish
    local vx, vy, vz = VX[i], VY[i], VZ[i]
    local l = sqrt(vx * vx + vy * vy + vz * vz)
    if l > 1e-6 then
        local q = qMul(qFromTo({1, 0, 0}, {vx / l, vy / l, vz / l}), qAxis({1, 0, 0}, 40 * ROLL[i] * sin(2.1 * T + PH[i])))
        WX[i], WY[i], WZ[i], WW[i] = q[1], q[2], q[3], q[4]
    end
end

local function stepFlock(T, dt)
    -- how far apart the clouds keep: the mass slowly loosens and tightens
    SEP = 0.86 + 0.2 * sin(0.13 * T + 0.4) + 0.08 * sin(0.31 * T)
    -- the invisible guide wanders around the room; now and then it becomes two, and the mass splits
    local lx = 0.6 * sin(0.63 * T) + 0.3 * sin(1.47 * T + 1)
    local ly = 0.32 * sin(0.53 * T + 2) + 0.18 * sin(1.27 * T)
    local lz = 0.38 * sin(0.43 * T + 0.5) + 0.2 * sin(1.09 * T + 2)
    local ox, oy, oz = 0, 0, 0
    local split = sin(0.071 * T + 1.2)
    if split > 0.55 then
        split = smooth((split - 0.55) / 0.3) * 1.1
        local ax, ay, az = cos(0.2 * T), 0.4 * sin(0.17 * T), sin(0.2 * T)
        local l = sqrt(ax * ax + ay * ay + az * az)
        ox, oy, oz = ax / l * split, ay / l * split, az / l * split
    end
    -- the center of the whole mass
    local cx, cy, cz, nb = 0, 0, 0, 0
    for i = 1, NB do
        if BORN[i] then cx = cx + PX[i]; cy = cy + PY[i]; cz = cz + PZ[i]; nb = nb + 1 end
    end
    if nb == 0 then return end
    cx, cy, cz = cx / nb, cy / nb, cz / nb
    frameNo = frameNo + 1
    local slice = frameNo % SLICES
    -- half of the clouds move on each frame, with a double step (the others are extrapolated, see poseCloud)
    local par = frameNo % 2
    dt = dt * 2
    local turn = dt * 4
    if turn > 1 then turn = 1 end
    for i = 1, NB do
        if BORN[i] then
            if i % SLICES == slice then neighbours(i, T) end
        end
        if BORN[i] and i % 2 == par then
            local px, py, pz, vx, vy, vz = PX[i], PY[i], PZ[i], VX[i], VY[i], VZ[i]
            local tx, ty, tz = lx + ox, ly + oy, lz + oz
            if i % 2 == 0 then tx, ty, tz = lx - ox, ly - oy, lz - oz end
            -- follow the guide and keep one mass: the big bodies hold the core, the spray drifts loose at the edges
            local c = CORE[i]
            local kl, kc = 0.4 + 0.4 * c, 0.6 * c
            local fx = (tx - px) * kl + (cx - px) * kc + SX[i] * 3 + NX[i]
            local fy = (ty - py) * kl + (cy - py) * kc + SY[i] * 3 + NY[i]
            local fz = (tz - pz) * kl + (cz - pz) * kc + SZ[i] * 3 + NZ[i]
            if AN[i] > 0 then                                   -- move like the neighbours
                fx = fx + (AX[i] - vx) * 1.1; fy = fy + (AY[i] - vy) * 1.1; fz = fz + (AZ[i] - vz) * 1.1
            end
            local r2 = px * px + py * py + pz * pz
            if r2 > 3.61 then                                   -- stay inside the room-sized volume
                local r = sqrt(r2)
                local k = -(r - 1.9) * 4 / r
                fx = fx + px * k; fy = fy + py * k; fz = fz + pz * k
            end
            vx = vx + fx * dt; vy = vy + fy * dt; vz = vz + fz * dt
            if fx * fx + fy * fy + fz * fz > 42 and FL[i] < 0.8 then FL[i] = 0.8 end      -- a sudden turn: a flash
            local s = sqrt(vx * vx + vy * vy + vz * vz)
            if s > 2.3 then local k = 2.3 / s; vx = vx * k; vy = vy * k; vz = vz * k
            elseif s < 0.45 and s > 1e-6 then local k = 0.45 / s; vx = vx * k; vy = vy * k; vz = vz * k end
            VX[i], VY[i], VZ[i] = vx, vy, vz
            PX[i], PY[i], PZ[i] = px + vx * dt, py + vy * dt, pz + vz * dt
            -- turn smoothly toward where it wants to face
            local qx, qy, qz, qw = QX[i], QY[i], QZ[i], QW[i]
            local wx, wy, wz, ww = WX[i], WY[i], WZ[i], WW[i]
            if qx * wx + qy * wy + qz * wz + qw * ww < 0 then wx, wy, wz, ww = -wx, -wy, -wz, -ww end
            qx = qx + (wx - qx) * turn; qy = qy + (wy - qy) * turn; qz = qz + (wz - qz) * turn; qw = qw + (ww - qw) * turn
            local l = sqrt(qx * qx + qy * qy + qz * qz + qw * qw)
            QX[i], QY[i], QZ[i], QW[i] = qx / l, qy / l, qz / l, qw / l
            ROT[i] = nil
        end
    end
end

-- put a cloud's layer where the flock says: its content center at the cloud's place, turned and scaled around it
local function poseCloud(i, s, ahead)
    local rec = REC[i]
    local L = rec.layer
    local px, py, pz = PX[i] + VX[i] * ahead, PY[i] + VY[i] * ahead, PZ[i] + VZ[i] * ahead
    local k = S_UNITS
    local x = C[1] + (RIGHT[1] * px + UPV[1] * py + FWD[1] * pz) * k
    local y = C[2] + (RIGHT[2] * px + UPV[2] * py + FWD[2] * pz) * k
    local z = C[3] + (RIGHT[3] * px + UPV[3] * py + FWD[3] * pz) * k
    local b, c = rec.base, rec.center
    local pos = Vector3:New(b[1] + x - c[1], b[2] + y - c[2], b[3] + z - c[3])
    -- the turn, from the work's frame to the canvas (only when it changed)
    local rot = ROT[i]
    if not rot then
        local qx, qy, qz, qw = QX[i], QY[i], QZ[i], QW[i]
        if qw < 0 then qx, qy, qz, qw = -qx, -qy, -qz, -qw end
        if qw > 1 then qw = 1 end
        local half = acos(qw)
        local sn = sin(half)
        if sn < 1e-5 then rot = Rotation:AngleAxis(0, Vector3:New(0, 1, 0))
        else
            local ax = (RIGHT[1] * qx + UPV[1] * qy + FWD[1] * qz) / sn
            local ay = (RIGHT[2] * qx + UPV[2] * qy + FWD[2] * qz) / sn
            local az = (RIGHT[3] * qx + UPV[3] * qy + FWD[3] * qz) / sn
            rot = Rotation:AngleAxis(2 * half * DEG, Vector3:New(ax, ay, az))
        end
        ROT[i] = rot
    end
    if s < 0.002 then s = 0.002 end
    local tw = TWIN[i]
    local twPos = nil
    if ON[i] and tw and tw.ready then
        local tb, tc = tw.base, tw.center
        twPos = Vector3:New(tb[1] + x - tc[1], tb[2] + y - tc[2], tb[3] + z - tc[3])
    end
    local ts = s * (1.05 + 0.25 * FL[i])
    if fastT == nil then                                        -- the first time, check the one-call way works
        fastT = pcall(function() L.transform = Transform:New(pos, rot, s) end)
        if fastT then
            if twPos then tw.layer.transform = Transform:New(twPos, rot, ts) end
            return
        end
    end
    if fastT then
        L.transform = Transform:New(pos, rot, s)
        if twPos then tw.layer.transform = Transform:New(twPos, rot, ts) end
    else
        L.position = pos; L.rotation = rot; L.scale = s
        if twPos then tw.layer.position = twPos; tw.layer.rotation = rot; tw.layer.scale = ts end
    end
end

local waves, nextWave, nextStartle = {}, 1.5, 6
local function handLocal()
    local ok, p = pcall(function() return Brush.position end)
    if not ok or not p then return nil end
    local w = {(p.x - C[1]) / S_UNITS, (p.y - C[2]) / S_UNITS, (p.z - C[3]) / S_UNITS}
    return {w[1] * RIGHT[1] + w[2] * RIGHT[2] + w[3] * RIGHT[3], w[1] * UPV[1] + w[2] * UPV[2] + w[3] * UPV[3],
            w[1] * FWD[1] + w[2] * FWD[2] + w[3] * FWD[3]}
end
local function lightUp(T, dt)
    -- a wave of light runs through the mass from somewhere on its edge
    if T > nextWave then
        local cx, cy, cz, nb = 0, 0, 0, 0
        for i = 1, NB do if BORN[i] then cx = cx + PX[i]; cy = cy + PY[i]; cz = cz + PZ[i]; nb = nb + 1 end end
        if nb > 0 then
            local o = norm(randUnit())
            waves[#waves + 1] = {x = cx / nb + o[1] * 1.2, y = cy / nb + o[2] * 1.2, z = cz / nb + o[3] * 1.2, t0 = T}
        end
        nextWave = T + 0.9 + 1.2 * Random.value
    end
    -- now and then the school startles: it darts apart in a flash, then regathers
    local st = nil
    if T > nextStartle and NB > 0 then
        local k = 1 + Math:Floor(Random.value * NB)
        if k > NB then k = NB end
        st = {PX[k], PY[k], PZ[k]}
        nextStartle = T + 6 + 7 * Random.value
    end
    local hand = handLocal()
    local decay = exp(-dt * 3.4)
    for i = 1, NB do
        local f = FL[i] * decay
        local px, py, pz = PX[i], PY[i], PZ[i]
        for _, w in ipairs(waves) do
            local r = (T - w.t0) * 3.2
            local dx, dy, dz = px - w.x, py - w.y, pz - w.z
            if abs(sqrt(dx * dx + dy * dy + dz * dz) - r) < 0.35 then f = 1 end
        end
        if st and BORN[i] then
            local dx, dy, dz = px - st[1], py - st[2], pz - st[3]
            local d = sqrt(dx * dx + dy * dy + dz * dz) + 1e-3
            if d < 1.6 then
                f = 1
                local k = 3.2 * (1.6 - d) / d
                VX[i] = VX[i] + dx * k; VY[i] = VY[i] + dy * k; VZ[i] = VZ[i] + dz * k
            end
        end
        if hand and BORN[i] then
            local dx, dy, dz = px - hand[1], py - hand[2], pz - hand[3]
            local d = sqrt(dx * dx + dy * dy + dz * dz) + 1e-3
            if d < 0.7 then
                f = 1
                local k = 25 * (0.7 - d) / d * dt
                VX[i] = VX[i] + (dx - dz) * k; VY[i] = VY[i] + dy * k; VZ[i] = VZ[i] + (dz + dx) * k
            end
        end
        if not BORN[i] then f = 0 end
        FL[i] = f
        local tw = TWIN[i]
        if tw and tw.ready then
            if not ON[i] and f > 0.22 then ON[i] = true; tw.layer:Show()
            elseif ON[i] and f < 0.12 then ON[i] = false; tw.layer:Hide() end
        end
    end
    local keep = {}
    for _, w in ipairs(waves) do if T - w.t0 < 1.4 then keep[#keep + 1] = w end end
    waves = keep
end
local function animate(T, dt)
    if not flockReady then initFlock() end
    if dt > 0.05 then dt = 0.05 end
    for i = 1, NB do if not BORN[i] and T >= BIRTH[i] then BORN[i] = true end end
    stepFlock(T, dt)
    lightUp(T, dt)
    local par = frameNo % 2
    for i = 1, NB do
        if BORN[i] then
            local g = T - BIRTH[i]
            if g < 1.4 then g = springy(g / 1.4) else g = 1 end
            poseCloud(i, g * (0.86 + 0.16 * sin(1.9 * T + PH[i])), (i % 2 == par) and 0 or dt)
        end
    end
end

-- ---------- the plugin ----------
local placed, startTime, lastTime, clockT = false, 0, 0, 0
local reported = false
local announcedReady = false

local function setLights(on)
    if Parameters.lights ~= 1 then return end
    pcall(function()
        if on then
            saved.lights = {Sketch.ambientLightColor, Sketch.mainLightColor, Sketch.secondaryLightColor,
                            Sketch.mainLightRotation, Sketch.secondaryLightRotation}
            Sketch.ambientLightColor = Color:New(0.42, 0.38, 0.48)
            Sketch.mainLightColor = Color:New(1.0, 0.94, 0.88)
            Sketch.secondaryLightColor = Color:New(0.45, 0.4, 0.75)
            local d1 = norm({-FWD[1] * 1, -0.7, -FWD[3] * 1})
            Sketch.mainLightRotation = Rotation:LookRotation(Vector3:New(d1[1], d1[2], d1[3]), Vector3:New(0, 1, 0))
            local d2 = norm({FWD[1] + RIGHT[1] * 0.6, 0.3, FWD[3] + RIGHT[3] * 0.6})
            Sketch.secondaryLightRotation = Rotation:LookRotation(Vector3:New(d2[1], d2[2], d2[3]), Vector3:New(0, 1, 0))
        elseif saved.lights then
            local l = saved.lights
            Sketch.ambientLightColor = l[1]; Sketch.mainLightColor = l[2]; Sketch.secondaryLightColor = l[3]
            Sketch.mainLightRotation = l[4]; Sketch.secondaryLightRotation = l[5]
        end
    end)
end

local function place()
    local p = Brush.position
    local d = Brush.direction
    FWD = norm({-d.x, 0, -d.z})
    UPV = {0, 1, 0}
    RIGHT = norm(cross(UPV, FWD))
    ZOOM = App.currentScale
    if ZOOM == nil or ZOOM < 0.01 then ZOOM = 1 end
    S_UNITS = UNITS / ZOOM * Parameters.size
    local dist = Parameters.distance * UNITS / ZOOM
    C = {p.x - FWD[1] * dist, p.y + 0.1 * UNITS / ZOOM, p.z - FWD[3] * dist}
    local sz = 0.1
    pcall(function() sz = Brush.sizeAbsolute end)
    saved.layer = Sketch.layers.active
    saved.type, saved.size, saved.color = Brush.type, sz, Brush.colorRgb
    VIEWROT = Rotation:LookRotation(Vector3:New(-FWD[1], -FWD[2], -FWD[3]), Vector3:New(0, 1, 0))
    setLights(true)
    buildParts()
    placed = true
    App:Error("Luminous Sea: growing...")
end

local function step()
    local now = App.time
    local dt = now - lastTime
    lastTime = now
    if not placed then
        if Brush.triggerPressedThisFrame or (now - startTime > 3) then place() end
        return
    end
    if #queue > 0 then prepare(dt) end
    -- the clock only starts once everything is drawn (a few seconds the first time)
    if #queue == 0 then
        if not announcedReady then
            announcedReady = true
            App:Error("Luminous Sea: alive (" .. #recs .. " layers, " .. stats.strokes .. " strokes)")
            if useDWB == false and saved.type then
                Brush.type = saved.type
                pcall(function() Brush.sizeAbsolute = saved.size end)
                Brush.colorRgb = saved.color
            end
        end
        local d = dt
        if d > 0.1 then d = 0.1 end
        clockT = clockT + d * Parameters.speed
        animate(clockT, d * Parameters.speed)
    end
end

function Start()
    placed, reported, announcedReady = false, false, false
    recs, queue = {}, {}
    flockReady = false
    waves, nextWave, nextStartle = {}, 1.5, 6
    stats = {strokes = 0, points = 0}
    startTime = App.time
    lastTime = App.time
    clockT = 0
    App:Error("Luminous Sea: on. Point forward and wait 3 seconds")
end

function Main()
    local ok, err = pcall(step)
    if not ok and not reported then
        reported = true
        App:Error("Luminous Sea error: " .. tostring(err))
    end
end

function End()
    for _, rec in ipairs(recs) do
        if rec.layer then pcall(function() rec.layer:Delete() end) end
    end
    recs, queue = {}, {}
    pcall(function() Sketch.layers.active = Sketch.layers.main end)
    setLights(false)
    placed = false
end

