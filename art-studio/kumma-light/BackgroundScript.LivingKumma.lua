-- Living Kumma for Open Brush (Background Plugin).
-- The Omani kumma's motifs as one living 3D flower: fleshy petals of the great rosette, inner petals and leaves,
-- a pistil of pearls, a ring of pearls and a crown of triangles, and four stems that curl outward carrying leaves,
-- berries, eight-pointed gem stars and small blooms (the medallions). It grows from a seed, blooms, breathes and
-- sways, closes again and sinks back into the seed, then grows again (a 57-second loop).
--
-- Built only on what is safe in every recent Open Brush: it draws everything once (a few strokes per frame) and then
-- only moves, turns and scales layers. Volumes come from Hull brushes and soft tubes from the Lofted brush.
-- If something goes wrong, the reason is shown on the back of your brush controller.
--
-- How to use: Extras > Plugins and Scripts > Background: pick LivingKumma, press the eye button, then the big
-- button of the row. Point your hand forward and wait 3 seconds (or press the trigger).

Settings = {
    description = "Living Kumma: the Omani kumma's motifs as a living 3D flower that grows, blooms and sways",
    space = "canvas"
}

Parameters = {
    size = {label = "Size", type = "float", min = 0.2, max = 2, default = 0.95},
    distance = {label = "Distance (m)", type = "float", min = 0.8, max = 5, default = 2.4},
    speed = {label = "Speed", type = "float", min = 0.4, max = 2, default = 1},
    look = {label = "Look 1 glossy 2 soft 3 glow", type = "int", min = 1, max = 3, default = 1},
    lights = {label = "Set the lights 0 no 1 yes", type = "int", min = 0, max = 1, default = 1},
}

local UNITS = 10
local TAU = 2 * Math.pi
local LOOP = 57

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

-- ---------- colors (from the drawing) ----------
local COL = {
    magenta = "#E0359A", pink = "#F07CC4", vein = "#A3226F", vein2 = "#C9408F", purple = "#8A4BE0", navy = "#4A49C0", blue = "#4D8EF0",
    sky = "#8FD0F7", red = "#D0405F", green = "#3FB55A", lime = "#A6E25E", gold = "#F2C94C",
}

-- ---------- shapes as point clouds (Hull brushes wrap them in a smooth volume) ----------
local function sphere(c, r, n)
    local pts = {}
    n = n or 14
    local ga = Math.pi * (3 - Math:Sqrt(5))
    for i = 0, n - 1 do
        local y = 1 - 2 * (i + 0.5) / n
        local rr = Math:Sqrt(1 - y * y)
        local a = ga * i
        pts[#pts + 1] = {c[1] + r * rr * Math:Cos(a), c[2] + r * y, c[3] + r * rr * Math:Sin(a)}
    end
    return pts
end
-- a fleshy petal (or leaf) along angle a: from radius r0 to r1, width w, cupped toward the viewer, thickness th
local function petal(a, r0, r1, w, cup, th, z0)
    local pts = {}
    local ca, sa = Math:Cos(a), Math:Sin(a)
    for i = 0, 10 do
        local u = i / 10
        local d = r0 + (r1 - r0) * u
        local wid = w * Math:Sin(Math.pi * (0.06 + 0.94 * u)) ^ 0.75
        for _, v in ipairs({-1, -0.5, 0, 0.5, 1}) do
            local o = v * wid
            local z = (z0 or 0) + cup * u * u + 0.35 * cup * (1 - v * v) * Math:Sin(Math.pi * u)
            local x, y = d * ca - o * sa, d * sa + o * ca
            pts[#pts + 1] = {x, y, z + th * Math:Sin(Math.pi * u) * (1 - 0.6 * v * v)}
            pts[#pts + 1] = {x, y, z - th * 0.6 * Math:Sin(Math.pi * u) * (1 - 0.6 * v * v)}
        end
    end
    return pts
end
-- the vein along a petal's middle, riding on its front surface
local function vein(a, r0, r1, cup, z0)
    local pts = {}
    local ca, sa = Math:Cos(a), Math:Sin(a)
    for i = 0, 12 do
        local u = i / 12
        local d = r0 + (r1 - r0) * u
        local uu = (d - r0) / (r1 - r0)
        pts[#pts + 1] = {d * ca, d * sa, z0 + cup * uu * uu + 0.35 * cup * Math:Sin(Math.pi * uu) + 0.03 * Math:Sin(Math.pi * uu)}
    end
    return pts
end
local function veinPr()
    local p = {}
    for i = 0, 12 do p[#p + 1] = 0.35 + 0.65 * Math:Sin(Math.pi * i / 12) end
    return p
end
-- a square slab (two of them, turned 45 degrees, make an eight-pointed khatam star)
local function slab(c, half, rot, th, axisA, axisB, normal)
    local pts = {}
    for _, s in ipairs({{1, 1}, {1, -1}, {-1, -1}, {-1, 1}}) do
        local x = s[1] * half * Math:Cos(rot) - s[2] * half * Math:Sin(rot)
        local y = s[1] * half * Math:Sin(rot) + s[2] * half * Math:Cos(rot)
        for _, z in ipairs({-th, th}) do
            pts[#pts + 1] = add(c, add(add(mul(axisA, x), mul(axisB, y)), mul(normal, z)))
        end
    end
    pts[#pts + 1] = add(c, mul(normal, th * 2.2))      -- a gem's raised center
    pts[#pts + 1] = add(c, mul(normal, -th * 1.6))
    return pts
end
local function prism(corners, th, normal)
    local pts = {}
    for _, p in ipairs(corners) do
        pts[#pts + 1] = add(p, mul(normal, th))
        pts[#pts + 1] = add(p, mul(normal, -th))
    end
    return pts
end

-- ---------- drawing: once, a few strokes per frame ----------
local useDWB = nil
local saved = {}
local VIEWROT = nil
local stats = {strokes = 0, points = 0}
local function brushes()
    local look = Parameters.look
    if look == 2 then return "Matte Hull", "Matte Hull", "Lofted" end
    if look == 3 then return "Unlit Hull", "Unlit Hull", "Faceted Tube" end
    return "Shiny Hull", "Matte Hull", "Lofted"
end

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

local function buildParts()
    local HULL, SOFT, TUBE = brushes()
    -- the pistil: a cluster of pearls at the heart (first, so a seed appears right away)
    part("pistil", function()
        local j = {J(sphere({0, 0, 0.05}, 0.07, 18), HULL, 0.012, COL.lime)}
        for k = 0, 5 do
            local a = k * TAU / 6
            j[#j + 1] = J(sphere({0.085 * Math:Cos(a), 0.085 * Math:Sin(a), 0.03}, 0.045, 12), HULL, 0.01, (k % 2 == 0) and COL.green or COL.gold)
        end
        for k = 0, 7 do
            local a = k * TAU / 8 + 0.2
            j[#j + 1] = J(sphere({0.16 * Math:Cos(a), 0.16 * Math:Sin(a), 0.0}, 0.03, 10), HULL, 0.008, COL.magenta)
        end
        return j
    end, {pivot = {0, 0, 0}})
    -- the leaves behind the flower (one layer)
    part("sepals", function()
        local j = {}
        for k = 0, 7 do
            local a = k * TAU / 8 + Math.pi / 2 + Math.pi / 8
            j[#j + 1] = J(petal(a, 0.2, 1.12, 0.13, 0.05, 0.025, -0.12), SOFT, 0.012, (k % 2 == 0) and COL.green or COL.lime)
        end
        return j
    end, {pivot = {0, 0, 0}})
    -- the great petals of the rosette, each hinged at its base
    for k = 0, 7 do
        local a = k * TAU / 8 + Math.pi / 2
        part("petal", function()
            return {J(petal(a, 0.12, 0.98, 0.21, 0.16, 0.03, 0), HULL, 0.014, COL.magenta), J(vein(a, 0.16, 0.86, 0.16, 0.035), TUBE, 0.022, COL.vein, veinPr())}
        end,
             {pivot = {0.12 * Math:Cos(a), 0.12 * Math:Sin(a), 0}, hinge = {-Math:Sin(a), Math:Cos(a), 0}, k = k, closed = 78})
    end
    for k = 0, 7 do
        local a = k * TAU / 8 + Math.pi / 2 + Math.pi / 8
        part("inner", function()
            return {J(petal(a, 0.1, 0.6, 0.12, 0.2, 0.025, 0.05), HULL, 0.012, COL.pink), J(vein(a, 0.13, 0.52, 0.2, 0.085), TUBE, 0.016, COL.vein2, veinPr())}
        end,
             {pivot = {0.1 * Math:Cos(a), 0.1 * Math:Sin(a), 0.05}, hinge = {-Math:Sin(a), Math:Cos(a), 0}, k = k, closed = 85})
    end
    -- a ring of pearls and a crown of triangles (the bands of the kumma)
    part("pearls", function()
        local j = {}
        for k = 0, 27 do
            local a = k * TAU / 28
            j[#j + 1] = J(sphere({1.24 * Math:Cos(a), 1.24 * Math:Sin(a), -0.04}, 0.062, 14), HULL, 0.01, (k % 2 == 0) and COL.pink or COL.sky)
        end
        return j
    end, {pivot = {0, 0, 0}, spin = 7})
    part("crown", function()
        local j = {}
        for k = 0, 23 do
            local a0, a1 = k * TAU / 24 + 0.03, (k + 1) * TAU / 24 - 0.03
            local am = (a0 + a1) / 2
            local r0, r1 = 1.36, 1.6
            local tri = {{r0 * Math:Cos(a0), r0 * Math:Sin(a0), -0.06}, {r1 * Math:Cos(am), r1 * Math:Sin(am), 0.02},
                         {r0 * Math:Cos(a1), r0 * Math:Sin(a1), -0.06}}
            j[#j + 1] = J(prism(tri, 0.02, {0, 0, 1}), HULL, 0.008, (k % 2 == 0) and COL.purple or COL.red)
        end
        return j
    end, {pivot = {0, 0, 0}, spin = -5})
    -- four stems curling outward, each in three segments that bend like a living plant
    for s = 0, 3 do
        local base = Math.pi / 4 + s * Math.pi / 2
        local N = 36
        local line = {}
        for i = 0, N do
            local u = i / N
            local a = base + 0.9 * u + 0.9 * u ^ 3
            local r = 0.55 + 1.35 * u
            line[#line + 1] = {r * Math:Cos(a), r * Math:Sin(a), -0.18 + 0.32 * Math:Sin(Math.pi * u)}
        end
        for g = 0, 2 do
            local i0, i1 = g * 12, g * 12 + 12
            local seg = {}
            local prs = {}
            for i = i0, i1 do
                seg[#seg + 1] = line[i + 1]
                local u = i / N
                prs[#prs + 1] = 1 - 0.72 * u
            end
            local joint = line[i0 + 1]
            part("stem", function()
                local j = {J(seg, TUBE, 0.11, COL.green, prs)}
                j[#j + 1] = J(sphere(joint, 0.05 * (1 - 0.45 * g / 2), 10), SOFT, 0.008, COL.green)     -- a knuckle hides the joint
                local mid = line[i0 + 7]
                local nxt = line[i0 + 8]
                local tng = norm(sub(nxt, mid))
                local side = norm(cross(tng, {0, 0, 1}))
                if g == 0 or g == 2 then                                                   -- leaves
                    for _, sg in ipairs({1, -1}) do
                        local tipp = add(mid, add(mul(side, 0.3 * sg), mul(tng, 0.14)))
                        local la = Math:Atan2(tipp[2] - mid[2], tipp[1] - mid[1])
                        local lp = petal(la, 0, 0.33, 0.095, 0.06, 0.018, 0)
                        for _, q in ipairs(lp) do q[1] = q[1] + mid[1]; q[2] = q[2] + mid[2]; q[3] = q[3] + mid[3] end
                        j[#j + 1] = J(lp, SOFT, 0.008, (sg > 0) and COL.lime or COL.green)
                    end
                end
                if g == 1 then                                                             -- berries and a gem star
                    local bc = add(mid, mul(side, 0.12))
                    for _, o in ipairs({{-0.035, 0, 0}, {0.035, 0, 0}, {0, 0.05, 0.01}, {0, -0.02, 0.04}}) do
                        j[#j + 1] = J(sphere(add(bc, o), 0.032, 10), HULL, 0.008, COL.magenta)
                    end
                    local gc = add(mid, mul(side, -0.16))
                    j[#j + 1] = J(slab(gc, 0.075, 0, 0.018, {1, 0, 0}, {0, 1, 0}, {0, 0, 1}), HULL, 0.006, COL.blue)
                    j[#j + 1] = J(slab(gc, 0.075, Math.pi / 4, 0.018, {1, 0, 0}, {0, 1, 0}, {0, 0, 1}), HULL, 0.006, COL.sky)
                end
                if g == 2 then                                                             -- a small bloom: the medallion
                    local tip = line[N + 1]
                    j[#j + 1] = J(sphere(tip, 0.055, 14), HULL, 0.01, COL.magenta)
                    for k = 0, 7 do
                        local a = k * TAU / 8
                        local pp = petal(a, 0.05, 0.25, 0.07, 0.06, 0.015, 0)
                        for _, q in ipairs(pp) do q[1] = q[1] + tip[1]; q[2] = q[2] + tip[2]; q[3] = q[3] + tip[3] end
                        j[#j + 1] = J(pp, HULL, 0.008, (k % 2 == 0) and COL.purple or COL.navy)
                    end
                    local ring = {}
                    local rp = {}
                    for k = 0, 24 do
                        local a = k * TAU / 24
                        ring[#ring + 1] = {tip[1] + 0.29 * Math:Cos(a), tip[2] + 0.29 * Math:Sin(a), tip[3] - 0.02}
                        rp[#rp + 1] = 0.8
                    end
                    j[#j + 1] = J(ring, TUBE, 0.03, COL.lime, rp)
                end
                return j
            end, {stem = s, seg = g, pivot = joint, next = line[i1 + 1]})
        end
    end
end

-- ---------- turning a layer (Open Brush turns and scales it around its pivot, set by CenterPivot) ----------
-- show the layer's content turned by q (around point P) and scaled by s, with P moved to target (all canvas)
local function pose(rec, q, s, P, target)
    local L = rec.layer
    local c = rec.center
    local pos = add(target, mul(qRot(q, sub(c, P)), s))
    L.position = Vector3:New(rec.base[1] + pos[1] - c[1], rec.base[2] + pos[2] - c[2], rec.base[3] + pos[3] - c[3])
    local w = q[4]
    if w < 0 then q = {-q[1], -q[2], -q[3], -w}; w = -w end
    if w > 1 then w = 1 end
    local half = Math:Acos(w)
    local sn = Math:Sin(half)
    if sn < 1e-5 then L.rotation = Rotation:AngleAxis(0, Vector3:New(0, 1, 0))
    else L.rotation = Rotation:AngleAxis(2 * half * 180 / Math.pi, Vector3:New(q[1] / sn, q[2] / sn, q[3] / sn)) end
    if s < 0.002 then s = 0.002 end
    L.scale = s
end

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
            rec.layer:Show()
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

-- ---------- life: the timeline ----------
local function life(t)
    local L = {}
    L.grow = springy((t - 0.3) / 3.5)                      -- the seed grows into the plant
    L.bloom = smooth((t - 3.5) / 6.5)                       -- the petals open
    L.close = smooth((t - 41) / 7)                          -- they close again
    L.sink = smooth((t - 48) / 6)                           -- and everything sinks into the seed
    L.open = L.bloom * (1 - L.close)
    L.size = L.grow * (1 - 0.96 * L.sink)
    L.breath = 1 + 0.025 * Math:Sin(t * 1.3)
    return L
end

local function animate(t, T)
    local L = life(t)
    -- the whole flower: a slow turn, a gentle tilt sway, breathing
    local Qf = qMul(qAxis(UPV, 7 * Math:Sin(T * 0.21)), qMul(qAxis(RIGHT, 5 * Math:Sin(T * 0.17)), qAxis(FWD, 4 * T)))
    local Sf = L.size * L.breath
    local function place(local_point) return add(C, mul(qRot(Qf, mul(dir(local_point), S_UNITS)), Sf)) end
    local stemFrames = {}
    for _, rec in ipairs(recs) do
        if rec.ready then
            local k = rec.kind
            if k == "pistil" then
                local pulse = 1 + 0.08 * Math:Sin(T * 2.6) + 0.6 * L.sink
                local seed = Math:Max(Sf, 0.38 * L.sink + 0.3 * (1 - L.grow) + 0.05)   -- a visible, pulsing seed pod
                pose(rec, qMul(Qf, qAxis(FWD, 20 * T)), seed * pulse, canvas({0, 0, 0}), C)
            elseif k == "sepals" then
                local s = Sf * (0.25 + 0.75 * smooth((t - 1) / 3))
                pose(rec, qMul(Qf, qAxis(FWD, -3 * T)), s, canvas({0, 0, 0}), C)
            elseif k == "petal" or k == "inner" then
                -- each petal opens on its hinge; a wave runs around the flower; it flutters a little
                local delay = (k == "inner") and 0.12 or 0
                local o = smooth((L.bloom - delay - 0.03 * rec.k) / (1 - delay - 0.03 * 7)) * (1 - L.close)
                local flutter = 6 * Math:Sin(T * 1.7 - rec.k * TAU / 8) * o
                local ang = rec.closed * (1 - o) + flutter - 8 * o
                local hingeW = dir(rec.hinge)
                local q = qMul(Qf, qAxis(hingeW, -ang))
                local grow = Sf * (0.35 + 0.65 * smooth((t - 2.5 - 0.1 * rec.k) / 2))
                pose(rec, q, grow, canvas(rec.pivot), place(rec.pivot))
            elseif k == "pearls" or k == "crown" then
                local appear = smooth((t - 6 - ((k == "crown") and 1.5 or 0)) / 3) * (1 - L.close * 0.6)
                pose(rec, qMul(Qf, qAxis(FWD, rec.spin * T)), Sf * (0.6 + 0.4 * appear) * appear + 0.001, canvas({0, 0, 0}), C)
            elseif k == "stem" then
                -- forward kinematics: each segment bends from the joint at its base, carried by the one before
                local prev = stemFrames[rec.stem]
                local baseLocal, Qp
                if rec.seg == 0 or not prev then baseLocal = rec.pivot; Qp = Q0
                else baseLocal = prev.tipPos; Qp = prev.q end
                local sway = (5 + 5 * rec.seg) * Math:Sin(T * 0.9 - rec.seg * 0.9 + rec.stem * 1.6)
                local curl = 38 * L.close + 55 * (1 - L.grow) - 12 * L.open
                local bend = qAxis({0, 0, 1}, sway + curl * (0.6 + 0.4 * rec.seg))
                local Qk = qMul(Qp, bend)
                local g = smooth((t - 0.8 - 0.9 * rec.seg - 0.25 * rec.stem) / 1.6)
                local segS = 0.05 + 0.95 * g
                local tipLocal = add(baseLocal, mul(qRot(Qk, sub(rec.next, rec.pivot)), segS))
                stemFrames[rec.stem] = {tipPos = tipLocal, q = Qk}
                local v = dir({Qk[1], Qk[2], Qk[3]})                -- the bend, from the work's frame to the canvas
                local qW = qMul(Qf, {v[1], v[2], v[3], Qk[4]})
                pose(rec, qW, Sf * segS, canvas(rec.pivot), place(baseLocal))
            end
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
    App:Error("Living Kumma: growing...")
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
    -- the clock only starts once the whole plant is drawn (a few seconds the first time)
    if #queue == 0 then
        if not announcedReady then
            announcedReady = true
            App:Error("Living Kumma: alive (" .. #recs .. " layers, " .. stats.strokes .. " strokes)")
            if useDWB == false and saved.type then
                Brush.type = saved.type
                pcall(function() Brush.sizeAbsolute = saved.size end)
                Brush.colorRgb = saved.color
            end
        end
        local d = dt
        if d > 0.1 then d = 0.1 end
        clockT = clockT + d * Parameters.speed
        animate(clockT % LOOP, clockT)
    end
end

function Start()
    placed, reported, announcedReady = false, false, false
    recs, queue = {}, {}
    stats = {strokes = 0, points = 0}
    startTime = App.time
    lastTime = App.time
    clockT = 0
    App:Error("Living Kumma: on. Point forward and wait 3 seconds")
end

function Main()
    local ok, err = pcall(step)
    if not ok and not reported then
        reported = true
        App:Error("Living Kumma error: " .. tostring(err))
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
