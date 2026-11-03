"""Caustic light pattern for the sand: a horizontally tileable band.

Worley (cellular) noise on a cylinder; caustic lines are where the nearest and second-nearest
feature points are nearly equidistant (F2 - F1 small). Rows are squashed toward the top so
cells look flatter further away, as on a floor seen at a low angle. Alpha fades in at the top
edge so the band blends into the back of the sand.
"""
import numpy as np
from PIL import Image


def caustic_band(w=1024, h=300, seed=0, cells=26, sharp=0.09):
    rng = np.random.default_rng(seed)
    n = cells * 4
    pts = np.column_stack([rng.random(n) * w, rng.random(n) * (h * 2.0)])
    ys = (np.linspace(0, 1, h) ** 1.6) * h * 2.0  # world v: rows compressed near the top
    xs = np.arange(w)
    X, Y = np.meshgrid(xs, ys)
    d1 = np.full(X.shape, 1e9)
    d2 = np.full(X.shape, 1e9)
    for px, py in pts:
        dx = np.abs(X - px)
        dx = np.minimum(dx, w - dx)  # wrap horizontally
        d = np.hypot(dx, Y - py)
        d2 = np.where(d < d1, d1, np.minimum(d2, d))
        d1 = np.minimum(d1, d)
    cell = w / cells
    c = np.exp(-(d2 - d1) / (cell * sharp))
    yy = np.linspace(0, 1, h)[:, None]
    fade = np.clip(yy / 0.25, 0, 1) ** 2 * (0.55 + 0.45 * yy)
    a = np.clip(c * fade, 0, 1)
    arr = np.zeros((h, w, 4), np.uint8)
    arr[..., 0], arr[..., 1], arr[..., 2] = 225, 245, 255
    arr[..., 3] = (a * 255).astype(np.uint8)
    return Image.fromarray(arr)
