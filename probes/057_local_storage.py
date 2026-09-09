"""Q: can a LocalStorage row be created over REST, and by anyone other than an administrator?

Whether "point at any folder" is self-service or a support ticket. LocalStorage is site-wide like Step
and PublishedFileType, so a row created here is visible to every project, and probe 019's rule that a
name spent is spent forever is the thing to test on the delete.

Writes are gated behind --write and named zzprobe_057_*. The site's own rows are never touched.
"""
import json

import _lib
from sg_groundtruth.client import FPT

env = _lib.load_env()
c = _lib.client()
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
JSON = {"Content-Type": "application/json"}
rows = []


def err(r):
    try:
        return json.dumps(r.json().get("errors", r.json()))
    except ValueError:
        return repr(r.text)


# --- 1. the type -------------------------------------------------------------------------------
f = c.get("/schema/LocalStorage/fields").json()["data"]
rows.append(f"=== 1. /schema/LocalStorage/fields -> {len(f)} fields, no 'project': "
            f"{'project' not in f}")
for n in sorted(f):
    d = f[n]
    rows.append(f"  {n:<22} {d['data_type']['value']:<12} mandatory={d['mandatory']['value']!s:<5} "
                f"editable={d['editable']['value']!s:<5} unique={d['unique']['value']!s:<5} "
                f"visible.editable={d['visible']['editable']}")

rows.append("\n=== 2. addressing")
for p in ("/entity/local_storages", "/entity/local_storage", "/entity/LocalStorage",
          "/entity/localstorages", "/entity/storages"):
    r = c.get(p, params={"page[size]": 1})
    rows.append(f"  GET {p:<28} -> {r.status_code}"
                + ("" if r.ok else " " + json.loads(r.text)["errors"][0]["detail"]))

r = c.get("/entity/local_storages",
          params={"fields": "code,mac_path,windows_path,linux_path", "page[size]": 100})
existing = r.json()["data"]
_lib.note_from(r.json())
for s in existing:
    for k in ("mac_path", "windows_path", "linux_path"):
        _lib.note_path(s["attributes"].get(k))
rows.append(f"  rows on this site: {len(existing)}, ids {[s['id'] for s in existing]}")
rows.append("  platforms defined: " + json.dumps(
    {k: sum(1 for s in existing if s["attributes"].get(k))
     for k in ("mac_path", "windows_path", "linux_path")}))

rows.append("\n=== 3. project scope")
PROJECT = _lib.sample_projects(c, env)[0]
r = c.post("/entity/local_storages/_search", headers=ARR,
           json={"filters": [["project", "is", {"type": "Project", "id": PROJECT}]],
                 "fields": ["code"]})
rows.append(f"  _search on project -> {r.status_code} {err(r) if not r.ok else 'ok'}")
a = c.get("/entity/local_storages", params={"fields": "code", "page[size]": 100})
b = c.get("/entity/local_storages", params={"fields": "code", "page[size]": 100,
                                            "project_id": PROJECT})
rows.append(f"  ?project_id=<a project> -> {b.status_code}, {len(b.json().get('data', []))} rows "
            f"against {len(a.json()['data'])} unscoped")

if not _lib.writes_allowed():
    rows.append("\n(read-only run; the write half needs --write)")
    _lib.emit("057_local_storage", "\n".join(rows), env)
    raise SystemExit(0)

# --- 4. create, delete, and the name afterwards -------------------------------------------------
CODE = "zzprobe_057_a"
with _lib.Created(c) as made:
    rows.append("\n=== 4. create")
    for label, body in (
        ("{}", {}),
        ("{mac_path} only", {"mac_path": "/zzprobe_057_orphan"}),
        ("{code} only", {"code": CODE}),
    ):
        r = c.post("/entity/local_storages", headers=JSON, json=body)
        rows.append(f"  {label:<22} -> {r.status_code} " + (f"id={r.json()['data']['id']}"
                                                            if r.ok else err(r)))
        if r.ok:
            made.add("local_storages", r.json()["data"]["id"])

    made_id = made.rows[-1][1]
    for label, i in (("an empty body", made.rows[0][1]), ("a bare {code}", made_id)):
        got = c.get(f"/entity/local_storages/{i}").json()["data"]
        rows.append(f"  the row {label} made: " + json.dumps(got["attributes"]))

    rows.append("\n=== 5. the same code again, while the first is alive")
    r = c.post("/entity/local_storages", headers=JSON, json={"code": CODE})
    rows.append(f"  POST {{code}} duplicate -> {r.status_code} " + (f"id={r.json()['data']['id']}"
                                                                    if r.ok else err(r)))
    if r.ok:
        made.add("local_storages", r.json()["data"]["id"])

    rows.append("\n=== 6. all three roots on one row")
    r = c.post("/entity/local_storages", headers=JSON, json={
        "code": "zzprobe_057_three", "mac_path": "/zzprobe_057_three",
        "windows_path": "Z:\\zzprobe_057_three", "linux_path": "/mnt/zzprobe_057_three",
        "description": "zzprobe 057, deleted on exit"})
    rows.append(f"  POST all three -> {r.status_code}" + ("" if r.ok else f" {err(r)}"))
    if r.ok:
        three = made.add("local_storages", r.json()["data"]["id"])
        rows.append("  read back: " + json.dumps(c.get(f"/entity/local_storages/{three}", params={
            "fields": "code,mac_path,windows_path,linux_path"}).json()["data"]["attributes"]))

    rows.append("\n=== 7. delete, then the same code again")
    d = c.delete(f"/entity/local_storages/{made_id}")
    made.rows = [row for row in made.rows if row != ("local_storages", made_id)]
    rows.append(f"  DELETE /entity/local_storages/{made_id} -> {d.status_code} "
                f"{'' if d.status_code == 204 else err(d)}")
    rows.append(f"  GET it afterwards -> {c.get(f'/entity/local_storages/{made_id}').status_code}")
    r = c.post("/entity/local_storages", headers=JSON, json={"code": CODE})
    rows.append(f"  POST the same code again -> {r.status_code} " + (f"id={r.json()['data']['id']}"
                                                                     if r.ok else err(r)))
    if r.ok:
        again = made.add("local_storages", r.json()["data"]["id"])
        rows.append(f"  DELETE that one too -> {c.delete(f'/entity/local_storages/{again}').status_code}")
        made.rows = [row for row in made.rows if row != ("local_storages", again)]

    # --- 8. a caller who is not an administrator ------------------------------------------------
    rows.append("\n=== 8. as a non-admin")
    cands = c.post("/entity/human_users/_search", headers=ARR,
                   json={"filters": [["can_impersonate_this_user", "is", True],
                                     ["sg_status_list", "is", "act"]],
                         "fields": "login,permission_rule_set", "page": {"size": 200}})
    _lib.note_from(cands.json())
    by_set = {}
    for u in cands.json().get("data", []):
        name = (u["relationships"]["permission_rule_set"]["data"] or {}).get("name")
        by_set.setdefault(name, u["attributes"]["login"])
    rows.append(f"  impersonable, by permission_rule_set: {sorted(by_set)}")
    lower = next((v for k, v in sorted(by_set.items()) if k != "Admin"), None)
    lower_set = next((k for k in sorted(by_set) if k != "Admin"), None)
    if not lower:
        rows.append("  no impersonable user outside Admin on this site; not measured")
    else:
        lc = FPT.from_env(env, sudo_as_login=lower)
        # Both reads now, not against the count taken before this run created rows.
        r = lc.get("/entity/local_storages", params={"fields": "code,mac_path", "page[size]": 100})
        mine = c.get("/entity/local_storages", params={"fields": "code", "page[size]": 100})
        rows.append(f"  as {lower_set!r}: GET /entity/local_storages -> {r.status_code}, "
                    f"{len(r.json().get('data', []))} rows against "
                    f"{len(mine.json()['data'])} as the script user at the same moment")
        r = lc.post("/entity/local_storages", headers=JSON, json={"code": "zzprobe_057_lower"})
        rows.append(f"  as {lower_set!r}: POST -> {r.status_code} "
                    + (f"id={r.json()['data']['id']}" if r.ok else err(r)))
        if r.ok:
            made.add("local_storages", r.json()["data"]["id"])
        # On a zzprobe row, never on the site's own: an update the site keeps is not a probe.
        target = made.rows[-1][1] if made.rows else None
        if target:
            r = lc.put(f"/entity/local_storages/{target}", headers=JSON,
                       json={"mac_path": "/zzprobe_057_lower_write"})
            rows.append(f"  as {lower_set!r}: PUT on a zzprobe row -> {r.status_code} "
                        + ("" if r.ok else err(r)))
            r = lc.delete(f"/entity/local_storages/{target}")
            rows.append(f"  as {lower_set!r}: DELETE a zzprobe row -> {r.status_code} "
                        + ("" if r.status_code == 204 else err(r)))
            if r.status_code == 204:
                made.rows = [row for row in made.rows if row != ("local_storages", target)]

    rows.append("\n=== cleanup")

_lib.emit("057_local_storage", "\n".join(rows), env)
