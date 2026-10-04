"""
LowPolyPalms generator: 5 live coconut palms and 3 dead ones as OBJ + MTL. No dependencies beyond Python 3.

    python gen_palms.py [out_dir]

Z up, centimetres, pivot at the foot of the trunk.

Live palm: a tapered trunk with a gentle bow (it leans out low and straightens towards the top), alternating ring
bands, a husk boot and the unopened spear at the crown; arching fronds, youngest up top, older ones arching out and
down with hanging tips, the oldest yellowing; a skirt of dead brown fronds hanging against the trunk below the
crown; clusters of coconuts under the crown.
Dead palms: a snapped bare snag, a dried palm with every frond hanging brown, a leaning palm with a broken crown.

A frond is a rachis polyline with leaflets hanging off both sides as an inverted V, the edge widths alternating for
a feathery saw-tooth silhouette. Fronds are one-sided strips: render them with a TWO-SIDED material.

Material slots (flat colours, see COLOURS): TrunkA, TrunkB (bands), Husk, Young, Frond, Old, Dead, Nut.
"""
import math
import os
import random
import sys

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "OBJ")

# linear RGB base colours (as used in Unreal); the MTL gets them converted to sRGB
COLOURS = {"TrunkA": (0.24, 0.20, 0.15), "TrunkB": (0.16, 0.13, 0.10), "Husk": (0.13, 0.08, 0.04),
           "Young": (0.17, 0.28, 0.04), "Frond": (0.06, 0.18, 0.03), "Old": (0.22, 0.17, 0.05),
           "Dead": (0.17, 0.09, 0.035), "Nut": (0.20, 0.25, 0.04)}


def srgb(c):
    return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055


class Mesh:
    """Flat-shaded OBJ builder in cm; faces CCW seen from the front. Fronds carry UVs for the frond texture."""

    def __init__(self):
        self.v, self.vt, self.vn, self.vi, self.ti, self.ni, self.faces = [], [], [], {}, {}, {}, {}

    def _idx(self, store, lut, val):
        k = tuple(round(c, 4) for c in val)
        if k not in lut:
            store.append(k)
            lut[k] = len(store)
        return lut[k]

    def poly(self, slot, pts, uvs=None):
        a, b, c = pts[0], pts[1], pts[-1]
        u = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
        w = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
        n = (u[1] * w[2] - u[2] * w[1], u[2] * w[0] - u[0] * w[2], u[0] * w[1] - u[1] * w[0])
        L = math.sqrt(sum(x * x for x in n))
        if L < 1e-9:
            return                                   # degenerate
        ni = self._idx(self.vn, self.ni, tuple(x / L for x in n))
        uvs = uvs or [(0.0, 0.0)] * len(pts)
        self.faces.setdefault(slot, []).append([(self._idx(self.v, self.vi, p), self._idx(self.vt, self.ti, t), ni)
                                                for p, t in zip(pts, uvs)])

    def tris(self):
        return sum(len(f) - 2 for fs in self.faces.values() for f in fs)

    def write(self, path, comment=""):
        base = os.path.splitext(os.path.basename(path))[0]
        with open(path, "w") as f:
            f.write("# LowPolyPalms - %s (cm, Z up)\nmtllib %s.mtl\no %s\n" % (comment, base, base))
            for p in self.v:
                f.write("v %.2f %.2f %.2f\n" % p)
            for t in self.vt:
                f.write("vt %.4f %.4f\n" % t)
            for n in self.vn:
                f.write("vn %.4f %.4f %.4f\n" % n)
            for slot in COLOURS:
                if slot in self.faces:
                    f.write("usemtl %s\n" % slot)
                    for face in self.faces[slot]:
                        f.write("f " + " ".join("%d/%d/%d" % c for c in face) + "\n")
        with open(os.path.join(os.path.dirname(path), base + ".mtl"), "w") as f:
            for slot in COLOURS:
                if slot in self.faces:
                    r, g, b = (srgb(c) for c in COLOURS[slot])
                    f.write("newmtl %s\nKd %.4f %.4f %.4f\nKs 0 0 0\nd 1\nillum 1\n" % (slot, r, g, b))
                    if slot in FRONDS:
                        f.write("map_Kd T_PalmFrond.png\n")
                    f.write("\n")


FRONDS = ("Young", "Frond", "Old", "Dead")


def quad(m, slot, a, b, c, d):
    m.poly(slot, [a, b, c, d])


def tri(m, slot, a, b, c):
    m.poly(slot, [a, b, c])


Z = (0.0, 0.0, 1.0)


def add(a, b, k=1.0):
    return (a[0] + b[0] * k, a[1] + b[1] * k, a[2] + b[2] * k)


def sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def norm(a):
    L = math.sqrt(a[0] ** 2 + a[1] ** 2 + a[2] ** 2) or 1.0
    return (a[0] / L, a[1] / L, a[2] / L)


# ------------------------------------------------------------------ trunk
def trunk_curve(H, lean, bow, yaw, wob, seg):
    """Centre line: leans out quickly low down then straightens; wob adds a sideways S."""
    c, s = math.cos(yaw), math.sin(yaw)
    pts = []
    for i in range(seg + 1):
        t = i / seg
        a = lean * (1 - (1 - t) ** 2) * (1 - bow) + lean * t * bow
        b = wob * math.sin(math.pi * t)
        pts.append((a * c - b * s, a * s + b * c, H * t))
    return pts


def trunk(m, pts, r0, r1, sides=6, jag=None, rng=None):
    """Tapered tube along pts (flared foot), alternating band colours. Returns the top ring radius."""
    n = len(pts) - 1
    rings = []
    for i, p in enumerate(pts):
        t = i / n
        T = norm(sub(pts[min(i + 1, n)], pts[max(i - 1, 0)]))
        e1 = norm(cross((0.0, 1.0, 0.0), T))
        e2 = cross(T, e1)
        r = r1 + (r0 - r1) * (1 - t) ** 1.4
        if i == 0:
            r *= 1.45                       # root flare
        ring = []
        for k in range(sides):
            a = 2 * math.pi * (k + 0.5 * (i % 2)) / sides
            q = add(add(p, e1, r * math.cos(a)), e2, r * math.sin(a))
            if jag and i == n:
                q = add(q, Z, -rng.uniform(0, jag))      # snapped top: ragged rim
            ring.append(q)
        rings.append(ring)
    for i in range(n):
        slot = "TrunkA" if i % 2 == 0 else "TrunkB"
        A, B = rings[i], rings[i + 1]
        for k in range(sides):
            k1 = (k + 1) % sides
            if i % 2 == 0:
                # B ring is rotated half a step: zigzag between rings
                tri(m, slot, A[k], A[k1], B[k])
                tri(m, slot, B[k], A[k1], B[k1])
            else:
                tri(m, slot, A[k], B[k1], B[k])
                tri(m, slot, A[k], A[k1], B[k1])
    return rings[-1]


def cap(m, slot, ring, top):
    for k in range(len(ring)):
        tri(m, slot, ring[k], ring[(k + 1) % len(ring)], top)


# ------------------------------------------------------------------ fronds
def frond_path(base, az, elev, L, droop, n):
    """Arching rachis: straight line at elevation elev, pulled down by droop*(s/L)^2 towards the tip."""
    d = (math.cos(elev) * math.cos(az), math.cos(elev) * math.sin(az), math.sin(elev))
    return [add(add(base, d, L * j / n), Z, -droop * (j / n) ** 2) for j in range(n + 1)]


def uvface(m, slot, pts, uvs):
    m.poly(slot, pts, uvs)


def frond(m, slot, pts, az, wmax, fold0, fold1, rng, bare=0.12, serr=0.42, tiles=3.0):
    """Leaflets either side of the rachis, folded down as an inverted V, saw-tooth edges.
    UVs for the frond texture: U across (0.5 on the rachis, out to 0/1 at full leaflet width), V along, tiled."""
    side = (math.sin(az), -math.cos(az), 0.0)                   # horizontal, constant along the frond
    n = len(pts) - 1
    prev = None
    for j, p in enumerate(pts):
        u = j / n
        T = norm(sub(pts[min(j + 1, n)], pts[max(j - 1, 0)]))
        up = norm(cross(side, T))
        if u < bare:
            w = 6.0
        else:
            v = (u - bare) / (1 - bare)
            w = wmax * math.sin(math.pi * min(1.0, 0.12 + v * 0.95)) ** 0.7
        if j % 2 and 0 < j < n:
            w *= serr
        if j == n:
            w = 0.0
        f = math.radians(fold0 + (fold1 - fold0) * u) + rng.uniform(-0.08, 0.08)
        R = add(add(p, side, w * math.cos(f)), up, -w * math.sin(f))
        Lf = add(add(p, side, -w * math.cos(f)), up, -w * math.sin(f))
        tv = tiles * u
        eu = 0.5 * min(1.0, w / max(wmax, 1.0))                # texture width follows the leaflet width
        if prev:
            p0, R0, L0, tv0, eu0 = prev
            if w > 0:
                uvface(m, slot, [p0, p, R, R0], [(0.5, tv0), (0.5, tv), (0.5 + eu, tv), (0.5 + eu0, tv0)])
                uvface(m, slot, [L0, Lf, p, p0], [(0.5 - eu0, tv0), (0.5 - eu, tv), (0.5, tv), (0.5, tv0)])
            else:
                uvface(m, slot, [p0, p, R0], [(0.5, tv0), (0.5, tv), (0.5 + eu0, tv0)])
                uvface(m, slot, [L0, p, p0], [(0.5 - eu0, tv0), (0.5, tv), (0.5, tv0)])
        prev = (p, R, Lf, tv, eu)


def coconuts(m, centre, axis_az, rng, count, r=13.0):
    for i in range(count):
        a = axis_az + rng.uniform(-0.6, 0.6)
        rad = rng.uniform(18, 42)
        q = (centre[0] + math.cos(a) * rad, centre[1] + math.sin(a) * rad, centre[2] - rng.uniform(15, 75))
        rr = r * rng.uniform(0.9, 1.15)
        P = [add(q, (rr, 0, 0)), add(q, (0, rr, 0)), add(q, (-rr, 0, 0)), add(q, (0, -rr, 0))]
        top, bot = add(q, Z, rr * 1.2), add(q, Z, -rr * 1.25)
        for k in range(4):
            tri(m, "Nut", P[k], P[(k + 1) % 4], top)
            tri(m, "Nut", P[(k + 1) % 4], P[k], bot)


def crown(m, top_ring, top, T, rng, fronds, skirt, nuts, scale=1.0, spear=True, dead=False):
    """Husk boot, spear, live fronds, dead skirt, coconuts."""
    boot_h = 70 * scale
    ctr = add(top, T, boot_h)
    # husk boot: widen then close over
    sides = len(top_ring)
    mid = []
    for k, q in enumerate(top_ring):
        d = sub(q, top)
        mid.append(add(add(top, d, 1.45), T, boot_h * 0.55))
    for k in range(sides):
        k1 = (k + 1) % sides
        quad(m, "Husk", top_ring[k], top_ring[k1], mid[k1], mid[k])
    cap(m, "Husk", mid, ctr)
    if spear:
        base = [add(ctr, (math.cos(a) * 9, math.sin(a) * 9, -10)) for a in (0, 2.1, 4.2)]
        tipp = add(ctr, T, 150 * scale)
        for k in range(3):
            tri(m, "Young", base[k], base[(k + 1) % 3], tipp)
    golden = math.pi * (3 - math.sqrt(5))
    az0 = rng.uniform(0, 2 * math.pi)
    n = len(fronds)
    for i, (slot, elev, L, droop, wmax, f0, f1) in enumerate(fronds):
        az = az0 + i * golden + rng.uniform(-0.15, 0.15)
        b = add(ctr, (math.cos(az) * 14, math.sin(az) * 14, -12 - 30 * i / max(n, 1)))
        pts = frond_path(b, az, math.radians(elev), L * scale, droop * scale, 10)
        frond(m, slot, pts, az, wmax * scale, f0, f1, rng)
    for i, (elev, L, wmax) in enumerate(skirt):
        az = az0 + 0.4 + i * (2 * math.pi / max(len(skirt), 1)) + rng.uniform(-0.25, 0.25)
        b = add(ctr, (math.cos(az) * 22, math.sin(az) * 22, -50 * scale - rng.uniform(0, 25)))
        pts = frond_path(b, az, math.radians(elev), L * scale, -10 * scale, 5)
        frond(m, "Dead", pts, az, wmax * scale, 70, 82, rng, bare=0.08, serr=0.55)
    for k in range(nuts[0]):
        coconuts(m, add(ctr, Z, -40 * scale), az0 + k * 2.3 + 0.7, rng, nuts[1])
    return ctr


# ------------------------------------------------------------------ variants
def live_palm(name, seed, H, lean, bow, wob, n_fronds, n_skirt, nuts, scale=1.0, r0=26.0, r1=15.0):
    rng = random.Random(seed)
    m = Mesh()
    pts = trunk_curve(H, lean, bow, rng.uniform(0, 2 * math.pi), wob, 12)
    ring = trunk(m, pts, r0, r1)
    top = pts[-1]
    T = norm(sub(pts[-1], pts[-2]))
    fr = []
    for i in range(n_fronds):
        t = i / max(n_fronds - 1, 1)                 # 0 = youngest (top), 1 = oldest
        slot = "Young" if t < 0.15 else ("Old" if t > 0.84 else "Frond")
        elev = 68 - 88 * t + rng.uniform(-6, 6)
        L = rng.uniform(400, 460) * (0.8 + 0.2 * min(t / 0.3, 1))     # young ones shorter; older ones no bigger
        droop = 60 + 300 * t ** 1.1 + rng.uniform(-30, 30)
        if slot == "Old":
            L *= 0.85                                # oldest green fronds: no bigger than the ones above
        # leaflets hang: the V opens wider towards the tip and on older fronds
        fr.append((slot, elev, L, droop, rng.uniform(80, 95) * (1 - 0.15 * max(t - 0.7, 0) / 0.3), 40 + 15 * t, 62 + 16 * t))
    # dead skirt: old fronds, no longer than the mature ones and shrivelled narrower
    # never bigger than the leaves above them: capped by the smallest mature/old frond
    cap_L = 0.9 * min(f[2] for f in fr if f[0] != "Young")
    cap_W = 0.9 * min(f[4] for f in fr if f[0] != "Young")
    sk = [(rng.uniform(-84, -62), min(rng.uniform(260, 340), cap_L), min(rng.uniform(24, 32), cap_W)) for _ in range(n_skirt)]
    crown(m, ring, top, T, rng, fr, sk, nuts, scale)
    m.write(os.path.join(OUT, name + ".obj"), "coconut palm " + name)
    return m.tris()


def dead_snag(name, seed):
    """Bare trunk snapped off at 6 m: ragged top, a couple of frond stubs."""
    rng = random.Random(seed)
    m = Mesh()
    pts = trunk_curve(520, 80, 0.2, rng.uniform(0, 6.3), 25, 9)
    ring = trunk(m, pts, 25, 17, jag=55, rng=rng)
    cap(m, "Husk", ring, add(pts[-1], Z, -60))
    for k in range(3):
        az = rng.uniform(0, 6.3)
        b = add(pts[-1], (math.cos(az) * 15, math.sin(az) * 15, -120 - k * 70))
        frond(m, "Dead", frond_path(b, az, math.radians(rng.uniform(-60, -20)), rng.uniform(60, 110), 5, 2), az, 10, 60, 70, rng)
    m.write(os.path.join(OUT, name + ".obj"), "dead palm snag")
    return m.tris()


def dead_dried(name, seed):
    """Full height but dead: every frond brown, collapsed and hanging round the trunk."""
    rng = random.Random(seed)
    m = Mesh()
    pts = trunk_curve(600, 110, 0.3, rng.uniform(0, 6.3), 30, 12)
    ring = trunk(m, pts, 26, 15)
    T = norm(sub(pts[-1], pts[-2]))
    fr = [("Dead", rng.uniform(-50, 15), rng.uniform(320, 400), rng.uniform(200, 320), rng.uniform(36, 48), 55, 75)
          for _ in range(11)]
    sk = [(rng.uniform(-88, -76), rng.uniform(260, 340), rng.uniform(24, 32)) for _ in range(9)]
    crown(m, ring, pts[-1], T, rng, fr, sk, (0, 0), spear=False)
    m.write(os.path.join(OUT, name + ".obj"), "dried dead palm")
    return m.tris()


def dead_broken(name, seed):
    """Tall leaning trunk, crown mostly gone: a few fronds snapped at the stem hanging straight down."""
    rng = random.Random(seed)
    m = Mesh()
    pts = trunk_curve(650, 190, 0.15, rng.uniform(0, 6.3), -40, 12)
    ring = trunk(m, pts, 25, 13)
    T = norm(sub(pts[-1], pts[-2]))
    ctr = crown(m, ring, pts[-1], T, rng, [], [(rng.uniform(-88, -80), rng.uniform(240, 320), 30) for _ in range(5)],
                (0, 0), spear=False)
    for k in range(5):
        az = rng.uniform(0, 6.3)
        b = add(ctr, (math.cos(az) * 14, math.sin(az) * 14, -15))
        first = frond_path(b, az, math.radians(rng.uniform(10, 40)), rng.uniform(90, 160), 10, 2)
        kink = first[-1]
        hang = [add(kink, (math.cos(az) * 15 * j, math.sin(az) * 15 * j, -95 * j)) for j in range(1, 4)]
        frond(m, "Dead", first + hang, az, 34, 60, 80, rng, bare=0.35, serr=0.55)
    m.write(os.path.join(OUT, name + ".obj"), "broken dead palm")
    return m.tris()


VARIANTS = [
    ("SM_Palm_Coco_A", lambda n: live_palm(n, 11, 620, 150, 0.25, 20, 19, 7, (3, 4))),
    ("SM_Palm_Coco_B", lambda n: live_palm(n, 12, 700, 300, 0.05, 40, 18, 8, (2, 5))),
    ("SM_Palm_Coco_C", lambda n: live_palm(n, 13, 560, 45, 0.6, 10, 20, 6, (3, 3))),
    ("SM_Palm_Coco_D", lambda n: live_palm(n, 14, 600, 170, 0.4, -110, 17, 9, (2, 4))),
    ("SM_Palm_Coco_E", lambda n: live_palm(n, 15, 380, 60, 0.5, 15, 15, 5, (0, 0), scale=0.8, r0=30, r1=20)),
    ("SM_Palm_Dead_A", lambda n: dead_snag(n, 21)),
    ("SM_Palm_Dead_B", lambda n: dead_dried(n, 22)),
    ("SM_Palm_Dead_C", lambda n: dead_broken(n, 23)),
]

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for name, f in VARIANTS:
        print(name, f(name))
