"""Q: what does each endpoint the corpus names actually take, and what does it answer?

The corpus records behaviour, one question at a time, and the endpoint an entry names was a note in
its body. That leaves no place holding the request contract and the real response for one call, which
is what someone about to make it is holding. This probe records that surface, per endpoint: the exact
call, the status, the envelope, and the edge cases that live on the call rather than on a data type.

Read-only by default. `--write` adds the create, update, delete, batch and upload endpoints, all in
the sandbox project, all cleaned up by `_lib.Created`.

The four schema-writing endpoints are deliberately absent. A deleted field name is never freed
(docs/quirks.md), so this probe never creates one; their recorded output is in findings 019 and 040.
"""
import json

import _lib

env = _lib.load_env()
c = _lib.client()
PROJECT = _lib.sample_projects(c, env)[0]
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
HASH = {"Content-Type": "application/vnd+shotgun.api3_hash+json"}
rows = []


def out(s=""):
    rows.append(s)


def head(endpoint):
    out(f"\n\n===== {endpoint} =====")


def shape(obj, depth=0, key=""):
    """The envelope, not the payload: key names and value types, one list element deep.

    A response body is the thing a caller needs the shape of, and 500 rows of it teaches nothing that
    the first row does not.
    """
    pad = "  " * depth
    if isinstance(obj, dict):
        if not obj:
            return f"{pad}{key}: {{}}"
        lines = [f"{pad}{key}: {{" if key else f"{pad}{{"]
        for k, v in obj.items():
            lines.append(shape(v, depth + 1, k))
        lines.append(f"{pad}}}")
        return "\n".join(lines)
    if isinstance(obj, list):
        if not obj:
            return f"{pad}{key}: []"
        return f"{pad}{key}: [{len(obj)} x\n" + shape(obj[0], depth + 1) + f"\n{pad}]"
    if isinstance(obj, str):
        v = obj if len(obj) <= 60 else obj[:57] + "..."
        return f'{pad}{key}: "{v}"'
    return f"{pad}{key}: {json.dumps(obj)}"


def call(label, method, path, note="", **kw):
    """One request, its status, and enough of the answer to be worth reading."""
    r = c.request(method, path, **kw)
    sent = []
    if kw.get("params"):
        sent.append(f"params={json.dumps(kw['params'])}")
    if kw.get("json"):
        sent.append(f"body={json.dumps(kw['json'])}")
    if kw.get("headers"):
        sent.append(f"headers={json.dumps(kw['headers'])}")
    out(f"\n-- {label}")
    out(f"   {method} {path}" + (f"  {'  '.join(sent)}" if sent else ""))
    out(f"   -> {r.status_code} {r.headers.get('Content-Type', '')}  {len(r.content)} bytes"
        + (f"   {note}" if note else ""))
    try:
        body = r.json()
    except ValueError:
        out(f"   body (not JSON): {r.text[:200]!r}")
        return r, None
    _lib.note_from(body)
    if not r.ok:
        out("   " + json.dumps(body.get("errors", body))[:400])
    return r, body


def envelope(body, limit=40):
    for line in shape(body).splitlines()[:limit]:
        out("   " + line)


# ---------------------------------------------------------------- read-only

head("POST /auth/access_token")
import requests  # noqa: E402  the one call the client cannot make for us

r = requests.post(f"{c.site}/api/v1/auth/access_token",
                  data={"grant_type": "client_credentials",
                        "client_id": env["FPT_API_SCRIPT_NAME"],
                        "client_secret": env["FPT_API_API_KEY"]},
                  headers={"Accept": "application/json"}, timeout=30)
out(f"\n-- correct call, form-encoded\n   -> {r.status_code} {r.headers.get('Content-Type')}")
envelope(r.json())
for label, kw in (
    ("Content-Type: application/json instead of form", {"json": {"grant_type": "client_credentials"}}),
    ("unknown grant_type", {"data": {"grant_type": "magic", "client_id": "x", "client_secret": "y"}}),
    ("missing client_secret", {"data": {"grant_type": "client_credentials", "client_id": "x"}}),
):
    e = requests.post(f"{c.site}/api/v1/auth/access_token",
                      headers={"Accept": "application/json"}, timeout=30, **kw)
    out(f"\n-- {label}\n   -> {e.status_code}  {e.text[:220]}")

head("GET /")
r, b = call("the API root, no token needed", "GET", "/api/v1")
envelope(b)

head("GET /preferences")
r, b = call("site display settings", "GET", "/preferences")
envelope(b)
r, b = call("one preference by name", "GET", "/preferences", params={"prefs": "hours_per_day"})
envelope(b)

head("GET /schema")
r, b = call("every enabled entity type", "GET", "/schema")
out(f"   {len(b['data'])} types")
envelope({"data": {k: b["data"][k] for k in list(b["data"])[:1]}})
r, b = call("with project_id", "GET", "/schema", params={"project_id": PROJECT},
            note="same list; scope shows on fields, not types")

head("GET /schema/<Type>")
r, b = call("one type", "GET", "/schema/Version")
envelope(b)
r, b = call("a type the site has not enabled", "GET", "/schema/CustomEntity99")
r, b = call("a type that does not exist at all", "GET", "/schema/NotTypeAtAll")

head("GET /schema/<Type>/fields")
r, b = call("every field on one type", "GET", "/schema/Version/fields")
out(f"   {len(b['data'])} fields")
envelope({"data": {"code": b["data"]["code"]}})
r, b = call("with project_id", "GET", "/schema/Version/fields", params={"project_id": PROJECT},
            note="hidden_values appears only with it (probe 009)")

head("GET /schema/<Type>/fields/<field>")
r, b = call("one field, site scope", "GET", "/schema/Version/fields/sg_status_list")
envelope(b)
r, b = call("same field, project scope", "GET", "/schema/Version/fields/sg_status_list",
            params={"project_id": PROJECT})
p = b["data"]["properties"]
out(f"   valid_values {len(p['valid_values']['value'])}, "
    f"hidden_values {p['hidden_values']['value']}")
r, b = call("a field that does not exist", "GET", "/schema/Version/fields/sg_not_a_field")

head("GET /entity/<type>")
r, b = call("a page of rows", "GET", "/entity/versions",
            params={"fields": "code,entity,sg_status_list", "page[size]": 2,
                    "filter[project.Project.id]": PROJECT})
envelope(b)
r, b = call("page past the end", "GET", "/entity/versions",
            params={"page[size]": 2, "page[number]": 99999,
                    "filter[project.Project.id]": PROJECT},
            note="links.next is still emitted (probe 006)")
out("   data: " + json.dumps(b["data"]) + "   links: " + json.dumps(b.get("links", {})))
r, b = call("unknown field name", "GET", "/entity/versions",
            params={"fields": "code,sg_not_a_field", "page[size]": 1,
                    "filter[project.Project.id]": PROJECT},
            note="dropped at 200")
out("   " + json.dumps(b["data"][0]["attributes"] if b["data"] else {}))
r, b = call("a type that does not exist", "GET", "/entity/not_a_type", params={"page[size]": 1})
r, b = call("page[size] above any documented cap", "GET", "/entity/versions",
            params={"page[size]": 1000, "fields": "id", "filter[project.Project.id]": PROJECT})
out(f"   returned {len(b['data'])} rows")

head("GET /entity/<type>/<id>")
first = c.get("/entity/versions", params={"fields": "code", "page[size]": 1,
                                          "filter[project.Project.id]": PROJECT}).json()["data"]
VERSION_ID = first[0]["id"] if first else None
r, b = call("one row", "GET", f"/entity/versions/{VERSION_ID}", params={"fields": "code,entity"})
envelope(b)
r, b = call("an id that does not exist", "GET", "/entity/versions/999999999")
r, b = call("a retired row", "GET", f"/entity/versions/{VERSION_ID}",
            params={"options[return_only]": "retired"})

head("POST /entity/<type>/_search")
r, b = call("array filters", "POST", "/entity/versions/_search", headers=ARR,
            json={"filters": [["project", "is", {"type": "Project", "id": PROJECT}]],
                  "fields": "code", "page": {"size": 2}})
envelope(b)
r, b = call("nested and/or, api3_hash", "POST", "/entity/versions/_search", headers=HASH,
            json={"filters": {"logical_operator": "and", "conditions": [
                ["project", "is", {"type": "Project", "id": PROJECT}],
                {"logical_operator": "or", "conditions": [
                    ["sg_status_list", "is", "fin"], ["sg_status_list", "is", "rev"]]}]},
                  "fields": "code,sg_status_list", "page": {"size": 2}})
r, b = call("a condition as {path, relation, values}", "POST", "/entity/versions/_search",
            headers=HASH, note="the shape that runs nowhere (probe 030)",
            json={"filters": {"logical_operator": "and", "conditions": [
                {"path": "code", "relation": "is", "values": ["x"]}]}, "fields": "code"})
r, b = call("array body without the vendor Content-Type", "POST", "/entity/versions/_search",
            json={"filters": [["project", "is", {"type": "Project", "id": PROJECT}]],
                  "fields": "code"})
r, b = call("unknown operator", "POST", "/entity/versions/_search", headers=ARR,
            json={"filters": [["code", "wat", "x"]], "fields": "code"})
r, b = call("empty filters", "POST", "/entity/versions/_search", headers=ARR,
            json={"filters": [], "fields": "code", "page": {"size": 1}},
            note="site-wide, unscoped")

head("POST /entity/<type>/_summarize")
r, b = call("count grouped by a status", "POST", "/entity/versions/_summarize", headers=ARR,
            json={"filters": [["project", "is", {"type": "Project", "id": PROJECT}]],
                  "summary_fields": [{"field": "id", "type": "count"}],
                  "grouping": [{"field": "sg_status_list", "type": "exact", "direction": "asc"}]})
envelope(b, 30)
r, b = call("no grouping", "POST", "/entity/versions/_summarize", headers=ARR,
            json={"filters": [["project", "is", {"type": "Project", "id": PROJECT}]],
                  "summary_fields": [{"field": "id", "type": "count"}]})
out("   " + json.dumps(b.get("data", b))[:200])
r, b = call("summarize an unsummarizable field", "POST", "/entity/versions/_summarize", headers=ARR,
            json={"filters": [], "summary_fields": [{"field": "image", "type": "count"}]})

_lib.emit("041_endpoint_surface", "\n".join(rows), env)
WROTE = len(rows)

# ---------------------------------------------------------------- writes

if _lib.writes_allowed():
    SANDBOX = _lib.sandbox_id(c, env)
    with _lib.Created(c) as made:
        head("POST /entity/<type>")
        r, b = call("create with project alone", "POST", "/entity/shots",
                    json={"project": {"type": "Project", "id": SANDBOX}})
        SHOT = made.add("shots", b["data"]["id"])
        envelope(b, 25)
        out(f"   server-invented code: {b['data']['attributes'].get('code')!r}")
        r, b = call("create with ?fields", "POST", "/entity/shots",
                    params={"fields": "code"},
                    json={"project": {"type": "Project", "id": SANDBOX}, "code": "zzprobe_041"},
                    note="?fields is ignored on every write (probe 024)")
        SHOT2 = made.add("shots", b["data"]["id"])
        out(f"   keys returned: {len(b['data']['attributes'])}")
        r, b = call("create with no project", "POST", "/entity/shots", json={"code": "zzprobe_041b"})
        r, b = call("create with an unknown field", "POST", "/entity/shots",
                    json={"project": {"type": "Project", "id": SANDBOX}, "sg_not_a_field": 1})
        if r.ok:
            made.add("shots", b["data"]["id"])

        head("PUT /entity/<type>/<id>")
        r, b = call("update one key", "PUT", f"/entity/shots/{SHOT}",
                    json={"description": "written by probe 041"})
        out(f"   keys returned: {len(b['data']['attributes'])}  (the whole record)")
        r, b = call("key omitted from the body", "PUT", f"/entity/shots/{SHOT}",
                    json={"code": "zzprobe_041_renamed"},
                    note="description untouched, not cleared")
        out(f"   description now: {b['data']['attributes'].get('description')!r}")
        r, b = call("empty body", "PUT", f"/entity/shots/{SHOT}", json={})
        r, b = call("an id that does not exist", "PUT", "/entity/shots/999999999",
                    json={"description": "x"})

        head("POST /entity/_batch")
        r, b = call("one create and one update, atomic", "POST", "/entity/_batch", json={"requests": [
            {"request_type": "create", "entity": "Shot",
             "data": {"project": {"type": "Project", "id": SANDBOX}, "code": "zzprobe_041_batch"}},
            {"request_type": "update", "entity": "Shot", "record_id": SHOT,
             "data": {"description": "batched"}}]})
        if r.ok:
            for row in b.get("data", []):
                inner = row.get("data", row)
                if inner.get("type") == "Shot" and inner.get("id") not in (SHOT, SHOT2):
                    made.add("shots", inner["id"])
        envelope(b, 22)
        r, b = call("one bad request in the batch", "POST", "/entity/_batch", json={"requests": [
            {"request_type": "create", "entity": "Shot",
             "data": {"project": {"type": "Project", "id": SANDBOX}, "code": "zzprobe_041_rollback"}},
            {"request_type": "update", "entity": "Shot", "record_id": 999999999,
             "data": {"description": "x"}}]},
            note="does the good one survive?")
        check = c.post("/entity/shots/_search", headers=ARR,
                       json={"filters": [["code", "is", "zzprobe_041_rollback"]], "fields": "code"})
        out(f"   rows named zzprobe_041_rollback afterwards: {len(check.json().get('data', []))}")

        head("GET /entity/<type>/<id>/<field>/_upload")
        r, b = call("no filename", "GET", f"/entity/shots/{SHOT}/image/_upload")
        r, b = call("presigned links for one media field", "GET",
                    f"/entity/shots/{SHOT}/image/_upload",
                    params={"filename": "probe041.png"})
        envelope(b, 20)
        UP = b.get("links", {}) if r.ok else {}

        head("GET /entity/<type>/<id>/_upload")
        r, b = call("a type with no such field", "GET", f"/entity/shots/{SHOT}/attachments/_upload",
                    params={"filename": "probe041.txt"},
                    note="the field name is part of the path, and Shot has none")
        note = c.post("/entity/notes", json={"project": {"type": "Project", "id": SANDBOX},
                                             "subject": "zzprobe_041"})
        NOTE = made.add("notes", note.json()["data"]["id"])
        r, b = call("no field named, stores as an Attachment", "GET",
                    f"/entity/notes/{NOTE}/attachments/_upload",
                    params={"filename": "probe041.txt"})
        envelope(b, 18)
        AUP, AINFO = (b.get("links", {}), b.get("data", {})) if r.ok else ({}, {})

        head("PUT <links.upload>")
        if AUP.get("upload"):
            body = b"probe 041\n"
            put = requests.put(AUP["upload"], data=body, timeout=60)
            out(f"\n-- the bytes, straight to storage\n   PUT <links.upload>  {len(body)} bytes"
                f"\n   -> {put.status_code}  headers: "
                f"{ {k: v for k, v in put.headers.items() if k.lower() in ('etag', 'content-length')} }")
            out(f"   body: {put.text[:120]!r}")

        head("POST <links.complete_upload>")
        if AUP.get("complete_upload"):
            r2 = c.post(AUP["complete_upload"],
                        json={"upload_info": AINFO, "upload_data": {}})
            out(f"\n-- tell the site the object is there"
                f"\n   POST {AUP['complete_upload']}"
                f"\n   -> {r2.status_code} {r2.headers.get('Content-Type', '')}"
                f"  {len(r2.content)} bytes")
            out(f"   body: {r2.text[:200]!r}")
            back = c.get(f"/entity/notes/{NOTE}", params={"fields": "attachments"})
            att = back.json()["data"]["relationships"].get("attachments", {}).get("data", [])
            out(f"   Shot.attachments afterwards: {json.dumps(att)}")
            for a in att:
                made.add("attachments", a["id"])

        head("DELETE /entity/<type>/<id>")
        gone = made.rows.pop()  # deleted here rather than by the context manager, to record it
        r, b = call("retire a row", "DELETE", f"/entity/{gone[0]}/{gone[1]}")
        out(f"   body: {r.text[:80]!r}")
        r, b = call("read it back", "GET", f"/entity/{gone[0]}/{gone[1]}")
        r, b = call("read it back as retired", "GET", f"/entity/{gone[0]}/{gone[1]}",
                    params={"options[return_only]": "retired"})
        if r.ok:
            out("   found: the row is retired, not erased")
        r, b = call("delete it twice", "DELETE", f"/entity/{gone[0]}/{gone[1]}")

    _lib.emit("041_endpoint_surface writes", "\n".join(rows[WROTE:]), env)
