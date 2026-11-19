-- Organic Kumma for Open Brush (Background Plugin).
-- A living, irregular mass made of the kumma's inks: a glowing heart, soft lobes of matter that grow ragged and
-- dark toward the edges, splash trails flung outward, drops of ink flying off and coming back, and tiny shards of the
-- kumma's stars and pearls dissolved inside. Nothing is symmetric and nothing repeats: the mass breathes, ripples,
-- turns around a wandering axis, bursts and gathers at irregular moments.
--
-- Built only on what is safe in every recent Open Brush: it draws everything once (a few strokes per frame) and then
-- only moves, turns and scales layers. All the matter is made of Hull-brush volumes.
-- If something goes wrong, the reason is shown on the back of your brush controller.
--
-- How to use: Extras > Plugins and Scripts > Background: pick OrganicKumma, press the eye button, then the big
-- button of the row. Point your hand forward and wait 3 seconds (or press the trigger).

Settings = {
    description = "Organic Kumma: an irregular living mass made of the kumma's inks",
    space = "canvas"
}

Parameters = {
    size = {label = "Size", type = "float", min = 0.2, max = 2, default = 1.05},
    distance = {label = "Distance (m)", type = "float", min = 0.8, max = 5, default = 2.4},
    speed = {label = "Speed", type = "float", min = 0.3, max = 2, default = 1},
    density = {label = "Density", type = "int", min = 1, max = 3, default = 2},
    look = {label = "Look 1 glossy 2 soft 3 glow", type = "int", min = 1, max = 3, default = 1},
    lights = {label = "Set the lights 0 no 1 yes", type = "int", min = 0, max = 1, default = 1},
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



-- ---------- colors: the kumma's inks, from a glowing heart to dark ink at the edges ----------
local COL = {
    core1 = "#EEF7FF", core2 = "#A9DDFF", core3 = "#CFBDF6",
    pink = "#EE5DB4", magenta = "#D81E8C", rose = "#F08CC8", lav = "#A06BE6",
    purple = "#7A35D6", violet = "#4E2096", blue = "#3F7FEA", sky = "#7FC8F5",
    ink1 = "#2A1036", ink2 = "#3A1A66", ink3 = "#5A1F4F", green = "#3FB55A",
}
local function pick(t) return t[1 + Math:Floor(Random.value * #t)] end
local function rnd(a, b) return a + (b - a) * Random.value end
local function randDir(skew)
    local d
    repeat d = {rnd(-1, 1), rnd(-1, 1), rnd(-1, 1)} until d[1] * d[1] + d[2] * d[2] + d[3] * d[3] <= 1
    d = {d[1] + skew[1], d[2] * 0.85 + skew[2], d[3] * 0.55 + skew[3]}   -- flatter toward you, heavier on one side
    return norm(d)
end

-- an irregular pebble: noisy points around an ellipsoid; a Hull brush wraps them in a soft organic volume
local function pebble(c, r, stretchDir, stretch)
    local pts = {}
    local ax = {rnd(0.7, 1.25), rnd(0.65, 1.2), rnd(0.6, 1.1)}
    local ph = {rnd(0, TAU), rnd(0, TAU), rnd(0, TAU)}
    local n = 30
    local ga = Math.pi * (3 - Math:Sqrt(5))
    for i = 0, n - 1 do
        local y = 1 - 2 * (i + 0.5) / n
        local rr = Math:Sqrt(1 - y * y)
        local a = ga * i
        local v = {rr * Math:Cos(a), y, rr * Math:Sin(a)}
        local bump = 1 + 0.22 * Math:Sin(3 * v[1] + ph[1]) * Math:Sin(2 * v[2] + ph[2]) + 0.12 * Math:Sin(4 * v[3] + ph[3])
        local p = {v[1] * ax[1] * r * bump, v[2] * ax[2] * r * bump, v[3] * ax[3] * r * bump}
        if stretchDir then                                   -- pulled outward like a drop of paint in flight
            local along = p[1] * stretchDir[1] + p[2] * stretchDir[2] + p[3] * stretchDir[3]
            if along > 0 then p = add(p, mul(stretchDir, along * stretch)) end
        end
        pts[#pts + 1] = add(c, p)
    end
    return pts
end

-- (kept for reference) a smear: a soft tube that swells and thins out
local function smear(d, r0, r1, curve)
    local pts, pr = {}, {}
    local side = norm(cross(d, {0, 0, 1}))
    if side[1] * side[1] + side[2] * side[2] + side[3] * side[3] < 0.1 then side = {1, 0, 0} end
    local w1, w2 = rnd(-1, 1) * curve, rnd(-1, 1) * curve * 0.5
    local N = 16
    for i = 0, N do
        local u = i / N
        local r = r0 + (r1 - r0) * u
        local bend = w1 * u * u + w2 * Math:Sin(Math.pi * u)
        pts[#pts + 1] = add(mul(d, r), mul(side, bend))
        pr[#pr + 1] = (0.35 + 0.65 * Math:Sin(Math.pi * (0.15 + 0.85 * (1 - u)) * 0.5)) * (1 - u) ^ 0.6 + 0.04 * Math:Sin(u * 17)
    end
    return pts, pr
end

-- tiny shards of the kumma, dissolved in the mass: a khatam made of two square slabs, and pearls
local function khatamShard(c, r)
    local a, b = {1, 0, 0}, {0, 1, 0}
    local out = {}
    for _, rot in ipairs({0, Math.pi / 4}) do
        local pts = {}
        for _, s in ipairs({{1, 1}, {1, -1}, {-1, -1}, {-1, 1}}) do
            local x = s[1] * r * Math:Cos(rot) - s[2] * r * Math:Sin(rot)
            local y = s[1] * r * Math:Sin(rot) + s[2] * r * Math:Cos(rot)
            pts[#pts + 1] = add(c, {x, y, r * 0.25}); pts[#pts + 1] = add(c, {x, y, -r * 0.25})
        end
        pts[#pts + 1] = add(c, {0, 0, r * 0.6})
        out[#out + 1] = pts
    end
    return out
end

-- ---------- the mass: a heart, lobes, smears, flying ink and dissolved shards ----------
local SKEW = {-0.35, 0.22, 0}                                 -- the mass leans up and to one side, never symmetric
local function centerOf(pts)
    local s = {0, 0, 0}
    for _, p in ipairs(pts) do s = add(s, p) end
    return mul(s, 1 / #pts)
end

local function buildParts()
    local HULL, SOFT, TUBE = brushes()
    local GLOW = (Parameters.look == 2) and "Matte Hull" or "Unlit Hull"
    local d = Parameters.density
    -- the heart: a bright, glowing knot
    part("heart", function()
        local j = {}
        for i = 1, 14 + 4 * d do
            local p = mul(randDir({0, 0, 0}), rnd(0, 0.2))
            j[#j + 1] = J(pebble(p, rnd(0.05, 0.11)), GLOW, 0.012, pick({COL.core1, COL.core2, COL.core3, COL.core1, COL.rose}))
        end
        return j
    end, {home = {0, 0, 0}, swing = 0.02, spin = 9, wob = 14})
    -- lobes of soft matter, denser near the heart, ragged at the edges
    for i = 1, 22 + 3 * d do
        local dd = randDir(SKEW)
        local r = 0.22 + 1.15 * Random.value ^ 1.2
        local home = mul(dd, r)
        local far = (r - 0.22) / 1.15
        part("lobe", function()
            local j = {}
            local n = Math:Floor(5 + 4 * (1 - far) + 2 * d)
            for k = 1, n do
                local off = add(mul(randDir({0, 0, 0}), rnd(0.03, 0.2 + 0.1 * far)), mul(dd, rnd(-0.05, 0.22)))
                local rad = rnd(0.04, 0.12) * (1.25 - 0.75 * far)
                local col
                if far < 0.22 then col = pick({COL.core2, COL.rose, COL.sky, COL.core3})
                elseif far < 0.55 then col = pick({COL.pink, COL.magenta, COL.magenta, COL.lav, COL.purple})
                else col = pick({COL.purple, COL.violet, COL.magenta, COL.ink3, COL.ink2, COL.ink1}) end
                local brush = (k % 2 == 0) and HULL or SOFT
                j[#j + 1] = J(pebble(add(home, off), rad, dd, rnd(0.3, 1.2) * far), brush, 0.012, col)
            end
            return j
        end, {home = home, dirv = dd, far = far, swing = 0.05 + 0.08 * far, spin = rnd(-7, 7), wob = rnd(6, 15),
              axis = randDir({0, 0, 0}), ph = rnd(0, TAU), f = rnd(0.6, 1.4)})
    end
    -- splash trails: drops flung outward along curved paths, smaller and darker as they go
    for i = 1, 7 + d do
        local dd = randDir(SKEW)
        part("trail", function()
            local j = {}
            for k = 1, 3 + d do
                local dk = norm(add(dd, mul(randDir({0, 0, 0}), 0.4)))
                local side = norm(cross(dk, {rnd(-1, 1), rnd(-1, 1), 1}))
                local r0, r1 = rnd(0.3, 0.6), rnd(1.1, 1.9)
                local bendA = rnd(-0.25, 0.25)
                local n = 6 + Math:Floor(3 * Random.value)
                for m = 0, n - 1 do
                    local u = m / (n - 1)
                    local r = r0 + (r1 - r0) * u ^ 0.85
                    local c = add(mul(dk, r), mul(side, bendA * u * u))
                    local nxt = add(mul(dk, r + 0.05), mul(side, bendA * (u + 0.05) * (u + 0.05)))
                    local tg = norm(sub(nxt, c))
                    local col
                    if u < 0.3 then col = pick({COL.rose, COL.pink, COL.core3})
                    elseif u < 0.7 then col = pick({COL.magenta, COL.lav, COL.purple})
                    else col = pick({COL.violet, COL.ink3, COL.ink2}) end
                    j[#j + 1] = J(pebble(c, 0.065 * (1 - 0.8 * u) + 0.008, tg, rnd(0.6, 1.5)), (m % 2 == 0) and HULL or SOFT, 0.01, col)
                end
            end
            return j
        end, {home = mul(dd, 0.85), dirv = dd, far = 0.8, swing = 0.05, spin = rnd(-3, 3), wob = rnd(4, 9),
              axis = randDir({0, 0, 0}), ph = rnd(0, TAU), f = rnd(0.7, 1.3)})
    end
    -- ink thrown off the edges, flying outward and coming back
    for i = 1, 5 + d do
        local dd = randDir(SKEW)
        part("ink", function()
            local j = {}
            for k = 1, 9 + 3 * d do
                local dk = norm(add(dd, mul(randDir({0, 0, 0}), 0.5)))
                local p = mul(dk, rnd(1.0, 1.7))
                local col = (Random.value < 0.6) and pick({COL.ink1, COL.ink2, COL.ink3}) or pick({COL.magenta, COL.core1, COL.purple})
                j[#j + 1] = J(pebble(p, rnd(0.012, 0.045), dk, rnd(0.5, 2.5)), HULL, 0.006, col)
            end
            return j
        end, {home = mul(dd, 1.3), dirv = dd, far = 1, period = rnd(5, 9), ph = Random.value, axis = randDir({0, 0, 0}), wob = rnd(10, 30)})
    end
    -- shards of the kumma, half hidden in the matter
    for i = 1, 2 do
        part("shard", function()
            local j = {}
            for k = 1, 4 do
                local c = mul(randDir(SKEW), rnd(0.3, 0.85))
                for _, s in ipairs(khatamShard(c, rnd(0.035, 0.06))) do j[#j + 1] = J(s, HULL, 0.004, pick({COL.blue, COL.sky})) end
            end
            for k = 1, 6 do
                j[#j + 1] = J(pebble(mul(randDir(SKEW), rnd(0.3, 0.95)), rnd(0.02, 0.03)), HULL, 0.004, pick({COL.core1, COL.rose, COL.green}))
            end
            return j
        end, {home = {0, 0, 0}, dirv = {0, 1, 0}, far = 0.5, swing = 0.03, spin = (i == 1) and 5 or -7, wob = 10,
              axis = randDir({0, 0, 0}), ph = rnd(0, TAU), f = 1})
    end
end

-- ---------- the motion: no fixed rhythm, no repeating cycle ----------
local function n3(T, a, b, c) return Math:Sin(T * a) * 0.55 + Math:Sin(T * b + 1.7) * 0.3 + Math:Sin(T * c + 4.1) * 0.15 end

local function animate(T)
    local grow = springy((T - 0.3) / 4.5)                      -- at the start the matter swells out of the heart
    -- the breath of the whole mass, and its rare, irregular bursts and contractions
    local breath = 1 + 0.05 * Math:Sin(T * 0.55) + 0.03 * Math:Sin(T * 0.91 + 1.3)
    local b = Math:Sin(T * 0.23) * Math:Sin(T * 0.37 + 0.7)
    local burst = 0
    if b > 0 then burst = b ^ 3 end
    local hold = 0
    if b < 0 then hold = (-b) ^ 3 end
    -- the whole mass turns slowly around an axis that keeps wandering
    local Qg = qMul(qAxis(FWD, 4.5 * T + 25 * Math:Sin(T * 0.05)),
                    qMul(qAxis(UPV, 22 * Math:Sin(T * 0.11)), qAxis(RIGHT, 14 * Math:Sin(T * 0.083 + 1))))
    local Sg = grow
    for _, rec in ipairs(recs) do
        if rec.ready then
            local k = rec.kind
            local q, s, home
            if k == "ink" then
                -- flying out from the edge, thinning out, and coming back from the heart
                local u = (T / rec.period + rec.ph) % 1
                local f = 0.55 + 0.75 * u + 0.4 * burst
                home = mul(rec.home, f - 1)
                s = (smooth(u / 0.12) * (1 - smooth((u - 0.72) / 0.28))) * (0.9 + 0.3 * burst)
                q = qAxis(rec.axis, rec.wob * Math:Sin(T * 0.7 + rec.ph * 6))
            else
                local wave = Math:Sin(T * 0.8 * (rec.f or 1) - (rec.far or 0) * 3 + (rec.ph or 0))   -- a ripple through the mass
                local f = breath * (1 + 0.07 * wave) + (0.35 * burst - 0.18 * hold) * (rec.far or 0)
                local o = {rec.swing * n3(T, 0.31 * (rec.f or 1), 0.53, 0.97), rec.swing * n3(T + 7, 0.27, 0.61 * (rec.f or 1), 1.13),
                           rec.swing * 0.6 * n3(T + 13, 0.35, 0.49, 0.83)}
                home = add(mul(rec.home, f - 1), o)
                local ax = rec.axis or {0, 0, 1}
                q = qMul(qAxis({0, 0, 1}, (rec.spin or 0) * T), qAxis(ax, (rec.wob or 10) * n3(T + (rec.ph or 0), 0.41, 0.67, 1.21)))
                s = 1 + 0.12 * n3(T + 3 * (rec.ph or 0), 0.73, 1.07, 1.61) + 0.18 * burst * (rec.far or 0)
                if k == "heart" then s = 1 + 0.12 * Math:Sin(T * 1.7) + 0.4 * burst - 0.1 * hold end
            end
            -- this part's own place: its content center, pushed by the breath, moved by the noise, carried by the whole
            if not rec.cLocal then                                -- its content center, back in the work's frame
                local w = mul(sub(rec.center, C), 1 / S_UNITS)
                rec.cLocal = {w[1] * RIGHT[1] + w[2] * RIGHT[2] + w[3] * RIGHT[3], w[1] * UPV[1] + w[2] * UPV[2] + w[3] * UPV[3],
                              w[1] * FWD[1] + w[2] * FWD[2] + w[3] * FWD[3]}
            end
            local tgtLocal = add(rec.cLocal, home)
            local target = add(C, mul(qRot(Qg, mul(dir(tgtLocal), S_UNITS)), Sg))
            local P = rec.center
            local v = dir({q[1], q[2], q[3]})
            pose(rec, qMul(Qg, {v[1], v[2], v[3], q[4]}), Sg * s, P, target)
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
    App:Error("Organic Kumma: growing...")
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
            App:Error("Organic Kumma: alive (" .. #recs .. " layers, " .. stats.strokes .. " strokes)")
            if useDWB == false and saved.type then
                Brush.type = saved.type
                pcall(function() Brush.sizeAbsolute = saved.size end)
                Brush.colorRgb = saved.color
            end
        end
        local d = dt
        if d > 0.1 then d = 0.1 end
        clockT = clockT + d * Parameters.speed
        animate(clockT)
    end
end

function Start()
    placed, reported, announcedReady = false, false, false
    recs, queue = {}, {}
    stats = {strokes = 0, points = 0}
    startTime = App.time
    lastTime = App.time
    clockT = 0
    App:Error("Organic Kumma: on. Point forward and wait 3 seconds")
end

function Main()
    local ok, err = pcall(step)
    if not ok and not reported then
        reported = true
        App:Error("Organic Kumma error: " .. tostring(err))
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

