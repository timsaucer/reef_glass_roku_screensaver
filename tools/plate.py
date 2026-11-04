"""Turn a generated reef plate into the tank's plate layers and plate-derived sprites.

Usage:
  .venv/bin/python tools/plate.py grid <plate.png> <out.jpg>
      1080p copy with a labeled 100 px grid, for reading coordinates and tracing outlines

  .venv/bin/python tools/plate.py build <plate.png> --spec gen/plate_spec.json
      writes roku/reefglass/images/{bg.jpg, rocks_low.png, lip.png, anemone_<n>.png,
      clam.png, clam_shimmer.png} and positions into scenes/reef.json; check images go to
      gen/work/. fg.png comes from tools/layers.py (depth), run separately.

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
    "burrow": [x, y],                   optional: dig a burrow into the sand here
    "anemone": [[x, y], ...],           polygon around the anemone (tentacles and foot)
    "anemoneCenter": [x, y],            the oral disc; sway grows from here to the tips
    "clam": [[x, y], ...]               optional: polygon around the clam's mantle, for a shimmer
  }

The anemone and clam stay in the plate. The anemone's sway frames are the plate's own
anemone pixels, warped sideways more toward the tentacle tips; drawn over the plate they make
it sway in place. The clam shimmer is the mantle's own fine highlights, lifted into an alpha
sprite that pulses over it.
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
SCENE = ROOT / "roku/reefglass/scenes/reef.json"
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


def dig_burrow(rgb, x, y):
    """Darkens a soft elliptical hole into the sand and returns the lip sprite: the sand just
    in front of the hole, cut from the plate, so the goby and shrimp can sink behind it."""
    out = rgb.astype(np.float32)
    yy, xx = np.mgrid[0:1080, 0:1920]
    rx, ry = 34, 11
    d = ((xx - x) / rx) ** 2 + ((yy - y) / ry) ** 2
    hole = np.clip(1.25 - d, 0, 1) ** 0.7
    shade = 1 - 0.82 * hole
    out *= shade[..., None]
    # A faint ring of disturbed sand around the mouth.
    ring = np.exp(-((np.sqrt(d) - 1.35) ** 2) / 0.08) * (yy > y - 4)
    out = out * (1 - 0.12 * ring[..., None]) + 255 * 0.06 * ring[..., None]
    out = out.clip(0, 255).astype(np.uint8)
    # Lip: the plate's sand across the front half of the hole, alpha fading upward.
    lw, lh = 2 * rx + 40, 28
    lx0, ly0 = x - lw // 2, y - 6
    crop = rgb[ly0:ly0 + lh, lx0:lx0 + lw].astype(np.float32)
    ly, lx = np.mgrid[0:lh, 0:lw]
    ex = (lx - lw / 2) / (rx + 14)
    top = 6 + 10 * ex ** 2  # the rim curves up toward its ends
    a = np.clip((ly - top) / 5 + 0.5, 0, 1) * np.clip((1 - np.abs(ex)) * 3, 0, 1)
    lip = np.dstack([crop, a * 255]).clip(0, 255).astype(np.uint8)
    return out, Image.fromarray(lip, "RGBA"), (lx0, ly0)


def anemone_frames(rgb, pts, center, n=6, amp=7.0):
    mask = poly_mask(pts, 1.5)
    x0, y0, w, h = cv2.boundingRect(np.array(pts, np.int32))
    pad = int(amp) + 4
    x0, y0, w, h = x0 - pad, y0 - pad, w + 2 * pad, h + pad
    crop = rgb[y0:y0 + h, x0:x0 + w].astype(np.float32)
    m = mask[y0:y0 + h, x0:x0 + w]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    # Seen face-on the tentacles radiate from the oral disc: sway grows from 0 at the disc's
    # center to full at the tentacle tips.
    cx, cy = center[0] - x0, center[1] - y0
    rmax = max(w, h) / 2
    reach = np.clip(np.hypot(xx - cx, yy - cy) / rmax, 0, 1) ** 1.3
    frames = []
    for i in range(n):
        ph = 2 * math.pi * i / n
        # A slow traveling wave across the crown, plus a gentle shared lean.
        dx = amp * reach * (0.6 * np.sin(ph + xx / 55.0) + 0.4 * np.sin(ph))
        dy = 0.25 * amp * reach * np.sin(ph + 1.3 + xx / 70.0)
        mx, my = (xx - dx).astype(np.float32), (yy - dy).astype(np.float32)
        warped = cv2.remap(crop, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        wm = cv2.remap(m, mx, my, cv2.INTER_LINEAR, borderValue=0)
        frames.append(Image.fromarray(np.dstack([warped, wm * 255]).clip(0, 255).astype(np.uint8), "RGBA"))
    return frames, (x0, y0, w, h)


def clam_shimmer(rgb, pts):
    mask = poly_mask(pts, 1.0)
    x0, y0, w, h = cv2.boundingRect(np.array(pts, np.int32))
    crop = rgb[y0:y0 + h, x0:x0 + w].astype(np.float32) / 255
    m = mask[y0:y0 + h, x0:x0 + w]
    lum = crop.mean(axis=2)
    hi = np.clip((lum - cv2.GaussianBlur(lum, (0, 0), 4)) * 6, 0, 1)  # fine bright spots
    hi = cv2.GaussianBlur(hi, (0, 0), 0.8) * m
    # Tint the shimmer with the mantle's own color, lifted toward white.
    col = np.clip(crop * 0.5 + 0.6, 0, 1)
    spr = np.dstack([col * 255, hi * 255]).clip(0, 255).astype(np.uint8)
    return Image.fromarray(spr, "RGBA"), (x0, y0, w, h)


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
    if (IMAGES / "fg.png").exists():
        fga = np.array(Image.open(IMAGES / "fg.png").convert("RGBA"))[..., 3]
        rocks = rocks * (fga < 250)
    rl = np.dstack([rgb, rocks[..., None] * 255]).clip(0, 255).astype(np.uint8)[otop:]
    save_rgba(Image.fromarray(rl, "RGBA"), IMAGES / "rocks_low.png")
    cfg["caustics"]["top"] = top
    cfg["caustics"]["occluderTop"] = otop
    return top, sand


def rocks_only(spec_path):
    """Rebuild rocks_low.png alone from the finished plate (bg.jpg)."""
    spec = json.loads(Path(spec_path).read_text())
    cfg = json.loads(SCENE.read_text())
    rgb = np.array(Image.open(IMAGES / "bg.jpg").convert("RGB"))
    rocks_layer(rgb, spec, cfg)
    SCENE.write_text(json.dumps(cfg, indent=2) + "\n")


def build(src, spec_path):
    spec = json.loads(Path(spec_path).read_text())
    rgb = load_1080(src)
    cfg = json.loads(SCENE.read_text())
    WORK.mkdir(parents=True, exist_ok=True)

    # Anemone frames and clam shimmer come from the clean plate (before the burrow is dug).
    if "anemone" in spec:
        frames, (ax, ay, aw, ah) = anemone_frames(rgb, spec["anemone"], spec["anemoneCenter"], cfg["anemone"].get("frames", 6), spec.get("anemoneAmp", 7.0))
        for i, f in enumerate(frames):
            save_rgba(f, IMAGES / f"anemone_{i}.png")
        cfg["anemone"].update({"x": ax + aw // 2, "y": ay + ah})
    if "clam" in spec:
        sh, (cx, cy, cw, chh) = clam_shimmer(rgb, spec["clam"])
        save_rgba(sh, IMAGES / "clam_shimmer.png")
        cfg["clam"] = {"x": cx + cw // 2, "y": cy + chh, "inPlate": True}

    if "burrow" in spec:
        bx, by = spec["burrow"]
        rgb, lip, _ = dig_burrow(rgb, bx, by)
        save_rgba(lip, IMAGES / "lip.png")
        cfg["burrow"].update({"x": bx, "y": by})
    Image.fromarray(rgb).save(IMAGES / "bg.jpg", quality=88)

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
