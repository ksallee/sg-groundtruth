"""Q: what does `/api/v1` answer a bearer past its `exp`, and a bearer the site never issued?

sg-onset holds a bearer across a flaky connection and needs to tell "mint a new one" from every
other failure. Probe 001 measured `expires_in` 600 and never spent a token past it. This mints one
bearer, decodes its `exp` (probe 027), spends it just before and just after, and sends forged ones
next to it: a random string, the real token with its signature altered, the real token with its
payload altered, an empty bearer, and no Authorization header. Each answer is printed whole:
status, the `errors[]` object, and every header that names auth.

Read-only. Takes about 11 minutes: it waits past the token's `exp`.

    python probes/133_bearer_expiry.py
"""
import base64
import json
import secrets
import time

import requests

import _lib

env = _lib.load_env()
c = _lib.client()
SITE = c.site
rows = []
AUTHY = ("www-authenticate", "content-type", "x-request-id")


def out(s=""):
    rows.append(str(s))


def claims(tok):
    p = tok.split(".")[1]
    return json.loads(base64.urlsafe_b64decode(p + "=" * (-len(p) % 4)))


def b64(d):
    return base64.urlsafe_b64encode(json.dumps(d, separators=(",", ":")).encode()).rstrip(b"=").decode()


def spend(label, tok, method="GET", path="/entity/projects", **kw):
    h = {"Accept": "application/json"}
    if tok is not None:
        h["Authorization"] = f"Bearer {tok}" if tok != "<raw>" else "Bearer"
    r = requests.request(method, f"{SITE}/api/v1{path}", headers=h, timeout=30,
                         params={"page[size]": 1, "fields": "id"} if method == "GET" else None, **kw)
    hd = {k.lower(): v for k, v in r.headers.items()}
    out(f"  {label}: {method} {path} -> {r.status_code}")
    for k in AUTHY:
        if k in hd and k != "x-request-id":
            out(f"      {k}: {hd[k]}")
    if not r.ok:
        out(f"      body: {r.text[:600]}")
    return r


tok_resp = requests.post(f"{SITE}/api/v1/auth/access_token", data={
    "grant_type": "client_credentials", "client_id": env["FPT_API_SCRIPT_NAME"],
    "client_secret": env["FPT_API_API_KEY"]}, headers={"Accept": "application/json"}, timeout=30).json()
tok = tok_resp["access_token"]
cl = claims(tok)
minted = time.time()
out(f"===== minted: expires_in {tok_resp['expires_in']}; exp - iat = {cl['exp'] - cl['iat']} s; "
    f"iat vs local clock {cl['iat'] - minted:+.0f} s")

h, p, s = tok.split(".")
forged_sig = f"{h}.{p}.{s[:-4]}{'AAAA' if not s.endswith('AAAA') else 'BBBB'}"
forged_payload = f"{h}.{b64({**cl, 'exp': cl['exp'] + 86400})}.{s}"
random_jwt = f"{b64({'alg': 'HS256'})}.{b64({**cl, 'jti': secrets.token_hex(8)})}.{secrets.token_urlsafe(32)}"

out("\n===== fresh token, and bearers the site never issued")
spend("fresh token", tok)
spend("random string, 40 chars", secrets.token_urlsafe(30))
spend("real header and payload, signature altered", forged_sig)
spend("real signature, payload altered (exp + 1 day)", forged_payload)
spend("JWT-shaped, random signature", random_jwt)
spend("'Authorization: Bearer' with no token", "<raw>")
spend("no Authorization header", None)
spend("random string on POST _search", secrets.token_urlsafe(30), "POST", "/entity/projects/_search",
      json={"filters": [], "fields": ["id"]}, )
spend("random string on GET /api/v1 (the root, public)", secrets.token_urlsafe(30), path="")

wait = cl["exp"] - time.time() - 20
out(f"\n===== waiting {wait:.0f} s to 20 s before exp")
time.sleep(max(0, wait))
spend(f"same token at exp - {cl['exp'] - time.time():.0f} s", tok)
time.sleep(max(0, cl["exp"] - time.time() + 5))
out(f"\n===== past exp")
spend(f"same token at exp + {time.time() - cl['exp']:.0f} s", tok)
spend("same token on POST _search", tok, "POST", "/entity/projects/_search",
      json={"filters": [], "fields": ["id"]})
spend("same token on PUT (a write; no row named exists)", tok, "PUT", "/entity/projects/999999999",
      json={"name": "x"})
time.sleep(60)
spend(f"same token at exp + {time.time() - cl['exp']:.0f} s", tok)

_lib.emit("133_bearer_expiry", "\n".join(rows), env)
