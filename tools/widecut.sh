#!/usr/bin/env bash
# Usage: tools/widecut.sh
# Rebuilds the wide tank's pieces, background and scene from the drafts in gen/drafts: the
# depth maps (tools/depth.py, cached in gen/work), the cuts with their per-piece settings
# (tools/mound.py), the hand retouches (tools/retouch.py), then tools/wideplate.py and
# tools/widescene.py. The reefs' redraws and the empty tank are FLUX.2 klein edits of the
# plate (README, pipeline step 5); the mounds are Z-Image-Turbo drafts (gen/prompts/mound_*).
set -euo pipefail
cd "$(dirname "$0")/.."
P=.venv/bin/python
depth() { [[ -f "$2" ]] || $P tools/depth.py "$1" "$2"; }

depth gen/drafts/flux2_reef_left_s5.png gen/work/reef_left_depth.png
depth gen/drafts/flux2_reef_right_s3.png gen/work/reef_right_depth.png
depth gen/drafts/zit_mound_branch_s1.png gen/work/mound_branch_s1_depth.png
depth gen/drafts/zit_mound_plate_s1.png gen/work/mound_plate_s1_depth.png

# The plate's left reef (anemone, clam), redrawn complete past the photo's left edge.
$P tools/mound.py gen/drafts/flux2_reef_left_s5.png gen/work/reef_left_depth.png reef_left \
  --far 0 --region 0,0,1560,1080 --near 0.08 --band 0.015 --sand 0.5 --sand-sat 0.4 \
  --crisp-below 700 --skirt 830 --floor 780 --paint-dark-box 430,760,480,820 --plate left
$P tools/retouch.py reef_left
# The plate's right reef (moray cave), redrawn complete past the photo's right edge.
$P tools/mound.py gen/drafts/flux2_reef_right_s3.png gen/work/reef_right_depth.png reef_right \
  --far 0 --region 150,150,1920,1080 --sand 0.5 --sand-sat 0.4 --crisp-below 620 --skirt 770 \
  --floor 730 --clear 140,738,238,800 --water-dist 22 --water-box 0,0,600,1080 --key 55 \
  --keep-box 1380,725,1510,800 --close-box 240,690,420,800,14 --paint-box 1400,770,1440,800 \
  --plate right
# The two generated mounds at the tank's ends.
$P tools/mound.py gen/drafts/zit_mound_branch_s1.png gen/work/mound_branch_s1_depth.png mound_a \
  --scale 0.8 --far 0 --crisp-below 760 --skirt 735 --floor 725 --sand-sat 0.4 --water-dist 30
$P tools/mound.py gen/drafts/zit_mound_plate_s1.png gen/work/mound_plate_s1_depth.png mound_b \
  --scale 0.62 --far 0 --crisp-below 600 --skirt 560

$P tools/wideplate.py
$P tools/widescene.py
