"""Usage: .venv/bin/python tools/regions.py

Finds the parts of the big alpha layers that hold any pixels, so the screensaver draws only
those (as sub-rectangles of the same bitmap) instead of blending acres of transparent pixels.
The GPU's blend cost scales with area, while each extra draw call costs script time, so the
rectangles are horizontal bands split into runs, at the band height and gap that minimize the
estimated frame time. Writes plate.fgRects and caustics.occluderRects (bitmap px: x, y, w, h)
into scenes/reef.json.

Run it after anything rebuilds fg.png (tools/layers.py) or rocks_low.png (tools/plate.py).
"""
import json
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
IMAGES = ROOT / "roku/reefglass/images"
SCENE = ROOT / "roku/reefglass/scenes/reef.json"
T = 16  # occupancy cell, px
# Measured on the 3810X: one full-screen alpha layer ~4.9 ms, one draw call ~0.02 ms.
MS_PER_PX = 4.9 / (1920 * 1080)
MS_PER_DRAW = 0.02


def bands(occ, bh, gap):
    """Rects (cell units) covering occ: bands bh cells tall, runs merged across gaps <= gap."""
    rows, cols = occ.shape
    out = []
    for y0 in range(0, rows, bh):
        band = occ[y0:y0 + bh]
        used = np.nonzero(band.any(axis=1))[0]
        if not len(used):
            continue
        # Trim the band to its used rows.
        b0, b1 = y0 + used[0], y0 + used[-1] + 1
        colsu = np.nonzero(band.any(axis=0))[0]
        start = prev = colsu[0]
        for c in list(colsu[1:]) + [None]:
            if c is not None and c - prev <= gap + 1:
                prev = c
                continue
            out.append((start, b0, prev + 1 - start, b1 - b0))
            if c is not None:
                start = prev = c
    return out


def best_rects(alpha):
    h, w = alpha.shape
    ph, pw = -(-h // T) * T, -(-w // T) * T
    a = np.zeros((ph, pw), bool)
    a[:h, :w] = alpha > 0
    occ = a.reshape(ph // T, T, pw // T, T).any(axis=(1, 3))
    best = None
    for bh in range(2, 40):
        for gap in range(0, 12):
            rs = bands(occ, bh, gap)
            area = sum(rw * rh for _, _, rw, rh in rs) * T * T
            cost = area * MS_PER_PX + len(rs) * MS_PER_DRAW
            if best is None or cost < best[0]:
                best = (cost, rs, area)
    cost, rs, area = best
    px = [[int(x * T), int(y * T), int(min(rw * T, w - x * T)), int(min(rh * T, h - y * T))] for x, y, rw, rh in rs]
    full = w * h * MS_PER_PX + MS_PER_DRAW
    return px, area / (w * h), cost, full


def main():
    cfg = json.loads(SCENE.read_text())
    for name, sect, key in (("fg.png", "plate", "fgRects"), ("rocks_low.png", "caustics", "occluderRects")):
        alpha = np.array(Image.open(IMAGES / name).convert("RGBA"))[..., 3]
        rects, frac, cost, full = best_rects(alpha)
        cfg[sect][key] = rects
        print(f"{name}: {len(rects)} rects, {frac:.0%} of its area, est {full:.2f} -> {cost:.2f} ms")
    SCENE.write_text(json.dumps(cfg, indent=2) + "\n")


if __name__ == "__main__":
    main()
