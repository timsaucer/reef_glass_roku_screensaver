#!/usr/bin/env bash
# Usage: tools/screenshot.sh <out.jpg>  — grabs the dev app's current frame from the Roku.
set -euo pipefail
cd "$(dirname "$0")/.."
source .env
curl -sS --digest -u "rokudev:$ROKU_DEV_PASSWORD" -F "mysubmit=Screenshot" "http://$ROKU_IP/plugin_inspect" > /dev/null
curl -sS --digest -u "rokudev:$ROKU_DEV_PASSWORD" -o "$1" "http://$ROKU_IP/pkgs/dev.jpg"
