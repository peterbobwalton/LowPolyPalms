"""
Greyscale frond pattern for the palms, multiplied by the frond colour (live green, yellowing, dead brown all share it).
U runs across the frond (0 left leaflet tips, 0.5 the midrib, 1 right tips), V along it (the generator tiles it 3x).
Leaflets angle out and forward towards the tip, each shaded like a folded leaf (gradients, no lines), so they read as
a herringbone of V's. Opaque single channel: no alpha.
"""
import math
import os
import random
import sys

from PIL import Image

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
W, H, SS = 256, 512, 2          # final size, supersampling
N = 10                          # leaflets per tile per side
# How far a leaflet runs along the frond (in leaflet pitches) between the midrib and its tip. A tile is about 1.5 m of
# frond and 0.9 m across, so 5 pitches puts the leaflets at roughly 50 degrees to the midrib on the mesh: a herringbone.
SWEEP = 5.0


def smooth(e0, e1, x):
    t = max(0.0, min(1.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def value(u, v, rng_noise):
    """No lines: every leaflet is shaded like a folded leaf - dark at its leading edge, brightening to the lit
    crease, then a darker underside - so the leaflets read as a V (herringbone) along the frond."""
    du = abs(u - 0.5) * 2.0                          # 0 at the midrib, 1 at the leaflet tips
    phase = v * N - du * SWEEP                       # leaflets sweep towards the tip on both sides (V points to the base)
    k = math.floor(phase)
    s = phase - k                                    # 0..1 across one leaflet
    tone = random.Random(int(k) % N * 2 + (u > 0.5)).uniform(-0.07, 0.07)   # repeats per tile: no seam
    if s < 0.58:
        val = 0.66 + 0.33 * (s / 0.58) ** 1.4         # lit half: dark edge -> bright crease
    else:
        t = (s - 0.58) / 0.42
        val = 0.99 - 0.20 * smooth(0.0, 0.25, t) - 0.10 * t   # past the crease: drops into the shaded half
    val += tone
    val *= 0.84 + 0.16 * smooth(0.03, 0.22, du)     # shadowed where the leaflets join the midrib
    val *= 1.0 - 0.18 * du * du                     # a little darker towards the tips
    rib = 1.0 - smooth(0.015, 0.045, du)            # soft pale midrib
    val = val * (1 - rib) + 0.9 * rib
    return max(0.0, min(1.0, val + rng_noise))


def main():
    rng = random.Random(7)
    big = Image.new("L", (W * SS, H * SS))
    px = big.load()
    for y in range(H * SS):
        v = (y + 0.5) / (H * SS)
        for x in range(W * SS):
            u = (x + 0.5) / (W * SS)
            px[x, y] = int(255 * value(u, v, rng.uniform(-0.02, 0.02)))
    img = big.resize((W, H), Image.LANCZOS)
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, "T_PalmFrond.png")
    img.save(path)
    lin = [((c / 255 + 0.055) / 1.055) ** 2.4 if c > 10 else c / 255 / 12.92 for c in img.get_flattened_data()]
    print(path, 'gain', round(len(lin) / sum(lin), 3))


if __name__ == "__main__":
    main()
