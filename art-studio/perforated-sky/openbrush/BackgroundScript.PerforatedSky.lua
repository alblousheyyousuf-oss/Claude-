-- The Perforated Sky for Open Brush (Background Plugin).
-- One night of the real Omani sky over Nizwa, around you. In the aflaj (Oman's ancient water channels) the
-- shares of water were timed by the rising of stars; in the kumma (the embroidered Omani cap) the hole is
-- punched before the stitch. Here the stars are the holes and the falaj water is the thread: each time a star
-- clears the eastern hills, the water rises to it from the pool in front of you and embroiders it into the sky:
-- a rosette of lazy-daisy petals, then a running stitch that passes through real faint stars, as through the
-- punched holes of a kumma. The sky turns all night like a cap in the embroiderer's hands. When the night ends,
-- the embroidered sky stays in your sketch (unless you set Keep to 0).
--
-- Built only on what is safe in every recent Open Brush: it draws strokes a few at a time and moves layers.
-- If something goes wrong, the reason is shown on the back of your brush controller.
--
-- How to use: Extras > Plugins and Scripts > Background: pick PerforatedSky, press the eye button, then the big
-- button of the row. Point your hand toward where you want the stars to rise (that becomes the east) and wait
-- 3 seconds (or press the trigger).
--
-- Star positions: d3-celestial star catalogue (c) 2015 Olaf Frohn, BSD 3-Clause licence.

Settings = {
    description = "Perforated Sky: the Omani night sky, embroidered star by star",
    space = "canvas"
}

Parameters = {
    month = {label = "Night of the month 1-12", type = "int", min = 1, max = 12, default = 11},
    athar = {label = "Seconds per athar", type = "float", min = 5, max = 60, default = 20},
    radius = {label = "Sky radius (m)", type = "float", min = 8, max = 40, default = 22},
    keep = {label = "Keep the embroidery 0 no 1 yes", type = "int", min = 0, max = 1, default = 1},
    lights = {label = "Set the lights 0 no 1 yes", type = "int", min = 0, max = 1, default = 1},
}

local UNITS = 10
local PI = Math.pi
local DEG = PI / 180
local TAU = 2 * PI
local sin = (math and math.sin) or function(x) return Math:Sin(x) end
local cos = (math and math.cos) or function(x) return Math:Cos(x) end
local sqrt = (math and math.sqrt) or function(x) return Math:Sqrt(x) end
local acos = (math and math.acos) or function(x) return Math:Acos(x) end
local floor = (math and math.floor) or function(x) return Math:Floor(x) end
local abs = (math and math.abs) or function(x) return Math:Abs(x) end
local exp = (math and math.exp) or function(x) return Math:Exp(x) end
local tan = (math and math.tan) or function(x) return Math:Tan(x) end
local LAT = 22.93 * DEG
local LON = 57.53
local ATHARS = 24
local NIGHT_HOURS = 10.5
local RISE_ALT = 5 * DEG
local INK = {"#D81E8C", "#7A35D6", "#9BE060", "#3F7FEA", "#EE5DB4", "#C8304F"}

-- ---------- the brightest stars: ra*10, dec*10 (degrees), magnitude*10, (B-V)*100, brightest first ----------
local SD = {
    1013,-167,-14,1,960,-527,-6,16,2139,192,0,124,2199,-608,0,71,2792,388,0,0,792,460,1,80,786,-82,2,-3,1148,52,4,43,
    244,-572,4,-16,888,74,4,150,2110,-604,6,-23,2977,89,8,22,1866,-631,8,-24,690,165,9,154,2013,-112,10,-24,2474,-264,
    11,186,1163,280,12,99,3444,-296,12,14,1919,-597,12,-24,3104,453,12,9,2199,-608,14,90,1521,120,14,-9,1047,-290,15,
    -21,1136,319,16,3,1878,-571,16,160,2634,-371,16,-23,813,63,16,-22,816,286,16,-13,1383,-697,17,7,841,-12,17,-18,3321,
    -470,17,-7,852,-19,17,-20,1224,-473,18,-14,1935,560,18,-2,511,499,18,48,2760,-344,18,-3,1659,618,18,106,1071,-264,
    18,67,2069,493,18,-10,1256,-595,19,120,2643,-430,19,41,899,449,19,8,2522,-690,19,145,994,164,19,0,1312,-547,19,4,
    3064,-567,19,-12,380,893,20,64,957,-180,20,-24,1419,-87,20,144,318,235,20,115,1550,198,20,113,109,-180,20,102,2838,
    -263,20,-13,2117,-364,21,101,21,291,21,-4,174,356,21,158,869,-97,21,-17,2227,742,21,146,3407,-469,21,161,2637,126,
    21,16,470,410,21,0,310,423,21,137,1773,146,21,9,142,607,22,-5,1904,-490,22,-2,1209,-400,22,-27,1393,-593,22,19,2337,
    267,22,3,1370,-434,22,166,2010,549,22,6,3056,403,22,67,101,565,22,117,2692,515,22,152,830,-3,22,-18,23,591,23,38,
    2050,-535,23,-17,2401,-226,23,-12,2525,-343,23,114,2205,-474,23,-15,2189,-422,23,-16,1655,564,23,3,2212,271,24,97,
    3260,99,24,152,2656,-390,24,-17,66,-423,24,108,1785,537,24,4,2576,-157,24,6,3459,281,24,166,1110,-293,24,-8,3196,
    626,24,26,1405,-550,25,-14,3116,340,25,102,3462,152,25,0,456,41,25,163,2493,-106,25,4,2089,-473,26,-18,1685,205,26,
    13,2414,-198,26,-6,832,-178,26,21,1821,-507,26,-13,1840,-175,26,-11,2857,-299,26,6,2293,-94,26,-7,2361,64,26,117,
    287,208,26,16,849,-341,26,-12,899,372,26,-8,1886,-234,26,89,215,602,27,16,2087,184,27,58,2246,-431,27,-18,742,332,
    27,149,1617,-494,27,90,1893,-691,27,-18,2627,-373,27,-18,1093,-371,27,162,2752,-298,27,138,2966,106,27,151,2436,-37,
    27,158,2460,615,27,91,1607,-644,27,-22,1904,-14,27,37,839,-59,28,-21,2001,-367,28,7,2227,-160,28,15,2659,46,28,117,
    770,-51,28,16,2476,215,28,95,2587,144,28,116,1838,-587,28,-19,2626,523,28,95,2338,-412,28,-22,821,-208,28,81,2503,
    316,28,65,64,-773,28,62,2490,-282,28,-21,2770,-254,28,102,33,152,28,-19,1219,-243,28,46,2388,-634,28,32,585,319,28,
    27,2613,-555,28,148,2630,-499,28,-14,569,241,28,-9,1955,110,28,93,3268,-161,28,18,297,-616,29,29,2962,451,29,0,957,
    225,29,162,2297,-687,29,1,3346,-603,29,139,446,-403,29,13,2874,-210,29,38,1118,83,29,-10,1940,383,29,-12,2397,-261,
    29,-18,595,400,29,-20,2453,-256,29,30,3229,-56,29,83,462,535,29,72,1468,-651,29,27,3408,302,29,85,1025,-506,29,121,
    1875,-165,29,-1,3314,-3,30,97,595,-135,30,159,844,211,30,-15,1465,238,30,81,2715,-304,30,98,1997,-232,30,92,2669,
    -401,30,51,2864,139,30,1,324,350,30,14,1674,445,30,114,2302,718,30,6,2530,-380,30,-20,3285,-374,30,-8,557,478,30,
    -12,951,-301,30,-16,1058,-238,30,-8,1825,-226,30,133,755,438,30,54,1916,-681,30,-18,2180,383,30,19,2927,280,30,109,
    3053,-148,30,79,1010,251,31,138,1556,415,31,160,2881,677,31,99,2744,-368,31,158,1338,59,31,98,1624,-162,31,123,1739,
    -630,31,-4,3094,-473,31,100,877,-358,31,115,1348,480,31,22,2547,-560,31,155,2588,248,31,8,2248,-421,31,-21,1403,344,
    31,155,1428,-570,32,154,2588,368,32,144,994,-432,32,-10,1432,517,32,48,2572,657,32,-12,2814,-270,32,-11,766,412,32,
    -15,2206,-650,32,26,725,70,32,48,764,-224,32,146,2544,94,32,116,2675,-370,32,119,3182,302,32,99,3548,776,32,103,
    2303,-406,32,-23,2446,-47,32,97,2753,-29,32,94,3222,706,32,-20,1020,-619,32,22,3028,-8,32,-7,1123,-433,32,151,2116,
    -267,32,109,2260,-253,32,167,2847,327,32,-5,568,-742,33,159,98,309,33,127,2605,-250,33,-19,3437,-158,33,7,782,-162,
    33,-11,1534,-700,33,-7,2312,590,33,117,685,-550,33,-8,1580,-617,33,-9,937,225,33,160,2613,-564,33,-15,165,-467,33,
    88,463,388,33,153,1839,570,33,8,2580,-432,33,44,2698,-98,33,99,2867,-277,33,117,636,-625,33,92,1686,154,33,0,1173,
    -249,33,122,286,637,34,-15,811,-24,34,-24,1013,129,34,44,1276,607,34,86,2914,31,34,32,2307,-447,34,-19,1317,64,34,
    68,2037,-6,34,11,838,99,34,-16,1543,-613,34,154,1939,34,34,157,3327,582,34,156,672,159,34,18,221,-433,34,154,602,
    125,34,-10,2074,-417,34,-22,2281,-521,34,92,3113,618,34,91,3404,108,34,-9,283,296,34,49,2400,-384,34,-21,2666,277,
    34,75,3112,-662,34,16,1377,-590,34,-19,1542,234,34,31,2866,-49,34,-10,1543,429,34,3,123,578,35,59,171,-102,35,116,
    1192,-530,35,-18,2289,333,35,96,408,32,35,9,2074,-425,35,-17,1518,168,35,-3,2507,389,35,92,260,-159,35,73,1054,-279,
    35,173,1696,331,35,140,2255,404,35,96,2767,-460,35,-18,3421,-513,35,8,1025,-325,35,-12,1100,220,35,37,3424,662,35,
    105,2997,195,35,157,3425,246,35,93,558,-98,35,92,1453,99,35,52,1492,-546,35,-7,2825,334,35,0,2844,-211,35,115,3325,
    62,35,9,672,192,35,101,1241,92,35,148,1733,-319,35,95,2374,-34,35,-4,2644,-154,35,26,645,-338,36,-11,867,-148,36,10,
    2149,-461,36,-18,2753,727,36,49,3022,-662,36,75,49,-88,36,121,341,-515,36,-12,1698,-148,36,111,2531,-380,36,-21,
    1161,244,36,93,1359,472,36,1,2180,304,36,130,2305,-363,36,153,1095,165,36,11,3045,-125,36,88,245,486,36,127,794,-68,
    36,-12,861,-224,36,48,1777,18,36,52,1853,-604,36,139,210,-82,36,106,1032,340,36,10,1301,-529,36,-17,1427,-405,36,37,
    2343,-281,36,136,2628,-607,36,-10,425,273,36,-10,512,90,36,89,1526,-124,36,101,1956,-715,36,119,2664,-647,36,116,
    229,153,36,97,573,241,36,-7,1163,-380,36,171,2536,-424,36,139,3455,423,36,-10,1764,-667,36,16,3094,146,36,42,649,
    156,36,98,1429,631,36,36,2365,154,36,7,2717,-501,36,-10,3372,0,36,41,2320,291,37,32,2347,-298,37,-18,2111,644,37,-5,
    3137,-585,37,125,728,56,37,-16,1309,-332,37,-18,2968,185,37,131,3474,-212,37,120,92,539,37,-20,290,-516,37,84,756,
    411,37,115,1463,-625,37,101,1765,478,37,118,3250,-167,37,32,499,-218,37,161,2694,292,37,94,3493,33,37,92,736,24,37,
    -18,891,-142,37,34,1181,-406,37,101,2377,45,37,15,2718,96,37,16,2988,64,37,86,532,-95,37,88,562,241,37,-10,899,543,
    37,101,3162,439,37,161,518,97,37,-8,2216,19,37,0,2684,569,37,118,3254,-774,37,101,3432,-76,37,163,279,-103,37,114,
    2455,192,37,30,3187,380,37,39,1360,-471,38,117,2670,27,38,4,834,-625,38,64,878,-209,38,98,972,-70,38,-11,2862,-217,
    38,101,2924,517,38,15,3378,503,38,3,427,559,38,169,563,426,38,42,657,175,38,98,847,-26,38,-19,1264,-661,38,113,1302,
    -466,38,67,2524,-590,38,156,3099,159,38,-6,3217,-224,38,100,3318,253,38,44,1072,-705,38,101,1114,278,38,102,1477,
    590,38,29,1634,-589,38,94,2203,137,38,4,3119,-95,38,0,474,449,38,98,1633,342,38,104,1695,315,38,61,480,-290,38,54,
    1147,-268,38,-16,2337,105,38,27,2893,534,38,95,3034,467,38,127,689,-306,38,96,1570,-587,38,32,2357,263,38,2,3544,
    465,38,98,305,28,38,2,1397,368,38,7,1729,693,38,161,2477,20,38,2,2649,460,38,-18,1565,-168,38,146,2096,-421,38,-22,
    2220,-790,38,143,560,-648,38,113,561,323,38,2,671,160,38,95,1338,-606,38,-10,1582,93,38,-15,1593,-482,38,30,1881,
    -721,38,-16,2719,288,38,-2,2734,-211,38,20,2970,703,38,89,635,-423,38,108,868,-511,38,17,955,-334,38,86,1537,-421,
    38,5,1884,698,38,-12,1894,-485,38,5,2391,157,38,48,2759,218,38,117,2788,-82,38,132,142,385,39,13,695,-143,39,108,
    828,-355,39,113,2439,-637,39,110,2484,-789,39,92,2691,373,39,135,3354,-14,39,-6,565,244,39,-6,1315,-460,39,2,2097,
    -448,39,-21,2208,-57,39,38,2392,-292,39,-20,2981,10,39,63,24,-457,39,101,284,193,39,-5,1482,260,39,122,2280,-487,39,
    -3,3476,-452,39,100,441,-89,39,109,1035,-242,39,174,1386,23,39,-6,1850,-7,39,3,2991,351,39,102,1450,-11,39,131,1703,
    -545,39,-16,2028,-394,39,119,608,60,39,3,1264,-39,39,-1,1870,-502,39,-19,2263,-471,39,-14,2339,-148,39,101,2449,463,
    39,-15,2551,309,39,-2,2904,-178,39,23,3190,52,39,55,66,-437,39,18,228,-491,39,97,436,528,39,76,691,-34,39,-21,1155,
    -726,39,103,1671,-590,39,123,2417,-207,39,-5,2702,29,39,3,171,-552,39,-12,1153,-96,39,102,1160,-290,39,16,1312,182,
    39,108,3143,412,39,3,309,724,40,0,992,-193,40,104,622,477,40,-2,898,-428,40,115,1352,418,40,46,1378,-623,40,-18,
    2907,-445,40,-8,2910,-406,40,-10,3039,477,40,145,3507,-201,40,108,660,-340,40,147,879,391,40,113,1092,-680,40,76,
    1300,-353,40,94,1829,-524,40,-16,2377,-336,40,-4,3001,-729,40,-3,3373,-435,40,102,3416,236,40,107,597,358,40,2,3235,
    456,40,88,300,-211,40,155,937,-63,40,132,1561,-740,40,37,2013,550,40,17,3494,-582,40,41,1356,-664,40,14,1710,105,40,
    42,2430,-195,40,8,259,507,40,-10,714,-33,40,-15,1060,206,40,90,1087,-268,40,-15,2205,-378,40,-16,2405,586,40,53,
    2450,-502,40,108,2808,-714,40,113,3073,304,40,40,1326,-277,40,127,1821,-247,40,33,2849,151,40,108,2854,-57,40,108,
    343,338,40,2,759,604,40,92,1317,288,40,101,1936,-572,40,-18,2714,25,40,86,3083,113,40,-12,3598,69,40,42,630,-68,40,
    33,1765,65,40,150,2163,519,40,50,3388,-1,40,-8,473,496,40,60,1246,-769,40,41,1311,-426,40,87,1703,60,40,-6,2074,158,
    40,152,2151,-379,40,-3,2195,-494,40,-15,3424,-136,40,157,741,135,41,116,1140,269,41,154,1712,-177,41,22,1844,-680,
    41,160,1846,-640,41,-17,2209,-352,41,136,2549,-532,41,145,2140,-60,41,51,2272,-453,41,-16,2294,-588,41,9,3373,584,
    41,78,118,243,41,110,354,-687,41,3,399,3,41,-21,456,-236,41,16,1035,-120,41,142,1436,-592,41,-1,1649,-183,41,108,
    2838,439,41,140,3165,-172,41,-1,3205,198,41,111,842,93,41,95,2372,181,41,162,242,414,41,54,410,492,41,51,1173,-464,
    41,-16,2772,-491,41,100,2875,-393,41,116,402,-399,41,101,1059,-156,41,-11,1294,-430,41,11,1479,-148,41,92,1589,-786,
    41,158,1766,-612,41,90,2342,-663,41,116,2874,-379,41,4,3452,-528,41,96,399,-683,41,-6,637,484,41,94,906,96,41,17,
    1813,87,41,97,2988,-419,41,106,3130,-269,41,163,3374,-437,41,157,810,-78,41,94,972,202,41,-12,2385,-167,41,100,3115,
    -253,41,43,3415,-814,41,21,3550,56,41,51,527,129,41,111,566,239,41,-5,1294,57,41,0,1817,-646,41,35,2332,314,41,-13,
    2394,269,41,123,3262,256,41,42,3340,377,41,145,1080,-5,42,0,2609,371,42,-1,3551,443,42,-7,910,233,42,84,1123,318,42,
    32,2411,-114,42,46,2616,-242,42,28,82,629,42,13,574,-362,42,93,3342,-78,42,98,2132,-103,42,132,2141,461,42,9,2491,
    -353,42,154,3338,570,42,28,3402,-270,42,-10,2074,-345,42,152,2814,205,42,48,827,59,42,-14,1192,-229,42,72,1570,367,
    42,91,2485,424,42,-1,3417,122,42,50,3440,-325,42,95
}
local NS = #SD / 4
local sRA, sDEC, sMAG, sBV = {}, {}, {}, {}
for i = 1, NS do
    local b = (i - 1) * 4
    sRA[i] = SD[b + 1] / 10 * DEG; sDEC[i] = SD[b + 2] / 10 * DEG; sMAG[i] = SD[b + 3] / 10; sBV[i] = SD[b + 4] / 100
end

-- ---------- small math ----------
local function dot(a, b) return a[1] * b[1] + a[2] * b[2] + a[3] * b[3] end
local function cross(a, b) return {a[2] * b[3] - a[3] * b[2], a[3] * b[1] - a[1] * b[3], a[1] * b[2] - a[2] * b[1]} end
local function add(a, b) return {a[1] + b[1], a[2] + b[2], a[3] + b[3]} end
local function sub(a, b) return {a[1] - b[1], a[2] - b[2], a[3] - b[3]} end
local function mul(a, s) return {a[1] * s, a[2] * s, a[3] * s} end
local function norm(a)
    local l = sqrt(a[1] * a[1] + a[2] * a[2] + a[3] * a[3])
    if l < 1e-9 then return {0, 0, 1} end
    return {a[1] / l, a[2] / l, a[3] / l}
end
local function ang(a, b)
    local d = dot(a, b)
    if d > 1 then d = 1 elseif d < -1 then d = -1 end
    return acos(d)
end
local function slerp(a, b, t)
    local w = ang(a, b)
    if w < 1e-6 then return {a[1], a[2], a[3]} end
    local s = sin(w)
    return add(mul(a, sin((1 - t) * w) / s), mul(b, sin(t * w) / s))
end
local function smooth(a, b, x)
    local t = (x - a) / (b - a)
    if t < 0 then t = 0 elseif t > 1 then t = 1 end
    return t * t * (3 - 2 * t)
end
local function qAxis(ax, deg)
    local a = norm(ax)
    local h = deg * PI / 360
    local s = sin(h)
    return {a[1] * s, a[2] * s, a[3] * s, cos(h)}
end
local function qRot(q, v)
    local x, y, z, w = q[1], q[2], q[3], q[4]
    local tx, ty, tz = 2 * (y * v[3] - z * v[2]), 2 * (z * v[1] - x * v[3]), 2 * (x * v[2] - y * v[1])
    return {v[1] + w * tx + (y * tz - z * ty), v[2] + w * ty + (z * tx - x * tz), v[3] + w * tz + (x * ty - y * tx)}
end
local seed = 7
local function rnd() seed = (seed * 16807) % 2147483647; return (seed - 1) / 2147483646 end

-- ---------- the frame of the night (canvas units) ----------
local C = {0, 0, 0}                 -- centre of the sky dome (your head)
local E, N, UPV = {0, 0, 1}, {-1, 0, 0}, {0, 1, 0}
local Mv, Wv, Pv = {1, 0, 0}, {0, 0, -1}, {0, 1, 0}   -- celestial equator on the meridian, west, celestial pole
local S = 10                        -- canvas units per metre
local RC = 220                      -- sky radius in canvas units
local ZOOM = 1
local SIGN = 1                      -- which way a positive angle about the pole turns the sky westward
local night = {lst0 = 0, span = 1}
local VIEWROT = nil

-- the direction of a star at local sidereal time th (radians): unit vector in the canvas
local function starDir(i, th)
    local H = th - sRA[i]
    local cd = cos(sDEC[i])
    return add(add(mul(Mv, cd * cos(H)), mul(Wv, cd * sin(H))), mul(Pv, sin(sDEC[i])))
end
local function lstAt(jd)
    local h = 18.697374558 + 24.06570982441908 * (jd - 2451545.0) + LON / 15
    h = h % 24
    if h < 0 then h = h + 24 end
    return h * 15 * DEG
end
local function makeNight(month)
    -- the night of the 15th, from 18:45 to 05:15 Oman time
    local y, m, d = 2026, month, 15
    local a = floor((14 - m) / 12)
    local yy, mm = y + 4800 - a, m + 12 * a - 3
    local jdn = d + floor((153 * mm + 2) / 5) + 365 * yy + floor(yy / 4) - floor(yy / 100) + floor(yy / 400) - 32045
    local jd0 = jdn - 0.5 + 14.75 / 24
    return {lst0 = lstAt(jd0), span = NIGHT_HOURS * 1.00273790935 * 15 * DEG}
end
local function riseT(i)
    local c = (sin(RISE_ALT) - sin(LAT) * sin(sDEC[i])) / (cos(LAT) * cos(sDEC[i]))
    if c <= -1 or c >= 1 then return nil end
    local d = (sRA[i] - acos(c) - night.lst0) % TAU
    if d < 0 then d = d + TAU end
    return d / night.span
end
local function chooseShares()
    local cand = {}
    for i = 1, NS do
        if sMAG[i] > 3.6 then break end
        local T = riseT(i)
        if T and T < 1 then cand[#cand + 1] = {i = i, T = T} end
    end
    local used, shares, prev = {}, {}, -1
    for k = 0, ATHARS - 1 do
        local target = k / ATHARS
        if prev + 0.6 / ATHARS > target then target = prev + 0.6 / ATHARS end
        local best, bc = nil, 1e9
        for _, c in ipairs(cand) do
            if not used[c.i] and c.T >= target then
                local late = (c.T - target) * ATHARS
                if late <= 1.1 then
                    local cost = late * 1.3 + sMAG[c.i] * 0.55
                    if cost < bc then bc = cost; best = c end
                end
            end
        end
        if not best then
            for _, c in ipairs(cand) do
                if not used[c.i] and c.T >= target and (not best or c.T < best.T) then best = c end
            end
        end
        if not best then break end
        used[best.i] = true
        shares[#shares + 1] = {star = best.i, T = best.T}
        prev = best.T
    end
    return shares
end

-- ---------- drawing ----------
local useDWB = nil
local saved = {}
local stats = {strokes = 0}
local function drawInto(layer, pts, brush, sizeM, color, pressures)
    local n = #pts
    if n < 2 then return end
    local list = {}
    for i = 1, n do
        local c = pts[i]
        local pr = 1
        if pressures then pr = pressures[i] end
        list[i] = Transform:New(Vector3:New(c[1], c[2], c[3]), VIEWROT, pr)
    end
    list[n + 1] = list[n]                                   -- Open Brush skips the last point of a path
    local path = Path:New(list)
    local size = sizeM * UNITS / ZOOM
    local col = Color:New(color)
    if useDWB ~= false then
        local ok = pcall(function() path:DrawWithBrush(brush, size, col, 0, layer) end)
        useDWB = ok
    end
    if useDWB == false then
        Sketch.layers.active = layer
        Brush.type = brush
        if not pcall(function() Brush.sizeAbsolute = size end) then Brush.size = 0.5 end
        Brush.colorRgb = col
        path:Draw()
        Sketch.layers.active = saved.layer
    end
    stats.strokes = stats.strokes + 1
end
local function pebble(c, r, n)                             -- a small irregular blob (for stars and drops)
    local pts = {}
    local ga = PI * (3 - sqrt(5))
    for i = 0, n - 1 do
        local y = 1 - 2 * (i + 0.5) / n
        local rr = sqrt(1 - y * y)
        local a = ga * i
        pts[#pts + 1] = add(c, {rr * cos(a) * r, y * r, rr * sin(a) * r})
    end
    return pts
end
local function bvColor(bv)
    if bv < 0.0 then return "#CCD8FF" elseif bv < 0.3 then return "#E4EAFF" elseif bv < 0.6 then return "#FFF8EE"
    elseif bv < 1.0 then return "#FFE8C2" elseif bv < 1.4 then return "#FFD2A0" end
    return "#FFBE8C"
end

-- ---------- layers ----------
local recs, queue = {}, {}
local function part(kind, jobsFn, extra)
    local rec = {kind = kind, jobsFn = jobsFn, ready = false}
    if extra then for k, v in pairs(extra) do rec[k] = v end end
    recs[#recs + 1] = rec
    queue[#queue + 1] = rec
    return rec
end
local function J(pts, brush, size, color, pressures) return {pts = pts, brush = brush, size = size, color = color, pr = pressures} end
local budget = 2
local function prepare(dt)
    if dt > 1 / 45 then budget = Math:Max(1, budget - 1) elseif dt < 1 / 66 then budget = Math:Min(6, budget + 0.2) end
    local done = 0
    while #queue > 0 and done < floor(budget) do
        local rec = queue[1]
        if not rec.layer then
            rec.layer = Layer:New()
            Sketch.layers.active = saved.layer
            rec.layer:Hide()
            rec.jobs = rec.jobsFn()
            rec.j = 1
        end
        if rec.j > #rec.jobs then
            rec.layer:Show()
            if rec.pivot then
                -- small travelling clouds: their pivot goes to their centre, then they only move and scale
                rec.layer:CenterPivot()
                rec.layer.scale = 0.002
                local p = rec.layer.position
                rec.base = {p.x, p.y, p.z}
                rec.center = {rec.cx[1], rec.cx[2], rec.cx[3]}
            end
            rec.ready = true
            table.remove(queue, 1)
        else
            local jb = rec.jobs[rec.j]
            drawInto(rec.layer, jb.pts, jb.brush, jb.size, jb.color, jb.pr)
            rec.j = rec.j + 1
            done = done + 1
        end
    end
end
-- move a cloud so that its centre sits at target (canvas), with uniform scale s
local function placeCloud(rec, target, s)
    if s < 0.002 then s = 0.002 end
    local c = rec.center
    rec.layer.position = Vector3:New(rec.base[1] + target[1] - c[1], rec.base[2] + target[2] - c[2], rec.base[3] + target[3] - c[3])
    rec.layer.scale = s
end

-- ---------- the land, the sky, the thread ----------
local skyRec, landRec = nil, nil
local clouds = {}
local NCLOUD = 8
local function pointOnSky(u) return add(C, mul(u, RC)) end
local function buildParts()
    local th0 = night.lst0
    -- the land: dark ground, the hills of the horizon (high Jebel Akhdar to the north), the falaj and its pool
    landRec = part("land", function()
        local j = {}
        local floorY = C[2] - 1.5 * S
        local ring = {}
        for k = 0, 47 do
            local a = k / 48 * TAU
            local d = add(mul(N, cos(a)), mul(E, sin(a)))
            ring[#ring + 1] = {C[1] + d[1] * RC * 1.03, floorY - 0.4 * S, C[3] + d[3] * RC * 1.03}
        end
        j[#j + 1] = J(ring, "Unlit Hull", 0.3, "#04040A")
        for k = 0, 23 do
            local a0, a1 = k / 24 * TAU, (k + 1.08) / 24 * TAU
            local function hill(a)
                local dn = a
                if dn > PI then dn = TAU - dn end
                return (2.4 + 1.1 * sin(a * 3 + 1.1) + 0.6 * sin(a * 7.3 + 0.4) + 9 * exp(-(dn * dn) / 0.6)) * DEG
            end
            local pts = {}
            for _, a in ipairs({a0, a1}) do
                local d = add(mul(N, cos(a)), mul(E, sin(a)))
                local r = RC * 0.98
                pts[#pts + 1] = {C[1] + d[1] * r, floorY - 0.5 * S, C[3] + d[3] * r}
                pts[#pts + 1] = {C[1] + d[1] * r, C[2] + r * tan(hill(a)), C[3] + d[3] * r}
            end
            j[#j + 1] = J(pts, "Unlit Hull", 1.2, "#06060D")
        end
        -- the falaj: it comes from the eastern hills and ends in a small pool in front of you
        local chan, chan2 = {}, {}
        local poolC = {C[1] + E[1] * 1.2 * S, floorY + 0.02 * S, C[3] + E[3] * 1.2 * S}
        for k = 0, 40 do
            local t = k / 40
            local dist = 1.2 * S + (RC * 0.95 - 1.2 * S) * (1 - t) ^ 1.6
            local wob = (1 - t) ^ 0.5 * (1.4 * sin(dist / S * 0.09) + 0.5 * sin(dist / S * 0.27 + 1.3)) * S * (t < 0.92 and 1 or (1 - t) / 0.08)
            local p = add(add({C[1], floorY + 0.03 * S, C[3]}, mul(E, dist)), mul(N, wob))
            chan[#chan + 1] = p
            chan2[#chan2 + 1] = add(p, {0, 0.02 * S, 0})
        end
        j[#j + 1] = J(chan, "Icing", 0.09, "#0A2A2E")
        j[#j + 1] = J(chan2, "Icing", 0.03, "#5FE3D2")
        local pool = {}
        for k = 0, 23 do
            local a = k / 24 * TAU
            pool[#pool + 1] = add(poolC, add(mul(N, cos(a) * 0.42 * S), mul(E, sin(a) * 0.42 * S)))
        end
        j[#j + 1] = J(pool, "Unlit Hull", 0.04, "#0E3B40")
        return j
    end, {noPivot = true, poolC = nil})
    -- the sky: the brightest stars at the start of the night (the layer then turns with the sky)
    skyRec = part("sky", function()
        local j = {}
        for i = 1, NS do
            local u = starDir(i, th0)
            local r = (0.035 + 0.075 * 10 ^ (-0.2 * sMAG[i])) * S
            j[#j + 1] = J(pebble(pointOnSky(u), r, 6), "Unlit Hull", 0.02, bvColor(sBV[i]))
        end
        return j
    end, {noPivot = true})
    -- the thread: small clouds of water that rise from the pool and follow the needle
    for k = 1, NCLOUD do
        local cx = {C[1], C[2], C[3]}
        part("cloud", function()
            local j = {}
            for q = 1, 6 do
                local c = add(cx, {(rnd() - 0.5) * 0.3 * S, (rnd() - 0.5) * 0.3 * S, (rnd() - 0.5) * 0.3 * S})
                local len = (0.03 + 0.05 * rnd()) * S
                local d = norm({rnd() - 0.5, rnd() - 0.5, rnd() - 0.5})
                j[#j + 1] = J({sub(c, mul(d, len)), c, add(c, mul(d, len))}, "Icing", 0.05 + 0.04 * rnd(),
                              (q % 3 == 0) and "#E8F6F4" or "#5FE3D2", {0.3, 1, 0.3})
            end
            return j
        end, {pivot = true, cx = cx, idx = k})
    end
end

-- ---------- the stitches of one athar ----------
local stitchJobs = {}                       -- strokes to draw on the sky layer at given times
local plan = {}                             -- the needle's paths in this athar (sky-local unit vectors)
local cur = nil
local function schedule(t, pts, brush, size, color, pr)
    stitchJobs[#stitchJobs + 1] = {t = t, pts = pts, brush = brush, size = size, color = color, pr = pr}
end
local function tangentBasis(s)
    local ref = {0, 1, 0}
    if abs(dot(s, ref)) > 0.9 then ref = {1, 0, 0} end
    local e1 = norm(cross(ref, s))
    return e1, cross(s, e1)
end
local function petal(s, psi, L, W)
    local e1, e2 = tangentBasis(s)
    local d = add(mul(e1, cos(psi)), mul(e2, sin(psi)))
    local n = add(mul(e1, -sin(psi)), mul(e2, cos(psi)))
    local pts = {}
    for k = 0, 18 do
        local a = k / 18 * TAU
        local r = (1 - cos(a)) / 2
        pts[#pts + 1] = norm(add(s, add(mul(d, L * r ^ 0.85), mul(n, W * sin(a) * r * 1.15))))
    end
    return pts
end
-- holes between two stars: real stars near a gently curving vine, or new pricks where there is none
local REF
local function holesBetween(a, b, bend)
    local total = ang(a, b)
    local side = norm(cross(a, b))
    local G = 40
    local guide, gc = {}, {0}
    for k = 0, G do
        local t = k / G
        guide[k + 1] = norm(add(slerp(a, b, t), mul(side, bend * total * sin(PI * t))))
        if k > 0 then gc[k + 1] = gc[k] + ang(guide[k], guide[k + 1]) end
    end
    local glen = gc[G + 1]
    local list = {}
    local cmax = cos(1.6 * DEG)
    local mid = norm(add(a, b))
    local capCos = cos(total / 2 + 3 * DEG)
    local planeSin = sin(abs(bend) * total + 2 * DEG)
    for i = 1, NS do
        local v = REF[i]
        if sMAG[i] >= 2.4 and dot(v, mid) > capCos and abs(dot(v, side)) < planeSin then
            local best, bd = -1, cmax
            for k = 1, G + 1, 2 do
                local d = dot(v, guide[k])
                if d > bd then bd = d; best = k end
            end
            if best > 0 and gc[best] > 0.9 * DEG and gc[best] < glen - 0.9 * DEG then list[#list + 1] = {i = i, along = gc[best], v = v} end
        end
    end
    table.sort(list, function(p, q) return p.along < q.along end)
    local function at(x)
        local k = 2
        while k < G + 1 and gc[k] < x do k = k + 1 end
        local f = (x - gc[k - 1]) / Math:Max(1e-9, gc[k] - gc[k - 1])
        return norm(add(mul(guide[k - 1], 1 - f), mul(guide[k], f)))
    end
    local chain = {{v = a, along = 0, i = -1}}
    local last = 0
    local function fill(upto)
        while upto - last > 3.6 * DEG do last = last + 2.5 * DEG; chain[#chain + 1] = {v = at(last), along = last, i = -2} end
    end
    for _, h in ipairs(list) do
        if h.along - last >= 1.4 * DEG then
            fill(h.along)
            if h.along - last >= 1.4 * DEG then chain[#chain + 1] = h; last = h.along end
        end
    end
    fill(glen)
    chain[#chain + 1] = {v = b, along = glen, i = -1}
    return chain
end
local function arcPts(a, b, bulge, n)
    local side = norm(cross(a, b))
    local w = ang(a, b)
    local pts = {}
    for k = 0, n do
        local t = k / n
        pts[#pts + 1] = norm(add(slerp(a, b, t), mul(side, bulge * w * sin(PI * t))))
    end
    return pts
end
local shares = {}
REF = {}                                    -- star directions at the start of the night (sky-local), computed once
local function toSky(list)                  -- sky-local unit vectors -> canvas points on the sky layer
    local out = {}
    for k = 1, #list do out[k] = pointOnSky(list[k]) end
    return out
end
local function sewAthar(k, ts, D)
    local sh = shares[k]
    local si = sh.star
    local s = starDir(si, night.lst0)
    local ink, ink2 = INK[(k - 1) % #INK + 1], INK[(k + 1) % #INK + 1]
    local nPet = 6
    if sMAG[si] < 1.0 then nPet = 8 elseif sMAG[si] < 2.2 then nPet = 7 end
    local bright = (2.5 - sMAG[si]) / 4
    if bright < 0 then bright = 0 elseif bright > 1 then bright = 1 end
    local L = (1.9 + 0.7 * bright) * DEG
    local W = L * 0.42
    plan = {}
    local psi0 = rnd() * PI
    local dPet = 0.30 * D / nPet
    for p = 0, nPet - 1 do
        local pts = petal(s, psi0 + p * TAU / nPet, L, W)
        local t0 = ts + 0.22 * D + p * dPet
        plan[#plan + 1] = {pts = pts, t0 = t0, t1 = t0 + dPet * 0.8}
        schedule(t0 + dPet * 0.8, toSky(pts), "Icing", 0.06, ink)
    end
    -- running stitches: to the nearest stitched star, and sometimes to the previous one
    local partners = {}
    if k > 1 then
        local bestJ, bd = nil, 1e9
        for q = 1, k - 1 do
            local d = ang(s, starDir(shares[q].star, night.lst0))
            if d < bd then bd = d; bestJ = q end
        end
        partners[#partners + 1] = shares[bestJ].star
        local prev = shares[k - 1].star
        if (k % 3 == 1) and prev ~= shares[bestJ].star and ang(s, starDir(prev, night.lst0)) < 48 * DEG then partners[#partners + 1] = prev end
    end
    local tRun = ts + 0.52 * D
    local lens, chains = {}, {}
    local totalLen = 0
    for c, pj in ipairs(partners) do
        chains[c] = holesBetween(s, starDir(pj, night.lst0), ((k + c) % 2 == 0 and 1 or -1) * (0.10 + 0.08 * rnd()))
        lens[c] = chains[c][#chains[c]].along
        totalLen = totalLen + lens[c]
    end
    for c, chain in ipairs(chains) do
        local dur = 0.30 * D * lens[c] / Math:Max(totalLen, 1e-6)
        local speed = lens[c] / dur
        local path = {}
        local u = 0
        for h = 1, #chain - 1 do
            local a, b = chain[h].v, chain[h + 1].v
            local w = ang(a, b)
            local nseg = Math:Max(3, floor(w / (0.5 * DEG)) + 1)
            local bul = 0.04
            if h % 2 == 0 then bul = -0.04 end
            local seg = arcPts(a, b, bul, nseg)
            local tEnd = tRun + (u + w) / speed
            if h % 2 == 1 then schedule(tEnd, toSky(seg), "Icing", 0.07, (h % 4 == 1) and ink2 or ink) end
            for q = (h > 1) and 2 or 1, #seg do path[#path + 1] = seg[q] end
            if chain[h + 1].i ~= -1 then
                local hv = chain[h + 1].v
                schedule(tEnd, pebble(pointOnSky(hv), 0.05 * S, 6), "Unlit Hull", 0.02, "#DDEEFF")
            end
            u = u + w
        end
        plan[#plan + 1] = {pts = path, t0 = tRun, t1 = tRun + dur}
        tRun = tRun + dur
    end
    cur = {k = k, si = si, ts = ts, D = D, tRise0 = ts + 0.06 * D, tRise1 = ts + 0.22 * D, tRel = ts + 0.9 * D}
end

-- ---------- per frame: the sky turns, the thread moves ----------
local Qsky = {0, 0, 0, 1}
local skyPos = {0, 0, 0}
local function setSky(dth)
    local deg = SIGN * dth / DEG
    Qsky = qAxis(Pv, deg)
    local qc = qRot(Qsky, C)
    skyPos = {C[1] - qc[1], C[2] - qc[2], C[3] - qc[3]}
    local L = skyRec.layer
    L.position = Vector3:New(skyPos[1], skyPos[2], skyPos[3])
    L.rotation = Rotation:AngleAxis(deg, Vector3:New(Pv[1], Pv[2], Pv[3]))
end
local function skyNow(u)                    -- where a sky-local unit vector is now, in the canvas
    return add(skyPos, qRot(Qsky, pointOnSky(u)))
end
local function pathPoint(p, f)
    if not p.cum then
        p.cum = {0}
        for q = 2, #p.pts do p.cum[q] = p.cum[q - 1] + ang(p.pts[q - 1], p.pts[q]) end
    end
    if f < 0 then f = 0 elseif f > 1 then f = 1 end
    local target = f * p.cum[#p.cum]
    local lo, hi = 2, #p.cum
    while lo < hi do
        local mid = floor((lo + hi) / 2)
        if p.cum[mid] < target then lo = mid + 1 else hi = mid end
    end
    local a, b = p.pts[lo - 1], p.pts[lo]
    local g = (target - p.cum[lo - 1]) / Math:Max(1e-9, p.cum[lo] - p.cum[lo - 1])
    return norm(add(mul(a, 1 - g), mul(b, g)))
end
local function bez(p0, p1, p2, p3, t)
    local u = 1 - t
    return add(add(mul(p0, u * u * u), mul(p1, 3 * u * u * t)), add(mul(p2, 3 * u * t * t), mul(p3, t * t * t)))
end
local function moveThread(t)
    if not cur then
        for _, c in ipairs(clouds) do placeCloud(c, c.center, 0.002) end
        return
    end
    local starP = skyNow(starDir(cur.si, night.lst0))
    local poolC = landRec.poolC
    if t < cur.tRise1 + 0.4 then
        local q = (t - cur.tRise0) / (cur.tRise1 - cur.tRise0)
        local p1 = add(poolC, {0, 3.2 * S, 0})
        local p2 = {C[1] + (starP[1] - C[1]) * 0.45, C[2] + 6 * S, C[3] + (starP[3] - C[3]) * 0.45}
        for i, c in ipairs(clouds) do
            local sg = q * 1.4 - (i - 1) * 0.05
            if q < 0 or sg <= 0 then placeCloud(c, poolC, 0.002)
            else
                if sg > 1 then sg = 1 end
                local w = sin(PI * sg) * 0.6 * S
                local pos = bez(poolC, p1, p2, starP, sg)
                pos = add(pos, {sin(t * 2 + i) * w, cos(t * 1.7 + i * 2) * w * 0.6, cos(t * 2.3 + i) * w})
                placeCloud(c, pos, 0.5 + 2.2 * sg * sg)
            end
        end
    elseif t < cur.tRel then
        local p = nil
        for _, pl in ipairs(plan) do if t >= pl.t0 and t < pl.t1 then p = pl end end
        for i, c in ipairs(clouds) do
            local pos
            if p then
                local f = (t - p.t0) / (p.t1 - p.t0) - (i - 1) * 0.035
                pos = skyNow(pathPoint(p, f))
            else
                pos = add(starP, {sin(t + i) * 0.4 * S, cos(t * 0.8 + i) * 0.4 * S, sin(t * 1.3 + i * 2) * 0.4 * S})
            end
            placeCloud(c, pos, 1.4 - (i - 1) * 0.1)
        end
    else
        local r = (t - cur.tRel) / (0.1 * cur.D)
        for i, c in ipairs(clouds) do placeCloud(c, starP, (1 - smooth(0, 1, r)) * 1.2) end
    end
end

-- ---------- the plugin ----------
local placed, startTime, lastTime, clock = false, 0, 0, 0
local reported, announced, finished = false, false, false
local nextK = 1
local NIGHT = 24 * 20
local function setLights(on)
    if Parameters.lights ~= 1 then return end
    pcall(function()
        if on then
            saved.lights = {Sketch.ambientLightColor, Sketch.mainLightColor, Sketch.secondaryLightColor,
                            Sketch.mainLightRotation, Sketch.secondaryLightRotation}
            Sketch.ambientLightColor = Color:New(0.36, 0.38, 0.5)
            Sketch.mainLightColor = Color:New(0.75, 0.8, 0.95)
            Sketch.secondaryLightColor = Color:New(0.3, 0.45, 0.6)
            Sketch.mainLightRotation = Rotation:LookRotation(Vector3:New(0, -1, 0.2), Vector3:New(0, 0, 1))
            Sketch.secondaryLightRotation = Rotation:LookRotation(Vector3:New(0.3, 0.6, 1), Vector3:New(0, 1, 0))
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
    E = norm({d.x, 0, d.z})
    UPV = {0, 1, 0}
    N = norm(cross(E, UPV))                    -- on your left when you face east
    ZOOM = App.currentScale
    if ZOOM == nil or ZOOM < 0.01 then ZOOM = 1 end
    S = UNITS / ZOOM
    RC = Parameters.radius * S
    C = {p.x, p.y + 0.25 * S, p.z}
    local south = mul(N, -1)
    Mv = add(mul(south, sin(LAT)), mul(UPV, cos(LAT)))
    Wv = mul(E, -1)
    Pv = add(mul(N, cos(LAT)), mul(UPV, sin(LAT)))
    -- turning by +90 degrees about the pole must carry the meridian toward the west
    local turned = qRot(qAxis(Pv, 90), Mv)
    SIGN = (dot(turned, Wv) > 0) and 1 or -1
    night = makeNight(Parameters.month)
    NIGHT = ATHARS * Parameters.athar
    shares = chooseShares()
    for i = 1, NS do REF[i] = starDir(i, night.lst0) end
    saved.layer = Sketch.layers.active
    local sz = 0.1
    pcall(function() sz = Brush.sizeAbsolute end)
    saved.type, saved.size, saved.color = Brush.type, sz, Brush.colorRgb
    VIEWROT = Rotation:LookRotation(Vector3:New(-E[1], -E[2], -E[3]), Vector3:New(0, 1, 0))
    setLights(true)
    buildParts()
    landRec.poolC = {C[1] + E[1] * 1.2 * S, C[2] - 1.5 * S + 0.05 * S, C[3] + E[3] * 1.2 * S}
    placed = true
    App:Error("Perforated Sky: drawing the sky...")
end
local function step()
    local now = App.time
    local dt = now - lastTime
    lastTime = now
    if not placed then
        if Brush.triggerPressedThisFrame or (now - startTime > 3) then place() end
        return
    end
    if #queue > 0 then prepare(dt); return end
    if not announced then
        announced = true
        clouds = {}
        for _, r in ipairs(recs) do if r.kind == "cloud" then clouds[#clouds + 1] = r end end
        App:Error("Perforated Sky: the night begins (" .. #shares .. " stars will take their share)")
        if useDWB == false and saved.type then
            Brush.type = saved.type
            pcall(function() Brush.sizeAbsolute = saved.size end)
            Brush.colorRgb = saved.color
        end
    end
    local d = dt
    if d > 0.1 then d = 0.1 end
    if finished then return end
    clock = clock + d
    local T = clock / NIGHT
    if T > 1 then
        T = 1
        finished = true
        cur = nil
        moveThread(clock)
        App:Error("Perforated Sky: dawn. The embroidered night stays in your sketch.")
    end
    setSky(T * night.span)
    -- a new share begins when its star clears the eastern hills
    while nextK <= #shares and T >= shares[nextK].T do
        local k = nextK
        local ts = shares[k].T * NIGHT
        local te = (k < #shares) and shares[k + 1].T * NIGHT or Math:Min(NIGHT, ts + 1.2 * Parameters.athar)
        sewAthar(k, ts, Math:Max(0.6 * Parameters.athar, te - ts))
        nextK = nextK + 1
    end
    -- stitches appear when the needle finishes them (a few strokes per frame at most)
    local drawn = 0
    local k = 1
    while k <= #stitchJobs and drawn < 3 do
        local jb = stitchJobs[k]
        if jb.t <= clock then
            drawInto(skyRec.layer, jb.pts, jb.brush, jb.size, jb.color, jb.pr)
            table.remove(stitchJobs, k)
            drawn = drawn + 1
        else
            k = k + 1
        end
    end
    if not finished then moveThread(clock) end
end

function Start()
    placed, reported, announced, finished = false, false, false, false
    recs, queue, clouds, stitchJobs, plan = {}, {}, {}, {}, {}
    cur, nextK, clock = nil, 1, 0
    stats = {strokes = 0}
    seed = 7
    startTime = App.time
    lastTime = App.time
    App:Error("Perforated Sky: on. Point to where the stars should rise and wait 3 seconds")
end

function Main()
    local ok, err = pcall(step)
    if not ok and not reported then
        reported = true
        App:Error("Perforated Sky error: " .. tostring(err))
    end
end

function End()
    for _, rec in ipairs(recs) do
        local keep = (Parameters.keep == 1) and (rec.kind == "sky" or rec.kind == "land") and rec.ready
        if rec.layer and not keep then pcall(function() rec.layer:Delete() end) end
    end
    recs, queue, clouds = {}, {}, {}
    pcall(function() Sketch.layers.active = Sketch.layers.main end)
    setLights(false)
    placed = false
end
