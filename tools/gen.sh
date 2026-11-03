#!/usr/bin/env bash
# Usage: W=1920 H=1088 tools/gen.sh <prompt-name> <seed>...
# One Z-Image-Turbo image per seed, strictly one at a time (two at once thrash memory).
set -euo pipefail
cd "$(dirname "$0")/.."
name=$1; shift
for s in "$@"; do
  out="gen/drafts/zit_${name}_s${s}.png"
  [[ -f "$out" ]] && { echo "skip $out"; continue; }
  .venv/bin/mflux-generate-z-image-turbo -q 8 --low-ram --prompt-file "gen/prompts/$name.txt" \
    --width "${W:-1920}" --height "${H:-1088}" --seed "$s" --output "$out"
  echo "done $out"
done
