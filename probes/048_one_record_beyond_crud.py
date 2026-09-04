"""Q: what else answers on one record besides GET, PUT and DELETE?

The spec advertises four more operations addressed at a single row and two at a single page. Three of
the four look like cheaper reads and one looks like an update via POST. This probe measures what each
one actually takes and answers, so a caller can tell a shortcut from a different endpoint entirely.

Read-only by default. `--write` adds the POST on a single record and the last-accessed write, both in
the sandbox project, both cleaned up by `_lib.Created`.
"""
import json
import random

import _lib

env = _lib.load_env()
c = _lib.client()
PROJECT = _lib.sample_projects(c, env)[0]
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
rows = []


def out(s=""):
    rows.append(s)


def head(endpoint):
    out(f"\n\n===== {endpoint} =====")


def call(label, method, path, note="", follow=True, **kw):
    r = c.request(method, path, allow_redirects=follow, **kw)
    sent = []
    if kw.get("params"):
        sent.append(f"params={json.dumps(kw['params'])}")
    if kw.get("json") is not None:
        sent.append(f"body={json.dumps(kw['json'])}")
    if kw.get("headers"):
        sent.append(f"headers={json.dumps(kw['headers'])}")
    out(f"\n-- {label}")
    out(f"   {method} {path}" + (f"  {'  '.join(sent)}" if sent else ""))
    extra = ""
    if r.history:
        extra = f"  after {[h.status_code for h in r.history]}"
    if r.headers.get("Content-Range"):
        extra += f"  Content-Range: {r.headers['Content-Range']}"
    out(f"   -> {r.status_code} {r.headers.get('Content-Type', '')}  {len(r.content)} bytes{extra}"
        + (f"   {note}" if note else ""))
    try:
        body = r.json()
    except ValueError:
        return r, None
    _lib.note_from(body)
    if not r.ok:
        out("   " + json.dumps(body.get("errors", body)))
    return r, body


# ---------------------------------------------------------------- fixtures

VERSION = c.get("/entity/versions", params={
    "fields": "code", "page[size]": 1,
    "filter[project.Project.id]": PROJECT}).json()["data"][0]["id"]

# The widest multi_entity link the first page of any project-scoped type offers, so the paging
# question is asked of a field with more than a handful of rows in it.
LINKED, LINKED_FIELD, LINKED_N = None, None, 0
for slug, field in (("assets", "shots"), ("sequences", "shots"), ("shots", "tasks")):
    got = c.post(f"/entity/{slug}/_search", headers=ARR, json={
        "filters": [["project", "is", {"type": "Project", "id": PROJECT}]],
        "fields": field, "page": {"size": 100}}).json().get("data", [])
    for row in got:
        n = len(row["relationships"].get(field, {}).get("data", []))
        if n > LINKED_N:
            LINKED, LINKED_FIELD, LINKED_N = f"{slug}/{row['id']}", field, n

out(f"fixtures: a Version with media, and {LINKED_FIELD} on one row holding {LINKED_N} links")

# ------------------------------------------- GET /entity/<type>/<id>/<field>

head("GET /entity/<type>/<id>/<field>")
for field in ("code", "sg_status_list", "id", "entity", "playlists", "image", "sg_uploaded_movie",
              "entity.Shot.code", "sg_not_a_field"):
    call(f"{field}", "GET", f"/entity/versions/{VERSION}/{field}")

for alt in ("original", "thumbnail", "nope"):
    call(f"image, alt={alt}", "GET", f"/entity/versions/{VERSION}/image",
         params={"alt": alt}, follow=False)
call("image, alt=thumbnail, redirect followed", "GET", f"/entity/versions/{VERSION}/image",
     params={"alt": "thumbnail"}, note="the stored bytes")
call("image, alt=original, Range: bytes=0-100", "GET", f"/entity/versions/{VERSION}/image",
     params={"alt": "original"}, headers={"Range": "bytes=0-100"})
call("image, Range but no alt", "GET", f"/entity/versions/{VERSION}/image",
     headers={"Range": "bytes=0-100"}, note="Range without alt reads the field, not the file")

# A `url` field refuses `is null` as a filter (field_types/url), so an empty one is found by reading.
EMPTY = next((v["id"] for v in c.post("/entity/versions/_search", headers=ARR, json={
    "filters": [["project", "is", {"type": "Project", "id": PROJECT}]],
    "fields": "image,sg_uploaded_movie", "page": {"size": 100}}).json().get("data", [])
    if not v["attributes"].get("sg_uploaded_movie") and not v["attributes"].get("image")), None)
if EMPTY:
    for field in ("sg_uploaded_movie", "image"):
        call(f"{field} on a row where it is empty", "GET", f"/entity/versions/{EMPTY}/{field}")
        call(f"{field} empty, alt=original", "GET", f"/entity/versions/{EMPTY}/{field}",
             params={"alt": "original"}, follow=False)

a = c.get(f"/entity/versions/{VERSION}/sg_uploaded_movie").json()["data"]
out(f"\n   attachment hash keys: {sorted(a)}  content_type {a.get('content_type')!r} "
    f"link_type {a.get('link_type')!r} type {a.get('type')!r}")
one = c.get(f"/entity/versions/{VERSION}/image")
whole = c.get(f"/entity/versions/{VERSION}", params={"fields": "image"})
out(f"   cost: /image {len(one.content)} bytes vs ?fields=image {len(whole.content)} bytes")

# -------------------------- GET /entity/<type>/<id>/relationships/<related_field>

head("GET /entity/<type>/<id>/relationships/<related_field>")
for field in ("entity", "project", "playlists", "notes", "code", "image", "sg_not_a_field"):
    call(f"{field}", "GET", f"/entity/versions/{VERSION}/relationships/{field}")

call("a multi_entity with many links", "GET", f"/entity/{LINKED}/relationships/{LINKED_FIELD}")
for params in ({"page[size]": 2}, {"page[size]": 2, "page[number]": 2}, {"fields": "code"},
               {"sort": "code"}, {"options[return_only]": "retired"}):
    r, b = call(f"{json.dumps(params)}", "GET", f"/entity/{LINKED}/relationships/{LINKED_FIELD}",
                params=params)
    if r.ok:
        out(f"   returned {len(b['data'])} of {LINKED_N}, keys {sorted(b['data'][0])}, "
            f"links {json.dumps(b.get('links'))}")

rel = c.get(f"/entity/{LINKED}/relationships/{LINKED_FIELD}")
read = c.get(f"/entity/{LINKED}", params={"fields": LINKED_FIELD})
inner = read.json()["data"]["relationships"][LINKED_FIELD]
out(f"\n   same ids in the same order: "
    f"{[x['id'] for x in rel.json()['data']] == [x['id'] for x in inner['data']]}")
out(f"   cost, {LINKED_N} links: relationships {len(rel.content)} bytes vs "
    f"?fields={LINKED_FIELD} {len(read.content)} bytes")
sing_rel = c.get(f"/entity/versions/{VERSION}/relationships/entity")
sing_read = c.get(f"/entity/versions/{VERSION}", params={"fields": "entity"})
out(f"   cost, one link: relationships {len(sing_rel.content)} bytes vs ?fields=entity "
    f"{len(sing_read.content)} bytes")
out("   read wrapper: " + json.dumps(sing_read.json()["data"]["relationships"]["entity"]))
out("   relationships: " + json.dumps(sing_rel.json()))

# ------------------------------------------- GET /exports/page/...

head("GET /exports/page/<page_id>.<format>")
pages = c.get("/entity/pages", params={"fields": "page_type", "page[size]": 500,
                                       "filter[project.Project.id]": PROJECT}).json()["data"]
PAGE = pages[0]["id"]
for path in (f"/exports/page/{PAGE}.csv", f"/exports/page/{PAGE}.json",
             f"/exports/page/{PAGE}.xml", f"/exports/page/{PAGE}.txt",
             f"/exports/page/{PAGE}", "/exports/page/999999999.csv", "/exports/page/abc.csv"):
    r, b = call(path.rsplit("/", 1)[-1], "GET", path)
    if b is None:
        out(f"   body: {r.text[:120]!r}")

# Every page type the site has, four ids each, so "no page exports" is a measurement rather than
# one unlucky page.
by_type = {}
for p in c.get("/entity/pages", params={"fields": "page_type", "page[size]": 500}).json()["data"]:
    by_type.setdefault(p["attributes"].get("page_type"), []).append(p["id"])
random.seed(48)
tally = {}
for kind, ids in by_type.items():
    for i in random.sample(ids, min(4, len(ids))):
        r = c.get(f"/exports/page/{i}.csv")
        tally[r.status_code] = tally.get(r.status_code, 0) + 1
        if r.ok:
            out(f"\n   page {i} ({kind}) exported: {len(r.content)} bytes, "
                f"first line {r.text.splitlines()[0][:160]!r}")
out(f"\n   {sum(tally.values())} pages sampled over {len(by_type)} page_type values: "
    + ", ".join(f"{n} x {code}" for code, n in sorted(tally.items())))

head("GET /exports/page/<page_id>/<layout_name>.<format>")
for layout in ("Shots", "zzprobe_048_not_a_view"):
    call(layout, "GET", f"/exports/page/{PAGE}/{layout}.csv")

head("POST /entity/<type>/<id>")
call("an id that is not there", "POST", "/entity/versions/999999999", params={"revive": 1})
call("no revive parameter, on an id that is not there", "POST", "/entity/versions/999999999",
     json={"code": "zzprobe_048"})

_lib.emit("048_one_record_beyond_crud", "\n".join(rows), env)
WROTE = len(rows)

# ---------------------------------------------------------------- writes

if _lib.writes_allowed():
    SANDBOX = _lib.sandbox_id(c, env)
    USER = c.get("/entity/human_users", params={"fields": "id", "page[size]": 1}).json()["data"][0]["id"]

    def events_since(after):
        """Sandbox event types logged after an id, newest first. What a write left in the audit trail."""
        r = c.post("/entity/event_log_entries/_search", headers=ARR, json={
            "filters": [["project", "is", {"type": "Project", "id": SANDBOX}],
                        ["id", "greater_than", after]],
            "fields": "event_type", "page": {"size": 50}, "sort": "-id"})
        return [e["attributes"]["event_type"] for e in r.json().get("data", [])]

    def last_event():
        r = c.post("/entity/event_log_entries/_search", headers=ARR, json={
            "filters": [["project", "is", {"type": "Project", "id": SANDBOX}]],
            "fields": "id", "page": {"size": 1}, "sort": "-id"})
        d = r.json().get("data", [])
        return d[0]["id"] if d else 0

    with _lib.Created(c) as made:
        head("POST /entity/<type>/<id>  (writes)")
        new = c.post("/entity/shots", json={"project": {"type": "Project", "id": SANDBOX},
                                            "code": "zzprobe_048_revive"})
        SHOT = made.add("shots", new.json()["data"]["id"])
        c.put(f"/entity/shots/{SHOT}", json={"description": "before the delete"})

        r, b = call("revive a live row", "POST", f"/entity/shots/{SHOT}", params={"revive": 1},
                    note="never retired")
        out("   " + json.dumps(b))
        call("a body, no revive parameter", "POST", f"/entity/shots/{SHOT}",
             json={"description": "written by POST"}, note="is POST an alias for PUT?")
        after = c.get(f"/entity/shots/{SHOT}", params={"fields": "description"})
        out(f"   description now: {after.json()['data']['attributes'].get('description')!r}")

        out(f"\n   DELETE /entity/shots/{SHOT} -> {c.delete(f'/entity/shots/{SHOT}').status_code}")
        mark = last_event()
        r, b = call("revive the retired row", "POST", f"/entity/shots/{SHOT}", params={"revive": 1})
        out("   " + json.dumps(b))
        back = c.get(f"/entity/shots/{SHOT}", params={"fields": "description"})
        out(f"   GET afterwards -> {back.status_code}, description "
            f"{back.json()['data']['attributes'].get('description')!r}")
        out(f"   event_log_entries logged: {events_since(mark)}")
        c.delete(f"/entity/shots/{SHOT}")
        for params in ({"revive": "true"}, {"revive": 0}, {"revive": "false"}, {"revive": "yes"},
                       {}, {"revive": 1, "fields": "code"}):
            r, b = call(f"retired row, params={json.dumps(params)}", "POST",
                        f"/entity/shots/{SHOT}", params=params)
            if r.ok:
                out(f"   meta {json.dumps(b.get('meta'))}  "
                    f"data keys {sorted(b.get('data', {}))}")
                c.delete(f"/entity/shots/{SHOT}")
        r, b = call("a body alongside revive", "POST", f"/entity/shots/{SHOT}",
                    params={"revive": 1}, json={"description": "sent with the revive"})
        if r.ok:
            back = c.get(f"/entity/shots/{SHOT}", params={"fields": "description"})
            out(f"   description afterwards: "
                f"{back.json()['data']['attributes'].get('description')!r}")

        head("PUT /entity/projects/<id>/_update_last_accessed  (writes)")
        before = c.get(f"/entity/projects/{SANDBOX}",
                       params={"fields": "last_accessed_by_current_user"})
        out(f"\n   last_accessed_by_current_user before: "
            f"{before.json()['data']['attributes']['last_accessed_by_current_user']!r}")
        mark = last_event()
        r, b = call("the documented call", "PUT",
                    f"/entity/projects/{SANDBOX}/_update_last_accessed", json={"user_id": USER})
        if b:
            out("   " + json.dumps(b))
        after = c.get(f"/entity/projects/{SANDBOX}",
                      params={"fields": "last_accessed_by_current_user"})
        out(f"   last_accessed_by_current_user after: "
            f"{after.json()['data']['attributes']['last_accessed_by_current_user']!r}")
        out(f"   event_log_entries logged: {events_since(mark)}")
        call("no body", "PUT", f"/entity/projects/{SANDBOX}/_update_last_accessed", json={})
        call("a user id that is not there", "PUT",
             f"/entity/projects/{SANDBOX}/_update_last_accessed", json={"user_id": 999999999})
        call("user_id as a string", "PUT", f"/entity/projects/{SANDBOX}/_update_last_accessed",
             json={"user_id": str(USER)})
        call("a project id that is not there", "PUT",
             "/entity/projects/999999999/_update_last_accessed", json={"user_id": USER})
        call("the same path under another type", "PUT",
             f"/entity/shots/{SHOT}/_update_last_accessed", json={"user_id": USER})
        call("GET instead of PUT", "GET", f"/entity/projects/{SANDBOX}/_update_last_accessed")

    _lib.emit("048_one_record_beyond_crud writes", "\n".join(rows[WROTE:]), env)
