"""Usage: .venv/bin/python tools/fx.py

Procedural light and particle sprites: light shafts, marine snow and sand puffs.
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from imgio import save_rgba  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "roku/reefglass/images"


def soft(name, size, inner=0.0):
    """A soft white round spot."""
    yy, xx = np.mgrid[0:size, 0:size]
    r = np.hypot(xx - (size - 1) / 2, yy - (size - 1) / 2) / (size / 2)
    a = np.clip(1 - (r - inner) / (1 - inner), 0, 1) ** 2
    arr = np.zeros((size, size, 4), np.uint8)
    arr[..., :3] = 255
    arr[..., 3] = (a * 255).astype(np.uint8)
    save_rgba(Image.fromarray(arr), OUT / name)


def ray():
    """A light shaft, widening downward. Drawn 1.1x tall from y = -40, it fades out by
    y ~ 700: in open water, above the reef's base and the cave."""
    w, h = 160, 680
    x = np.linspace(-1, 1, w)[None, :]
    y = np.linspace(0, 1, h)[:, None]
    a = np.clip(1 - np.abs(x) / (0.4 + 0.6 * y), 0, 1) ** 1.5 * (1 - y) ** 1.3
    arr = np.zeros((h, w, 4), np.uint8)
    arr[..., :3] = (230, 245, 255)
    arr[..., 3] = (a * 255).astype(np.uint8)
    save_rgba(Image.fromarray(arr), OUT / "ray.png")

soft("mote.png", 8)
soft("puff.png", 24)
ray()
print("fx written")
