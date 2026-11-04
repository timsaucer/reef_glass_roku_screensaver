"""Cut a generated animal out of its plain studio background and export Roku sprites.

Usage:
  .venv/bin/python tools/cutout.py <draft.png> <name> --width <px> [--fish] [--flip]
        [--crop x0,y0,x1,y1] [--squash 0.5] [--key 22,48]

The drafts are generated on a plain bright green background (gen/prompts/*.txt). The key is
the color distance (CIE Lab) from the background, estimated from the image border, with a
soft ramp between the two --key thresholds. Only the largest connected subject is kept, and
green spill is removed from its edges.

--width   final sprite width in px: the size of the animal when nearest the glass (z = 1)
--fish    split into <name>_body.png and <name>_tail.png at the caudal peduncle (the narrowest
          column in the rear part of the fish), and write the tail pivot and length into
          roku/reefglass/scenes/reef.json (species <name>, or burrow.goby for the goby)
--flip    mirror first (sprites must face right)
--squash  scale height by this factor (a starfish seen at a low angle on the sand)
Writes gen/work/<name>_check.png (the cut over magenta) for review.
"""
import argparse
import json
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

ap = argparse.ArgumentParser()
ap.add_argument("src")
ap.add_argument("name")
ap.add_argument("--width", type=int, required=True)
ap.add_argument("--fish", action="store_true")
ap.add_argument("--flip", action="store_true")
ap.add_argument("--crop")
ap.add_argument("--squash", type=float, default=1.0)
ap.add_argument("--key", default="14,32")
ap.add_argument("--rear", default="0.08,0.42", help="fraction of the length (from the tail end) searched for the peduncle")
a = ap.parse_args()

rgb = np.array(Image.open(a.src).convert("RGB"))
if a.crop:
    x0, y0, x1, y1 = (int(v) for v in a.crop.split(","))
    rgb = rgb[y0:y1, x0:x1]
if a.flip:
    rgb = rgb[:, ::-1].copy()

lab = cv2.cvtColor(rgb.astype(np.float32) / 255, cv2.COLOR_RGB2LAB)  # true CIE Lab
border = np.concatenate([lab[:8].reshape(-1, 3), lab[-8:].reshape(-1, 3), lab[:, :8].reshape(-1, 3), lab[:, -8:].reshape(-1, 3)])
bgc = np.median(border, axis=0)
dist = np.linalg.norm(lab - bgc, axis=2)
k0, k1 = (float(v) for v in a.key.split(","))
alpha = np.clip((dist - k0) / (k1 - k0), 0, 1)

# Keep the largest subject; fill pinholes inside it.
solid = (alpha > 0.5).astype(np.uint8)
n, lbl, stats, _ = cv2.connectedComponentsWithStats(solid, 8)
if n > 1:
    big = 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])
    keep = cv2.dilate((lbl == big).astype(np.uint8), np.ones((9, 9), np.uint8))
    alpha *= keep
inside = cv2.morphologyEx((alpha > 0.5).astype(np.uint8), cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
alpha = np.maximum(alpha, inside.astype(np.float32) * (cv2.erode(inside, np.ones((5, 5), np.uint8)) > 0))

# Despill: green may not exceed the larger of red and blue (none of the animals are green).
# Where a pixel was green because the background showed through (translucent fins), it also
# loses alpha in proportion, so the fin stays see-through over the reef.
f = rgb.astype(np.float32)
bgrgb = np.median(np.concatenate([rgb[:8].reshape(-1, 3), rgb[-8:].reshape(-1, 3)]), axis=0).astype(np.float32)
cap = np.maximum(f[..., 0], f[..., 2])
spill = np.clip((f[..., 1] - cap) / max(1.0, bgrgb[1] - max(bgrgb[0], bgrgb[2])), 0, 1)
f[..., 1] = np.minimum(f[..., 1], cap + 4)
alpha = alpha * (1 - 0.75 * spill)
rgba = np.dstack([f, alpha * 255]).clip(0, 255).astype(np.uint8)

ys, xs = np.nonzero(alpha > 0.05)
pad = 4
y0, y1 = max(ys.min() - pad, 0), min(ys.max() + pad + 1, rgba.shape[0])
x0, x1 = max(xs.min() - pad, 0), min(xs.max() + pad + 1, rgba.shape[1])
rgba = rgba[y0:y1, x0:x1]

# Downscale in premultiplied alpha so edges don't pick up dark or green fringes.
im = Image.fromarray(rgba, "RGBA").convert("RGBa")
w = a.width
h = max(1, round(rgba.shape[0] * w / rgba.shape[1] * a.squash))
im = im.resize((w, h), Image.LANCZOS).convert("RGBA")
WORK.mkdir(parents=True, exist_ok=True)


def check(img, path):
    bg = Image.new("RGBA", img.size, (255, 0, 255, 255))
    Image.alpha_composite(bg, img).save(path)


if not a.fish:
    save_rgba(im, IMAGES / f"{a.name}.png")
    check(im, WORK / f"{a.name}_check.png")
    print(f"{a.name}.png {w}x{h}")
    sys.exit()

# Tail split: the caudal peduncle is the narrowest point of the rear part of the body.
arr = np.array(im)
al = arr[..., 3].astype(np.float32) / 255
heights = cv2.GaussianBlur((al > 0.5).sum(axis=0).astype(np.float32)[None, :], (0, 0), 1.5)[0]
r0, r1 = (float(v) for v in a.rear.split(","))
lo, hi = int(w * r0), int(w * r1)
c = lo + int(np.argmin(heights[lo:hi]))
rows = np.nonzero(al[:, c] > 0.5)[0]
py = int((rows.min() + rows.max()) / 2) if len(rows) else h // 2
ov = max(2, w // 60)  # the tail runs a little under the body so no gap opens as it beats
tail = im.crop((0, 0, c + ov, h))
body = im.crop((c, 0, w, h))
# Trim the tail sprite vertically to its content, keeping the pivot row.
ta = np.array(tail)[..., 3]
tr = np.nonzero(ta.max(axis=1) > 10)[0]
t0, t1 = int(tr.min()), int(tr.max()) + 1
# Center the tail sprite on the pivot row so its right-edge middle is the hinge.
half = max(py - t0, t1 - py)
tail_c = Image.new("RGBA", (tail.width, 2 * half), (0, 0, 0, 0))
tail_c.paste(tail, (0, half - py))
save_rgba(body, IMAGES / f"{a.name}_body.png")
save_rgba(tail_c, IMAGES / f"{a.name}_tail.png")

chk = im.copy()
d = np.array(chk)
d[:, c] = (0, 255, 255, 255)
d[py, max(c - 6, 0):c + 7] = (255, 255, 255, 255)
check(Image.fromarray(d), WORK / f"{a.name}_check.png")

cfg = json.loads(SCENE.read_text())
pivot = [ov, py]
if a.name == "goby":
    cfg["burrow"]["goby"] = {"pivot": pivot}
else:
    cfg["species"][a.name]["pivot"] = pivot
    cfg["species"][a.name]["len"] = body.width
SCENE.write_text(json.dumps(cfg, indent=2) + "\n")
print(f"{a.name}: body {body.width}x{h}, tail {tail_c.width}x{tail_c.height}, pivot {pivot}, peduncle col {c} of {w}")
