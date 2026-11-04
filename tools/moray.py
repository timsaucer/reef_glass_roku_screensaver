"""Build the moray eel sprites and the cave shade.

Usage:
  .venv/bin/python tools/cutout.py gen/drafts/zit_moray_s1.png moray_full --crop 150,120,600,576 --width 450
  .venv/bin/python tools/moray.py [--width 210] [--tilt 24]

Reads images/moray_full.png (the keyed eel, head facing left, body running off the draft's
right and bottom edges) and writes:
  moray.png       the eel without its lower jaw, tilted so the body runs back level into the
                  cave, darkening toward the cut-off end; a dark mouth lining fills the gape
  moray_jaw.png   the lower jaw alone, rotated about its hinge to gape
  cave_shade.png  the plate's cave: its rock and its dark interior, with alpha rising from the
                  mouth toward the back, drawn over the eel so its body fades into the dark
and the moray block of scenes/reef.json (jaw hinge and offset, shade position). moray_full.png
is removed afterward.

Coordinates below are hand traced: JAW on the 450 px wide keyed draft, CAVE on the 1080p plate.
"""
import argparse
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
SCENE = ROOT / "roku/reefglass/scenes/reef.json"
WORK = ROOT / "gen/work"

# Lower jaw: below the mouth line from the tip back to the gape corner, then down round the
# chin and back along the underside.
JAW = [(0, 114), (60, 140), (120, 162), (176, 184), (196, 200), (186, 236), (140, 222), (80, 196), (30, 168), (0, 150)]
HINGE = (184, 192)
EXTEND = 170  # px of body added past the draft's right edge
MOUTH = [(0, 114), (60, 140), (120, 162), (176, 184)]  # the jaw's top edge, for the lining
# Cave opening under the right-hand rock (1080p plate px); everything outside it is rock.
# The right-hand side of the opening follows the plate's own dark interior, so the rock wall the
# eel slides out from behind has its real edge.
CAVE = [(1402, 876), (1404, 806), (1428, 782), (1470, 772), (1530, 771), (1566, 778), (1604, 790), (1606, 876)]
SHADE_BOX = (1380, 750, 1660, 900)
WALL = (1555, 26)  # right of this x, only pixels darker than this luminance are cave interior


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--width", type=int, default=210)
    ap.add_argument("--tilt", type=float, default=24.0, help="degrees counterclockwise, to level the body")
    a = ap.parse_args()

    full = np.array(Image.open(IMAGES / "moray_full.png").convert("RGBA")).astype(np.float32)
    # The draft cuts the body off at its right edge: continue it (mirrored) so it runs on
    # behind the cave wall instead of ending in view.
    full = np.pad(full, ((0, 0), (0, EXTEND), (0, 0)), mode="symmetric")
    h, w = full.shape[:2]
    jm = np.zeros((h, w), np.float32)
    cv2.fillPoly(jm, [np.array(JAW, np.int32)], 1.0)
    jm = cv2.GaussianBlur(jm, (0, 0), 0.8)
    # Mouth lining: a dark band just under the mouth line, inside the jaw, revealed as it opens.
    lining = np.zeros((h, w), np.float32)
    cv2.polylines(lining, [np.array(MOUTH, np.int32)], False, 1.0, 22)
    lining = np.clip(lining * (jm > 0.5), 0, 1)

    jaw = full.copy()
    jaw[..., 3] *= jm
    body = full.copy()
    body[..., 3] *= (1 - jm)
    dark = np.array([38, 18, 24], np.float32)
    body[..., :3] = body[..., :3] * (1 - lining[..., None]) + dark * lining[..., None]
    body[..., 3] = np.maximum(body[..., 3], 255 * lining * (full[..., 3] / 255))

    # Pad, then tilt both pieces the same way about the image center, tracking the hinge.
    pad = 60
    def prep(img):
        img = np.pad(img, ((pad, pad), (pad, pad), (0, 0)))
        im = Image.fromarray(img.clip(0, 255).astype(np.uint8), "RGBA").convert("RGBa")
        return im.rotate(a.tilt, resample=Image.BICUBIC, expand=False)
    bim, jim = prep(body), prep(jaw)
    cx, cy = (w + 2 * pad) / 2, (h + 2 * pad) / 2
    t = math.radians(a.tilt)
    hx, hy = HINGE[0] + pad - cx, HINGE[1] + pad - cy
    # PIL rotates counterclockwise on screen (y down): x' = x cos + y sin, y' = -x sin + y cos.
    hx, hy = cx + hx * math.cos(t) + hy * math.sin(t), cy - hx * math.sin(t) + hy * math.cos(t)

    # Darken toward the body's cut-off end (right side) so it melts into the cave.
    def to_np(im):
        return np.array(im.convert("RGBA")).astype(np.float32)
    B, J = to_np(bim), to_np(jim)
    ys, xs = np.nonzero(B[..., 3] + J[..., 3] > 8)
    x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    ramp = np.clip((np.arange(B.shape[1]) - (x0 + 0.45 * (x1 - x0))) / (0.45 * (x1 - x0)), 0, 1)[None, :, None]
    for arr in (B, J):
        arr[..., :3] *= 1 - 0.85 * ramp
    B, J = B[y0:y1, x0:x1], J[y0:y1, x0:x1]
    hx, hy = hx - x0, hy - y0

    k = a.width / B.shape[1]
    size = (a.width, round(B.shape[0] * k))
    def out(arr):
        im = Image.fromarray(arr.clip(0, 255).astype(np.uint8), "RGBA").convert("RGBa")
        return im.resize(size, Image.LANCZOS).convert("RGBA")
    bo, jo = out(B), out(J)
    hx, hy = hx * k, hy * k
    # Jaw sprite: crop to its content; record where it sits in the body sprite.
    ja = np.array(jo)[..., 3]
    jy, jx = np.nonzero(ja > 4)
    jx0, jy0 = int(jx.min()), int(jy.min())
    jo = jo.crop((jx0, jy0, int(jx.max()) + 1, int(jy.max()) + 1))
    save_rgba(bo, IMAGES / "moray.png")
    save_rgba(jo, IMAGES / "moray_jaw.png")

    # Cave shade from the plate.
    bg = np.array(Image.open(IMAGES / "bg.jpg").convert("RGB")).astype(np.float32)
    sx0, sy0, sx1, sy1 = SHADE_BOX
    crop = bg[sy0:sy1, sx0:sx1]
    inside = np.zeros((1080, 1920), np.float32)
    cv2.fillPoly(inside, [np.array(CAVE, np.int32)], 1.0)
    inside = inside[sy0:sy1, sx0:sx1]
    lum = cv2.GaussianBlur(crop.mean(axis=2), (0, 0), 1.5)
    xx = np.arange(sx0, sx1, dtype=np.float32)[None, :].repeat(crop.shape[0], 0)
    dark = np.clip((WALL[1] + 10 - lum) / 20, 0, 1)
    inside = inside * np.where(xx > WALL[0], dark, 1.0)
    inside = cv2.morphologyEx(inside, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    inside = cv2.GaussianBlur(inside, (0, 0), 1.0)
    alpha = 1 - inside
    shade = np.dstack([crop, alpha * 255]).clip(0, 255).astype(np.uint8)
    save_rgba(Image.fromarray(shade, "RGBA"), IMAGES / "cave_shade.png")

    cfg = json.loads(SCENE.read_text())
    m = cfg.get("moray", {})
    m.update({
        "jaw": [jx0, jy0], "jawHinge": [round(hx, 1), round(hy, 1)],
        "shade": [sx0, sy0],
    })
    m.setdefault("x", 1440)
    m.setdefault("y", 830)
    m.setdefault("reach", 160)
    m.setdefault("threat", 260)
    m.setdefault("gape", 9)
    cfg["moray"] = m
    SCENE.write_text(json.dumps(cfg, indent=2) + "\n")

    # Check image: the eel in place, jaw open, over the plate.
    chk = Image.open(IMAGES / "bg.jpg").convert("RGBA").crop((1300, 700, 1700, 950))
    ox, oy = m["x"] - 1300, m["y"] - bo.height // 2 - 700
    jr = jo.rotate(m["gape"], resample=Image.BICUBIC, center=(hx - jx0, hy - jy0))
    chk.alpha_composite(jr, (ox + jx0, oy + jy0))
    chk.alpha_composite(bo, (ox, oy))
    chk.alpha_composite(Image.open(IMAGES / "cave_shade.png").convert("RGBA"), (sx0 - 1300, sy0 - 700))
    chk.convert("RGB").resize((800, 500)).save(WORK / "moray_check.jpg")
    (IMAGES / "moray_full.png").unlink()
    print(f"moray {bo.size}, jaw {jo.size} at {jx0},{jy0}, hinge {hx:.1f},{hy:.1f}")


if __name__ == "__main__":
    main()
