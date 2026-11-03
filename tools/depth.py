"""Usage: python tools/depth.py <image> <out.png>

Writes a 16-bit relative depth map (bright = near) with Depth Anything V2 Small (Apache 2.0).
"""
import sys

import numpy as np
import torch
from PIL import Image
from transformers import pipeline

src, dst = sys.argv[1], sys.argv[2]
device = "mps" if torch.backends.mps.is_available() else "cpu"
pipe = pipeline("depth-estimation", model="depth-anything/Depth-Anything-V2-Small-hf", device=device)
img = Image.open(src).convert("RGB")
d = pipe(img)["predicted_depth"].squeeze().float().cpu().numpy()
d = np.array(Image.fromarray(d).resize(img.size, Image.BICUBIC))
d = (d - d.min()) / (d.max() - d.min())
Image.fromarray((d * 65535).astype(np.uint16)).save(dst)
