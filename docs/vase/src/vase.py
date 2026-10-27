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
SYMMETRIC = True              # front and back halves mirror each other: the chest runs straight
                              # through the base and stands proud by PROUD at front and back
UPPER_SKEW = 18.0             # used only when SYMMETRIC is False (closest fit to the photo):
UPPER_DROP = 5.4              #   chest depth skews right / top falls toward the back
NECK_OD, NECK_ID = 5.8, 4.5   # neck outer / inner diameter
NECK_X = 1.3                  # neck axis x when SYMMETRIC (matches the photo)
WALL, FLOOR = 0.8, 1.0        # slab thickness, base floor thickness
SHRINK = 0.12                 # total clay shrinkage (wet -> fired)
RIM = 2.0                     # contact rim left around the window joining chest floor and seat floor

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
if SYMMETRIC:
    V = np.array([0.0, D0 + 2 * PROUD, 0.0])
else:   # chest back rests on the inner face of the base back wall (assembly stop)
    _vy = (D0 / 2 - WALL) - yf
    _vxy = _vy / math.cos(math.radians(UPPER_SKEW))
    V = np.array([_vy * math.tan(math.radians(UPPER_SKEW)), _vy, -_vxy * math.tan(math.radians(UPPER_DROP))])
P6, P1, P4, P5 = [np.array([x, yf, z]) for x, z in UPPER_FRONT]
P2, P3 = P1 + V, P4 + V
NECK_C = (P1 + P4) / 2 + V / 2        # centre of upper top face
if SYMMETRIC:   # on the front/back mirror plane, left-right where the photo shows it
    _n = np.cross(P4 - P1, P2 - P1)
    NECK_C = np.array([NECK_X, 0.0, P1[2] - (_n[0] * (NECK_X - P1[0]) + _n[1] * (0.0 - P1[1])) / _n[2]])
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
    def __init__(self, code, name, poly, e1=None, other=None, mirror_note="", trim=False):
        self.code, self.name, self.poly = code, name, [np.asarray(p, float) for p in poly]
        self.trim = trim
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
        if self.trim:   # drop strips no wider than a wall: that edge is the top of the wall below
            w = WALL * 0.6
            kept = kept.buffer(-w, join_style=2).buffer(w, join_style=2).intersection(full)
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
        Face("B5", "سطح القاعدة المائل الأيسر", [eLf, rf, rb, eLb], e1=(1, 0, 0), other=Hu, trim=True),
        Face("B6", "سطح القاعدة المائل الأيمن", [rf, eRf, eRb, rb], e1=(1, 0, 0), other=Hu, trim=True),
        Face("B7", "قاع القاعدة", [BLb, BRb, FRb, FLb], e1=(1, 0, 0)),
        Face("U1", "واجهة الكتلة العلوية", [P6, P5, P4, P1], other=Hb),
        Face("U2", "ظهر الكتلة العلوية", [P5 + V, P6 + V, P1 + V, P4 + V], other=Hb, mirror_note="معكوسة"),
        Face("U3", "سطح الكتلة العلوية (حامل العنق)", [P1, P4, P3, P2], e1=P4 - P1, other=Hb),
        Face("U4", "جانب الكتلة العلوية الأيمن", [P5, P5 + V, P4 + V, P4], other=Hb),
        Face("U5", "جانب الكتلة العلوية الأيسر", [P6 + V, P6, P1, P1 + V], other=Hb),
        Face("U6", "قاع الكتلة العلوية", [P6, P6 + V, P5 + V, P5], e1=P5 - P6, other=Hb),
    ]
    # seat of the chair-shaped base: the chest faces where they lie inside the base, seen from the seat
    U = {f.code: f for f in F}
    for code, name, src in [("S1", "أرضية المقعد", "U6"), ("S2", "جدار المقعد الأيسر", "U5"), ("S3", "جدار المقعد الأيمن", "U4")]:
        poly = clip_poly(U[src].poly, Hb)[::-1]
        F.append(Face(code, name, poly, e1=(P5 - P6) if code == "S1" else None))
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
                'orient="auto-start-reverse"><path d="M0,1 L10,5 L0,9 z" fill="#c0392b"/></marker>'
                '<marker id="ab" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="4" markerHeight="4" '
                'orient="auto"><path d="M0,1 L10,5 L0,9 z" fill="#1f6fb2"/></marker>'
                '<pattern id="hatch" width="2" height="2" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
                '<rect width="2" height="2" fill="#fff3d6"/><line x1="0" y1="0" x2="0" y2="2" stroke="#d68910" stroke-width="0.6"/>'
                '</pattern></defs>\n')
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
        (f"وعمقه {np.linalg.norm(V[:2]) * 10:.0f} مم منحرف {UPPER_SKEW:.0f}° يميناً للخلف", 3.1, "normal"),
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

    def insert(self, w, h, rotate=True):
        best = None
        for fx, fy, fw, fh in self.free:
            for rot, (ww, hh) in enumerate([(w, h), (h, w)] if rotate else [(w, h)]):
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


# three modules built separately, then joined once (score + slip)
MODULES = [
    ("1-base", "القاعدة (الكرسي)", ["B1", "B2", "B3", "B4", "B5", "B6", "B7", "S1", "S2", "S3"],
     "B = غلاف القاعدة · S = المقعد الذي يجلس فيه الصدر · الأحمر المظلل = يُقصّ مكان المقعد · الأرقام بالمليمتر"),
    ("2-chest", "الصدر", ["U1", "U2", "U3", "U4", "U5", "U6"],
     "كل وجه يُقصّ كاملاً · المخطط البرتقالي = يلتصق بالمقعد (هشّر كامل المساحة) · الأحمر المنقط = حافة المقعد"),
    ("3-neck", "الرأس (العنق والفوهة)", ["N1", "N2", "T1"],
     "N1 للبناء بالشريحة · N2 مقطع للرمي على الدولاب · T1 اختبار الانكماش: اعمله قبل كل شيء"),
]


def floor_window():
    """Window through chest floor U6 and seat floor S1 (same place): joins the cavities, vents the kiln."""
    f = [x for x in faces() if x.code == "U6"][0]
    full, cut, kept = f.shapes()
    win = cut.buffer(-RIM, join_style=2)
    return f, [f.o + x * f.e1 + y * f.e2 for x, y in list(win.exterior.coords)[:-1]]


def neck_heights():
    th = np.linspace(0, 2 * np.pi, 721)
    zb = top_plane_z(NECK_C[0] + R_OUT * np.cos(th), NECK_C[1] + R_OUT * np.sin(th))
    return H_TOTAL - zb.max(), H_TOTAL - zb.min(), th[np.argmax(zb)]


def _poly(svg, g, T, **kw):
    for p in getattr(g, "geoms", [g]):
        if p.geom_type == "Polygon" and p.area > 1e-5:
            svg.poly([T(q) for q in p.exterior.coords], **kw)
            for h in p.interiors:
                svg.poly([T(q) for q in h.coords], **dict(kw, fill="#fff"))


def _lines(svg, g, T, **kw):
    for p in getattr(g, "geoms", [g]):
        if p.geom_type == "LineString" and p.length > 1e-3:
            svg.poly([T(q) for q in p.coords], closed=False, **kw)


def _edge_lengths(svg, g, T, k):
    for p in getattr(g, "geoms", [g]):
        if p.geom_type != "Polygon": continue
        cs = list(p.exterior.coords)[:-1]
        c = np.array(T(np.array(p.representative_point().coords[0])))
        for i in range(len(cs)):
            a, b = np.array(cs[i]), np.array(cs[(i + 1) % len(cs)])
            L = np.linalg.norm(b - a) * k
            if L < 12: continue
            A, B = np.array(T(a)), np.array(T(b))
            mid = (A + B) / 2; t = nrm(B - A); nn = np.array([t[1], -t[0]])
            if nn @ (c - mid) > 0: nn = -nn
            ang = math.degrees(math.atan2(t[1], t[0]))
            if ang > 90: ang -= 180
            if ang < -90: ang += 180
            svg.text(mid - nn * 2.6 + np.array([0, 1.0]), f"{L:.0f}", size=2.6, fill="#1f6fb2", rot=ang)


def template_jobs():
    """(code, kind, face, outline-geometry, extras) for every slab of every module."""
    jobs = {}
    _, win = floor_window()
    for f in faces():
        full, cut, kept = f.shapes()
        jobs[f.code] = dict(kind="chest" if f.code[0] == "U" else "base", f=f, geom=full, cut=cut, kept=kept)
    jobs["U6"]["window"] = jobs["S1"]["window"] = win
    s, zb = neck_strip()
    jobs["N1"] = dict(kind="strip", f=None, geom=Polygon(list(zip(s, zb)) + [(s[-1], H_TOTAL), (s[0], H_TOTAL)]),
                      s=s, zb=zb)
    kk = 10.0 / (1 - SHRINK)
    jobs["T1"] = dict(kind="test", f=None, geom=Polygon([(0, 0), (130 / kk, 0), (130 / kk, 50 / kk), (0, 50 / kk)]))
    hmin, hmax, _ = neck_heights()
    jobs["N2"] = dict(kind="profile", f=None, hmin=hmin, hmax=hmax,
                      geom=Polygon([(-R_OUT - 2.2, H_TOTAL - hmax - 1.6), (R_OUT + 2.2, H_TOTAL - hmax - 1.6),
                                    (R_OUT + 2.2, H_TOTAL + 1.2), (-R_OUT - 2.2, H_TOTAL + 1.2)]))
    return jobs


def _window(svg, j, T):
    g = Polygon(j["f"].to2d(j["window"]))
    _poly(svg, g, T, stroke="#c0392b", width=0.45, fill="#fff")
    c = g.centroid
    svg.text(T((c.x, c.y - 0.9)), "نافذة تُقصّ · تنطبق على " + ("S1" if j["f"].code == "U6" else "U6"),
             size=2.4, fill="#c0392b", rtl=True)


def draw_job(svg, code, j, T, k, J=None):
    kind = j["kind"]
    if kind == "base":
        f, full, cut, kept = j["f"], j["geom"], j["cut"], j["kept"]
        if cut is not None:
            svg.poly([T(q) for q in full.exterior.coords], stroke="#999", width=0.25, dash="2,1.5")
            _poly(svg, cut.intersection(full), T, stroke="#c0392b", width=0.35, fill="#f6dcd8")
            c = cut.intersection(full).representative_point()
            svg.text(T((c.x, c.y)), "يُقصّ — مكان المقعد", size=2.8, fill="#c0392b", rtl=True)
        _poly(svg, kept, T, stroke="#111", width=0.5, fill="#f4efe6")
        _edge_lengths(svg, kept, T, k)
        _joint_labels(svg, j, T, k, J)
        if "window" in j:
            _window(svg, j, T)
        cp = kept.representative_point() if cut is not None else kept.centroid
        if "window" in j: cp = Polygon(f.to2d(j["window"])).centroid
        cx, cy = T((cp.x, cp.y))
    elif kind == "chest":
        f, full, cut, kept = j["f"], j["geom"], j["cut"], j["kept"]
        _poly(svg, full, T, stroke="#111", width=0.5, fill="#f4efe6")
        if cut is not None:   # this part sits in the seat: the whole area is scored and slipped
            _poly(svg, cut, T, stroke="#d68910", width=0.2, fill="url(#hatch)")
            _lines(svg, kept.boundary.intersection(cut.buffer(1e-4)), T, stroke="#c0392b", width=0.5, dash="2.2,1.2")
            q = cut.representative_point()
            svg.text(T((q.x, q.y)), "يلتصق بالمقعد — هشّر", size=2.6, fill="#9c640c", rtl=True)
        svg.poly([T(q) for q in full.exterior.coords], stroke="#111", width=0.5)
        _edge_lengths(svg, full, T, k)
        _joint_labels(svg, j, T, k, J)
        if code == "U3":   # neck seat (scored ring) + bore on the sloped top
            th = np.linspace(0, 2 * np.pi, 120)
            ring = []
            for r in (R_OUT, R_IN):
                P = [np.array([NECK_C[0] + r * math.cos(a), NECK_C[1] + r * math.sin(a), 0]) for a in th]
                for p in P: p[2] = top_plane_z(p[0], p[1])
                ring.append(Polygon(f.to2d(P)))
            _poly(svg, ring[0].difference(ring[1]), T, stroke="#d68910", width=0.25, fill="url(#hatch)")
            _poly(svg, ring[1], T, stroke="#c0392b", width=0.45, fill="#fff")
            c = ring[1].centroid; svg.text(T((c.x, c.y + 0.15)), f"Ø{NECK_ID * 10:.0f} تُقصّ", size=2.4, fill="#c0392b", rtl=True)
        if "window" in j:
            _window(svg, j, T)
        cp = full.centroid
        if code == "U3": cp = Point(cp.x, cp.y - (R_OUT + 1.0))
        if code == "U6": cp = Polygon(j["f"].to2d(j["window"])).centroid
        cx, cy = T((cp.x, cp.y))
    elif kind == "strip":
        g = j["geom"]; s, zb = j["s"], j["zb"]
        _poly(svg, g, T, stroke="#111", width=0.5, fill="#f4efe6")
        band = g.intersection(Polygon(list(zip(s, zb)) + list(zip(s[::-1], zb[::-1] + WALL))).buffer(0))
        _poly(svg, band, T, stroke="#d68910", width=0.2, fill="url(#hatch)")
        i = int(np.argmax(zb)); a, b = T((s[i], H_TOTAL)), T((s[i], zb[i]))
        svg.line(a, b, stroke="#1f6fb2", width=0.3, dash="1.5,1")
        svg.text((a[0], a[1] + 4.5), "الضلع الأقصر ← يتجه نحو الزاوية العليا P1", size=2.4, fill="#1f6fb2", rtl=True)
        c = g.centroid; cx, cy = T((c.x, c.y + 0.4))
        svg.text((cx, cy + 9.5), f"طولها {s[-1] * k:.0f} · تُلفّ حول أنبوب Ø{NECK_ID * k / 10 * 10:.0f} ويُلحم طرفاها", size=2.6, rtl=True)
    elif kind == "test":   # shrinkage test strip, drawn directly in wet mm
        x0, y0 = T((j["geom"].bounds[0], j["geom"].bounds[3]))
        svg.poly([(x0, y0), (x0 + 130, y0), (x0 + 130, y0 + 34), (x0, y0 + 34)], stroke="#111", width=0.5, fill="#f4efe6")
        for xm, lab in ((15, "0"), (115, "100 مم")):
            svg.line((x0 + xm, y0 + 6), (x0 + xm, y0 + 20), stroke="#c0392b", width=0.5)
            svg.text((x0 + xm, y0 + 25), lab, size=3, fill="#c0392b", rtl="مم" in lab)
        svg.line((x0 + 15, y0 + 13), (x0 + 115, y0 + 13), stroke="#c0392b", width=0.25, dash="1.5,1")
        lines = ["اقطعها من نفس الطين، واخدش خطّين بينهما 100 مم، واحرقها قبل القطعة",
                 f"بعد الحرق: {100 * (1 - SHRINK):.0f} مم = القوالب صحيحة · غير ذلك اطبع بمقياس {100 * (1 - SHRINK):.0f} ÷ القياس × 100%"]
        for i_, t_ in enumerate(lines):
            svg.text((x0 + 65, y0 + 40 + i_ * 4.6), t_, size=2.7, rtl=True)
        cx, cy = x0 + 65, y0 + 5.5
        svg.text((cx, cy + 1.2), "T1 · شريحة اختبار الانكماش", size=3.2, weight="bold", rtl=True)
        return
    else:   # profile for wheel throwing
        hmin, hmax = j["hmin"], j["hmax"]
        top, zl, zr = H_TOTAL, H_TOTAL - hmin, H_TOTAL - hmax
        outer = [(-R_OUT, zl), (R_OUT, zr), (R_OUT, top), (-R_OUT, top)]
        svg.poly([T(q) for q in outer], stroke="#111", width=0.5, fill="#f4efe6")
        slope = (zl - zr) / (2 * R_OUT)
        for x in (-R_IN, R_IN):
            svg.line(T((x, top)), T((x, zl - slope * (x + R_OUT))), stroke="#777", width=0.25, dash="1.2,0.9")
        svg.poly([T(q) for q in [(-R_OUT, zl), (R_OUT, zr), (R_OUT, zr + WALL), (-R_OUT, zl + WALL)]],
                 stroke="#d68910", width=0.2, fill="url(#hatch)")
        dim(svg, T((-R_OUT, top)), T((R_OUT, top)), -5, f"Ø{NECK_OD * k:.0f}", color="#1f6fb2")
        dim(svg, T((-R_IN, top - 1.2)), T((R_IN, top - 1.2)), 0.01, f"Ø{NECK_ID * k:.0f}", size=2.4, color="#1f6fb2")
        dim(svg, T((-R_OUT, zl)), T((-R_OUT, top)), 5, f"{hmin * k:.0f}", color="#1f6fb2")
        dim(svg, T((R_OUT, zr)), T((R_OUT, top)), -5, f"{hmax * k:.0f}", color="#1f6fb2")
        ang = math.degrees(math.atan(slope))
        q = T((0, zr)); svg.text((q[0], q[1] + 6), f"قصّ القاعدة بميل {ang:.1f}°", size=2.6, fill="#c0392b", rtl=True)
        cx, cy = T((0, top - hmin * 0.45))
    name = {"N1": "شريحة العنق", "N2": "مقطع العنق للرمي"}.get(code) or j["f"].name
    note = j["f"].mirror_note if j["f"] is not None else ""
    svg.text((cx, cy - 1.5), code, size=6, weight="bold", fill="#444")
    svg.text((cx, cy + 4.5), name + (f" ({note})" if note else ""), size=3, rtl=True)


def color_key(svg, x0, y0):
    """compact colour key in the sheet header (two rows of four)."""
    items = [("cut", "قصّ على الخط الأسود"), ("remove", "يُقصّ ويُرمى (مكان المقعد)"),
             ("hole", "فتحة تُقصّ وتُرمى"), ("hatch", "تهشير: يلتصق، لا يُقصّ"),
             ("seat", "حافة المقعد على الصدر"), ("ref", "شكل مرجعي — لا تقصّ عليه"),
             ("len", "طول الضلع بالمم (رطب)"), ("ang", "زاوية قطع الحافة")]
    w = 58
    for i, (kind, lab) in enumerate(items):
        col, row = i % 4, i // 4
        xr = x0 + (4 - col) * w - 2; y = y0 + row * 6
        sw = (xr - 8, y, xr - 1, y + 4)
        if kind == "cut": svg.poly([(sw[0], sw[1]), (sw[2], sw[1]), (sw[2], sw[3]), (sw[0], sw[3])], stroke="#111", width=0.5, fill="#f4efe6")
        if kind == "remove": svg.poly([(sw[0], sw[1]), (sw[2], sw[1]), (sw[2], sw[3]), (sw[0], sw[3])], stroke="#c0392b", width=0.35, fill="#f6dcd8")
        if kind == "hole": svg.poly([(sw[0], sw[1]), (sw[2], sw[1]), (sw[2], sw[3]), (sw[0], sw[3])], stroke="#c0392b", width=0.45, fill="#fff")
        if kind == "hatch": svg.poly([(sw[0], sw[1]), (sw[2], sw[1]), (sw[2], sw[3]), (sw[0], sw[3])], stroke="#d68910", width=0.2, fill="url(#hatch)")
        if kind == "seat": svg.line((sw[0], y + 2), (sw[2], y + 2), stroke="#c0392b", width=0.5, dash="2.2,1.2")
        if kind == "ref": svg.poly([(sw[0], sw[1]), (sw[2], sw[1]), (sw[2], sw[3]), (sw[0], sw[3])], stroke="#999", width=0.25, dash="1.5,1")
        if kind == "len": svg.text((xr - 4.5, y + 3.3), "116", size=2.8, fill="#1f6fb2")
        if kind == "ang": svg.text((xr - 4.5, y + 3.3), "∠45°", size=2.6, fill="#7d3c98")
        svg.text((xr - 9.5, y + 3.2), lab, size=2.6, anchor="end", rtl=True)


def templates(path_fmt):
    k = 10.0 / (1 - SHRINK)             # cm(fired) -> mm(wet)
    W, Hh, M, G, HEAD = 420, 297, 10, 8, 17
    J = template_jobs()
    JT = joints()
    out = []
    for key, title, codes, legend in MODULES:
        size = lambda b: ((b[2] - b[0]) * k + G, (b[3] - b[1]) * k + G)
        order = sorted(codes, key=lambda c: -size(J[c]["geom"].bounds)[0] * size(J[c]["geom"].bounds)[1])
        packers, pages = [], []
        for c in order:
            w, h = size(J[c]["geom"].bounds)
            rotate = J[c]["kind"] in ("base", "chest")   # neck pieces keep their reading direction
            for pk, pg in zip(packers, pages):
                r = pk.insert(w, h, rotate)
                if r: pg.append((c, r)); break
            else:
                pk = MaxRects(W - 2 * M + G, Hh - 2 * M - 18 - HEAD + G); packers.append(pk)
                pages.append([(c, pk.insert(w, h, rotate))])
        for pi, page in enumerate(pages):
            svg = SVG(W, Hh)
            for c, (px, py, rot) in page:
                minx, miny, maxx, maxy = J[c]["geom"].bounds
                px, py = px + M, py + M + HEAD
                if rot:   # 90° turn, no mirroring
                    T = lambda q, px=px, py=py, maxy=maxy, maxx=maxx: (px + (maxy - q[1]) * k, py + (maxx - q[0]) * k)
                else:
                    T = lambda q, px=px, py=py, minx=minx, maxy=maxy: (px + (q[0] - minx) * k, py + (maxy - q[1]) * k)
                draw_job(svg, c, J[c], T, k, JT)
            n = key.split("-")[0]
            svg.text((W - M, M + 7), f"الجزء {n}: {title}", size=7, anchor="end", weight="bold", rtl=True)
            svg.text((W - M, M + 11.5), f"لوح {pi + 1}/{len(pages)} · {len(codes)} قطع: {' '.join(codes)}",
                     size=3, anchor="end", rtl=True, fill="#555")
            color_key(svg, M, M + 1)
            svg.line((M, M + HEAD - 2), (W - M, M + HEAD - 2), width=0.3, stroke="#999")
            svg.line((M, Hh - 14), (M + 100, Hh - 14), width=0.6)
            for i in range(11): svg.line((M + i * 10, Hh - 15.5), (M + i * 10, Hh - 12.5), width=0.3)
            svg.text((M + 50, Hh - 8.5), "مسطرة تحقق: 100 مم — اطبع بمقياس 100% (A3)", size=3, rtl=True)
            svg.text((W - M, Hh - 13), f"قوالب القصّ بالمقاس الرطب (انكماش {SHRINK * 100:.0f}%) · شرائح بسماكة {WALL * 10:.0f} مم",
                     size=3.2, anchor="end", rtl=True, weight="bold")
            svg.text((W - M, Hh - 7.5), legend + " · ∠ = الزاوية بين الوجه الظاهر وسطح القطع · ⟂ + حبل = قص عمودي وحبل طين من الداخل",
                     size=2.6, anchor="end", rtl=True)
            p = path_fmt.format(key, pi + 1); svg.save(p); out.append(p)
    return out


# ───────────────────────── modules: solids, quantities, exploded assembly ─────────────────────────
def top_plane():
    n = nrm(np.cross(P4 - P1, P2 - P1))
    if n[2] < 0: n = -n
    return n, float(n @ P1)


def modules():
    base, upper = hull(base_halfspaces()), hull(upper_halfspaces())
    n, d = top_plane()
    z0, z1 = neck_z0() - 1, H_TOTAL
    neck = (cylinder(R_OUT, z0, z1) - cylinder(R_IN, z0 - 1, z1 + 1)).trim_by_plane(list(n), d)
    wf, win = floor_window()
    window = Manifold.hull_points(np.array([p + s * wf.n for p in win for s in (-2.0, 2.0)]))
    bore = cylinder(R_IN, 20.0, H_TOTAL + 1)
    seat_wall = hull(inset(upper_halfspaces(), -WALL))     # chest grown by one wall: inner face of the seat slabs
    shells = dict(
        base=(base - upper) - (hull(inset(base_halfspaces(), WALL, FLOOR)) - seat_wall) - window,
        chest=upper - hull(inset(upper_halfspaces(), WALL)) - bore - window,
        neck=neck)
    solids_ = dict(base=base - upper, chest=upper, neck=neck)
    return solids_, shells


def join_lines():
    """3D segments where the chest meets the base surface (edges of the openings)."""
    Hu = upper_halfspaces(); segs = []
    for f in faces():
        if f.code[0] != "B": continue
        c = clip_poly(f.poly, Hu)
        if len(c) < 3: continue
        F = Polygon(f.to2d(f.poly))
        for i in range(len(c)):
            a, b = c[i], c[(i + 1) % len(c)]
            m2 = Point(f.to2d([(a + b) / 2])[0])
            if F.exterior.distance(m2) > 1e-6: segs.append((a, b))
    return segs


def assembly(path, mods):
    sol, shells = mods
    svg = SVG(420, 297)
    svg.poly([(8, 8), (412, 8), (412, 289), (8, 289)], width=0.6)
    E, PHI = math.radians(CAM["E"]), math.radians(CAM["PHI"])
    CE, SE, CP, SP = math.cos(E), math.sin(E), math.cos(PHI), math.sin(PHI)
    vdir = (SP * CE, CP * CE, -SE)
    fP = lambda p: (CP * p[0] - SP * p[1], -(p[2] * CE + (SP * p[0] + CP * p[1]) * SE))
    sc = 4.5
    o = np.array([175, 262.0])
    off = dict(base=np.zeros(3), chest=-1.15 * V + np.array([-5.0, 0, 9.0]))
    off["neck"] = off["chest"] + np.array([0, 0, 9.0])
    P = lambda p: o + np.array(fP(p)) * sc
    for key in ("base", "chest", "neck"):
        draw_view(svg, sol[key].translate(list(off[key])), vdir, fP, o, sc, hidden=False)
    for a, b in join_lines():
        svg.line(P(a), P(b), stroke="#c0392b", width=0.6)
        svg.line(P(a + off["chest"]), P(b + off["chest"]), stroke="#c0392b", width=0.6, dash="2,1.2")
    # insertion arrows
    c0 = (P1 + P4 + P5 + P6) / 4 + V * 0.5
    a, b = P(c0 + off["chest"] - V * 0.15), P(c0 + V * 0.1)
    svg.add(f'<line x1="{a[0]:.2f}" y1="{a[1]:.2f}" x2="{b[0]:.2f}" y2="{b[1]:.2f}" stroke="#1f6fb2" stroke-width="0.6" '
            f'stroke-dasharray="3,1.5" marker-end="url(#ab)"/>')
    nc = np.array([NECK_C[0], NECK_C[1], H_TOTAL])
    a, b = P(nc + off["neck"] - np.array([0, 0, 1.0])), P(nc + off["chest"] + np.array([0, 0, 0.6]))
    svg.add(f'<line x1="{a[0]:.2f}" y1="{a[1]:.2f}" x2="{b[0]:.2f}" y2="{b[1]:.2f}" stroke="#1f6fb2" stroke-width="0.6" '
            f'stroke-dasharray="3,1.5" marker-end="url(#ab)"/>')
    for key, lab, pt in [("base", "١ القاعدة (الكرسي)", np.array([xL - 1.5, yb, 6.0])),
                         ("chest", "٢ الصدر", P6 + np.array([-2.5, 0, 4.0])),
                         ("neck", "٣ الرأس", nc + np.array([-R_OUT - 3.5, 0, -1.0]))]:
        q = P(pt + off[key]); svg.text(q, lab, size=5, weight="bold", anchor="end", rtl=True, fill="#1f6fb2")
    E2, PH2 = math.radians(38), math.radians(28)
    c2, s2, cp2, sp2 = math.cos(E2), math.sin(E2), math.cos(PH2), math.sin(PH2)
    f2 = lambda p: (cp2 * p[0] - sp2 * p[1], -(p[2] * c2 + (sp2 * p[0] + cp2 * p[1]) * s2))
    o2 = np.array([328, 258.0]); sc2 = 2.6
    draw_view(svg, sol["base"], (sp2 * c2, cp2 * c2, -s2), f2, o2, sc2, hidden=False)
    for a, b in join_lines():
        svg.line(o2 + np.array(f2(a)) * sc2, o2 + np.array(f2(b)) * sc2, stroke="#c0392b", width=0.5)
    svg.text(o2 + np.array([0, 14]), "القاعدة من الأمام والأعلى: المقعد بين الذراعين", size=3.2, weight="bold", rtl=True)
    svg.text((150, 283), "التركيب: الصدر يجلس في مقعد القاعدة ويبرز منه أماماً وخلفاً بالتساوي، ثم يُثبَّت الرأس فوقه", size=3.6, weight="bold", rtl=True)
    # steps + table
    vol = {kk: shells[kk].volume() for kk in shells}
    wet = lambda v: v / (1 - SHRINK) ** 3 * 1.95 / 1000
    hmin, hmax, _ = neck_heights()
    lines = [
        ("ثلاث كتل تُصنع منفصلة ثم تُجمع مرة واحدة", 5.0, "bold", "#111"),
        ("", 2, "normal", "#111"),
        ("١ · القاعدة على شكل كرسي — 10 شرائح، صندوق مغلق:", 3.3, "normal", "#111"),
        ("    ذراع يسرى منخفضة · ذراع يمنى عالية (الكتف) · مقعد بينهما", 3.3, "normal", "#111"),
        ("٢ · الصدر — 6 شرائح، صندوق مغلق كامل الأوجه يجلس في المقعد", 3.3, "normal", "#111"),
        (f"    بفتحة Ø{NECK_ID * 10:.0f} في سطحه ونافذة في قاعه تنطبق على نافذة المقعد", 3.3, "normal", "#111"),
        (f"٣ · الرأس — أسطوانة Ø{NECK_OD * 10:.0f}/{NECK_ID * 10:.0f}، قاعدتها مقصوصة بميل سطح الصدر", 3.3, "normal", "#111"),
        ("", 2, "normal", "#111"),
        ("خطوات الجمع (كل الكتل بالجلد الصلب نفسه)", 3.8, "bold", "#111"),
        ("1. تجربة جافة: أدخل الصدر في المقعد كالدُّرج، باتجاه السهم،", 3.2, "normal", "#111"),
        (f"    حتى يبرز {PROUD * 10:.0f} مم من الأمام و{PROUD * 10:.0f} مم من الخلف (رطب: {PROUD / (1 - SHRINK) * 10:.1f} مم)", 3.2, "normal", "#111"),
        ("    — النصف الأمامي والخلفي متماثلان. شذّب أي احتكاك", 3.2, "normal", "#111"),
        ("2. هشّر وجوه المقعد الثلاثة (الأرضية والجداران)،", 3.2, "normal", "#111"),
        ("    والمساحة البرتقالية على الصدر، ثم ادهن الطين السائل على الجهتين", 3.2, "normal", "#111"),
        ("3. أدخل الصدر حتى يتساوى بروزه، واضغطه لأسفل وللجانبين", 3.2, "normal", "#111"),
        ("4. مرّر حبل طين رفيعاً على حواف المقعد من الخارج (الخط الأحمر)،", 3.2, "normal", "#111"),
        ("    وامسح الطين السائل الزائد", 3.2, "normal", "#111"),
        ("5. هشّر حلقة المقعد على سطح الصدر وقاعدة العنق، وثبّته رأسياً", 3.2, "normal", "#111"),
        (f"    بحيث تكون فوهته على {H_TOTAL * 10:.0f} مم (بعد الحرق) والضلع الأقصر نحو P1", 3.2, "normal", "#111"),
        ("6. غطِّ القطعة بالنايلون وجفّفها ببطء لعدة أيام", 3.2, "normal", "#111"),
        ("", 2, "normal", "#111"),
        ("كل الوصلات وجه مستوٍ على وجه مستوٍ، فلا قصّ مائل ولا فراغات.", 3.2, "bold", "#1f6fb2"),
        ("النافذة المشتركة في القاع إلزامية: تصل الماء إلى القاعدة وتُخرج البخار في الفرن.", 3.2, "bold", "#1f6fb2"),
    ]
    y = 22
    for s, size, w, col in lines:
        svg.text((404, y), s, size=size, anchor="end", weight=w, rtl=True, fill=col); y += size * 1.75
    y += 4
    svg.text((404, y), "كمية الطين لكل جزء (جدار 8 مم)", size=3.6, anchor="end", weight="bold", rtl=True); y += 6
    rows = [("القاعدة", "base", 10), ("الصدر", "chest", 6), ("الرأس", "neck", 1)]
    svg.text((404, y), "الجزء", size=3, anchor="end", rtl=True, weight="bold")
    svg.text((350, y), "شرائح", size=3, anchor="end", rtl=True, weight="bold")
    svg.text((320, y), "طين رطب (كجم)", size=3, anchor="end", rtl=True, weight="bold")
    svg.text((285, y), "بعد الحرق (كجم)", size=3, anchor="end", rtl=True, weight="bold"); y += 5
    for name, kk, n in rows:
        svg.text((404, y), name, size=3, anchor="end", rtl=True)
        svg.text((345, y), f"{n}", size=3, anchor="end")
        svg.text((310, y), f"{wet(vol[kk]):.2f}", size=3, anchor="end")
        svg.text((275, y), f"{vol[kk] * 2.2 / 1000:.2f}", size=3, anchor="end"); y += 4.6
    tot = sum(vol.values())
    svg.text((404, y), "المجموع", size=3, anchor="end", rtl=True, weight="bold")
    svg.text((310, y), f"{wet(tot):.2f}", size=3, anchor="end", weight="bold")
    svg.text((275, y), f"{tot * 2.2 / 1000:.2f}", size=3, anchor="end", weight="bold"); y += 7
    svg.text((404, y), "أضف 25% هدراً عند شراء الطين · كثافة الطين الرطب 1.95 والمحروق 2.2 غ/سم³", size=2.8, anchor="end", rtl=True, fill="#555")
    svg.save(path)
    return vol


# ───────────────────────── joints: the cut angle of every slab edge ─────────────────────────
BLOCKS = {"base": "BS", "chest": "U"}


def _inside(block, p, tol=1e-6):
    Hb, Hu = base_halfspaces(), upper_halfspaces()
    in_u = all(n @ p < c - tol for n, c in Hu)
    if block == "chest": return all(n @ p <= c + tol for n, c in Hu)
    return all(n @ p <= c + tol for n, c in Hb) and not in_u


def slabs():
    """code -> dict(face, block, 2D outline (as cut), 3D rings, outward normal, plane constant)."""
    out = {}
    for f in faces():
        full, cut, kept = f.shapes()
        block = "chest" if f.code[0] == "U" else "base"
        g = full if block == "chest" else kept
        rings = [[f.o + x * f.e1 + y * f.e2 for x, y in list(p.exterior.coords)[:-1]]
                 for p in getattr(g, "geoms", [g]) if p.geom_type == "Polygon" and p.area > 1e-4]
        c3 = f.o + f.e1 * g.centroid.x + f.e2 * g.centroid.y
        n = f.n if not _inside(block, c3 + 0.05 * f.n) else -f.n
        out[f.code] = dict(f=f, block=block, g2=g, rings=rings, n=n, c=float(n @ f.o))
    return out


def _seg_dist(p, a, b):
    t = np.clip((p - a) @ (b - a) / max((b - a) @ (b - a), 1e-12), 0, 1)
    return np.linalg.norm(p - (a + t * (b - a)))


def _on_boundary(s, p, tol=2e-3):
    return any(_seg_dist(p, r[i], r[(i + 1) % len(r)]) < tol for r in s["rings"] for i in range(len(r)))


def _into(s, mid, e):
    """unit vector in the slab's plane, perpendicular to edge e, pointing into the slab."""
    d = nrm(np.cross(s["n"], e))
    q = s["f"].to2d([mid + 0.02 * d])[0]
    return d if s["g2"].buffer(1e-6).contains(Point(q)) else -d


def _intervals(p, q, rings, tol=2e-3):
    """parts of segment pq (as t-intervals) that lie on any edge of the given rings."""
    L2 = (q - p) @ (q - p); out = []
    for r in rings:
        for i in range(len(r)):
            a, b = r[i], r[(i + 1) % len(r)]
            # both ends of ab on the infinite line pq?
            da = np.linalg.norm(np.cross(q - p, a - p)) / math.sqrt(L2)
            db = np.linalg.norm(np.cross(q - p, b - p)) / math.sqrt(L2)
            if da > tol or db > tol: continue
            ta, tb = sorted([(a - p) @ (q - p) / L2, (b - p) @ (q - p) / L2])
            t0, t1 = max(0.0, ta), min(1.0, tb)
            if (t1 - t0) * math.sqrt(L2) > tol: out.append((t0, t1))
    return out


def joints():
    """code -> list of (a3, b3, label, kind, other, angle) for every edge run of every slab."""
    S = slabs(); res = {c: [] for c in S}
    for ca, A in S.items():
        others = [cb for cb, B in S.items() if cb != ca and B["block"] == A["block"]]
        for r in A["rings"]:
            for i in range(len(r)):
                p, q = r[i], r[(i + 1) % len(r)]
                L = np.linalg.norm(q - p)
                if L < 1e-3: continue
                e = (q - p) / L
                cuts = sorted([(t0, t1, cb) for cb in others for t0, t1 in _intervals(p, q, S[cb]["rings"])])
                pieces, t = [], 0.0
                for t0, t1, cb in cuts:
                    if t0 > t + 1e-6: pieces.append((t, t0, None))
                    pieces.append((max(t, t0), t1, cb)); t = max(t, t1)
                if t < 1 - 1e-6: pieces.append((t, 1.0, None))
                for t0, t1, cb in pieces:
                    if t1 - t0 < 1e-6: continue
                    a3, b3 = p + (q - p) * t0, p + (q - p) * t1
                    mid = (a3 + b3) / 2; dA = _into(A, mid, e)
                    if cb is not None:
                        B = S[cb]; dB = _into(B, mid, e)
                        geo = math.degrees(math.acos(np.clip(dA @ dB, -1, 1)))
                        if B["n"] @ (0.02 * dA) < 0:       # convex corner: mitre, each slab cut at half the angle
                            res[ca].append((a3, b3, f"∠{geo / 2:.0f}°", "miter", cb, geo))
                        else:                               # inside corner of the seat
                            res[ca].append((a3, b3, "⟂ + حبل", "inner", cb, 360 - geo))
                        continue
                    hit = None
                    for cb2 in others:
                        B = S[cb2]
                        for kind, cc in (("butt", B["c"] - WALL), ("cap", B["c"])):
                            if abs(B["n"] @ a3 - cc) < 2e-3 and abs(B["n"] @ b3 - cc) < 2e-3:
                                if kind == "butt" and not B["g2"].buffer(0.05).contains(Point(B["f"].to2d([mid])[0])): continue
                                hit = (kind, cb2); break
                        if hit: break
                    if hit:
                        B = S[hit[1]]
                        u = nrm(np.cross(e, B["n"]))
                        if u @ (-A["n"]) < 0: u = -u
                        th = math.degrees(math.acos(np.clip(dA @ u, -1, 1)))
                        lab = f"∠{th:.0f}° على {hit[1]}" if hit[0] == "butt" else f"∠{th:.0f}° حافة ظاهرة"
                        res[ca].append((a3, b3, lab, hit[0], hit[1], th))
                    else:
                        res[ca].append((a3, b3, None, "free", None, None))
    return res


def _joint_labels(svg, j, T, k, J):
    f = j["f"]
    if f is None or f.code not in J: return
    g = j["kept"] if j["kind"] == "base" else j["geom"]
    for a3, b3, lab, kind, cb, ang in J[f.code]:
        if lab is None or np.linalg.norm(b3 - a3) * k < 14: continue
        a2, b2 = f.to2d([a3, b3])
        A, B = np.array(T(a2)), np.array(T(b2))
        mid = (A + B) / 2; t = nrm(B - A); nn = np.array([t[1], -t[0]])
        m2 = (np.array(a2) + np.array(b2)) / 2; tt = nrm(np.array(b2) - np.array(a2))
        side = np.array([-tt[1], tt[0]])
        if not g.buffer(1e-6).contains(Point(m2 + side * 0.15)): side = -side
        inside_dir = np.array(T(m2 + side * 0.2)) - np.array(T(m2))
        if nn @ inside_dir < 0: nn = -nn
        ang_t = math.degrees(math.atan2(t[1], t[0]))
        if ang_t > 90: ang_t -= 180
        if ang_t < -90: ang_t += 180
        out = -nn                                   # angle sits just outside the cut line, length just inside
        up = np.array([math.sin(math.radians(ang_t)), -math.cos(math.radians(ang_t))])
        pos = mid + out * (1.1 if out @ up > 0 else 3.1)
        svg.text(pos, lab, size=2.5, fill="#7d3c98", rot=ang_t, rtl="على" in lab or "حبل" in lab or "ظاهرة" in lab)


def verify():
    """Numbers that back the accuracy claims in README §9."""
    S = slabs(); J = joints(); rep = {}
    shared, free = {}, []
    for ca, runs in J.items():
        for a3, b3, lab, kind, cb, ang in runs:
            Lmm = np.linalg.norm(b3 - a3) * 10
            if kind == "free":
                if Lmm > 3: free.append((ca, round(Lmm, 1)))
            elif kind in ("miter", "inner"):
                shared[(ca, cb)] = shared.get((ca, cb), 0) + Lmm
    n_pairs = len(shared) // 2
    pair_err = max(abs(v_ - shared.get((b_, a_), 0)) for (a_, b_), v_ in shared.items())
    rep["paired edge runs"] = n_pairs
    rep["max unmatched length (mm)"] = round(pair_err, 3)
    rep["edges with no joint info"] = free
    mods = modules()
    rep["chest/base overlap (cm3)"] = round((mods[0]["chest"] ^ mods[1]["base"]).volume(), 4)
    area_b = sum(Polygon(S[c]["f"].to2d(r)).area for c in S if S[c]["block"] == "base" for r in S[c]["rings"])
    area_u = sum(Polygon(S[c]["f"].to2d(r)).area for c in S if S[c]["block"] == "chest" for r in S[c]["rings"])
    rep["base slabs area vs chair surface (cm2)"] = (round(area_b, 1), round(mods[0]["base"].surface_area(), 1))
    rep["chest slabs area vs prism surface (cm2)"] = (round(area_u, 1), round(mods[0]["chest"].surface_area(), 1))
    return rep, J


# ───────────────────────── main ─────────────────────────
def main():
    S = solids()
    write_stl(S["solid"], os.path.join(OUT, "vase-solid.stl"))
    write_stl(S["hollow"], os.path.join(OUT, "vase-hollow.stl"))
    errs = render_photo_check(os.path.join(OUT, "fit-check.png"))
    drawings(S, os.path.join(OUT, "drawings.svg"))
    for f in os.listdir(OUT):
        if f.startswith("templates-") and f.endswith(".svg"): os.remove(os.path.join(OUT, f))
    pages = templates(os.path.join(OUT, "templates-{}-{}.svg"))
    mods = modules()
    # mould masters, one per block (the base is the chair shape, seat included)
    for kk in ("base", "chest", "neck"):
        write_stl(mods[0][kk], os.path.join(OUT, f"module-{kk}.stl"))
    mvol = assembly(os.path.join(OUT, "assembly.svg"), mods)
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
    print("template pages:", [os.path.basename(p) for p in pages])
    print("module clay (fired cm3):", {kk: round(v_) for kk, v_ in mvol.items()},
          "wet kg:", {kk: round(v_ / (1 - SHRINK) ** 3 * 1.95 / 1000, 2) for kk, v_ in mvol.items()})
    print(f"V = {np.round(V, 3)}  depth = {np.linalg.norm(V[:2]):.2f}  chest back y = {(yf + V[1]):.2f}")


if __name__ == "__main__":
    main()
