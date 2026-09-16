"""Q: is a HumanUser's activity_stream the person's feed, or the changes to their own record?

Probe 043 measured the stream on a Shot and a Project. An artist page wants one feed of a person's
day, and the spec says nothing about what `/entity/human_users/<id>/activity_stream` holds. Three
readings are possible: the updates the person made, the updates on what they follow, or the
attribute changes on the HumanUser row itself. Read-only; the person is the one named by
FPT_USER_LOGIN, resolved by login, never by id.
"""
import json
from collections import Counter

import _lib

env = _lib.load_env()
c = _lib.client()
PROJECT = _lib.sample_projects(c, env)[0]
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
rows = []

login = (env.get("FPT_USER_LOGIN") or "").strip()
if not login:
    raise SystemExit("set FPT_USER_LOGIN in .env.local, the person whose feed to read")
me = c.post("/entity/human_users/_search", headers=ARR,
            json={"filters": [["login", "is", login]], "fields": ["login"]}).json()["data"]
if not me:
    raise SystemExit(f"no HumanUser with login {login!r}")
ME = me[0]["id"]


def tally(updates, who):
    by_type = Counter(u["update_type"] for u in updates)
    by_meta = Counter((u["meta"] or {}).get("type") for u in updates)
    by_entity = Counter(u["primary_entity"]["type"] for u in updates if u.get("primary_entity"))
    by_author = Counter("me" if (u["created_by"] or {}).get("id") == who
                        and (u["created_by"] or {}).get("type") == "HumanUser"
                        else (u["created_by"] or {}).get("type") for u in updates)
    return by_type, by_meta, by_entity, by_author


def stream(label, path, **params):
    r = c.get(path, params=params or None)
    rows.append(f"\n-- {label}")
    q = "?" + "&".join(f"{k}={v}" for k, v in params.items()) if params else ""
    if r.status_code != 200:
        rows.append(f"   GET {path}{q} -> {r.status_code} {json.dumps(r.json().get('errors'))[:300]}")
        return []
    d = r.json()["data"]
    _lib.note_from(d)
    ups = d["updates"]
    rows.append(f"   GET {path}{q} -> 200  updates={len(ups)}"
                f"  latest_update_id={d['latest_update_id']}  earliest_update_id={d['earliest_update_id']}")
    if ups:
        t, m, e, a = tally(ups, ME)
        rows.append(f"   update_type   {dict(t)}")
        rows.append(f"   meta.type     {dict(m)}")
        rows.append(f"   primary_entity {dict(e)}")
        rows.append(f"   created_by    {dict(a)}")
        rows.append(f"   span {ups[-1]['created_at']} .. {ups[0]['created_at']}")
    return ups


rows.append("===== the person's own stream, 500 deep")
mine = stream("HumanUser stream", f"/entity/human_users/{ME}/activity_stream", limit=500)

# The three readings, tested against the same 500 rows.
following = c.get(f"/entity/human_users/{ME}/following").json()["data"]
followed = {(f["type"], f["id"]) for f in following}
rows.append(f"\n-- the person follows {len(following)} records: "
            f"{dict(Counter(f['type'] for f in following))}")
on_followed = sum(1 for u in mine if u.get("primary_entity")
                  and (u["primary_entity"]["type"], u["primary_entity"]["id"]) in followed)
by_me = sum(1 for u in mine if (u["created_by"] or {}).get("id") == ME
            and (u["created_by"] or {}).get("type") == "HumanUser")
about_me = sum(1 for u in mine if (u.get("primary_entity") or {}).get("type") == "HumanUser"
               and u["primary_entity"]["id"] == ME)
rows.append(f"   of {len(mine)} updates: {by_me} made by the person, {on_followed} on a record they "
            f"follow, {about_me} about the HumanUser row itself")
others = [u for u in mine if (u["created_by"] or {}).get("id") != ME]
if others:
    rows.append("   first update the person did not make, verbatim:")
    rows.append("   " + json.dumps(others[0])[:600])
if mine:
    rows.append("   first update, verbatim:")
    rows.append("   " + json.dumps(mine[0])[:600])

rows.append("\n\n===== the same 500 window on the project, for the vocabulary")
proj = stream("Project stream", f"/entity/projects/{PROJECT}/activity_stream", limit=500)
metas = {}
for u in proj:
    k = (u["update_type"], (u["meta"] or {}).get("type"))
    metas.setdefault(k, sorted((u["meta"] or {}).keys()))
rows.append("   meta keys per (update_type, meta.type):")
for k, v in sorted(metas.items(), key=str):
    rows.append(f"     {k}: {v}")

rows.append("\n\n===== a Task the person is assigned to, and its entity")
tasks = c.post("/entity/tasks/_search", headers=ARR,
               json={"filters": [["task_assignees", "in", [{"type": "HumanUser", "id": ME}]]],
                     "fields": ["content", "entity", "project"], "sort": "-updated_at",
                     "page": {"size": 5}}).json()["data"]
rows.append(f"   {len(tasks)} of the person's tasks read (newest updated first)")
for t in tasks[:2]:
    ent = (t["relationships"].get("entity") or {}).get("data")
    stream(f"Task {t['id']} stream", f"/entity/tasks/{t['id']}/activity_stream", limit=100)
    if ent:
        slug = {"Shot": "shots", "Asset": "assets"}.get(ent["type"])
        if slug:
            stream(f"its {ent['type']} stream", f"/entity/{slug}/{ent['id']}/activity_stream",
                   limit=100)

rows.append("\n\n===== entity_fields on a HumanUser stream")
r = c.get(f"/entity/human_users/{ME}/activity_stream",
          params={"limit": 3, "entity_fields[Version]": "sg_status_list,entity",
                  "entity_fields[Task]": "due_date,task_assignees"})
if r.ok:
    for u in r.json()["data"]["updates"]:
        rows.append(f"   {u['primary_entity']['type']}: {sorted(u['primary_entity'])}")

_lib.emit("066_user_feed", "\n".join(rows), env)
