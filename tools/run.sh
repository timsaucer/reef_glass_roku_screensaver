#!/usr/bin/env bash
# Usage: tools/run.sh [secs] [query]  — sideload the dev build, launch it with an ECP query
# (e.g. "hour=22&profile=1"), capture the console for <secs>, and take a screenshot.
set -euo pipefail
cd "$(dirname "$0")/.."
source .env
secs="${1:-20}"; query="${2:-}"
tools/sideload.sh roku/reefglass
.venv/bin/python tools/console.py "$secs" > build/console.txt 2>&1 &
cpid=$!
sleep 1
curl -s -o /dev/null -w "launch %{http_code}\n" -X POST "http://$ROKU_IP:8060/launch/dev${query:+?$query}"
sleep $(( secs > 8 ? secs - 6 : 2 ))
tools/screenshot.sh build/shot.jpg && echo "screenshot build/shot.jpg"
wait $cpid || true
grep -vE '^\s*$' build/console.txt | tail -60
