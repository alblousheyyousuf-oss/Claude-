-- Kumma Light for Open Brush (Background Plugin).
-- Draws a nebula of smoke and stars; the Omani kumma's symbols form in it as light
-- (eight-pointed star, medallions, bands, vine, rosette), then dissolve. At the end everything
-- is swallowed into a core and explodes again. A 72-second loop.
--
-- How to use: turn it on in Extras > Plugins and Scripts > Background (the eye button + the big
-- button of the row), then point your hand forward and press the trigger once: the work appears
-- 2.5 meters in front of you. Turning it off removes its layers.

Settings = {
    description = "Kumma Light: Omani kumma symbols forming from a living nebula of smoke and stars",
    space = "canvas"
}

Parameters = {
    size = {label = "Size", type = "float", min = 0.3, max = 3, default = 1},
    speed = {label = "Speed", type = "float", min = 0.3, max = 2, default = 1},
    thickness = {label = "Thickness", type = "float", min = 0.2, max = 5, default = 1},
    density = {label = "Density", type = "int", min = 1, max = 3, default = 2},
}

local LOOP = 72
local UNITS = 10                -- 1 meter = 10 units in Open Brush
local TAU = 2 * Math.pi

-- ---------- state ----------
local placed = false
local C = {0, 0, 0}             -- center of the work (in canvas units)
local RIGHT, UPV, FWD = {1, 0, 0}, {0, 1, 0}, {0, 0, 1}   -- the work's frame (FWD toward the user)
local layers = {}               -- {layer=, base=Vector3, kind=, ...}
local clock0 = 0
local saved = {}

-- ---------- small vector helpers (plain Lua numbers) ----------
local function v3(x, y, z) return {x, y, z} end
local function norm(a)
    local l = Math:Sqrt(a[1] * a[1] + a[2] * a[2] + a[3] * a[3])
    if l < 1e-6 then return {0, 0, 1} end
    return {a[1] / l, a[2] / l, a[3] / l}
end
local function cross(a, b) return {a[2] * b[3] - a[3] * b[2], a[3] * b[1] - a[1] * b[3], a[1] * b[2] - a[2] * b[1]} end

-- a point in the work's frame (meters) -> a canvas position
local function world(p)
    local s = UNITS * Parameters.size
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

-- ---------- the kumma's colors ----------
local COL = {
    navy = "#3D3DD9", blue = "#4D94FF", sky = "#8CD9FF", red = "#F2385F", magenta = "#FF38A8",
    pink = "#FF85CC", purple = "#9E4DFF", green = "#4DD966", lime = "#9EF266", white = "#FFF0FA",
}

-- ---------- drawing ----------
local function densify(pts, closed, step)
    local out = {}
    local n = #pts
    local m = closed and n or n - 1
    for i = 1, m do
        local a, b = pts[i], pts[(i % n) + 1]
        local dx, dy, dz = b[1] - a[1], b[2] - a[2], b[3] - a[3]
        local L = Math:Sqrt(dx * dx + dy * dy + dz * dz)
        local k = Math:Max(1, Math:Ceil(L / step))
        for j = 0, k - 1 do
            table.insert(out, {a[1] + dx * j / k, a[2] + dy * j / k, a[3] + dz * j / k})
        end
    end
    if closed then table.insert(out, {pts[1][1], pts[1][2], pts[1][3]})
    else table.insert(out, pts[n]) end
    return out
end

local function stroke(pts, brush, size, color)
    if #pts < 2 then return end
    local list = {}
    for i = 1, #pts do table.insert(list, world(pts[i])) end
    Brush.type = brush
    Brush.size = size * Parameters.thickness
    Brush.colorRgb = Color:New(color)
    local path = Path:New(list)
    path:Draw()
end

-- a symbol path: a glowing tube (Neon Pulse) + sparkles of stars along it
local function symbolPath(pts, closed, color)
    local d = densify(pts, closed, 0.025)
    stroke(d, "Neon Pulse", 0.11, color)
    stroke(d, "Stars", 0.16, color)
end

-- ---------- the symbols (2D in the plane facing the user, or 3D rings around the vertical axis) ----------
local function circle(r, n, cx, cy)
    local t = {}
    for i = 0, n - 1 do
        local a = TAU * i / n
        table.insert(t, {(cx or 0) + r * Math:Cos(a), (cy or 0) + r * Math:Sin(a), 0})
    end
    return t
end
local function khatam(R)                 -- eight-pointed star (two squares): 16 points
    local r = R * Math:Cos(Math.pi / 4) / Math:Cos(Math.pi / 8)
    local t = {}
    for i = 0, 15 do
        local a = i * Math.pi / 8 + Math.pi / 2
        local rr = (i % 2 == 1) and r or R
        table.insert(t, {rr * Math:Cos(a), rr * Math:Sin(a), 0})
    end
    return t
end
local function lens(a, r0, r1, w, n)     -- a petal or leaf
    local t = {}
    n = n or 16
    for _, s in ipairs({1, -1}) do
        for i = 0, n do
            local u = (s > 0) and (i / n) or (1 - i / n)
            local d = r0 + (r1 - r0) * u
            local o = s * w * Math:Sin(Math.pi * u)
            table.insert(t, {d * Math:Cos(a) - o * Math:Sin(a), d * Math:Sin(a) + o * Math:Cos(a), 0})
        end
    end
    return t
end
local function rhombus(w, h, cx, cy)
    return {{cx, cy + h, 0}, {cx + w, cy, 0}, {cx, cy - h, 0}, {cx - w, cy, 0}}
end
local function moved(pts, dx, dy, dz, ry)      -- move (and turn around the vertical axis)
    local t = {}
    local c, s = Math:Cos(ry or 0), Math:Sin(ry or 0)
    for i = 1, #pts do
        local p = pts[i]
        table.insert(t, {p[1] * c + p[3] * s + dx, p[2] + dy, -p[1] * s + p[3] * c + dz})
    end
    return t
end

local function drawStar(R)
    symbolPath(khatam(R), true, COL.magenta)
    symbolPath(khatam(R * 0.84), true, COL.purple)
    local oct = {}
    for i = 0, 7 do
        local a = i * TAU / 8 + Math.pi / 8
        table.insert(oct, {R * 0.47 * Math:Cos(a), R * 0.47 * Math:Sin(a), 0})
    end
    symbolPath(oct, true, COL.blue)
    symbolPath(circle(R * 0.24, 40), true, COL.sky)
    symbolPath(circle(R * 0.07, 16), true, COL.white)
end

local function drawMedallion(R, dx, dy, dz, ry)
    symbolPath(moved(circle(R, 64), dx, dy, dz, ry), true, COL.green)
    symbolPath(moved(circle(R * 0.88, 64), dx, dy, dz, ry), true, COL.lime)
    for k = 0, 7 do
        symbolPath(moved(lens(k * TAU / 8 + Math.pi / 2, R * 0.14, R * 0.74, R * 0.13), dx, dy, dz, ry), true, COL.purple)
    end
    symbolPath(moved(khatam(R * 0.3), dx, dy, dz, ry), true, COL.blue)
    symbolPath(moved(circle(R * 0.08, 16), dx, dy, dz, ry), true, COL.magenta)
end

local function drawFlower(R)
    symbolPath(circle(R * 1.04, 128), true, COL.purple)
    symbolPath(circle(R * 0.13, 32), true, COL.lime)
    for k = 0, 7 do
        local a = k * TAU / 8 + Math.pi / 2
        symbolPath(lens(a, R * 0.14, R * 0.98, R * 0.17, 24), true, COL.magenta)
        symbolPath(lens(a, R * 0.22, R * 0.8, R * 0.07, 20), true, COL.pink)
        symbolPath(lens(a + Math.pi / 8, R * 0.18, R * 0.66, R * 0.07, 18), true, COL.green)
    end
    for k = 0, 7 do                       -- eight small stars around the rosette
        local a = k * TAU / 8 + Math.pi / 8
        local st = khatam(0.16)
        local cx, cy = 1.5 * Math:Cos(a), 1.5 * Math:Sin(a)
        local t = {}
        for i = 1, #st do table.insert(t, {st[i][1] + cx, st[i][2] + cy, 0}) end
        symbolPath(t, true, (k % 2 == 0) and COL.blue or COL.sky)
    end
end

local function ringPoint(R, a, y) return {R * Math:Sin(a), y, R * Math:Cos(a)} end
local function drawBands()
    local R, n = 1.05, 20
    for k = 0, n - 1 do                   -- the triangles (zigzag) around
        local a0, a1 = k * TAU / n, (k + 1) * TAU / n
        local tri = {ringPoint(R, a0, -0.16), ringPoint(R, (a0 + a1) / 2, 0.14), ringPoint(R, a1, -0.16)}
        symbolPath(tri, true, (k % 2 == 0) and COL.purple or COL.red)
    end
    for _, y in ipairs({0.33, -0.33}) do  -- two rings of beads
        for k = 0, 31 do
            local a = k * TAU / 32
            local c = {}
            for i = 0, 11 do
                local b = TAU * i / 12
                local q = {0.045 * Math:Cos(b), 0.045 * Math:Sin(b)}
                table.insert(c, {R * Math:Sin(a) + q[1] * Math:Cos(a), y + q[2], R * Math:Cos(a) - q[1] * Math:Sin(a)})
            end
            symbolPath(c, true, (k % 2 == 0) and COL.pink or COL.sky)
        end
    end
end

local function drawVine()
    local R, y0, y1, turns = 0.72, -0.95, 0.95, 2.5
    local pts = {}
    local n = 400
    for i = 0, n do
        local u = i / n
        local a = TAU * turns * u
        local w = 0.09 * Math:Sin(a * 6)
        table.insert(pts, {(R + w) * Math:Sin(a), y0 + (y1 - y0) * u, (R + w) * Math:Cos(a)})
    end
    symbolPath(pts, false, COL.green)
    local m = Math:Round(turns * 12)
    for j = 0, m - 1 do                   -- clusters of berries
        local u = (j + 0.25) / m
        local a = TAU * turns * u
        local y = y0 + (y1 - y0) * u
        local rr = R + ((j % 2 == 1) and -0.13 or 0.13)
        for _, off in ipairs({{-0.035, 0}, {0.035, 0}, {0, 0.055}}) do
            local c = {}
            for i = 0, 10 do
                local b = TAU * i / 11
                local qx, qy = 0.03 * Math:Cos(b) + off[1], 0.03 * Math:Sin(b) + off[2]
                table.insert(c, {rr * Math:Sin(a) + qx * Math:Cos(a), y + qy, rr * Math:Cos(a) - qx * Math:Sin(a)})
            end
            symbolPath(c, true, (j % 3 == 0) and COL.pink or COL.magenta)
        end
    end
end

-- ---------- the nebula: smoke along the lines of a chaotic stream (ABC flow) ----------
local function flow(p)
    local k = 2.2
    local x, y, z = p[1] * k, p[2] * k, p[3] * k
    local A, B, Cc = 1.0, 0.75, 0.6
    local vx = A * Math:Sin(z) + Cc * Math:Cos(y)
    local vy = B * Math:Sin(x) + A * Math:Cos(z)
    local vz = Cc * Math:Sin(y) + B * Math:Cos(x)
    return norm({vx - 0.7 * p[3], vy * 0.6, vz + 0.7 * p[1]})   -- plus a swirl around the vertical axis
end

local function fieldColor(p)
    local r2 = p[1] * p[1] + p[2] * p[2] + p[3] * p[3]
    if r2 < 0.04 then return (Random.value < 0.5) and COL.white or COL.sky end
    local n = Math:Sin(1.3 * p[1] + 0.4) * Math:Cos(1.1 * p[2] - 0.3) + 0.6 * Math:Sin(1.7 * p[3] + 1.2)
    if n < -0.6 then return COL.navy end
    if n < -0.15 then return COL.purple end
    if n < 0.3 then return COL.magenta end
    if n < 0.75 then return COL.pink end
    return COL.blue
end

local function randomSeed(rmax)
    local p
    repeat
        p = {Random.value * 2 - 1, Random.value * 2 - 1, Random.value * 2 - 1}
    until p[1] * p[1] + p[2] * p[2] + p[3] * p[3] <= 1
    local r = rmax * (0.2 + 0.8 * Random.value ^ 0.8)
    return {p[1] * r, p[2] * r * 0.75, p[3] * r}
end

local function streamline(seed, steps, h)
    local pts = {seed}
    local p = seed
    for i = 1, steps do
        local v = flow(p)
        p = {p[1] + v[1] * h, p[2] + v[2] * h, p[3] + v[3] * h}
        if p[1] * p[1] + p[2] * p[2] + p[3] * p[3] > 1.6 * 1.6 then break end
        table.insert(pts, p)
    end
    return pts
end

local function drawNebula(brush, count, size, steps)
    for i = 1, count do
        local s = randomSeed(1.3)
        local pts = streamline(s, steps, 0.04)
        stroke(pts, brush, size * (0.7 + 0.6 * Random.value), fieldColor(s))
    end
end

local function drawCore()
    for i = 1, 3 do
        stroke(streamline(randomSeed(0.12), 8, 0.02), "Smoke", 0.12, (i == 1) and COL.sky or COL.pink)
    end
    for i = 1, 14 do
        stroke(streamline(randomSeed(0.3), 12, 0.03), "Stars", 0.08, (i % 3 == 0) and COL.sky or COL.white)
    end
end

-- ---------- layers ----------
local function newLayer(kind, drawFn, extra)
    local L = Layer:New()
    Sketch.layers.active = L
    drawFn()
    L.allowStrokeAnimation = true
    L:CenterPivot()
    local rec = {layer = L, kind = kind, base = L.position, visible = true}
    if extra then for k, v in pairs(extra) do rec[k] = v end end
    table.insert(layers, rec)
    return rec
end

-- the symbols in time (seconds in the loop), as in the browser version
local ACTS = {
    {name = "star", t0 = 4, t1 = 11.5, hold = 3.2, axis = "fwd", spin = 7},
    {name = "medallions", t0 = 15, t1 = 22.5, hold = 3.2, axis = "up", spin = 13},
    {name = "bands", t0 = 26, t1 = 33.5, hold = 3.2, axis = "up", spin = 17, tilt = 24},
    {name = "vine", t0 = 37, t1 = 44.5, hold = 3.2, axis = "up", spin = -20},
    {name = "flower", t0 = 50, t1 = 60.5, hold = 5.0, axis = "fwd", spin = 4},
}

local function build()
    saved = {type = Brush.type, size = Brush.size, color = Brush.colorRgb}
    local d = Parameters.density
    -- each layer turns around its own tilted axis, at its own speed (whole turns per loop -> seamless)
    newLayer("smoke", function() drawNebula("Smoke", 9 * d, 0.3, 26) end, {turns = 1, wob = 9, axis = {0.15, 1, 0.1}})
    newLayer("smoke", function() drawNebula("Smoke", 9 * d, 0.25, 22) end, {turns = -1, wob = 12, axis = {-0.3, 1, 0.2}})
    newLayer("dust", function() drawNebula("Stars", 16 * d, 0.1, 26) end, {turns = 2, wob = 7, axis = {0.4, 1, -0.2}})
    newLayer("dust", function() drawNebula("Snow", 12 * d, 0.07, 24) end, {turns = -2, wob = 10, axis = {0.1, 1, 0.5}})
    newLayer("dust", function() drawNebula("Stars", 14 * d, 0.07, 30) end, {turns = 1, wob = 14, axis = {1, 0.4, 0.2}})
    newLayer("dust", function() drawNebula("Embers", 6 * d, 0.1, 14) end, {turns = -1, wob = 6, axis = {-0.6, 1, -0.4}})
    newLayer("core", drawCore, {turns = -2, wob = 0, axis = {0, 1, 0}})
    local draws = {
        star = function()
            drawStar(0.95)
            for k = 0, 3 do
                local a = Math.pi / 4 + k * Math.pi / 2
                local cx, cy = 1.38 * Math:Cos(a), 1.38 * Math:Sin(a)
                symbolPath(rhombus(0.11, 0.17, cx, cy), true, COL.green)
                symbolPath(rhombus(0.06, 0.09, cx, cy), true, COL.lime)
            end
        end,
        medallions = function()
            drawMedallion(0.44, -0.78, -0.32, 0.25, 0.5)
            drawMedallion(0.44, 0.78, -0.32, 0.25, -0.5)
            drawMedallion(0.44, 0, 0.6, -0.1, 0)
        end,
        bands = drawBands,
        vine = drawVine,
        flower = function() drawFlower(1.0) end,
    }
    for i, A in ipairs(ACTS) do
        local rec = newLayer("symbol", draws[A.name], {act = A})
        rec.layer:Hide()
        rec.visible = false
    end
    Sketch.layers.active = Sketch.layers.main
    Brush.type = saved.type
    Brush.size = saved.size
    Brush.colorRgb = saved.color
end

-- ---------- the movement every frame ----------
local function axisVec(name)
    if name == "fwd" then return Vector3:New(FWD[1], FWD[2], FWD[3]) end
    return Vector3:New(0, 1, 0)
end

local function animate(t)
    -- the whole nebula: bursts after each symbol, swallowed into the core at the end, then an explosion
    local burst = 0.22 * (bump(t, 11.7, 0.9) + bump(t, 22.7, 0.9) + bump(t, 33.7, 0.9) + bump(t, 44.7, 0.9)) + 0.3 * bump(t, 60.8, 1.0)
    local collapse = env(t, 61.5, 64.5, 68.2, 68.21)
    local explode = env(t, 68.2, 69.2, 69.2, 71.5)
    local breathe = 1 + 0.05 * Math:Sin(t * 2.1)
    local nebScale = breathe + burst
    nebScale = nebScale * (1 - 0.92 * collapse) + 0.35 * explode * (1 - collapse)
    if t >= 68.2 and t < 69.2 then nebScale = 0.08 + (1.35 - 0.08) * smooth((t - 68.2) / 1.0) end
    local flowA = 0.35 * (0.5 + 0.5 * Math:Sin(TAU * t / 9))         -- the smoke stretches and retracts
    local tiltAxis = Vector3:New(RIGHT[1], RIGHT[2], RIGHT[3])

    for _, rec in ipairs(layers) do
        local L = rec.layer
        if rec.kind ~= "symbol" then
            local turn = 360 * rec.turns * t / LOOP + 25 * Math:Sin(TAU * 2 * t / LOOP) * rec.turns
            local spinFaster = 140 * env(t, 60, 62.5, 66, 68.2) * (rec.turns > 0 and 1 or -1)   -- the final vortex
            local a = rec.axis
            local ax = Vector3:New(a[1] * RIGHT[1] + a[2] * UPV[1] + a[3] * FWD[1],
                                   a[1] * RIGHT[2] + a[2] * UPV[2] + a[3] * FWD[2],
                                   a[1] * RIGHT[3] + a[2] * UPV[3] + a[3] * FWD[3])
            local rot = Rotation:AngleAxis(rec.wob * Math:Sin(TAU * t / 18 + rec.wob), tiltAxis)
            rot = rot:Multiply(Rotation:AngleAxis(turn + spinFaster, ax))
            L.rotation = rot
            local s = nebScale
            if rec.kind == "core" then s = 1 + 0.6 * collapse + 0.3 * bump(t, 68.6, 1.2) end
            L.scale = s
            if rec.kind == "smoke" then
                L:SetShaderClipping(flowA * 0.6, 0.35 - flowA * 0.6)
            end
        else
            local A = rec.act
            local inAct = (t >= A.t0 - 0.05) and (t <= A.t1 + 0.05)
            if inAct and not rec.visible then L:Show(); rec.visible = true end
            if (not inAct) and rec.visible then L:Hide(); rec.visible = false end
            if inAct then
                local ramp = 2.6
                local reveal = smooth((t - A.t0) / ramp)
                local release = smooth((t - (A.t0 + ramp + A.hold)) / (A.t1 - (A.t0 + ramp + A.hold)))
                -- the symbol draws itself, holds, then unravels while expanding
                L:SetShaderClipping(release, 1 - reveal)
                L.scale = 0.4 + 0.6 * smooth((t - A.t0) / (ramp * 0.8)) + 0.45 * release
                local rot = Rotation:AngleAxis(A.spin * (t - A.t0), axisVec(A.axis))
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
end

function Main()
    if not placed then
        if Brush.triggerPressedThisFrame then
            local p = Brush.position
            local d = Brush.direction
            FWD = norm({-d.x, 0, -d.z})                 -- the symbols face the user
            UPV = {0, 1, 0}
            RIGHT = norm(cross(UPV, FWD))
            -- the center: 2.5 meters in front of the hand (in the pointing direction), a little higher
            local dist = 2.5 * UNITS * Parameters.size
            C = {p.x - FWD[1] * dist, p.y + 0.15 * UNITS, p.z - FWD[3] * dist}
            build()
            placed = true
            clock0 = App.time - 68.2 / Parameters.speed  -- it begins with an explosion from a point
        end
        return
    end
    local t = ((App.time - clock0) * Parameters.speed) % LOOP
    animate(t)
end

function End()
    -- when turned off: remove its layers, so turning it on again starts clean
    for _, rec in ipairs(layers) do rec.layer:Delete() end
    layers = {}
    placed = false
    if saved.type then
        Brush.type = saved.type
        Brush.size = saved.size
        Brush.colorRgb = saved.color
    end
end
