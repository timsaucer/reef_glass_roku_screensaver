# Credits

Every shipped image was made for Reef Glass and is dedicated to the public domain under
[CC0 1.0](LICENSE-ART). Generated images come from
[Z-Image-Turbo](https://huggingface.co/Tongyi-MAI/Z-Image-Turbo) (Apache 2.0), run locally
with [mflux](https://github.com/filipstrand/mflux) on 2026-11-03; prompts are in
`gen/prompts/` and the kept drafts in `gen/drafts/` (seed in the file name).

| Shipped image(s) | Source | Prompt / seed | Processing |
|---|---|---|---|
| `bg.jpg`, `fg.png`, `rocks_low.png`, `lip.png`, `anemone_*.png`, `clam_shimmer.png` | generated | `reef2.txt`, seed 4 | cropped (35,0,1884,1040) and scaled to 1080p; reef layer split by depth ([Depth Anything V2 Small](https://huggingface.co/depth-anything/Depth-Anything-V2-Small-hf), Apache 2.0); burrow, anemone sway and clam shimmer derived by `tools/plate.py` (`gen/plate_spec.json`) |
| `clown_body/tail.png` | generated | `clown.txt`, seed 1 | `tools/cutout.py --fish` |
| `bluetang_body/tail.png` | generated | `bluetang.txt`, seed 1 | `tools/cutout.py --fish` |
| `yellowtang_body/tail.png` | generated | `yellowtang.txt`, seed 1 | `tools/cutout.py --fish` |
| `damsel_body/tail.png` | generated | `damsel.txt`, seed 1 | `tools/cutout.py --fish` |
| `gramma_body/tail.png` | generated | `gramma.txt`, seed 2 | `tools/cutout.py --fish` |
| `goby_body/tail.png` | generated | `goby.txt`, seed 1 | `tools/cutout.py --fish --key 5,16` |
| `shrimp.png` | generated | `shrimp.txt`, seed 1 | `tools/cutout.py` |
| `starfish.png` | generated | `starfish.txt`, seed 1 | `tools/cutout.py --squash 0.42` |
| `duster_crown.png`, `duster_tube.png` | generated | `duster.txt`, seed 1 | `tools/cutout.py --crop` (crown and tube cut separately) |
| `caustic_*.png`, `ray.png`, `mote.png`, `puff.png` | procedural | — | `tools/fx.py`, `tools/caustics.py` |
| `icon_*.jpg`, `store/poster-540x405.jpg` | device screenshot of the above | — | `tools/icons.py` (title in Georgia, rendered) |
| `flame_body/tail.png`, `clam.png` | procedural placeholders, not shown | — | `tools/placeholders.py` |
