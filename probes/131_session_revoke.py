"""Q: can a client end the session behind a session token, so that signing out of an app signs the
token out on the site?

Probe 052 found the session token is the web app's `_session_id` cookie and that every bearer minted
from it renews the session. An app that only forgets the token leaves a live session on the site for
one more window. This looks for a call that ends it: first in the site's own `/spec.json`, then at
the sign-out routes a web app of this kind serves, answered with no cookie and with a cookie no
session holds.

    python probes/131_session_revoke.py           the contract, without a person present
    python probes/131_session_revoke.py --login   opens a launcher approval page in a browser and
                                                  waits for a person to approve it (probe 052), then
                                                  tries each route with that fresh token until one
                                                  ends the session, reading the session and the token
                                                  endpoint after each. Also asks whether a bearer
                                                  minted before sign-out still reads

`--login` never touches `session_token.local.json`: the token it gets lives only in memory and is
signed out by the run. Read-only on site data.
"""
import json
import re
import sys
import time
import uuid
import webbrowser

import requests

import _lib

env = _lib.load_env()
site = env["FPT_API_SITE_URL"].rstrip("/")
LAUNCHER = f"{site}/internal_api/app_session_request"
TOKEN = f"{site}/api/v1/auth/access_token"
SESSION = f"{site}/internal_api/session"
WAIT = 900
rows = []
# Undocumented candidates, in the order --login tries them: the least destructive-looking first.
ROUTES = [("DELETE", "/internal_api/session"), ("POST", "/user/logout"), ("GET", "/user/logout"),
          ("DELETE", "/api/v1/auth/access_token"), ("POST", "/api/v1/auth/revoke")]


def brief(r):
    loc = r.headers.get("location", "")
    return (f"{r.status_code} {r.headers.get('content-type', '')}"
            + (f"  location {loc}" if loc else f"  {r.text.strip().replace(chr(10), ' ')[:300]}"))


def call(method, path, cookie=None, bearer=None):
    h = {"Authorization": f"Bearer {bearer}"} if bearer else {}
    return requests.request(method, f"{site}{path}", cookies={"_session_id": cookie} if cookie else None,
                            headers=h, allow_redirects=False, timeout=30)


def mint(tok):
    return requests.post(TOKEN, data={"grant_type": "session_token", "session_token": tok},
                         headers={"Accept": "application/json"}, timeout=30)


rows.append("=== /spec.json, searched")
spec = _lib.client().get("/spec.json").json()
ops = [(m.upper(), p, v[m]) for p, v in spec["paths"].items()
       for m in v if m.lower() in ("get", "post", "put", "patch", "delete")]
rows.append(f"  {len(spec['paths'])} paths, {len(ops)} operations")
for w in ("revoke", "logout", "log_out", "sign_out", "signout", "invalidate", "session"):
    hits = sorted({f"{m} {p}" for m, p, op in ops if re.search(w, p + json.dumps(op), re.I)})
    rows.append(f"  {w}: {hits or 'nowhere'}")
auth_ops = sorted({f"{m} {p}" for m, p, _ in ops if "/auth" in p})
rows.append(f"  operations under /auth: {auth_ops}")

rows.append("\n=== the routes, no cookie and a cookie no session holds")
for m, p in ROUTES:
    rows.append(f"  {m:6} {p}")
    rows.append(f"     no cookie   -> {brief(call(m, p))}")
    rows.append(f"     random      -> {brief(call(m, p, cookie=uuid.uuid4().hex))}")

if "--login" in sys.argv:
    rows.append("\n=== --login: a fresh session token, then each route until one ends it")
    made = requests.post(LAUNCHER, data={"appName": "sg-groundtruth probe 131",
                                         "machineId": uuid.uuid4().hex}, timeout=30).json()
    sid, url = made["sessionRequestId"], made["url"]
    print(f"Open this page, log in if asked and click approve:\n  {url}\n", flush=True)
    webbrowser.open(url)
    t0, tok = time.time(), None
    while time.time() - t0 < WAIT and not tok:
        r = requests.put(f"{LAUNCHER}/{sid}", timeout=30)
        if r.status_code == 404:
            made = requests.post(LAUNCHER, data={"appName": "sg-groundtruth probe 131",
                                                 "machineId": uuid.uuid4().hex}, timeout=30).json()
            sid, url = made["sessionRequestId"], made["url"]
            print(f"that request expired; approve this one instead:\n  {url}\n", flush=True)
            webbrowser.open(url)
            continue
        tok = (r.json() if r.ok else {}).get("sessionToken")
        if not tok:
            time.sleep(2)
    if not tok:
        rows.append(f"  not approved within {WAIT}s")
    else:
        m0 = mint(tok)
        bearer = m0.json().get("access_token") if m0.ok else None
        rows.append(f"  mint before -> {m0.status_code}; GET /internal_api/session -> "
                    f"{call('GET', '/internal_api/session', cookie=tok).status_code}")
        for m, p in ROUTES:
            r = call(m, p, cookie=tok, bearer=bearer if p.startswith("/api/v1") else None)
            s = call("GET", "/internal_api/session", cookie=tok)
            k = mint(tok)
            rows.append(f"  {m} {p} with the token -> {brief(r)}")
            rows.append(f"     then GET /internal_api/session -> {s.status_code} {s.text.strip()[:120]}")
            rows.append(f"     then mint -> {k.status_code} {k.text.strip()[:300] if not k.ok else '(a bearer)'}")
            if not k.ok and s.status_code == 401:
                b = requests.get(f"{site}/api/v1/entity/projects", params={"page[size]": 1},
                                 headers={"Authorization": f"Bearer {bearer}"}, timeout=30)
                rows.append(f"  session ended by {m} {p}. A bearer minted before it, "
                            f"GET /entity/projects -> {b.status_code}")
                break
        else:
            rows.append("  no route ended the session. It is still live: it ends one window after "
                        "the last mint (probe 052)")

_lib.emit("131_session_revoke", "\n".join(rows), env)
