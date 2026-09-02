"""Q: what does the token endpoint actually return, and how long is a token good for?"""
import requests

import _lib

env = _lib.load_env()
site = env["FPT_API_SITE_URL"].rstrip("/")
FORM = "application/x-www-form-urlencoded"
CREDS = {
    "grant_type": "client_credentials",
    "client_id": env["FPT_API_SCRIPT_NAME"],
    "client_secret": env["FPT_API_API_KEY"],
}


def token(content_type=None):
    h = {"Accept": "application/json"}
    if content_type:
        h["Content-Type"] = content_type
    return requests.post(f"{site}/api/v1/auth/access_token", data=CREDS, headers=h, timeout=30)


r = token()
d = r.json() if r.ok else {}
shape = {k: (f"<{type(v).__name__}, {len(str(v))} chars>" if k.endswith("token") else v) for k, v in d.items()}

probe = _lib.client()
g = probe.get("/entity/projects", params={"fields": "name", "page[size]": 3})
_lib.note_from(g.json() if g.ok else {})

# The charset parameter: two production clients pin the bare media type here, so ask whether the
# parameter is what the endpoint rejects, or only the media type in front of it.
charset = []
for ct in (f"{FORM}; charset=utf-8", f"{FORM};charset=UTF-8", f"{FORM}; charset=bogus", FORM,
           None, "text/plain", "application/json"):
    t = token(ct)
    body = t.json() if t.headers.get("Content-Type", "").startswith("application/") else {}
    detail = f"{sorted(body)}" if t.ok else _lib.dump(body.get("errors", t.text))
    charset.append(f"  Content-Type: {ct!r}\n  -> {t.status_code} {detail}")

actual = (
    f"POST auth -> {r.status_code}\n"
    f"payload keys/values: {_lib.dump(shape)}\n\n"
    f"GET /entity/projects -> {g.status_code}\n"
    f"projects: {[(p['id'], p['attributes']['name']) for p in g.json()['data']] if g.ok else g.text[:200]}\n\n"
    "=== Content-Type on the token endpoint\n" + "\n\n".join(charset)
)

_lib.emit("001_auth", actual, env)
