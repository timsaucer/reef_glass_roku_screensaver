"""Usage: .venv/bin/python tools/wideplate.py [gen/wide_spec.json]

Builds the wide tank's background, roku/reefglass/images/wide_bg0.jpg, wide_bg1.jpg (1920 px
tiles), and the moray's cave shade for it (cave_shade_wide.png).

- The empty tank: the one-screen plate (bg.jpg) with its reef edited out (FLUX.2 klein,
  gen/prompts/plate_empty_edit.txt), a few seeds side by side (spec "bgParts": each a draft,
  the tank columns x0..x1 it covers and the draft column it starts at; no stretching),
  cross-faded over "bgFade" px where a reef stands in front. The edit draws the sand line
  as a broad hump; each draft is flattened (a smooth vertical shift, only the hump's broad
  shape: the line keeps its own soft, uneven edge) onto row SAND, as in the plate, and its
  water and sand colors are matched, row by row, to the plate's open water and sand (the
  water then scaled by spec "waterGain", to taste a little darker).
- Every piece (gen/work/<name>_rgba.png, written by tools/mound.py) is baked in over its
  draft's own sand and contact shadows around its base (<name>_skirt.png, feathered into
  the tank's sand), as the plate has its reef in it: the pieces drawn over them at run time
  only hide fish behind the coral, and they meet their own sand, so no cut edge shows. Each piece's top is also mirrored, rippled, into
  the water surface, as the plate's left reef is.
- The cave shade: the plate's (tools/moray.py) alpha over the right reef's draft at the
  cave, the draft warped back onto the plate's frame (spec "reefs": photo-to-draft affine).

Writes gen/work/wideplate_check.jpg (the whole tank at half size).
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from imgio import save_rgba  # noqa: E402
from widelayout import resolve  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
IMAGES = ROOT / "roku/reefglass/images"
WORK = ROOT / "gen/work"
SAND = 749          # plate row where the sand meets the back glass
GAP = (765, 875)    # plate columns of open water and sand between its reefs
SHADE_BOX = (1380, 750)  # tools/moray.py: the cave shade's corner on the plate


def sand_line(img):
    lum = cv2.GaussianBlur(cv2.cvtColor(np.clip(img, 0, 255).astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32), (0, 0), sigmaX=8, sigmaY=3)
    water = np.median(lum[450:600], axis=0)
    sand = np.median(lum[900:1000], axis=0)
    return 600 + np.argmax(lum[600:950] > (water + 0.5 * (sand - water))[None, :], axis=0).astype(np.float32)


def flatten(img):
    """Moves the sand line's broad shape onto row SAND with a smooth vertical shift that fades
    away above and below it."""
    h, w = img.shape[:2]
    line = cv2.GaussianBlur(sand_line(img)[None, :], (0, 0), 300, borderType=cv2.BORDER_REFLECT)[0]
    shift = line - SAND                                   # source row = target row + shift
    y = np.arange(h, dtype=np.float32)[:, None]
    fall = np.exp(-((y - SAND) / 260.0) ** 2)
    my = (y + shift[None, :] * fall).astype(np.float32)
    mx = np.tile(np.arange(w, dtype=np.float32), (h, 1))
    return cv2.remap(img, mx, my, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)


WATER_GAIN = 1.0


def match_color(img, ref):
    """Each row's mean color shifted onto the plate gap's at that row, both smoothed over
    ~25 rows (separately above and below the sand line, blended across it): the water keeps
    the plate's darkening toward the top. (One mean for all the water left it ~15 levels
    lighter up high; a per-row match without smoothing printed the plate's own bands.)"""
    def rows(x):
        m = x.mean(axis=1)
        out = m.copy()
        out[:SAND] = cv2.GaussianBlur(m[:SAND][:, None, :], (0, 0), sigmaX=0.1, sigmaY=25, borderType=cv2.BORDER_REPLICATE)[:, 0, :]
        out[SAND:] = cv2.GaussianBlur(m[SAND:][:, None, :], (0, 0), sigmaX=0.1, sigmaY=25, borderType=cv2.BORDER_REPLICATE)[:, 0, :]
        return out
    # Broad side-to-side patches (the edit's pale reflections on the back glass) halved in
    # the water, so no stretch of it is much lighter than the plate's.
    low = cv2.GaussianBlur(img, (0, 0), sigmaX=150, sigmaY=25)
    water = np.clip((SAND - 20 - np.arange(img.shape[0])) / 40, 0, 1)[:, None, None]
    img = img - 0.5 * water * (low - low.mean(axis=1, keepdims=True))
    d = rows(ref) - rows(img)
    d = cv2.GaussianBlur(d[:, None, :], (0, 0), sigmaX=0.1, sigmaY=8)[:, 0, :]
    out = img + d[:, None, :]
    # A little darker than the plate's water (spec "waterGain"), the sand unchanged.
    return out * (1 - (1 - WATER_GAIN) * water)


CONTACT = 0.3   # darkest contact shadow under a piece's lower outline
GRAIN = 8   # px: sand texture finer than this comes from the plate


def plate_open_sand():
    """The plate's open sand: below the sand line, away from its reef (fg.png over
    rocks_low.png) by 15 px."""
    fg = Image.open(IMAGES / "fg.png").convert("RGBA")
    layer = Image.new("RGBA", fg.size, (0, 0, 0, 0))
    layer.alpha_composite(Image.open(IMAGES / "rocks_low.png").convert("RGBA"), (0, 605))
    layer.alpha_composite(fg)
    free = (np.array(layer)[..., 3] < 5).astype(np.uint8)
    free = cv2.erode(free, np.ones((31, 31), np.uint8)) > 0
    free[:SAND + 6] = False
    return free


def sand_grain(photo, W, rng):
    """Fine sand grain for the whole tank, quilted from the plate's open sand: blocks taken at
    the same rows (the grain's size follows the perspective), soft-overlapped."""
    h = photo.shape[0]
    hp = photo - cv2.GaussianBlur(photo, (0, 0), GRAIN)
    free = plate_open_sand()
    out = np.zeros((h, W, 3), np.float32)
    wsum = np.zeros((h, W, 1), np.float32)
    bh, bw, ov = 64, 160, 24
    win = np.minimum(np.minimum(np.arange(bw) + 1, bw - np.arange(bw)) / ov, 1)[None, :] * \
        np.minimum(np.minimum(np.arange(bh) + 1, bh - np.arange(bh)) / ov, 1)[:, None]
    for y0 in range(SAND + 6, h, bh - ov):
        y1 = min(y0 + bh, h)
        rows_free = free[y0:y1].all(axis=0)
        # Source columns where a whole block is free.
        ok = np.convolve(rows_free.astype(np.float32), np.ones(bw), "valid") >= bw - 0.5
        starts = np.nonzero(ok)[0]
        if len(starts) == 0:
            continue
        for x0 in range(0, W, bw - ov):
            x1 = min(x0 + bw, W)
            sx = int(rng.choice(starts))
            blk = hp[y0:y1, sx:sx + (x1 - x0)]
            if rng.random() < 0.5:
                blk = blk[:, ::-1]
            wv = win[:y1 - y0, :x1 - x0, None]
            out[y0:y1, x0:x1] += blk * wv
            wsum[y0:y1, x0:x1] += wv
    return out / np.maximum(wsum, 1e-6), wsum > 1e-6


def main():
    spec = resolve(json.loads((Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "gen/wide_spec.json").read_text()))
    W = spec["width"]
    global WATER_GAIN
    WATER_GAIN = spec.get("waterGain", 1.0)
    photo = np.array(Image.open(IMAGES / "bg.jpg").convert("RGB")).astype(np.float32)
    h = photo.shape[0]
    gap = photo[:, GAP[0]:GAP[1]]

    # Empty tank from the drafts.
    out = np.zeros((h, W, 3), np.float32)
    wsum = np.zeros((1, W, 1), np.float32)
    fade = spec.get("bgFade", 300)
    parts = spec["bgParts"]
    r = np.linspace(0, 1, fade, dtype=np.float32)
    r = r * r * (3 - 2 * r)
    for i, p in enumerate(parts):
        img = np.array(Image.open(ROOT / p["img"]).convert("RGB")).astype(np.float32)[:h]
        img = match_color(flatten(img), gap)
        x0, x1, s = p["x0"], p["x1"], p["src"]
        seg = img[:, s:s + (x1 - x0)]
        assert seg.shape[1] == x1 - x0, f"{p['img']}: needs columns {s}..{s + x1 - x0}"
        wgt = np.ones(x1 - x0, np.float32)
        if i > 0:
            wgt[:fade] = r
        if i < len(parts) - 1:
            wgt[-fade:] = np.minimum(wgt[-fade:], r[::-1])
        out[:, x0:x1] += seg * wgt[None, :, None]
        wsum[:, x0:x1] += wgt[None, :, None]
        print(f"{Path(p['img']).name}: tank {x0}..{x1}")
    out /= np.maximum(wsum, 1e-6)

    # Pieces: first the drafts' own sand and shadows around their bases; then the sand's fine
    # grain over everything (so those skirts get it too: a redraw's sand is softer); then the
    # pieces and their reflections.
    placed = []
    for p in spec["pieces"]:
        src = WORK / (Path(p["img"]).stem + "_rgba.png")
        if not src.exists():
            print("no", src.name, "- not baked")
            continue
        im = Image.open(src).convert("RGBA")
        sc = p.get("sc", 1.0)
        if sc != 1.0:
            im = im.resize((round(im.width * sc), round(im.height * sc)), Image.LANCZOS)
        if p.get("mir"):
            im = im.transpose(Image.FLIP_LEFT_RIGHT)
        a = np.array(im).astype(np.float32) / 255
        x0, y0 = p["x"], p["y"]
        ph, pw = a.shape[:2]
        al = a[..., 3]
        xs = np.nonzero(al.max(axis=0) > 0.5)[0]
        base = y0 + int(np.nonzero((al[:, xs.min():xs.max()] > 0.5).any(axis=1))[0].max())
        # The draft's own sand and contact shadows around the base (tools/mound.py --skirt).
        skf = WORK / (Path(p["img"]).stem + "_skirt.png")
        if skf.exists():
            sk = np.array(Image.open(skf).convert("RGBA")).astype(np.float32) / 255
            off = json.loads(skf.with_suffix(".json").read_text())
            sx, sy = x0 + off["dx"], y0 + off["dy"]
            sa, sb = max(sx, 0), min(sx + sk.shape[1], W)
            ta, tb = max(sy, 0), min(sy + sk.shape[0], h)
            ss = sk[ta - sy:tb - sy, sa - sx:sb - sx].copy()
            # Its sand matched to the tank's under it, per channel, from the skirt's fringe on
            # the sand, varying smoothly down the rows (a redraw's sand is often a little
            # lighter or hazier, which showed as a ring around the base).
            under = out[ta:tb, sa:sb] / 255
            # Only lit sand outside the piece: its rock edges and the real contact shadows are
            # darker, and measuring them brightened the sand near the base almost to white.
            pa_s = np.zeros(sk.shape[:2], np.float32)
            px0, py0 = -off["dx"], -off["dy"]
            pa_s[py0:py0 + ph, px0:px0 + pw] = al[:sk.shape[0] - py0, :sk.shape[1] - px0]
            pa_s = pa_s[ta - sy:tb - sy, sa - sx:sb - sx]
            lum_s = ss[..., :3].mean(axis=2)
            fr = ((ss[..., 3] > 0.15) & (pa_s < 0.03) & (lum_s > 0.62) & ((np.arange(ta, tb) > SAND + 10)[:, None])).astype(np.float32)
            num = ((under - ss[..., :3]) * fr[..., None]).sum(axis=1)
            den = fr.sum(axis=1)
            num = cv2.GaussianBlur(num[:, None, :], (0, 0), sigmaX=0.1, sigmaY=30)[:, 0, :]
            den = cv2.GaussianBlur(den[:, None], (0, 0), sigmaX=0.1, sigmaY=30)[:, 0]
            dlt = np.where(den[:, None] > 2, num / np.maximum(den, 1e-6)[:, None], 0)
            onsand = np.clip((np.arange(ta, tb) - SAND) / 20, 0, 1)[:, None]
            ss[..., :3] = np.clip(ss[..., :3] + (dlt * onsand)[:, None, :], 0, 1)
            out[ta:tb, sa:sb] = out[ta:tb, sa:sb] * (1 - ss[..., 3:]) + ss[..., :3] * 255 * ss[..., 3:]
        placed.append((p, a, x0, y0, ph, pw, base))

    # The sand's fine grain from the plate's own sand (the edit's and the redraws' are softer).
    grain, has = sand_grain(photo, W, np.random.default_rng(5))
    k = np.clip((np.arange(h) - (SAND + 6)) / 20, 0, 1)[:, None, None] * has
    out = out * (1 - k) + (cv2.GaussianBlur(out, (0, 0), GRAIN) + grain) * k

    # A soft contact shadow on the sand under each piece's lower outline (the skirts carry the
    # drafts' own; this deepens it where a part meets the sand, e.g. under the clam's lip).
    for p, a, x0, y0, ph, pw, base in placed:
        al = a[..., 3]
        solid = al > 0.5
        low = np.where(solid.any(axis=0), ph - 1 - np.argmax(solid[::-1], axis=0), -1)
        sh = np.zeros((h, W), np.float32)
        rows_t = np.arange(h, dtype=np.float32)
        for c in np.nonzero(low >= 0)[0]:
            tx = x0 + c
            if not 0 <= tx < W:
                continue
            by = y0 + low[c]
            if by < SAND + 25:
                continue
            d = rows_t - by
            sh[:, tx] = np.where(d < -4, 0, np.exp(-np.maximum(d, 0) / 12.0))
        sh = cv2.GaussianBlur(sh, (0, 0), sigmaX=7, sigmaY=3)
        out *= (1 - CONTACT * sh)[..., None]

    for p, a, x0, y0, ph, pw, base in placed:
        ya, yb = max(y0, 0), min(y0 + ph, h)
        xa, xb = max(x0, 0), min(x0 + pw, W)
        sub = a[ya - y0:yb - y0, xa - x0:xb - x0]
        out[ya:yb, xa:xb] = out[ya:yb, xa:xb] * (1 - sub[..., 3:]) + sub[..., :3] * 255 * sub[..., 3:]
        # Reflection: the top 40% mirrored, squashed to 30%, rippled, fading downward.
        top = a[:int(ph * 0.4)][::-1]
        rh = max(8, int(top.shape[0] * 0.3))
        refl = cv2.resize(top, (pw, rh), interpolation=cv2.INTER_AREA)
        rr = np.arange(rh, dtype=np.float32)[:, None]
        wob = (6 * np.sin(rr * 0.9) + 3 * np.sin(rr * 2.3 + 1.0)).astype(np.float32)
        rmx = (np.arange(pw, dtype=np.float32)[None, :] + wob).astype(np.float32)
        rmy = np.repeat(rr, pw, axis=1).astype(np.float32)
        refl = cv2.GaussianBlur(cv2.remap(refl, rmx, rmy, cv2.INTER_LINEAR), (0, 0), 0.7)
        ra = refl[..., 3:] * 0.8 * np.clip(1.3 - rr / rh, 0, 1)[..., None]
        out[:rh, xa:xb] = out[:rh, xa:xb] * (1 - ra[:, xa - x0:xb - x0]) + refl[:, xa - x0:xb - x0, :3] * 255 * ra[:, xa - x0:xb - x0]
        print(f"baked {p['img']} at {x0},{y0}, base row {base}")

    out = np.clip(out, 0, 255).astype(np.uint8)
    for kx in range((W + 1919) // 1920):
        tile = out[:, kx * 1920:(kx + 1) * 1920]
        f = IMAGES / f"wide_bg{kx}.jpg"
        Image.fromarray(tile).save(f, quality=88)
        print(f.name, f.stat().st_size // 1024, "KB")

    # Cave shade: the plate's shade alpha over the right reef's draft, warped back onto the
    # plate's frame (so the moray's plate coordinates carry over through the same transform).
    rf = spec["reefs"]["right"]
    M = np.array(rf["affine"], np.float32)
    draft = np.array(Image.open(ROOT / rf["draft"]).convert("RGB")).astype(np.float32)
    old = np.array(Image.open(IMAGES / "cave_shade.png").convert("RGBA")).astype(np.float32)
    plate_view = cv2.warpAffine(draft, cv2.invertAffineTransform(M), (photo.shape[1], h), flags=cv2.INTER_CUBIC)
    bx, by = SHADE_BOX
    crop = plate_view[by:by + old.shape[0], bx:bx + old.shape[1]]
    shade = np.dstack([crop, old[..., 3]]).clip(0, 255).astype(np.uint8)
    save_rgba(Image.fromarray(shade, "RGBA"), IMAGES / "cave_shade_wide.png")
    print("cave_shade_wide.png", (IMAGES / "cave_shade_wide.png").stat().st_size // 1024, "KB")

    WORK.mkdir(parents=True, exist_ok=True)
    Image.fromarray(out).resize((W // 2, h // 2), Image.LANCZOS).save(WORK / "wideplate_check.jpg", quality=88)


if __name__ == "__main__":
    main()
