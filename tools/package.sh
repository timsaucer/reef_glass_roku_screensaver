#!/usr/bin/env bash
# Usage: tools/package.sh
# Installs the screensaver-only (--release) build on the dev Roku, has the device sign and
# package it with the developer key (ROKU_SIGN_PASSWORD in .env), and downloads the result to
# build/reefglass-<major>.<minor>.<build>.pkg for upload to the Developer Dashboard.
set -euo pipefail
cd "$(dirname "$0")/.."
source .env
: "${ROKU_SIGN_PASSWORD:?run genkey first (see STORE.md)}"
m=roku/reefglass/manifest
ver="$(grep ^major_version= $m | cut -d= -f2).$(grep ^minor_version= $m | cut -d= -f2).$(grep ^build_version= $m | cut -d= -f2)"
tools/sideload.sh roku/reefglass --release
page=$(curl -sS --digest -u "rokudev:$ROKU_DEV_PASSWORD" \
  -F "mysubmit=Package" -F "app_name=Reef Glass/$ver" -F "passwd=$ROKU_SIGN_PASSWORD" -F "pkg_time=$(date +%s)000" \
  "http://$ROKU_IP/plugin_package")
pkg=$(grep -oE 'pkgs/[A-Za-z0-9_./-]+\.pkg' <<<"$page" | head -1 || true)
if [[ -z "$pkg" ]]; then
  grep -oE '"text":"[^"]*"' <<<"$page" | cut -d\" -f4 >&2 || true
  echo "packaging failed" >&2
  exit 1
fi
out="build/reefglass-$ver.pkg"
curl -sS --digest -u "rokudev:$ROKU_DEV_PASSWORD" -o "$out" "http://$ROKU_IP/$pkg"
echo "$out ($(stat -f%z "$out") bytes)"
