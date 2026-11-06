"""The wide tank's layout (gen/wide_spec.json) resolved: a piece cut from a reef's redraw
("reef": side) stands where that redraw's origin is placed ("reefs".<side>."draftAt") plus the
piece's crop corner in the draft (gen/work/<name>_cut.json, written by tools/mound.py), so a
recut that moves the crop never misplaces the piece against what is anchored to the reef.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def cut(img):
    return json.loads((ROOT / "gen/work" / (Path(img).stem + "_cut.json")).read_text())


def resolve(spec):
    for p in spec["pieces"]:
        if "reef" in p:
            at = spec["reefs"][p["reef"]]["draftAt"]
            c = cut(p["img"])["crop"]
            p["x"], p["y"] = at[0] + c[0], at[1] + c[1]
    return spec


def plate_to_tank(spec, side, x, y):
    """Plate px on a reef to tank px, through the plate-to-redraw transform."""
    r = spec["reefs"][side]
    M = r["affine"]
    u = M[0][0] * x + M[0][1] * y + M[0][2] + r["draftAt"][0]
    v = M[1][0] * x + M[1][1] * y + M[1][2] + r["draftAt"][1]
    return round(u), round(v)
