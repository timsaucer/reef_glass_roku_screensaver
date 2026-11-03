"""Usage: python tools/console.py <seconds> [--launch]

Streams the Roku BrightScript console (port 8085) for <seconds>, minus beacon noise.
--launch starts the sideloaded dev app after the console is attached.
"""
import socket
import sys
import time
import urllib.request
from pathlib import Path

env = dict(l.split("=", 1) for l in (Path(__file__).resolve().parent.parent / ".env").read_text().split())
ip = env["ROKU_IP"]
secs = float(sys.argv[1])
s = socket.create_connection((ip, 8085))
s.settimeout(0.5)
if "--launch" in sys.argv:
    time.sleep(0.5)
    try:
        urllib.request.urlopen(urllib.request.Request(f"http://{ip}:8060/launch/dev", method="POST"))
    except urllib.error.HTTPError as e:
        print(f"[launch: {e.code}, app likely already running]")
end = time.time() + secs
buf = b""
# Print complete lines as they arrive, so a long capture can be read while it runs.
while time.time() < end:
    try:
        d = s.recv(4096)
        if not d:
            break
        buf += d
    except socket.timeout:
        continue
    *lines, rest = buf.split(b"\n")
    buf = rest
    for line in lines:
        text = line.decode(errors="replace").rstrip()
        if text.strip() and "beacon" not in text:
            print(text, flush=True)
