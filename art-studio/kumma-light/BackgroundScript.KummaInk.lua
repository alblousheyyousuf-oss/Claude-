-- Kumma Ink for Open Brush (Background Plugin) - live pen version.
-- An invisible pen draws the Omani kumma's symbols in the air in front of you, live, a few points per frame:
-- the outline, then a back-and-forth scribble fill like the original pen drawing. Each symbol breathes and
-- turns, then is swallowed by a small core of ink and disappears, and the pen draws the next one. Ink
-- tendrils are drawn, drift and are swallowed around it. At the end the core bursts into a splash of
-- droplets and the cycle starts again (about 70 seconds).
--
-- How to use: Extras > Plugins and Scripts > Background: pick KummaInk, press the eye button, then the
-- big button of the row. Point your hand forward and press the trigger, or wait 3 seconds.
-- It draws very little per frame, and the pen slows down by itself if the headset is busy.
-- Turning it off removes its layers.

Settings = {
    description = "Kumma Ink: a live pen draws the Omani kumma's symbols in the air",
    space = "canvas"
}

Parameters = {
    size = {label = "Size", type = "float", min = 0.2, max = 2, default = 0.55},
    speed = {label = "Speed", type = "float", min = 0.3, max = 2, default = 1},
    thickness = {label = "Thickness", type = "float", min = 0.2, max = 4, default = 1},
    density = {label = "Density", type = "int", min = 1, max = 3, default = 2},
}

local LOOP = 70
local UNITS = 10                -- 1 meter = 10 units in Open Brush
local TAU = 2 * Math.pi

-- ---------- state ----------
local placed = false
local C = {0, 0, 0}
local RIGHT, UPV, FWD = {1, 0, 0}, {0, 1, 0}, {0, 0, 1}
local S_UNITS = 10
local clock0, startTime, lastTime = 0, 0, 0
local saved = {}

-- ---------- helpers ----------
local function norm(a)
    local l = Math:Sqrt(a[1] * a[1] + a[2] * a[2] + a[3] * a[3])
    if l < 1e-6 then return {0, 0, 1} end
    return {a[1] / l, a[2] / l, a[3] / l}
end
local function cross(a, b) return {a[2] * b[3] - a[3] * b[2], a[3] * b[1] - a[1] * b[3], a[1] * b[2] - a[2] * b[1]} end

local function world(p)
    local s = S_UNITS * Parameters.size
    return Vector3:New(
        C[1] + (p[1] * RIGHT[1] + p[2] * UPV[1] + p[3] * FWD[1]) * s,
        C[2] + (p[1] * RIGHT[2] + p[2] * UPV[2] + p[3] * FWD[2]) * s,
        C[3] + (p[1] * RIGHT[3] + p[2] * UPV[3] + p[3] * FWD[3]) * s)
end

local function smooth(x)
    if x < 0 then x = 0 elseif x > 1 then x = 1 end
    return x * x * x * (x * (x * 6 - 15) + 10)
end
local function env(t, a, b, c, d)
    if t < a or t > d then return 0 end
    if t < b then return smooth((t - a) / (b - a)) end
    if t < c then return 1 end
    return 1 - smooth((t - c) / (d - c))
end
local function bump(t, c, w)
    local x = 1 - Math:Abs(t - c) / w
    if x < 0 then return 0 end
    return x * x
end

-- ---------- the colors of the drawing (a little brighter, so they read on dark and light backgrounds) ----------
local COL = {
    navy = "#5251C8", blue = "#4D8EF0", sky = "#8FD0F7", red = "#D0405F", magenta = "#E0359A",
    pink = "#F07CC4", purple = "#8A4BE0", green = "#4DC75E", lime = "#9BE060", ink = "#3A1A66",
}

-- ---------- brushes (with a safe fallback if a name is missing in this version) ----------
local brushOK = {}
local function setBrush(name, fallback)
    if brushOK[name] == nil then
        pcall(function() Brush.type = fallback end)
        local before = Brush.type
        local ok = pcall(function() Brush.type = name end)
        brushOK[name] = ok and (Brush.type ~= before)
    end
    if brushOK[name] then Brush.type = name else Brush.type = fallback end
end

local function densify(pts, closed, step)
    local out = {}
    local n = #pts
    local m = closed and n or n - 1
    for i = 1, m do
        local a, b = pts[i], pts[(i % n) + 1]
        local dx, dy, dz = b[1] - a[1], b[2] - a[2], (b[3] or 0) - (a[3] or 0)
        local L = Math:Sqrt(dx * dx + dy * dy + dz * dz)
        local k = Math:Max(1, Math:Ceil(L / step))
        for j = 0, k - 1 do
            out[#out + 1] = {a[1] + dx * j / k, a[2] + dy * j / k, (a[3] or 0) + dz * j / k}
        end
    end
    local last = closed and pts[1] or pts[n]
    out[#out + 1] = {last[1], last[2], last[3] or 0}
    return out
end

-- the wobble of a hand: slow and small, never mechanical
local function wobble(pts, amp)
    local out = {}
    local f1, f2 = 0.12 + 0.1 * Random.value, 0.45 + 0.3 * Random.value
    local p1, p2, p3 = Random.value * TAU, Random.value * TAU, Random.value * TAU
    for i = 1, #pts do
        local p = pts[i]
        out[i] = {p[1] + amp * (Math:Sin(i * f1 + p1) + 0.35 * Math:Sin(i * f2 + p2)),
                  p[2] + amp * (Math:Cos(i * f1 + p2) + 0.35 * Math:Sin(i * f2 + p3)),
                  p[3] + amp * 0.5 * Math:Sin(i * f1 + p3)}
    end
    return out
end

-- a closed outline drawn by hand: it starts anywhere and overlaps its end a little
local function handLoop(d)
    local n = #d - 1
    if n < 3 then return d end
    local s = Math:Floor(Random.value * n)
    local extra = Math:Round(n * 0.07) + 2
    local out = {}
    for k = 0, n + extra do out[#out + 1] = d[((s + k) % n) + 1] end
    return out
end

-- a scribble that fills a convex 2D shape, back and forth like a pen (one continuous stroke)
local function scribble(poly, spacing, angle)
    local ca, sa = Math:Cos(angle), Math:Sin(angle)
    local q, ymin, ymax = {}, 1e9, -1e9
    for i = 1, #poly do
        local x, y = poly[i][1], poly[i][2]
        local ry = -x * sa + y * ca
        q[i] = {x * ca + y * sa, ry}
        if ry < ymin then ymin = ry end
        if ry > ymax then ymax = ry end
    end
    local out, dir = {}, 1
    local y = ymin + spacing * (0.3 + 0.4 * Random.value)
    while y < ymax do
        local x0, x1 = 1e9, -1e9
        for i = 1, #q do
            local a, b = q[i], q[(i % #q) + 1]
            if (a[2] <= y and b[2] > y) or (b[2] <= y and a[2] > y) then
                local x = a[1] + (y - a[2]) * (b[1] - a[1]) / (b[2] - a[2])
                if x < x0 then x0 = x end
                if x > x1 then x1 = x end
            end
        end
        local inset = spacing * 0.35
        if x1 - x0 > 2 * inset then
            local yy = y + spacing * 0.3 * (Random.value - 0.5)
            if dir > 0 then
                out[#out + 1] = {x0 + inset, yy}; out[#out + 1] = {x1 - inset, yy + spacing * 0.35}
            else
                out[#out + 1] = {x1 - inset, yy}; out[#out + 1] = {x0 + inset, yy + spacing * 0.35}
            end
            dir = -dir
        end
        y = y + spacing * (0.8 + 0.4 * Random.value)
    end
    local res = {}
    for i = 1, #out do
        local x, yv = out[i][1], out[i][2]
        res[i] = {x * ca - yv * sa, x * sa + yv * ca, 0}
    end
    return res
end

-- ---------- shapes: a 2D outline + where it lives in 3D ----------
local function planar(dx, dy, dz, ry)
    local c, s = Math:Cos(ry or 0), Math:Sin(ry or 0)
    return function(p) return {p[1] * c + dx, p[2] + dy, -p[1] * s + dz} end
end
local function ringMap(R)              -- (arc length, height) on a cylinder of radius R
    return function(p) local a = p[1] / R; return {R * Math:Sin(a), p[2], R * Math:Cos(a)} end
end
local function tangentMap(R, a, y0)    -- a small plane touching the cylinder at angle a
    local c, s = Math:Cos(a), Math:Sin(a)
    return function(p) return {R * s + p[1] * c, y0 + p[2], R * c - p[1] * s} end
end
local IDENT = planar(0, 0, 0, 0)

local function circle(r, n, cx, cy)
    local t = {}
    for i = 0, n - 1 do
        local a = TAU * i / n
        t[#t + 1] = {(cx or 0) + r * Math:Cos(a), (cy or 0) + r * Math:Sin(a)}
    end
    return t
end
local function khatam(R, cx, cy)       -- eight-pointed star (two squares): 16 points
    local r = R * Math:Cos(Math.pi / 4) / Math:Cos(Math.pi / 8)
    local t = {}
    for i = 0, 15 do
        local a = i * Math.pi / 8 + Math.pi / 2
        local rr = (i % 2 == 1) and r or R
        t[#t + 1] = {(cx or 0) + rr * Math:Cos(a), (cy or 0) + rr * Math:Sin(a)}
    end
    return t
end
local function lens(a, r0, r1, w, n)
    local t = {}
    n = n or 14
    for _, s in ipairs({1, -1}) do
        for i = 0, n do
            local u = (s > 0) and (i / n) or (1 - i / n)
            local d = r0 + (r1 - r0) * u
            local o = s * w * Math:Sin(Math.pi * u)
            t[#t + 1] = {d * Math:Cos(a) - o * Math:Sin(a), d * Math:Sin(a) + o * Math:Cos(a)}
        end
    end
    return t
end
local function rhombus(w, h, cx, cy)
    return {{cx, cy + h}, {cx + w, cy}, {cx, cy - h}, {cx - w, cy}}
end

-- shape list helpers
local function S(list, poly, col, map, outline, fill, spacing)
    list[#list + 1] = {poly = poly, col = col, map = map or IDENT, outline = outline ~= false,
                       fill = fill, spacing = spacing or 0.02}
end
local function khatamTips(list, R, col, map, cx, cy)   -- the 8 points of the star, each filled
    local k = khatam(R, cx, cy)
    for i = 1, 16, 2 do
        local prev, nxt = k[((i - 2) % 16) + 1], k[(i % 16) + 1]
        S(list, {prev, k[i], nxt}, col, map, false, true, 0.016)
    end
end

-- ---------- the symbols ----------
local function symStar()
    local L = {}
    S(L, khatam(0.95), COL.magenta)
    khatamTips(L, 0.95, COL.magenta)
    S(L, khatam(0.8), COL.purple)
    local oct = {}
    for i = 0, 7 do
        local a = i * TAU / 8 + Math.pi / 8
        oct[#oct + 1] = {0.47 * Math:Cos(a), 0.47 * Math:Sin(a)}
    end
    S(L, oct, COL.purple, nil, true, true, 0.024)
    S(L, circle(0.24, 36), COL.blue, nil, true, true, 0.018)
    S(L, circle(0.07, 16), COL.navy, nil, true, true, 0.012)
    for k = 0, 3 do
        local a = Math.pi / 4 + k * Math.pi / 2
        local cx, cy = 1.38 * Math:Cos(a), 1.38 * Math:Sin(a)
        S(L, rhombus(0.11, 0.17, cx, cy), COL.green, nil, true, true, 0.016)
        S(L, rhombus(0.05, 0.08, cx, cy), COL.lime, nil, true, true, 0.012)
    end
    return L
end

local function medallion(L, R, map)
    S(L, circle(R, 64), COL.green, map)
    S(L, circle(R * 0.88, 64), COL.lime, map)
    for k = 0, 7 do
        S(L, lens(k * TAU / 8 + Math.pi / 2, R * 0.14, R * 0.74, R * 0.13), (k % 2 == 0) and COL.purple or COL.magenta,
          map, true, true, 0.016)
    end
    S(L, khatam(R * 0.3), COL.blue, map)
    S(L, circle(R * 0.08, 16), COL.pink, map, true, true, 0.01)
end
local function symMedallions()
    local L = {}
    medallion(L, 0.44, planar(-0.78, -0.32, 0.25, 0.5))
    medallion(L, 0.44, planar(0.78, -0.32, 0.25, -0.5))
    medallion(L, 0.44, planar(0, 0.6, -0.1, 0))
    return L
end

local function symBands()
    local L = {}
    local R, n = 1.05, 20
    local map = ringMap(R)
    for k = 0, n - 1 do
        local s0, s1 = R * k * TAU / n, R * (k + 1) * TAU / n
        S(L, {{s0, -0.16}, {(s0 + s1) / 2, 0.14}, {s1, -0.16}}, (k % 2 == 0) and COL.purple or COL.red, map, true, true, 0.018)
    end
    for _, y in ipairs({0.33, -0.33}) do
        for k = 0, 31 do
            local a = k * TAU / 32
            S(L, circle(0.045, 14), (k % 2 == 0) and COL.pink or COL.sky, tangentMap(R, a, y), true, true, 0.011)
        end
    end
    return L
end

local function symVine()
    local L = {}
    local R, y0, y1, turns = 0.72, -0.95, 0.95, 2.5
    local pts = {}
    for i = 0, 300 do
        local u = i / 300
        local a = TAU * turns * u
        local w = 0.09 * Math:Sin(a * 6)
        pts[#pts + 1] = {(R + w) * Math:Sin(a), y0 + (y1 - y0) * u, (R + w) * Math:Cos(a)}
    end
    L[#L + 1] = {path3 = pts, col = COL.green}
    local m = Math:Round(turns * 12)
    for j = 0, m - 1 do
        local u = (j + 0.25) / m
        local a = TAU * turns * u
        local y = y0 + (y1 - y0) * u
        local rr = R + ((j % 2 == 1) and -0.13 or 0.13)
        for _, off in ipairs({{-0.035, 0}, {0.035, 0}, {0, 0.055}}) do
            S(L, circle(0.03, 12, off[1], off[2]), (j % 3 == 0) and COL.pink or COL.magenta, tangentMap(rr, a, y),
              true, true, 0.009)
        end
    end
    return L
end

local function symFlower()
    local L = {}
    local R = 1.0
    S(L, circle(R * 1.04, 128), COL.purple)
    for k = 0, 7 do
        local a = k * TAU / 8 + Math.pi / 2
        S(L, lens(a, R * 0.14, R * 0.98, R * 0.17, 20), COL.magenta, nil, true, true, 0.02)
        S(L, lens(a, R * 0.24, R * 0.78, R * 0.06, 16), COL.pink)
        S(L, lens(a + Math.pi / 8, R * 0.18, R * 0.66, R * 0.07, 16), COL.green, nil, true, true, 0.016)
    end
    S(L, circle(R * 0.13, 32), COL.lime, nil, true, true, 0.014)
    for k = 0, 7 do
        local a = k * TAU / 8 + Math.pi / 8
        local cx, cy = 1.5 * Math:Cos(a), 1.5 * Math:Sin(a)
        local col = (k % 2 == 0) and COL.blue or COL.sky
        S(L, khatam(0.16, cx, cy), col)
        khatamTips(L, 0.16, col, nil, cx, cy)
        S(L, circle(0.05, 12, cx, cy), COL.navy, nil, true, true, 0.01)
    end
    return L
end

local function flow(p)
    local k = 2.2
    local x, y, z = p[1] * k, p[2] * k, p[3] * k
    local vx = Math:Sin(z) + 0.6 * Math:Cos(y)
    local vy = 0.75 * Math:Sin(x) + Math:Cos(z)
    local vz = 0.6 * Math:Sin(y) + 0.75 * Math:Cos(x)
    return norm({vx - 0.7 * p[3], vy * 0.6, vz + 0.7 * p[1]})
end
-- an ink tendril: it follows the stream, then its curvature grows so it ends in a curl (like ink in water)
local function tendril(seed, steps, h)
    local pts = {seed}
    local p = seed
    local dir = flow(p)
    local ax = norm({Random.value * 2 - 1, 1.5 * (Random.value * 2 - 1), Random.value * 2 - 1})
    local k0, k1 = 0.02 + 0.04 * Random.value, 0.22 + 0.28 * Random.value
    local sgn = (Random.value < 0.5) and -1 or 1
    for i = 1, steps do
        local u = i / steps
        local ang = sgn * (k0 + k1 * u * u)
        local c, s = Math:Cos(ang), Math:Sin(ang)
        local kx = cross(ax, dir)
        local kd = ax[1] * dir[1] + ax[2] * dir[2] + ax[3] * dir[3]
        dir = norm({dir[1] * c + kx[1] * s + ax[1] * kd * (1 - c), dir[2] * c + kx[2] * s + ax[2] * kd * (1 - c),
                    dir[3] * c + kx[3] * s + ax[3] * kd * (1 - c)})
        local f = flow(p)
        dir = norm({dir[1] * 0.85 + f[1] * 0.15, dir[2] * 0.85 + f[2] * 0.15, dir[3] * 0.85 + f[3] * 0.15})
        p = {p[1] + dir[1] * h, p[2] + dir[2] * h, p[3] + dir[3] * h}
        if p[1] * p[1] + p[2] * p[2] + p[3] * p[3] > 1.7 * 1.7 then break end
        pts[#pts + 1] = p
    end
    return pts
end


local STRAND = {COL.magenta, COL.purple, COL.blue, COL.pink, COL.navy, COL.sky, COL.purple, COL.magenta}

-- ---------- rotations (quaternions) so each layer turns around its own center ----------
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

-- show a layer's content (drawn around canvas point P) turned by q, scaled by s, with its center at target
local function applyPose(L, q, s, P, target)
    local rp = qRot(q, P)
    L.position = Vector3:New(target[1] - s * rp[1], target[2] - s * rp[2], target[3] - s * rp[3])
    local w = q[4]
    if w < 0 then q = {-q[1], -q[2], -q[3], -w}; w = -w end
    if w > 1 then w = 1 end
    local half = Math:Acos(w)
    local sn = Math:Sin(half)
    if sn < 1e-5 then
        L.rotation = Rotation:AngleAxis(0, Vector3:New(0, 1, 0))
    else
        L.rotation = Rotation:AngleAxis(2 * half * 180 / Math.pi, Vector3:New(q[1] / sn, q[2] / sn, q[3] / sn))
    end
    L.scale = s
end

-- ---------- the pen: strokes are drawn a few points at a time ----------
local budget = 24               -- points per frame (adapts to how busy the headset is)
local CHUNK = 14                -- points per drawn piece (pieces share an end point, so the line is continuous)
local drawEvery, frameNo = 1, 0 -- if the headset is struggling, the pen only draws every few frames
local pens = {}
local drewThisFrame = false

local function job(pts, brush, fallback, size, color, whole)
    return {pts = pts, i = 1, brush = brush, fallback = fallback, size = size, color = color, whole = whole}
end

local function drawPiece(j, n)
    local last = j.i + n
    if last > #j.pts then last = #j.pts end
    local list = {}
    for k = j.i, last do list[#list + 1] = world(j.pts[k]) end
    if #list >= 2 then
        setBrush(j.brush, j.fallback)
        Brush.size = j.size * Parameters.thickness
        Brush.colorRgb = Color:New(j.color)
        local path = Path:New(list)
        path:Draw()
        drewThisFrame = true
    end
    local used = last - j.i + 1
    j.i = last
    return used
end

local function newPen(rec, jobs, duration)
    local total = 0
    for _, j in ipairs(jobs) do total = total + #j.pts end
    local pen = {rec = rec, jobs = jobs, k = 1, rate = total / (duration * 0.8), credit = 0}   -- finishes with time to spare
    pens[#pens + 1] = pen
    rec.pen = pen
end

local function runPens(dt)
    local spent = 0
    for _, pen in ipairs(pens) do
        if pen.k <= #pen.jobs and spent < budget then
            pen.credit = pen.credit + pen.rate * dt
            local cap = budget
            if cap < CHUNK + 2 then cap = CHUNK + 2 end
            if pen.credit > cap then pen.credit = cap end
            local switched = false
            while pen.k <= #pen.jobs and spent < budget do
                local j = pen.jobs[pen.k]
                local left = #j.pts - j.i + 1
                local need = CHUNK
                if j.whole or left < need then need = left end
                if pen.credit < need then break end    -- wait until a whole piece is ready
                if not switched then Sketch.layers.active = pen.rec.layer; switched = true end
                local n = need - 1
                if j.whole then n = #j.pts end
                local used = drawPiece(j, n)
                if used < 1 then used = 1 end
                pen.credit = pen.credit - used
                spent = spent + used
                if j.i >= #j.pts then pen.k = pen.k + 1 end
            end
        end
    end
    local keep = {}
    for _, pen in ipairs(pens) do
        if pen.k <= #pen.jobs and not pen.cancelled then keep[#keep + 1] = pen end
    end
    pens = keep
end

-- ---------- what the pen draws ----------
local function tilted(pts, tilt)
    if not tilt then return pts end
    local q = qAxis({1, 0, 0}, tilt)
    local out = {}
    for i = 1, #pts do out[i] = qRot(q, pts[i]) end
    return out
end

local function symbolJobs(shapes, tilt)
    local jobs = {}
    for _, sh in ipairs(shapes) do                       -- the outlines first
        local d
        if sh.path3 then
            d = densify(sh.path3, false, 0.035)
        elseif sh.outline then
            local flat = densify(sh.poly, true, 0.03)
            d = {}
            for i = 1, #flat do d[i] = sh.map(flat[i]) end
            d = handLoop(d)
        end
        if d then jobs[#jobs + 1] = job(tilted(wobble(d, 0.004), tilt), "Marker", "Marker", 0.06, sh.col) end
    end
    for _, sh in ipairs(shapes) do                       -- then the scribble fills
        if sh.fill then
            local sp = sh.spacing * (2.4 - 0.6 * Parameters.density)
            local z = densify(scribble(sh.poly, sp, Random.value * Math.pi), false, 0.06)
            local out = {}
            for i = 1, #z do out[i] = sh.map(z[i]) end
            jobs[#jobs + 1] = job(tilted(wobble(out, 0.002), tilt), "Marker", "Marker", 0.028, sh.col)
        end
    end
    return jobs
end

local function strandJobs(center)
    local jobs = {}
    for i = 1, 2 + Parameters.density do
        local s = {center[1] + 0.15 * (Random.value * 2 - 1), center[2] + 0.12 * (Random.value * 2 - 1),
                   center[3] + 0.15 * (Random.value * 2 - 1)}
        local pts = tendril(s, 30 + Math:Round(18 * Random.value), 0.028)
        jobs[#jobs + 1] = job(wobble(pts, 0.004), "Marker", "Marker", 0.026 + 0.012 * Random.value,
                              STRAND[1 + Math:Floor(Random.value * #STRAND)])
    end
    local d = {center[1] + 0.2 * (Random.value * 2 - 1), center[2], center[3] + 0.2 * (Random.value * 2 - 1)}
    jobs[#jobs + 1] = job({d, {d[1] + 0.05, d[2] + 0.02, d[3]}, {d[1] + 0.1, d[2] + 0.01, d[3] + 0.03}},
                          "Dot Marker", "Stars", 0.03, COL.ink, true)
    return jobs
end

local function coreJobs()
    local jobs = {}
    for i = 1, 6 do                                      -- a small tight knot of scribbles
        local pts = {}
        local ph = Random.value * TAU
        for j = 0, 36 do
            local a = ph + j * 0.55
            local r = 0.025 + 0.04 * Random.value
            pts[#pts + 1] = {r * Math:Cos(a), r * Math:Sin(a) * 0.8, 0.035 * Math:Sin(a * 0.7)}
        end
        jobs[#jobs + 1] = job(pts, "Marker", "Marker", 0.03, (i % 2 == 0) and COL.magenta or COL.navy)
    end
    return jobs
end

local function splashJobs()
    local jobs = {}
    for i = 1, 30 + 6 * Parameters.density do           -- droplets thrown outward along curved rays
        local d = norm({Random.value * 2 - 1, (Random.value * 2 - 1) * 0.7, Random.value * 2 - 1})
        local r0 = 0.12 + 0.25 * Random.value
        local pts = {}
        for j = 0, 4 do
            local r = r0 + j * 0.05
            pts[#pts + 1] = {d[1] * r + 0.025 * j * d[3], d[2] * r, d[3] * r - 0.025 * j * d[1]}
        end
        jobs[#jobs + 1] = job(pts, "Dot Marker", "Stars", 0.035,
                              (i % 3 == 0) and COL.ink or STRAND[1 + (i % #STRAND)], true)
    end
    return jobs
end

-- ---------- the timeline (seconds in a 70-second loop) ----------
local ACTS = {
    {fn = symStar, t0 = 2.5, draw = 5.5, hold = 2.5, absorb = 2.0, axis = "fwd", spin = 6},
    {fn = symMedallions, t0 = 12.0, draw = 6.0, hold = 2.5, absorb = 2.0, axis = "up", spin = 12},
    {fn = symBands, t0 = 22.5, draw = 6.0, hold = 2.5, absorb = 2.0, axis = "up", spin = 15, tilt = 22},
    {fn = symVine, t0 = 33.0, draw = 6.0, hold = 2.5, absorb = 2.0, axis = "up", spin = -16},
    {fn = symFlower, t0 = 43.5, draw = 7.0, hold = 4.5, absorb = 2.5, axis = "fwd", spin = 4},
}
local T_GROW, T_BURST, T_SPREAD, T_GATHER = 58.5, 63.0, 66.2, 69.6

local plans, recs = {}, {}
local loopIdx = -1
local absorbed = 0

local function makePlans()
    plans = {}
    plans[#plans + 1] = {kind = "core", t0 = 0.2, tDraw = 1.8, tAbsorb = T_BURST, tEnd = T_BURST,
                         build = function() return coreJobs(), {0, 0, 0} end}
    for _, A in ipairs(ACTS) do
        plans[#plans + 1] = {kind = "symbol", act = A, t0 = A.t0, tDraw = A.t0 + A.draw, tAbsorb = A.t0 + A.draw + A.hold,
                             tEnd = A.t0 + A.draw + A.hold + A.absorb,
                             build = function() return symbolJobs(A.fn(), A.tilt), {0, 0, 0} end}
    end
    local ts = 1.0
    while ts < 52 do                                     -- ink tendrils: drawn, drift, swallowed
        local a = Random.value * TAU
        local r = 0.55 + 0.6 * Random.value
        local c = {r * Math:Sin(a), (Random.value * 2 - 1) * 0.5, r * Math:Cos(a)}
        plans[#plans + 1] = {kind = "strand", t0 = ts, tDraw = ts + 2.2, tAbsorb = ts + 8.2, tEnd = ts + 10.2,
                             build = function() return strandJobs(c), c end,
                             drift = {(Random.value * 2 - 1) * 0.25, 0.1 + 0.2 * Random.value, (Random.value * 2 - 1) * 0.25},
                             axis = {Random.value * 2 - 1, 1, Random.value * 2 - 1}, turn = (Random.value * 2 - 1) * 60}
        ts = ts + 2.6 + 0.8 * Random.value
    end
    plans[#plans + 1] = {kind = "splash", t0 = T_BURST, tDraw = T_BURST + 0.6, tAbsorb = T_SPREAD, tEnd = T_GATHER,
                         build = function() return splashJobs(), {0, 0, 0} end}
end

local function deleteRec(rec)
    if rec.pen then rec.pen.cancelled = true end
    Sketch.layers.active = saved.layer
    rec.layer:Delete()
end

local function startPlan(p)
    local L = Layer:New()
    local jobs, center = p.build()
    local w = world(center)
    local rec = {plan = p, layer = L, P = {w.x, w.y, w.z}}
    recs[#recs + 1] = rec
    newPen(rec, jobs, p.tDraw - p.t0)
end

local function axisOf(name)
    if name == "fwd" then return FWD end
    return {0, 1, 0}
end

local function updateRec(rec, t)
    local p = rec.plan
    local L = rec.layer
    if t < p.tDraw then return end                       -- still being drawn: the layer stays still
    if rec.pen and not rec.pen.cancelled then rec.pen.cancelled = true end
    local m = S_UNITS * Parameters.size
    local CW = {C[1], C[2], C[3]}
    if p.kind == "symbol" then
        local A = p.act
        local h = t - p.tDraw
        local q = qAxis(axisOf(A.axis), A.spin * h)
        local s = 1 + 0.03 * Math:Sin(h * 2.2)
        if t >= p.tAbsorb then                           -- swallowed by the core: spiral and shrink
            local x = smooth((t - p.tAbsorb) / (p.tEnd - p.tAbsorb))
            q = qMul(qAxis(FWD, 220 * x), q)
            s = s * (1 - x) ^ 1.6 + 0.01
        end
        applyPose(L, q, s, rec.P, rec.P)
    elseif p.kind == "strand" then
        local h = t - p.tDraw
        local life = smooth(h / (p.tAbsorb - p.tDraw))
        local tg = {rec.P[1] + (p.drift[1] * RIGHT[1] + p.drift[2] * UPV[1] + p.drift[3] * FWD[1]) * m * life,
                    rec.P[2] + (p.drift[1] * RIGHT[2] + p.drift[2] * UPV[2] + p.drift[3] * FWD[2]) * m * life,
                    rec.P[3] + (p.drift[1] * RIGHT[3] + p.drift[2] * UPV[3] + p.drift[3] * FWD[3]) * m * life}
        local q = qAxis(p.axis, p.turn * life)
        local s = 1 + 0.08 * life
        if t >= p.tAbsorb then
            local x = smooth((t - p.tAbsorb) / (p.tEnd - p.tAbsorb))
            tg = {tg[1] + (CW[1] - tg[1]) * x, tg[2] + (CW[2] - tg[2]) * x, tg[3] + (CW[3] - tg[3]) * x}
            q = qMul(qAxis({0, 1, 0}, 160 * x), q)
            s = s * (1 - x) ^ 1.4 + 0.01
        end
        applyPose(L, q, s, rec.P, tg)
    elseif p.kind == "core" then
        local grow = smooth((t - T_GROW) / (T_BURST - T_GROW))
        local s = (1 + 0.1 * absorbed) * (1 + 0.08 * Math:Sin(t * 3.1)) * (1 + 2.5 * grow)
        local q = qAxis({0.2, 1, 0.1}, 25 * t + 500 * grow * grow)
        applyPose(L, q, s, rec.P, rec.P)
    elseif p.kind == "splash" then
        local s
        if t < p.tAbsorb then s = 1 + 1.4 * smooth((t - p.tDraw) / (p.tAbsorb - p.tDraw))
        else s = 2.4 * (1 - smooth((t - p.tAbsorb) / (p.tEnd - p.tAbsorb))) ^ 1.3 + 0.01 end
        applyPose(L, qAxis({0.3, 1, 0.2}, 30 * (t - p.tDraw)), s, rec.P, rec.P)
    end
end

local function tick(t)
    for _, p in ipairs(plans) do
        if not p.started and t >= p.t0 then
            p.started = true
            if t < p.tEnd - 0.05 then startPlan(p) end
        end
    end
    local keep = {}
    for _, rec in ipairs(recs) do
        if t >= rec.plan.tEnd then
            if rec.plan.kind == "symbol" or rec.plan.kind == "strand" then absorbed = absorbed + 1 end
            deleteRec(rec)
        else
            updateRec(rec, t)
            keep[#keep + 1] = rec
        end
    end
    recs = keep
end

-- ---------- the plugin ----------
function Start()
    placed = false
    recs, pens, plans = {}, {}, {}
    loopIdx = -1
    startTime = App.time
    lastTime = App.time
end

local function place()
    local p = Brush.position
    local d = Brush.direction
    FWD = norm({-d.x, 0, -d.z})
    UPV = {0, 1, 0}
    RIGHT = norm(cross(UPV, FWD))
    local zoom = App.currentScale
    if zoom == nil or zoom < 0.01 then zoom = 1 end
    S_UNITS = UNITS / zoom
    local dist = (0.9 + 1.3 * Parameters.size) * S_UNITS
    C = {p.x - FWD[1] * dist, p.y + 0.1 * S_UNITS, p.z - FWD[3] * dist}
    saved = {type = Brush.type, size = Brush.size, color = Brush.colorRgb, layer = Sketch.layers.active}
    placed = true
    clock0 = App.time
    App:Error("Kumma Ink: drawing (scene scale " .. Math:Round(zoom * 100) / 100 .. ")")
end

function Main()
    local now = App.time
    local dt = now - lastTime
    lastTime = now
    if not placed then
        if Brush.triggerPressedThisFrame or (now - startTime > 3) then place() end
        return
    end
    -- the pen slows down by itself when frames take too long, and speeds up again when there is room
    if dt > 1 / 45 then
        budget = budget * 0.7
        if budget < 6 then budget = 6 end
    elseif dt < 1 / 65 then
        budget = budget + 1
        if budget > 160 then budget = 160 end
    end
    local total = (now - clock0) * Parameters.speed
    local idx = Math:Floor(total / LOOP)
    local t = total - idx * LOOP
    if idx ~= loopIdx then
        for _, rec in ipairs(recs) do deleteRec(rec) end
        recs, pens = {}, {}
        absorbed = 0
        makePlans()
        loopIdx = idx
    end
    tick(t)
    drewThisFrame = false
    if dt > 0.2 then dt = 0.2 end
    if dt > 1 / 36 then
        drawEvery = drawEvery + 1
        if drawEvery > 10 then drawEvery = 10 end
    elseif dt < 1 / 65 and drawEvery > 1 then
        drawEvery = drawEvery - 1
    end
    frameNo = frameNo + 1
    if frameNo % drawEvery == 0 then runPens(dt * Parameters.speed * drawEvery) end
    if drewThisFrame then                                -- give the user's brush back after each frame of drawing
        Brush.type = saved.type
        Brush.size = saved.size
        Brush.colorRgb = saved.color
    end
    Sketch.layers.active = saved.layer
end

function End()
    for _, rec in ipairs(recs) do deleteRec(rec) end
    recs, pens = {}, {}
    placed = false
    if saved.type then
        Brush.type = saved.type
        Brush.size = saved.size
        Brush.colorRgb = saved.color
    end
end
