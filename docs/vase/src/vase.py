#!/usr/bin/env python3
"""
مزهرية تكعيبية — نموذج بارامتري معاد بناؤه من صورة واحدة
Cubist vase — parametric reconstruction from a single photo.

All design values are FIRED size in cm (total height = 30 cm).
Run:  python3 vase.py            -> regenerates every asset in ../
Deps: numpy, pillow, manifold3d, shapely
"""
import math, os, struct, sys
import numpy as np
from PIL import Image, ImageDraw
from manifold3d import Manifold
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)
PHOTO = os.path.join(OUT, "reference.jpg")

# ───────────────────────── design parameters (fired, cm) ─────────────────────────
H_TOTAL = 30.0            # rim height
W0, D0 = 12.0, 8.4        # base footprint (front width × depth)
FLARE = 14.0              # side faces lean outward (deg); front/back faces are vertical
EAVE_L, EAVE_R = 15.0, 17.8   # height of base top at left / right corner
ROOF = 25.0               # both roof slopes of the base (deg)
PROUD = 1.2               # upper block front face stands proud of base front face
# upper block front face (x, z) on plane y = -(D0/2 + PROUD):  P6, P1, P4, P5
UPPER_FRONT = [(-6.1, 12.2), (-5.1, 27.4), (5.8, 23.3), (3.9, 10.2)]
UPPER_V = (2.9, 9.0, -0.9)    # extrusion (depth) vector of the upper block
NECK_OD, NECK_ID = 5.8, 4.5   # neck outer / inner diameter
WALL, FLOOR = 0.8, 1.0        # slab thickness, base floor thickness
SHRINK = 0.12                 # total clay shrinkage (wet -> fired)

# camera recovered from the photo (orthographic): used only for the fit check
CAM = dict(E=12.7, PHI=-32.2, K=18.975, U0=443.5, V0=878.3)

# ───────────────────────── derived geometry ─────────────────────────
tw = math.tan(math.radians(FLARE))
sr = math.tan(math.radians(ROOF))
yb = -D0 / 2                          # base front plane
yf = yb - PROUD                       # upper block front plane
xL = -(W0 / 2 + tw * EAVE_L)          # left eave x
xR = W0 / 2 + tw * EAVE_R             # right eave x
x_ridge = (EAVE_R - EAVE_L + sr * (xR + xL)) / (2 * sr)
z_ridge = EAVE_L + sr * (x_ridge - xL)
V = np.array(UPPER_V, float)
P6, P1, P4, P5 = [np.array([x, yf, z]) for x, z in UPPER_FRONT]
P2, P3 = P1 + V, P4 + V
NECK_C = (P1 + P4) / 2 + V / 2        # centre of upper top face
R_OUT, R_IN = NECK_OD / 2, NECK_ID / 2


def nrm(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def base_halfspaces():
    H = [((0, 0, -1), 0), ((0, -1, 0), D0 / 2), ((0, 1, 0), D0 / 2),
         ((-1, 0, -tw), W0 / 2), ((1, 0, -tw), W0 / 2),
         ((-sr, 0, 1), EAVE_L - sr * xL), ((sr, 0, 1), EAVE_R + sr * xR)]
    out = []
    for n, c in H:
        n = np.array(n, float); L = np.linalg.norm(n)
        out.append((n / L, c / L))
    return out


def prism_halfspaces(face, v):
    F = np.array(face); cen = F.mean(0) + v / 2
    H = []
    nf = nrm(np.cross(F[1] - F[0], F[2] - F[0]))
    for n, p in [(nf, F[0]), (-nf, F[0] + v)]:
        if n @ (cen - p) > 0: n = -n
        H.append((n, n @ p))
    for i in range(len(F)):
        a, b = F[i], F[(i + 1) % len(F)]
        n = nrm(np.cross(b - a, v))
        if n @ (cen - a) > 0: n = -n
        H.append((n, n @ a))
    return H


def upper_halfspaces():
    return prism_halfspaces([P6, P1, P4, P5], V)


def inset(H, t, floor=None):
    out = []
    for n, c in H:
        d = floor if (floor is not None and n[2] < -0.99) else t
        out.append((n, c - d))
    return out


def hs_vertices(H):
    pts = []
    for i in range(len(H)):
        for j in range(i + 1, len(H)):
            for k in range(j + 1, len(H)):
                A = np.array([H[i][0], H[j][0], H[k][0]])
                if abs(np.linalg.det(A)) < 1e-9: continue
                p = np.linalg.solve(A, [H[i][1], H[j][1], H[k][1]])
                if all(n @ p <= c + 1e-7 for n, c in H): pts.append(p)
    return np.unique(np.round(pts, 9), axis=0)


def hull(H):
    return Manifold.hull_points(hs_vertices(H))


def top_plane_z(x, y):
    """z of the upper block top face (plane through P1, P4, P2)."""
    n = np.cross(P4 - P1, P2 - P1)
    return P1[2] - (n[0] * (x - P1[0]) + n[1] * (y - P1[1])) / n[2]


def neck_z0():
    th = np.linspace(0, 2 * np.pi, 361)
    return min(top_plane_z(NECK_C[0] + R_OUT * np.cos(th), NECK_C[1] + R_OUT * np.sin(th))) - 1.5


def cylinder(r, z0, z1, seg=96):
    return Manifold.cylinder(z1 - z0, r, r, seg).translate([NECK_C[0], NECK_C[1], z0])


def solids():
    base, upper = hull(base_halfspaces()), hull(upper_halfspaces())
    neck = cylinder(R_OUT, neck_z0(), H_TOTAL)
    solid = base + upper + neck
    cavity = (hull(inset(base_halfspaces(), WALL, FLOOR)) + hull(inset(upper_halfspaces(), WALL))
              + cylinder(R_IN, 18.0, H_TOTAL + 1))
    hollow = solid - cavity
    bore = solid - cylinder(R_IN, 20.0, H_TOTAL + 1)   # solid with the neck opening (for drawings)
    return dict(base=base, upper=upper, neck=neck, solid=solid, cavity=cavity, hollow=hollow, bore=bore)


# ───────────────────────── STL ─────────────────────────
def mesh_arrays(m):
    me = m.to_mesh()
    return np.asarray(me.vert_properties)[:, :3].astype(float), np.asarray(me.tri_verts).astype(int)


def write_stl(m, path, scale=10.0):
    Vt, T = mesh_arrays(m); Vt = Vt * scale
    with open(path, "wb") as f:
        f.write(b"cubist vase (mm)".ljust(80, b" "))
        f.write(struct.pack("<I", len(T)))
        for t in T:
            a, b, c = Vt[t]
            n = np.cross(b - a, c - a); L = np.linalg.norm(n); n = n / L if L else n
            f.write(struct.pack("<12fH", *n, *a, *b, *c, 0))


# ───────────────────────── photo fit check ─────────────────────────
def render_photo_check(path):
    E, PHI, K, U0, V0 = (math.radians(CAM["E"]), math.radians(CAM["PHI"]), CAM["K"], CAM["U0"], CAM["V0"])
    CE, SE, CP, SP = math.cos(E), math.sin(E), math.cos(PHI), math.sin(PHI)
    photo = Image.open(PHOTO).convert("RGB"); Wd, Ht = photo.size
    X, Y = np.meshgrid(np.arange(Wd) + .5, np.arange(Ht) + .5)
    u = (X - U0) / K; v = (V0 - Y) / K
    oc = np.stack([u, np.full_like(u, -80), (v + 80 * SE) / CE], -1)
    inv = lambda q: np.stack([CP * q[..., 0] + SP * q[..., 1], -SP * q[..., 0] + CP * q[..., 1], q[..., 2]], -1)
    O = inv(oc); R = inv(np.array([[[0, CE, -SE]]]))[0, 0]
    neckH = [((0, 0, 1.), H_TOTAL), ((0, 0, -1.), -neck_z0())]
    for i in range(96):
        a = 2 * np.pi * (i + .5) / 96; n = np.array([np.cos(a), np.sin(a), 0])
        neckH.append((n, n @ NECK_C + R_OUT * np.cos(np.pi / 96)))
    neckH = [(np.array(n, float), c) for n, c in neckH]
    best = np.full(u.shape, np.inf); fid = np.full(u.shape, -1); fn = np.zeros(u.shape + (3,))
    for s, H in enumerate([base_halfspaces(), upper_halfspaces(), neckH]):
        tin = np.full(u.shape, -np.inf); tout = np.full(u.shape, np.inf)
        face = np.full(u.shape, -1); nn = np.zeros(u.shape + (3,))
        for i, (n, c) in enumerate(H):
            den = n @ R; t = (c - O @ n) / den
            if den < 0:
                up = t > tin; tin = np.where(up, t, tin); face = np.where(up, 100 * s + i, face)
                nn = np.where(up[..., None], n, nn)
            else:
                tout = np.minimum(tout, t)
        hit = (tin < tout) & (tin < best)
        best = np.where(hit, tin, best); fid = np.where(hit, face, fid); fn = np.where(hit[..., None], nn, fn)
    Pt = O + best[..., None] * R
    hole = (fid == 200) & (np.hypot(Pt[..., 0] - NECK_C[0], Pt[..., 1] - NECK_C[1]) < R_IN)
    fid = np.where(hole, 999, fid)
    edge = np.zeros(fid.shape, bool)
    edge[:, 1:] |= fid[:, 1:] != fid[:, :-1]; edge[1:, :] |= fid[1:, :] != fid[:-1, :]
    # merge the many neck facets into one face for the edge overlay
    fid2 = np.where((fid >= 202) & (fid < 300), 202, fid)
    edge2 = np.zeros(fid.shape, bool)
    edge2[:, 1:] |= fid2[:, 1:] != fid2[:, :-1]; edge2[1:, :] |= fid2[1:, :] != fid2[:-1, :]
    a = np.asarray(photo).copy(); a[edge2] = [225, 20, 20]
    ov = Image.fromarray(a)
    light = nrm([-0.55, -0.45, 0.70])
    sh = np.clip(0.35 + 0.65 * np.clip(fn @ light, 0, 1), 0, 1)
    rgb = np.stack([sh * 236, sh * 230, sh * 220], -1)
    rgb[fid < 0] = [250, 250, 250]; rgb[hole] = [70, 66, 60]; rgb[edge2] = [60, 60, 60]
    rd = Image.fromarray(rgb.astype(np.uint8))
    box = (200, 280, 700, 940)
    ov, rd, ph = ov.crop(box), rd.crop(box), photo.crop(box)
    sheet = Image.new("RGB", (ph.width * 3 + 40, ph.height), "white")
    for i, im in enumerate([ph, ov, rd]): sheet.paste(im, (i * (ph.width + 20), 0))
    sheet.save(path)
    # quantitative check against hand-measured photo points
    def img(p):
        x, y, z = p; uu = CP * x - SP * y; dd = SP * x + CP * y
        return np.array([U0 + K * uu, V0 - K * (z * CE + dd * SE)])
    pts = {
        "base FL bottom": ((-W0 / 2, yb, 0), (305, 880)), "base FR bottom": ((W0 / 2, yb, 0), (497, 906)),
        "base BR bottom": ((W0 / 2, -yb, 0), (582, 877)), "left eave": ((xL, yb, EAVE_L), (247, 595)),
        "right eave (front)": ((xR, yb, EAVE_R), (565, 585)), "upper P1": (tuple(P1), (307, 379)),
        "upper P4": (tuple(P4), (482, 479)), "upper P3": (tuple(P3), (620, 470)),
        "crease left": (tuple(P6), (292, 657)), "crease right": (tuple(P5), (452, 717)),
        "neck rim centre": ((NECK_C[0], NECK_C[1], H_TOTAL), (465, 330)),
    }
    errs = {k: float(np.linalg.norm(img(p) - np.array(q))) for k, (p, q) in pts.items()}
    return errs


# ───────────────────────── polygon helpers ─────────────────────────
def clip_poly(poly, H):
    """Sutherland–Hodgman: keep part of planar 3D polygon inside all half-spaces."""
    out = [np.asarray(p, float) for p in poly]
    for n, c in H:
        if not out: break
        res = []
        for i in range(len(out)):
            a, b = out[i], out[(i + 1) % len(out)]
            da, db = n @ a - c, n @ b - c
            if da <= 1e-9: res.append(a)
            if (da < -1e-9 < db) or (db < -1e-9 < da):
                res.append(a + (b - a) * (da / (da - db)))
        out = res
    return out


class Face:
    def __init__(self, code, name, poly, e1=None, other=None, mirror_note=""):
        self.code, self.name, self.poly = code, name, [np.asarray(p, float) for p in poly]
        self.n = nrm(np.cross(self.poly[1] - self.poly[0], self.poly[2] - self.poly[0]))
        up = np.array([0, 0, 1.0]) - self.n * self.n[2]
        if np.linalg.norm(up) < 1e-6: up = np.array([0, 1.0, 0]) - self.n * self.n[1]
        self.e2 = nrm(up) if e1 is None else nrm(np.cross(self.n, nrm(e1)))
        self.e1 = nrm(np.cross(self.e2, self.n))
        self.o = self.poly[0]
        self.other, self.mirror_note = other, mirror_note

    def to2d(self, pts):
        return [((p - self.o) @ self.e1, (p - self.o) @ self.e2) for p in pts]

    def shapes(self):
        full = Polygon(self.to2d(self.poly)).buffer(0)
        cut = None
        if self.other is not None:
            c = clip_poly(self.poly, self.other)
            if len(c) >= 3:
                cp = Polygon(self.to2d(c)).buffer(0)
                if cp.area > 1e-4: cut = cp
        kept = full if cut is None else full.difference(cut.buffer(1e-5, join_style=2)).buffer(0)
        return full, cut, kept


def faces():
    Hb, Hu = base_halfspaces(), upper_halfspaces()
    FLb, FRb, BRb, BLb = (-W0 / 2, yb, 0), (W0 / 2, yb, 0), (W0 / 2, -yb, 0), (-W0 / 2, -yb, 0)
    eLf, eRf, rf = (xL, yb, EAVE_L), (xR, yb, EAVE_R), (x_ridge, yb, z_ridge)
    eLb, eRb, rb = (xL, -yb, EAVE_L), (xR, -yb, EAVE_R), (x_ridge, -yb, z_ridge)
    F = [
        Face("B1", "واجهة القاعدة الأمامية", [FLb, FRb, eRf, rf, eLf], other=Hu),
        Face("B2", "واجهة القاعدة الخلفية", [BRb, BLb, eLb, rb, eRb], other=Hu, mirror_note="معكوسة"),
        Face("B3", "جانب القاعدة الأيسر", [BLb, FLb, eLf, eLb], other=Hu),
        Face("B4", "جانب القاعدة الأيمن", [FRb, BRb, eRb, eRf], other=Hu),
        Face("B5", "سطح القاعدة المائل الأيسر", [eLf, rf, rb, eLb], e1=(1, 0, 0), other=Hu),
        Face("B6", "سطح القاعدة المائل الأيمن", [rf, eRf, eRb, rb], e1=(1, 0, 0), other=Hu),
        Face("B7", "قاع القاعدة", [BLb, BRb, FRb, FLb], e1=(1, 0, 0)),
        Face("U1", "واجهة الكتلة العلوية", [P6, P5, P4, P1], other=Hb),
        Face("U2", "ظهر الكتلة العلوية", [P5 + V, P6 + V, P1 + V, P4 + V], other=Hb, mirror_note="معكوسة"),
        Face("U3", "سطح الكتلة العلوية (حامل العنق)", [P1, P4, P3, P2], e1=P4 - P1, other=Hb),
        Face("U4", "جانب الكتلة العلوية الأيمن", [P5, P5 + V, P4 + V, P4], other=Hb),
        Face("U5", "جانب الكتلة العلوية الأيسر", [P6 + V, P6, P1, P1 + V], other=Hb),
        Face("U6", "قاع الكتلة العلوية", [P6, P6 + V, P5 + V, P5], e1=P5 - P6, other=Hb),
    ]
    return F


def neck_strip():
    """Unrolled neck wall (mid-wall circumference) with bottom curve following the sloped top face."""
    rm = (R_OUT + R_IN) / 2
    th = np.linspace(0, 2 * np.pi, 181)
    zb = top_plane_z(NECK_C[0] + R_OUT * np.cos(th), NECK_C[1] + R_OUT * np.sin(th))
    s = rm * th
    return s, zb


# ───────────────────────── SVG helpers ─────────────────────────
class SVG:
    def __init__(self, w_mm, h_mm):
        self.w, self.h, self.items = w_mm, h_mm, []

    def add(self, s): self.items.append(s)

    def poly(self, pts, stroke="#111", width=0.35, fill="none", dash=None, closed=True):
        d = " ".join(f"{x:.2f},{y:.2f}" for x, y in pts)
        tag = "polygon" if closed else "polyline"
        da = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<{tag} points="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{width}"{da} stroke-linejoin="round"/>')

    def line(self, a, b, stroke="#111", width=0.35, dash=None):
        da = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<line x1="{a[0]:.2f}" y1="{a[1]:.2f}" x2="{b[0]:.2f}" y2="{b[1]:.2f}" stroke="{stroke}" stroke-width="{width}"{da}/>')

    def text(self, p, s, size=3.2, anchor="middle", fill="#111", rot=0, weight="normal", rtl=False):
        tr = f' transform="rotate({rot:.1f} {p[0]:.2f} {p[1]:.2f})"' if rot else ""
        dr = ' direction="rtl"' if rtl else ' direction="ltr"'
        if rtl:  # callers give the visual anchor; in RTL text 'start' is the right edge
            anchor = {"start": "end", "end": "start"}.get(anchor, anchor)
        self.add(f'<text x="{p[0]:.2f}" y="{p[1]:.2f}" font-size="{size}" text-anchor="{anchor}" fill="{fill}" '
                 f'font-weight="{weight}"{dr}{tr}>{s}</text>')

    def save(self, path):
        head = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}mm" height="{self.h}mm" '
                f'viewBox="0 0 {self.w} {self.h}" font-family="Noto Naskh Arabic, Amiri, Tahoma, Arial, sans-serif">\n'
                f'<rect width="{self.w}" height="{self.h}" fill="#fff"/>\n'
                '<defs><marker id="ar" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="5" markerHeight="5" '
                'orient="auto-start-reverse"><path d="M0,1 L10,5 L0,9 z" fill="#c0392b"/></marker></defs>\n')
        with open(path, "w", encoding="utf-8") as f:
            f.write(head + "\n".join(self.items) + "\n</svg>\n")


def dim(svg, a, b, off, label, size=2.8, color="#c0392b"):
    """aligned dimension between sheet points a,b, offset perpendicular by off (mm)."""
    a, b = np.array(a, float), np.array(b, float)
    t = nrm(b - a); n = np.array([-t[1], t[0]])
    A, B = a + n * off, b + n * off
    for p, q in [(a, A), (b, B)]:
        svg.line(p + n * np.sign(off) * 0.8, q + n * np.sign(off) * 1.2, stroke=color, width=0.18)
    svg.add(f'<line x1="{A[0]:.2f}" y1="{A[1]:.2f}" x2="{B[0]:.2f}" y2="{B[1]:.2f}" stroke="{color}" '
            f'stroke-width="0.22" marker-start="url(#ar)" marker-end="url(#ar)"/>')
    m = (A + B) / 2 + n * np.sign(off) * 1.4 + np.array([0, size * 0.35])
    ang = math.degrees(math.atan2(t[1], t[0]))
    if ang > 90: ang -= 180
    if ang < -90: ang += 180
    svg.text(m, label, size=size, fill=color, rot=ang)


# ───────────────────────── orthographic drawings ─────────────────────────
def visible_edges(m, view_dir, crease_deg=20.0, step=0.15):
    Vt, T = mesh_arrays(m)
    A, B, C = Vt[T[:, 0]], Vt[T[:, 1]], Vt[T[:, 2]]
    N = np.cross(B - A, C - A); N /= np.linalg.norm(N, axis=1)[:, None]
    emap = {}
    for ti, t in enumerate(T):
        for i in range(3):
            e = tuple(sorted((t[i], t[(i + 1) % 3])))
            emap.setdefault(e, []).append(ti)
    d = nrm(view_dir); cos_c = math.cos(math.radians(crease_deg))
    sel = []
    for e, tl in emap.items():
        if len(tl) != 2: sel.append(e); continue
        n1, n2 = N[tl[0]], N[tl[1]]
        if n1 @ n2 < cos_c or (n1 @ d) * (n2 @ d) < 0: sel.append(e)
    # sample points & occlusion test (rays toward viewer: direction -d)
    segs = []
    E1, E2 = B - A, C - A
    for e in sel:
        p, q = Vt[e[0]], Vt[e[1]]
        L = np.linalg.norm(q - p); k = max(2, int(L / step) + 1)
        ts = np.linspace(0, 1, k); S = p + (q - p) * ts[:, None]
        O = S - d * 1e-3
        Dr = -d
        h = np.cross(Dr, E2)                       # (nt,3)
        a = (E1 * h).sum(1)
        ok = np.abs(a) > 1e-12
        f = np.where(ok, 1 / np.where(ok, a, 1), 0)
        s = O[:, None, :] - A[None]                # (ns,nt,3)
        uu = f * (s * h).sum(2)
        qv = np.cross(s, E1[None])
        vv = f * (qv * Dr).sum(2)
        tt = f * (qv * E2[None]).sum(2)
        hit = ok & (uu >= -1e-9) & (vv >= -1e-9) & (uu + vv <= 1 + 1e-9) & (tt > 2e-3)
        vis = ~hit.any(1)
        segs.append((S, vis))
    return segs


def draw_view(svg, m, view_dir, to2d, origin, scale, hidden=True):
    for S, vis in visible_edges(m, view_dir):
        P = np.array([to2d(p) for p in S]) * scale + origin
        for flag, style in [(True, dict(width=0.45)), (False, dict(width=0.2, stroke="#888", dash="1.2,0.9"))]:
            if flag is False and not hidden: continue
            run = []
            for i in range(len(P)):
                if vis[i] == flag: run.append(P[i])
                else:
                    if len(run) > 1: svg.poly(run, closed=False, **style)
                    run = []
            if len(run) > 1: svg.poly(run, closed=False, **style)


def drawings(S, path):
    sc = 5.0                     # 1:2  (1 cm = 5 mm on sheet)
    svg = SVG(420, 297)
    svg.poly([(8, 8), (412, 8), (412, 289), (8, 289)], width=0.6)
    m = S["bore"]
    # front view (look +y): screen x = x, screen y = -z
    oF = np.array([80, 250.0])
    fF = lambda p: (p[0], -p[2])
    draw_view(svg, m, (0, 1, 0), fF, oF, sc)
    # right view (look -x): screen x = y, screen y = -z
    oR = np.array([205, 250.0])
    fR = lambda p: (p[1], -p[2])
    draw_view(svg, m, (-1, 0, 0), fR, oR, sc)
    # top view (look -z): screen x = x, screen y = -y
    oT = np.array([80, 62.0])
    fT = lambda p: (p[0], -p[1])
    draw_view(svg, m, (0, 0, -1), fT, oT, sc, hidden=False)
    F = lambda p: oF + np.array(fF(p)) * sc
    R_ = lambda p: oR + np.array(fR(p)) * sc
    Tt = lambda p: oT + np.array(fT(p)) * sc
    mm = lambda v: f"{v * 10:.0f}"
    # front dims
    dim(svg, F((-W0 / 2, 0, 0)), F((W0 / 2, 0, 0)), 9, mm(W0))
    dim(svg, F((xL, 0, 0)), F((xL, 0, EAVE_L)), -10, mm(EAVE_L))
    dim(svg, F((xR, 0, 0)), F((xR, 0, EAVE_R)), 8, mm(EAVE_R))
    hmax = H_TOTAL
    dim(svg, F((xR + 2.2, 0, 0)), F((xR + 2.2, 0, hmax)), 14, mm(hmax))
    dim(svg, F((xL, 0, 0)), F((xR, 0, 0)), 18, mm(xR - xL))
    svg.line(F((xL, 0, 0)), F((xL, 0, EAVE_L)), stroke="#c0392b", width=0.12, dash="0.8,0.8")
    svg.line(F((xR, 0, 0)), F((xR, 0, EAVE_R)), stroke="#c0392b", width=0.12, dash="0.8,0.8")
    dim(svg, F((NECK_C[0] - R_OUT, 0, H_TOTAL)), F((NECK_C[0] + R_OUT, 0, H_TOTAL)), -6, "Ø" + mm(NECK_OD))
    dim(svg, F(P6), F(P1), 6, mm(np.linalg.norm(P1 - P6)))
    dim(svg, F(P1), F(P4), -6, mm(np.linalg.norm(P4 - P1)))
    for p, lab in [(P1, mm(P1[2])), (P4, mm(P4[2])), (P5, mm(P5[2])), (P6, mm(P6[2]))]:
        q = F(p); svg.text(q + np.array([-6.5 if p[0] < 0 else 6.5, -1.5 if p[2] > 20 else 4.5]), f"z={lab}", size=2.4, fill="#1f6fb2")
    svg.text(F((x_ridge, 0, z_ridge)) + np.array([0, -2]), f"z={mm(z_ridge)}", size=2.4, fill="#1f6fb2")
    svg.text(F((xL, 0, 0)) + np.array([-2, 5]), f"{FLARE:.0f}°", size=2.6, fill="#1f6fb2")
    svg.text(F((xL + 2.5, 0, EAVE_L + 0.4)), f"{ROOF:.0f}°", size=2.6, fill="#1f6fb2")
    svg.text(F((xR - 2.2, 0, EAVE_R + 0.5)), f"{ROOF:.0f}°", size=2.6, fill="#1f6fb2")
    ang_top = math.degrees(math.atan2(P1[2] - P4[2], P4[0] - P1[0]))
    svg.text(F((P4[0] - 3.2, 0, P4[2] - 0.2)), f"{ang_top:.1f}°", size=2.6, fill="#1f6fb2")
    svg.text(oF + np.array([0, 31]), "المسقط الأمامي", size=4.2, weight="bold", rtl=True)
    # right dims
    dim(svg, R_((0, yb, 0)), R_((0, -yb, 0)), 9, mm(D0))
    dim(svg, R_((0, yf, H_TOTAL)), R_((0, -yb, H_TOTAL)), -8, mm(-yb - yf))
    dim(svg, R_((0, yf, P6[2])), R_((0, yb, P6[2])), 4, mm(PROUD), size=2.4)
    svg.text(oR + np.array([0, 31]), "المسقط الجانبي الأيمن", size=4.2, weight="bold", rtl=True)
    # top dims
    dim(svg, Tt(P4), Tt(P3), 5, mm(np.linalg.norm(V[:2])))
    skew = math.degrees(math.atan2(V[0], V[1]))
    svg.text(Tt(P3) + np.array([6, 2]), f"{skew:.0f}°", size=2.6, fill="#1f6fb2")
    dim(svg, Tt((NECK_C[0] - R_IN, NECK_C[1], 0)), Tt((NECK_C[0] + R_IN, NECK_C[1], 0)), -3.5, "Ø" + mm(NECK_ID), size=2.4)
    svg.text(oT + np.array([0, -38]), "المسقط العلوي", size=4.2, weight="bold", rtl=True)
    # pictorial view from the photo's camera (1:3)
    E, PHI = math.radians(CAM["E"]), math.radians(CAM["PHI"])
    CE, SE, CP, SP = math.cos(E), math.sin(E), math.cos(PHI), math.sin(PHI)
    vdir = (SP * CE, CP * CE, -SE)
    fP = lambda p: (CP * p[0] - SP * p[1], -(p[2] * CE + (SP * p[0] + CP * p[1]) * SE))
    oP = np.array([335, 271.0])
    draw_view(svg, m, vdir, fP, oP, 10 / 3.5, hidden=False)
    svg.text(oP + np.array([0, 13]), "منظور بزاوية الصورة نفسها (1:3.5)", size=3.4, weight="bold", rtl=True)
    # title block / notes
    x0 = 312
    notes = [
        ("مزهرية تكعيبية — إعادة بناء هندسية", 5.0, "bold"),
        ("الارتفاع الكلي 300 مم (مقاس بعد الحرق)", 3.4, "normal"),
        ("الأبعاد بالمليمتر · مقياس الرسم 1:2", 3.4, "normal"),
        ("نظام الإسقاط: الزاوية الثالثة", 3.4, "normal"),
        ("", 3, "normal"),
        ("القاعدة: منشور منفرج الجانبين 14° بسقف جمالوني 25°", 3.1, "normal"),
        ("الواجهة الأمامية والخلفية رأسيتان تماماً", 3.1, "normal"),
        ("الكتلة العلوية: منشور مائل، واجهته بارزة 12 مم", 3.1, "normal"),
        ("وعمقه 95 مم منحرف 18° يميناً للخلف", 3.1, "normal"),
        ("العنق: أسطوانة رأسية Ø58/45 فوق مركز السطح", 3.1, "normal"),
        ("", 3, "normal"),
        ("خطوط منقطة رمادية = حواف مخفية", 3.1, "normal"),
        ("z = الارتفاع من سطح الطاولة", 3.1, "normal"),
        ("الأرقام مستنتجة من صورة واحدة: التفاوت ±3 مم تقريباً", 3.1, "normal"),
    ]
    y = 30
    for s, size, w in notes:
        svg.text((404, y), s, size=size, anchor="end", weight=w, rtl=True); y += size * 1.9
    # coordinate table
    y += 4
    svg.text((404, y), "إحداثيات الرؤوس (مم) — الأصل: مركز القاع", size=3.4, anchor="end", weight="bold", rtl=True); y += 6
    rows = [("P1", P1), ("P4", P4), ("P5", P5), ("P6", P6), ("P2", P2), ("P3", P3),
            ("حافة يسار", np.array([xL, yb, EAVE_L])), ("حافة يمين", np.array([xR, yb, EAVE_R])),
            ("قمة السقف", np.array([x_ridge, yb, z_ridge])), ("مركز العنق", np.array([NECK_C[0], NECK_C[1], H_TOTAL]))]
    for i, c in enumerate("xyz"): svg.text((x0 + 20 * i, y), c, size=3, anchor="end", weight="bold")
    y += 5
    for name, p in rows:
        for i in range(3): svg.text((x0 + 20 * i, y), f"{p[i] * 10:.0f}", size=3, anchor="end")
        svg.text((404, y), name, size=3, anchor="end", rtl=True); y += 4.6
    svg.save(path)


# ───────────────────────── slab templates (wet size, 1:1) ─────────────────────────
class MaxRects:
    """Minimal MaxRects bin packer (best-short-side-fit, 90° rotation allowed)."""
    def __init__(self, w, h):
        self.free = [(0.0, 0.0, w, h)]

    def insert(self, w, h):
        best = None
        for fx, fy, fw, fh in self.free:
            for rot, (ww, hh) in enumerate([(w, h), (h, w)]):
                if ww <= fw and hh <= fh:
                    score = (min(fw - ww, fh - hh), max(fw - ww, fh - hh))
                    if best is None or score < best[0]: best = (score, fx, fy, ww, hh, rot)
        if best is None: return None
        _, x, y, ww, hh, rot = best
        nf = []
        for fx, fy, fw, fh in self.free:
            if x >= fx + fw or x + ww <= fx or y >= fy + fh or y + hh <= fy:
                nf.append((fx, fy, fw, fh)); continue
            if x > fx: nf.append((fx, fy, x - fx, fh))
            if x + ww < fx + fw: nf.append((x + ww, fy, fx + fw - x - ww, fh))
            if y > fy: nf.append((fx, fy, fw, y - fy))
            if y + hh < fy + fh: nf.append((fx, y + hh, fw, fy + fh - y - hh))
        inside = lambda a, b: a[0] >= b[0] and a[1] >= b[1] and a[0] + a[2] <= b[0] + b[2] and a[1] + a[3] <= b[1] + b[3]
        self.free = [a for i, a in enumerate(nf)
                     if not any(inside(a, b) and (a != b or j < i) for j, b in enumerate(nf) if j != i)]
        return x, y, rot


def templates(path_fmt):
    k = 10.0 / (1 - SHRINK)             # cm(fired) -> mm(wet)
    items = []
    for f in faces():
        full, cut, kept = f.shapes()
        items.append((f, full, cut, kept))
    s, zb = neck_strip()
    neck_poly = Polygon(list(zip(s, zb)) + [(s[-1], H_TOTAL), (s[0], H_TOTAL)])
    W, Hh, M, G = 420, 297, 10, 8
    jobs = [("face", f, kept if f.code.startswith("U") else full, None if f.code.startswith("U") else cut, kept)
            for f, full, cut, kept in items]
    jobs.append(("neck", None, neck_poly, None, neck_poly))
    size = lambda b: ((b[2] - b[0]) * k + G, (b[3] - b[1]) * k + G)
    jobs.sort(key=lambda j: -size(j[2].bounds)[0] * size(j[2].bounds)[1])
    packers, pages = [], []
    for j in jobs:
        w, h = size(j[2].bounds)
        for pk, pg in zip(packers, pages):
            r = pk.insert(w, h)
            if r: pg.append(j + (r,)); break
        else:
            pk = MaxRects(W - 2 * M + G, Hh - 2 * M - 18 + G); packers.append(pk)
            pages.append([j + (pk.insert(w, h),)])
    out = []
    for pi, page in enumerate(pages):
        svg = SVG(W, Hh)
        for kind, f, full, cut, kept, (px, py, rot) in page:
            minx, miny, maxx, maxy = full.bounds
            px, py = px + M, py + M
            if rot:   # 90° turn, no mirroring
                T = lambda q: (px + (maxy - q[1]) * k, py + (maxx - q[0]) * k)
            else:
                T = lambda q: (px + (q[0] - minx) * k, py + (maxy - q[1]) * k)
            if kind == "face":
                fullpts = [T(q) for q in full.exterior.coords]
                if cut is not None:
                    svg.poly(fullpts, stroke="#999", width=0.25, dash="2,1.5")
                    cg = cut.intersection(full)
                    for g in getattr(cg, "geoms", [cg]):
                        if g.geom_type == "Polygon" and g.area > 1e-4:
                            svg.poly([T(q) for q in g.exterior.coords], stroke="#c0392b", width=0.3,
                                     fill="#c0392b", dash=None)
                            svg.items[-1] = svg.items[-1].replace('fill="#c0392b"', 'fill="#c0392b" fill-opacity="0.12"')
                for g in getattr(kept, "geoms", [kept]):
                    if g.geom_type != "Polygon" or g.area < 1e-4: continue
                    pts = [T(q) for q in g.exterior.coords]
                    svg.poly(pts, stroke="#111", width=0.5, fill="#f4efe6")
                    for hole in g.interiors:
                        svg.poly([T(q) for q in hole.coords], stroke="#111", width=0.5, fill="#fff")
                    # edge lengths (wet mm)
                    cs = list(g.exterior.coords)[:-1]
                    for i in range(len(cs)):
                        a, b = np.array(cs[i]), np.array(cs[(i + 1) % len(cs)])
                        L = np.linalg.norm(b - a) * k
                        if L < 12: continue
                        A, B = np.array(T(a)), np.array(T(b))
                        mid = (A + B) / 2; t = nrm(B - A); nn = np.array([t[1], -t[0]])
                        c = np.array(T(np.array(g.centroid.coords[0])))
                        if nn @ (c - mid) > 0: nn = -nn
                        ang = math.degrees(math.atan2(t[1], t[0]))
                        if ang > 90: ang -= 180
                        if ang < -90: ang += 180
                        svg.text(mid - nn * 2.6 + np.array([0, 1.0]), f"{L:.0f}", size=2.6, fill="#1f6fb2", rot=ang)
                if f.code == "U3":   # neck seat + bore ellipse on the sloped top
                    th = np.linspace(0, 2 * np.pi, 120)
                    for r, sty in [(R_OUT, dict(stroke="#555", width=0.3, dash="1.5,1")), (R_IN, dict(stroke="#c0392b", width=0.35))]:
                        P = [np.array([NECK_C[0] + r * math.cos(a), NECK_C[1] + r * math.sin(a), 0]) for a in th]
                        for p in P: p[2] = top_plane_z(p[0], p[1])
                        svg.poly([T(q) for q in f.to2d(P)], **sty)
                cx, cy = T(np.array(kept.centroid.coords[0]) if not kept.is_empty else np.array(full.centroid.coords[0]))
                svg.text((cx, cy - 1.5), f.code, size=6, weight="bold", fill="#444")
                svg.text((cx, cy + 4.5), f.name + (f" ({f.mirror_note})" if f.mirror_note else ""), size=3, rtl=True)
            else:
                pts = [T(q) for q in full.exterior.coords]
                svg.poly(pts, stroke="#111", width=0.5, fill="#f4efe6")
                cx, cy = T(np.array(full.centroid.coords[0]))
                svg.text((cx, cy - 1), "N1", size=6, weight="bold", fill="#444")
                svg.text((cx, cy + 5), "شريحة العنق (تُلف حول قالب Ø45)", size=3, rtl=True)
                svg.text((cx, cy + 9.5), f"الطول {s[-1] * k:.0f} · الحافة السفلية تتبع ميل السطح", size=2.6, rtl=True)
        # footer: scale check + legend
        svg.line((M, Hh - 14), (M + 100, Hh - 14), width=0.6)
        for i in range(11): svg.line((M + i * 10, Hh - 15.5), (M + i * 10, Hh - 12.5), width=0.3)
        svg.text((M + 50, Hh - 8.5), "مسطرة تحقق: 100 مم — اطبع بمقياس 100% (A3)", size=3, rtl=True)
        svg.text((W - M, Hh - 13), f"قوالب القصّ بالمقاس الرطب (انكماش {SHRINK * 100:.0f}%) · الأرقام بالمليمتر · لوح {pi + 1}/{len(pages)}",
                 size=3.2, anchor="end", rtl=True, weight="bold")
        svg.text((W - M, Hh - 7.5), "الخط الأسود = خط القص · الأحمر المظلل = فتحة/جزء يُزال حيث تتداخل الكتلتان · المنقط = الشكل الكامل قبل التقليم",
                 size=2.7, anchor="end", rtl=True)
        p = path_fmt.format(pi + 1); svg.save(p); out.append(p)
    return out


# ───────────────────────── main ─────────────────────────
def main():
    S = solids()
    write_stl(S["solid"], os.path.join(OUT, "vase-solid.stl"))
    write_stl(S["hollow"], os.path.join(OUT, "vase-hollow.stl"))
    errs = render_photo_check(os.path.join(OUT, "fit-check.png"))
    drawings(S, os.path.join(OUT, "drawings.svg"))
    for f in os.listdir(OUT):
        if f.startswith("templates-") and f.endswith(".svg"): os.remove(os.path.join(OUT, f))
    pages = templates(os.path.join(OUT, "templates-{}.svg"))
    vol_ext = S["solid"].volume(); vol_clay = S["hollow"].volume()
    vol_cav = (S["cavity"] ^ S["solid"]).volume()
    print("== derived ==")
    print(f"left eave x={xL:.2f}  right eave x={xR:.2f}  overall width={xR - xL:.2f}")
    print(f"ridge x={x_ridge:.2f} z={z_ridge:.2f}")
    print(f"P2={np.round(P2, 2)} P3={np.round(P3, 2)} neck centre={np.round(NECK_C, 2)}")
    print(f"neck height above top-face centre = {H_TOTAL - NECK_C[2]:.2f}")
    print(f"upper front edge slope = {math.degrees(math.atan2(P1[2] - P4[2], P4[0] - P1[0])):.1f} deg")
    print(f"left edge lean = {math.degrees(math.atan2(P1[0] - P6[0], P1[2] - P6[2])):.1f} deg, "
          f"right edge lean = {math.degrees(math.atan2(P4[0] - P5[0], P4[2] - P5[2])):.1f} deg")
    print(f"crease slope = {math.degrees(math.atan2(P6[2] - P5[2], P5[0] - P6[0])):.1f} deg")
    print(f"skew = {math.degrees(math.atan2(V[0], V[1])):.1f} deg, depth = {np.linalg.norm(V[:2]):.2f}, "
          f"top drop = {math.degrees(math.atan2(-V[2], np.linalg.norm(V[:2]))):.1f} deg")
    print(f"exterior volume = {vol_ext:.0f} cm3 ; clay (fired) = {vol_clay:.0f} cm3 ; cavity = {vol_cav:.0f} cm3")
    print(f"surface area = {S['solid'].surface_area():.0f} cm2")
    print("photo fit error (px):", {k: round(v, 1) for k, v in errs.items()})
    print("rms px = %.2f  (1 px ≈ %.2f mm)" % (math.sqrt(np.mean(np.square(list(errs.values())))), 10 / CAM["K"]))
    for f in faces():
        full, cut, kept = f.shapes()
        print(f"{f.code}: full {full.area:.1f} cm2, kept {kept.area:.1f} cm2, cut {0 if cut is None else cut.area:.1f}")
    print("template pages:", pages)


if __name__ == "__main__":
    main()
