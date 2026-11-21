"""Q: an entity or multi_entity link whose target row was deleted: what does a read return, does it
come back when the target is revived, and what does a write naming a deleted row answer?

sg-onset links rows to rows a person may delete on another device. Probe 060 measured the read once:
`sg_task` reads null and a multi_entity drops the element. This measures it again on stock fields,
then what 060 did not: the link after the target is revived, and every write that names a retired
row, next to a row id that never existed.

Rows, all in the sandbox: Tasks T1, T2; Playlists P1, P2; Version V with `sg_task` T1 and
`playlists` [P1, P2]. T1 and P1 are deleted, read through V, revived, read again, deleted again,
then named in writes: `PUT` on V, a `POST` of a new Version, and a `_batch` update. Last, V's list is
replaced while P1 is retired and P1 revived, to see whether the hidden element survives a replace.

Writes behind `--write`. Every row is deleted before exit; T1 and P1 are left retired, as deleted.

    python probes/161_link_to_deleted_row.py --write
"""
import json

import _lib

ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
env = _lib.load_env()
c = _lib.client()
if not _lib.writes_allowed():
    raise SystemExit("probe 161 writes; run with --write")
SB = _lib.sandbox_id(c, env)
P = {"type": "Project", "id": SB}
rows = []
GONE = 99999999


def out(s=""):
    rows.append(str(s))


def errs(r):
    if not r.content:
        return "(empty body)"
    try:
        j = r.json()
    except ValueError:
        return r.text[:2000]
    return json.dumps(j.get("errors", j))


def ref(t, i):
    return {"type": t, "id": i}


def links(v, label):
    g = c.get(f"/entity/versions/{v}", params={"fields": "sg_task,playlists"}).json()["data"]["relationships"]
    s = c.post("/entity/versions/_search", headers=ARR, json={
        "filters": [["id", "is", v]], "fields": ["sg_task", "playlists"]}).json()["data"][0]["relationships"]
    rel = c.get(f"/entity/versions/{v}/relationships/playlists").json()["data"]
    short = lambda d: None if d is None else ([x["name"] for x in d] if isinstance(d, list) else d["name"])
    out(f"  {label}: sg_task {short(g['sg_task']['data'])!r}  playlists {short(g['playlists']['data'])}")
    out(f"    _search equal to GET: {s == g}; relationships/playlists {short(rel)}")


def count(filters):
    r = c.post("/entity/versions/_search", headers=ARR, json={"filters": filters, "fields": ["id"]})
    return f"{len(r.json()['data'])} rows" if r.ok else f"{r.status_code} {errs(r)}"


retired = []
with _lib.Created(c) as made:
    try:
        t1 = c.post("/entity/tasks", json={"project": P, "content": "zzprobe_161_t1"}).json()["data"]["id"]
        t2 = made.add("tasks", c.post("/entity/tasks", json={"project": P, "content": "zzprobe_161_t2"}).json()["data"]["id"])
        p1 = c.post("/entity/playlists", json={"project": P, "code": "zzprobe_161_p1"}).json()["data"]["id"]
        p2 = made.add("playlists", c.post("/entity/playlists", json={"project": P, "code": "zzprobe_161_p2"}).json()["data"]["id"])
        v = made.add("versions", c.post("/entity/versions", json={
            "project": P, "code": "zzprobe_161_v", "sg_task": ref("Task", t1),
            "playlists": [ref("Playlist", p1), ref("Playlist", p2)]}).json()["data"]["id"])
        retired = [("tasks", t1), ("playlists", p1)]
        links(v, "before")

        out("\n===== delete T1 and P1")
        for slug, i in retired:
            out(f"  DELETE /entity/{slug}/<{slug[:-1]}> -> {c.delete(f'/entity/{slug}/{i}').status_code}")
        links(v, "after")
        out(f"  filter sg_task is T1 -> {count([['id', 'is', v], ['sg_task', 'is', ref('Task', t1)]])}; "
            f"playlists is P1 -> {count([['id', 'is', v], ['playlists', 'is', ref('Playlist', p1)]])}")
        r = c.get(f"/entity/tasks/{t1}", params={"options[return_only]": "retired", "fields": "content"})
        out(f"  T1 under return_only=retired -> {r.status_code}")

        out("\n===== revive T1 and P1")
        for slug, i in retired:
            r = c.post(f"/entity/{slug}/{i}", params={"revive": 1})
            out(f"  revive {slug[:-1]} -> {r.status_code} {json.dumps(r.json().get('meta')) if r.ok else errs(r)}")
        links(v, "after revive")

        out("\n===== delete T1 and P1 again, then name them in writes")
        for slug, i in retired:
            c.delete(f"/entity/{slug}/{i}")
        links(v, "deleted again")
        writes = (
            ("PUT sg_task = T1 (retired)", {"sg_task": ref("Task", t1)}),
            ("PUT sg_task = a Task id never used", {"sg_task": ref("Task", GONE)}),
            ("PUT sg_task = T2 (live)", {"sg_task": ref("Task", t2)}),
            ("PUT playlists = [P1] (retired), bare list", {"playlists": [ref("Playlist", p1)]}),
            ("PUT playlists = [P2, P1]", {"playlists": [ref("Playlist", p2), ref("Playlist", p1)]}),
            ("PUT playlists add [P1]", {"playlists": {"multi_entity_update_mode": "add",
                                                      "value": [ref("Playlist", p1)]}}),
            ("PUT playlists remove [P1]", {"playlists": {"multi_entity_update_mode": "remove",
                                                         "value": [ref("Playlist", p1)]}}),
            ("PUT playlists = [a Playlist id never used]", {"playlists": [ref("Playlist", GONE)]}),
        )
        for label, body in writes:
            r = c.put(f"/entity/versions/{v}", json=body)
            out(f"  {label} -> {r.status_code} {'' if r.ok else errs(r)}")
            links(v, "    then")

        r = c.post("/entity/versions", json={"project": P, "code": "zzprobe_161_new", "sg_task": ref("Task", t1)})
        out(f"  POST /entity/versions with sg_task = T1 (retired) -> {r.status_code} {'' if r.ok else errs(r)}")
        if r.status_code == 201:
            made.add("versions", r.json()["data"]["id"])
        r = c.post("/entity/_batch", json={"requests": [{"request_type": "update", "entity": "Version",
                                                          "record_id": v, "data": {"sg_task": ref("Task", t1)}}]})
        out(f"  _batch update sg_task = T1 (retired) -> {r.status_code} {'' if r.ok else errs(r)}")
        links(v, "    then")

        out("\n===== the hidden link: replace the list while P1 is retired, then revive P1")
        r = c.put(f"/entity/versions/{v}", json={"playlists": [ref("Playlist", p2)]})
        out(f"  PUT playlists = [P2], bare list -> {r.status_code} {'' if r.ok else errs(r)}")
        r = c.post(f"/entity/playlists/{p1}", params={"revive": 1})
        out(f"  revive P1 -> {r.status_code}")
        links(v, "after revive")
        c.delete(f"/entity/playlists/{p1}")
    finally:
        for slug, i in retired:
            live = c.get(f"/entity/{slug}/{i}").status_code == 200
            if live:
                out(f"  T1/P1 left live; DELETE /entity/{slug}/<id> -> {c.delete(f'/entity/{slug}/{i}').status_code}")

for slug in ("tasks", "playlists", "versions"):
    key = "content" if slug == "tasks" else "code"
    n = c.post(f"/entity/{slug}/_search", headers=ARR, json={
        "filters": [["project", "is", P], [key, "starts_with", "zzprobe_161"]], "fields": ["id"]}).json()["data"]
    out(f"  live {slug} named zzprobe_161 at exit: {len(n)}")
_lib.emit("161_link_to_deleted_row", "\n".join(rows), env)
