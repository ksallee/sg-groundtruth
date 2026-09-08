"""Q: can a client with only `requests` obtain a session token through the App Session Launcher, and
what is that token worth at the REST token endpoint?

**This probe needs a person.** The launcher hands out a session token only after someone logged into
the site in a browser approves the request, so `--login` opens a page in your browser and waits for
you to click approve. Nothing here can approve it for you, and a run without `--login` measures the
contract only, never a token.

Probe 027 found the token endpoint accepts `grant_type=session_token` and the root document advertises
`authentication_app_session_launcher_enabled`, and stopped there: obtaining a session token needed the
launcher. This measures the launcher itself, endpoint by endpoint, without Toolkit. Everything the
site wants is read off its own 400s, which name the missing parameters.

Three modes, all read-only on site data. Nothing here creates an entity row.

    python probes/052_app_session_launcher.py            the contract, without a person present
    python probes/052_app_session_launcher.py --login    also opens the approval URL and waits for a
                                                         person to approve it in a browser, then spends
                                                         the session token at the token endpoint and
                                                         writes it to session_token.local.json
    python probes/052_app_session_launcher.py --check    re-spends the saved session token and reads the
                                                         session behind it, to measure how long a session
                                                         lives and what keeps it alive. Run it again hours
                                                         and days later
    python probes/052_app_session_launcher.py --expiry   polls a request nobody approves until the site
                                                         forgets it, to time how long a pending one lives

`session_token.local.json` is gitignored (`*.local.json`) and is a credential: it authenticates as
the person who approved it.
"""
import base64
import json
import sys
import time
import uuid
import webbrowser
from pathlib import Path

import requests

import _lib

env = _lib.load_env()
site = env["FPT_API_SITE_URL"].rstrip("/")
LAUNCHER = f"{site}/internal_api/app_session_request"
TOKEN = f"{site}/api/v1/auth/access_token"
SAVED = _lib.ROOT / "session_token.local.json"
APP = "sg-groundtruth probe 052"
WAIT = 900          # seconds a person gets to approve, across as many requests as that takes
rows = []


def show(label, r):
    """Status, content type and the whole body. An error body is the contract; never trim it."""
    loc = r.headers.get("location", "")
    rows.append(f"  {label} -> {r.status_code} {r.headers.get('content-type', '')}"
                + (f"  location {loc}" if loc else ""))
    rows.append(f"     {r.text.strip()[:400]}")
    return r


def claims(tok):
    """The middle segment of the bearer, decoded and never verified (probe 027)."""
    p = tok.split(".")[1]
    return json.loads(base64.urlsafe_b64decode(p + "=" * (-len(p) % 4)))


def mint(**data):
    return requests.post(TOKEN, data=data, headers={"Accept": "application/json"}, timeout=30)


def spend(session_token, label):
    """One access token from a session token, and what the bearer says about who it is."""
    r = mint(grant_type="session_token", session_token=session_token)
    if not r.ok:
        rows.append(f"  {label}: {r.status_code} {r.text.strip()[:300]}")
        return None
    d = r.json()
    cl = claims(d["access_token"])
    rows.append(f"  {label}: 200 expires_in {d.get('expires_in')} refresh_token "
                f"{'present' if d.get('refresh_token') else 'absent'} "
                f"claims user={cl.get('user')} auth_type={cl.get('auth_type')!r} "
                f"sudo_as_login={cl.get('sudo_as_login')!r} session_uuid="
                f"{'set' if cl.get('session_uuid') else None}")
    return d, cl


def session_status(session_token, label):
    """What the site says about the session behind a token, and what keeps it alive.

    The web app's own session checker reads `GET /internal_api/session` and renews with `POST`. The
    session token is that page's `_session_id` cookie, so the same two calls answer for a client.
    """
    S = f"{site}/internal_api/session"
    c = {"_session_id": session_token}
    rows.append(f"\n=== {label}: GET /internal_api/session with the session token as _session_id")
    r = requests.get(S, cookies=c, timeout=30)
    rows.append(f"  cookie -> {r.status_code} {r.text.strip()[:400]}")
    if not r.ok:
        return None
    d0 = r.json()
    now = time.time()
    for k in ("app", "license"):
        v = d0.get(k) or {}
        rows.append(f"  {k}: created {(now - v.get('createdAt', now)) / 3600:.1f}h ago, expires in "
                    f"{(v.get('expiresAt', now) - now) / 3600:.1f}h")
    rows.append(f"  expirationReason {d0.get('expirationReason')!r} expired {d0.get('expired')!r} "
                f"notifyAt {(d0.get('notifyAt', now) - now) / 3600:.1f}h from now")
    # What counts as activity: a second GET, a bearer minted from the token, and the renew call. A
    # mint within 300s of the last move reads as no move; the two POSTs move it every time.
    d1 = requests.get(S, cookies=c, timeout=30).json()
    rows.append(f"  a second GET moves expiresAt: {d1['expiresAt'] != d0['expiresAt']}")
    mint(grant_type="session_token", session_token=session_token)
    d2 = requests.get(S, cookies=c, timeout=30).json()
    rows.append(f"  minting a bearer from the session token moves expiresAt: {d2['expiresAt'] != d1['expiresAt']} "
                f"(+{d2['expiresAt'] - d1['expiresAt']}s)")
    p = requests.post(S, cookies=c, timeout=30)
    d3 = requests.get(S, cookies=c, timeout=30).json()
    rows.append(f"  POST /internal_api/session -> {p.status_code} {p.text.strip()[:100]}; moves expiresAt: "
                f"{d3['expiresAt'] != d2['expiresAt']}")
    p = requests.post(f"{site}/internal_api/autodesk_identity/license_renewal", cookies=c, timeout=30)
    d4 = requests.get(S, cookies=c, timeout=30).json()
    rows.append(f"  POST /internal_api/autodesk_identity/license_renewal -> {p.status_code} "
                f"{p.text.strip()[:100]}; moves license.expiresAt: "
                f"{d4['license']['expiresAt'] != d3['license']['expiresAt']}")
    rows.append(f"  no cookie -> {requests.get(S, timeout=30).status_code}; "
                f"POST no cookie -> {requests.post(S, timeout=30).status_code}")
    return d4


# 1. What the root document says before any token exists.
root = requests.get(f"{site}/api/v1", timeout=30).json()["data"]
rows.append("=== 1. GET /api/v1")
for k in ("user_authentication_method", "unified_login_flow_enabled",
          "authentication_app_session_launcher_enabled", "shotgun_version"):
    rows.append(f"  {k}: {root.get(k)!r}")

# 2. The create call, read off its own refusals. No token, no cookie.
rows.append("\n=== 2. POST /internal_api/app_session_request  (no Authorization, no cookie)")
show("GET  same path", requests.get(LAUNCHER, timeout=30))
show("POST no body", requests.post(LAUNCHER, timeout=30))
show("POST form appName only", requests.post(LAUNCHER, data={"appName": APP}, timeout=30))
machine = uuid.uuid4().hex
made = show("POST form appName+machineId",
            requests.post(LAUNCHER, data={"appName": APP, "machineId": machine}, timeout=30)).json()
show("POST json appName+machineId",
     requests.post(LAUNCHER, json={"appName": APP, "machineId": machine + "-json"}, timeout=30))
sid, url = made["sessionRequestId"], made["url"]
rows.append(f"  response keys {sorted(made)}; url path {url.replace(site, '')}")

# 3. The poll call, on a request nobody has approved.
rows.append("\n=== 3. PUT /internal_api/app_session_request/<sessionRequestId>  (pending)")
show("PUT  no body", requests.put(f"{LAUNCHER}/{sid}", timeout=30))
show("PUT  wrong machineId", requests.put(f"{LAUNCHER}/{sid}", data={"machineId": "nope"}, timeout=30))
show("GET  same path", requests.get(f"{LAUNCHER}/{sid}", timeout=30))
show("POST same path", requests.post(f"{LAUNCHER}/{sid}", timeout=30))
show("PUT  unknown id", requests.put(f"{LAUNCHER}/probe052_not_an_id", timeout=30))
show("GET  the browser url, no cookie", requests.get(url, timeout=30, allow_redirects=False))

# 4. A person approves it. Only with --login: it needs a browser and someone logged in.
if "--login" in sys.argv:
    rows.append(f"\n=== 4. approval, polled every 2s for up to {WAIT}s")
    print("A browser page is opening. Log in as yourself if asked, then click approve. Nothing\n"
          f"continues until you do:\n  {url}\n", flush=True)
    webbrowser.open(url)
    t0, got, renewed = time.time(), None, 0
    while time.time() - t0 < WAIT:
        r = requests.put(f"{LAUNCHER}/{sid}", timeout=30)
        if r.status_code == 404:
            # A pending request is forgotten by the site after a few minutes (--expiry times it). The
            # person then needs a fresh URL, which is what a client has to do too.
            made = requests.post(LAUNCHER, data={"appName": APP, "machineId": machine}, timeout=30).json()
            sid, url, renewed = made["sessionRequestId"], made["url"], renewed + 1
            rows.append(f"  request forgotten after {time.time() - t0:.0f}s; new one issued")
            print(f"the previous request expired; open and approve this one instead:\n  {url}\n", flush=True)
            webbrowser.open(url)
            continue
        d = r.json() if r.ok else {}
        if r.status_code != 200 or d.get("approved"):
            got = r
            break
        time.sleep(2)
    if got is None:
        rows.append(f"  not approved within {WAIT}s over {renewed + 1} request(s); last answer "
                    f"{r.status_code} {r.text[:200]}")
        d = {}
    else:
        d = got.json() if got.ok else {}
        rows.append(f"  approved after {time.time() - t0:.0f}s -> {got.status_code} keys {sorted(d)}")
        rows.append("     " + json.dumps({k: (v if k in ("approved", "userLogin") else "<value>")
                                          for k, v in d.items()}))
        _lib.note_from(d)
        show("PUT  again, after approval", requests.put(f"{LAUNCHER}/{sid}", timeout=30))
    if d:
        tok = d.get("sessionToken") or d.get("session_token") or ""
        if tok:
            rows.append("\n=== 5. the session token at POST /api/v1/auth/access_token")
            first = spend(tok, "grant_type=session_token")
            spend(tok, "same session token, second time")
            if first:
                # Who the person is, read from the row the claim names.
                who = first[1].get("user") or {}
                slug = "human_users" if who.get("type") == "HumanUser" else "api_users"
                r = requests.get(f"{site}/api/v1/entity/{slug}/{who.get('id')}",
                                 params={"fields": "login,permission_rule_set"},
                                 headers={"Authorization": f"Bearer {first[0]['access_token']}",
                                          "Accept": "application/json"}, timeout=30)
                body = r.json().get("data", {}) if r.ok else r.text[:200]
                if isinstance(body, dict):
                    _lib.note_from(body)
                    prs = ((body.get("relationships") or {}).get("permission_rule_set") or {}).get("data")
                    rows.append(f"  GET /entity/{slug}/<id> -> {r.status_code} permission_rule_set {prs}")
                else:
                    rows.append(f"  GET /entity/{slug}/<id> -> {r.status_code} {body}")
                # Does the refresh grant work on a token minted from a session?
                rt = first[0].get("refresh_token")
                if rt:
                    r = mint(grant_type="refresh_token", refresh_token=rt)
                    rows.append(f"  grant_type=refresh_token -> {r.status_code} "
                                f"{'expires_in ' + str(r.json().get('expires_in')) if r.ok else r.text[:200]}")
            session_status(tok, "5c. the session behind the token, minutes after approval")
            SAVED.write_text(json.dumps({"session_token": tok, "session_request_id": sid,
                                         "approved_at": time.time(),
                                         "approved_at_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}))
            rows.append(f"  saved to {SAVED.name} for --check")

# 5b. How long a request nobody approves stays answerable.
if "--expiry" in sys.argv:
    rows.append("\n=== 5b. --expiry: a pending request, polled every 15s until the site forgets it")
    made = requests.post(LAUNCHER, data={"appName": APP, "machineId": machine + "-expiry"}, timeout=30).json()
    t0 = time.time()
    while time.time() - t0 < 1200:
        r = requests.put(f"{LAUNCHER}/{made['sessionRequestId']}", timeout=30)
        if r.status_code != 200:
            rows.append(f"  {r.status_code} {r.text.strip()[:200]} after {time.time() - t0:.0f}s")
            break
        time.sleep(15)
    else:
        rows.append("  still pending after 1200s")

# 6. A saved session, hours or days later.
if "--check" in sys.argv:
    rows.append("\n=== 6. --check: the saved session token, re-spent")
    if not SAVED.is_file():
        rows.append("  nothing saved; run --login first")
    else:
        s = json.loads(SAVED.read_text())
        age = time.time() - s["approved_at"]
        rows.append(f"  approved {age / 3600:.1f}h ago ({s['approved_at_iso']})")
        spend(s["session_token"], "grant_type=session_token")
        session_status(s["session_token"], f"6b. the session, {age / 3600:.1f}h after approval")
        show("PUT  the approved request id, again",
             requests.put(f"{LAUNCHER}/{s['session_request_id']}", timeout=30))
        s["last_check"] = time.time()
        SAVED.write_text(json.dumps(s))

_lib.emit("052_app_session_launcher", "\n".join(rows), env)
