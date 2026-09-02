"""Q: how is POST /entity/_batch driven, and what does it guarantee?

Probe 024 found the endpoint and its id key. This one answers what a caller has to decide before
writing against it: can one batch reference a row it created, is the response in request order, how far
does the rollback reach, and how many requests fit.
"""
import json
import time

import requests

import _lib

env = _lib.load_env()
c = _lib.client()
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
P = "zzprobe_029"
rows = []


def err(r):
    try:
        return json.dumps(r.json().get("errors", r.json()))
    except ValueError:
        return repr(r.text[:400])


def batch(reqs, **kw):
    return c.post("/entity/_batch", json={"requests": reqs}, **kw)


def kind(row):
    """Which request a response row answers, read from its own shape alone (probe 024)."""
    if "did_delete" in row:
        return "delete"
    return "update" if "status" in row else "create"


def line(row):
    d = row.get("data", row)
    return (f"{kind(row):<6} outer={sorted(row)} type={d.get('type')} id={d.get('id')} "
            f"code={(d.get('attributes') or {}).get('code')!r}")


rows.append("=== contract: the endpoint enumerates itself through 400s (verbatim)")
for label, body in (
        ("array body", [{"request_type": "create", "entity": "Version"}]),
        ("no requests key", {"entity": "Version"}),
        ("requests: []", {"requests": []}),
        ("missing entity", {"requests": [{"request_type": "create"}]}),
        ("missing data", {"requests": [{"request_type": "create", "entity": "Version"}]}),
        ("request_type read", {"requests": [{"request_type": "read", "entity": "Version",
                                             "data": {}}]}),
        ("entity as URL slug", {"requests": [{"request_type": "delete", "entity": "versions",
                                              "record_id": 999999999}]}),
        ("delete, no record_id", {"requests": [{"request_type": "delete", "entity": "Version"}]}),
        ("delete unknown id", {"requests": [{"request_type": "delete", "entity": "Version",
                                             "record_id": 999999999}]})):
    r = c.post("/entity/_batch", json=body)
    rows.append(f"  {label:<20} {r.status_code} {err(r)}")
r = c.post("/entity/_batch", headers=ARR, json={"requests": []})
rows.append(f"  {'vendor Content-Type':<20} {r.status_code} {err(r)}")

rows.append("\n=== how many requests are accepted? first, without writing anything")
rows.append("  every row has no data, so a count cap would have to answer something other than the")
rows.append("  missing-data 400 that one row gets.")
for n in (1, 50, 101, 501, 1001, 5001):
    r = c.post("/entity/_batch", json={"requests": [
        {"request_type": "create", "entity": "Version"} for _ in range(n)]})
    e = r.json().get("errors", [{}])[0]
    src = e.get("source")
    if isinstance(src, dict) and list(src) == ["data"] and isinstance(src["data"], list):
        shape = f"source.data = {len(src['data'])}x {json.dumps(src['data'][0])}"
    else:
        shape = json.dumps(e)
    rows.append(f"  n={n:<5} {r.status_code} {e.get('title')!r} {shape}")

if not _lib.writes_allowed():
    rows.append("\n(read-only run; the write half needs --write)")
    _lib.emit("029_batch", "\n".join(rows), env)
    raise SystemExit(0)

SANDBOX = _lib.sandbox_id(c, env)

with _lib.Created(c) as made:
    def track(resp):
        """Register every id a batch response reports, so the run leaves nothing behind."""
        for row in resp.json().get("data", []):
            d = row.get("data", row)
            if d.get("id") and kind(row) == "create":
                made.add("versions" if d.get("type") == "Version" else "shots", d["id"])
        return resp

    def purge(prefix):
        """Delete every sandbox Version whose code starts with prefix, in batches. Returns the count,
        which is also how many rows a request that never answered still committed."""
        n = 0
        while True:
            s = c.post("/entity/versions/_search", headers=ARR, json={
                "filters": [["project", "is", {"type": "Project", "id": SANDBOX}],
                            ["code", "starts_with", prefix]],
                "fields": ["code"], "page": {"size": 150}})
            d = s.json().get("data", [])
            if not d:
                return n
            dr = batch([{"request_type": "delete", "entity": "Version", "record_id": x["id"]}
                        for x in d])
            if not dr.ok:
                raise SystemExit(f"could not clean {prefix}: {err(dr)}")
            n += len(d)

    rows.append("\n=== can one batch reference a row it creates?")
    rows.append("  request 0 creates a Shot; request 1 is a Version whose entity points at it.")
    for label, ref, extra in (
            ("index as $0", {"type": "Shot", "id": "$0"}, {}),
            ("negative index", {"type": "Shot", "id": -1}, {}),
            ("index as int str", {"type": "Shot", "id": "0"}, {}),
            ("uuid, echoed key", {"type": "Shot", "uuid": "u1"}, {"uuid": "u1"}),
            ("uuid as id", {"type": "Shot", "id": "u1"}, {"uuid": "u1"})):
        req0 = {"request_type": "create", "entity": "Shot",
                "data": {"project": {"type": "Project", "id": SANDBOX}, "code": f"{P}_dep"}}
        req0.update(extra)
        r = batch([req0, {"request_type": "create", "entity": "Version",
                          "data": {"project": {"type": "Project", "id": SANDBOX},
                                   "code": f"{P}_dep_v", "entity": ref}}])
        track(r)
        rows.append(f"  {label:<18} {r.status_code} {err(r) if not r.ok else 'created'}")

    rows.append("\n=== the two-batch sequence a dependent create actually needs")
    r = batch([{"request_type": "create", "entity": "Shot",
                "data": {"project": {"type": "Project", "id": SANDBOX}, "code": f"{P}_sh010",
                         "description": "batch 1"}}])
    track(r)
    shot_id = r.json()["data"][0]["data"]["id"]
    rows.append(f"  batch 1  {r.status_code}  {line(r.json()['data'][0])}")

    r = batch([{"request_type": "create", "entity": "Version",
                "data": {"project": {"type": "Project", "id": SANDBOX}, "code": f"{P}_v001",
                         "entity": {"type": "Shot", "id": shot_id}, "sg_status_list": "rev"}},
               {"request_type": "create", "entity": "Version",
                "data": {"project": {"type": "Project", "id": SANDBOX}, "code": f"{P}_v002",
                         "entity": {"type": "Shot", "id": shot_id}, "sg_status_list": "rev"}},
               {"request_type": "update", "entity": "Shot", "record_id": shot_id,
                "data": {"description": "batch 2"}}])
    track(r)
    rows.append(f"  batch 2  {r.status_code}")
    for i, row in enumerate(r.json()["data"]):
        rows.append(f"    row {i}  {line(row)}")
    d = r.json()["data"][0]["data"]
    rows.append(f"    create row body:\n{_lib.dump(r.json()['data'][0], 900)}")
    _lib.note_from(r.json())
    v1, v2 = [row["data"]["id"] for row in r.json()["data"][:2]]

    rows.append("\n=== is the response in request order?")
    rows.append("  update an old row, create a new one, update, create, delete: if the rows come back")
    rows.append("  sorted by id or grouped by type the interleaving breaks.")
    r = batch([{"request_type": "update", "entity": "Version", "record_id": v1,
                "data": {"description": "ord 0"}},
               {"request_type": "create", "entity": "Version",
                "data": {"project": {"type": "Project", "id": SANDBOX}, "code": f"{P}_ord1"}},
               {"request_type": "update", "entity": "Version", "record_id": v2,
                "data": {"description": "ord 2"}},
               {"request_type": "create", "entity": "Version",
                "data": {"project": {"type": "Project", "id": SANDBOX}, "code": f"{P}_ord3"}},
               {"request_type": "update", "entity": "Shot", "record_id": shot_id,
                "data": {"description": "ord 4"}}])
    track(r)
    for i, row in enumerate(r.json()["data"]):
        d = row.get("data", row)
        rows.append(f"    row {i}  {kind(row):<6} type={d.get('type')} id={d.get('id')} "
                    f"desc={(d.get('attributes') or {}).get('description')!r}")

    rows.append("\n  two creates sharing one code: what distinguishes the response rows")
    r = batch([{"request_type": "create", "entity": "Version",
                "data": {"project": {"type": "Project", "id": SANDBOX}, "code": f"{P}_same",
                         "description": "first"}},
               {"request_type": "create", "entity": "Version",
                "data": {"project": {"type": "Project", "id": SANDBOX}, "code": f"{P}_same",
                         "description": "second"}}])
    track(r)
    for i, row in enumerate(r.json()["data"]):
        a = row["data"]["attributes"]
        rows.append(f"    row {i}  id={row['data']['id']} code={a.get('code')!r} "
                    f"description={a.get('description')!r}")

    rows.append("\n=== what a batch create does not validate")
    rows.append("  probe 012: POST /entity/versions without project is a 400. In a batch:")
    r = c.post("/entity/versions", json={"code": f"{P}_noproj_single"})
    rows.append(f"  POST /entity/versions, no project   {r.status_code} {err(r)}")
    r = batch([{"request_type": "create", "entity": "Version",
                "data": {"code": f"{P}_noproj"}}])
    orphan = r.json()["data"][0]["data"]["id"]
    made.add("versions", orphan)
    rows.append(f"  batch create, no project           {r.status_code} id={orphan}")
    rows.append(f"    create row relationships: {sorted(r.json()['data'][0]['data']['relationships'])}")
    g = c.get(f"/entity/versions/{orphan}", params={"fields": "code,project"})
    d = g.json().get("data")
    rows.append(f"    GET it back: {g.status_code} " + (
        f"code={d['attributes'].get('code')!r} "
        f"project={json.dumps((d.get('relationships') or {}).get('project'))}" if d else err(g)))
    s = c.post("/entity/versions/_search", headers=ARR, json={
        "filters": [["code", "is", f"{P}_noproj"]], "fields": ["code"]})
    rows.append(f"    site-wide _search for it: {s.status_code} rows={len(s.json().get('data', []))}")
    rows.append("  and an entity link pointing at an id that does not exist:")
    r = c.post("/entity/versions", json={"project": {"type": "Project", "id": SANDBOX},
                                         "code": f"{P}_dangling_single",
                                         "entity": {"type": "Shot", "id": 999999999}})
    if r.ok:
        made.add("versions", r.json()["data"]["id"])
    rows.append(f"  POST /entity/versions              {r.status_code} {err(r) if not r.ok else 'created'}")
    r = batch([{"request_type": "create", "entity": "Version",
                "data": {"project": {"type": "Project", "id": SANDBOX}, "code": f"{P}_dangling",
                         "entity": {"type": "Shot", "id": 999999999}}}])
    track(r)
    rows.append(f"  batch create                       {r.status_code} "
                f"{err(r) if not r.ok else 'created'}")

    rows.append("\n=== atomicity: one bad request among good ones")
    rows.append("  each round resets first: the sentinel row is deleted and the update target is set")
    rows.append("  back to 'before', so the counts below are that round's alone.")
    for label, bad in (
            ("update of id 999999999", {"request_type": "update", "entity": "Version",
                                        "record_id": 999999999, "data": {"description": "x"}}),
            ("delete of id 999999999", {"request_type": "delete", "entity": "Version",
                                        "record_id": 999999999}),
            ("create unknown field", {"request_type": "create", "entity": "Version",
                                      "data": {"project": {"type": "Project", "id": SANDBOX},
                                               "code": f"{P}_atomic_c", "sg_not_a_field": 1}}),
            ("create bad status", {"request_type": "create", "entity": "Version",
                                   "data": {"project": {"type": "Project", "id": SANDBOX},
                                            "code": f"{P}_atomic_d",
                                            "sg_status_list": "not_a_status"}})):
        c.put(f"/entity/versions/{v1}", json={"description": "before"})
        r = batch([{"request_type": "create", "entity": "Version",
                    "data": {"project": {"type": "Project", "id": SANDBOX},
                             "code": f"{P}_atomic", "description": "should not survive"}},
                   bad,
                   {"request_type": "update", "entity": "Version", "record_id": v1,
                    "data": {"description": "after"}}])
        s = c.post("/entity/versions/_search", headers=ARR, json={
            "filters": [["project", "is", {"type": "Project", "id": SANDBOX}],
                        ["code", "starts_with", f"{P}_atomic"]], "fields": ["code"]})
        left = c.get(f"/entity/versions/{v1}",
                     params={"fields": "description"}).json()["data"]["attributes"]["description"]
        rows.append(f"  {label:<24} {r.status_code} {err(r) if not r.ok else 'every row applied'}")
        rows.append(f"  {'':<24} rows the two good requests left: {len(s.json()['data'])} created, "
                    f"row {v1} description {left!r}")
        purge(f"{P}_atomic")

    rows.append("\n=== does batch delete behave like DELETE /entity/<type>/{id}?")
    r = batch([{"request_type": "create", "entity": "Version",
                "data": {"project": {"type": "Project", "id": SANDBOX}, "code": f"{P}_del_a"}},
               {"request_type": "create", "entity": "Version",
                "data": {"project": {"type": "Project", "id": SANDBOX}, "code": f"{P}_del_b"}}])
    track(r)
    a, b = [row["data"]["id"] for row in r.json()["data"]]
    r = batch([{"request_type": "delete", "entity": "Version", "record_id": a}])
    rows.append(f"  batch delete   {r.status_code} {json.dumps(r.json()['data'][0])}")
    rows.append(f"  GET that id    {c.get(f'/entity/versions/{a}').status_code}")
    r = batch([{"request_type": "delete", "entity": "Version", "record_id": a}])
    rows.append(f"  delete it again {r.status_code} {err(r) if not r.ok else json.dumps(r.json()['data'][0])}")
    dr = c.delete(f"/entity/versions/{b}")
    rows.append(f"  DELETE verb    {dr.status_code}, body {len(dr.content)}b {dr.text!r}")
    rows.append(f"  GET that id    {c.get(f'/entity/versions/{b}').status_code}")

    rows.append("\n=== the same count question with rows that do commit")
    for n in (200, 500, 1001):
        reqs = [{"request_type": "create", "entity": "Version",
                 "data": {"project": {"type": "Project", "id": SANDBOX},
                          "code": f"{P}_n{n}_{i}"}} for i in range(n)]
        t0 = time.time()
        try:
            r = batch(reqs)
            note = f"{r.status_code} rows={len(r.json().get('data', []))}"
        except requests.exceptions.ReadTimeout:
            note = "no response: the client gave up at its 60s read timeout"
        rows.append(f"  n={n:<5} {time.time() - t0:>5.1f}s  {note}  "
                    f"rows that committed: {purge(f'{P}_n{n}_')}")

    # Whatever a failed attempt or a surprise success left, delete it too.
    for slug in ("versions", "shots"):
        s = c.post(f"/entity/{slug}/_search", headers=ARR, json={
            "filters": [["project", "is", {"type": "Project", "id": SANDBOX}],
                        ["code", "starts_with", P]], "fields": ["code"], "page": {"size": 200}})
        known = {i for sl, i in made.rows if sl == slug}
        strays = [d["id"] for d in s.json().get("data", []) if d["id"] not in known]
        for i in strays:
            made.add(slug, i)
        rows.append(f"\n  strays swept in {slug}: {strays}")

_lib.emit("029_batch", "\n".join(rows), env)
