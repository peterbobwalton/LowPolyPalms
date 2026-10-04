"""
Greyscale frond pattern for the palms, multiplied by the frond colour (live green, yellowing, dead brown all share it).
U runs across the frond (0 left leaflet tips, 0.5 the midrib, 1 right tips), V along it (the generator tiles it 3x).
Leaflets angle out and forward towards the tip, with dark gaps between them and a pale vein down each. Opaque: no alpha.
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


def value(u, v, rng_noise):
    du = abs(u - 0.5) * 2.0                          # 0 at the midrib, 1 at the leaflet tips
    if du < 0.035:
        return 0.95 if du < 0.022 else 0.6         # pale rib with a dark edge
    phase = v * N + du * SWEEP                       # leaflets sweep towards the tip on both sides: a herringbone
    k = math.floor(phase)
    s = phase - k
    # each leaflet its own shade (seeded by leaflet and side) so the frond doesn't look ruled
    tone = random.Random(int(k) % N * 2 + (u > 0.5)).uniform(-0.09, 0.09)     # repeats per tile: no seam
    if s < 0.1:
        val = 0.5                                   # narrow gap between leaflets
    else:
        t = (s - 0.1) / 0.9
        val = 0.8 + tone + 0.12 * math.sin(math.pi * t)     # rounded leaflet
        if abs(t - 0.45) < 0.05:
            val = min(1.0, val + 0.07)              # leaflet vein
    val *= 1.0 - 0.25 * du * du                     # darker towards the tips
    return max(0.0, min(1.0, val + rng_noise))


def main():
    rng = random.Random(7)
    big = Image.new("L", (W * SS, H * SS))
    px = big.load()
    for y in range(H * SS):
        v = (y + 0.5) / (H * SS)
        for x in range(W * SS):
            u = (x + 0.5) / (W * SS)
            px[x, y] = int(255 * value(u, v, rng.uniform(-0.03, 0.03)))
    img = big.resize((W, H), Image.LANCZOS)
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, "T_PalmFrond.png")
    img.save(path)
    lin = [((c / 255 + 0.055) / 1.055) ** 2.4 if c > 10 else c / 255 / 12.92 for c in img.get_flattened_data()]
    print(path, 'gain', round(len(lin) / sum(lin), 3))


if __name__ == "__main__":
    main()
