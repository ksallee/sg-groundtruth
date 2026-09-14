"""Q: does the site answer a CORS preflight, and what may a browser page on another origin call?

A client that runs in a page rather than in a process is bound by what the site's own responses
say. Everything here is read off the response headers of calls that create nothing: `OPTIONS`
preflights, unauthenticated `GET`s, one real token mint and one real `_search`.

Four surfaces, because they are configured by different things: `/api/v1`, the `/internal_api`
endpoints the App Session Launcher lives on (probe 052), and two static web paths a page might
reach for (the status sprite of probe 010 and a stylesheet).

    python probes/062_cors.py
"""
import json

import requests

import _lib

env = _lib.load_env()
site = env["FPT_API_SITE_URL"].rstrip("/")
c = _lib.client()
rows = []

CORS = ("access-control-allow-origin", "access-control-allow-credentials",
        "access-control-allow-methods", "access-control-allow-headers",
        "access-control-max-age", "access-control-expose-headers", "vary")
ORIGIN = "https://example.invalid"
ACRH = "authorization,content-type"
# What a browser lets script read off a response without access-control-expose-headers.
SAFELISTED = {"cache-control", "content-language", "content-type", "expires", "last-modified",
              "pragma"}

# label, method the page would make, url
TARGETS = [
    ("POST /auth/access_token", "POST", f"{site}/api/v1/auth/access_token"),
    ("POST /entity/shots/_search", "POST", f"{site}/api/v1/entity/shots/_search"),
    ("GET /schema", "GET", f"{site}/api/v1/schema"),
    ("GET /", "GET", f"{site}/api/v1"),
    ("POST /internal_api/app_session_request", "POST", f"{site}/internal_api/app_session_request"),
    ("PUT /internal_api/app_session_request/<id>", "PUT",
     f"{site}/internal_api/app_session_request/probe062_not_an_id"),
    ("GET /internal_api/session", "GET", f"{site}/internal_api/session"),
    ("POST /internal_api/session", "POST", f"{site}/internal_api/session"),
    ("GET /images/sg_icon_image_map.png", "GET", f"{site}/images/sg_icon_image_map.png"),
    ("GET /dist/production/stylesheets/login.css", "GET",
     f"{site}/dist/production/stylesheets/login.css"),
]

ORIGINS = [
    ("https://example.invalid", "an https origin the site has never seen"),
    ("http://localhost:5173", "an http origin, the shape a dev server has"),
    ("null", "the literal null a sandboxed or file:// page sends"),
    ("banana", "a nonsense string that is not an origin at all"),
    (site, "the site's own origin"),
]


def cors(r):
    """The response's CORS headers, lowercased, in the order they are worth reading."""
    h = {k.lower(): v for k, v in r.headers.items()}
    return {k: h[k] for k in CORS if k in h}


def preflight(url, method, origin=ORIGIN, acrh=ACRH):
    head = {"Origin": origin} if origin is not None else {}
    if method is not None:
        head["Access-Control-Request-Method"] = method
    if acrh is not None:
        head["Access-Control-Request-Headers"] = acrh
    return requests.options(url, headers=head, timeout=30, allow_redirects=False)


def line(label, r, width=44):
    got = cors(r)
    loc = r.headers.get("location", "")
    rows.append(f"  {label:<{width}} {r.status_code}"
                + (f" -> {loc.replace(site, '<site>')[:60]}" if loc else "")
                + ("" if got else "   no CORS headers"))
    for k, v in got.items():
        rows.append(f"  {'':<{width}}   {k}: {v}")
    return got


# 1. The preflight a browser sends before a credentialed POST, on every surface.
rows.append(f"=== 1. OPTIONS with Origin: {ORIGIN}, Access-Control-Request-Method, "
            f"Access-Control-Request-Headers: {ACRH}")
answers = {}
for label, method, url in TARGETS:
    answers[label] = line(f"{label:<44} ({method})", preflight(url, method), width=52)

# 2. Does it echo, or does it decide? The same preflight from five origins.
rows.append("\n=== 2. the same preflight on POST /entity/shots/_search, one origin at a time")
search = f"{site}/api/v1/entity/shots/_search"
for origin, what in ORIGINS:
    got = cors(preflight(search, "POST", origin=origin))
    shown = origin.replace(site, "<site>")
    rows.append(f"  {shown:<26} {what}")
    rows.append(f"  {'':<26}   allow-origin {got.get('access-control-allow-origin')!r} "
                f"credentials {got.get('access-control-allow-credentials')!r} "
                f"vary {got.get('vary')!r}")

# 3. What the preflight answer depends on, if anything. A preflight a browser accepts has to name
# the method and every requested header; an answer missing allow-origin fails it outright.
rows.append("\n=== 3. preflight variations on POST /entity/shots/_search")
rows.append(f"  {'variation':<50} {'code':<5} {'allow-origin':<25} {'allow-methods':<32} "
            f"allow-headers")
for label, method, acrh in [
        ("Access-Control-Request-Method: GET", "GET", ACRH),
        ("Access-Control-Request-Method: PATCH", "PATCH", ACRH),
        ("Access-Control-Request-Method: DELETE", "DELETE", ACRH),
        ("Access-Control-Request-Method: TRACE", "TRACE", ACRH),
        ("Access-Control-Request-Method: BREW", "BREW", ACRH),
        ("Access-Control-Request-Method: post (lowercase)", "post", ACRH),
        ("Access-Control-Request-Headers: Authorization (cased)", "POST", "Authorization"),
        ("Access-Control-Request-Headers: authorization, content-type (spaced)", "POST",
         "authorization, content-type"),
        ("Access-Control-Request-Headers: x-made-up-header", "POST", "x-made-up-header"),
        ("Access-Control-Request-Headers: authorization,x-made-up-header", "POST",
         "authorization,x-made-up-header"),
        ("no Access-Control-Request-Headers", "POST", None),
        ("no Access-Control-Request-Method", None, ACRH),
        ("neither", None, None)]:
    r = preflight(search, method, acrh=acrh)
    got = cors(r)
    rows.append(f"  {label:<50} {r.status_code:<5} "
                f"{str(got.get('access-control-allow-origin')):<25} "
                f"{str(got.get('access-control-allow-methods')):<32} "
                f"{got.get('access-control-allow-headers')}")
r = preflight(search, "POST", origin=None)
rows.append(f"  {'no Origin at all':<50} {r.status_code:<5} "
            f"{json.dumps(cors(r)) if cors(r) else 'no CORS headers'}")
pf = preflight(search, "POST")
rows.append(f"  body of a preflight answer: {len(pf.content)} bytes, "
            f"content-type {pf.headers.get('content-type')!r}")

# 3b. The requested header names it will and will not sign off on, one at a time.
rows.append("\n=== 3b. one Access-Control-Request-Headers name at a time, POST "
            "/entity/shots/_search")
allowed, refused = [], []
for h in ("authorization", "content-type", "accept", "accept-language", "content-language",
          "cache-control", "if-none-match", "if-match", "range", "x-requested-with",
          "user-agent", "cookie", "referer", "origin", "content-length", "x-made-up-header"):
    got = cors(preflight(search, "POST", acrh=h))
    (allowed if got.get("access-control-allow-headers") else refused).append(h)
rows.append(f"  echoed back in access-control-allow-headers: {allowed}")
rows.append(f"  answered with no CORS headers at all:        {refused}")

# 4. The real calls, with an Origin header on them. Nothing here creates a row.
rows.append(f"\n=== 4. the request itself, with Origin: {ORIGIN}")
O = {"Origin": ORIGIN}

line("GET /api/v1 (no auth)", requests.get(f"{site}/api/v1", headers=O, timeout=30))

tok = requests.post(f"{site}/api/v1/auth/access_token", headers={**O, "Accept": "application/json"},
                    data={"grant_type": "client_credentials",
                          "client_id": env["FPT_API_SCRIPT_NAME"],
                          "client_secret": env["FPT_API_API_KEY"]}, timeout=30)
line("POST /auth/access_token, real credentials", tok)
bad = requests.post(f"{site}/api/v1/auth/access_token", headers={**O, "Accept": "application/json"},
                    data={"grant_type": "client_credentials", "client_id": "probe062",
                          "client_secret": "not-a-key"}, timeout=30)
line("POST /auth/access_token, refused", bad)

HSH = {"Content-Type": "application/vnd+shotgun.api3_hash+json"}
sr = c.post("/entity/shots/_search", headers={**O, **HSH},
            data=json.dumps({"filters": {"logical_operator": "and", "conditions": []},
                             "fields": "code", "page": {"size": 1}}))
line("POST /entity/shots/_search, bearer", sr)
line("POST /entity/shots/_search, Content-Type: application/json",
     c.post("/entity/shots/_search", headers=O,
            json={"filters": [], "fields": "code", "page": {"size": 1}}))
line("GET /schema, bearer", c.get("/schema", headers=O))
line("GET /internal_api/session, no cookie",
     requests.get(f"{site}/internal_api/session", headers=O, timeout=30))
line("PUT /internal_api/app_session_request/<unknown>",
     requests.put(f"{site}/internal_api/app_session_request/probe062_not_an_id", headers=O,
                  timeout=30))
line("GET /images/sg_icon_image_map.png",
     requests.get(f"{site}/images/sg_icon_image_map.png", headers=O, timeout=30,
                  allow_redirects=False))
line("GET /dist/production/stylesheets/login.css",
     requests.get(f"{site}/dist/production/stylesheets/login.css", headers=O, timeout=30,
                  allow_redirects=False))

# 4b. Is the preflight answered by the route or by whatever sits in front of it?
rows.append("\n=== 4b. the same preflight on paths no route serves")
for label, url in (("/api/v1/entity/not_a_type/_search",
                    f"{site}/api/v1/entity/not_a_type/_search"),
                   ("/api/v1/probe062_nothing_here", f"{site}/api/v1/probe062_nothing_here"),
                   ("/probe062_nothing_here", f"{site}/probe062_nothing_here")):
    r = preflight(url, "POST")
    got = cors(r)
    rows.append(f"  OPTIONS {label:<40} {r.status_code} allow-origin "
                f"{got.get('access-control-allow-origin')!r}")

# 4c. `access-control-allow-credentials: true` says the browser may send cookies. What the site
# does with a cookie on /api/v1 is the other half of that.
saved = _lib.ROOT / "session_token.local.json"
if saved.is_file():
    rows.append("\n=== 4c. what a cookie is worth on /api/v1 (the session token of probe 052)")
    ck = {"_session_id": json.loads(saved.read_text())["session_token"]}
    alive = requests.get(f"{site}/internal_api/session", cookies=ck, timeout=30)
    rows.append(f"  GET /internal_api/session, cookie only -> {alive.status_code} "
                f"{'session alive' if alive.ok else alive.text.strip()[:80]}")
    r = requests.get(f"{site}/api/v1/schema", cookies=ck,
                     headers={"Accept": "application/json"}, timeout=30)
    rows.append(f"  GET /api/v1/schema, cookie only, no bearer -> {r.status_code} "
                f"{r.text.strip()[:120]}")
    if not alive.ok:
        rows.append("  the saved session is expired, so this 401 does not separate 'the cookie is "
                    "not accepted here' from 'this cookie is dead'. Re-run after "
                    "probes/052_app_session_launcher.py --login")

# 5. What script could read off the answer it is allowed to make.
rows.append("\n=== 5. response headers on POST /entity/shots/_search that script cannot read")
expose = {h.strip().lower() for h in
          (cors(sr).get("access-control-expose-headers") or "").split(",") if h.strip()}
hidden = sorted(k.lower() for k in sr.headers if k.lower() not in SAFELISTED | expose)
rows.append(f"  access-control-expose-headers: "
            f"{cors(sr).get('access-control-expose-headers') or 'absent'}")
rows.append(f"  hidden from script: {hidden}")

_lib.emit("062_cors", "\n".join(rows), env)
