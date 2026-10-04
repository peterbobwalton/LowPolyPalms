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
N = 14                          # leaflets per tile per side
SLANT = 0.55                    # how far a leaflet runs towards the tip across the half-width (in leaflet pitches)


def value(u, v, rng_noise):
    du = abs(u - 0.5) * 2.0                          # 0 at the midrib, 1 at the leaflet tips
    if du < 0.035:
        return 0.98 if du < 0.022 else 0.62        # pale rib with a dark edge
    phase = v * N + du * SLANT * N / 4.0
    s = phase - math.floor(phase)
    if s < 0.13:
        val = 0.42                                  # gap between leaflets
    else:
        t = (s - 0.13) / 0.87
        val = 0.80 + 0.14 * math.sin(math.pi * t)  # rounded leaflet
        if abs(t - 0.5) < 0.06:
            val = min(1.0, val + 0.08)              # leaflet vein
    val *= 1.0 - 0.22 * du * du                     # darker towards the tips
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
    print(path, sum(img.getdata()) / (W * H) / 255.0)


if __name__ == "__main__":
    main()
