-- Kumma Ink for Open Brush (Background Plugin).
-- The Omani kumma's symbols drawn in the air in ink: a pen draws each symbol in front of you (outline, then a
-- scribble fill like the original pen drawing), it floats and breathes, then unwrites itself and fades while ink
-- flows around it in living streams. At the climax all the symbols return together as a turning constellation
-- around the great rosette, then everything is swallowed into a knot of ink that bursts, and it starts again.
--
-- How it works (from the Open Brush source): everything is drawn ONCE, hidden, a few strokes per frame. After that
-- the animation only reveals strokes (SetShaderClipping), dissolves them (_Dissolve) and moves layers, so it never
-- draws again: no hangs and nothing piling up in memory, however long it runs.
--
-- How to use: Extras > Plugins and Scripts > Background: pick KummaInk, press the eye button, then the big button
-- of the row. Point your hand forward; after 3 seconds (or press the trigger) the work appears in front of you.
-- Turning it off removes its layers.

Settings = {
    description = "Kumma Ink: the Omani kumma's symbols drawn in the air, flowing ink and a constellation",
    space = "canvas"
}

Parameters = {
    size = {label = "Size", type = "float", min = 0.2, max = 2, default = 0.9},
    distance = {label = "Distance (m)", type = "float", min = 0.8, max = 5, default = 2.1},
    speed = {label = "Speed", type = "float", min = 0.4, max = 2, default = 1},
    thickness = {label = "Thickness", type = "float", min = 0.3, max = 3, default = 1},
    density = {label = "Density", type = "int", min = 1, max = 3, default = 2},
}

local UNITS = 10                -- 1 meter = 10 units in Open Brush (at scene scale 1)
local TAU = 2 * Math.pi

-- ---------- state ----------
local placed = false
local C = {0, 0, 0}
local RIGHT, UPV, FWD = {1, 0, 0}, {0, 1, 0}, {0, 0, 1}
local S_UNITS = 10
local ZOOM = 1
local startTime, lastTime = 0, 0
local saved = {}

-- ---------- helpers ----------
local function norm(a)
    local l = Math:Sqrt(a[1] * a[1] + a[2] * a[2] + a[3] * a[3])
    if l < 1e-6 then return {0, 0, 1} end
    return {a[1] / l, a[2] / l, a[3] / l}
end
local function cross(a, b) return {a[2] * b[3] - a[3] * b[2], a[3] * b[1] - a[1] * b[3], a[1] * b[2] - a[2] * b[1]} end

local function world(p)
    local s = S_UNITS
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
local RADIAL = {}                      -- maps that lie on the imagined kumma's surface
local function ringMap(R)              -- (arc length, height) on a cylinder of radius R
    local f = function(p) local a = p[1] / R; return {R * Math:Sin(a), p[2], R * Math:Cos(a)} end
    RADIAL[f] = true
    return f
end
local function tangentMap(R, a, y0)    -- a small plane touching the cylinder at angle a
    local c, s = Math:Cos(a), Math:Sin(a)
    local f = function(p) return {R * s + p[1] * c, y0 + p[2], R * c - p[1] * s} end
    RADIAL[f] = true
    return f
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
                       fill = fill, spacing = spacing or 0.02, radial = RADIAL[map or IDENT] or false}
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
    L[#L + 1] = {path3 = pts, col = COL.green, radial = true}
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


local STRAND = {COL.magenta, COL.purple, COL.blue, COL.pink, COL.navy, COL.sky, COL.purple, COL.magenta, COL.green}

-- ---------- quaternions: each layer turns around its own center ----------
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

-- the work's frame (meters, relative to the center) -> canvas offset
local function off(o)
    local m = S_UNITS
    return {(o[1] * RIGHT[1] + o[2] * UPV[1] + o[3] * FWD[1]) * m,
            (o[1] * RIGHT[2] + o[2] * UPV[2] + o[3] * FWD[2]) * m,
            (o[1] * RIGHT[3] + o[2] * UPV[3] + o[3] * FWD[3]) * m}
end

-- show a layer's content (drawn around canvas point P) turned by q, scaled by s, its center moved to target
local function pose(L, q, s, P, target)
    local rp = qRot(q, P)
    L.position = Vector3:New(target[1] - s * rp[1], target[2] - s * rp[2], target[3] - s * rp[3])
    local w = q[4]
    if w < 0 then q = {-q[1], -q[2], -q[3], -w}; w = -w end
    if w > 1 then w = 1 end
    local half = Math:Acos(w)
    local sn = Math:Sin(half)
    if sn < 1e-5 then L.rotation = Rotation:AngleAxis(0, Vector3:New(0, 1, 0))
    else L.rotation = Rotation:AngleAxis(2 * half * 180 / Math.pi, Vector3:New(q[1] / sn, q[2] / sn, q[3] / sn)) end
    L.scale = s
end

-- reveal part of a layer's strokes, in the order they were drawn: from a to b (0..1). Never pass b <= 0
-- (Open Brush then turns clipping off and shows everything).
local function clip(L, a, b)
    if b < 0.0005 then b = 0.0005 end
    if a < 0 then a = 0 end
    if a > b then a = b end
    L:SetShaderClipping(a, b)
end
local function fade(L, v)
    if v < 0 then v = 0 elseif v > 1 then v = 1 end
    L:SetShaderFloat("_Dissolve", v)
end

-- ---------- drawing (once, hidden, a few strokes per frame) ----------
local VIEWROT = nil             -- the pen points away from the viewer: flat ribbons face you
local useDWB = nil
local strokesThisFrame, pointsThisFrame = 0, 0

local function pressure(i, n, base)
    local u = (i - 1) / Math:Max(1, n - 1)
    local e = Math:Sin(Math.pi * u)
    return base * (0.42 + 0.58 * e ^ 0.45)
end

local function drawInto(rec, pts, brush, widthM, color, smoothing, mode, taper)
    local n = #pts
    if n < 2 then return end
    local list = {}
    for i = 1, n do
        local p = pts[i]
        local w = world(p)
        local rot = VIEWROT
        if mode == "radial" then           -- ribbons lie on the surface of the imagined kumma
            local d = norm({-(p[1] * RIGHT[1] + p[3] * FWD[1]), 0, -(p[1] * RIGHT[3] + p[3] * FWD[3])})
            if d[1] * d[1] + d[3] * d[3] > 0.01 then rot = Rotation:LookRotation(Vector3:New(d[1], 0, d[3]), Vector3:New(0, 1, 0)) end
        end
        local pr = taper and pressure(i, n, 1) or 0.95
        list[i] = Transform:New(w, rot, pr)
    end
    list[n + 1] = list[n]                -- Open Brush skips the last point of a path
    local path = Path:New(list)
    local size = widthM * UNITS * Parameters.size * Parameters.thickness / ZOOM
    local col = Color:New(color)
    if useDWB ~= false then
        local ok = pcall(function() path:DrawWithBrush(brush, size, col, smoothing, rec.layer) end)
        if ok then useDWB = true else useDWB = false end
    end
    if useDWB == false then              -- older versions: draw with the pointer's brush on the active layer
        Sketch.layers.active = rec.layer
        Brush.type = brush
        -- Brush.size is 0..1 of the brush's range; sizeAbsolute is the real size
        if not pcall(function() Brush.sizeAbsolute = size end) then Brush.size = 0.25 end
        Brush.colorRgb = col
        path:Draw()
    end
    strokesThisFrame = strokesThisFrame + 1
    pointsThisFrame = pointsThisFrame + n * ((smoothing > 0) and 4 or 1)
end

-- jobs for a symbol: outlines first, then the scribble fills (that is also the order the pen reveals them)
local function symbolJobs(shapes)
    local jobs = {}
    for _, sh in ipairs(shapes) do
        local d
        if sh.path3 then d = densify(sh.path3, false, 0.04)
        elseif sh.outline then
            local flat = densify(sh.poly, true, 0.04)
            d = {}
            for i = 1, #flat do d[i] = sh.map(flat[i]) end
            d = handLoop(d)
        end
        if d then jobs[#jobs + 1] = {pts = wobble(d, 0.0035), brush = "Marker", w = 0.02, col = sh.col, smooth = 0.18,
                                     mode = sh.radial and "radial" or "view", taper = true} end
    end
    for _, sh in ipairs(shapes) do
        if sh.fill then
            local sp = sh.spacing * (1.05 - 0.15 * Parameters.density)
            local z = densify(scribble(sh.poly, sp, Random.value * Math.pi), false, 0.06)
            local out = {}
            for i = 1, #z do out[i] = sh.map(z[i]) end
            jobs[#jobs + 1] = {pts = wobble(out, 0.0015), brush = "Marker", w = 0.0105, col = sh.col, smooth = 0,
                               mode = sh.radial and "radial" or "view"}
        end
    end
    return jobs
end

local function strandJobs(k, n)
    local jobs = {}
    for i = 1, 4 + Parameters.density do
        local a = (k + Random.value) * TAU / n
        local r = 0.45 + 0.85 * Random.value
        local s = {r * Math:Sin(a), (Random.value * 2 - 1) * 0.55, r * Math:Cos(a)}
        local pts = tendril(s, 40 + Math:Round(24 * Random.value), 0.03)
        jobs[#jobs + 1] = {pts = wobble(pts, 0.004), brush = "Tapered Marker", w = 0.013 + 0.008 * Random.value,
                           col = STRAND[1 + Math:Floor(Random.value * #STRAND)], smooth = 0.2, mode = "view", taper = true}
    end
    return jobs
end

local function dropJobs(k)
    local jobs = {}
    for i = 1, 14 + 6 * Parameters.density do       -- ink droplets in a loose shell
        local d = norm({Random.value * 2 - 1, (Random.value * 2 - 1) * 0.75, Random.value * 2 - 1})
        local r = 0.5 + 0.9 * Random.value ^ 0.7
        local p = {d[1] * r, d[2] * r, d[3] * r}
        local pts = {p, {p[1] + 0.02, p[2] + 0.01, p[3]}, {p[1] + 0.04, p[2] + 0.005, p[3] + 0.01}}
        local col = (i % 3 == 0) and COL.ink or STRAND[1 + ((i + k) % #STRAND)]
        jobs[#jobs + 1] = {pts = pts, brush = "Dot Marker", w = 0.012, col = col, smooth = 0, mode = "view"}
    end
    return jobs
end

local function coreJobs()
    local jobs = {}
    for i = 1, 7 do                                  -- a tight knot of ink scribbles
        local pts = {}
        local ph = Random.value * TAU
        local ax = Random.value * TAU
        for j = 0, 34 do
            local a = ph + j * 0.6
            local r = 0.03 + 0.045 * Random.value
            local x, y, z = r * Math:Cos(a), r * Math:Sin(a), 0.03 * Math:Sin(a * 0.7)
            pts[#pts + 1] = {x * Math:Cos(ax) - z * Math:Sin(ax), y, x * Math:Sin(ax) + z * Math:Cos(ax)}
        end
        jobs[#jobs + 1] = {pts = pts, brush = "Marker", w = 0.008, col = (i % 2 == 0) and COL.magenta or COL.navy,
                           smooth = 0.15, mode = "view", taper = true}
    end
    return jobs
end

-- ---------- the parts of the work (each one a hidden layer, drawn once) ----------
local recs = {}
local queue = {}
local function newRec(kind, build, extra)
    local L = Layer:New()
    local rec = {kind = kind, layer = L, build = build, ready = false, shown = true}
    if extra then for k, v in pairs(extra) do rec[k] = v end end
    recs[#recs + 1] = rec
    queue[#queue + 1] = rec
    return rec
end
local function show(rec, on)
    if on and not rec.shown then rec.layer:Show(); rec.shown = true end
    if (not on) and rec.shown then rec.layer:Hide(); rec.shown = false end
end

-- each symbol is made of parts (layers) that turn on their own: interlacing stars, orbiting medallions, gears of bands
local function dirOf(v) return {v[1] * RIGHT[1] + v[2] * UPV[1] + v[3] * FWD[1], v[1] * RIGHT[2] + v[2] * UPV[2] + v[3] * FWD[2],
                                v[1] * RIGHT[3] + v[2] * UPV[3] + v[3] * FWD[3]} end
local function partsStar()
    local outer, inner = {}, {}
    S(outer, khatam(0.95), COL.magenta)
    khatamTips(outer, 0.95, COL.magenta)
    for k = 0, 3 do
        local a = Math.pi / 4 + k * Math.pi / 2
        local cx, cy = 1.38 * Math:Cos(a), 1.38 * Math:Sin(a)
        S(outer, rhombus(0.11, 0.17, cx, cy), COL.green, nil, true, true, 0.016)
        S(outer, rhombus(0.05, 0.08, cx, cy), COL.lime, nil, true, true, 0.012)
    end
    S(inner, khatam(0.78), COL.purple)
    khatamTips(inner, 0.78, COL.purple)
    local oct = {}
    for i = 0, 7 do
        local a = i * TAU / 8 + Math.pi / 8
        oct[#oct + 1] = {0.45 * Math:Cos(a), 0.45 * Math:Sin(a)}
    end
    S(inner, oct, COL.blue, nil, true, true, 0.02)
    S(inner, circle(0.24, 36), COL.sky, nil, true, true, 0.016)
    S(inner, circle(0.07, 16), COL.navy, nil, true, true, 0.01)
    return {{shapes = outer, spin = 1}, {shapes = inner, spin = -1.8}}
end
local function partsMedallions()
    local parts = {}
    local spots = {{-0.78, -0.32, 0.25, 0.5}, {0.78, -0.32, 0.25, -0.5}, {0, 0.6, -0.1, 0}}
    for i, sp in ipairs(spots) do
        local L = {}
        medallion(L, 0.44, planar(sp[1], sp[2], sp[3], sp[4]))
        parts[#parts + 1] = {shapes = L, center = {sp[1], sp[2], sp[3]}, spin = (i % 2 == 0) and -3 or 3,
                             axis = {Math:Sin(sp[4]), 0, Math:Cos(sp[4])}}
    end
    return parts
end
local function partsBands()                       -- a rosette border: triangles around a ring, two rings of beads
    local tri, inner, outer = {}, {}, {}
    local R, n = 0.92, 24
    for k = 0, n - 1 do
        local a0, a1 = k * TAU / n, (k + 1) * TAU / n
        local am = (a0 + a1) / 2
        S(tri, {{R * Math:Cos(a0), R * Math:Sin(a0)}, {(R + 0.3) * Math:Cos(am), (R + 0.3) * Math:Sin(am)},
                {R * Math:Cos(a1), R * Math:Sin(a1)}}, (k % 2 == 0) and COL.purple or COL.red, nil, true, true, 0.015)
    end
    S(tri, circle(R, 96), COL.magenta)
    S(inner, circle(0.62, 80), COL.blue)
    for k = 0, 23 do
        local a = k * TAU / 24
        S(inner, circle(0.05, 14, 0.74 * Math:Cos(a), 0.74 * Math:Sin(a)), (k % 2 == 0) and COL.pink or COL.sky, nil, true, true, 0.01)
    end
    S(outer, circle(1.47, 120), COL.blue)
    for k = 0, 35 do
        local a = k * TAU / 36
        S(outer, circle(0.045, 14, 1.36 * Math:Cos(a), 1.36 * Math:Sin(a)), (k % 2 == 0) and COL.sky or COL.pink, nil, true, true, 0.01)
    end
    return {{shapes = tri, spin = 1}, {shapes = inner, spin = -1.7}, {shapes = outer, spin = 2.2}}
end
local function leafAt(cx, cy, ang, len, w)
    local L = lens(ang, 0, len, w, 12)
    for i = 1, #L do L[i] = {L[i][1] + cx, L[i][2] + cy} end
    return L
end
local function partsVine()                        -- an arabesque: four curling stems with leaves and berries
    local parts = {}
    for s = 0, 3 do
        local sh = {}
        local ph = s * Math.pi / 2
        local stem = {}
        local N = 160
        for i = 0, N do
            local u = i / N
            local a = ph + u * 1.3 * Math.pi
            local r = 0.14 + 0.95 * u ^ 0.8 + 0.03 * Math:Sin(u * 9 * Math.pi)
            stem[#stem + 1] = {r * Math:Cos(a), r * Math:Sin(a), 0.1 * Math:Sin(u * 3 * Math.pi + s)}
        end
        sh[#sh + 1] = {path3 = stem, col = COL.green, radial = false}
        for j = 1, 6 do                            -- leaves on alternating sides, berries at the ends of the curls
            local i = Math:Floor(N * (0.12 + 0.14 * j))
            if i > N - 2 then i = N - 2 end
            local p, q = stem[i + 1], stem[i + 2]
            local ta = Math:Atan2(q[2] - p[2], q[1] - p[1])
            local side = (j % 2 == 0) and 1 or -1
            S(sh, leafAt(p[1], p[2], ta + side * 1.0, 0.17, 0.05), (j % 3 == 0) and COL.lime or COL.green, nil, true, true, 0.01)
            if j % 2 == 1 then
                local bx, by = p[1] - side * 0.07 * Math:Sin(ta), p[2] + side * 0.07 * Math:Cos(ta)
                for _, o in ipairs({{-0.03, 0}, {0.03, 0}, {0, 0.045}}) do
                    S(sh, circle(0.026, 12, bx + o[1], by + o[2]), (j % 3 == 0) and COL.pink or COL.magenta, nil, true, true, 0.008)
                end
            end
        end
        parts[#parts + 1] = {shapes = sh, spin = (s % 2 == 0) and 1 or 1.25}
    end
    return parts
end
local function partsFlower()
    local inner, outer = {}, {}
    local R = 1.0
    for k = 0, 7 do
        local a = k * TAU / 8 + Math.pi / 2
        S(inner, lens(a, R * 0.14, R * 0.98, R * 0.17, 20), COL.magenta, nil, true, true, 0.018)
        S(inner, lens(a, R * 0.24, R * 0.78, R * 0.06, 16), COL.pink)
        S(inner, lens(a + Math.pi / 8, R * 0.18, R * 0.66, R * 0.07, 16), COL.green, nil, true, true, 0.014)
    end
    S(inner, circle(R * 0.13, 32), COL.lime, nil, true, true, 0.012)
    S(outer, circle(R * 1.04, 128), COL.purple)
    S(outer, circle(R * 1.1, 128), COL.blue)
    for k = 0, 7 do
        local a = k * TAU / 8 + Math.pi / 8
        local cx, cy = 1.5 * Math:Cos(a), 1.5 * Math:Sin(a)
        local col = (k % 2 == 0) and COL.blue or COL.sky
        S(outer, khatam(0.16, cx, cy), col)
        khatamTips(outer, 0.16, col, nil, cx, cy)
        S(outer, circle(0.05, 12, cx, cy), COL.navy, nil, true, true, 0.01)
    end
    return {{shapes = inner, spin = 1}, {shapes = outer, spin = -0.8}}
end

-- the timeline (seconds in an 86-second loop)
local LOOP = 86
local ACTS = {
    {name = "star",       fn = partsStar,       t0 = 4,  draw = 4.8, float = 4.2, unravel = 3.2, axis = "view", spin = 9},
    {name = "medallions", fn = partsMedallions, t0 = 17, draw = 5.5, float = 4.0, unravel = 3.2, axis = "view", spin = -7},
    {name = "bands",      fn = partsBands,      t0 = 30, draw = 5.5, float = 4.0, unravel = 3.2, axis = "view", spin = 8},
    {name = "vine",       fn = partsVine,       t0 = 43, draw = 5.5, float = 4.0, unravel = 3.2, axis = "view", spin = -10},
    {name = "flower",     fn = partsFlower,     t0 = 56, draw = 6.0, float = 3.5, unravel = 0,   axis = "view", spin = 5},
}
local T_CONST, T_COLLAPSE, T_BURST, T_CALM = 65.5, 76.5, 80.5, 84.5
-- the constellation: where each symbol goes around the rosette (work frame, meters) and its size there
local RING = {star = {-1.0, 0.5, -0.1, 0.34}, medallions = {1.0, 0.5, -0.1, 0.3}, bands = {-0.95, -0.6, 0.05, 0.3},
              vine = {0.95, -0.6, 0.05, 0.34}, flower = {0, 0, 0, 0.6}}

local function buildAll()
    VIEWROT = Rotation:LookRotation(Vector3:New(-FWD[1], -FWD[2], -FWD[3]), Vector3:New(0, 1, 0))
    newRec("core", coreJobs)
    for i, A in ipairs(ACTS) do
        local parts = A.fn()
        for k, part in ipairs(parts) do
            newRec("symbol", function() return symbolJobs(part.shapes) end,
                   {act = A, part = k, center = part.center or {0, 0, 0}, spin = part.spin or 1, ownAxis = part.axis})
        end
        if i <= 4 then                               -- the ink streams are prepared between the symbols
            newRec("strand", function() return strandJobs(2 * i - 2, 8) end,
                   {axis = {Random.value - 0.5, 1, Random.value - 0.5}, turn = (Random.value < 0.5 and -1 or 1) * (0.5 + Random.value),
                    period = 7 + 5 * Random.value, ph = Random.value, win = 0.35 + 0.2 * Random.value})
            newRec("strand", function() return strandJobs(2 * i - 1, 8) end,
                   {axis = {Random.value - 0.5, 1, Random.value - 0.5}, turn = (Random.value < 0.5 and -1 or 1) * (0.5 + Random.value),
                    period = 7 + 5 * Random.value, ph = Random.value, win = 0.35 + 0.2 * Random.value})
        end
    end
    for k = 1, 3 do newRec("drops", function() return dropJobs(k) end, {axis = {Random.value - 0.5, 1, Random.value - 0.5}, turn = (k % 2 == 0) and -0.4 or 0.6}) end
    for _, rec in ipairs(recs) do rec.layer:Hide(); rec.shown = false end
    Sketch.layers.active = saved.layer
end

-- draw a little of the queue each frame (adapts to how busy the headset is)
local budget = 3
local function prepare(dt)
    if dt > 1 / 45 then budget = Math:Max(1, budget - 1) elseif dt < 1 / 66 then budget = Math:Min(10, budget + 0.25) end
    strokesThisFrame, pointsThisFrame = 0, 0
    while #queue > 0 and strokesThisFrame < Math:Floor(budget) and pointsThisFrame < 150 * budget do
        local rec = queue[1]
        if not rec.jobs then rec.jobs = rec.build(); rec.j = 1 end
        if rec.j > #rec.jobs then
            rec.ready = true
            table.remove(queue, 1)
        else
            local jb = rec.jobs[rec.j]
            drawInto(rec, jb.pts, jb.brush, jb.w, jb.col, jb.smooth, jb.mode, jb.taper)
            rec.j = rec.j + 1
        end
    end
    if useDWB == false then
        Sketch.layers.active = saved.layer
        if #queue == 0 and saved.type then           -- give the user's brush back once everything is drawn
            Brush.type = saved.type
            pcall(function() Brush.sizeAbsolute = saved.size end)
            Brush.colorRgb = saved.color
        end
    end
end

-- ---------- the movement, every frame ----------
local function actState(A, t)
    local d0, d1 = A.t0, A.t0 + A.draw
    local f1 = d1 + A.float
    local u1 = f1 + A.unravel
    if t < d0 then return "before" end
    if t < d1 then return "draw", (t - d0) / A.draw end
    if t < f1 then return "float", (t - d1) / A.float end
    if A.unravel > 0 and t < u1 then return "unravel", (t - f1) / A.unravel end
    return "after"
end

local function animSymbol(rec, t)
    local A = rec.act
    local L = rec.layer
    local st, x = actState(A, t)
    local h = t - A.t0
    local ax = (A.axis == "up") and {0, 1, 0} or FWD
    -- the symbol's own frame: a slow turn, a living sway, breathing and a gentle bob
    local Qs = qAxis(ax, A.spin * h)
    if A.tilt then Qs = qMul(qAxis(RIGHT, A.tilt), Qs) end
    Qs = qMul(qAxis(UPV, 9 * Math:Sin(h * 0.45)), Qs)
    local Ss = 1 + 0.025 * Math:Sin(h * 1.9)
    local bob = off({0, 0.03 * Math:Sin(h * 0.8), 0})
    local Ts = {C[1] + bob[1], C[2] + bob[2], C[3] + bob[3]}
    local ca, cb, fv = 0, 1.0001, 1
    if t >= T_CONST and t < T_COLLAPSE + 3.5 then                       -- the constellation, then the collapse
        local R = RING[A.name]
        local col = smooth((t - T_COLLAPSE) / 3.5)
        local rp = qRot(qAxis(FWD, 14 * (t - T_CONST)), off({R[1], R[2], R[3]}))
        Ts = {C[1] + rp[1] * (1 - col), C[2] + rp[2] * (1 - col), C[3] + rp[3] * (1 - col)}
        Qs = qMul(qAxis(FWD, 300 * col * col), qMul(qAxis(ax, A.spin * 1.5 * h), A.tilt and qAxis(RIGHT, A.tilt) or Q0))
        Ss = R[4] * (1 - col) ^ 1.5 + 0.01
        local stagger = ({star = 0, medallions = 0.4, bands = 0.8, vine = 1.2, flower = 0})[A.name]
        if A.name ~= "flower" then cb = 1.0001 * smooth((t - T_CONST - stagger) / 2.2) end
        fv = 1 - col * col
    else
        if st == "before" or st == "after" then show(rec, false); return end
        if st == "draw" then                                            -- the pens draw the parts, outline then fill
            local k = rec.part - 1
            local xx = (x - 0.12 * k) / (1 - 0.12 * k)
            if xx < 0 then xx = 0 end
            cb = 1.0001 * (0.03 + 0.97 * smooth(xx))
            Ss = Ss * (0.97 + 0.03 * x)
        elseif st == "unravel" then                                     -- it unwrites itself and fades, drifting up
            local e = smooth(x)
            ca = 0.9 * e
            fv = 1 - e ^ 1.4
            Ss = Ss * (1 + 0.22 * e)
            local up = off({0, 0.18 * e, 0.05 * e})
            Ts = {Ts[1] + up[1], Ts[2] + up[2], Ts[3] + up[3]}
            Qs = qMul(qAxis(ax, 25 * e), Qs)
        end
    end
    show(rec, true)
    clip(L, ca, cb)
    fade(L, fv)
    -- the part turns on its own around its own center, carried by the symbol
    local oax = rec.ownAxis and dirOf(rec.ownAxis) or ax
    local q = qMul(Qs, qAxis(oax, A.spin * (rec.spin - 1) * h))
    local co = off(rec.center)
    local cr = qRot(Qs, co)
    local target = {Ts[1] + Ss * cr[1], Ts[2] + Ss * cr[2], Ts[3] + Ss * cr[3]}
    local P = {C[1] + co[1], C[2] + co[2], C[3] + co[3]}
    pose(L, q, Ss, P, target)
end

local function animStrand(rec, t, life)
    local L = rec.layer
    local P = {C[1], C[2], C[3]}
    -- the ink flows along its streams: a window slides along the strokes
    local w = rec.win * (0.8 + 0.4 * life.surge)
    local a = ((t / rec.period + rec.ph) % 1) * (1 + w) - w
    clip(L, a, a + w)
    fade(L, life.vis)
    local q = qAxis(rec.axis, 360 * rec.turn * t / LOOP * life.spin)
    local s = life.scale
    pose(L, q, s, P, P)
end

local function lifeAt(t)
    -- how the ink around behaves through the loop
    local appear = smooth(t / 3.5)
    local col = smooth((t - T_COLLAPSE) / 3.5)
    local burst = smooth((t - T_BURST) / 1.2)
    local calm = smooth((t - T_BURST - 1.2) / 2.8)
    local scale = 0.15 + 0.85 * appear
    if t >= T_COLLAPSE then scale = (1 - col) * 1 + 0.03 end
    if t >= T_BURST then scale = 0.03 + 1.5 * burst - 0.5 * calm end
    local vis = 0.35 + 0.65 * appear
    if t >= T_COLLAPSE and t < T_BURST then vis = 1 - 0.6 * col end
    if t >= T_BURST then vis = 0.4 + 0.6 * burst end
    local surge = 0.5 + 0.5 * Math:Sin(t * 0.21) + smooth((t - T_CONST) / 3) * 0.6
    local spin = 1 + 4 * col * (1 - burst)
    return {scale = scale, vis = vis, surge = surge, spin = spin}
end

local function animCore(rec, t)
    local L = rec.layer
    local P = {C[1], C[2], C[3]}
    local seed = 1 - smooth((t - 3.5) / 1.5)
    local col = smooth((t - T_COLLAPSE) / 3.5)
    local burst = smooth((t - T_BURST) / 0.6)
    local vis = Math:Max(seed, col * (1 - burst))
    for _, A in ipairs(ACTS) do                                    -- it flickers as each symbol unwrites itself
        local st, x = actState(A, t)
        if st == "unravel" then vis = Math:Max(vis, 0.55 * Math:Sin(Math.pi * x)) end
    end
    if vis < 0.02 then show(rec, false); return end
    show(rec, true)
    clip(L, 0, 1.0001 * Math:Max(smooth(t / 2.5), (t > 3) and 1 or 0))
    fade(L, vis)
    local s = 1 + 0.12 * Math:Sin(t * 3) + 3.2 * col * (1 - burst) + 2 * burst
    pose(L, qAxis({0.2, 1, 0.1}, 40 * t + 600 * col * col), s, P, P)
end

local function animDrops(rec, t, life)
    local L = rec.layer
    local P = {C[1], C[2], C[3]}
    show(rec, true)
    clip(L, 0, 1.0001 * smooth((t - 0.5) / 4))
    fade(L, 0.75 * life.vis)
    local s = life.scale * (1 + 0.04 * Math:Sin(t * 0.9 + rec.turn))
    pose(L, qAxis(rec.axis, 360 * rec.turn * t / LOOP * life.spin), s, P, P)
end

-- ---------- the plugin ----------
local clockT, ready = 0, false

function Start()
    placed = false
    recs, queue = {}, {}
    startTime = App.time
    lastTime = App.time
    clockT, ready = 0, false
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
    C = {p.x - FWD[1] * dist, p.y + 0.12 * UNITS / ZOOM, p.z - FWD[3] * dist}
    local sz = Brush.size
    pcall(function() sz = Brush.sizeAbsolute end)
    saved = {layer = Sketch.layers.active, type = Brush.type, size = sz, color = Brush.colorRgb}
    buildAll()
    placed = true
    App:Error("Kumma Ink: preparing the ink...")
end

function Main()
    local now = App.time
    local dt = now - lastTime
    lastTime = now
    if not placed then
        if Brush.triggerPressedThisFrame or (now - startTime > 3) then place() end
        return
    end
    if #queue > 0 then prepare(dt) end
    -- the clock waits if the next part is not drawn yet (only in the first loop)
    local nextNeeded = nil
    for _, rec in ipairs(recs) do
        if not rec.ready then
            local tNeed = 0
            if rec.kind == "symbol" then tNeed = rec.act.t0 elseif rec.kind == "strand" or rec.kind == "drops" then tNeed = 0.5 end
            if rec.kind == "core" then tNeed = 0 end
            if nextNeeded == nil or tNeed < nextNeeded then nextNeeded = tNeed end
        end
    end
    local step = dt
    if step > 0.1 then step = 0.1 end
    local tLoop = clockT % LOOP
    if nextNeeded == nil or tLoop + step * Parameters.speed < nextNeeded or clockT >= LOOP then
        clockT = clockT + step * Parameters.speed
    end
    if not ready and #queue == 0 then
        ready = true
        App:Error("Kumma Ink: ready")
    end
    local t = clockT % LOOP
    local life = lifeAt(t)
    for _, rec in ipairs(recs) do
        if rec.ready or rec.kind == "symbol" then
            if rec.kind == "symbol" then if rec.ready then animSymbol(rec, t) end
            elseif rec.kind == "strand" then show(rec, true); animStrand(rec, t, life)
            elseif rec.kind == "drops" then animDrops(rec, t, life)
            elseif rec.kind == "core" then animCore(rec, t) end
        end
    end
end

function End()
    for _, rec in ipairs(recs) do rec.layer:Delete() end
    recs, queue = {}, {}
    placed = false
    if saved.layer then Sketch.layers.active = Sketch.layers.main end
    if useDWB == false and saved.type then
        Brush.type = saved.type
        pcall(function() Brush.sizeAbsolute = saved.size end)
        Brush.colorRgb = saved.color
    end
end
