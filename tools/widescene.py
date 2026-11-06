"""Usage: .venv/bin/python tools/widescene.py [gen/wide_spec.json]

Builds scenes/tank.json, the panning tank, from gen/base_scene.json (species, light, fx)
and a layout spec (gen/wide_spec.json):

  width, period          tank width (px) and camera back-and-forth period (s)
  ease                   fraction of each sweep spent speeding up (and slowing down)
  bg, bgBands            background tiles (pkg paths) and parallax bands [y0, y1, par]
  pieces                 [{img, x, y, sc?, par?, mir?, tint?, shadow?}]: img is a file in
                         roku/reefglass/images; near pieces (par 1) make up the coral map
  reefs                  {left, right}: the plate's two reefs as redrawn pieces: "affine" maps
                         plate px to the redraw's draft, "draftAt" is where the redraw's origin
                         stands in the tank (pieces with "reef": side are placed from it and
                         their crop, see tools/widelayout.py). Everything the base scene places
                         on a reef (moray, dusters, starfish, homes; plate x < 820: left)
                         moves with it. A species override home [x, y, z, "left"] is in plate
                         px on that reef; without the tag, in tank px.
  low                    [x0, x1] of open sand where cruisers may graze
  species                per-species overrides (e.g. clown count, group, soloSize)

Everything in tank.json is in tank coordinates. The coral map is the near pieces' alpha in
cells of 40 px, grown by one cell.
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from widelayout import plate_to_tank, resolve  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
IMAGES = ROOT / "roku/reefglass/images"
SCENES = ROOT / "roku/reefglass/scenes"
SPLIT = 820  # one-screen plate: x of the open water between the left and right reefs


def coral_map(spec, cell=40, grow=1):
    w, h = spec["width"], 1080
    alpha = np.zeros((h, w), np.float32)
    for p in spec["pieces"]:
        if p.get("par", 1.0) < 1:
            continue
        im = Image.open(IMAGES / p["img"]).convert("RGBA")
        sc = p.get("sc", 1.0)
        if sc != 1.0:
            im = im.resize((round(im.width * sc), round(im.height * sc)), Image.LANCZOS)
        if p.get("mir"):
            im = im.transpose(Image.FLIP_LEFT_RIGHT)
        a = np.array(im)[..., 3].astype(np.float32) / 255
        x0, y0 = int(p["x"]), int(p["y"])
        xa, ya = max(x0, 0), max(y0, 0)
        xb, yb = min(x0 + a.shape[1], w), min(y0 + a.shape[0], h)
        if xb > xa and yb > ya:
            alpha[ya:yb, xa:xb] = np.maximum(alpha[ya:yb, xa:xb], a[ya - y0:yb - y0, xa - x0:xb - x0])
    rows_n, cols_n = h // cell, w // cell
    occ = (alpha[:rows_n * cell, :cols_n * cell].reshape(rows_n, cell, cols_n, cell).mean(axis=(1, 3)) > 0.1).astype(np.uint8)
    if grow:
        k = 2 * grow + 1
        occ = cv2.dilate(occ, np.ones((k, k), np.uint8))
    return {"cell": cell, "rows": ["".join("#" if v else "." for v in r) for r in occ]}


def main():
    spec_path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "gen/wide_spec.json"
    spec = resolve(json.loads(spec_path.read_text()))
    cfg = json.loads((ROOT / "gen/base_scene.json").read_text())
    W = spec["width"]

    def side_of(x):
        return "left" if x < SPLIT else "right"

    def to_tank(x, y, side=None):
        return plate_to_tank(spec, side or side_of(x), x, y)

    cfg["pan"] = {
        "width": W,
        "period": spec["period"],
        "ease": spec.get("ease", 0.15),
        "bg": spec["bg"],
        "bgBands": spec["bgBands"],
        "pieces": [dict(p, img="pkg:/images/" + p["img"], shadow=False) for p in spec["pieces"]],
    }
    cfg["coral"] = coral_map(spec)
    r = cfg["roam"]
    r["x0"], r["x1"] = -260, W + 260
    if "low" in spec:
        r["low"]["x0"], r["low"]["x1"] = spec["low"]
    for d in cfg["dusters"]:
        d["x"], d["y"] = to_tank(d["x"], d["y"])
    sf = cfg["starfish"]
    (sf["x0"], sf["y"]), (sf["x1"], _) = to_tank(sf["x0"], sf["y"]), to_tank(sf["x1"], sf["y"])
    m = cfg["moray"]
    m["x"], m["y"] = to_tank(m["x"], m["y"])
    # The clip stays exactly at the shade's right edge (as on the plate): mapped on its own,
    # the transform's ~1% scale moved it 2 px past, a column of eel showing beside the rock.
    clip_off = m["clip"] - m["shade"][0]
    m["shade"] = list(to_tank(*m["shade"]))
    m["clip"] = m["shade"][0] + clip_off
    cfg["anemone"]["home"] = list(to_tank(*cfg["anemone"]["home"]))
    for name, sp in cfg["species"].items():
        if "homes" in sp:
            sp["homes"] = [list(to_tank(h[0], h[1])) + h[2:] for h in sp["homes"]]
        if "visitAt" in sp:
            sp["visitAt"] = list(to_tank(*sp["visitAt"][:2])) + sp["visitAt"][2:]
        ov = json.loads(json.dumps(spec.get("species", {}).get(name, {})))
        if "homes" in ov:
            ov["homes"] = [list(to_tank(h[0], h[1], h[3])) + [h[2]] if len(h) > 3 else h for h in ov["homes"]]
        sp.update(ov)
    out = SCENES / "tank.json"
    out.write_text(json.dumps(cfg, indent=2) + "\n")
    print("wrote", out)
    print("\n".join(cfg["coral"]["rows"]))
    # Piece images in the package that the layout does not use (mound.py writes a near and a
    # far version of every mound): each costs package space for nothing.
    used = {p["img"] for p in spec["pieces"]}
    for f in sorted(list(IMAGES.glob("mound_*.png")) + list(IMAGES.glob("reef_*.png")) + list(IMAGES.glob("pan_*.png"))):
        if f.name not in used:
            print(f"warning: {f.name} is not used ({f.stat().st_size // 1024} KB); delete it from the package")


if __name__ == "__main__":
    main()
