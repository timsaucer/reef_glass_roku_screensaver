"""Usage: .venv/bin/python tools/placeholders.py

Draws simple placeholder art for every sprite and plate layer into roku/reefglass/images, so
the animation code can be built and tuned on the device before any photoreal art exists.
Each file here has the same name, size and anchor conventions the final art must follow
(see roku/reefglass/scenes/reef.json), so final art drops in without code changes.

Fish: <name>_body.png faces right; the tail is a separate <name>_tail.png whose right edge
attaches at the body's tail pivot (reef.json "pivot", in body pixels).
"""
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
from caustics import caustic_band  # noqa: E402
from imgio import save_rgba  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "roku/reefglass/images"
rng = np.random.default_rng(7)
W, H = 1920, 1080
SAND_TOP = 800
CAUSTIC_TOP = 780


def noise(w, h, scale, octaves=4):
    """Smooth value noise in 0..1."""
    acc = np.zeros((h, w))
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        s = max(2, int(scale / 2**o))
        g = rng.random((h // s + 2, w // s + 2))
        im = Image.fromarray((g * 255).astype(np.uint8)).resize(((w // s + 2) * s, (h // s + 2) * s), Image.BICUBIC)
        acc += amp * np.asarray(im, dtype=float)[:h, :w] / 255
        tot += amp
        amp *= 0.5
    return acc / tot


def blob(d, cx, cy, rx, ry, fill, n=18, jitter=0.25):
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        r = 1 + jitter * (rng.random() - 0.5) * 2
        pts.append((cx + rx * r * math.cos(a), cy + ry * r * math.sin(a)))
    d.polygon(pts, fill=fill)


def plate():
    y = np.linspace(0, 1, H)[:, None]
    top, bot = np.array([40, 120, 170]), np.array([8, 40, 80])
    arr = np.zeros((H, W, 3))
    for c in range(3):
        arr[:, :, c] = top[c] * (1 - y) + bot[c] * y
    # Far reef wall: dark bluish band with noise.
    n = noise(W, H, 160)
    wall = (np.arange(H)[:, None] > 420 + 120 * n[400:401, :]) & (np.arange(H)[:, None] < SAND_TOP + 20)
    arr[wall] = arr[wall] * 0.55 + np.array([20, 50, 70]) * 0.45 * (0.7 + 0.6 * n[wall])[:, None]
    # Sand floor.
    sy = np.clip((np.arange(H) - SAND_TOP) / (H - SAND_TOP), 0, 1)[:, None]
    sand = np.array([150, 160, 150]) * (1 - sy) + np.array([215, 205, 175]) * sy
    sm = (np.arange(H)[:, None] >= SAND_TOP + 40 * (n[700:701, :] - 0.5)) & np.ones((1, W), bool)
    grain = noise(W, H, 6, 2)
    for c in range(3):
        arr[:, :, c] = np.where(sm, sand[:, c:c + 1] * (0.85 + 0.3 * grain), arr[:, :, c])
    im = Image.fromarray(arr.clip(0, 255).astype(np.uint8))
    # Rocks and coral go on their own layer: composited into the plate, and their lower part is
    # also shipped as rocks_low.png, drawn over the caustics so the light lands on sand only.
    rocks = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(rocks)
    # Rock masses left and right, with coral heads.
    for cx, cy, rx, ry in [(250, 760, 380, 230), (520, 820, 260, 120), (1700, 700, 380, 300), (1450, 800, 220, 120)]:
        blob(d, cx, cy, rx, ry, (70, 72, 78))
    for cx, cy, r, col in [(150, 560, 90, (190, 90, 140)), (380, 610, 70, (120, 170, 90)), (1560, 470, 110, (150, 110, 190)),
                           (1780, 420, 80, (220, 130, 90)), (1350, 690, 60, (90, 170, 170)), (620, 720, 50, (210, 170, 80))]:
        blob(d, cx, cy, r, r * 0.75, col, jitter=0.4)
    rocks = rocks.filter(ImageFilter.GaussianBlur(1.2))
    im = Image.alpha_composite(im.convert("RGBA"), rocks).convert("RGB")
    save_rgba(rocks.crop((0, CAUSTIC_TOP, W, H)), OUT / "rocks_low.png")
    # Burrow mouth on the open sand.
    ImageDraw.Draw(im).ellipse((1150, 918, 1215, 940), fill=(40, 34, 30))
    im = im.filter(ImageFilter.GaussianBlur(1.2))
    im.save(OUT / "bg.jpg", quality=88)

    fg = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(fg)
    blob(d, 60, 1060, 330, 170, (55, 52, 58, 255))
    blob(d, 1900, 1040, 300, 190, (60, 56, 62, 255))
    blob(d, 130, 900, 80, 60, (230, 120, 70, 255), jitter=0.5)
    blob(d, 1820, 860, 90, 70, (170, 80, 160, 255), jitter=0.5)
    save_rgba(fg.filter(ImageFilter.GaussianBlur(1.0)), OUT / "fg.png")


def fish(name, bw, bh, col, tw, tcol, stripes=(), split=None, eye=True, shape=0.5):
    """Body faces right. shape: 0 slim .. 1 tall disc."""
    s = 2  # supersample
    im = Image.new("RGBA", (bw * s, bh * s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cy = bh * s / 2
    # Dorsal and anal fins.
    d.polygon([(bw * s * 0.25, cy), (bw * s * 0.45, cy - bh * s * 0.5), (bw * s * 0.8, cy)], fill=col)
    d.polygon([(bw * s * 0.3, cy), (bw * s * 0.5, cy + bh * s * 0.48), (bw * s * 0.75, cy)], fill=col)
    ry = bh * s * (0.22 + 0.2 * shape)
    d.ellipse((0, cy - ry, bw * s, cy + ry), fill=col)
    if split:
        x = bw * s * split[0]
        mask = Image.new("L", im.size, 0)
        ImageDraw.Draw(mask).rectangle((0, 0, x, im.size[1]), fill=255)
        alpha = im.getchannel("A")
        tint = Image.new("RGBA", im.size, split[1])
        tint.putalpha(Image.composite(alpha, Image.new("L", im.size, 0), mask))
        im = Image.alpha_composite(im, tint)
        d = ImageDraw.Draw(im)
    alpha = im.getchannel("A")
    for x0, x1, c in stripes:
        band = Image.new("RGBA", im.size, (0, 0, 0, 0))
        ImageDraw.Draw(band).rectangle((bw * s * x0, 0, bw * s * x1, bh * s), fill=c)
        band.putalpha(Image.composite(alpha, Image.new("L", im.size, 0), band.getchannel("A")))
        im = Image.alpha_composite(im, band)
        d = ImageDraw.Draw(im)
    if eye:
        ex, ey, er = bw * s * 0.82, cy - ry * 0.25, max(3, bh * s * 0.06)
        d.ellipse((ex - er, ey - er, ex + er, ey + er), fill=(15, 15, 20, 255))
    im = im.resize((bw, bh), Image.LANCZOS)
    save_rgba(im, OUT / f"{name}_body.png")
    th = int(bh * 0.7)
    t = Image.new("RGBA", (tw * s, th * s), (0, 0, 0, 0))
    ImageDraw.Draw(t).polygon([(tw * s, th * s / 2 - th * s * 0.12), (0, 0), (tw * s * 0.3, th * s / 2), (0, th * s),
                               (tw * s, th * s / 2 + th * s * 0.12)], fill=tcol)
    save_rgba(t.resize((tw, th), Image.LANCZOS), OUT / f"{name}_tail.png")


def fishes():
    fish("clown", 110, 64, (240, 110, 20, 255), 34, (240, 110, 20, 255),
         stripes=[(0.18, 0.24, (255, 255, 255, 255)), (0.48, 0.56, (255, 255, 255, 255)), (0.74, 0.8, (255, 255, 255, 255))])
    fish("bluetang", 170, 110, (30, 70, 200, 255), 50, (250, 210, 30, 255),
         stripes=[(0.25, 0.7, (20, 25, 50, 255))], shape=0.8)
    fish("yellowtang", 150, 130, (250, 220, 30, 255), 40, (250, 220, 30, 255), shape=1.0)
    fish("gramma", 70, 36, (150, 40, 190, 255), 22, (250, 200, 30, 255), split=(0.45, (250, 200, 30, 255)), shape=0.2)
    fish("damsel", 60, 40, (40, 120, 255, 255), 20, (40, 120, 255, 255), shape=0.6)
    fish("flame", 90, 64, (240, 60, 20, 255), 28, (240, 60, 20, 255),
         stripes=[(0.4, 0.44, (30, 10, 10, 255)), (0.55, 0.59, (30, 10, 10, 255)), (0.7, 0.74, (30, 10, 10, 255))], shape=0.7)
    fish("goby", 84, 30, (250, 215, 40, 255), 22, (250, 215, 40, 255), shape=0.0)


def shrimp():
    s = 2
    w, h = 70, 34
    im = Image.new("RGBA", (w * s, h * s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse((6 * s, 8 * s, 52 * s, 28 * s), fill=(235, 140, 60, 255))
    for x in (16, 26, 36):
        d.rectangle((x * s, 8 * s, (x + 4) * s, 28 * s), fill=(250, 240, 230, 255))
    d.ellipse((46 * s, 4 * s, 70 * s, 22 * s), fill=(240, 90, 40, 255))  # big claw, facing right
    d.line((50 * s, 14 * s, 68 * s, 2 * s), fill=(240, 200, 180, 255), width=s)
    save_rgba(im.resize((w, h), Image.LANCZOS), OUT / "shrimp.png")


def lip():
    """Front rim of the burrow mouth, drawn over the goby and shrimp so they sink into it."""
    w, h = 110, 30
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(im).ellipse((0, 4, w, h + 18), fill=(190, 180, 155, 255))
    save_rgba(im.filter(ImageFilter.GaussianBlur(1.5)), OUT / "lip.png")


def anemone(frames=6):
    w, h = 220, 150
    for f in range(frames):
        s = 2
        im = Image.new("RGBA", (w * s, h * s), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        ph = 2 * math.pi * f / frames
        for i in range(46):
            bx = (20 + (w - 40) * i / 45) * s
            by = (h - 12) * s
            ang = -math.pi / 2 + (i / 45 - 0.5) * 1.6
            length = (70 + 30 * math.sin(i * 1.7)) * s
            pts = []
            for k in range(12):
                u = k / 11
                sway = 0.35 * math.sin(ph + i * 0.4 + u * 2.0) * u
                a = ang + sway
                pts.append((bx + math.cos(a) * length * u, by + math.sin(a) * length * u))
            d.line(pts, fill=(200, 210, 120, 255), width=7 * s, joint="curve")
            px, py = pts[-1]
            d.ellipse((px - 5 * s, py - 5 * s, px + 5 * s, py + 5 * s), fill=(235, 120, 180, 255))
        d.ellipse((10 * s, (h - 26) * s, (w - 10) * s, h * s), fill=(150, 90, 70, 255))
        save_rgba(im.resize((w, h), Image.LANCZOS), OUT / f"anemone_{f}.png")


def duster():
    s = 2
    w, h = 90, 70
    im = Image.new("RGBA", (w * s, h * s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for i in range(24):
        a = math.pi + math.pi * i / 23
        x1, y1 = w * s / 2 + math.cos(a) * 44 * s, h * s + math.sin(a) * 66 * s
        d.line((w * s / 2, h * s, x1, y1), fill=(230, 200, 220, 230) if i % 2 else (160, 60, 120, 230), width=3 * s)
    save_rgba(im.resize((w, h), Image.LANCZOS), OUT / "duster_crown.png")
    tube = Image.new("RGBA", (16, 80), (0, 0, 0, 0))
    ImageDraw.Draw(tube).rounded_rectangle((0, 0, 15, 79), 6, fill=(120, 100, 80, 255))
    save_rgba(tube, OUT / "duster_tube.png")


def clam():
    s = 2
    w, h = 150, 80
    im = Image.new("RGBA", (w * s, h * s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse((0, 10 * s, w * s, h * s), fill=(200, 195, 175, 255))
    d.ellipse((10 * s, 4 * s, (w - 10) * s, 40 * s), fill=(30, 90, 140, 255))
    save_rgba(im.resize((w, h), Image.LANCZOS), OUT / "clam.png")
    sh = Image.new("RGBA", (w * s, h * s), (0, 0, 0, 0))
    d = ImageDraw.Draw(sh)
    for _ in range(40):
        x, y = rng.uniform(16, w - 16) * s, rng.uniform(8, 36) * s
        r = rng.uniform(2, 5) * s
        d.ellipse((x - r, y - r, x + r, y + r), fill=(80, 230, 220, 255))
    save_rgba(sh.resize((w, h), Image.LANCZOS).filter(ImageFilter.GaussianBlur(1)), OUT / "clam_shimmer.png")


def starfish():
    s = 2
    r = 40
    im = Image.new("RGBA", (2 * r * s, 2 * r * s), (0, 0, 0, 0))
    pts = []
    for i in range(10):
        a = -math.pi / 2 + math.pi * i / 5
        rr = (r if i % 2 == 0 else r * 0.4) * s
        pts.append((r * s + rr * math.cos(a), r * s + rr * math.sin(a)))
    ImageDraw.Draw(im).polygon(pts, fill=(230, 120, 60, 255))
    # Seen at a low angle on the sand: squash vertically.
    save_rgba(im.resize((2 * r, r), Image.LANCZOS), OUT / "starfish.png")


def soft(name, size, inner=0.0):
    yy, xx = np.mgrid[0:size, 0:size]
    r = np.hypot(xx - (size - 1) / 2, yy - (size - 1) / 2) / (size / 2)
    a = np.clip(1 - (r - inner) / (1 - inner), 0, 1) ** 2
    arr = np.zeros((size, size, 4), np.uint8)
    arr[..., :3] = 255
    arr[..., 3] = (a * 255).astype(np.uint8)
    save_rgba(Image.fromarray(arr), OUT / name)


def ray():
    w, h = 160, 900
    x = np.linspace(-1, 1, w)[None, :]
    y = np.linspace(0, 1, h)[:, None]
    a = np.clip(1 - np.abs(x) / (0.4 + 0.6 * y), 0, 1) ** 1.5 * (1 - y) ** 1.3
    arr = np.zeros((h, w, 4), np.uint8)
    arr[..., :3] = (230, 245, 255)
    arr[..., 3] = (a * 255).astype(np.uint8)
    save_rgba(Image.fromarray(arr), OUT / "ray.png")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    plate()
    fishes()
    shrimp()
    lip()
    anemone()
    duster()
    clam()
    starfish()
    soft("mote.png", 8)
    soft("puff.png", 24)
    ray()
    for i in range(2):
        save_rgba(caustic_band(1024, 300, seed=11 + i, cells=26 + 6 * i), OUT / f"caustic_{i}.png")
    print("placeholders written to", OUT)
