-- Kumma Ink for Open Brush (Background Plugin).
-- The Omani kumma's symbols are drawn in the air in ink, as if by an invisible pen: the outline first,
-- then a back-and-forth scribble fill like the original pen drawing, then a living sketchy line on top.
-- Each symbol holds, then dissolves like ink in water with a splash of droplets, while ink strands flow
-- around it. At the end everything swirls into a point and bursts again. A 72-second loop.
--
-- How to use: Extras > Plugins and Scripts > Background: pick KummaInk, press the eye button, then the
-- big button of the row. Point your hand forward and press the trigger, or wait 3 seconds.
-- Looks best on a light background (Extras > Backdrop). Turning it off removes its layers.

Settings = {
    description = "Kumma Ink: Omani kumma symbols drawn in the air in living ink",
    space = "canvas"
}

Parameters = {
    size = {label = "Size", type = "float", min = 0.3, max = 3, default = 1},
    speed = {label = "Speed", type = "float", min = 0.3, max = 2, default = 1},
    thickness = {label = "Thickness", type = "float", min = 0.2, max = 4, default = 1},
    density = {label = "Density", type = "int", min = 1, max = 3, default = 2},
}

local LOOP = 72
local UNITS = 10                -- 1 meter = 10 units in Open Brush
local TAU = 2 * Math.pi

-- ---------- state ----------
local placed = false
local C = {0, 0, 0}
local RIGHT, UPV, FWD = {1, 0, 0}, {0, 1, 0}, {0, 0, 1}
local S_UNITS = 10
local layers = {}
local clock0, startTime = 0, 0
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

-- ---------- the colors of the drawing (inks), and a darker ink for the living outline ----------
local COL = {
    navy = "#2B2A93", blue = "#3C7FE0", sky = "#7CC4F2", red = "#9E1B3A", magenta = "#D4248F",
    pink = "#E86BB8", purple = "#6E2BB5", green = "#3FAE4C", lime = "#8BD650", ink = "#2A1145",
}
local DARK = {}
DARK[COL.magenta] = "#8C1360"; DARK[COL.purple] = "#45208A"; DARK[COL.blue] = "#1F4FA6"
DARK[COL.sky] = "#2F7FB0"; DARK[COL.green] = "#1F7A33"; DARK[COL.lime] = "#4E8F2A"
DARK[COL.pink] = "#B03C80"; DARK[COL.red] = "#6E1026"; DARK[COL.navy] = "#1A1A66"

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

local function stroke(pts, brush, fallback, size, color)
    if #pts < 2 then return end
    local list = {}
    for i = 1, #pts do list[i] = world(pts[i]) end
    setBrush(brush, fallback)
    Brush.size = size * Parameters.thickness
    Brush.colorRgb = Color:New(color)
    local path = Path:New(list)
    path:Draw()
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

-- draw a symbol: its lines (pen outline + living sketch line) and its scribble fills
local function drawLines(shapes)
    for _, sh in ipairs(shapes) do
        local d
        if sh.path3 then
            d = densify(sh.path3, false, 0.02)
        elseif sh.outline then
            local flat = densify(sh.poly, true, 0.015)
            d = {}
            for i = 1, #flat do d[i] = sh.map(flat[i]) end
            d = handLoop(d)
        end
        if d then
            stroke(wobble(d, 0.004), "Tapered Marker", "Marker", 0.05, sh.col)
            stroke(wobble(d, 0.007), "Dr. Wigglez", "Marker", 0.04, DARK[sh.col] or COL.ink)
        end
    end
end
local function drawFills(shapes)
    for _, sh in ipairs(shapes) do
        if sh.fill then
            local sp = sh.spacing * (2.2 - 0.6 * Parameters.density)
            local z = scribble(sh.poly, sp, Random.value * Math.pi)
            local d = densify(z, false, 0.03)
            local out = {}
            for i = 1, #d do out[i] = sh.map(d[i]) end
            stroke(wobble(out, 0.002), "Marker", "Marker", 0.022, sh.col)
        end
    end
end

-- ---------- the ink around: strands along the lines of a chaotic stream, and droplets ----------
local function flow(p)
    local k = 2.2
    local x, y, z = p[1] * k, p[2] * k, p[3] * k
    local vx = Math:Sin(z) + 0.6 * Math:Cos(y)
    local vy = 0.75 * Math:Sin(x) + Math:Cos(z)
    local vz = 0.6 * Math:Sin(y) + 0.75 * Math:Cos(x)
    return norm({vx - 0.7 * p[3], vy * 0.6, vz + 0.7 * p[1]})
end
local function streamline(seed, steps, h)
    local pts = {seed}
    local p = seed
    for i = 1, steps do
        local v = flow(p)
        p = {p[1] + v[1] * h, p[2] + v[2] * h, p[3] + v[3] * h}
        if p[1] * p[1] + p[2] * p[2] + p[3] * p[3] > 1.7 * 1.7 then break end
        pts[#pts + 1] = p
    end
    return pts
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

local function drawCluster(k, n, count)
    for i = 1, count do
        local a = (k + Random.value) * TAU / n
        local r = 0.3 + 1.0 * Random.value ^ 0.7
        local s = {r * Math:Sin(a), (Random.value * 2 - 1) * 0.6 * (1.2 - 0.4 * r), r * Math:Cos(a)}
        local pts = tendril(s, 34 + Math:Round(22 * Random.value), 0.028)
        local col = STRAND[1 + Math:Floor(Random.value * #STRAND)]
        if i % 4 == 0 then
            stroke(wobble(pts, 0.006), "Dr. Wigglez", "Marker", 0.035, col)
        else
            stroke(wobble(pts, 0.004), "Tapered Marker", "Marker", 0.018 + 0.02 * Random.value, col)
        end
    end
    for i = 1, 2 do                      -- a few ink droplets
        local a = (k + Random.value) * TAU / n
        local r = 0.4 + 0.9 * Random.value
        local s = {r * Math:Sin(a), (Random.value * 2 - 1) * 0.5, r * Math:Cos(a)}
        stroke(streamline(s, 6, 0.03), "Dot Marker", "Stars", 0.03, (i == 1) and COL.ink or COL.purple)
    end
end

local function drawSplash()
    for i = 1, 36 do                     -- droplets thrown outward along curved rays
        local d = norm({Random.value * 2 - 1, (Random.value * 2 - 1) * 0.7, Random.value * 2 - 1})
        local r0 = 0.5 + 0.4 * Random.value
        local pts = {}
        for j = 0, 5 do
            local r = r0 + j * 0.06
            pts[#pts + 1] = {d[1] * r + 0.03 * j * d[3], d[2] * r, d[3] * r - 0.03 * j * d[1]}
        end
        local col = (i % 3 == 0) and COL.ink or STRAND[1 + (i % #STRAND)]
        stroke(pts, "Dot Marker", "Stars", 0.035, col)
    end
end

local function drawCore()
    for i = 1, 6 do                      -- a small tight knot of scribbles
        local pts = {}
        local ph = Random.value * TAU
        for j = 0, 40 do
            local a = ph + j * 0.55
            local r = 0.03 + 0.05 * Random.value
            pts[#pts + 1] = {r * Math:Cos(a), r * Math:Sin(a) * 0.8, 0.04 * Math:Sin(a * 0.7)}
        end
        stroke(pts, "Tapered Marker", "Marker", 0.02, (i % 2 == 0) and COL.magenta or COL.navy)
    end
end

-- ---------- layers ----------
local function newLayer(kind, drawFn, extra)
    local L = Layer:New()
    L.allowStrokeAnimation = true        -- before drawing, so each stroke can be revealed
    Sketch.layers.active = L
    drawFn()
    L:CenterPivot()
    local rec = {layer = L, kind = kind, base = L.position, visible = true}
    if extra then for k, v in pairs(extra) do rec[k] = v end end
    layers[#layers + 1] = rec
    return rec
end

local ACTS = {
    {name = "star", fn = symStar, t0 = 4, t1 = 12.5, hold = 3.0, axis = "fwd", spin = 5},
    {name = "medallions", fn = symMedallions, t0 = 15, t1 = 23.5, hold = 3.0, axis = "up", spin = 10},
    {name = "bands", fn = symBands, t0 = 26, t1 = 34.5, hold = 3.0, axis = "up", spin = 13, tilt = 24},
    {name = "vine", fn = symVine, t0 = 37, t1 = 45.5, hold = 3.0, axis = "up", spin = -14},
    {name = "flower", fn = symFlower, t0 = 49, t1 = 60.5, hold = 4.5, axis = "fwd", spin = 3},
}
local DRAW = 3.2                         -- seconds the pen takes to draw a symbol

local function build()
    saved = {type = Brush.type, size = Brush.size, color = Brush.colorRgb}
    local d = Parameters.density
    local NC = 8
    for k = 0, NC - 1 do
        newLayer("ink", function() drawCluster(k, NC, 4 * d) end, {
            amp = {0.08 + 0.1 * Random.value, 0.06 + 0.08 * Random.value, 0.08 + 0.1 * Random.value},
            freq = {1 + Math:Round(2 * Random.value), 1 + Math:Round(2 * Random.value), 1 + Math:Round(2 * Random.value)},
            ph = {Random.value * TAU, Random.value * TAU, Random.value * TAU},
            wobAxis = {Random.value * 2 - 1, 1, Random.value * 2 - 1},
            wob = 6 + 8 * Random.value, wobFreq = 1 + Math:Round(Random.value), flowPh = Random.value,
            flowSpeed = (Random.value < 0.5) and 1 or 2})
    end
    newLayer("core", drawCore, {amp = {0, 0, 0}, freq = {1, 1, 1}, ph = {0, 0, 0}, wobAxis = {0, 1, 0}, wob = 0, wobFreq = 1})
    local splash = newLayer("splash", drawSplash, {})
    splash.layer:Hide(); splash.visible = false
    for _, A in ipairs(ACTS) do
        local shapes = A.fn()
        local lines = newLayer("lines", function() drawLines(shapes) end, {act = A})
        local fills = newLayer("fills", function() drawFills(shapes) end, {act = A})
        lines.layer:Hide(); lines.visible = false
        fills.layer:Hide(); fills.visible = false
    end
    Sketch.layers.active = Sketch.layers.main
    Brush.type = saved.type
    Brush.size = saved.size
    Brush.colorRgb = saved.color
end

-- ---------- the movement every frame ----------
local function show(rec, on)
    if on and not rec.visible then rec.layer:Show(); rec.visible = true end
    if (not on) and rec.visible then rec.layer:Hide(); rec.visible = false end
end

local function animate(t)
    local burst = 0.18 * (bump(t, 12.4, 1.2) + bump(t, 23.4, 1.2) + bump(t, 34.4, 1.2) + bump(t, 45.4, 1.2)) + 0.25 * bump(t, 60.5, 1.2)
    local collapse = env(t, 61.5, 64.5, 68.2, 68.21)
    local nebScale = (1 + 0.04 * Math:Sin(t * 1.7) + burst) * (1 - 0.93 * collapse)
    if t >= 68.2 and t < 69.4 then nebScale = 0.07 + (1.25 - 0.07) * smooth((t - 68.2) / 1.2) end
    if t >= 69.4 then nebScale = 1.25 - 0.25 * smooth((t - 69.4) / 2.6) end
    local tiltAxis = Vector3:New(RIGHT[1], RIGHT[2], RIGHT[3])
    local vortex = 200 * env(t, 60.5, 63.5, 68.2, 68.21)
    local cv, sv = Math:Cos(vortex * Math.pi / 180), Math:Sin(vortex * Math.pi / 180)
    local w = TAU * t / LOOP
    local m = S_UNITS * Parameters.size

    -- the act in progress (for the splash)
    local act = nil
    for _, A in ipairs(ACTS) do if t >= A.t0 and t <= A.t1 then act = A end end

    for _, rec in ipairs(layers) do
        local L = rec.layer
        if rec.kind == "ink" or rec.kind == "core" then
            local o = {rec.amp[1] * Math:Sin(rec.freq[1] * w + rec.ph[1]), rec.amp[2] * Math:Sin(rec.freq[2] * w + rec.ph[2]),
                       rec.amp[3] * Math:Sin(rec.freq[3] * w + rec.ph[3])}
            local bx = rec.base.x - C[1] + (o[1] * RIGHT[1] + o[2] * UPV[1] + o[3] * FWD[1]) * m
            local by = rec.base.y - C[2] + (o[1] * RIGHT[2] + o[2] * UPV[2] + o[3] * FWD[2]) * m
            local bz = rec.base.z - C[3] + (o[1] * RIGHT[3] + o[2] * UPV[3] + o[3] * FWD[3]) * m
            bx, bz = bx * cv + bz * sv, -bx * sv + bz * cv
            L.position = Vector3:New(C[1] + bx * nebScale, C[2] + by * nebScale, C[3] + bz * nebScale)
            local wa = rec.wobAxis
            L.rotation = Rotation:AngleAxis(rec.wob * Math:Sin(rec.wobFreq * w + rec.ph[1]) + vortex,
                                            Vector3:New(wa[1] * 0.3, 1, wa[3] * 0.3))
            if rec.kind == "core" then
                L.scale = 1 + 1.5 * collapse + 0.8 * bump(t, 68.6, 1.4)
            else
                L.scale = nebScale * (1 + 0.05 * Math:Sin(2 * w + rec.ph[2]))
                -- the ink flows along its strands: a visible window slides along each stroke
                local win = 0.6
                local a = ((rec.flowPh + rec.flowSpeed * t / 14) % 1) * (1 + win) - win
                local cs = a; if cs < 0 then cs = 0 end
                local ce = 1 - (a + win); if ce < 0 then ce = 0 end
                L:SetShaderClipping(cs, ce)
            end
        elseif rec.kind == "splash" then
            -- when a symbol starts to dissolve, its ink splashes outward
            local on = false
            if act then
                local tr = act.t0 + DRAW + act.hold
                local x = (t - tr) / (act.t1 - tr)
                if x > 0 and x < 1 then
                    on = true
                    L.scale = 0.6 + 1.4 * smooth(x)
                    L:SetShaderClipping(0, 1 - smooth(x / 0.25))
                    L:SetShaderFloat("_Dissolve", 1 - smooth((x - 0.5) / 0.5))
                    L.rotation = Rotation:AngleAxis(act.t0 * 37, Vector3:New(0.3, 1, 0.2))
                end
            end
            show(rec, on)
        else
            local A = rec.act
            local inAct = (t >= A.t0 - 0.05) and (t <= A.t1 + 0.05)
            show(rec, inAct)
            if inAct then
                -- the pen: outlines first, then the scribble fills follow
                local reveal
                if rec.kind == "lines" then reveal = smooth((t - A.t0) / (DRAW * 0.7))
                else reveal = smooth((t - A.t0 - DRAW * 0.35) / (DRAW * 0.65)) end
                local tr = A.t0 + DRAW + A.hold
                local release = smooth((t - tr) / (A.t1 - tr))
                -- dissolving like ink in water: it spreads, turns, thins and retracts
                L:SetShaderClipping(release * 0.9, 1 - reveal)
                L:SetShaderFloat("_Dissolve", 1 - release)
                L.scale = 1 + 0.6 * release
                local ax = (A.axis == "fwd") and Vector3:New(FWD[1], FWD[2], FWD[3]) or Vector3:New(0, 1, 0)
                local rot = Rotation:AngleAxis(A.spin * (t - A.t0) - 25 * release, ax)
                if A.tilt then rot = Rotation:AngleAxis(A.tilt, tiltAxis):Multiply(rot) end
                L.rotation = rot
            end
        end
    end
end

-- ---------- the plugin ----------
function Start()
    placed = false
    layers = {}
    startTime = App.time
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
    local dist = (1.0 + 1.4 * Parameters.size) * S_UNITS
    C = {p.x - FWD[1] * dist, p.y + 0.15 * S_UNITS, p.z - FWD[3] * dist}
    build()
    placed = true
    clock0 = App.time - 68.2 / Parameters.speed
    App:Error("Kumma Ink: ready (" .. #layers .. " layers)")
end

function Main()
    if not placed then
        if Brush.triggerPressedThisFrame or (App.time - startTime > 3) then place() end
        return
    end
    local t = ((App.time - clock0) * Parameters.speed) % LOOP
    animate(t)
end

function End()
    for _, rec in ipairs(layers) do rec.layer:Delete() end
    layers = {}
    placed = false
    if saved.type then
        Brush.type = saved.type
        Brush.size = saved.size
        Brush.colorRgb = saved.color
    end
end
