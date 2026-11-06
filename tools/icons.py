"""Usage: .venv/bin/python tools/icons.py <frame.jpg> [--zoom 1.25] [--at x,y]

Writes the app icons (roku/reefglass/images/icon_{fhd,hd,sd}.jpg) and the store poster
(store/poster-540x405.jpg) from a full 1920x1080 frame (a device screenshot, so fish are in
it), with the title set in Georgia (a macOS system font, rendered into the image).

--zoom  how far in from the frame filling the image (1.25: the default crop)
--at    the frame px of the crop's center (default: around the anemone, left of center)
"""
import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
ap = argparse.ArgumentParser()
ap.add_argument("frame")
ap.add_argument("--zoom", type=float, default=1.25)
ap.add_argument("--at")
a = ap.parse_args()
src = Image.open(a.frame).convert("RGB")
font = "/System/Library/Fonts/Supplemental/Georgia.ttf"
TITLE = "Reef Glass"
out = {
    ROOT / "roku/reefglass/images/icon_fhd.jpg": (540, 405),
    ROOT / "roku/reefglass/images/icon_hd.jpg": (290, 218),
    ROOT / "roku/reefglass/images/icon_sd.jpg": (246, 140),
    ROOT / "store/poster-540x405.jpg": (540, 405),
}
for path, (w, h) in out.items():
    # Cover-crop around the anemone and the open water beside it.
    s = max(w / src.width, h / src.height) * a.zoom
    im = src.resize((int(src.width * s), int(src.height * s)), Image.LANCZOS)
    if a.at:
        cx, cy = (float(v) * s for v in a.at.split(","))
        x = int(min(max(cx - w / 2, 0), im.width - w))
        y = int(min(max(cy - h / 2, 0), im.height - h))
    else:
        x, y = int((im.width - w) * 0.22), int((im.height - h) * 0.55)
    im = im.crop((x, y, x + w, y + h))
    f = ImageFont.truetype(font, int(h * 0.17))
    d = ImageDraw.Draw(im)
    tw = d.textlength(TITLE, font=f)
    tx, ty = (w - tw) / 2, h * 0.07
    # A dark glow behind the title (it sits over coral, not open water) and a tight shadow.
    glow = Image.new("L", im.size, 0)
    ImageDraw.Draw(glow).text((tx, ty), TITLE, font=f, fill=255, stroke_width=max(2, int(h * 0.012)), stroke_fill=255)
    im.paste((0, 18, 36), mask=glow.filter(ImageFilter.GaussianBlur(h * 0.02)).point(lambda v: int(v * 0.75)))
    shadow = Image.new("L", im.size, 0)
    ImageDraw.Draw(shadow).text((tx, ty + 2), TITLE, font=f, fill=230)
    im.paste((0, 20, 40), mask=shadow.filter(ImageFilter.GaussianBlur(2)))
    ImageDraw.Draw(im).text((tx, ty), TITLE, font=f, fill=(240, 248, 250))
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path, quality=90)
print("icons and poster written")
