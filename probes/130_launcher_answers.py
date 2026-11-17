"""Q: what shape is a `sessionRequestId`, is the approval `url` always on the site's own host, and
what does the launcher answer when the site has it switched off?

Probe 052 measured the launcher's contract and showed `url` as `<site>/app_session_request/<id>`.
A client that shows `url` to a person, or a proxy that forwards it (probe 062), needs to know whether
the host can differ from the site's and what an id looks like before it validates one. A proxy also
adds forwarding headers, so the create call is repeated with each of them.

    python probes/130_launcher_answers.py

No token, no cookie. Five pending requests are created. Each is offered a `DELETE`, then polled until
the site forgets it (about five minutes, probe 052), so a run takes that long. Nothing else is written.

The switched-off case needs a site whose `authentication_app_session_launcher_enabled` is false. The
probe reads the flag and runs the create call either way; it never changes a preference.
"""
import os
import re
import time
import uuid
from urllib.parse import parse_qs, urlparse

import requests

import _lib

env = _lib.load_env()
site = env["FPT_API_SITE_URL"].rstrip("/")
host = urlparse(site).hostname
LAUNCHER = f"{site}/internal_api/app_session_request"
APP = "sg-groundtruth probe 130"
rows = []


def shape(s):
    classes = [n for n, p in (("0-9", r"[0-9]"), ("a-f", r"[a-f]"), ("g-z", r"[g-z]"),
                              ("A-Z", r"[A-Z]"), ("-", r"-"), ("_", r"_")) if re.search(p, s)]
    other = sorted(set(re.sub(r"[0-9A-Za-z_-]", "", s)))
    uuidish = bool(re.fullmatch(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", s))
    return f"length {len(s)}, characters {''.join(classes)}{' other ' + repr(other) if other else ''}, " \
           f"UUID form {uuidish}"


rows.append("=== GET /api/v1")
root = requests.get(f"{site}/api/v1", timeout=30).json()["data"]
enabled = root.get("authentication_app_session_launcher_enabled")
rows.append(f"  authentication_app_session_launcher_enabled: {enabled!r}")
rows.append(f"  user_authentication_method: {root.get('user_authentication_method')!r}")

made = []
for label, headers in (("no extra header", {}),
                       ("X-Forwarded-Host: example.invalid", {"X-Forwarded-Host": "example.invalid"}),
                       ("Forwarded: host=example.invalid", {"Forwarded": "host=example.invalid;proto=https"}),
                       ("Origin and Referer https://example.invalid",
                        {"Origin": "https://example.invalid", "Referer": "https://example.invalid/"}),
                       ("X-Forwarded-Host, -Proto: http, -Port: 8443",
                        {"X-Forwarded-Host": "example.invalid", "X-Forwarded-Proto": "http",
                         "X-Forwarded-Port": "8443"})):
    r = requests.post(LAUNCHER, data={"appName": APP, "machineId": uuid.uuid4().hex},
                      headers=headers, timeout=30)
    rows.append(f"\n=== POST /internal_api/app_session_request, {label}")
    rows.append(f"  -> {r.status_code} {r.headers.get('content-type', '')}")
    if not r.ok:
        rows.append(f"     {r.text.strip()[:500]}")
        continue
    d = r.json()
    sid, url = d["sessionRequestId"], d["url"]
    made.append(sid)
    u = urlparse(url)
    q = parse_qs(u.query)
    rows.append(f"  keys {sorted(d)}")
    rows.append(f"  sessionRequestId: {shape(sid)}")
    rows.append(f"  url scheme {u.scheme}, host is the site's own: {u.hostname == host}"
                + ("" if u.hostname == host else f" (host {u.hostname})")
                + f", port {u.port}, path {u.path.replace(sid, '<id>')}, query keys {sorted(q)}, "
                f"sticky_id equals the id: {q.get('sticky_id', [''])[0] == sid}")
    rows.append(f"  sticky_id: {shape(q.get('sticky_id', [''])[0])}")

rows.append(f"\n=== the ids: {len(made)} made, {len(set(made))} distinct, "
            f"common prefix length {len(os.path.commonprefix(made)) if made else 0}")

rows.append("\n=== clean-up: DELETE each, then PUT to see if it is gone")
for i, sid in enumerate(made):
    d = requests.delete(f"{LAUNCHER}/{sid}", timeout=30)
    p = requests.put(f"{LAUNCHER}/{sid}", timeout=30)
    rows.append(f"  request {i + 1}: DELETE -> {d.status_code} {d.text.strip()[:200]}; "
                f"PUT after -> {p.status_code} {p.text.strip()[:100]}")

rows.append("\n=== each request polled every 30s until it reads 404")
t0, left = time.time(), set(made)
while left and time.time() - t0 < 480:
    time.sleep(30)
    for sid in sorted(left):
        if requests.put(f"{LAUNCHER}/{sid}", timeout=30).status_code == 404:
            left.discard(sid)
            rows.append(f"  one forgotten by {time.time() - t0:.0f}s")
rows.append(f"  {len(left)} still answering after {time.time() - t0:.0f}s")

_lib.emit("130_launcher_answers", "\n".join(rows), env)
