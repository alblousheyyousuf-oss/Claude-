#!/usr/bin/env python3
"""
دليل البناء المصوّر: كل كتلة على حدة ثم الدمج.
Illustrated build manual: every block on its own, then the merge.

Run:  python3 docs/vase/src/manual.py      (after vase.py; needs Playwright + Chromium for the PDF)
Writes docs/vase/manual/*.png, docs/vase/manual/manual.html and docs/vase/manual.pdf
"""
import math, os, subprocess, html
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from manifold3d import Manifold, CrossSection, FillRule
from shapely.geometry import Polygon
import vase as v

OUT = os.path.join(v.OUT, "manual")
K = 10.0 / (1 - v.SHRINK)                 # fired cm -> wet mm
wet = lambda cm: cm * K
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

CLAY, NEW, DONE, CONTACT, HOLE = (233, 226, 212), (240, 160, 70), (214, 206, 190), (246, 190, 110), (90, 84, 76)

S = v.slabs()
J = v.joints()
NAMES = {"B1": "الواجهة الأمامية", "B2": "الواجهة الخلفية", "B3": "الجانب الأيسر", "B4": "الجانب الأيمن",
         "B5": "السقف الأيسر", "B6": "السقف الأيمن", "B7": "القاع", "S1": "أرضية المقعد", "S2": "جدار المقعد الأيسر",
         "S3": "جدار المقعد الأيمن", "U1": "واجهة الصدر", "U2": "ظهر الصدر", "U3": "سطح الصدر", "U4": "جانب الصدر الأيمن",
         "U5": "جانب الصدر الأيسر", "U6": "قاع الصدر"}


# ───────────────────────── geometry of the slabs ─────────────────────────
def _holes(code):
    f = S[code]["f"]
    if code in ("U6", "S1"):
        return [Polygon(f.to2d(v.floor_window()[1]))]
    if code == "U3":
        th = np.linspace(0, 2 * np.pi, 96, endpoint=False)
        P = [np.array([v.NECK_C[0] + v.R_IN * math.cos(a), v.NECK_C[1] + v.R_IN * math.sin(a), 0]) for a in th]
        for p in P: p[2] = v.top_plane_z(p[0], p[1])
        return [Polygon(f.to2d(P))]
    return []


def _extrude(f, n_out, geom):
    out = []
    for p in getattr(geom, "geoms", [geom]):
        if p.geom_type != "Polygon" or p.area < 1e-4: continue
        cs = CrossSection([np.array(p.exterior.coords[:-1])] + [np.array(h.coords[:-1]) for h in p.interiors],
                          FillRule.EvenOdd)
        M = np.column_stack([f.e1, f.e2, -n_out, f.o])
        out.append(Manifold.extrude(cs, v.WALL).transform(M))
    return out


def slab(code, contact=False):
    """list of (manifold, tag) for one slab; tag 'contact' marks where a chest face sits in the seat."""
    s = S[code]; g = s["g2"]
    for h in _holes(code): g = g.difference(h)
    if contact and code[0] == "U":
        cut = s["f"].shapes()[1]
        if cut is not None:
            return [(m, "main") for m in _extrude(s["f"], s["n"], g.difference(cut))] + \
                   [(m, "contact") for m in _extrude(s["f"], s["n"], g.intersection(cut))]
    return [(m, "main") for m in _extrude(s["f"], s["n"], g)]


def neck():
    return v.modules()[0]["neck"]


# ───────────────────────── tiny z-buffer renderer ─────────────────────────
def camera(elev, azim):
    a, e = math.radians(azim), math.radians(elev)
    d = -np.array([math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)])
    r = np.cross(d, [0, 0, 1.0]); r /= np.linalg.norm(r)
    u = np.cross(r, d)
    return d, r, u


def render(parts, elev=24, azim=-30, size=(1000, 720), frame=None, margin=40):
    """parts: list of (manifold, rgb, offset3). Returns (PIL image, project(p3) -> (x, y))."""
    d, r, u = camera(elev, azim)
    W, H = size; ss = 2
    allv = []
    data = []
    for pi, part in enumerate(parts):
        m, col, off = part[:3]
        smooth = len(part) > 3 and part[3]
        me = m.to_mesh()
        V = np.asarray(me.vert_properties)[:, :3] + np.asarray(off, float)
        T = np.asarray(me.tri_verts)
        allv.append(V); data.append((V, T, col, pi, smooth))
    A = np.vstack(allv)
    sx, sy = A @ r, A @ u
    if frame is None: frame = (sx.min(), sx.max(), sy.min(), sy.max())
    x0, x1, y0, y1 = frame
    sc = min((W - 2 * margin) / (x1 - x0), (H - 2 * margin) / (y1 - y0))
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2

    def project(p):
        p = np.asarray(p, float)
        return (W / 2 + (p @ r - cx) * sc, H / 2 - (p @ u - cy) * sc)

    Ws, Hs = W * ss, H * ss
    zb = np.full((Hs, Ws), np.inf); img = np.full((Hs, Ws, 3), 255.0); fid = np.full((Hs, Ws), -1, np.int64)
    L = -d * 0.55 + u * 0.65 - r * 0.45; L /= np.linalg.norm(L)
    planes = {}
    for V, T, col, pi, smooth in data:
        X = (W / 2 + (V @ r - cx) * sc) * ss; Y = (H / 2 - (V @ u - cy) * sc) * ss; Z = V @ d
        for t in T:
            a_, b_, c_ = V[t]
            n = np.cross(b_ - a_, c_ - a_); ln = np.linalg.norm(n)
            if ln < 1e-12: continue
            n /= ln
            if smooth and abs(n[2]) < 0.97:
                key = (pi, "wall", n @ (a_ - V.mean(0)) > 0)
            else:
                key = (pi, round(abs(n[0]), 2), round(abs(n[1]), 2), round(abs(n[2]), 2), round(abs(n @ a_), 1))
            idv = planes.setdefault(key, len(planes))
            shade = 0.52 + 0.48 * abs(n @ L)
            xs, ys, zs = X[t], Y[t], Z[t]
            bx0, bx1 = max(int(xs.min()), 0), min(int(xs.max()) + 1, Ws - 1)
            by0, by1 = max(int(ys.min()), 0), min(int(ys.max()) + 1, Hs - 1)
            if bx1 < bx0 or by1 < by0: continue
            gx, gy = np.meshgrid(np.arange(bx0, bx1 + 1) + 0.5, np.arange(by0, by1 + 1) + 0.5)
            den = (ys[1] - ys[2]) * (xs[0] - xs[2]) + (xs[2] - xs[1]) * (ys[0] - ys[2])
            if abs(den) < 1e-9: continue
            w0 = ((ys[1] - ys[2]) * (gx - xs[2]) + (xs[2] - xs[1]) * (gy - ys[2])) / den
            w1 = ((ys[2] - ys[0]) * (gx - xs[2]) + (xs[0] - xs[2]) * (gy - ys[2])) / den
            w2 = 1 - w0 - w1
            ins = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
            if not ins.any(): continue
            z = w0 * zs[0] + w1 * zs[1] + w2 * zs[2]
            sub = zb[by0:by1 + 1, bx0:bx1 + 1]
            upd = ins & (z < sub - 1e-9)
            sub[upd] = z[upd]
            img[by0:by1 + 1, bx0:bx1 + 1][upd] = np.array(col, float) * shade
            fid[by0:by1 + 1, bx0:bx1 + 1][upd] = idv
    e = np.zeros((Hs, Ws), bool)
    e[:, 1:] |= fid[:, 1:] != fid[:, :-1]; e[1:, :] |= fid[1:, :] != fid[:-1, :]
    e2 = e.copy(); e2[1:, :] |= e[:-1, :]; e2[:, 1:] |= e[:, :-1]
    img[e2] = img[e2] * 0.25 + np.array([40, 36, 32]) * 0.75
    im = Image.fromarray(img.clip(0, 255).astype(np.uint8)).resize((W, H), Image.LANCZOS)
    return im, project


def arrow(dr, a, b, col=(31, 111, 178), w=6, head=22):
    a, b = np.array(a, float), np.array(b, float)
    t = b - a; L = np.linalg.norm(t)
    if L < 1e-6: return
    t /= L; n = np.array([-t[1], t[0]])
    tip = b; base = b - t * head
    dr.line([tuple(a), tuple(base)], fill=col, width=w)
    dr.polygon([tuple(tip), tuple(base + n * head * 0.45), tuple(base - n * head * 0.45)], fill=col)


def tag(dr, p, txt, col=(40, 36, 32), bg=(255, 255, 255), size=30):
    f = ImageFont.truetype(FONT, size)
    x0, y0, x1, y1 = dr.textbbox((0, 0), txt, font=f)
    w, h = x1 - x0, y1 - y0
    x, y = p[0] - w / 2, p[1] - h / 2
    dr.rounded_rectangle([x - 8, y - 6, x + w + 8, y + h + 10], radius=8, fill=bg, outline=col, width=3)
    dr.text((x - x0, y - y0), txt, font=f, fill=col)


def centroid(m, off=(0, 0, 0)):
    me = m.to_mesh(); V = np.asarray(me.vert_properties)[:, :3]
    return V.mean(0) + np.asarray(off, float)


# ───────────────────────── step pictures ─────────────────────────
def step_image(name, done, new, explode=6.0, elev=24, azim=32, transform=None, labels=True, extra=None,
               frame_codes=None, contact=False, size=(1000, 720), arrows=(), up=()):
    """done/new: slab codes; new slabs are drawn pulled out along their outward normal, with an arrow home."""
    def place(m):
        return m.transform(transform) if transform is not None else m

    def nrm_t(n):
        return (transform[:, :3] @ n) if transform is not None else n

    parts, notes = [], []
    for c in done:
        for m, tg in slab(c, contact):
            parts.append((place(m), CONTACT if tg == "contact" else DONE, (0, 0, 0)))
    for c in new:
        off = (np.array([0, 0, 1.0]) if c in up else nrm_t(S[c]["n"])) * explode
        for m, tg in slab(c, contact):
            parts.append((place(m), NEW, off))
        notes.append((c, off))
    if extra:
        parts += extra
    fr_parts = parts
    im, P = render(fr_parts, elev, azim, size)
    dr = ImageDraw.Draw(im)
    for c, off in notes:
        m0 = place(slab(c)[0][0])
        cen = centroid(m0)
        if explode >= 0.5: arrow(dr, P(cen + off * 1.0), P(cen + off * 0.25))
        if labels: tag(dr, P(cen + off * (1.08 if explode >= 0.5 else 1)), c, col=(170, 90, 10))
    for a3, b3 in arrows:
        arrow(dr, P(a3), P(b3), w=8, head=28)
    if labels:
        for c in done:
            cen = centroid(place(slab(c)[0][0]))
            # label only if that point is in view of the image
            x, y = P(cen)
            if 30 < x < size[0] - 30 and 30 < y < size[1] - 30 and c in (frame_codes or []):
                tag(dr, (x, y), c, size=24)
    path = os.path.join(OUT, name + ".png")
    im.save(path, optimize=True)
    return name + ".png"


def chest_lying():
    """build the chest lying on its front face U1 (outer face on the board)."""
    Rx = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]], float)     # (0,-1,0) -> (0,0,-1)
    pts = np.array([Rx @ p for p in S["U1"]["rings"][0]])
    t = np.array([-v.NECK_C[0], 0, -pts[:, 2].min()])
    return np.column_stack([Rx, t])


def edges_text(code):
    """'with B7: ∠52°' style summary of the cut of every edge of a slab, from the joint analysis."""
    seen = {}
    for a3, b3, lab, kind, cb, ang in J[code]:
        if lab is None or np.linalg.norm(b3 - a3) * K < 8: continue
        key = (cb, lab)
        seen[key] = seen.get(key, 0) + np.linalg.norm(b3 - a3) * K
    out = []
    for (cb, lab), L in sorted(seen.items(), key=lambda kv: -kv[1]):
        if "ظاهرة" in lab:
            out.append(f'<span class="eg" dir="rtl">ظاهرة <b dir="ltr">{html.escape(lab.split(" ")[0])}</b></span>')
        elif "حبل" in lab:
            out.append(f'<span class="eg" dir="rtl"><b dir="ltr">{cb}</b> ⟂ + حبل</span>')
        else:
            out.append(f'<span class="eg" dir="ltr">{cb} <b>{html.escape(lab)}</b></span>')
    return '<span class="egs">' + "".join(out) + "</span>"


# ───────────────────────── 2D diagrams (inline SVG) ─────────────────────────
SVG_ROLL = '''<svg viewBox="0 0 320 150" class="dg"><rect x="10" y="110" width="300" height="14" fill="#c9a77c"/>
<rect x="20" y="96" width="22" height="14" fill="#8d6e4c"/><rect x="278" y="96" width="22" height="14" fill="#8d6e4c"/>
<rect x="46" y="98" width="228" height="12" rx="3" fill="#e9e2d4" stroke="#555"/>
<rect x="30" y="66" width="260" height="28" rx="14" fill="#d8b98f" stroke="#6b4f2f"/><rect x="2" y="74" width="30" height="12" rx="6" fill="#6b4f2f"/><rect x="288" y="74" width="30" height="12" rx="6" fill="#6b4f2f"/>
<text x="31" y="140" font-size="13" text-anchor="middle">8 مم</text><text x="289" y="140" font-size="13" text-anchor="middle">8 مم</text>
<text x="160" y="50" font-size="14" text-anchor="middle">مسطرتان بسماكة 8 مم على الجانبين</text></svg>'''

SVG_BEVEL = '''<svg viewBox="0 0 320 170" class="dg">
<polygon points="40,130 200,130 184,114 40,114" fill="#e9e2d4" stroke="#333"/>
<polygon points="200,130 200,20 184,20 184,114" fill="#f0a046" stroke="#333"/>
<line x1="200" y1="130" x2="176" y2="106" stroke="#c0392b" stroke-width="2" stroke-dasharray="4,3"/>
<path d="M150,130 A50,50 0 0 0 165,95" fill="none" stroke="#7d3c98" stroke-width="2"/>
<text x="128" y="104" font-size="15" fill="#7d3c98">∠45°</text>
<text x="70" y="152" font-size="13">الوجه الظاهر</text><text x="208" y="70" font-size="13">الوجه الظاهر</text>
<text x="212" y="140" font-size="12" fill="#c0392b">سطح القطع</text></svg>'''

SVG_SCORE = '''<svg viewBox="0 0 320 150" class="dg"><rect x="30" y="70" width="260" height="22" fill="#e9e2d4" stroke="#333"/>
<polygon points="30,70 290,70 270,50 50,50" fill="#f6e3c4" stroke="#333"/>
''' + "".join(f'<line x1="{60 + i * 18}" y1="52" x2="{72 + i * 18}" y2="68" stroke="#9c640c" stroke-width="2"/>'
              f'<line x1="{72 + i * 18}" y1="52" x2="{60 + i * 18}" y2="68" stroke="#9c640c" stroke-width="2"/>' for i in range(11)) + '''
<rect x="210" y="8" width="70" height="12" rx="6" fill="#6b4f2f" transform="rotate(25 245 14)"/><polygon points="196,22 214,30 206,44 188,36" fill="#c9a77c"/>
<text x="160" y="125" font-size="14" text-anchor="middle">خدوش متقاطعة بعمق 1–2 مم، ثم طين سائل على الوجهين</text></svg>'''

SVG_COIL = '''<svg viewBox="0 0 320 170" class="dg">
<polygon points="40,140 280,140 280,124 56,124" fill="#e9e2d4" stroke="#333"/>
<polygon points="40,140 40,20 56,20 56,124" fill="#e9e2d4" stroke="#333"/>
<circle cx="64" cy="116" r="11" fill="#f0a046" stroke="#9c640c"/>
<text x="96" y="104" font-size="14">حبل طين يُضغط في الزاوية الداخلية</text>
<text x="96" y="124" font-size="12" fill="#555">ثم يُمسح بإصبع أو بأداة مدوّرة</text></svg>'''

SVG_TEMPLATE = '''<svg viewBox="0 0 320 160" class="dg"><rect x="20" y="40" width="280" height="100" fill="#e9e2d4" stroke="#999"/>
<polygon points="60,60 250,52 270,122 70,128" fill="#fff" fill-opacity="0.85" stroke="#111" stroke-width="2"/>
<line x1="250" y1="52" x2="290" y2="14" stroke="#555" stroke-width="5"/><circle cx="250" cy="52" r="3" fill="#c0392b"/>
<text x="160" y="155" font-size="13" text-anchor="middle">ضع القالب على الشريحة وقصّ حوله بسكين رفيعة عمودية</text></svg>'''


# ───────────────────────── the manual ─────────────────────────
def build():
    os.makedirs(OUT, exist_ok=True)
    H = []
    page = lambda inner, cls="": H.append(f'<section class="page {cls}">{inner}</section>')

    def result(img, title, items, check):
        return (f'<div class="result"><div class="pic s"><img src="{img}"/></div><div class="txt"><h3>{title}</h3>'
                + "".join(f"<p>{it}</p>" for it in items) + f'<div class="check"><b>تحقّق:</b> {check}</div></div></div>')

    def step(num, title, img, items, check=None, note=None):
        lis = "".join(f"<li>{it}</li>" for it in items)
        ck = f'<div class="check"><b>تحقّق:</b> {check}</div>' if check else ""
        nt = f'<div class="note">{note}</div>' if note else ""
        return (f'<div class="step"><div class="num">{num}</div><div class="txt"><h3>{title}</h3><ol>{lis}</ol>{ck}{nt}</div>'
                f'<div class="pic"><img src="{img}"/></div></div>')

    # pictures ─ base
    B = ["B7", "B1", "B2", "B3", "B4", "S1", "S2", "S3", "B5", "B6"]
    bview = dict(elev=30, azim=35)
    seat_view = dict(elev=52, azim=28)
    ib = [step_image("b1", [], ["B7"], explode=0.01, **bview),
          step_image("b2", ["B7"], ["B1", "B2"], **bview),
          step_image("b3", ["B7", "B1", "B2"], ["B3", "B4"], **bview),
          step_image("b4", ["B7", "B1", "B2", "B3", "B4"], ["S1"], explode=8, **seat_view),
          step_image("b5", ["B7", "B1", "B2", "B3", "B4", "S1"], ["S2", "S3"], explode=9, up=("S2", "S3"), **seat_view),
          step_image("b6", ["B7", "B1", "B2", "B3", "B4", "S1", "S2", "S3"], ["B5", "B6"], explode=6, **seat_view),
          step_image("b7", B, [], **seat_view)]
    # pictures ─ chest, built lying on its front face
    Tl = chest_lying()
    cview = dict(elev=38, azim=30, transform=Tl)
    ic = [step_image("c1", [], ["U1"], explode=0.01, **cview),
          step_image("c2", ["U1"], ["U6", "U5"], explode=6, **cview),
          step_image("c3", ["U1", "U6", "U5"], ["U4", "U3"], explode=6, **cview),
          step_image("c4", ["U1", "U6", "U5", "U4", "U3"], ["U2"], explode=7, **cview),
          step_image("c5", ["U1", "U2", "U3", "U4", "U5", "U6"], [], contact=True, elev=22, azim=35)]
    # pictures ─ neck
    nk = neck()
    im, P = render([(nk, NEW, (0, 0, 0), True)], 20, 30, (700, 620)); im.save(os.path.join(OUT, "n1.png"))
    # neck strip as flat drawing
    s, zb = v.neck_strip()
    pts = [(x * K, (v.H_TOTAL - z) * K) for x, z in zip(s, zb)]
    poly = pts + [(s[-1] * K, 0), (0, 0)]
    Wst = s[-1] * K; Hst = max(p[1] for p in pts)
    strip_svg = (f'<svg viewBox="-10 -16 {Wst + 20:.0f} {Hst + 40:.0f}" class="dg">'
                 f'<polygon points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in poly)}" fill="#f0a046" stroke="#333" stroke-width="1"/>'
                 f'<text x="{Wst / 2:.0f}" y="-4" font-size="9" text-anchor="middle">الحافة العليا = الفوهة (مستقيمة)</text>'
                 f'<text x="{Wst / 2:.0f}" y="{Hst + 16:.0f}" font-size="9" text-anchor="middle">الحافة السفلية المنحنية تجلس على سطح الصدر المائل</text></svg>')
    # pictures ─ merge
    allB = B; allU = ["U1", "U2", "U3", "U4", "U5", "U6"]
    slide = np.array([0, -16.0, 0])
    mview = dict(elev=26, azim=38)
    extra_chest = [(m, CONTACT if tg == "contact" else DONE, slide) for c in allU for m, tg in slab(c, True)]
    cc = (v.P1 + v.P4 + v.P5 + v.P6) / 4 + v.V / 2
    im1 = step_image("m1", allB, [], extra=extra_chest, labels=False, arrows=[(cc + slide * 0.55, cc + slide * 0.1)], **mview)
    seat_hi = [(m, CONTACT, (0, 0, 0)) for c in ("S1", "S2", "S3") for m, _ in slab(c)]
    im2 = step_image("m2", [c for c in allB if c[0] != "S"], [], extra=seat_hi + extra_chest, labels=False, **seat_view)
    im3 = step_image("m3", allB + allU, [], labels=False, elev=18, azim=40)
    lift = np.array([0, 0, 9.0])
    top = np.array([v.NECK_C[0], v.NECK_C[1], v.H_TOTAL])
    im4 = step_image("m4", allB + allU, [], labels=False, extra=[(nk, NEW, lift, True)], elev=22, azim=35,
                     arrows=[(top + lift + np.array([0, 0, 2.5]), top + lift * 0.15)])
    im5 = step_image("m5", allB + allU, [], labels=False, extra=[(nk, DONE, (0, 0, 0), True)], elev=v.CAM["E"], azim=-v.CAM["PHI"])

    # side view: vertical neck on the sloped chest top
    ang = math.radians(math.degrees(math.atan2(v.P1[2] - v.P4[2], v.P4[0] - v.P1[0])))
    Ro, Ri = v.R_OUT * K, v.R_IN * K
    cx0, base_y = 160, 120
    yl, yr = base_y - math.tan(ang) * Ro, base_y + math.tan(ang) * Ro
    top_y = min(yl, yr) - wet(v.neck_heights()[0])
    neck_side = (f'<svg viewBox="0 0 320 170" class="dg"><polygon points="20,{base_y - math.tan(ang) * 140:.0f} 300,{base_y + math.tan(ang) * 140:.0f} 300,168 20,168" fill="#e9e2d4" stroke="#333"/>'
                 f'<polygon points="{cx0 - Ro:.0f},{yl:.0f} {cx0 + Ro:.0f},{yr:.0f} {cx0 + Ro:.0f},{top_y:.0f} {cx0 - Ro:.0f},{top_y:.0f}" fill="#f0a046" stroke="#333"/>'
                 f'<line x1="{cx0 - Ri:.0f}" y1="{top_y:.0f}" x2="{cx0 - Ri:.0f}" y2="{yl - 4:.0f}" stroke="#555" stroke-dasharray="3,3"/>'
                 f'<line x1="{cx0 + Ri:.0f}" y1="{top_y:.0f}" x2="{cx0 + Ri:.0f}" y2="{yr - 4:.0f}" stroke="#555" stroke-dasharray="3,3"/>'
                 f'<line x1="{cx0:.0f}" y1="{top_y - 12:.0f}" x2="{cx0:.0f}" y2="{base_y + 30:.0f}" stroke="#1f6fb2" stroke-dasharray="6,3"/>'
                 f'<text x="{cx0 + 8:.0f}" y="{top_y - 4:.0f}" font-size="11" fill="#1f6fb2">رأسي</text>'
                 f'<text x="190" y="162" font-size="11">سطح الصدر U3 مائل {math.degrees(ang):.1f}°</text>'
                 f'<text x="{cx0 - Ro - 6:.0f}" y="{(yl + top_y) / 2:.0f}" font-size="10" text-anchor="end">{wet(v.neck_heights()[0]):.0f}</text>'
                 f'<text x="{cx0 + Ro + 6:.0f}" y="{(yr + top_y) / 2:.0f}" font-size="10">{wet(v.neck_heights()[1]):.0f}</text></svg>')

    # numbers used in the text
    w = lambda cm: f"{wet(cm):.0f}"
    hmin, hmax, _ = v.neck_heights()
    tilt = math.degrees(math.atan2(v.P1[2] - v.P4[2], v.P4[0] - v.P1[0]))
    clay = {kk: s_.volume() / (1 - v.SHRINK) ** 3 * 1.95 / 1000 for kk, s_ in v.modules()[1].items()}

    # ── cover
    page(f'''<div class="cover"><h1>دليل البناء والتركيب</h1><h2>المزهرية التكعيبية — ارتفاع 30 سم بعد الحرق</h2>
    <img class="hero" src="m5.png"/>
    <p class="lead">ثلاث كتل تُبنى كل منها وحدها كصندوق مغلق: <b>القاعدة</b> على شكل كرسي، و<b>الصدر</b> صندوق يجلس في مقعدها،
    و<b>الرأس</b> عنق أسطواني. بعد أن تبلغ الثلاث درجة الجلد الصلب نفسها تُدمج مرة واحدة بالتهشير والطين السائل.</p>
    <table class="toc"><tr><td>1</td><td>التحضير: الأدوات، الشرائح، قراءة القوالب، القطع المائل، التهشير</td></tr>
    <tr><td>2</td><td>الكتلة الأولى: القاعدة (الكرسي) — 6 خطوات</td></tr><tr><td>3</td><td>الكتلة الثانية: الصدر — 5 خطوات</td></tr>
    <tr><td>4</td><td>الكتلة الثالثة: الرأس — 3 خطوات</td></tr><tr><td>5</td><td>الدمج — 5 خطوات، ثم التجفيف والحرق</td></tr></table>
    <p class="small">كل المقاسات في هذا الدليل <b>بالمليمتر وبمقاس الطين الرطب</b> (ما تقيسه بيدك أثناء البناء)، إلا إذا ذُكر «بعد الحرق».
    محسوبة لانكماش 12%؛ اعمل اختبار الانكماش T1 أولاً.</p></div>''', "cv")

    # ── preparation
    page(f'''<h2 class="part">١ · التحضير</h2>
    <div class="grid2">
    <div class="box"><h3>الأدوات والمواد</h3><ul>
      <li>طين حجري أبيض بشاموت ناعم: <b>5 كجم</b> (القاعدة {clay["base"]:.1f} · الصدر {clay["chest"]:.1f} · الرأس {clay["neck"]:.2f} كجم صافٍ + هدر)</li>
      <li>نشّابة ومسطرتان خشبيتان بسماكة <b>8 مم</b> (أو آلة شرائح)</li>
      <li>سكين رفيعة حادة · إبرة طين · مسطرة معدنية · زاوية قائمة (گونيا)</li>
      <li>مقاييس زوايا من الكرتون: <b>45° · 50° · 52° · 54° · 37° · 31°</b> (تقصّها من ورق مقوى)</li>
      <li>أداة تهشير (شوكة أو مشط) · طين سائل (بربتين) · فرشاة · إسفنجة · أداة تنعيم (rib)</li>
      <li>لوح خشبي للبناء · قاعدة دوّارة إن وجدت · أكياس نايلون للتغطية</li>
      <li>أنبوب بقطر <b>51 مم</b> ملفوف بورق جرائد (للعنق) · فاصلان خشبيان سماكتهما <b>13.6 مم</b></li>
      <li>ملف القوالب <b>templates.pdf</b> مطبوعاً على A3 بمقياس 100%</li></ul></div>
    <div class="box"><h3>الترتيب الزمني</h3><ol>
      <li><b>اليوم 0:</b> اقطع شريحة الاختبار T1 واحرقها مع أول حرق متاح. إن خرجت المسافة 88 مم فالقوالب صحيحة، وإلا أعد الطباعة بمقياس 88 ÷ القياس × 100%.</li>
      <li><b>اليوم 1:</b> افرد كل الشرائح واتركها تتماسك حتى تُمسك شكلها دون أن تتشقق إذا ثُنيت قليلاً (بداية الجلد الصلب).</li>
      <li><b>اليوم 1–2:</b> اقطع القطع وابنِ الكتل الثلاث، كل واحدة وحدها، وغطِّها بالنايلون.</li>
      <li><b>اليوم 2–3:</b> حين تصل الثلاث إلى الجلد الصلب نفسه: الدمج.</li>
      <li><b>أسبوع:</b> تجفيف بطيء مغطى، ثم البسكويت والزجاج.</li></ol></div>
    </div>
    <div class="grid3">
    <div class="box">{SVG_ROLL}<h4>1 · فرد الشرائح</h4><p>افرد الطين بين المسطرتين حتى تلمسهما النشّابة، فتخرج السماكة 8 مم في كل مكان. اقلب الشريحة وافرد الجهة الأخرى حتى لا تلتوي.</p></div>
    <div class="box">{SVG_TEMPLATE}<h4>2 · القص بالقالب</h4><p>قصّ القالب الورقي على الخط الأسود. ضعه على الشريحة، وقصّ حوله عمودياً أولاً. الثقوب والنوافذ (إطار أحمر) تُقصّ وتُرمى. الخط الأحمر المتقطع يُنقل بوخز الإبرة عبر الورق كل 1 سم.</p></div>
    <div class="box">{SVG_BEVEL}<h4>3 · قراءة الزاوية البنفسجية</h4><p><b>∠45°</b> مكتوبة على حافة = اقطع تلك الحافة مائلة بحيث تكون الزاوية بين الوجه الظاهر وسطح القطع 45°. الحافة المقابلة في القطعة الأخرى عليها الرقم نفسه، فتلتقيان بلا فراغ. اقطع المائل <b>بعد</b> القص العمودي، والقالب ما زال فوق الشريحة ليحفظ الخط الخارجي.</p></div>
    <div class="box">{SVG_SCORE}<h4>4 · التهشير واللصق</h4><p>خطّط سطحي الالتقاء كليهما، وادهنهما بالطين السائل، واضغطهما معاً وحرّك قليلاً حتى «يمسك». امسح الفائض. المساحات البرتقالية المخططة على القوالب تُهشَّر كلها.</p></div>
    <div class="box">{SVG_COIL}<h4>5 · الزوايا الداخلية</h4><p>«⟂ + حبل» على حافة = اقطعها عمودية، وبعد اللصق اضغط حبل طين رفيعاً (قطره 5–6 مم) في الزاوية من الداخل وامسحه.</p></div>
    <div class="box"><h4>6 · قواعد ثابتة</h4><ul class="tight"><li>القوالب = الشكل <b>الخارجي</b>؛ كل القطع المائل يكون من الداخل.</li>
      <li>B1 = B2 وU1 = U2: قطعتان من القالب نفسه، الثانية بقلبه.</li><li>اضغط كل وصلة من الداخل بإصبع أو أداة، ومن الخارج بمسطرة.</li>
      <li>غطِّ كل ما لا تعمل عليه بالنايلون.</li></ul></div>
    </div>''')

    # ── base
    jB = {c: edges_text(c) for c in B}
    page('<h2 class="part">٢ · الكتلة الأولى: القاعدة (الكرسي)</h2><p class="intro">القاعدة صندوق مغلق من 10 شرائح: ذراع يسرى منخفضة، وذراع يمنى عالية، وبينهما مقعد مفتوح من الأمام والخلف والأعلى، يجلس فيه الصدر لاحقاً. الواجهتان الأمامية والخلفية رأسيتان تماماً، والجانبان مائلان للخارج 14°.</p>' +
         step(1, "القاع B7", ib[0], [
             "اقطع B7 من القالب (مستطيل 136 × 95 مم).",
             f"اشطف حوافه حسب الحافة المجاورة: {jB['B7']}",
             "ضعه على لوح البناء، والوجه الظاهر (الأسفل) على اللوح فوق قطعة قماش أو جرائد حتى لا يلتصق."],
             check="الطول 136 والعرض 95 مم، والزوايا قائمة بالگونيا.") +
         step(2, "الواجهتان B1 وB2", ib[1], [
             "اقطع قطعتين من قالب B1 = B2: الأولى كما هي (B1 الأمامية) والثانية بقلب القالب (B2 الخلفية).",
             f"اشطف الحواف: {jB['B1']}",
             "الفتحة الكبيرة في الأعلى هي مكان المقعد؛ حوافها تلتقي بـ S1 وS2 وS3.",
             "هشّر الحافة الطويلة لـ B7 وأسفل B1، والصق B1 <b>رأسية تماماً</b> على الحافة الأمامية لـ B7. كرّر B2 على الحافة الخلفية.",
             "ادعمهما من الخارج بقطعتين خشبيتين حتى لا تميلا."],
             check="الواجهتان رأسيتان بالگونيا ومتوازيتان، والمسافة بينهما من الخارج 95 مم في الأسفل والأعلى.") +
         step(3, "الجانبان B3 (يسار) وB4 (يمين)", ib[2], [
             f"B3: {jB['B3']}",
             f"B4: {jB['B4']}",
             "الجانبان <b>مائلان للخارج 14°</b>: الصق كل جانب على حافة B7 والحافتين الجانبيتين لـ B1 وB2، وضع خلفه مقياس كرتون بزاوية 76° مع اللوح (أي 14° عن الرأسي) حتى يتماسك.",
             "B3 أقصر (176 مم) لأن الكتف الأيسر أخفض؛ B4 أطول (208 مم)."],
             check=f"الحافة العليا لـ B3 على {w(v.EAVE_L)} مم من اللوح، ولـ B4 على {w(v.EAVE_R)} مم. العرض الخارجي بين أعلى الجانبين ≈ {w(v.xR - v.xL)} مم."))
    page(step(4, "أرضية المقعد S1", ib[3], [
             "اقطع S1 وقصّ نافذتها (الإطار الأحمر).",
             f"اشطف الحواف: {jB['S1']}",
             "الأعلى ما زال مفتوحاً، فتصل يدك إلى الداخل. أنزل S1 من فوق، وألصق حافتيها <b>الطويلتين (116 مم)</b> على الحافتين السفليتين لفتحتي B1 وB2. حافتاها القصيرتان (95 مم) ستلتقيان بجداري المقعد.",
             "S1 مائلة نحو اليمين (لأن قاع الصدر مائل): ثبّتها على الحواف المقطوعة في B1 وB2 كما هي، ولا تحاول جعلها أفقية."],
             check=f"الحافة الأمامية لـ S1 على {w(v.P6[2])} مم من اللوح عند اليسار و{w(v.P5[2])} مم عند اليمين، وكذلك في الخلف.") +
         step(5, "جدارا المقعد S2 (يسار) وS3 (يمين)", ib[4], [
             f"S2: {jB['S2']}",
             f"S3: {jB['S3']}",
             "ألصق كل جدار بين حافة أرضية المقعد وحافتي فتحة B1 وB2.",
             "<b>الآن، قبل إغلاق السقف:</b> مدّ يدك إلى الداخل واضغط حبل طين في زاويتي الأرضية مع الجدارين (⟂ + حبل)، وامسحه."],
             note="بعد السقف لن تصل إلى هذه الزوايا، فلا تؤجلها.") +
         step(6, "السقف B5 (يسار) وB6 (يمين)", ib[5], [
             f"B5: {jB['B5']}",
             f"B6: {jB['B6']}",
             "ألصق B5 بين أعلى B3 وأعلى جدار المقعد S2، وB6 بين أعلى S3 وأعلى B4. كلاهما يميل 25°.",
             "حافتاهما الأمامية والخلفية تلتقيان بأعلى B1 وB2."],
             check="لا توجد فتحات إلا نافذة S1. اضغط كل الوصلات من الخارج بمسطرة ونعّمها."))
    H[-1] = H[-1].replace("</section>", result(ib[6], "النتيجة: القاعدة جاهزة", [
             "الكرسي الآن صندوق مغلق: ذراع يسرى منخفضة، ذراع يمنى عالية، والمقعد بينهما. الداخل لا يُرى إلا من نافذة S1؛ أدخل إصبعين ونعّم ما تصل إليه، ثم غطِّ القاعدة بالنايلون حتى يوم الدمج."],
             f"الكتف الأيسر {w(v.EAVE_L)} مم · الأيمن {w(v.EAVE_R)} مم · عرض المقعد عند أرضيته من الأمام {w(np.linalg.norm(v.P5 - v.P6))} مم · عمق القاعدة 95 مم.") + "</section>")

    # ── chest
    jU = {c: edges_text(c) for c in ["U1", "U2", "U3", "U4", "U5", "U6"]}
    page('<h2 class="part">٣ · الكتلة الثانية: الصدر</h2><p class="intro">الصدر صندوق مغلق من 6 شرائح، واجهته وظهره متطابقان (U1 = U2) وكل جوانبه عمودية عليهما. أسهل طريقة: تبنيه <b>مستلقياً على واجهته U1</b>، فتقف الجوانب الأربعة رأسية على اللوح، ثم تغلقه بالظهر U2.</p>' +
         step(1, "الواجهة U1 على اللوح", ic[0], [
             "اقطع قطعتين من قالب U1 = U2، الثانية بقلب القالب.",
             f"اشطف حواف الاثنتين: {jU['U1']}",
             "ضع U1 على اللوح ووجهها الظاهر إلى الأسفل. هذا الشكل الرباعي غير المنتظم هو مرجع الصدر كله."],
             check="أضلاع U1: 116 · 132 · 150 · 173 مم كما في القالب.") +
         step(2, "القاع U6 والجانب الأيسر U5", ic[1], [
             f"U6 (اقطع نافذتها): {jU['U6']}",
             f"U5: {jU['U5']}",
             "قف U6 على الضلع 116 لـ U1، وU5 على الضلع 173، كلاهما <b>عمودي</b> على U1 (تحقق بالگونيا).",
             "الزاوية بين U5 وU6 ليست قائمة؛ اتبع ضلعي U1 تماماً."],
             check="ارتفاع الجدارين فوق اللوح 123 مم (عمق الصدر).") +
         step(3, "الجانب الأيمن U4 والسطح U3", ic[2], [
             f"U4: {jU['U4']}",
             f"U3 (اقطع فتحة العنق Ø51، الدائرة الحمراء): {jU['U3']}",
             "قف U4 على الضلع 150 وU3 على الضلع 132، عموديين على U1.",
             "انتبه لاتجاه U3: فتحة العنق أقرب إلى جهة U4 (يمين الصدر)."],
             check="الجدران الأربعة عمودية على U1 وارتفاعها كلها 123 مم، وزوايا الإطار تطابق زوايا U1."))
    page(step(4, "الظهر U2 يغلق الصدر", ic[3], [
             "هشّر الحواف العليا للجدران الأربعة والحافة الداخلية لـ U2.",
             "أنزل U2 فوقها (مقلوبة عن U1) بحيث تطابق كل ضلع من أضلاعها الجدار تحته.",
             "اضغط من الأعلى بلطف بلوح خشبي مستوٍ، ثم أدخل أصابعك من فتحة U3 ونافذة U6 ونعّم الوصلات من الداخل."],
             check="الصندوق لا يتأرجح على اللوح، وU1 وU2 متوازيتان والمسافة بينهما 123 مم في كل الأركان.") +
         step(5, "الصدر جاهز (قائماً)", ic[4], [
             "اقلب الصدر برفق على قاعه U6 ليقف كما سيقف في القطعة.",
             "انقل الخط الأحمر المتقطع من قوالب U4 وU5 وU6 إلى الصدر بوخز الإبرة: هو حافة المقعد.",
             "المساحة البرتقالية في الرسم هي التي ستلتصق بالمقعد؛ لا تنعّمها، ستُهشَّر يوم الدمج.",
             "غطِّه بالنايلون."],
             check="سطح الصدر U3 يميل 20.6° نحو اليمين، وقاعه U6 يميل 11° نحو اليمين."))

    # ── neck
    page(f'''<h2 class="part">٤ · الكتلة الثالثة: الرأس (العنق والفوهة)</h2><p class="intro">العنق أسطوانة قطرها {w(v.R_OUT * 2)} مم من الخارج و{w(v.R_IN * 2)} مم من الداخل.
    حافتها العليا مستقيمة (الفوهة)، وحافتها السفلية مقصوصة بميل {tilt:.1f}° لتجلس على سطح الصدر المائل. يُصنع بإحدى طريقتين:</p>
    <div class="step"><div class="num">1</div><div class="txt"><h3>بالشريحة N1</h3><ol>
      <li>افرد شريحة بسماكة 6–7 مم واقطع N1 من القالب (طولها {s[-1] * K:.0f} مم).</li>
      <li>لفّ الأنبوب Ø51 بورق جرائد، ثم لفّ N1 حوله والحافة المستقيمة إلى الأعلى.</li>
      <li>اشطف الطرفين 45° بعكس بعضهما، هشّرهما، وألصقهما. نعّم خط اللحام من الخارج.</li>
      <li>علّم بقلم رصاص موضع <b>الضلع الأقصر</b> (الخط الأزرق في القالب): هذه الجهة تتجه إلى اليسار في القطعة.</li>
      <li>انتظر ساعة ثم اسحب الأنبوب، واترك الورق يخرج وحده.</li></ol>
      <div class="check"><b>تحقّق:</b> القطر الخارجي {w(v.R_OUT * 2)} مم، الارتفاع {wet(hmin):.0f} مم في الجهة القصيرة و{wet(hmax):.0f} مم في الطويلة.</div></div>
      <div class="pic">{strip_svg}</div></div>
    <div class="step"><div class="num">2</div><div class="txt"><h3>أو على الدولاب</h3><ol>
      <li>ارمِ أسطوانة جدارها 6–7 مم: قطرها الخارجي {w(v.R_OUT * 2)} مم والداخلي {w(v.R_IN * 2)} مم، وارتفاعها 75 مم على الأقل.</li>
      <li>اقطعها عن الدولاب واتركها تتماسك.</li>
      <li>علّم على جانبها خطاً بارتفاع {wet(hmin):.0f} مم وعلى الجانب المقابل {wet(hmax):.0f} مم، وصِل بينهما بخط مائل حول الأسطوانة.</li>
      <li>اقطع على الخط المائل بسكين رفيعة: هذه قاعدة العنق، والحافة العليا تبقى مستقيمة.</li></ol></div>
      <div class="pic"><img src="n1.png"/></div></div>
    <div class="step"><div class="num">3</div><div class="txt"><h3>تجهيز القاعدة المائلة</h3><ol>
      <li>ضع العنق على قالب U3 الورقي: يجب أن تنطبق قاعدته على البيضاوي المنقط حول الدائرة الحمراء.</li>
      <li>اقطع القاعدة بانحناء خفيف من الداخل (شطف 20°) حتى تجلس على السطح المائل بلا فراغ.</li>
      <li>غطِّ العنق بالنايلون. لا تلصقه قبل الدمج.</li></ol>
      <div class="check"><b>تحقّق:</b> حين يوضع العنق رأسياً على سطح مائل {tilt:.1f}°، تكون فوهته أفقية.</div></div>
      <div class="pic">{neck_side}</div></div>''')

    # ── merge
    page('<h2 class="part">٥ · الدمج</h2><p class="intro">ابدأ الدمج فقط حين تكون الكتل الثلاث <b>بدرجة الجلد الصلب نفسها</b>: تُمسك شكلها، ولا تترك عليها الأصابع أثراً، لكنها ما زالت باردة ورطبة عند اللمس. اختلاف الرطوبة هو السبب الأول لتشقق الوصلات.</p>' +
         step(1, "تجربة جافة: الصدر يدخل المقعد كالدُّرج", im1, [
             "ضع القاعدة على اللوح، والصدر أمامها قائماً على قاعه U6.",
             "أدخل الصدر في المقعد من الأمام، مستقيماً للخلف (اتجاه السهم)، دون طين سائل.",
             f"أوقفه حين يبرز <b>{wet(v.PROUD):.1f} مم</b> من الأمام و{wet(v.PROUD):.1f} مم من الخلف. استعمل الفاصلين الخشبيين للقياس.",
             "إن احتكّ في مكان، علّمه وشذّبه قليلاً؛ ثم أخرج الصدر."],
             check=f"زاويتا واجهة الصدر السفليتان على {w(v.P6[2])} مم (يسار) و{w(v.P5[2])} مم (يمين) من اللوح، ونافذة U6 فوق نافذة S1 تماماً.") +
         step(2, "التهشير والطين السائل", im2, [
             "خطّط وجوه المقعد الثلاثة (برتقالي في الرسم): الأرضية S1 والجداران S2 وS3.",
             "خطّط على الصدر المساحة البرتقالية تحت الخط الأحمر في U4 وU5 وU6.",
             "ادهن الطين السائل على الجهتين بطبقة متوسطة، وأكثر منه قرب الحواف الداخلية التي لن تصلها يدك."]))
    page(step(3, "إدخال الصدر وتثبيته", im3, [
             "أدخل الصدر كما في التجربة الجافة حتى يتساوى بروزه أماماً وخلفاً.",
             "اضغطه لأسفل وللجانبين بثبات حتى يخرج الطين السائل الزائد من الحواف.",
             "امسح الفائض، ثم مرّر حبل طين رفيعاً على حواف المقعد من الخارج (أمام وخلف وأعلى الذراعين) ونعّمه.",
             "من نافذة U3 (فتحة العنق) مدّ أداة طويلة ونعّم ما تصل إليه حول النافذتين."],
             check=f"البروز {wet(v.PROUD):.1f} مم من الجهتين · الصدر غير مائل للأمام أو الخلف · الكتف الأيسر {w(v.EAVE_L)} والأيمن {w(v.EAVE_R)} مم.") +
         step(4, "تثبيت الرأس", im4, [
             "خطّط الحلقة البرتقالية حول فتحة U3، وقاعدة العنق المائلة، وادهنهما بالطين السائل.",
             "ضع العنق <b>رأسياً</b> فوق الفتحة والضلع الأقصر نحو اليسار، واضغطه وأدِره قليلاً يميناً ويساراً حتى يمسك.",
             "تحقق بالگونيا من جهتين أنه رأسي، ثم نعّم الوصلة من الخارج بحبل طين رفيع، ومن الداخل بإصبع عبر الفوهة."],
             check=f"الفوهة على <b>{w(v.H_TOTAL)} مم</b> من اللوح وأفقية · محور العنق في منتصف العمق بين الأمام والخلف.") +
         step(5, "القطعة كاملة: التجفيف والحرق", im5, [
             "غطِّ القطعة بالنايلون كاملة، واكشفها قليلاً كل يوم لمدة أسبوع تقريباً حتى تجف ببطء ومن كل الجهات بالتساوي.",
             "حين تجف تماماً (لونها فاتح ولا برودة فيها): حرق البسكويت.",
             "لتحمل ماء: ازجج الداخل بطلاء بطانة (اسكبه، أدِره، وأفرغه). الخارج مطفأ أو أبيض مطفأ كما في الصورة.",
             "الحرق النهائي حسب طينك وزجاجك."],
             check="بعد الحرق: الارتفاع 300 مم، العرض الأقصى 202 مم، العمق 108 مم.") +
         f'''<div class="box final"><h3>جدول التحقق النهائي (رطب ← بعد الحرق)</h3><table class="ck">
         <tr><th>المقاس</th><th>رطب</th><th>بعد الحرق</th></tr>
         <tr><td>الفوهة من الطاولة</td><td>{w(v.H_TOTAL)}</td><td>300</td></tr>
         <tr><td>الكتف الأيسر</td><td>{w(v.EAVE_L)}</td><td>{v.EAVE_L * 10:.0f}</td></tr>
         <tr><td>الكتف الأيمن</td><td>{w(v.EAVE_R)}</td><td>{v.EAVE_R * 10:.0f}</td></tr>
         <tr><td>زاويتا واجهة الصدر السفليتان</td><td>{w(v.P6[2])} / {w(v.P5[2])}</td><td>{v.P6[2] * 10:.0f} / {v.P5[2] * 10:.0f}</td></tr>
         <tr><td>بروز الصدر أماماً وخلفاً</td><td>{wet(v.PROUD):.1f}</td><td>{v.PROUD * 10:.0f}</td></tr>
         <tr><td>العرض الأقصى (بين الكتفين)</td><td>{w(v.xR - v.xL)}</td><td>{(v.xR - v.xL) * 10:.0f}</td></tr>
         <tr><td>عمق القاعدة / الصدر</td><td>95 / 123</td><td>84 / 108</td></tr>
         <tr><td>قطر العنق</td><td>{w(v.R_OUT * 2)} / {w(v.R_IN * 2)}</td><td>{v.R_OUT * 20:.0f} / {v.R_IN * 20:.0f}</td></tr></table></div>''')

    css = '''@page{size:210mm 297mm;margin:0}*{box-sizing:border-box}body{margin:0;font-family:"Noto Naskh Arabic",Tahoma,Arial,sans-serif;color:#1d1b18;direction:rtl}
    .page{width:210mm;height:297mm;padding:12mm 12mm 10mm;page-break-after:always;overflow:hidden;position:relative}
    .page:last-child{page-break-after:auto}h1{font-size:30pt;margin:6mm 0 1mm}h2{font-size:15pt;margin:0 0 4mm;color:#555}
    h2.part{font-size:20pt;color:#1f6fb2;border-bottom:2px solid #1f6fb2;padding-bottom:2mm;margin-bottom:3mm}
    h3{font-size:12.5pt;margin:0 0 1.5mm}h4{font-size:11pt;margin:1mm 0}p,li,td{font-size:9.6pt;line-height:1.5}
    .intro{background:#f3f7fb;border-right:4px solid #1f6fb2;padding:2.5mm 4mm;margin:0 0 3mm}
    .step{display:flex;gap:4mm;align-items:flex-start;border:1px solid #ddd;border-radius:3mm;padding:3mm;margin-bottom:3mm;break-inside:avoid}
    .num{flex:0 0 11mm;height:11mm;border-radius:50%;background:#f0a046;color:#fff;font:bold 15pt Arial;display:flex;align-items:center;justify-content:center}
    .txt{flex:1 1 52%}.pic{flex:0 0 44%}.pic img{width:100%;display:block}.pic svg{width:100%}
    ol{margin:0;padding-right:5mm}ul{margin:0;padding-right:5mm}li{margin-bottom:1mm}
    .check{margin-top:2mm;background:#eef7ee;border-right:4px solid #3a8a3a;padding:1.5mm 3mm;font-size:9.4pt}
    .note{margin-top:2mm;background:#fff4e5;border-right:4px solid #d68910;padding:1.5mm 3mm;font-size:9.4pt}
    .grid2{display:grid;grid-template-columns:1fr 1fr;gap:4mm;margin-bottom:4mm}.grid3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:3mm}
    .box{border:1px solid #ddd;border-radius:3mm;padding:3mm}.box p{margin:1mm 0 0;font-size:8.8pt}.dg{width:100%;height:auto;font-family:Tahoma,Arial;direction:ltr}
    .tight li{font-size:8.8pt}.cover{text-align:center}.hero{width:62%;margin:2mm auto}.lead{font-size:11.5pt;line-height:1.7;text-align:justify}
    .toc{margin:4mm auto;border-collapse:collapse;width:85%}.toc td{border-bottom:1px solid #ddd;padding:1.8mm;text-align:right;font-size:11pt}
    .toc td:first-child{width:10mm;color:#fff;background:#1f6fb2;text-align:center;font-weight:bold}
    .small{font-size:9.5pt;color:#555}
    .egs{display:inline}.eg{display:inline-block;border:1px solid #cdb9e3;background:#f6f0fb;color:#4a2470;border-radius:1.5mm;padding:0 1.6mm;margin:0.4mm 0.6mm;font-size:8.8pt;white-space:nowrap}
    .result{display:flex;gap:4mm;align-items:center;border:2px solid #3a8a3a;border-radius:3mm;padding:3mm;margin-top:2mm;flex-direction:row-reverse}
    .pic.s{flex:0 0 30%}.ck{border-collapse:collapse;width:100%}.ck th,.ck td{border:1px solid #ccc;padding:0.7mm 2mm;text-align:center;font-size:9pt;line-height:1.3}
    .ck th{background:#f3f7fb}.final{margin-top:1mm;padding:2mm 3mm}.final h3{margin-bottom:1mm}'''
    doc = f'<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><title>دليل البناء</title><style>{css}</style></head><body>{"".join(H)}</body></html>'
    hp = os.path.join(OUT, "manual.html")
    with open(hp, "w", encoding="utf-8") as fh: fh.write(doc)
    return hp


if __name__ == "__main__":
    hp = build()
    pdf = os.path.join(v.OUT, "manual.pdf")
    js = os.path.join(os.path.dirname(os.path.abspath(__file__)), "html_pdf.js")
    subprocess.run(["node", js, hp, pdf], check=True)
    print("wrote", pdf)
