"""Turn a generated reef plate into the plate layers (gen/plate/): the first, one-screen tank's
art, kept as the source the wide tank's reefs, colors and sand are built from (README step 5).
The caustic band it records is no longer drawn.

Usage:
  .venv/bin/python tools/plate.py grid <plate.png> <out.jpg>
      1080p copy with a labeled 100 px grid, for reading coordinates and tracing outlines

  .venv/bin/python tools/plate.py build <plate.png> --spec gen/plate_spec.json
      writes gen/plate/{bg.jpg, rocks_low.png} and the caustic band into
      gen/base_scene.json; the check image goes to gen/work/. fg.png comes from tools/layers.py
      (depth), run separately.

  .venv/bin/python tools/plate.py rocks --spec gen/plate_spec.json
      rebuilds rocks_low.png alone from the finished bg.jpg

The spec (hand traced on the grid image, 1080p screen px):
  {
    "sand": [[x, y], ...],              polygon of open sand; caustics land only inside it
    "causticTop": 780,                  first row of the caustic band
    "piles": [[x0, y0, x1, y1], ...],   optional: boxes above the band whose rock and coral
                                        (whatever is not blue water) also hide far fish
    "occlude": [[[x, y], ...], ...]     optional: polygons (the cave mouth) redrawn whole over
                                        the light, so they stay dark
  }
The anemone and the giant clam are part of the plate.
"""
import json
import math
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from imgio import save_rgba  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
IMAGES = ROOT / "roku/reefglass/images"
PLATE = ROOT / "gen/plate"   # the one-screen plate: source of the wide tank\'s reefs, colors, sand
SCENE = ROOT / "gen/base_scene.json"
WORK = ROOT / "gen/work"


def load_1080(path):
    rgb = np.array(Image.open(path).convert("RGB"))
    h, w = rgb.shape[:2]
    ch = round(w * 1080 / 1920)
    rgb = rgb[(h - ch) // 2:(h - ch) // 2 + ch]
    return cv2.resize(rgb, (1920, 1080), interpolation=cv2.INTER_AREA)


def grid(src, out):
    img = load_1080(src)
    for x in range(0, 1920, 100):
        cv2.line(img, (x, 0), (x, 1079), (255, 255, 0), 1)
        cv2.putText(img, str(x), (x + 3, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
    for y in range(0, 1080, 100):
        cv2.line(img, (0, y), (1919, y), (255, 255, 0), 1)
        cv2.putText(img, str(y), (3, y - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
    Image.fromarray(img).save(out, quality=85)


def poly_mask(pts, feather=0):
    m = np.zeros((1080, 1920), np.float32)
    cv2.fillPoly(m, [np.array(pts, np.int32)], 1.0)
    if feather:
        m = cv2.GaussianBlur(m, (0, 0), feather)
    return m


def guided(guide, p, r=5, eps=1e-3):
    box = lambda x: cv2.boxFilter(x, -1, (2 * r + 1, 2 * r + 1))
    mi, mp = box(guide), box(p)
    a = (box(guide * p) - mi * mp) / (box(guide * guide) - mi * mi + eps)
    b = mp - a * mi
    return np.clip(box(a) * guide + box(b), 0, 1)


def rocks_layer(rgb, spec, cfg):
    """Write rocks_low.png: the reef's base rocks, drawn over the caustics, the light rays and
    the fish behind the reef. It is everything in the caustic band that is not open sand, plus, for each
    "pile" box above the band, the rock and coral standing out against the water there (keyed
    by how blue a pixel is). Returns the caustic band's top row and the sand mask."""
    top = spec["causticTop"]
    sand = poly_mask(spec["sand"], 3)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255
    sand = guided(gray, sand)
    rocks = 1 - sand
    rocks[:top] = 0
    otop = top
    f = rgb.astype(np.float32)
    blue = f[..., 2] - f[..., 0]
    for x0, y0, x1, y1 in spec.get("piles", []):
        k = np.clip((60 - blue[y0:y1, x0:x1]) / 30, 0, 1)
        k = cv2.morphologyEx(k, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        k = cv2.GaussianBlur(k, (0, 0), 0.8)
        rocks[y0:y1, x0:x1] = np.maximum(rocks[y0:y1, x0:x1], k)
        otop = min(otop, y0)
    # Never open water: a sliver above the sand line would otherwise hide far fish there.
    rocks = rocks * np.clip((60 - blue) / 30, 0, 1)
    # "occlude" polygons (the cave mouth) are redrawn whole, so the light drawn before this
    # layer never shows in them.
    for poly in spec.get("occlude", []):
        m = poly_mask(poly, 1.5)
        rocks = np.maximum(rocks, m)
        otop = min(otop, min(y for _, y in poly) - 4)
    # Where the coral layer (fg.png, drawn later over everything here) is solid, the rocks are
    # never seen: leave them out, which makes this file much smaller.
    if (PLATE / "fg.png").exists():
        fga = np.array(Image.open(PLATE / "fg.png").convert("RGBA"))[..., 3]
        rocks = rocks * (fga < 250)
    rl = np.dstack([rgb, rocks[..., None] * 255]).clip(0, 255).astype(np.uint8)[otop:]
    save_rgba(Image.fromarray(rl, "RGBA"), PLATE / "rocks_low.png")
    cfg["caustics"]["top"] = top
    cfg["caustics"]["occluderTop"] = otop
    return top, sand


def rocks_only(spec_path):
    """Rebuild rocks_low.png alone from the finished plate (bg.jpg)."""
    spec = json.loads(Path(spec_path).read_text())
    cfg = json.loads(SCENE.read_text())
    rgb = np.array(Image.open(PLATE / "bg.jpg").convert("RGB"))
    rocks_layer(rgb, spec, cfg)
    SCENE.write_text(json.dumps(cfg, indent=2) + "\n")


def build(src, spec_path):
    spec = json.loads(Path(spec_path).read_text())
    rgb = load_1080(src)
    cfg = json.loads(SCENE.read_text())
    WORK.mkdir(parents=True, exist_ok=True)

    Image.fromarray(rgb).save(PLATE / "bg.jpg", quality=88)

    top, sand = rocks_layer(rgb, spec, cfg)

    SCENE.write_text(json.dumps(cfg, indent=2) + "\n")
    chk = rgb.copy()
    chk[top:] = (chk[top:] * (0.5 + 0.5 * sand[top:, :, None]) + np.array([255, 0, 255]) * 0.5 * (1 - sand[top:, :, None])).astype(np.uint8)
    Image.fromarray(chk).resize((960, 540)).save(WORK / "plate_check.jpg")
    print("built plate layers; check gen/work/plate_check.jpg")


if __name__ == "__main__":
    if sys.argv[1] == "grid":
        grid(sys.argv[2], sys.argv[3])
    elif sys.argv[1] == "rocks":
        rocks_only(sys.argv[sys.argv.index("--spec") + 1])
    elif sys.argv[1] == "build":
        build(sys.argv[2], sys.argv[sys.argv.index("--spec") + 1])
