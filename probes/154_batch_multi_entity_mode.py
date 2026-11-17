"""Q: does a multi_entity add or remove with `multi_entity_update_mode` in the body work inside a
`_batch` update, and do two updates of one record in one batch apply in request order?

Recipe 009 measured the mode on a single `PUT`: in the body it edits in place, in the query string it
is ignored and the list is replaced. sg-onset links a Slate to Shots in batches. Recipe 002 measured
batch updates of plain fields only.

On a stock field, `Note.note_links`, with three Shots S1 to S3, each case on a fresh Note starting at
[S1], one `POST /entity/_batch` per case, read back after:

    add [S2]                       remove [S1]                bare list [S2] (the control)
    add [S3] then remove [S1]      set [S2] then add [S3]     add [S3] then set [S2]
    content "first" then "second"

Writes in the sandbox, behind `--write`: the Shots and Notes, deleted on exit.

    python probes/154_batch_multi_entity_mode.py --write
"""
import json

import _lib

env = _lib.load_env()
c = _lib.client()
if not _lib.writes_allowed():
    raise SystemExit("probe 154 writes; run with --write")
SB = _lib.sandbox_id(c, env)
P = {"type": "Project", "id": SB}
rows = []


def out(s=""):
    rows.append(str(s))
    print(s, flush=True)


def mode(m, *shots):
    return {"note_links": {"multi_entity_update_mode": m, "value": [S[x] for x in shots]}}


with _lib.Created(c) as made:
    S = {}
    for n in ("S1", "S2", "S3"):
        sid = made.add("shots", c.post("/entity/shots", json={"project": P, "code": f"zzprobe_154_{n}"}).json()["data"]["id"])
        S[n] = {"type": "Shot", "id": sid}
    NAME = {v["id"]: k for k, v in S.items()}
    cases = [
        ("add [S2]", [mode("add", "S2")]),
        ("remove [S1]", [mode("remove", "S1")]),
        ("bare list [S2]", [{"note_links": [S["S2"]]}]),
        ("add [S3], then remove [S1]", [mode("add", "S3"), mode("remove", "S1")]),
        ("set [S2], then add [S3]", [mode("set", "S2"), mode("add", "S3")]),
        ("add [S3], then set [S2]", [mode("add", "S3"), mode("set", "S2")]),
        ("content 'first', then 'second'", [{"content": "first"}, {"content": "second"}]),
    ]
    for label, updates in cases:
        nid = made.add("notes", c.post("/entity/notes", json={"project": P, "subject": "zzprobe_154",
                                                              "note_links": [S["S1"]]}).json()["data"]["id"])
        r = c.post("/entity/_batch", json={"requests": [
            {"request_type": "update", "entity": "Note", "record_id": nid, "data": d} for d in updates]})
        body = r.json()
        a = c.get(f"/entity/notes/{nid}", params={"fields": "note_links,content"}).json()["data"]
        links = [NAME.get(x["id"], x["id"]) for x in a["relationships"]["note_links"]["data"]]
        echo = ""
        if r.ok:
            echo = "; batch rows echo note_links " + json.dumps(
                [[NAME.get(x["id"], x["id"]) for x in
                  ((row.get("data") or row).get("relationships", {}).get("note_links", {}).get("data") or [])]
                 for row in body["data"]])
        else:
            echo = "; " + json.dumps(body.get("errors"))
        out(f"[S1] + {label} -> {r.status_code}; reads back note_links {links}"
            + (f", content {a['attributes']['content']!r}" if "content" in label else "") + echo)
    _lib.emit("154_batch_multi_entity_mode", "\n".join(rows), env)
