"""Write the coarse coral map into scenes/reef.json.

Usage: .venv/bin/python tools/coralmask.py [--cell 40] [--grow 1]

Fish may only cross the reef layer's depth (fgZ) or the anemone's depth where nothing of the
reef is behind or in front of them; otherwise the crossing would flip them from in front of the
coral to behind it in a single frame. The map is fg.png's alpha in cells of --cell px ('#' =
coral, '.' = open water), grown by --grow cells so a fish's fins clear the coral too.
"""
import argparse
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
IMAGES = ROOT / "roku/reefglass/images"
SCENE = ROOT / "roku/reefglass/scenes/reef.json"

ap = argparse.ArgumentParser()
ap.add_argument("--cell", type=int, default=40)
ap.add_argument("--grow", type=int, default=1)
a = ap.parse_args()

alpha = np.array(Image.open(IMAGES / "fg.png").convert("RGBA"))[..., 3].astype(np.float32) / 255
c = a.cell
h, w = alpha.shape[0] // c, alpha.shape[1] // c
occ = (alpha[:h * c, :w * c].reshape(h, c, w, c).mean(axis=(1, 3)) > 0.1).astype(np.uint8)
if a.grow:
    k = 2 * a.grow + 1
    occ = cv2.dilate(occ, np.ones((k, k), np.uint8))
rows = ["".join("#" if v else "." for v in r) for r in occ]
cfg = json.loads(SCENE.read_text())
cfg["coral"] = {"cell": c, "rows": rows}
SCENE.write_text(json.dumps(cfg, indent=2) + "\n")
print("\n".join(rows))
