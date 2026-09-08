"""Q: who can authenticate, and what does the caller's permission level change about what it reads?

Every finding in this corpus was measured by one script user. The API is the same for everyone; the
visibility is not. This asks which grants the token endpoint accepts besides client_credentials (probe
001), whether a caller can discover its own identity and permission level, and what the permission model
itself exposes to a reader.

Read-only. The credentials sent for the non-client_credentials grants are deliberately fake: the question
is which grant is *accepted*, not whether a password works.
"""
import base64
import json
from collections import Counter

import requests

import _lib

env = _lib.load_env()
c = _lib.client()
site = env["FPT_API_SITE_URL"].rstrip("/")
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
SCRIPT = env["FPT_API_SCRIPT_NAME"]
FAKE = "probe_027_not_a_real_value"
rows = []


def token(**data):
    return requests.post(f"{site}/api/v1/auth/access_token", data=data,
                         headers={"Accept": "application/json"}, timeout=30)


def err(r):
    """The whole errors[] object, source included. Trimming here loses the enumeration."""
    try:
        return json.dumps(r.json().get("errors", r.json()))
    except ValueError:
        return r.text[:300]


def claims(tok):
    """The bearer string is three dot-separated segments. Read the middle one; never verify it."""
    p = tok.split(".")[1]
    return json.loads(base64.urlsafe_b64decode(p + "=" * (-len(p) % 4)))


# 1. What the site says about its own auth before anyone authenticates.
root = c.get("/").json()["data"]
rows.append("=== 1. GET /api/v1  (site auth configuration, no filtering)")
for k in ("user_authentication_method", "unified_login_flow_enabled",
          "authentication_app_session_launcher_enabled"):
    rows.append(f"  {k}: {root.get(k)!r}")

# 2. Which grant types the endpoint accepts. Fake credentials throughout.
rows.append("\n=== 2. grant_type on POST /api/v1/auth/access_token")
GRANTS = [
    ("client_credentials", {"client_id": SCRIPT, "client_secret": env["FPT_API_API_KEY"]}),
    ("client_credentials (wrong secret)", {"client_id": SCRIPT, "client_secret": FAKE}),
    ("password", {"username": FAKE, "password": FAKE}),
    ("password (no arguments)", {}),
    ("session_token", {"session_token": FAKE}),
    ("session_token (no arguments)", {}),
    ("refresh_token", {"refresh_token": FAKE}),
    ("authorization_code", {"code": FAKE, "client_id": FAKE, "client_secret": FAKE,
                            "redirect_uri": "https://example.invalid/cb"}),
    ("implicit", {}),
    ("urn:ietf:params:oauth:grant-type:device_code", {"device_code": FAKE}),
    ("", {}),
    ("client_credentials_typo", {"client_id": SCRIPT, "client_secret": FAKE}),
]
for label, extra in GRANTS:
    grant = label.split(" ")[0]
    r = token(grant_type=grant, **extra)
    rows.append(f"  {label!r} -> {r.status_code} {'ok' if r.ok else err(r)}")

# 3. What the caller can learn about itself.
rows.append("\n=== 3. who am I")
for p in ("/me", "/auth/me", "/session", "/auth/session", "/users/me",
          "/entity/human_users/me", "/entity/api_users/me"):
    r = c.get(p)
    rows.append(f"  GET {p} -> {r.status_code} {err(r) if not r.ok else 'ok'}")

good = token(grant_type="client_credentials", client_id=SCRIPT, client_secret=env["FPT_API_API_KEY"])
payload = claims(good.json()["access_token"])
host_keys = ("iss", "aud")
shown = {k: ("<site host>" if k in host_keys else v) for k, v in payload.items()
         if k not in ("jti", "exp", "iat")}
rows.append(f"  bearer token segments: {[len(s) for s in good.json()['access_token'].split('.')]}"
            f"  header {base64.urlsafe_b64decode(good.json()['access_token'].split('.')[0] + '==').decode()}")
rows.append(f"  token claims (jti/exp/iat cut): {json.dumps(shown)}")

me = c.get(f"/entity/api_users/{payload['user']['id']}",
           params={"fields": "firstname,lastname,permission_rule_set,projects"})
_lib.note_from(me.json())
rows.append(f"  GET /entity/api_users/{payload['user']['id']} (id from the claim) -> {me.status_code}")
if me.ok:
    a = me.json()["data"]
    rel = a["relationships"]
    rows.append(f"    firstname {a['attributes']['firstname']!r}  "
                f"permission_rule_set {rel['permission_rule_set']['data']}  "
                f"projects {rel['projects']['data']}")

byname = c.post("/entity/api_users/_search", headers=ARR,
                json={"filters": [["firstname", "is", SCRIPT]], "fields": ["firstname"]})
_lib.note_from(byname.json())
rows.append(f"  POST /entity/api_users/_search firstname is <script name> -> {byname.status_code} "
            f"{[x['id'] for x in byname.json().get('data', [])]}")

# 4. What the permission model exposes.
rows.append("\n=== 4. the permission model")
for t in ("permissions", "permission_rules", "roles"):
    r = c.get(f"/entity/{t}")
    rows.append(f"  GET /entity/{t} -> {r.status_code} {err(r) if not r.ok else 'ok'}")
sch = c.get("/schema/PermissionRuleSet/fields").json()["data"]
rows.append(f"  /schema/PermissionRuleSet/fields -> {len(sch)} fields, "
            f"{sum(1 for f in sch.values() if f['editable']['value'])} editable: {sorted(sch)}")

sets = c.get("/entity/permission_rule_sets",
             params={"fields": "code,display_name,entity_type", "page[size]": 500}).json()["data"]
_lib.note_from(sets)
rows.append(f"  /entity/permission_rule_sets -> {len(sets)} rows")
for s in sets:
    at = s["attributes"]
    rows.append(f"    {s['id']:>3}  {at['entity_type']:<30} {at['code']}")

users = c.get("/entity/human_users",
              params={"fields": "login,permission_rule_set,groups", "page[size]": 500}).json()["data"]
_lib.note_from(users)
tally = Counter((u["relationships"]["permission_rule_set"]["data"] or {}).get("name") for u in users)
rows.append(f"  /entity/human_users -> {len(users)} rows, permission_rule_set: {dict(tally)}")
scripts = c.get("/entity/api_users",
                params={"fields": "firstname,permission_rule_set", "page[size]": 500}).json()["data"]
_lib.note_from(scripts)
stally = Counter((u["relationships"]["permission_rule_set"]["data"] or {}).get("name") for u in scripts)
rows.append(f"  /entity/api_users   -> {len(scripts)} rows, permission_rule_set: {dict(stally)}")
groups = c.get("/entity/groups", params={"fields": "code,users", "page[size]": 500}).json()["data"]
_lib.note_from(groups)
rows.append(f"  /entity/groups      -> {len(groups)} rows, "
            f"{[(g['id'], len(g['relationships']['users']['data'] or [])) for g in groups]}")

hu = c.get("/schema/HumanUser/fields").json()["data"]
rows.append("  HumanUser fields that decide visibility: "
            f"{sorted(k for k in hu if k in ('permission_rule_set', 'groups', 'projects', 'sg_status_list'))}")
rows.append(f"  HumanUser.can_impersonate_this_user present: {'can_impersonate_this_user' in hu}"
            f", editable {hu.get('can_impersonate_this_user', {}).get('editable', {}).get('value')}")

# 5. Impersonation. `/spec.json` declares it as an OAuth2 scope on both grants, not a body field:
#    "scopes": {"sudo_as_login:{user_login}": "Sudo to another users"}.
#
#    Subjects are discovered, never named here: a login in committed source is site data, and the
#    site the probe runs on decides which permission levels exist to compare.
rows.append("\n=== 5. sudo_as_login")
spec = requests.get(f"{site}/api/v1/spec.json", timeout=30)
flows = spec.json().get("components", {}).get("securitySchemes", {}).get("bearerAuth", {}).get("flows", {})
rows.append(f"  /spec.json bearerAuth flows {sorted(flows)}, "
            f"scopes {sorted({k for f in flows.values() for k in (f.get('scopes') or {})})}")

cands = c.post("/entity/human_users/_search", headers=ARR,
               json={"filters": [["can_impersonate_this_user", "is", True],
                                 ["sg_status_list", "is", "act"]],
                     "fields": "login,permission_rule_set", "page": {"size": 200}})
_lib.note_from(cands.json())
by_set = {}
for u in cands.json().get("data", []):
    name = (u["relationships"]["permission_rule_set"]["data"] or {}).get("name")
    by_set.setdefault(name, u["attributes"]["login"])
rows.append(f"  active + can_impersonate_this_user, by permission_rule_set: "
            f"{ {k: '<login>' for k in sorted(by_set)} }")

admin_login = by_set.get("Admin")
other = next((v for k, v in sorted(by_set.items()) if k != "Admin"), None)
other_set = next((k for k in sorted(by_set) if k != "Admin"), None)

# The two forms, on the same active target: the body field the API ignores, and the scope it reads.
if admin_login:
    for label, extra in (("sudo_as_login=<login> (body field)", {"sudo_as_login": admin_login}),
                         ("scope=sudo_as_login:<login>", {"scope": f"sudo_as_login:{admin_login}"})):
        r = token(grant_type="client_credentials", client_id=SCRIPT,
                  client_secret=env["FPT_API_API_KEY"], **extra)
        got = claims(r.json()["access_token"]) if r.ok else None
        rows.append(f"  {label} -> {r.status_code} "
                    + (f"user {got['user']} sudo_as_login {got.get('sudo_as_login') and '<login>'!r}"
                       if got else err(r)))

# Targets the scope refuses, so the failure shapes are on the record too.
dead = c.post("/entity/human_users/_search", headers=ARR,
              json={"filters": [["can_impersonate_this_user", "is", True],
                                ["sg_status_list", "is_not", "act"]],
                    "fields": "login", "page": {"size": 1}})
_lib.note_from(dead.json())
off = c.post("/entity/human_users/_search", headers=ARR,
             json={"filters": [["can_impersonate_this_user", "is", False],
                               ["sg_status_list", "is", "act"]],
                   "fields": "login", "page": {"size": 1}})
_lib.note_from(off.json())
for label, login in (("inactive target", (dead.json().get("data") or [{}])[0]
                      .get("attributes", {}).get("login")),
                     ("target with the flag off", (off.json().get("data") or [{}])[0]
                      .get("attributes", {}).get("login")),
                     ("unknown target", FAKE)):
    if not login:
        continue
    r = token(grant_type="client_credentials", client_id=SCRIPT,
              client_secret=env["FPT_API_API_KEY"], scope=f"sudo_as_login:{login}")
    # The API echoes the login back inside the message. A login is not an email, so the shared
    # scrubber cannot catch it; the probe knows what it sent and replaces it here.
    rows.append(f"  scope, {label} -> {r.status_code} "
                f"{(err(r) if not r.ok else 'ok').replace(login, '<login>')}")


def as_user(login):
    """A bearer acting as one HumanUser, or None where the site refused."""
    r = token(grant_type="client_credentials", client_id=SCRIPT,
              client_secret=env["FPT_API_API_KEY"], scope=f"sudo_as_login:{login}")
    return r.json()["access_token"] if r.ok else None


def get_as(tok, path, **params):
    return requests.get(f"{site}/api/v1{path}", timeout=60,
                        headers={"Authorization": f"Bearer {tok}", "Accept": "application/json"},
                        params=params or None)


# 6. What the level actually changes. The corpus was measured by one script user in api_admin and
#    says a lower level "may see fewer rows and fewer fields"; both halves are now measured.
rows.append("\n=== 6. what a permission level changes")
levels = [("script", None)] + [(k, v) for k, v in (("Admin", admin_login), (other_set, other)) if v]
toks = {k: (good.json()["access_token"] if v is None else as_user(v)) for k, v in levels}
toks = {k: t for k, t in toks.items() if t}
if len(toks) < 2:
    rows.append("  only one caller available on this site; the comparison was not measured here")
else:
    ENTS = ["projects", "human_users", "api_users", "versions", "shots", "published_files", "notes"]
    for ent in ENTS:
        cells = []
        for k, t in toks.items():
            r = get_as(t, f"/entity/{ent}", **{"page[size]": 200})
            cells.append(f"{k}:{len(r.json().get('data', [])) if r.ok else str(r.status_code) + ' ' + err(r)[:60]}")
        rows.append(f"  rows {ent:<17} {'  '.join(cells)}")
    for ty in ("Version", "HumanUser", "Project"):
        cells = [f"{k}:{len(get_as(t, f'/schema/{ty}/fields').json().get('data', {}))}" for k, t in toks.items()]
        rows.append(f"  schema fields {ty:<10} {'  '.join(cells)}")
    for k, t in toks.items():
        r = get_as(t, "/license_info")
        rows.append(f"  GET /license_info {k:<8} -> {r.status_code} {err(r) if not r.ok else 'ok'}")
    for p in ("/me", "/entity/human_users/me"):
        rows.append(f"  GET {p:<24} " + "  ".join(f"{k}:{get_as(t, p).status_code}" for k, t in toks.items()))

_lib.emit("027_auth_permissions", "\n".join(rows), env)
