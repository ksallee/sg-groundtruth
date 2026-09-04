"""Q: does /api/v1.1 differ from /api/v1, and which one should a client call?

Probe 042 found the site's own OpenAPI document advertises `servers[0].url` ending in `/api/v1.1`,
while every probe in this corpus was written against `/api/v1`: `client.py` pins the prefix and
nothing overrode it. That leaves every finding here resting on a version the deployment does not
advertise, and no statement anywhere about whether the two are the same API.

Rather than sample a few calls, this sweeps every read-only endpoint the corpus has a card for and
compares the two prefixes call by call. A body that differs only by the prefix echoed back in its
own `links` is the same body, so each pair is compared again with `/api/v1.1` normalised down to
`/api/v1`: that separates a different API from a different URL. Read-only throughout.
"""
import difflib
import json
import re

import _lib

env = _lib.load_env()
c = _lib.client()
rows = []

V1, V11 = "/api/v1", "/api/v1.1"
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
SEARCH = {"filters": [["id", "greater_than", 0]], "fields": ["code"],
          "page": {"size": 2}, "sort": "id"}

def strip_ids(text):
    """Blank the per-request error id, which differs on every call and says nothing about version."""
    return re.sub(r'"id":"[0-9a-f]{32}"', '"id":"<per-request>"', text)


shot = c.get("/entity/shots?page[size]=1&fields=code").json()["data"]
SHOT = shot[0]["id"] if shot else None
proj = c.get("/entity/projects?page[size]=1&fields=name").json()["data"]
PROJ = proj[0]["id"] if proj else None

# Every read-only call the corpus has a card for. Writes are excluded: this compares versions, and
# a create on each prefix would measure two rows rather than one API.
CALLS = [
    ("GET", "/", {}),
    ("GET", "/schema", {}),
    ("GET", "/schema/Shot", {}),
    ("GET", "/schema/Shot/fields", {}),
    ("GET", "/schema/Shot/fields/sg_status_list", {}),
    ("GET", "/preferences", {}),
    ("GET", "/license_info", {}),
    ("GET", "/spec.json", {}),
    ("GET", "/schedule/work_day_rules", {}),
    ("GET", "/webhook/hooks", {}),
    ("GET", "/entity/shots?page[size]=2&fields=code", {}),
    ("GET", f"/entity/shots/{SHOT}?fields=code,sg_status_list", {}),
    ("GET", f"/entity/shots/{SHOT}/followers", {}),
    ("GET", f"/entity/shots/{SHOT}/relationships/project", {}),
    ("GET", f"/entity/projects/{PROJ}?fields=name", {}),
    ("GET", "/entity/human_users?page[size]=1&fields=login", {}),
    ("POST", "/entity/shots/_search", {"headers": ARR, "json": SEARCH}),
    ("POST", "/entity/versions/_search", {"headers": ARR, "json": SEARCH}),
    ("POST", "/entity/shots/_summarize",
     {"headers": ARR, "json": {"filters": [], "summary_fields": [{"field": "id",
                                                                  "type": "count"}]}}),
    ("POST", "/entity/_text_search",
     {"json": {"text": "a", "entity_types": {"Shot": []}}}),
]

rows.append(f"===== {len(CALLS)} read-only calls, each made under both prefixes with one token")
agree = differ = 0
for method, path, kw in CALLS:
    if "None" in path:
        rows.append(f"   {method} {path}  skipped, no sample row")
        continue
    a = c.request(method, f"{V1}{path}", **kw)
    b = c.request(method, f"{V11}{path}", **kw)
    # Two artefacts are not version differences and both have to be removed before comparing.
    # Every error body carries a per-request `id` that changes on every call, and `/spec.json`
    # legitimately contains the string `/api/v1.1` under `servers` whichever prefix served it, so
    # normalising the prefix corrupts that one body. Accept a match either raw or normalised.
    ta, tb = strip_ids(a.text), strip_ids(b.text)
    same = a.status_code == b.status_code and (ta == tb or ta == tb.replace(V11, V1))
    agree += same
    differ += not same
    mark = "same" if same else "DIFFERS"
    rows.append(f"   {mark:8s} {a.status_code}/{b.status_code}  {method} {path}")
    if not same:
        d = [l for l in difflib.unified_diff(ta.splitlines(),
                                             tb.replace(V11, V1).splitlines(), n=0)][:10]
        rows.append("      " + json.dumps(d)[:500])

rows.append(f"\n   {agree} identical once the prefix is normalised, {differ} genuinely different")

rows.append("\n\n===== what prefix does a response echo in its own links")
for name, pre in (("v1", V1), ("v1.1", V11)):
    b = c.request("GET", f"{pre}/entity/shots?page[size]=1&fields=code").json()
    rows.append(f"   called {name:4s} -> {json.dumps(b.get('links'))[:150]}")

rows.append("\n\n===== a version segment that is not a version")
for seg in ["/api/v1.2", "/api/v2", "/api/v0", "/api/v1.10", "/api/version", "/api"]:
    r = c.request("GET", f"{seg}/entity/shots?page[size]=1")
    try:
        body = json.dumps(r.json().get("errors", r.json()))[:150]
    except ValueError:
        body = repr(r.text[:100])
    rows.append(f"   GET {seg}/entity/shots -> {r.status_code}  {body}")

rows.append("\n\n===== does either prefix advertise the other")
s1 = c.get("/spec.json").json()
r11 = c.request("GET", f"{V11}/spec.json")
rows.append(f"   /api/v1/spec.json    servers {json.dumps(s1.get('servers'))[:110]}")
if r11.ok:
    s11 = r11.json()
    ops1 = {(m.upper(), p) for p, v in s1["paths"].items() for m in v}
    ops11 = {(m.upper(), p) for p, v in s11["paths"].items() for m in v}
    rows.append(f"   /api/v1.1/spec.json  servers {json.dumps(s11.get('servers'))[:110]}")
    rows.append(f"   operations: v1 {len(ops1)}, v1.1 {len(ops11)}, identical {ops1 == ops11}")

_lib.emit("051_api_version", "\n".join(rows), env)
