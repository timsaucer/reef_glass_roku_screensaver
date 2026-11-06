"""Usage: .venv/bin/python tools/widebg.py <draft_a.png> <draft_b.png> [--width 3840]
                                      [--overlap 480] [--flatten 0.8]

Builds the wide tank's empty-tank background from two generated drafts (gen/prompts/
tank_empty.txt), as tiles of 1920 px: roku/reefglass/images/wide_bg0.jpg, wide_bg1.jpg, ...

0. Light patterns baked into the sand (the model draws caustics whatever the prompt says;
   the screensaver animates its own) are removed: thin bright lines are taken out of the
   sand's lightness with a morphological top-hat (--decaustic kernel px, 0 to skip).
1. The back of the sand floor (the first row halfway from the water's brightness to the sand's) is moved to y = 740,
   as in the one-screen plate, by remapping each draft's rows above and below it.
2. Landmarks are flattened: the broad brightness and color variations across the width are
   pulled toward each row's mean (--flatten), so no patch of glare or shade stands out.
3. Each row is matched to the open water and sand of the one-screen plate (bg.jpg, between
   its reefs), so the reef pieces cut from it, and their soft edges, sit right on it.
4. The two drafts are cross-faded over --overlap px and the result stretched to --width
   (featureless water and sand stretch invisibly).
Writes gen/work/widebg_check.jpg (the whole strip at half size).
"""
import argparse
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
IMAGES = ROOT / "roku/reefglass/images"
WORK = ROOT / "gen/work"
FLOOR = 740
GAP = (750, 890)  # bg.jpg columns of open water and sand between its two reefs

ap = argparse.ArgumentParser()
ap.add_argument("a")
ap.add_argument("b")
ap.add_argument("--width", type=int, default=3840)
ap.add_argument("--overlap", type=int, default=480)
ap.add_argument("--flatten", type=float, default=0.8)
ap.add_argument("--decaustic", type=int, default=15)
ap.add_argument("--strip", help="write the whole strip here instead of the tiles (texture for tools/wideplate.py)")
ap.add_argument("--floor", type=int, nargs=2, help="floor rows of the two drafts, if detection fails")
a = ap.parse_args()


def floor_row(img):
    lum = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY).astype(np.float32)
    prof = cv2.GaussianBlur(np.median(lum, axis=1)[:, None], (0, 0), 6)[:, 0]
    # The first row, going down, halfway from the water's brightness to the sand's.
    n = len(prof)
    water, sand = np.median(prof[int(n * 0.15):int(n * 0.3)]), np.median(prof[int(n * 0.85):])
    return int(np.argmax(prof > water + 0.5 * (sand - water)))


def decaustic(img, y, k):
    lab = cv2.cvtColor(img, cv2.COLOR_RGB2LAB).astype(np.float32)
    L = lab[..., 0]
    op = cv2.morphologyEx(L, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
    op = cv2.GaussianBlur(op, (0, 0), k / 4)
    sand = np.clip((np.arange(L.shape[0])[:, None] - (y - 20)) / 60, 0, 1)
    lab[..., 0] = L - 0.9 * np.clip(L - op, 0, None) * sand
    return cv2.cvtColor(np.clip(lab, 0, 255).astype(np.uint8), cv2.COLOR_LAB2RGB)


def remap(img, y):
    h = img.shape[0]
    rows = np.concatenate([np.linspace(0, y, FLOOR, endpoint=False), np.linspace(y, h - 1, 1080 - FLOOR)])
    mx = np.tile(np.arange(img.shape[1], dtype=np.float32), (1080, 1))
    my = np.tile(rows.astype(np.float32)[:, None], (1, img.shape[1]))
    return cv2.remap(img, mx, my, cv2.INTER_CUBIC)


def flatten(img, k):
    f = img.astype(np.float32)
    low = cv2.GaussianBlur(f, (0, 0), sigmaX=180, sigmaY=25)
    return f - k * (low - low.mean(axis=1, keepdims=True))


def match_rows(f, target, k=0.7):
    # Shift each row's mean most of the way onto the target's. Both are smoothed over many
    # rows: a broad color correction, not the old plate's own bands (its distant rock).
    cur = cv2.GaussianBlur(f.mean(axis=1)[:, None, :], (0, 0), 25)[:, 0, :]
    return f + k * (target - cur)[:, None, :]


old = np.array(Image.open(IMAGES / "bg.jpg").convert("RGB")).astype(np.float32)
target = cv2.GaussianBlur(np.median(old[:, GAP[0]:GAP[1]], axis=1)[:, None, :], (0, 0), 25)[:, 0, :]

parts = []
for i, path in enumerate((a.a, a.b)):
    img = np.array(Image.open(path).convert("RGB"))
    y = a.floor[i] if a.floor else floor_row(img)
    print(f"{Path(path).name}: floor at row {y}")
    if a.decaustic:
        img = decaustic(img, y, a.decaustic)
    parts.append(match_rows(flatten(remap(img, y), a.flatten), target))

o = a.overlap
A, B = parts
w = A.shape[1] + B.shape[1] - o
out = np.zeros((1080, w, 3), np.float32)
out[:, :A.shape[1]] = A
t = np.linspace(0, 1, o)
t = t * t * (3 - 2 * t)
out[:, A.shape[1] - o:A.shape[1]] = A[:, -o:] * (1 - t)[None, :, None] + B[:, :o] * t[None, :, None]
out[:, A.shape[1]:] = B[:, o:]
out = cv2.resize(out, (a.width, 1080), interpolation=cv2.INTER_CUBIC)
out = np.clip(out, 0, 255).astype(np.uint8)
if a.strip:
    Image.fromarray(out).save(a.strip)
    print("wrote", a.strip)
    raise SystemExit
n = (a.width + 1919) // 1920
for k in range(n):
    tile = out[:, k * 1920:(k + 1) * 1920]
    p = IMAGES / f"wide_bg{k}.jpg"
    Image.fromarray(tile).save(p, quality=85)
    print(p.name, tile.shape[1], "px", p.stat().st_size // 1024, "KB")
WORK.mkdir(parents=True, exist_ok=True)
Image.fromarray(out).resize((a.width // 2, 540)).save(WORK / "widebg_check.jpg", quality=88)
