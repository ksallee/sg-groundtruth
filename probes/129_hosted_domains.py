"""Q: under which Autodesk domains does a hosted Flow PT site answer, and does one name redirect to
another?

A proxy that forwards the App Session Launcher calls (probe 062) has to decide which hosts it will
forward to. Autodesk's security page lists `<mysite>.shotgrid.autodesk.com` and
`<mysite>.shotgunstudio.com` and no regional host. This asks the configured site's own name under
each domain, plus a name no site holds, so a wildcard answer is not mistaken for a site.

    python probes/129_hosted_domains.py

Unauthenticated GETs only, redirects never followed. Two requests per host. Nothing is created.
"""
import socket
import uuid
from urllib.parse import urlparse

import requests

import _lib

env = _lib.load_env()
site = env["FPT_API_SITE_URL"].rstrip("/")
host = urlparse(site).hostname
name = host.split(".")[0]
own = host[len(name) + 1:]
# The two Autodesk lists (security page) and the pre-2022 product name. Nothing regional is listed.
DOMAINS = ["shotgrid.autodesk.com", "shotgunstudio.com", "shotgun.autodesk.com"]
nobody = f"zzprobe129-{uuid.uuid4().hex[:8]}"
rows = [f"configured site: <site>.{own}"]


def resolve(h):
    try:
        return sorted({a[4][0] for a in socket.getaddrinfo(h, 443, proto=socket.IPPROTO_TCP)})
    except socket.gaierror as e:
        return f"no DNS ({e.args[-1]})"


def get(url):
    try:
        r = requests.get(url, allow_redirects=False, timeout=20)
    except requests.RequestException as e:
        return f"{type(e).__name__}: {str(e)[:160]}"
    loc = r.headers.get("location", "")
    body = r.text.strip().replace("\n", " ")[:160]
    return (f"{r.status_code} {r.headers.get('content-type', '')}"
            + (f"  location {loc}" if loc else f"  {body}"))


for d in DOMAINS:
    for label, n in (("site name", name), ("unheld name", nobody)):
        h = f"{n}.{d}"
        rows.append(f"\n=== {label} under {d}{'  (the configured host)' if h == host else ''}")
        ips = resolve(h)
        rows.append(f"  DNS: {'resolves' if isinstance(ips, list) else ips}")
        if not isinstance(ips, list):
            continue
        rows.append(f"  GET /        -> {get(f'https://{h}/')}")
        rows.append(f"  GET /api/v1  -> {get(f'https://{h}/api/v1')}")

rows.append("\n=== the configured host over http")
rows.append(f"  GET http://<site>.{own}/ -> {get(f'http://{host}/')}")

_lib.emit("129_hosted_domains", "\n".join(rows).replace(nobody, "<unheld>"), env)
