# Credits

Every shipped image was made for Reef Glass and is dedicated to the public domain under
[CC0 1.0](LICENSE-ART). Generated images come from
[Z-Image-Turbo](https://huggingface.co/Tongyi-MAI/Z-Image-Turbo) (Apache 2.0), run locally
with [mflux](https://github.com/filipstrand/mflux) on 2026-11-03, 2026-11-04 and 2026-11-05, and edits with
[FLUX.2 klein 4B](https://huggingface.co/black-forest-labs/FLUX.2-klein-4B) (Apache 2.0) on 2026-11-06; prompts are in
`gen/prompts/` and the kept drafts in `gen/drafts/` (seed in the file name).

| Shipped image(s) | Source | Prompt / seed | Processing |
|---|---|---|---|
| The plate, `gen/plate/bg.jpg`, `fg.png`, `rocks_low.png` (not shipped: the source of the reefs, colors and sand below) | generated | `reef2.txt`, seed 4 | cropped (35,0,1884,1040) and scaled to 1080p; reef layer split by depth ([Depth Anything V2 Small](https://huggingface.co/depth-anything/Depth-Anything-V2-Small-hf), Apache 2.0), rock mask by `tools/plate.py` (`gen/plate_spec.json`) |
| `clown_atlas*.png` | generated, then 3D | `clown.txt`, seed 1 | keyed (`gen/meshes/clown_full.png`), reconstructed in 3D with [TripoSR](https://github.com/VAST-AI-Research/TripoSR) (MIT; `gen/meshes/clown.ply`), rendered straight and bent by `tools/fishviews.py` with the photo's interior projected onto the flanks |
| `bluetang_atlas*.png` | generated, then 3D | `bluetang.txt`, seed 1 | keyed (`gen/meshes/bluetang_full.png`), reconstructed in 3D with [TripoSR](https://github.com/VAST-AI-Research/TripoSR) (MIT; `gen/meshes/bluetang.ply`), rendered straight and bent by `tools/fishviews.py` with the photo's interior projected onto the flanks |
| `yellowtang_atlas*.png` | generated, then 3D | `yellowtang.txt`, seed 1 | keyed (`gen/meshes/yellowtang_full.png`), reconstructed in 3D with [TripoSR](https://github.com/VAST-AI-Research/TripoSR) (MIT; `gen/meshes/yellowtang.ply`), rendered straight and bent by `tools/fishviews.py` with the photo's interior projected onto the flanks |
| `damsel_atlas*.png` | generated, then 3D | `damsel.txt`, seed 1 | keyed (`gen/meshes/damsel_full.png`), reconstructed in 3D with [TripoSR](https://github.com/VAST-AI-Research/TripoSR) (MIT; `gen/meshes/damsel.ply`), rendered straight and bent by `tools/fishviews.py` with the photo's interior projected onto the flanks |
| `gramma_atlas*.png` | generated, then 3D | `gramma.txt`, seed 2 | keyed (`gen/meshes/gramma_full.png`), reconstructed in 3D with [TripoSR](https://github.com/VAST-AI-Research/TripoSR) (MIT; `gen/meshes/gramma.ply`), rendered straight and bent by `tools/fishviews.py` with the photo's interior projected onto the flanks |
| `moray.png`, `moray_jaw.png` | generated | `dragon_moray.txt`, seed 1 | `tools/cutout.py --crop 150,100,1024,576 --width 450`, then `tools/moray.py` with the jaw traced in `gen/moray_trace.json` (jaw split, tilt, fade) |
| `puffer_atlas*.png`, `puffer_ball_atlas*.png` | generated, then 3D | `puffer.txt`, `puffer_ball.txt`, seed 1 | keyed (`gen/meshes/puffer_full.png`, `puffer_ball_full.png`), reconstructed in 3D with [TripoSR](https://github.com/VAST-AI-Research/TripoSR) (MIT), rendered by `tools/fishviews.py` |
| `starfish.png` | generated | `starfish.txt`, seed 1 | `tools/cutout.py --squash 0.42` |
| `duster_crown.png`, `duster_tube.png` | generated | `duster.txt`, seed 1 | `tools/cutout.py --crop` (crown and tube cut separately) |
| `wide_bg0.jpg`, `wide_bg1.jpg` | the plate with its reef removed by FLUX.2 klein 4B | `plate_empty_edit.txt` seeds 3, 6, 10 | `tools/wideplate.py` (sand line flattened, colors matched to the plate, sand grain from the plate, the pieces with their sand, contact shadows and surface reflections baked in) |
| `mound_a.png`, `mound_b.png` | generated | `mound_branch.txt` seed 1, `mound_plate.txt` seed 1 | cut by depth ([Depth Anything V2 Small](https://huggingface.co/depth-anything/Depth-Anything-V2-Small-hf), Apache 2.0) with `tools/mound.py` |
| `reef_left.png`, `reef_right.png`, `cave_shade.png` | the plate's own pixels wherever it shows the two reefs, completed past its frame by FLUX.2 klein 4B redraws | `reef_extend_left.txt` seed 5, `reef_extend_right.txt` seed 3 | `tools/widecut.sh` (`tools/mound.py`, `tools/retouch.py`: a patch of coral from `mound_soft.txt` seed 1); cave shade by `tools/wideplate.py` with the plate's cave alpha (`tools/moray.py`) |
| `ray.png`, `mote.png`, `puff.png` | procedural | — | `tools/fx.py` |
| `splash_*.jpg` | rendered (title in Georgia on the tank's dark blue) | — | `tools/splash.py` |
| `icon_*.jpg`, `store/poster-540x405.jpg` | device screenshot of the above | — | `tools/icons.py` (title in Georgia, rendered) |
| `store/screenshots/*.jpg` | device screenshots of the above | — | — |
