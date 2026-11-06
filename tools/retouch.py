"""Usage: .venv/bin/python tools/retouch.py <name>

Retouches a cut piece by hand-written PhotoCraft steps, after tools/mound.py and before
tools/wideplate.py: gen/retouch/<name>.json holds "commands", a list of [command id, params]
for photocraft-cli (e.g. clone a patch of coral to a layer, flip it, shift its color, merge it
down, to cover a blurred spot without an obvious copy). One extra step, "patch" {src, box,
feather, center}: a piece of another image (best an unused draft, so nothing in the tank is
seen twice), cut out with feathered edges and placed as a new layer centred there; the steps
after it act on that layer. They run on gen/work/<name>_rgba.png;
the result replaces it and roku/reefglass/images/<name>.png (palette).

PhotoCraft: ~/.local/bin/photocraft-cli (`photocraft-cli commands` lists the commands).
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from imgio import save_rgba  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PC = Path.home() / ".local/bin/photocraft-cli"

name = sys.argv[1]
spec_ = json.loads((ROOT / "gen/retouch" / f"{name}.json").read_text())
steps = spec_["commands"]
# "coords": "draft": positions are in the draft's px (they stay put when a recut moves the
# piece's crop); they are moved into the piece by its crop corner (gen/work/<name>_cut.json).
cx0 = cy0 = 0
if spec_.get("coords") == "draft":
    cx0, cy0 = json.loads((ROOT / "gen/work" / f"{name}_cut.json").read_text())["crop"]
src = ROOT / "gen/work" / f"{name}_rgba.png"
with tempfile.TemporaryDirectory() as td:
    out = Path(td) / "out.png"
    args = [str(PC), "run", str(src)]
    for k, (cmd, params) in enumerate(steps):
        if cmd == "patch":
            import numpy as np
            from scipy import ndimage
            x0, y0, x1, y1 = params["box"]
            crop = Image.open(ROOT / params["src"]).convert("RGB").crop((x0, y0, x1, y1))
            f = params.get("feather", 10)
            m = np.zeros((y1 - y0, x1 - x0), np.float32)
            m[f:-f, f:-f] = 1
            m = ndimage.gaussian_filter(m, f / 2.5)
            pp = Path(td) / f"patch{k}.png"
            Image.fromarray(np.dstack([np.array(crop), (np.clip(m / m.max(), 0, 1) * 255).astype(np.uint8)]), "RGBA").save(pp)
            cmd, params = "file.placeEmbedded", {"path": str(pp), "scale": 100, "fit": False, "smartObject": False, "center": [params["center"][0] - cx0, params["center"][1] - cy0]}
        if cmd == "select.rect" and cx0:
            params = dict(params, x=params["x"] - cx0, y=params["y"] - cy0)
        args += ["--cmd", cmd, "--params", json.dumps(params)]
    args += ["--out", str(out)]
    subprocess.run(args, check=True, stdout=subprocess.DEVNULL)
    im = Image.open(out).convert("RGBA")
    assert im.size == Image.open(src).size, "retouch changed the piece's size"
    im.save(src)
save_rgba(im, ROOT / "roku/reefglass/images" / f"{name}.png")
print(f"{name}: {len(steps)} PhotoCraft steps applied")
