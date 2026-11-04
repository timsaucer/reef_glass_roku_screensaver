# Credits

Every shipped image was made for Reef Glass and is dedicated to the public domain under
[CC0 1.0](LICENSE-ART). Generated images come from
[Z-Image-Turbo](https://huggingface.co/Tongyi-MAI/Z-Image-Turbo) (Apache 2.0), run locally
with [mflux](https://github.com/filipstrand/mflux) on 2026-11-03 and 2026-11-04; prompts are in
`gen/prompts/` and the kept drafts in `gen/drafts/` (seed in the file name).

| Shipped image(s) | Source | Prompt / seed | Processing |
|---|---|---|---|
| `bg.jpg`, `fg.png`, `rocks_low.png` | generated | `reef2.txt`, seed 4 | cropped (35,0,1884,1040) and scaled to 1080p; reef layer split by depth ([Depth Anything V2 Small](https://huggingface.co/depth-anything/Depth-Anything-V2-Small-hf), Apache 2.0), rock mask by `tools/plate.py` (`gen/plate_spec.json`) |
| `clown_atlas*.png` | generated, then 3D | `clown.txt`, seed 1 | keyed (`gen/meshes/clown_full.png`), reconstructed in 3D with [TripoSR](https://github.com/VAST-AI-Research/TripoSR) (MIT; `gen/meshes/clown.ply`), rendered straight and bent by `tools/fishviews.py` with the photo's interior projected onto the flanks |
| `bluetang_atlas*.png` | generated, then 3D | `bluetang.txt`, seed 1 | keyed (`gen/meshes/bluetang_full.png`), reconstructed in 3D with [TripoSR](https://github.com/VAST-AI-Research/TripoSR) (MIT; `gen/meshes/bluetang.ply`), rendered straight and bent by `tools/fishviews.py` with the photo's interior projected onto the flanks |
| `yellowtang_atlas*.png` | generated, then 3D | `yellowtang.txt`, seed 1 | keyed (`gen/meshes/yellowtang_full.png`), reconstructed in 3D with [TripoSR](https://github.com/VAST-AI-Research/TripoSR) (MIT; `gen/meshes/yellowtang.ply`), rendered straight and bent by `tools/fishviews.py` with the photo's interior projected onto the flanks |
| `damsel_atlas*.png` | generated, then 3D | `damsel.txt`, seed 1 | keyed (`gen/meshes/damsel_full.png`), reconstructed in 3D with [TripoSR](https://github.com/VAST-AI-Research/TripoSR) (MIT; `gen/meshes/damsel.ply`), rendered straight and bent by `tools/fishviews.py` with the photo's interior projected onto the flanks |
| `gramma_atlas*.png` | generated, then 3D | `gramma.txt`, seed 2 | keyed (`gen/meshes/gramma_full.png`), reconstructed in 3D with [TripoSR](https://github.com/VAST-AI-Research/TripoSR) (MIT; `gen/meshes/gramma.ply`), rendered straight and bent by `tools/fishviews.py` with the photo's interior projected onto the flanks |
| `moray.png`, `moray_jaw.png` | generated | `moray.txt`, seed 1 | `tools/cutout.py --crop 150,120,600,576`, then `tools/moray.py` (jaw split, tilt, fade) |
| `cave_shade.png` | from `bg.jpg` | — | `tools/moray.py` |
| `puffer_atlas*.png`, `puffer_ball_atlas*.png` | generated, then 3D | `puffer.txt`, `puffer_ball.txt`, seed 1 | keyed (`gen/meshes/puffer_full.png`, `puffer_ball_full.png`), reconstructed in 3D with [TripoSR](https://github.com/VAST-AI-Research/TripoSR) (MIT), rendered by `tools/fishviews.py` |
| `starfish.png` | generated | `starfish.txt`, seed 1 | `tools/cutout.py --squash 0.42` |
| `duster_crown.png`, `duster_tube.png` | generated | `duster.txt`, seed 1 | `tools/cutout.py --crop` (crown and tube cut separately) |
| `caustic_*.png`, `ray.png`, `mote.png`, `puff.png` | procedural | — | `tools/fx.py`, `tools/caustics.py` |
| `icon_*.jpg`, `store/poster-540x405.jpg` | device screenshot of the above | — | `tools/icons.py` (title in Georgia, rendered) |
| `store/screenshots/*.jpg` | device screenshots of the above | — | — |
