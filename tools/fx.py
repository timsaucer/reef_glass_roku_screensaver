"""Usage: .venv/bin/python tools/fx.py

Procedural light and particle sprites: caustic bands for the sand, light shafts, marine snow
and sand puffs. The caustic band's height must reach from caustics.top in reef.json to the
bottom of the screen.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from caustics import caustic_band  # noqa: E402
from imgio import save_rgba  # noqa: E402
import placeholders as ph  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
cfg = json.loads((ROOT / "roku/reefglass/scenes/reef.json").read_text())
h = 1080 - cfg["caustics"]["top"]
for i in range(2):
    save_rgba(caustic_band(1024, h, seed=11 + i, cells=26 + 6 * i), ph.OUT / f"caustic_{i}.png")
ph.soft("mote.png", 8)
ph.soft("puff.png", 24)
ph.ray()
print(f"fx written (caustic band {h} px)")
