#!/usr/bin/env bash
# Usage: tools/sideload.sh <app-dir> [--release]
# Zips the app and installs it on the dev Roku. Exits non-zero unless the device reports a
# successful (or identical) install.
#
# --release packages it the way it ships: screensaver-only. The manifest loses "title" and
# gains an explicit entry point and hidden=1, and source/dev.brs (Main) is left out.
# Reef Glass has no settings screen, so there is no run_screensaver_settings entry.
set -euo pipefail
cd "$(dirname "$0")/.."
source .env
app="${1:?app dir}"
release="${2:-}"
zip="$PWD/build/$(basename "$app")${release:+-release}.zip"
mkdir -p build && rm -f "$zip"
stage="$app"
if [[ "$release" == "--release" ]]; then
  stage="$PWD/build/stage-$(basename "$app")"
  rm -rf "$stage" && cp -R "$app" "$stage"
  rm -f "$stage/source/dev.brs"
  { grep -v '^title=' "$app/manifest"
    printf 'run_screensaver=RunScreenSaver\nhidden=1\n'
  } > "$stage/manifest"
fi
(cd "$stage" && zip -qr -X "$zip" . -x '.*')
msg=$(curl -sS --digest -u "rokudev:$ROKU_DEV_PASSWORD" \
  -F "mysubmit=Install" -F "archive=@$zip" \
  "http://$ROKU_IP/plugin_install" | grep -oE '"text":"[^"]*"' | cut -d\" -f4 || true)
echo "$msg ($(du -h "$zip" | cut -f1) zip)"
grep -qE "Install Success|Identical" <<<"$msg"
