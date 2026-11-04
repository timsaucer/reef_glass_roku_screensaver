# Credits

Every shipped image was made for Reef Glass and is dedicated to the public domain under
[CC0 1.0](LICENSE-ART). Generated images come from
[Z-Image-Turbo](https://huggingface.co/Tongyi-MAI/Z-Image-Turbo) (Apache 2.0), run locally
with [mflux](https://github.com/filipstrand/mflux) on 2026-11-03 and 2026-11-04; prompts are in
`gen/prompts/` and the kept drafts in `gen/drafts/` (seed in the file name).

| Shipped image(s) | Source | Prompt / seed | Processing |
|---|---|---|---|
| `bg.jpg`, `fg.png`, `rocks_low.png`, `anemone_*.png` | generated | `reef2.txt`, seed 4 | cropped (35,0,1884,1040) and scaled to 1080p; reef layer split by depth ([Depth Anything V2 Small](https://huggingface.co/depth-anything/Depth-Anything-V2-Small-hf), Apache 2.0); anemone sway derived by `tools/plate.py` (`gen/plate_spec.json`) |
| `clown_body/tail.png` | generated | `clown.txt`, seed 1 | `tools/cutout.py --fish` |
| `bluetang_body/tail.png` | generated | `bluetang.txt`, seed 1 | `tools/cutout.py --fish` |
| `yellowtang_body/tail.png` | generated | `yellowtang.txt`, seed 1 | `tools/cutout.py --fish` |
| `damsel_body/tail.png` | generated | `damsel.txt`, seed 1 | `tools/cutout.py --fish` |
| `gramma_body/tail.png` | generated | `gramma.txt`, seed 2 | `tools/cutout.py --fish` |
| `lion_body/tail.png` | generated | `lion.txt`, seed 1 | `tools/cutout.py --fish --rear 0.18,0.3` |
| `<fish>_front.png` | generated | `<fish>_front.txt`, seed 1 | `tools/cutout.py --front` |
| `moray.png`, `moray_jaw.png` | generated | `moray.txt`, seed 1 | `tools/cutout.py --crop 150,120,600,576`, then `tools/moray.py` (jaw split, tilt, fade) |
| `cave_shade.png` | from `bg.jpg` | — | `tools/moray.py` |
| `starfish.png` | generated | `starfish.txt`, seed 1 | `tools/cutout.py --squash 0.42` |
| `duster_crown.png`, `duster_tube.png` | generated | `duster.txt`, seed 1 | `tools/cutout.py --crop` (crown and tube cut separately) |
| `caustic_*.png`, `ray.png`, `mote.png`, `puff.png` | procedural | — | `tools/fx.py`, `tools/caustics.py` |
| `icon_*.jpg`, `store/poster-540x405.jpg` | device screenshot of the above | — | `tools/icons.py` (title in Georgia, rendered) |
