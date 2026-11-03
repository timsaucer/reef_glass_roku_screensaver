"""Shared image output helpers."""
import imagequant
from PIL import Image


def save_rgba(im: Image.Image, path, colors=256):
    """Saves an RGBA sprite as a palette PNG with alpha (libimagequant): ~3x smaller than RGBA
    and visually the same; the sideload limit (~3 MB package) makes this matter."""
    im = im.convert("RGBA")
    imagequant.quantize_pil_image(im, dithering_level=1.0, max_colors=colors).save(path, optimize=True)
