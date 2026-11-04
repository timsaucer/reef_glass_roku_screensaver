"""Reconstruct a fish as a 3D mesh from its side photo with TripoSR (MIT, runs locally).

Usage (TripoSR's own env, see README "Fish views"):
  ext/venv/bin/python tools/fish3d.py <keyed_rgba.png> <out.ply> [--res 256] [--device mps]

The input is the keyed fish on transparency (tools/cutout.py output before any split). It is
composited on mid gray, framed square as TripoSR expects, and the mesh is written with vertex
colors.
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import torch
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "ext/TripoSR"))
from tsr.system import TSR  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("src")
ap.add_argument("out")
ap.add_argument("--res", type=int, default=256)
ap.add_argument("--device", default="mps")
ap.add_argument("--fill", type=float, default=0.85, help="fraction of the square the fish spans")
a = ap.parse_args()

im = Image.open(a.src).convert("RGBA")
w, h = im.size
side = int(max(w, h) / a.fill)
sq = Image.new("RGBA", (side, side), (0, 0, 0, 0))
sq.paste(im, ((side - w) // 2, (side - h) // 2))
arr = np.array(sq).astype(np.float32) / 255
rgb = arr[..., :3] * arr[..., 3:] + 0.5 * (1 - arr[..., 3:])
img = Image.fromarray((rgb * 255).astype(np.uint8)).resize((512, 512), Image.LANCZOS)
img.save(Path(a.out).with_suffix(".input.png"))

model = TSR.from_pretrained("stabilityai/TripoSR", config_name="config.yaml", weight_name="model.ckpt")
model.renderer.set_chunk_size(8192)
model.to(a.device)
with torch.no_grad():
    codes = model([img], device=a.device)
    meshes = model.extract_mesh(codes, True, resolution=a.res)
meshes[0].export(a.out)
print("wrote", a.out, len(meshes[0].vertices), "verts")
