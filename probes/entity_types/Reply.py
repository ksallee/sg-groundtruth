"""Q: how is a Reply addressed, what can it hang off, and how does a client read a thread in order?

Two things are worth settling. `Reply` is the awkward slug, because a naive plural and an English plural
are different words. And a Reply is assumed to belong to a Note, while an external survey reports replies
created on a Delivery; `valid_types` on `Reply.entity` settles which is true.

Read-only by default. `--write` adds the create contract and a three-reply thread in the sandbox, every
row deleted on the way out.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _lib  # noqa: E402

env = _lib.load_env()
c = _lib.client()
PROJECT = _lib.sample_projects(c, env)[0]
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
JSN = {"Content-Type": "application/json"}
rows = []


def err(r):
    """Whole errors[] object, source included; the 400 is where the API documents itself (probe 017)."""
    try:
        return json.dumps(r.json().get("errors", r.json()), indent=1)
    except ValueError:
        return r.text


def search(entity, filt, fields=("id",), size=500, sort=None):
    body = {"filters": filt, "fields": list(fields), "page": {"size": size}}
    if sort:
        body["sort"] = sort
    r = c.post(f"/entity/{entity}/_search", headers=ARR, json=body)
    if not r.ok:
        return f"ERR {r.status_code}", err(r)
    return len(r.json()["data"]), r.json()["data"]


def props(entity, field):
    r = c.get(f"/schema/{entity}/fields/{field}")
    if not r.ok:
        return {}, {"ERR": err(r)}
    d = r.json()["data"]
    flat = {k: (v.get("value") if isinstance(v, dict) else v) for k, v in d.items() if k != "properties"}
    return flat, {k: v.get("value") for k, v in (d.get("properties") or {}).items()}


rows.append("=== the REST path slug: a naive plural and an English plural are different words here")
for slug in ("replies", "replys", "reply", "Reply", "Replies", "repliess"):
    r = c.get(f"/entity/{slug}", params={"page[size]": 1})
    tail = "" if r.ok else json.dumps(r.json()["errors"][0].get("detail") or r.json()["errors"][0].get("title"))
    rows.append(f"  GET /entity/{slug:9s} -> {r.status_code} {tail}")
r = c.get("/entity/replies", params={"page[size]": 1})
if r.ok and r.json()["data"]:
    rows.append(f"  links.self normalises to {r.json()['data'][0]['links']['self']}")

rows.append("\n=== project-scoped or site-wide")
schema = c.get("/schema/Reply/fields").json()["data"]
rows.append(f"  Reply fields ({len(schema)}): {sorted(schema)}")
for attempt, call in (
        ('_search [["project", "is", {{Project, N}}]]',
         lambda: c.post("/entity/replies/_search", headers=ARR,
                        json={"filters": [["project", "is", {"type": "Project", "id": PROJECT}]],
                              "fields": ["content"], "page": {"size": 1}})),
        ("GET ?filter[project]=N",
         lambda: c.get("/entity/replies", params={"filter[project]": PROJECT, "page[size]": 1})),
        ("GET ?project_id=N",
         lambda: c.get("/entity/replies", params={"project_id": PROJECT, "page[size]": 1}))):
    r = call()
    rows.append(f"  {attempt} -> {r.status_code}")
    if not r.ok:
        rows.append("   " + err(r).replace("\n", "\n   "))

rows.append("\n=== identity and body")
for f in ("content", "cached_display_name", "publish_status", "user", "created_at"):
    ff, _ = props("Reply", f)
    rows.append(f"  Reply.{f:20s} name={ff.get('name')!r} data_type={ff.get('data_type')} "
                f"mandatory={ff.get('mandatory')} unique={ff.get('unique')} editable={ff.get('editable')}")
rows.append(f"  flagged mandatory: {sorted(k for k, v in schema.items() if (v.get('mandatory') or {}).get('value'))}")
rows.append(f"  flagged unique:    {sorted(k for k, v in schema.items() if (v.get('unique') or {}).get('value'))}")
n, data = search("replies", [], fields=("content", "cached_display_name", "publish_status"), size=500)
if isinstance(n, int):
    filled = {}
    for d in data:
        for k, v in d["attributes"].items():
            if v not in (None, ""):
                filled[k] = filled.get(k, 0) + 1
    rows.append(f"  over {n} replies site-wide, non-null: {filled}")
    for d in data[:1]:
        _lib.note_from(d)
        a = d["attributes"]
        rows.append(f"  sample row id={d['id']} content={str(a.get('content'))[:60]!r} "
                    f"cached_display_name={a.get('cached_display_name')!r}")

rows.append("\n=== what a Reply attaches to: Reply.entity valid_types, read rather than assumed")
ef, ep = props("Reply", "entity")
vt = ep.get("valid_types") or []
rows.append(f"  Reply.entity data_type={ef.get('data_type')} mandatory={ef.get('mandatory')} "
            f"editable={ef.get('editable')} valid_types: {len(vt)} types")
allt = sorted(c.get("/schema").json()["data"])
rows.append(f"  /schema lists {len(allt)} entity types; Reply.entity names {len(vt)} of them")
rows.append(f"  types on the site NOT in Reply.entity valid_types: {sorted(set(allt) - set(vt))}")
rows.append(f"  is Note in valid_types: {'Note' in vt}   Delivery: {'Delivery' in vt}   "
            f"Version: {'Version' in vt}   Reply: {'Reply' in vt}")
uf, up = props("Reply", "user")
rows.append(f"  Reply.user valid_types={up.get('valid_types')} editable={uf.get('editable')}")

rows.append("\n=== which types hold the reverse field")
back = []
for t in allt:
    r = c.get(f"/schema/{t}/fields")
    if not r.ok:
        continue
    for k, v in r.json()["data"].items():
        p = {kk: vv.get("value") for kk, vv in (v.get("properties") or {}).items()}
        if (p.get("valid_types") or []) == ["Reply"]:
            back.append(f"{t}.{k} ({(v.get('data_type') or {}).get('value')}, "
                        f"editable={(v.get('editable') or {}).get('value')})")
rows.append(f"  fields whose valid_types is exactly ['Reply']: {back}")

rows.append("\n=== what existing replies actually hang off, site-wide")
n, data = search("replies", [], fields=("content", "entity", "user"), size=500)
if isinstance(n, int):
    by_type = {}
    for d in data:
        e = (d.get("relationships", {}).get("entity", {}).get("data") or {}).get("type")
        by_type[repr(e)] = by_type.get(repr(e), 0) + 1
    rows.append(f"  over {n} replies: entity.type -> {by_type}")

rows.append("\n=== ordering: how a client reads a thread")
n, data = search("replies", [], fields=("content", "created_at", "entity"), size=500)
if isinstance(n, int) and data:
    ids = [d["id"] for d in data]
    times = [d["attributes"].get("created_at") for d in data]
    rows.append(f"  default (no sort): ids ascending={ids == sorted(ids)} "
                f"created_at ascending={times == sorted(times)}")
    for s in (["created_at"], ["-created_at"], ["id"], ["-id"], ["content"]):
        k, kd = search("replies", [], fields=("created_at",), size=500, sort=s)
        if isinstance(k, int):
            got = [d["id"] for d in kd]
            rows.append(f"  sort {s} -> {k} rows, ids ascending={got == sorted(got)}, first={got[0]}")
        else:
            rows.append(f"  sort {s} -> {k}")
            rows.append("   " + kd.replace("\n", "\n   "))
    # a thread read in order, one filter per entity type seen
    counts = {}
    for d in data:
        e = d.get("relationships", {}).get("entity", {}).get("data") or {}
        if e:
            counts[(e.get("type"), e.get("id"))] = counts.get((e.get("type"), e.get("id")), 0) + 1
    for (etype, eid), k in sorted(counts.items(), key=lambda kv: -kv[1])[:3]:
        n2, d2 = search("replies", [["entity", "is", {"type": etype, "id": eid}]],
                        fields=("content", "created_at"), size=100, sort=["created_at"])
        rows.append(f"  thread on a {etype} with {k} repl(ies), "
                    f"[[\"entity\", \"is\", {{\"type\": \"{etype}\", \"id\": <id>}}]] sort created_at -> {n2}")
        if isinstance(n2, int):
            rows.append(f"    ids in that order: {[d['id'] for d in d2]} "
                        f"created_at {[d['attributes'].get('created_at') for d in d2]}")
        else:
            head = json.loads(d2)[0]
            title = head["title"]
            rows.append(f"    title (list of valid types trimmed): {title[:110]} ... ")
            rows.append(f"    the list names {title.count(chr(34)) // 2} types, and includes {etype!r}: "
                        f"{chr(34) + etype + chr(34) in title}")
            rows.append(f"    {etype} present in /schema: {etype in allt}; "
                        f"in Reply.entity valid_types: {etype in vt}")
    k2, _ = search("replies", [["entity", "type_is", "Note"]], fields=("content",), size=500)
    k3, _ = search("replies", [["entity", "type_is", "Delivery"]], fields=("content",), size=500)
    rows.append(f"  [[\"entity\", \"type_is\", \"Note\"]] -> {k2} rows; "
                f"type_is \"Delivery\" -> {k3} rows")

if not _lib.writes_allowed():
    rows.append("\n(read-only run; pass --write for the create contract and the thread)")
else:
    SANDBOX = _lib.sandbox_id(c, env)
    with _lib.Created(c) as made:
        rows.append("\n=== create contract, sandbox project (probe 012: mandatory is not the contract)")
        r = c.post("/entity/notes", headers=JSN,
                   json={"project": {"type": "Project", "id": SANDBOX}, "subject": "zzprobe_reply_thread",
                         "content": "zzprobe note body"})
        NOTE = made.add("notes", r.json()["data"]["id"]) if r.ok else None
        rows.append(f"  (host Note: POST /entity/notes -> {r.status_code})")
        r = c.post("/entity/versions", headers=JSN,
                   json={"project": {"type": "Project", "id": SANDBOX}, "code": "zzprobe_reply_host"})
        VER = made.add("versions", r.json()["data"]["id"]) if r.ok else None

        attempts = [
            ("empty body", {}),
            ("project alone", {"project": {"type": "Project", "id": SANDBOX}}),
            ("content alone", {"content": "zzprobe reply body"}),
            ("entity alone", {"entity": {"type": "Note", "id": NOTE}}),
            ("entity + content", {"entity": {"type": "Note", "id": NOTE}, "content": "zzprobe reply a"}),
            ("entity + content, entity is a Version",
             {"entity": {"type": "Version", "id": VER}, "content": "zzprobe reply on a version"}),
            ("entity as a bare id", {"entity": NOTE, "content": "zzprobe reply bare id"}),
        ]
        orphans = []
        for label, body in attempts:
            r = c.post("/entity/replies", headers=JSN, json=body)
            if r.ok:
                d = r.json()["data"]
                made.add("replies", d["id"])
                ent = (d.get("relationships") or {}).get("entity", {}).get("data")
                if not ent:
                    orphans.append(d["id"])
                rows.append(f"  {r.status_code} {label}: id={d['id']} attributes={json.dumps(d['attributes'])} "
                            f"entity={json.dumps(ent)}")
                _lib.note_from(d)
            else:
                rows.append(f"  {r.status_code} {label}:")
                rows.append("   " + err(r).replace("\n", "\n   "))

        rows.append("\n=== deleting a Reply whose entity is null")
        if orphans:
            i = orphans[0]
            r = c.delete(f"/entity/replies/{i}")
            rows.append(f"  DELETE /entity/replies/<id>, entity null -> {r.status_code}")
            if not r.ok:
                rows.append("   " + err(r).replace("\n", "\n   "))
            # Created cannot delete these, so give every one an entity before the teardown runs.
            for i in orphans:
                p = c.put(f"/entity/replies/{i}", headers=JSN, json={"entity": {"type": "Note", "id": NOTE}})
                r = c.delete(f"/entity/replies/{i}")
                rows.append(f"  PUT entity={{Note, <id>}} -> {p.status_code}, then DELETE -> {r.status_code}")
                if r.ok:
                    made.rows = [(s, x) for s, x in made.rows if not (s == "replies" and x == i)]

        rows.append("\n=== a Reply hung off a Delivery, the case an external survey reports")
        dn, dd = search("deliveries", [], fields=("title",), size=1)
        did = dd[0]["id"] if isinstance(dn, int) and dn else None
        if did is None:
            r = c.post("/entity/deliveries", headers=JSN,
                       json={"project": {"type": "Project", "id": SANDBOX}, "title": "zzprobe_delivery"})
            rows.append(f"  no Delivery on the probed site; POST /entity/deliveries -> {r.status_code}")
            if r.ok:
                did = made.add("deliveries", r.json()["data"]["id"])
            else:
                rows.append("   " + err(r).replace("\n", "\n   "))
        if did:
            r = c.post("/entity/replies", headers=JSN,
                       json={"entity": {"type": "Delivery", "id": did},
                             "content": "zzprobe reply on a delivery"})
            rows.append(f"  POST entity={{Delivery, <id>}} -> {r.status_code}")
            if r.ok:
                made.add("replies", r.json()["data"]["id"])
                rows.append(f"    id={r.json()['data']['id']} entity="
                            f"{json.dumps(r.json()['data']['relationships']['entity']['data'])}")
            else:
                rows.append("   " + err(r).replace("\n", "\n   "))
            dr = c.get(f"/entity/deliveries/{did}", params={"fields": "title,replies"})
            rows.append(f"  GET the Delivery with fields=replies -> "
                        f"{json.dumps((dr.json()['data'].get('relationships') or {}).get('replies', {}).get('data'))}")

        rows.append("\n=== the thread: three replies on one Note, then read back in order")
        made_ids = []
        for body in ("zzprobe thread 1", "zzprobe thread 2", "zzprobe thread 3"):
            r = c.post("/entity/replies", headers=JSN,
                       json={"entity": {"type": "Note", "id": NOTE}, "content": body})
            if r.ok:
                made_ids.append(made.add("replies", r.json()["data"]["id"]))
        rows.append(f"  created {len(made_ids)} replies: {made_ids}")
        for label, s in (("no sort", None), ("created_at", ["created_at"]), ("-created_at", ["-created_at"]),
                         ("id", ["id"])):
            n, data = search("replies", [["entity", "is", {"type": "Note", "id": NOTE}]],
                             fields=("content", "created_at"), size=50, sort=s)
            if isinstance(n, int):
                rows.append(f"  {label:12s} -> " + json.dumps(
                    [[d["id"], d["attributes"].get("content"), d["attributes"].get("created_at")]
                     for d in data]))
            else:
                rows.append(f"  {label:12s} -> {n}")
                rows.append("   " + data.replace("\n", "\n   "))
        nf, npp = props("Note", "replies")
        rows.append(f"  Note.replies data_type={nf.get('data_type')} editable={nf.get('editable')} "
                    f"valid_types={npp.get('valid_types')}")
        r = c.get(f"/entity/notes/{NOTE}", params={"fields": "subject,replies"})
        rows.append(f"  GET the Note with fields=replies -> "
                    f"{json.dumps((r.json()['data'].get('relationships') or {}).get('replies', {}).get('data'))}")

        rows.append("\n=== is a Reply editable after the fact?")
        if made_ids:
            for field, value in (("content", "zzprobe edited body"),
                                 ("entity", {"type": "Version", "id": VER}),
                                 ("content", None)):
                r = c.put(f"/entity/replies/{made_ids[0]}", headers=JSN, json={field: value})
                if r.ok:
                    d = r.json()["data"]
                    rows.append(f"  PUT {field}={json.dumps(value)} -> 200, reads back "
                                f"{json.dumps(d['attributes'].get(field) or (d.get('relationships') or {}).get(field, {}).get('data'))}")
                else:
                    rows.append(f"  PUT {field}={json.dumps(value)} -> {r.status_code}")
                    rows.append("   " + err(r).replace("\n", "\n   "))

actual = "\n".join(rows)
_lib.emit("entity_types/Reply", actual, env)
