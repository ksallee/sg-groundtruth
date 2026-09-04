#!/usr/bin/env python3
"""Shoot pages of the built site, headless, and print only the paths written.

Why a script and not a browser MCP: an MCP returns an accessibility snapshot and a console log on
every call, which is most of what a session costs. This writes files to disk and prints one line of
JSON, so an agent reads the one screenshot it asked for and pays for nothing else.

    tools/shot.py /entity-types/Version
    tools/shot.py / /how-it-works --width 1680 --full
    tools/shot.py /entity-types/Version --overlay ../corpus.local --out /tmp/shots

Needs playwright, which this repo does not depend on:

    uv run --with playwright --python 3.11 python site/tools/shot.py /

--overlay rebuilds with PUBLIC_OVERLAY_SOURCE pointed at that directory, which is how the reading
levels are exercised: `corpus/` alone renders the API level, `corpus.example` or a `corpus.local`
with several projects renders the marked sections. Without it the existing build is served as it
stands. Either way the server is a `vite preview` on a free port, so two agents never collide.

Exit status is the number of paths that did not answer 200, so it works in a pipeline.
"""
import argparse
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

SITE = Path(__file__).resolve().parents[1]


def free_port(start=4300):
    for p in range(start, start + 60):
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", p)) != 0:
                return p
    raise SystemExit("no free port")


def build(overlay):
    """Rebuild only when asked to change the reading level; a build is 2s but not free."""
    env = {**os.environ, "PUBLIC_OVERLAY_SOURCE": overlay}
    r = subprocess.run(["npx", "vite", "build", "--logLevel", "error"],
                       cwd=SITE, env=env, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(r.stderr.strip() or "vite build failed")


def serve(port):
    """--host is not optional: vite preview binds [::1] by default, so a readiness probe on
    127.0.0.1 never connects and free_port() above reports a held port as free."""
    proc = subprocess.Popen(["npx", "vite", "preview", "--port", str(port), "--strictPort",
                             "--host", "127.0.0.1"],
                            cwd=SITE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(60):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=2).read()
            return proc
        except Exception:
            time.sleep(0.5)
    proc.terminate()
    raise SystemExit(f"vite preview did not come up on {port}")


def main():
    ap = argparse.ArgumentParser(prog="shot.py", description=__doc__.split("\n")[0])
    ap.add_argument("paths", nargs="+", help="routes to shoot, e.g. / /how-it-works")
    ap.add_argument("--out", default="", help="directory for the images (default: a temp dir)")
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=900)
    ap.add_argument("--full", action="store_true", help="whole page, not just the viewport")
    ap.add_argument("--overlay", default="", help="PUBLIC_OVERLAY_SOURCE to rebuild with")
    ap.add_argument("--js", default="", help="file with an async body run before each shot; - for stdin")
    a = ap.parse_args()

    out = Path(a.out) if a.out else Path(os.environ.get("TMPDIR", "/tmp")) / "sg-shots"
    out.mkdir(parents=True, exist_ok=True)

    js = ""
    if a.js:
        js = sys.stdin.read() if a.js == "-" else Path(a.js).read_text()

    if a.overlay:
        build(a.overlay)

    port = free_port()
    proc = serve(port)
    from playwright.sync_api import sync_playwright

    shots, bad = [], 0
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(headless=True)
            ctx = b.new_context(viewport={"width": a.width, "height": a.height})
            pg = ctx.new_page()
            for path in a.paths:
                r = pg.goto(f"http://127.0.0.1:{port}{path}", wait_until="networkidle")
                # A prerendered 404 still renders, so the status is the only honest check.
                if not r or r.status != 200:
                    shots.append({"path": path, "status": r.status if r else None})
                    bad += 1
                    continue
                if js:
                    pg.evaluate(f"async () => {{ {js} }}")
                name = (path.strip("/").replace("/", "-") or "index") + f"-{a.width}.png"
                f = out / name
                pg.screenshot(path=str(f), full_page=a.full)
                shots.append({"path": path, "file": str(f), "bytes": f.stat().st_size})
            ctx.close()
            b.close()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except Exception:
            proc.kill()

    print(json.dumps({"shots": shots}, indent=1))
    return bad


if __name__ == "__main__":
    raise SystemExit(main())
