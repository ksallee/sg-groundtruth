"""Q: how does the API expose attention: who is following what, and what changed on a record?

Six calls the corpus does not cover: `activity_stream`, `followers`, `following`, `follow`,
`unfollow` and `thread_contents`. The first answers "what happened here" the way the web
application's activity feed does; the middle four are the subscription list; the last returns a
Note and its replies in one call.

The read half runs ungated. `--write` adds the follow and unfollow pair, which changes real
subscription state, so it only ever follows rows this probe made and unfollows them before it
exits.
"""
import json
import time

import _lib

env = _lib.load_env()
c = _lib.client()
PROJECT = _lib.sample_projects(c, env)[0]
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
rows = []


def call(label, method, path, **kw):
    r = c.request(method, path, **kw)
    rows.append(f"\n-- {label}")
    q = "?" + "&".join(f"{k}={v}" for k, v in (kw.get("params") or {}).items()) if kw.get("params") else ""
    body = f"  {json.dumps(kw['json'])}" if kw.get("json") is not None else ""
    rows.append(f"   {method} {path}{q}{body}")
    if not r.content:
        rows.append(f"   -> {r.status_code}, empty body")
        return r, None
    try:
        b = r.json()
    except ValueError:
        rows.append(f"   -> {r.status_code} body (not JSON): {r.text[:200]!r}")
        return r, None
    _lib.note_from(b)
    rows.append(f"   -> {r.status_code} {json.dumps(b.get('errors', b))[:400]}")
    return r, b


def stream(label, path, **params):
    r = c.get(path, params=params or None)
    rows.append(f"\n-- {label}")
    q = "?" + "&".join(f"{k}={v}" for k, v in params.items()) if params else ""
    if r.status_code != 200:
        rows.append(f"   GET {path}{q} -> {r.status_code} {json.dumps(r.json()['errors'])[:300]}")
        return None
    d = r.json()["data"]
    _lib.note_from(d)
    ids = [u["id"] for u in d["updates"]]
    rows.append(f"   GET {path}{q} -> 200  updates={len(ids)}"
                f"  latest_update_id={d['latest_update_id']}"
                f"  earliest_update_id={d['earliest_update_id']}")
    rows.append(f"   ids {ids[:4]}{' ... ' + str(ids[-1]) if len(ids) > 4 else ''}")
    return d


SHOT = c.post("/entity/shots/_search", headers=ARR,
              json={"filters": [["project", "is", {"type": "Project", "id": PROJECT}]],
                    "fields": "code", "page": {"size": 1}}).json()["data"][0]["id"]
# The lowest-id HumanUser on the site. A login is site data, so the probe resolves one rather than
# naming one, and it is only ever asked about rows this run created.
USERS = c.get("/entity/human_users", params={"fields": "login", "page[size]": 1}).json()["data"]
USER = USERS[0]["id"]

rows.append("===== GET /entity/<type>/<id>/activity_stream")
d = stream("default, no parameters", f"/entity/shots/{SHOT}/activity_stream")
if d:
    rows.append("   one update, verbatim:")
    rows.append("   " + json.dumps(d["updates"][0]))
stream("limit 500, the documented cap", f"/entity/shots/{SHOT}/activity_stream", limit=500)
stream("limit 501", f"/entity/shots/{SHOT}/activity_stream", limit=501)
stream("limit 0", f"/entity/shots/{SHOT}/activity_stream", limit=0)
stream("limit not an integer", f"/entity/shots/{SHOT}/activity_stream", limit="abc")
PIVOT = d["updates"][1]["id"] if d and len(d["updates"]) > 1 else 1
rows.append(f"\n   the next four calls pivot on update id {PIVOT}, which is in the stream")
stream("max_id, the page-down parameter", f"/entity/shots/{SHOT}/activity_stream",
       limit=3, max_id=PIVOT)
stream("min_id, the top-up parameter", f"/entity/shots/{SHOT}/activity_stream",
       limit=50, min_id=PIVOT)
stream("the same stream on a Project", f"/entity/projects/{PROJECT}/activity_stream", limit=2)
stream("an id that is not there", "/entity/shots/999999999/activity_stream")
stream("a type that is not there", "/entity/bogus_things/1/activity_stream")

plain = c.get(f"/entity/shots/{SHOT}/activity_stream", params={"limit": 1}).json()
wide = c.get(f"/entity/shots/{SHOT}/activity_stream",
             params={"limit": 1, "entity_fields[Shot]": "code,sg_status_list"}).json()
a, b = plain["data"]["updates"][0]["primary_entity"], wide["data"]["updates"][0]["primary_entity"]
_lib.note_from(a)
_lib.note_from(b)
rows.append("\n-- entity_fields[Shot]=code,sg_status_list widens primary_entity, keyed by its type")
rows.append(f"   without: {sorted(a)}")
rows.append(f"   with:    {sorted(b)}")
rows.append(f"   created_by is unchanged: {sorted(plain['data']['updates'][0]['created_by'])}")

rows.append("\n\n===== GET /entity/<type>/<id>/followers")
call("a Shot nobody follows", "GET", f"/entity/shots/{SHOT}/followers")
# A Note that has at least one Reply, so thread_contents has a thread to return.
REPLY = c.post("/entity/replies/_search", headers=ARR,
               json={"filters": [["entity", "type_is", "Note"]], "fields": "entity",
                     "page": {"size": 1}}).json()
NOTE = REPLY["data"][0]["relationships"]["entity"]["data"]["id"]
_, fol = call("a Note", "GET", f"/entity/notes/{NOTE}/followers")
# The most-followed of a handful of Notes, to see whether the list is ordered and whether it pages.
CROWD = max(c.post("/entity/notes/_search", headers=ARR,
                   json={"filters": [], "fields": "id", "page": {"size": 20}}).json()["data"],
            key=lambda n: len(c.get(f"/entity/notes/{n['id']}/followers").json()["data"]))["id"]
_, fol = call("the most-followed Note of twenty", "GET", f"/entity/notes/{CROWD}/followers")
if fol and fol["data"]:
    rows.append(f"   {len(fol['data'])} rows, no page key, ids in the order returned: "
                f"{[x['id'] for x in fol['data']]}")
    rows.append(f"   follow the links.self it hands back: GET {fol['data'][0]['links']['self']}"
                f" -> {c.get(fol['data'][0]['links']['self']).status_code}")
call("an id that is not there", "GET", "/entity/notes/999999999/followers")
call("Project, which is followable in the web application", "GET",
     f"/entity/projects/{PROJECT}/followers")

rows.append("\n\n===== GET /entity/human_users/<user_id>/following")
r, f = call("the whole list, no filter", "GET", f"/entity/human_users/{USER}/following")
if f:
    from collections import Counter
    rows.append(f"   {len(f['data'])} rows, no page key, types "
                f"{dict(Counter(x['type'] for x in f['data']))}")
    rows.append(f"   row shape {json.dumps(f['data'][0])}")
    rows.append(f"   follow the links.self it hands back: GET {f['data'][0]['links']['self']}"
                f" -> {c.get(f['data'][0]['links']['self']).status_code}")
for q in ({"entity": "notes"}, {"entity": "Note"}, {"entity": "shots"},
          {"entity": "notes", "project_id": PROJECT}, {"project_id": PROJECT},
          {"entity": "bogus_things"}, {"project_id": 999999999}):
    r, b = call(f"filter {q}", "GET", f"/entity/human_users/{USER}/following", params=q)
    if r.ok:
        rows[-1] = f"   -> 200 {len(b['data'])} rows"
call("an id that is not there", "GET", "/entity/human_users/999999999/following")
API_USER = c.get("/entity/api_users", params={"page[size]": 1}).json()["data"][0]["id"]
call("an ApiUser id, which is not a HumanUser id", "GET",
     f"/entity/human_users/{API_USER}/following")

rows.append("\n\n===== GET /entity/notes/<id>/thread_contents")
r, t = call("a Note", "GET", f"/entity/notes/{NOTE}/thread_contents")
if t:
    rows.append(f"   {len(t['data'])} rows, types {[x['type'] for x in t['data']]}")
    rows.append(f"   keys per row {[sorted(x) for x in t['data']]}")
r, w = call("entity_fields, the one documented parameter", "GET",
            f"/entity/notes/{NOTE}/thread_contents",
            params={"entity_fields[Note]": "sg_status_list,subject",
                    "entity_fields[Reply]": "updated_at",
                    "entity_fields[Attachment]": "filename"})
if w:
    rows[-1] = f"   -> 200 keys per row {[sorted(x) for x in w['data']]}"
call("a Version", "GET", f"/entity/versions/1/thread_contents")
call("an id that is not there", "GET", "/entity/notes/999999999/thread_contents")

if not _lib.writes_allowed():
    rows.append("\n\n===== follow / unfollow  (skipped, needs --write)")
    _lib.emit("043_attention", "\n".join(rows), env)
    raise SystemExit

SANDBOX = _lib.sandbox_id(c, env)
rows.append("\n\n===== POST /entity/human_users/<user_id>/follow")
with _lib.Created(c) as made:
    A = made.add("shots", c.post("/entity/shots", json={
        "project": {"type": "Project", "id": SANDBOX}, "code": "zzprobe_043_a"}).json()["data"]["id"])
    B = made.add("shots", c.post("/entity/shots", json={
        "project": {"type": "Project", "id": SANDBOX}, "code": "zzprobe_043_b"}).json()["data"]["id"])
    rows.append("   Shots made in the sandbox for this section, followed as one HumanUser")
    try:
        call("the documented body", "POST", f"/entity/human_users/{USER}/follow",
             json={"entities": [{"record_id": A, "entity": "Shot"}]})
        call("read it back", "GET", f"/entity/shots/{A}/followers")
        call("the same call again", "POST", f"/entity/human_users/{USER}/follow",
             json={"entities": [{"record_id": A, "entity": "Shot"}]})
        call("snake_case plural, as every path segment spells it", "POST",
             f"/entity/human_users/{USER}/follow",
             json={"entities": [{"record_id": B, "entity": "shots"}]})
        call("read the second one back", "GET", f"/entity/shots/{B}/followers")
        call("no entities wrapper", "POST", f"/entity/human_users/{USER}/follow",
             json={"record_id": A, "entity": "Shot"})
        call("empty list", "POST", f"/entity/human_users/{USER}/follow", json={"entities": []})
        call("empty body", "POST", f"/entity/human_users/{USER}/follow", json={})
        call("a type that is not there", "POST", f"/entity/human_users/{USER}/follow",
             json={"entities": [{"record_id": A, "entity": "Bogus"}]})
        call("an id that is not there", "POST", f"/entity/human_users/{USER}/follow",
             json={"entities": [{"record_id": 999999999, "entity": "Shot"}]})
        C = made.add("shots", c.post("/entity/shots", json={
            "project": {"type": "Project", "id": SANDBOX},
            "code": "zzprobe_043_c"}).json()["data"]["id"])
        call("one good and one bad in the same call", "POST", f"/entity/human_users/{USER}/follow",
             json={"entities": [{"record_id": C, "entity": "Shot"},
                                {"record_id": 999999999, "entity": "Shot"}]})
        call("was the good half of that call applied", "GET", f"/entity/shots/{C}/followers")
        call("the vendor content type _search needs", "POST", f"/entity/human_users/{USER}/follow",
             headers=ARR, json={"entities": [{"record_id": A, "entity": "Shot"}]})
        call("a user id that is not there", "POST", "/entity/human_users/999999999/follow",
             json={"entities": [{"record_id": A, "entity": "Shot"}]})
        call("does the follow show up in the user's following list", "GET",
             f"/entity/human_users/{USER}/following", params={"project_id": SANDBOX})

        rows.append("\n\n===== PUT /entity/<type>/<id>/unfollow")
        call("no body", "PUT", f"/entity/shots/{A}/unfollow", json={})
        call("the documented body", "PUT", f"/entity/shots/{A}/unfollow", json={"user_id": USER})
        call("read it back", "GET", f"/entity/shots/{A}/followers")
        call("the same call again, nobody left to unfollow", "PUT",
             f"/entity/shots/{A}/unfollow", json={"user_id": USER})
        call("POST instead of PUT", "POST", f"/entity/shots/{A}/unfollow", json={"user_id": USER})
        call("a user id that is not there", "PUT", f"/entity/shots/{B}/unfollow",
             json={"user_id": 999999999})
        call("clear the second one", "PUT", f"/entity/shots/{B}/unfollow", json={"user_id": USER})
        call("both clear", "GET", f"/entity/shots/{B}/followers")

        rows.append("\n-- does a write reach the stream, polled every 5s for 90s")
        seen = None
        for t_ in range(0, 91, 5):
            if c.get(f"/entity/shots/{A}/activity_stream").json()["data"]["updates"]:
                seen = t_
                break
            time.sleep(5)
        rows.append(f"   the three Shots this run made: "
                    f"{'still absent after 90s' if seen is None else f'first seen at {seen}s'}")
        rows.append(f"   polling ended at {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}")
        ps = stream("the sandbox Project's stream, which would carry the same creates",
                    f"/entity/projects/{SANDBOX}/activity_stream", limit=3)
        if ps and ps["updates"]:
            rows.append(f"   newest update on the whole site: id {ps['updates'][0]['id']}, "
                        f"created_at {ps['updates'][0]['created_at']}, "
                        f"{ps['updates'][0]['update_type']} of a "
                        f"{ps['updates'][0]['primary_entity']['type']}")
    finally:
        # Deleting the rows takes the follow entries with them; unfollow anyway, so a failure
        # part way through this block still leaves the user's subscription list as it was.
        for i in (A, B, C):
            c.put(f"/entity/shots/{i}/unfollow", json={"user_id": USER})

_lib.emit("043_attention", "\n".join(rows), env)
