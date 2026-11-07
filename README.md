# Reef Glass

A Roku screensaver: a calm saltwater reef tank seen through the glass, about two screens wide,
that the view slowly glides across and back. Photoreal reefs on white sand, with fish, critters
and light animated over them.

- **Fish:** a clownfish pair, blue and yellow tangs, royal grammas, a loose school of blue
  damselfish and a porcupine pufferfish that now and then puffs up. Each fish is a 3D model
  pre-rendered from 26 headings with three strengths of body bend. Fish turn and tilt as they
  climb and dive, pass in front of and behind the reef, and keep a little apart.
- **Critters:** a dragon moray in the cave under the right-hand rock, feather duster worms that
  snap shut when fish pass, and a starfish on the sand.
- **Light:** light shafts, the reef reflected in the water surface, drifting marine snow.
- **Setting:** lighting stays at daytime (the default), dusk or night, or follows the Roku's
  clock (day, dusk, moonlit night).

## Layout

- `roku/reefglass/`: the package (BrightScript `roScreen` at 30 fps; SceneGraph only for the
  settings screen)
  - `source/`: `main.brs` (entry points, frame loop), `reef.brs` (draw order, light),
    `fish.brs` (fish), `critters.brs`, `moray.brs`, `pan.brs` (background, reef pieces, camera),
    `settings.brs`, `dev.brs` (dev builds only)
  - `components/`: the settings screen
  - `scenes/tank.json`: every position and tuning value, built by `tools/widescene.py` from
    `gen/base_scene.json` (species, light, fish views) and `gen/wide_spec.json` (layout)
  - `images/`: built assets, made by `tools/`
- `tools/`: asset pipeline and device helpers
- `gen/`: prompts, the drafts that were used, keyed fish photos and 3D meshes, the original
  one-screen plate (`gen/plate/`: the source of the reefs, colors and sand), retouch steps
- `store/`, `STORE.md`: store listing and assets

## Device

`.env` (gitignored) holds `ROKU_IP`, `ROKU_DEV_PASSWORD`, `ROKU_DEV_ID`, `ROKU_SIGN_PASSWORD`.

- `tools/run.sh [secs] [query]`: sideload the dev build, launch it, capture the console and a
  screenshot (`build/shot.jpg`)
- Launch parameters (see `source/dev.brs`): `hour=`, `daycycle=`, `lighting=`, `settings=1`,
  `profile=1`, `trace=<species>`, `pose=<species>` (with `fine=`, `pp=`, `pitch=`), `puff=1`,
  `fps=<n>` (0: uncapped), `pan=<s>`, `cam=<x>`, `nofish=1`
- `tools/sideload.sh roku/reefglass [--release]`, `tools/console.py`, `tools/screenshot.sh`
- `tools/package.sh`: signed release package for the store (see `STORE.md`)

## Art pipeline

1. `tools/gen.sh <prompt> <seed>...`: Z-Image-Turbo drafts (mflux, local).
2. The original plate (`gen/plate/`, from the first one-screen tank): `tools/plate.py
   grid|build|rocks` with `gen/plate_spec.json`; `tools/depth.py` and `tools/layers.py` split
   its reef layer (`fg.png`). `tools/fx.py` makes the light sprites.
3. Animals: `tools/cutout.py` keys a draft from its green background.
4. Fish: `ext/venv/bin/python tools/fish3d.py` rebuilds the keyed photo in 3D (TripoSR), then
   `ext/venv/bin/python tools/fishviews.py views <mesh> <name> --photo <keyed.png>` renders and
   packs the views (`--fat`, `--under`, `--len`, `--ped`, `--ball`; `strip` previews a turn).
5. Wide tank (`mflux-generate-flux2-edit -m flux2-klein-4b`, about 1.5 min a try):
   the plate with its reef edited out (`gen/prompts/plate_empty_edit.txt`) gives the empty
   tank; the plate shifted 700 px with a blank side (`reef_extend_<side>.txt`) gives each reef
   redrawn complete; the end mounds are Z-Image-Turbo drafts (`mound_*.txt`).
   `tools/widecut.sh` then rebuilds everything from `gen/drafts`: depth maps
   (`tools/depth.py`), the cuts with their per-piece settings (`tools/mound.py`; `--plate`
   uses the plate's own pixels wherever it shows the reef), the PhotoCraft retouches in
   `gen/retouch` (`tools/retouch.py`), the background tiles and cave shade
   (`tools/wideplate.py`) and `scenes/tank.json` (`tools/widescene.py`).
6. `tools/moray.py` for the eel; `tools/icons.py <screenshot> [--zoom] [--at]` for the icons and
   store poster; `tools/splash.py` for the splash screens.

TripoSR setup (`ext/` is gitignored): clone https://github.com/VAST-AI-Research/TripoSR into
`ext/TripoSR`, `uv venv -p 3.11 ext/venv`, then `VIRTUAL_ENV=ext/venv uv pip install torch
omegaconf einops transformers==4.44.2 trimesh huggingface-hub scikit-image pillow moderngl numpy
imageio imagequant opencv-python-headless`. Local patches: marching cubes from scikit-image in
`tsr/models/isosurface.py` (vertices in torchmcubes' z, y, x order), and an optional `rembg`
import in `tsr/utils.py`.

## License

Code: [Apache 2.0](LICENSE). Images: [CC0 1.0](LICENSE-ART), all made for this project; see
[CREDITS.md](CREDITS.md).
