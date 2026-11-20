-- OB-Sim: an emulation of the Open Brush Lua plugin API (the subset plugins use), written to match the C# source
-- (icosa-foundation/open-brush v2.32): Path:Draw / DrawWithBrush -> DrawStrokes.DrawNestedTrList,
-- Layer pose (TRS), SetShaderClipping(start, end) on batches, _Dissolve, Show/Hide, Brush.direction = rot * back.
-- Everything that would change the scene is recorded in LOG for the renderer.

LOG = {strokes = {}, layers = {}, events = {}, errors = {}}
SIM = {time = 0, frame = 0}

local function vnew(x, y, z) return setmetatable({x = x or 0, y = y or 0, z = z or 0}, V3MT) end
V3MT = {}
V3MT.__index = function(t, k)
    if k == "magnitude" then return math.sqrt(t.x * t.x + t.y * t.y + t.z * t.z) end
    if k == "normalized" then local m = math.sqrt(t.x * t.x + t.y * t.y + t.z * t.z); if m < 1e-9 then return vnew(0, 0, 0) end return vnew(t.x / m, t.y / m, t.z / m) end
    return Vector3[k]
end
V3MT.__add = function(a, b) return vnew(a.x + b.x, a.y + b.y, a.z + b.z) end
V3MT.__sub = function(a, b) return vnew(a.x - b.x, a.y - b.y, a.z - b.z) end
V3MT.__mul = function(a, b)
    if type(a) == "number" then return vnew(b.x * a, b.y * a, b.z * a) end
    if type(b) == "number" then return vnew(a.x * b, a.y * b, a.z * b) end
    error("Vector3 * Vector3 is not supported")
end
V3MT.__unm = function(a) return vnew(-a.x, -a.y, -a.z) end
Vector3 = {}
function Vector3:New(x, y, z)
    assert(type(x) == "number" and type(y) == "number" and type(z) == "number", "Vector3:New needs 3 numbers")
    assert(x == x and y == y and z == z, "Vector3:New got NaN")
    return vnew(x, y, z)
end
function Vector3:Add(o) return vnew(self.x + o.x, self.y + o.y, self.z + o.z) end
function Vector3:Multiply(s) return vnew(self.x * s, self.y * s, self.z * s) end
function Vector3:Cross(a, b) return vnew(a.y * b.z - a.z * b.y, a.z * b.x - a.x * b.z, a.x * b.y - a.y * b.x) end
function Vector3:Dot(a, b) return a.x * b.x + a.y * b.y + a.z * b.z end
Vector3.zero = vnew(0, 0, 0); Vector3.up = vnew(0, 1, 0); Vector3.forward = vnew(0, 0, 1); Vector3.right = vnew(1, 0, 0)

-- quaternions (Unity convention x, y, z, w)
local function qnew(x, y, z, w) return setmetatable({x = x, y = y, z = z, w = w}, QMT) end
QMT = {}
QMT.__index = Rotation
local function qmul(a, b)
    return qnew(a.w * b.x + a.x * b.w + a.y * b.z - a.z * b.y, a.w * b.y - a.x * b.z + a.y * b.w + a.z * b.x,
                a.w * b.z + a.x * b.y - a.y * b.x + a.z * b.w, a.w * b.w - a.x * b.x - a.y * b.y - a.z * b.z)
end
function qrot(q, v)
    local x, y, z, w = q.x, q.y, q.z, q.w
    local tx, ty, tz = 2 * (y * v.z - z * v.y), 2 * (z * v.x - x * v.z), 2 * (x * v.y - y * v.x)
    return vnew(v.x + w * tx + (y * tz - z * ty), v.y + w * ty + (z * tx - x * tz), v.z + w * tz + (x * ty - y * tx))
end
Rotation = {}
QMT.__index = Rotation
function Rotation:AngleAxis(deg, axis)
    assert(type(deg) == "number" and deg == deg, "Rotation:AngleAxis: bad angle")
    local m = math.sqrt(axis.x ^ 2 + axis.y ^ 2 + axis.z ^ 2)
    if m < 1e-9 then return qnew(0, 0, 0, 1) end
    local h = math.rad(deg) / 2
    local s = math.sin(h) / m
    return qnew(axis.x * s, axis.y * s, axis.z * s, math.cos(h))
end
function Rotation:LookRotation(fwd, up)
    up = up or vnew(0, 1, 0)
    local f = fwd.normalized
    local r = Vector3:Cross(up, f).normalized
    local u = Vector3:Cross(f, r)
    -- matrix columns r, u, f -> quaternion
    local m00, m01, m02 = r.x, u.x, f.x
    local m10, m11, m12 = r.y, u.y, f.y
    local m20, m21, m22 = r.z, u.z, f.z
    local tr = m00 + m11 + m22
    if tr > 0 then
        local s = math.sqrt(tr + 1) * 2
        return qnew((m21 - m12) / s, (m02 - m20) / s, (m10 - m01) / s, 0.25 * s)
    elseif m00 > m11 and m00 > m22 then
        local s = math.sqrt(1 + m00 - m11 - m22) * 2
        return qnew(0.25 * s, (m01 + m10) / s, (m02 + m20) / s, (m21 - m12) / s)
    elseif m11 > m22 then
        local s = math.sqrt(1 + m11 - m00 - m22) * 2
        return qnew((m01 + m10) / s, 0.25 * s, (m12 + m21) / s, (m02 - m20) / s)
    else
        local s = math.sqrt(1 + m22 - m00 - m11) * 2
        return qnew((m02 + m20) / s, (m12 + m21) / s, 0.25 * s, (m10 - m01) / s)
    end
end
function Rotation:Multiply(o) return qmul(self, o) end
Rotation.zero = qnew(0, 0, 0, 1)
Rotation.identity = qnew(0, 0, 0, 1)

Transform = {}
local TMT = {__index = Transform}
function Transform:New(t, r, s)
    if type(r) == "number" then s = r; r = nil end
    return setmetatable({position = t or vnew(0, 0, 0), rotation = r or qnew(0, 0, 0, 1), scale = s or 1, __tr = true}, TMT)
end

Color = {}
local function hex2rgb(h)
    h = h:gsub("#", "")
    return {tonumber(h:sub(1, 2), 16) / 255, tonumber(h:sub(3, 4), 16) / 255, tonumber(h:sub(5, 6), 16) / 255}
end
function Color:New(a, b, c)
    if type(a) == "string" then local v = hex2rgb(a); return {r = v[1], g = v[2], b = v[3]} end
    return {r = a or 0, g = b or 0, b = c or 0}
end
Color.red = Color:New(1, 0, 0); Color.white = Color:New(1, 1, 1); Color.black = Color:New(0, 0, 0)

Math = {pi = math.pi}
for _, f in ipairs({"sin", "cos", "tan", "sqrt", "abs", "floor", "ceil", "acos", "asin", "atan", "exp", "log"}) do
    local g = math[f]
    Math[f:sub(1, 1):upper() .. f:sub(2)] = function(self, x) return g(x) end
end
function Math:Max(a, b) return math.max(a, b) end
function Math:Min(a, b) return math.min(a, b) end
function Math:Round(x) return math.floor(x + 0.5) end
function Math:Atan2(y, x) return math.atan(y, x) end
function Math:Pow(a, b) return a ^ b end
function Math:Clamp(v, a, b) return math.max(a, math.min(b, v)) end

Random = setmetatable({}, {__index = function(t, k)
    if k == "value" then return SIMRAND() end
    if k == "insideUnitSphere" then
        local x, y, z
        repeat x, y, z = SIMRAND() * 2 - 1, SIMRAND() * 2 - 1, SIMRAND() * 2 - 1 until x * x + y * y + z * z <= 1
        return vnew(x, y, z)
    end
end})

-- brushes known to the simulator (names matched like Open Brush: lowercase, letters and digits only)
BRUSHES = {}
for _, n in ipairs({"Marker", "Tapered Marker", "Dot Marker", "Light", "Ink", "Soft Highlighter", "Highlighter",
                    "Stars", "Dots", "Smoke", "Snow", "Embers", "Neon Pulse", "Dr. Wigglez", "Felt", "Wire", "Toon",
                    "Velvet Ink", "Tapered Flat", "Flat", "Paper", "Splatter", "Bubbles", "Shiny Hull", "Matte Hull",
                    "Unlit Hull", "Diamond Hull", "Lofted", "Icing", "Petal", "Faceted Tube", "Tube Toon Inverted"}) do
    BRUSHES[(n:lower():gsub("[^%w]", ""))] = n
end
local function lookupBrush(name)
    if type(name) ~= "string" then return nil end
    return BRUSHES[(name:lower():gsub("[^%w]", ""))]
end

-- layers: canvases with a local pose (TRS)
local LayerMT = {}
local layerCount = 0
ALLLAYERS = {}
Layer = {}
local function newCanvas(isMain)
    layerCount = layerCount + 1
    local L = {__id = layerCount, __T = vnew(0, 0, 0), __R = qnew(0, 0, 0, 1), __S = 1, __vis = true,
               __clip = nil, __diss = 1, __deleted = false, __anim = false, __main = isMain, __nstrokes = 0}
    LOG.layers[layerCount] = {id = layerCount, created = SIM.time, main = isMain}
    setmetatable(L, LayerMT)
    ALLLAYERS[layerCount] = L
    return L
end
LayerMT.__index = function(L, k)
    if k == "position" then return L.__T end
    if k == "rotation" then return L.__R end
    if k == "scale" then return L.__S end
    if k == "transform" then return Transform:New(L.__T, L.__R, L.__S) end
    if k == "allowStrokeAnimation" then return L.__anim end
    if k == "index" then return L.__id - 1 end
    if k == "active" then return Sketch.layers.active == L end
    return Layer[k]
end
LayerMT.__newindex = function(L, k, v)
    if k == "position" then assert(v.x == v.x, "NaN position"); L.__T = vnew(v.x, v.y, v.z)
    elseif k == "rotation" then assert(v.w == v.w, "NaN rotation"); L.__R = qnew(v.x, v.y, v.z, v.w)
    elseif k == "scale" then assert(type(v) == "number" and v == v, "bad scale"); L.__S = v
    elseif k == "transform" then
        assert(type(v) == "table" and v.__tr, "transform needs a Transform")
        local t, r = v.position, v.rotation
        assert(t.x == t.x and r.w == r.w and v.scale == v.scale, "NaN transform")
        L.__T = vnew(t.x, t.y, t.z); L.__R = qnew(r.x, r.y, r.z, r.w); L.__S = v.scale
    elseif k == "allowStrokeAnimation" then L.__anim = v
    elseif k == "active" then if v then Sketch.layers.active = L end
    else rawset(L, k, v) end
end
function Layer:New()
    local L = newCanvas(false)
    Sketch.layers.active = L          -- AddLayerCommand(makeActive: true)
    LOG.events[#LOG.events + 1] = {t = SIM.time, kind = "addLayer", layer = L.__id}
    return L
end
function Layer:Show() self.__vis = true end
function Layer:Hide() self.__vis = false end
function Layer:Delete()
    assert(not self.__deleted, "layer deleted twice")
    self.__deleted = true
    LOG.layers[self.__id].deleted = SIM.time
    if Sketch.layers.active == self then Sketch.layers.active = Sketch.layers.main end
end
function Layer:Clear()
    LOG.events[#LOG.events + 1] = {t = SIM.time, kind = "clear", layer = self.__id}
end
function Layer:SetShaderClipping(a, b, c)
    if type(a) == "string" then a, b = b, c end
    assert(type(a) == "number" and type(b) == "number", "SetShaderClipping needs numbers")
    self.__clip = {a, b}
end
function Layer:SetShaderFloat(a, b, c)
    if c ~= nil then a, b = b, c end
    if a == "_Dissolve" then self.__diss = b end
end
-- CanvasScript.CenterPivot: the pose moves to the bounds' center and the strokes shift so nothing moves on screen
function Layer:CenterPivot()
    local b = self.__bounds
    if not b then return end
    local c = vnew((b[1] + b[4]) / 2, (b[2] + b[5]) / 2, (b[3] + b[6]) / 2)
    self.__T = vnew(self.__T.x + c.x, self.__T.y + c.y, self.__T.z + c.z)
    LOG.layers[self.__id].pivot = {c.x, c.y, c.z}
    LOG.layers[self.__id].pivotTime = SIM.time
    self.__bounds = {b[1] - c.x, b[2] - c.y, b[3] - c.z, b[4] - c.x, b[5] - c.y, b[6] - c.z}
end

-- the main layer and the sketch
MAINLAYER = nil
Sketch = {layers = {}}
local layersMT = {
    __index = function(t, k)
        if k == "main" then return MAINLAYER end
        if k == "active" then return rawget(t, "__active") end
        if k == "count" then return layerCount end
    end,
    __newindex = function(t, k, v)
        if k == "active" then rawset(t, "__active", v) else rawset(t, k, v) end
    end
}
setmetatable(Sketch.layers, layersMT)
MAINLAYER = newCanvas(true)
Sketch.layers.active = MAINLAYER
Sketch.mainLayer = MAINLAYER

-- brush state (the pointer)
BRUSHSTATE = {type = "Marker", size = 0.2, color = {r = 1, g = 1, b = 1}}
HAND = {pos = vnew(0, 12, 0), rot = qnew(0, 0, 0, 1), trigger = false}
Brush = setmetatable({}, {
    __index = function(t, k)
        if k == "type" then return BRUSHSTATE.type end
        if k == "sizeAbsolute" then return BRUSHSTATE.size end
        if k == "size" then return BRUSHSTATE.size end
        if k == "colorRgb" then return BRUSHSTATE.color end
        if k == "position" then return HAND.pos end
        if k == "rotation" then return HAND.rot end
        if k == "direction" then return qrot(HAND.rot, vnew(0, 0, -1)) end   -- rot * Vector3.back
        if k == "triggerPressedThisFrame" then return HAND.trigger end
        if k == "triggerIsPressed" then return HAND.trigger end
        if k == "triggerReleasedThisFrame" then return false end
    end,
    __newindex = function(t, k, v)
        if k == "type" then
            local n = lookupBrush(v)
            if n then BRUSHSTATE.type = n else LOG.errors[#LOG.errors + 1] = "No brush found: " .. tostring(v) end
        elseif k == "sizeAbsolute" then BRUSHSTATE.size = v
        elseif k == "size" then BRUSHSTATE.size = 0.05 + v * 0.95   -- 0..1 of a typical brush range (Marker 0.05..1)
        elseif k == "colorRgb" then BRUSHSTATE.color = v end
    end
})

App = setmetatable({}, {__index = function(t, k)
    if k == "time" then return SIM.time end
    if k == "frames" then return SIM.frame end
    if k == "currentScale" then return SIM.scale or 1 end
end})
function App:Error(msg) LOG.events[#LOG.events + 1] = {t = SIM.time, kind = "message", text = tostring(msg)} end

-- paths and drawing (DrawStrokes.DrawNestedTrList)
Path = {}
local PathMT = {__index = Path}
function Path:New(list)
    local pts = {}
    for i, p in ipairs(list or {}) do
        if p.__tr then pts[i] = p else pts[i] = Transform:New(vnew(p.x, p.y, p.z)) end
    end
    return setmetatable({__pts = pts}, PathMT)
end
function Path:Insert(p) self.__pts[#self.__pts + 1] = p.__tr and p or Transform:New(vnew(p.x, p.y, p.z)) end

local function makeStroke(path, brush, size, color, smoothing, layer)
    local pts = path.__pts
    if #pts < 2 then return end
    if layer.__deleted then LOG.errors[#LOG.errors + 1] = "drew on a deleted layer"; return end
    local cps = {}
    local function add(pos, tr)
        assert(pos.x == pos.x and pos.y == pos.y and pos.z == pos.z, "NaN in a stroke")
        local q = tr.rotation
        cps[#cps + 1] = {pos.x, pos.y, pos.z, q.x, q.y, q.z, q.w, tr.scale}
    end
    for i = 1, #pts - 1 do                      -- the C# loop never reaches the last vertex
        local tr = pts[i]
        local p, n = tr.position, pts[i + 1].position
        local tight = (i == 1) and 0.0001 or smoothing
        add(p, tr)
        if tight > 0 then
            add(vnew(p.x + (n.x - p.x) * tight, p.y + (n.y - p.y) * tight, p.z + (n.z - p.z) * tight), tr)
            add(vnew(p.x + (n.x - p.x) * 0.5, p.y + (n.y - p.y) * 0.5, p.z + (n.z - p.z) * 0.5), tr)
            add(vnew(p.x + (n.x - p.x) * (1 - tight), p.y + (n.y - p.y) * (1 - tight), p.z + (n.z - p.z) * (1 - tight)), tr)
        end
    end
    layer.__nstrokes = layer.__nstrokes + 1
    for _, cp in ipairs(cps) do
        local b = layer.__bounds
        if not b then layer.__bounds = {cp[1], cp[2], cp[3], cp[1], cp[2], cp[3]}
        else
            for k = 1, 3 do
                if cp[k] < b[k] then b[k] = cp[k] end
                if cp[k] > b[k + 3] then b[k + 3] = cp[k] end
            end
        end
    end
    LOG.strokes[#LOG.strokes + 1] = {t = SIM.time, layer = layer.__id, brush = brush, size = size,
                                     color = {color.r, color.g, color.b}, cps = cps}
    SIM.points = (SIM.points or 0) + #cps
    SIM.strokesThisFrame = (SIM.strokesThisFrame or 0) + 1
    return {count = 1}
end
function Path:Draw()
    return makeStroke(self, BRUSHSTATE.type, BRUSHSTATE.size, BRUSHSTATE.color, 0, Sketch.layers.active)
end
function Path:DrawWithBrush(brushType, size, color, smoothing, layer)
    local n = lookupBrush(brushType)
    if not n then LOG.errors[#LOG.errors + 1] = "No brush found: " .. tostring(brushType); n = BRUSHSTATE.type end
    return makeStroke(self, n, size, color or BRUSHSTATE.color, smoothing or 0, layer or Sketch.layers.active)
end

-- the state of every layer, sampled for the renderer: {id, Tx,Ty,Tz, Rx,Ry,Rz,Rw, S, visible, clipA, clipB, dissolve}
function SIM_SNAPSHOT()
    local out = {}
    for id = 2, layerCount do
        local L = ALLLAYERS[id]
        if not L.__deleted then
            local c = L.__clip
            out[#out + 1] = {id, L.__T.x, L.__T.y, L.__T.z, L.__R.x, L.__R.y, L.__R.z, L.__R.w, L.__S,
                             L.__vis and 1 or 0, c and c[1] or -1, c and c[2] or -1, L.__diss}
        end
    end
    return out
end
