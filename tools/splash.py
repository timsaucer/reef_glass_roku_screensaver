"""Usage: .venv/bin/python tools/splash.py

Writes the splash screens (roku/reefglass/images/splash_{fhd,hd,sd}.jpg, 1920x1080,
1280x720 and 720x480): opaque, the tank's dark blue (the manifest's splash_color) with the
title in Georgia, as on the icons. Roku's certification asks for FHD and HD splash images
listed in the manifest; a flat image keeps them a few KB each (the package limit is 4 MB).
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONT = "/System/Library/Fonts/Supplemental/Georgia.ttf"
TITLE = "Reef Glass"
BG = (0x06, 0x18, 0x2A)   # splash_color in the manifest

for name, (w, h) in {"fhd": (1920, 1080), "hd": (1280, 720), "sd": (720, 480)}.items():
    im = Image.new("RGB", (w, h), BG)
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype(FONT, int(h * 0.09))
    tw = d.textlength(TITLE, font=f)
    d.text(((w - tw) / 2, h * 0.44), TITLE, font=f, fill=(225, 238, 244))
    out = ROOT / f"roku/reefglass/images/splash_{name}.jpg"
    im.save(out, quality=90, optimize=True)
    print(out.name, out.stat().st_size // 1024, "KB")
