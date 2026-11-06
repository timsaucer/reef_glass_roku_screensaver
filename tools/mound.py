"""Usage: .venv/bin/python tools/mound.py <draft.png> <depth16.png> <name> [options]

Cuts a free-standing reef mound (a generated photo of one mound alone on open sand, see
gen/prompts/mound_*.txt) out of its draft for the wide tank, by depth: a pixel belongs to the
mound if it is nearer than the open water and sand at the same row, sampled at the frame's
left and right edges (where there is no mound). The sand in front of the mound is near too,
so below the back of the sand floor, sand-colored pixels (bright, unsaturated) are dropped.
Only the largest connected part is kept, and the alpha edge is snapped to the photo with a
guided filter.

Writes:
  roku/reefglass/images/<name>.png       the mound, cropped to its extent (palette PNG)
  roku/reefglass/images/<name>_far.png   the same at --far scale, for a distant copy
  gen/work/<name>_rgba.png               the mound at --scale, not palette-reduced: what
                                         tools/wideplate.py bakes into the background
  gen/work/<name>_check.jpg              the cut over magenta, for review
and prints the crop box and where the mound's base sits in it (for gen/wide_spec.json).

Options:
  --near 0.05   how much nearer than the edge reference a pixel must be
  --band 0.03   width of the soft transition
  --edge 0.12   fraction of the width at each side used as the reference
  --scale 1.0   scale the mound is stored (and drawn) at: store it at the size it is drawn,
                not larger, to keep the package small
  --far 0.5     scale of the distant copy (of the draft's size); 0 for none
  --region x0,y0,x1,y1  only this box can be mound (drops stray rocks at the frame edges)
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
WORK = ROOT / "gen/work"

ap = argparse.ArgumentParser()
ap.add_argument("draft")
ap.add_argument("depth")
ap.add_argument("name")
ap.add_argument("--near", type=float, default=0.05)
ap.add_argument("--band", type=float, default=0.03)
ap.add_argument("--edge", type=float, default=0.12)
ap.add_argument("--scale", type=float, default=1.0)
ap.add_argument("--far", type=float, default=0.5)
ap.add_argument("--region")
ap.add_argument("--crisp-below", type=int, help="below this draft row, sharpen the alpha edge (where the mound meets the sand: a soft edge there lets the draft's own sand blur into the tank's)")
ap.add_argument("--skirt", type=int, help="draft row near where the sand begins (the line is then found column by column): also write gen/work/<name>_skirt.png, the draft's own sand and contact shadows around the mound's base, feathered, for tools/wideplate.py to bake under it")
ap.add_argument("--sand-sat", type=float, default=0.3, help="saturation below which bright pixels count as sand (lit sand in blue water reaches ~0.35)")
ap.add_argument("--water-dist", type=float, help="drop pixels within this RGB distance of the row's open water (water seen between branches), e.g. 22")
ap.add_argument("--water-box", help="x0,y0,x1,y1: apply --water-dist only inside this box")
ap.add_argument("--key", type=float, help="also count as mound, near it and above the sand, pixels this far (RGB) from the row's open water, e.g. 35: recovers fine tips")
ap.add_argument("--fill-holes", type=int, help="fill holes enclosed by the mound up to this many px")
ap.add_argument("--fill-box", help="x0,y0,x1,y1: only holes inside this box are filled (sand under an arch is a hole too)")
ap.add_argument("--keep-box", action="append", help="x0,y0,x1,y1: never taken for sand here (pale coral lying over the sand); repeatable")
ap.add_argument("--close-box", action="append", help="x0,y0,x1,y1,r: close gaps up to r px in the outline within this box; repeatable")
ap.add_argument("--paint-box", action="append", help="x0,y0,x1,y1: paint over bright glass/sand pixels inside the mound here; repeatable")
ap.add_argument("--paint-dark-box", action="append", help="x0,y0,x1,y1: paint over deep-shadow pixels inside the mound here with mid-tone rock; repeatable")
ap.add_argument("--clear", action="append", help="x0,y0,x1,y1: never mound (e.g. a sliver of the draft's sand line); repeatable")
ap.add_argument("--floor", type=int, help="draft row of the back of the sand floor, if detection misses it")
ap.add_argument("--plate", choices=["left", "right"], help="the draft is a redraw of the one-screen plate's reef on this side (spec gen/wide_spec.json reefs.<side>.affine maps plate px to draft px): wherever the plate shows that reef, use the plate's own pixels and reef alpha (sharper, truer color), the redraw only past the plate's frame")
ap.add_argument("--sand", type=float, default=0.6, help="lightness above which unsaturated pixels below the floor count as sand")
a = ap.parse_args()

rgb = np.array(Image.open(a.draft).convert("RGB"))
d = np.array(Image.open(a.depth)).astype(np.float32) / 65535
gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255
h, w = d.shape


def guided(p, r=6, eps=2e-3):
    box = lambda x: cv2.boxFilter(x, -1, (2 * r + 1, 2 * r + 1))
    mi, mp = box(gray), box(p)
    a_ = (box(gray * p) - mi * mp) / (box(gray * gray) - mi * mi + eps)
    b_ = mp - a_ * mi
    return np.clip(box(a_) * gray + box(b_), 0, 1)


# Reference: open water and sand at each row, from the edge columns; the sand comes nearer
# toward the bottom, so the reference never decreases downward.
e = int(w * a.edge)
ref = np.median(np.concatenate([d[:, :e], d[:, w - e:]], axis=1), axis=1)
ref = np.maximum.accumulate(cv2.GaussianBlur(ref[:, None], (0, 0), 8)[:, 0])
alpha = np.clip((d - ref[:, None] - a.near) / a.band + 0.5, 0, 1)
# Sand: below the back of the floor (the sharpest brightening down the edge columns), bright
# and unsaturated.
lum = cv2.GaussianBlur(np.median(np.concatenate([gray[:, :e], gray[:, w - e:]], axis=1), axis=1)[:, None], (0, 0), 6)[:, 0]
floor = int(h * 0.45) + int(np.argmax(np.diff(lum)[int(h * 0.45):int(h * 0.95)]))
if a.floor is not None:
    floor = a.floor   # the sharpest brightening can miss (e.g. a draft whose sand line slopes)


def sand_mask(rgb):
    """Open sand: below the back of the floor, bright and unsaturated, and part of the open
    floor (regions reaching the frame's bottom or sides, or large ones seen through an arch;
    pale patches of rock inside the mound look the same but are enclosed)."""
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV).astype(np.float32) / 255
    sandy = np.clip((hsv[..., 2] - a.sand) / 0.08, 0, 1) * np.clip((a.sand_sat - hsv[..., 1]) / 0.1, 0, 1)
    # Sand in this water is white to cyan-blue; pale pink or purple (coral polyps lying over
    # the sand) is not, unless nearly grey.
    hue = hsv[..., 0] * 360
    tinted = (hue > 280) & (hue < 350) & (hsv[..., 1] > 0.12)
    sandy *= ~tinted
    sandy *= np.clip((np.arange(h)[:, None] - floor) / 20, 0, 1)
    for kb in a.keep_box or []:
        kx0, ky0, kx1, ky1 = (int(v) for v in kb.split(","))
        sandy[ky0:ky1, kx0:kx1] = 0
    n_, lab_, st_, _ = cv2.connectedComponentsWithStats((sandy > 0.3).astype(np.uint8))
    floorlab = np.zeros(n_, bool)
    for i in range(1, n_):
        x, y, ww, hh = st_[i, :4]
        floorlab[i] = (y + hh >= h - 2) or x <= 1 or x + ww >= w - 1 or st_[i, cv2.CC_STAT_AREA] > 0.003 * h * w
    sandy *= cv2.dilate(floorlab[lab_].astype(np.uint8), np.ones((5, 5), np.uint8))
    return cv2.GaussianBlur(sandy, (0, 0), 2)


alpha *= 1 - sand_mask(rgb)
print("floor at row", floor)
if a.region:
    x0, y0, x1, y1 = (int(v) for v in a.region.split(","))
    box = np.zeros_like(alpha)
    box[y0:y1, x0:x1] = 1
    alpha *= box
for box_ in a.clear or []:
    # Feathered, so clearing never leaves a straight cut through a soft edge.
    cx0, cy0, cx1, cy1 = (int(v) for v in box_.split(","))
    cl = np.zeros_like(alpha)
    cl[cy0:cy1, cx0:cx1] = 1
    alpha *= 1 - cv2.GaussianBlur(cl, (0, 0), 3)
if a.water_dist:
    wbox = np.zeros((h, w), np.float32)
    if a.water_box:
        bx0, by0, bx1, by1 = (int(v) for v in a.water_box.split(","))
        wbox[by0:by1, bx0:bx1] = 1
    else:
        wbox[:] = 1
    # Water seen between branches: pixels within this RGB distance of the open water at the
    # same row (the frame's edge columns), above the sand, are not mound.
    wrow = np.median(np.concatenate([rgb[:, :e], rgb[:, w - e:]], axis=1).astype(np.float32), axis=1)
    wrow = cv2.GaussianBlur(wrow[:, None, :], (0, 0), sigmaX=0.1, sigmaY=6)[:, 0, :]
    dist = np.linalg.norm(rgb.astype(np.float32) - wrow[:, None, :], axis=2)
    keep = np.clip((dist - a.water_dist) / 12, 0, 1)
    above_sand = np.clip((floor - 30 - np.arange(h)[:, None]) / 20, 0, 1)   # near the sand line it is glass, not water
    alpha *= 1 - (1 - keep) * above_sand * wbox
# Keep the largest connected part (the mound).
n, lab, stats, _ = cv2.connectedComponentsWithStats((alpha > 0.5).astype(np.uint8))
if n > 1:
    big = 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])
    keep = cv2.dilate((lab == big).astype(np.uint8), np.ones((15, 15), np.uint8))
    alpha *= keep
alpha = guided(alpha)
if a.crisp_below is not None:
    k = np.clip((np.arange(h)[:, None] - a.crisp_below) / 60, 0, 1)
    alpha = alpha * (1 - k) + np.clip((alpha - 0.35) / 0.3, 0, 1) * k
if a.plate:
    # The plate's own pixels and its hand-cut reef alpha (fg.png over rocks_low.png), warped
    # onto the draft, wherever the plate covers it; cross-faded over 80 px toward the plate's
    # frame edge, past which only the redraw exists.
    import json as _json
    spec_ = _json.loads((ROOT / "gen/wide_spec.json").read_text())
    M = np.array(spec_["reefs"][a.plate]["affine"], np.float32)
    plate = np.array(Image.open(IMAGES / "bg.jpg").convert("RGB"))
    fg = Image.open(IMAGES / "fg.png").convert("RGBA")
    layer = Image.new("RGBA", fg.size, (0, 0, 0, 0))
    layer.alpha_composite(Image.open(IMAGES / "rocks_low.png").convert("RGBA"), (0, 605))
    layer.alpha_composite(fg)
    pa = np.array(layer)[..., 3].astype(np.float32) / 255
    split = 820
    if a.plate == "left":
        pa[:, split:] = 0
    else:
        pa[:, :split] = 0
    nl, lab_p, st_p, _ = cv2.connectedComponentsWithStats(cv2.dilate((pa > 0.03).astype(np.uint8), np.ones((13, 13), np.uint8)))
    big_p = st_p[1:, cv2.CC_STAT_AREA].max()
    pa *= np.isin(lab_p, 1 + np.nonzero(st_p[1:, cv2.CC_STAT_AREA] >= 0.05 * big_p)[0])
    ph_, pw_ = pa.shape
    warp = lambda img_, interp: cv2.warpAffine(img_, M, (w, h), flags=interp, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    prgb = warp(plate.astype(np.float32), cv2.INTER_CUBIC)
    pal = warp(pa, cv2.INTER_LINEAR)
    inside = warp(np.ones((ph_, pw_), np.float32), cv2.INTER_LINEAR) > 0.999
    # Where to switch from the plate to the redraw: a seam through the band next to the plate's
    # frame edge, along the path where the two differ least (a cross-fade over the band showed
    # both where their details do not line up: a doubled look), feathered by only a few px.
    s = 1 if a.plate == "left" else -1          # the plate lies right (+) or left (-) of its edge
    xe_plate = 0.0 if a.plate == "left" else pw_ - 1.0
    ys_ = np.arange(h, dtype=np.float32)
    yp = (ys_ - M[1][2] - M[1][0] * xe_plate) / M[1][1]
    xe = M[0][0] * xe_plate + M[0][1] * yp + M[0][2]   # the frame edge in draft px, per row
    lo_, hi_ = 12, 140                            # band: this far inside the plate
    diff = np.abs(cv2.GaussianBlur(cv2.cvtColor(np.clip(prgb, 0, 255).astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32), (0, 0), 2)
                  - cv2.GaussianBlur(cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32), (0, 0), 2))
    nb = hi_ - lo_
    cost = np.full((h, nb), 1e6, np.float32)
    for y in range(h):
        xs_b = np.round(xe[y] + s * np.arange(lo_, hi_)).astype(int)
        okb = (xs_b >= 0) & (xs_b < w)
        cost[y, okb] = diff[y, xs_b[okb]]
    # Dynamic programming, one column of drift per row at most.
    acc = cost.copy()
    back = np.zeros((h, nb), np.int8)
    for y in range(1, h):
        prev = acc[y - 1]
        cand = np.stack([np.r_[1e9, prev[:-1]], prev, np.r_[prev[1:], 1e9]])
        k = np.argmin(cand, axis=0)
        acc[y] += cand[k, np.arange(nb)]
        back[y] = k - 1
    seam = np.zeros(h, int)
    seam[-1] = int(np.argmin(acc[-1]))
    for y in range(h - 1, 0, -1):
        seam[y - 1] = np.clip(seam[y] + back[y, seam[y]], 0, nb - 1)
    seam_x = xe + s * (lo_ + seam)
    xx = np.arange(w, dtype=np.float32)[None, :]
    wgt = np.clip((s * (xx - seam_x[:, None])) / 6.0 + 0.5, 0, 1) * inside
    wgt = cv2.GaussianBlur(wgt, (0, 0), 1.5)
    # The redraw alone (past the seam) is softer than the photo: sharpen it a little.
    soft = rgb.astype(np.float32)
    sharp = np.clip(soft + 0.7 * (soft - cv2.GaussianBlur(soft, (0, 0), 1.6)), 0, 255)
    rgb = np.clip(sharp * (1 - wgt[..., None]) + prgb * wgt[..., None], 0, 255).astype(np.uint8)
    # The plate's alpha, but only where the redraw also sees mound (grown 9 px): the plate's
    # hand-cut edges stay, its fringe of (shaded) sand around the base rocks goes.
    # (only near the base: higher up, the redraw's depth cut misses fine tips the plate's
    # alpha has, and capping it there clipped them).
    near_base = np.clip((np.arange(h)[:, None] - (floor - 40)) / 40, 0, 1)
    capped = np.minimum(pal, cv2.dilate(alpha, np.ones((19, 19), np.uint8)))
    alpha = alpha * (1 - wgt) + (pal * (1 - near_base) + capped * near_base) * wgt
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255
    # The plate's reef alpha takes in some of its sand around the base rocks: drop it again.
    alpha *= 1 - sand_mask(rgb)
    if a.crisp_below is not None:
        # Past the seam only: the plate's own soft edge meets its own sand in the skirt.
        k = np.clip((np.arange(h)[:, None] - a.crisp_below) / 60, 0, 1) * (1 - wgt)
        alpha = alpha * (1 - k) + np.clip((alpha - 0.35) / 0.3, 0, 1) * k
    # The redraw's outline keeps a dark rim of contact shadow where it meets the sand: trim
    # it by 2 px there (below the crisp row, past the seam).
    if a.crisp_below is not None:
        rim = (np.arange(h)[:, None] > a.crisp_below) & (wgt < 0.5)
        alpha = np.where(rim, np.minimum(alpha, cv2.erode(alpha, np.ones((5, 5), np.uint8))), alpha)
    print(f"plate pixels over {(wgt > 0.5).mean():.0%} of the draft")
if a.key:
    # Fine tips against plain water (the depth cut and the plate's frame-edge alpha cut them
    # roughly): near the mound and above the sand, anything clearly unlike the open water at
    # its row (the frame's edge columns) is mound.
    wrow_k = np.median(np.concatenate([rgb[:, :e], rgb[:, w - e:]], axis=1).astype(np.float32), axis=1)
    wrow_k = cv2.GaussianBlur(wrow_k[:, None, :], (0, 0), sigmaX=0.1, sigmaY=6)[:, 0, :]
    dk = np.linalg.norm(rgb.astype(np.float32) - wrow_k[:, None, :], axis=2)
    akey = np.clip((dk - a.key) / 20, 0, 1)
    near = cv2.dilate((alpha > 0.5).astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))).astype(np.float32)
    above = np.clip((floor - 20 - np.arange(h)[:, None]) / 20, 0, 1)
    alpha = np.maximum(alpha, akey * near * above)
alpha[alpha < 0.03] = 0
if a.fill_holes:
    # Small holes enclosed by the mound (glass glimpsed through a gap) filled: alpha 1, color
    # painted in from the coral around them.
    solid = (alpha > 0.5).astype(np.uint8)
    nh, labh, sth, _ = cv2.connectedComponentsWithStats(1 - solid, connectivity=4)
    holes = np.zeros((h, w), np.uint8)
    for i in range(1, nh):
        x_, y_, ww_, hh_, ar_ = sth[i]
        inbox = True
        if a.fill_box:
            fx0, fy0, fx1, fy1 = (int(v) for v in a.fill_box.split(","))
            inbox = x_ >= fx0 and y_ >= fy0 and x_ + ww_ <= fx1 and y_ + hh_ <= fy1
        if ar_ <= a.fill_holes and inbox and x_ > 0 and y_ > 0 and x_ + ww_ < w and y_ + hh_ < h:
            holes[labh == i] = 1
    if holes.any():
        holes = cv2.dilate(holes, np.ones((3, 3), np.uint8))
        rgb = cv2.inpaint(rgb, holes, 5, cv2.INPAINT_TELEA)
        alpha = np.maximum(alpha, holes.astype(np.float32))
        print(f"filled {int(holes.sum())} px of holes")
for cb in a.close_box or []:
    # Gaps open on one side (not holes) closed within this box: the mound's outline closed
    # morphologically, the new pixels painted in from the coral around them.
    *box_, rad = (int(v) for v in cb.split(","))
    bx0, by0, bx1, by1 = box_
    sub = (alpha[by0:by1, bx0:bx1] > 0.5).astype(np.uint8)
    closed = cv2.morphologyEx(sub, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * rad + 1, 2 * rad + 1)))
    new = ((closed > 0) & (sub == 0)).astype(np.uint8)
    if new.any():
        full = np.zeros((h, w), np.uint8)
        full[by0:by1, bx0:bx1] = cv2.dilate(new, np.ones((3, 3), np.uint8))
        rgb = cv2.inpaint(rgb, full, 5, cv2.INPAINT_TELEA)
        alpha[by0:by1, bx0:bx1] = np.maximum(alpha[by0:by1, bx0:bx1], closed.astype(np.float32))
        print(f"closed {int(new.sum())} px of gaps")
def paint_box(box, dark):
    """Pixels inside the mound here that do not belong are replaced by the nearest pixel that
    does, softened at the edge: light ones (glass, sand) by dark rock, or (dark) a deep
    shadow notch by mid-tone rock."""
    global rgb
    px0_, py0_, px1_, py1_ = (int(v) for v in box.split(","))
    hsv_p = cv2.cvtColor(rgb[py0_:py1_, px0_:px1_], cv2.COLOR_RGB2HSV).astype(np.float32) / 255
    inside = alpha[py0_:py1_, px0_:px1_] > 0.5
    if dark:
        bad = (hsv_p[..., 2] < 0.22) & inside
        good = (hsv_p[..., 2] > 0.3) & (hsv_p[..., 2] < 0.65) & inside
    else:
        bad = (hsv_p[..., 2] > 0.5) & inside
        good = (hsv_p[..., 2] < 0.42) & inside
    bm = cv2.dilate(bad.astype(np.uint8), np.ones((5, 5), np.uint8))
    srcm = (good & (bm == 0)).astype(np.uint8)
    if not bm.any() or not srcm.any():
        return
    sub_rgb = rgb[py0_:py1_, px0_:px1_].copy()
    _, lab_i = cv2.distanceTransformWithLabels(1 - srcm, cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
    src_y, src_x = np.nonzero(srcm)
    idx = np.zeros(lab_i.max() + 1, int)
    idx[lab_i[srcm == 1]] = np.arange(len(src_y))
    cloned = sub_rgb[src_y[idx[lab_i]], src_x[idx[lab_i]]]
    wgt_p = cv2.GaussianBlur(bm.astype(np.float32), (0, 0), 1.5)[..., None]
    rgb[py0_:py1_, px0_:px1_] = (sub_rgb * (1 - wgt_p) + cloned * wgt_p).astype(np.uint8)
    print(f"painted {int(bm.sum())} px")


for pb in a.paint_box or []:
    paint_box(pb, False)
for pb in a.paint_dark_box or []:
    paint_box(pb, True)
# A tighter edge (the depth cut and the guided filter leave a wide soft band, mostly
# background), then
# Edge colors decontaminated: a semi-transparent edge pixel still carries the draft's water
# or sand behind it (lighter than the tank's), a pale halo round every tip. Its own color is
# recovered against the local background (the draft blurred with the mound left out).
alpha = np.clip((alpha - 0.25) / 0.5, 0, 1)
alpha = alpha * alpha * (3 - 2 * alpha)
# Half a pixel off the outline: the edge pixels hold a sliver of the draft's (or plate's)
# lighter water, a faint light line against the tank's darker water. At the base, the same
# softens a hard, jagged cut against the sand.
alpha = 0.5 * (alpha + cv2.erode(alpha, np.ones((3, 3), np.uint8)))
if a.plate:
    # The plate's hand-cut alpha holds a little more of its water: half a pixel more there.
    alpha = np.where(wgt > 0.5, 0.5 * (alpha + cv2.erode(alpha, np.ones((3, 3), np.uint8))), alpha)
bgw = cv2.GaussianBlur((1 - alpha).astype(np.float32), (0, 0), 12)
bgc = cv2.GaussianBlur(rgb.astype(np.float32) * (1 - alpha)[..., None], (0, 0), 12) / np.maximum(bgw, 1e-3)[..., None]
# Above the sand only (at the base, the baked skirt is the draft's own sand), and not pushed
# from nearly transparent pixels (that overshoots into a dark line).
edge = (alpha > 0.1) & (alpha < 0.95) & (np.arange(h)[:, None] < floor)
fgc = (rgb.astype(np.float32) - (1 - alpha)[..., None] * bgc) / np.maximum(alpha, 0.5)[..., None]
# Capped: where the local background estimate is off (inside a mound, between dark rock), an
# uncapped correction turned edges and patches dark.
cap = np.where(wgt > 0.5, 45, 28)[..., None] if a.plate else 28
fgc = rgb.astype(np.float32) + np.clip(fgc - rgb.astype(np.float32), -cap, cap)
rgb = np.where(edge[..., None], np.clip(fgc, 0, 255), rgb.astype(np.float32)).astype(np.uint8)

ys, xs = np.nonzero(alpha > 0.03)
x0, y0, x1, y1 = xs.min(), ys.min(), xs.max() + 1, ys.max() + 1
rgba = np.dstack([rgb, (alpha * 255).astype(np.uint8)])[y0:y1, x0:x1]
im = Image.fromarray(rgba, "RGBA")
near = im if a.scale == 1 else im.resize((round(im.width * a.scale), round(im.height * a.scale)), Image.LANCZOS)
save_rgba(near, IMAGES / f"{a.name}.png")
WORK.mkdir(parents=True, exist_ok=True)
(WORK / f"{a.name}_cut.json").write_text(json.dumps({"crop": [int(x0), int(y0)], "scale": a.scale}) + "\n")
WORK.mkdir(parents=True, exist_ok=True)
near.save(WORK / f"{a.name}_rgba.png")
outs = [f"{a.name}.png"]
if a.far > 0:
    far = im.resize((round(im.width * a.far), round(im.height * a.far)), Image.LANCZOS)
    save_rgba(far, IMAGES / f"{a.name}_far.png")
    outs.append(f"{a.name}_far.png")

# Where the base meets the sand: the lowest row the solid mound reaches across its middle.
mid = alpha[:, (x0 + x1) // 2 - (x1 - x0) // 4:(x0 + x1) // 2 + (x1 - x0) // 4] > 0.5
base = int(np.nonzero(mid.any(axis=1))[0].max()) - y0
if a.skirt is not None:
    # The draft around the base: everything within ~25 px of the mound, but only sand: from
    # just below the draft's own sand line, found column by column where the sand is open and
    # carried across the mound (so the draft's line, at its own height, and its back glass
    # never show; the tank's line does), feathered out; baked under the mound, it meets the
    # draft's own sand and contact shadows.
    pad = 160
    lum2 = cv2.GaussianBlur(gray, (0, 0), sigmaX=4, sigmaY=2)
    wref = np.median(lum2[max(a.skirt - 250, 0):a.skirt - 120], axis=0)
    sref = np.median(lum2[min(a.skirt + 150, h - 60):h - 20], axis=0)
    lo = max(a.skirt - 120, 0)
    above = lum2[lo:h - 20] > (wref + 0.5 * (sref - wref))[None, :]
    line = lo + np.argmax(above, axis=0).astype(np.float32)
    open_col = (alpha[lo:h - 20] < 0.05).all(axis=0) & above.any(axis=0)
    xs_ = np.arange(w)
    line = np.interp(xs_, xs_[open_col], line[open_col]) if open_col.any() else np.full(w, float(a.skirt))
    line = cv2.GaussianBlur(line[None, :].astype(np.float32), (0, 0), 25)[0]
    m = cv2.dilate((alpha > 0.3).astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (51, 51))).astype(np.float32)
    m = cv2.GaussianBlur(m, (0, 0), 10)
    m *= np.clip((np.arange(h)[:, None] - (line[None, :] + 40)) / 30, 0, 1)
    m = np.maximum(m, alpha)
    sx0, sy0, sx1, sy1 = max(x0 - pad, 0), max(y0 - pad, 0), min(x1 + pad, w), min(y1 + pad, h)
    m[:, :sx0] = 0
    sk = Image.fromarray(np.dstack([rgb, (m * 255).astype(np.uint8)])[sy0:sy1, sx0:sx1], "RGBA")
    if a.scale != 1:
        sk = sk.resize((round(sk.width * a.scale), round(sk.height * a.scale)), Image.LANCZOS)
    sk.save(WORK / f"{a.name}_skirt.png")
    (WORK / f"{a.name}_skirt.json").write_text(f'{{"dx": {round((sx0 - x0) * a.scale)}, "dy": {round((sy0 - y0) * a.scale)}}}\n')
    print(f"  skirt: draft sand line {int(line.min())}..{int(line.max())}; offset {(sx0 - x0)},{(sy0 - y0)} px from the crop")
al = alpha[..., None]
chk = (rgb * al + np.array([255, 0, 255]) * (1 - al)).astype(np.uint8)
Image.fromarray(chk).resize((960, h * 960 // w)).save(WORK / f"{a.name}_check.jpg", quality=88)
print(f"{a.name}: crop {x0},{y0},{x1},{y1} size {x1 - x0}x{y1 - y0} base at {base} px from its top")
print(f"  stored at {a.scale}: {near.width}x{near.height}, base at {round(base * a.scale)}")
for f in outs:
    print(f, (IMAGES / f).stat().st_size // 1024, "KB")
