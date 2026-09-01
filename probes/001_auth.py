"""Q: what does the token endpoint actually return, and how long is a token good for?"""
import requests

import _lib

env = _lib.load_env()
site = env["FPT_API_SITE_URL"].rstrip("/")

r = requests.post(
    f"{site}/api/v1/auth/access_token",
    data={
        "grant_type": "client_credentials",
        "client_id": env["FPT_API_SCRIPT_NAME"],
        "client_secret": env["FPT_API_API_KEY"],
    },
    headers={"Accept": "application/json"},
    timeout=30,
)
d = r.json() if r.ok else {}
shape = {k: (f"<{type(v).__name__}, {len(str(v))} chars>" if k.endswith("token") else v) for k, v in d.items()}

probe = _lib.client()
g = probe.get("/entity/projects", params={"fields": "name", "page[size]": 3})

actual = (
    f"POST auth -> {r.status_code}\n"
    f"payload keys/values: {_lib.dump(shape)}\n\n"
    f"GET /entity/projects -> {g.status_code}\n"
    f"projects: {[(p['id'], p['attributes']['name']) for p in g.json()['data']] if g.ok else g.text[:200]}"
)

_lib.record(
    "001_auth",
    "POST /api/v1/auth/access_token  +  GET /api/v1/entity/projects",
    "client_credentials with script name/key returns a bearer token; expires_in documented as 600s.",
    actual,
    "client_credentials works; token lives 600s; refresh_token returned but the client re-auths instead.",
    env,
    tags=("auth", "client", "token"),
)
