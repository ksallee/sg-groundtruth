"""Q: what does a client get back when it spends a session token left idle past the site's window,
and can a client read that window?

Probe 052 measured that each bearer minted from a session token moves the session's expiry to now
plus the site window (one day on the probed site), and left the idle case unmeasured: it waits on
time. An offline capture app comes back from a multi-day shoot holding exactly such a token.
Writing the window is not attempted: probes 047 and 114 found `PUT /preferences/update` refused
with code 111 for every preference.

    python probes/126_session_idle.py           what can be measured now: the refusal for a token
                                                that was never valid, at both calls a client makes,
                                                and whether any read exposes the window
    python probes/126_session_idle.py --idle    reads `session_token.local.json`, written by
                                                `052_app_session_launcher.py --login`, and spends it.
                                                Run it more than one window after that login and
                                                after nothing else has spent the token: 052 --check
                                                spends it, which renews the session and voids the test

The saved file is a credential and gitignored (`*.local.json`). Nothing here prints it.
Read-only on site data.
"""
import json
import sys
import time
import uuid

import requests

import _lib

env = _lib.load_env()
site = env["FPT_API_SITE_URL"].rstrip("/")
TOKEN = f"{site}/api/v1/auth/access_token"
SESSION = f"{site}/internal_api/session"
SAVED = _lib.ROOT / "session_token.local.json"
rows = []


def envelope(r):
    """`errors[]` (every /api/v1 call) or bare `{"message": ...}` (/internal_api, probe 052)."""
    try:
        d = r.json()
    except ValueError:
        return "not JSON"
    if isinstance(d, dict) and isinstance(d.get("errors"), list):
        e = d["errors"][0] if d["errors"] else {}
        return f"errors[] status={e.get('status')} code={e.get('code')}"
    return f"bare, keys {sorted(d) if isinstance(d, dict) else type(d).__name__}"


def show(label, r):
    rows.append(f"  {label} -> {r.status_code} {r.headers.get('content-type', '')}")
    rows.append(f"     {r.text.strip()[:500]}")
    if not r.ok:
        rows.append(f"     envelope: {envelope(r)}")
    return r


def mint(tok):
    return requests.post(TOKEN, data={"grant_type": "session_token", "session_token": tok},
                         headers={"Accept": "application/json"}, timeout=30)


rows.append("===== a session token that was never valid")
for label, tok in (("32 zeros", "0" * 32), ("empty", ""), ("32 random hex", uuid.uuid4().hex)):
    show(f"POST /auth/access_token grant_type=session_token, {label}", mint(tok))
show("GET /internal_api/session, cookie _session_id=<32 random hex>",
     requests.get(SESSION, cookies={"_session_id": uuid.uuid4().hex}, timeout=30))

rows.append("\n===== is the window readable through the API")
c = _lib.client()
p = c.get("/preferences", params={"prefs": "*"})
keys = sorted((p.json().get("data") or {}).keys())
rows.append(f"  GET /preferences?prefs=* -> {p.status_code}, {len(keys)} keys: {keys}")
rows.append(f"  keys naming session, expiry or timeout: "
            f"{[k for k in keys if any(w in k for w in ('session', 'expir', 'timeout'))]}")
for name in ("user_session_expiry", "session_expiry", "api_session_expiry", "session_timeout"):
    r = c.get("/preferences", params={"prefs": name})
    rows.append(f"  GET /preferences?prefs={name} -> {r.status_code} data={json.dumps(r.json().get('data'))}")
root = requests.get(f"{site}/api/v1", timeout=30).json()["data"]
rows.append(f"  GET /api/v1 keys naming session or expiry: "
            f"{[k for k in root if 'session' in k or 'expir' in k]}")

if "--idle" in sys.argv:
    rows.append("\n===== --idle: the token saved by 052 --login")
    if not SAVED.is_file():
        rows.append("  nothing saved; run probes/052_app_session_launcher.py --login first")
    else:
        s = json.loads(SAVED.read_text())
        last = max(s.get("approved_at", 0), s.get("last_check", 0))
        rows.append(f"  approved {s.get('approved_at_iso')}; last spent "
                    f"{(time.time() - last) / 3600:.1f}h ago"
                    + ("; 052 --check has spent it since login" if s.get("last_check") else ""))
        g = show("GET /internal_api/session (052: a GET does not renew)",
                 requests.get(SESSION, cookies={"_session_id": s["session_token"]}, timeout=30))
        if g.ok:
            d = g.json()
            rows.append(f"     expired={d.get('expired')!r} expirationReason={d.get('expirationReason')!r} "
                        f"expiresAt {(d.get('expiresAt', time.time()) - time.time()) / 3600:.1f}h from now")
        m = mint(s["session_token"])
        rows.append(f"  POST /auth/access_token grant_type=session_token -> {m.status_code}")
        rows.append(f"     {m.text.strip()[:500] if not m.ok else '(a bearer; not printed)'}")
        if not m.ok:
            rows.append(f"     envelope: {envelope(m)}; same as a never-valid token above if both read "
                        f"errors[] status=400 code=102")
        show("GET /internal_api/session again",
             requests.get(SESSION, cookies={"_session_id": s["session_token"]}, timeout=30))
        s["idle_check"] = time.time()
        SAVED.write_text(json.dumps(s))

_lib.emit("126_session_idle", "\n".join(rows), env)
