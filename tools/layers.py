"""Usage: python tools/layers.py <plate> <depth16.png> <out_prefix> [options]

Splits a plate into parallax layers using its depth map:
  <out_prefix>_fg.png    RGBA near layer (depth - row ground depth >= near), alpha feathered
  <out_prefix>_bg.jpg    plate with the near layer filled, so small shifts show no holes
  <out_prefix>_land.png  with --land: RGBA of everything but open sky, so effects drawn over
                         the sky (aurora) can sit behind trees and buildings
  <out_prefix>_check.jpg fg (and land) over magenta, for review

Options:
  --near 0.15   how much nearer than the ground a pixel must be to count as foreground
  --band 0.05   width of the soft depth transition; smaller is a harder cut
  --matte       snap alpha edges to the plate with a guided filter (sharper, fewer half-alpha
                regions where depth is ambiguous)
  --grow 3      dilate the filled hole by this many px to hide edge fringes
  --region x0,y0,x1,y1  restrict the foreground to a box (soft-edged), e.g. just a branch
  --absolute    threshold raw depth (>= near); for an occluder that spans the central columns
                the row-ground reference is sampled from, like a branch across the top
"""
import argparse

import cv2
import numpy as np
from PIL import Image

ap = argparse.ArgumentParser()
ap.add_argument("plate")
ap.add_argument("depth")
ap.add_argument("out")
ap.add_argument("--near", type=float, default=0.15)
ap.add_argument("--band", type=float, default=0.05)
ap.add_argument("--matte", action="store_true")
ap.add_argument("--land", action="store_true")
ap.add_argument("--grow", type=int, default=3)
ap.add_argument("--absolute", action="store_true", help="threshold raw depth instead of depth above the row's ground")
ap.add_argument("--region", help="x0,y0,x1,y1 in plate px: only this box can be foreground")
a = ap.parse_args()

rgb = np.array(Image.open(a.plate).convert("RGB"))
d = np.array(Image.open(a.depth)).astype(np.float32) / 65535
gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255


def guided(p, r=6, eps=2e-3):
    # He et al. guided filter with the plate's luminance as guide: the output follows p in flat
    # regions but takes its edges from the image.
    box = lambda x: cv2.boxFilter(x, -1, (2 * r + 1, 2 * r + 1))
    mi, mp = box(gray), box(p)
    a_ = (box(gray * p) - mi * mp) / (box(gray * gray) - mi * mi + eps)
    b_ = mp - a_ * mi
    return np.clip(box(a_) * gray + box(b_), 0, 1)


def soft(x, edge):
    return np.clip((x - edge) / a.band + 0.5, 0, 1)


def check(alpha):
    al = alpha[..., None]
    return (rgb * al + np.array([255, 0, 255]) * (1 - al)).astype(np.uint8)


# Depth is relative, so compare each pixel with the open ground at the same row: the median
# depth across the central band, forced non-decreasing downward. Occluders (trunks, canopy)
# stand clearly nearer than the ground behind them; open meadow does not.
cx0, cx1 = int(d.shape[1] * 0.35), int(d.shape[1] * 0.65)
ground = np.maximum.accumulate(cv2.GaussianBlur(np.median(d[:, cx0:cx1], axis=1)[:, None], (0, 0), 8)[:, 0])
alpha = soft(d, a.near) if a.absolute else soft(d - ground[:, None], a.near)
if a.region:
    x0, y0, x1, y1 = (int(v) for v in a.region.split(","))
    box = np.zeros_like(alpha)
    box[y0:y1, x0:x1] = 1
    alpha *= cv2.GaussianBlur(box, (0, 0), 20)
alpha = guided(alpha) if a.matte else cv2.GaussianBlur(alpha, (0, 0), 1.2)
a8 = (alpha * 255).astype(np.uint8)
Image.fromarray(np.dstack([rgb, a8])).save(f"{a.out}_fg.png", optimize=True)

# Fill only under the solid core. Semi-transparent edges then sit over the original pixels
# they came from, so they match instead of showing as pale patches over the fill.
hole = (alpha > 0.5).astype(np.uint8) * 255
hole = cv2.dilate(hole, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * a.grow + 1,) * 2))
# Fill each hole pixel with the color of the nearest pixel outside the hole, then soften the
# fill. Only a thin ring of it is ever seen (as wide as the parallax shift), and nearest-color
# keeps sky next to sky and treeline next to treeline instead of smearing them together.
_, labels = cv2.distanceTransformWithLabels((hole == 0).astype(np.uint8) ^ 1, cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
ys, xs = np.nonzero(hole == 0)
lut = np.zeros((labels.max() + 1, 3), np.uint8)
lut[labels[ys, xs]] = rgb[ys, xs]
fill = cv2.GaussianBlur(lut[labels], (0, 0), 3)
bg = np.where(hole[..., None] > 0, fill, rgb)
Image.fromarray(bg).save(f"{a.out}_bg.jpg", quality=90)

chk = check(alpha)
if a.land:
    # Open sky is the farthest depth; everything else (treeline, cabin, ground) is land. The
    # land layer is cut from the filled background so it lines up with the bg it covers.
    sky_edge = np.percentile(d, 2) + 0.03
    land = guided(1 - soft(-d, -sky_edge)) if a.matte else 1 - soft(-d, -sky_edge)
    Image.fromarray(np.dstack([bg, (land * 255).astype(np.uint8)])).save(f"{a.out}_land.png", optimize=True)
    chk = np.concatenate([chk, check(land)], axis=0)
w = 960
Image.fromarray(chk).resize((w, chk.shape[0] * w // chk.shape[1])).save(f"{a.out}_check.jpg")
