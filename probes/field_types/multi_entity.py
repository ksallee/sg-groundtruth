"""Q: how does a `multi_entity` field read, write, clear and filter?

The headline is the update semantics. A multi-valued link is the one type where "PUT the field" is
ambiguous — replace the list, or merge into it? — and a client that guesses wrong either loses links or
never removes one. So the write half establishes replace-vs-merge first, then hunts for an incremental
add/remove: a relationships endpoint, a request-body verb, a query option, or nothing at all.

The rest is the matrix: value shapes (hashes, bare ints, duplicates, a foreign type), clear (`[]` vs
`null`), the read shape under `relationships`, and the filter semantics for a row that links TWO rows —
where `in`, `not_in` and `is` mean genuinely different things than they do on a single-valued field.

Read-only half — schema, read shape, the operator list, and probe 016's silent-dotted-read trap — runs
without --write.
"""
import json
import sys
import time

sys.path.insert(0, __file__.rsplit("/", 2)[0])
import _lib  # noqa: E402

env = _lib.load_env()
c = _lib.client()
PROJECT = _lib.sample_projects(c, env)[0]
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
JSN = {"Content-Type": "application/json"}
FIELD = "sg_ai_generated_from"    # multi_entity of Version — a Version can link Versions, so one
                                  # entity type builds every row this probe needs (probe 019 made it).
CANDIDATES = ("tasks", "playlists", "sg_ai_generated_from", "version_sg_ai_generated_from_versions",
              "notes", "attachment_links", "entity")
rows = []


def err(r):
    """Whole errors[] object. Probe 017 lost the legal-operator list for months to a [:120] slice."""
    try:
        return json.dumps(r.json().get("errors", r.json()), indent=1)
    except ValueError:
        return r.text


def search(project, filt, fields=("code", FIELD), size=200):
    return c.post("/entity/versions/_search", headers=ARR,
                  json={"filters": [["project", "is", {"type": "Project", "id": project}]] + filt,
                        "fields": list(fields), "page": {"size": size}})


rows.append("=== schema: the stock multi_entity fields on Version")
schema = c.get("/schema/Version/fields").json()["data"]
allme = sorted(k for k, v in schema.items() if (v.get("data_type") or {}).get("value") == "multi_entity")
rows.append(f"  every multi_entity field on Version ({len(allme)}): {allme}")
rows.append(f"  {'field':<24}{'data_type':<14}{'editable':<10}valid_types")
for f in CANDIDATES:
    d = schema.get(f)
    if not d:
        rows.append(f"  {f:<24}<absent from Version/fields>")
        continue
    g = lambda k: (d.get(k) or {}).get("value")  # noqa: E731
    vt = ((d.get("properties") or {}).get("valid_types") or {}).get("value")
    rows.append(f"  {f:<24}{str(g('data_type')):<14}{str(g('editable')):<10}{vt}")
rows.append("  probe 019: CREATING a multi_entity takes exactly one valid_type; stock ones carry more.")

rows.append("\n=== the API enumerates its own operators: send one that cannot exist")
for f in ("tasks", FIELD):
    r = search(PROJECT, [[f, "definitely_not_an_operator", None]])
    rows.append(f"  [[{f!r}, 'definitely_not_an_operator', None]] -> {r.status_code}")
    rows.append("   " + err(r).replace("\n", "\n   "))

rows.append("\n=== read: where a multi_entity value lands, and its exact shape")
got = search(PROJECT, [], fields=("code", "tasks", "playlists", FIELD), size=100)
data = got.json()["data"]
_lib.note_from(data)
filled = [d for d in data if (d.get("relationships", {}).get("tasks", {}).get("data"))]
for d in (filled or data)[:1]:
    rows.append(f"  keys on the row: {sorted(d)}")
    rows.append(f"  attributes: {sorted(d['attributes'])}   <- multi_entity is NOT here")
    rows.append(f"  relationships keys: {sorted(d.get('relationships', {}))}")
    rel = d.get("relationships", {}).get("tasks", {})
    rows.append(f"  relationships.tasks = {json.dumps(rel)[:600]}")
counts = {}
for d in data:
    n = len((d.get("relationships", {}).get("tasks", {}) or {}).get("data") or [])
    counts[n] = counts.get(n, 0) + 1
rows.append(f"  over {len(data)} rows, len(relationships.tasks.data) histogram: "
            f"{dict(sorted(counts.items()))}")
empty = [d for d in data if (d.get("relationships", {}).get(FIELD, {}) or {}).get("data") == []]
rows.append(f"  an UNSET multi_entity reads back as {json.dumps((empty or data)[0].get('relationships', {}).get(FIELD))}"
            f"  <- empty list, never null, never absent")

rows.append("\n=== probe 016's trap, restated concretely: dotted READ vs dotted FILTER")
r = c.get("/entity/versions", params={"fields": "code,tasks.Task.content,entity.Shot.code",
                                      "filter[project.Project.id]": PROJECT, "page[size]": 5})
attrs = sorted((r.json()["data"] or [{}])[0].get("attributes", {}))
rows.append(f"  GET ?fields=code,tasks.Task.content,entity.Shot.code -> {r.status_code}, "
            f"attributes returned: {attrs}")
rows.append("  ^ the single-entity hop is present; the multi_entity hop is SILENTLY ABSENT (probe 016)")
for label, filt in [("NEG tasks.Task.content is ZZZNOPE", [["tasks.Task.content", "is", "ZZZNOPE"]]),
                    ("    tasks.Task.content is_not ZZZNOPE", [["tasks.Task.content", "is_not", "ZZZNOPE"]])]:
    rr = search(PROJECT, filt, fields=("code",), size=200)
    rows.append(f"  FILTER {label:<38}-> {rr.status_code} "
                f"{len(rr.json().get('data', [])) if rr.ok else err(rr)[:200]} rows")

if not _lib.writes_allowed():
    rows.append("\n(read-only run: update semantics, value shapes, clear and the filter matrix need --write)")
else:
    SANDBOX = _lib.sandbox_id(c, env)
    RUN = f"zzprobe_multi_entity_{int(time.time()) % 100000}"
    made = []

    def create(code, body=None):
        r = c.post("/entity/versions",
                   json={"project": {"type": "Project", "id": SANDBOX}, "code": code, **(body or {})})
        if r.ok:
            made.append(r.json()["data"]["id"])
            return r.json()["data"]["id"], None
        return None, err(r)

    def put(vid, value, field=FIELD, params=None, body=None, method="PUT"):
        return c.request(method, f"/entity/versions/{vid}",
                         json=(body if body is not None else {field: value}),
                         headers=JSN, params=params)

    def read(vid, field=FIELD):
        r = c.get(f"/entity/versions/{vid}", params={"fields": field}).json()["data"]
        if field in r.get("relationships", {}):
            return [(x["type"], x["id"]) for x in (r["relationships"][field].get("data") or [])]
        if field in r.get("attributes", {}):
            return f"<in attributes: {r['attributes'][field]!r}>"
        return "<key absent from both attributes and relationships>"

    def h(vid):
        return {"type": "Version", "id": vid}

    A, _ = create(f"{RUN}_target_a")
    B, _ = create(f"{RUN}_target_b")
    T, _ = create(f"{RUN}_scratch")
    rows.append(f"\n=== three throwaway Versions in the sandbox: A, B (link targets) and T (mutated)")
    rows.append(f"  created ids A B T; T starts with {FIELD} = {read(T)}")

    rows.append("\n=== THE HEADLINE: does a second PUT replace the list or merge into it?")
    put(T, [h(A)])
    rows.append(f"  PUT [A]                          -> {read(T)}")
    r = put(T, [h(B)])
    rows.append(f"  PUT [B]  ({r.status_code})                    -> {read(T)}")
    rows.append("  ^ REPLACE if this shows B alone; MERGE if it shows A and B")

    rows.append("\n=== is there an incremental add/remove at all?")
    put(T, [h(A)])
    for label, fn in [
        ("PATCH /entity/versions/{id} body [B]",
         lambda: put(T, [h(B)], method="PATCH")),
        ("PUT body {'add': [B]}",
         lambda: put(T, None, body={FIELD: {"add": [h(B)]}})),
        ("PUT body {'remove': [A]}",
         lambda: put(T, None, body={FIELD: {"remove": [h(A)]}})),
        ("PUT ?options[multi_entity_update_modes][f]=add",
         lambda: put(T, [h(B)], params={f"options[multi_entity_update_modes][{FIELD}]": "add"})),
        ("PUT ?multi_entity_update_mode=add",
         lambda: put(T, [h(B)], params={"multi_entity_update_mode": "add"})),
        ("PUT body options.multi_entity_update_modes",
         lambda: put(T, None, body={FIELD: [h(B)],
                                    "options": {"multi_entity_update_modes": {FIELD: "add"}}})),
        ("GET /entity/versions/{id}/relationships/f",
         lambda: c.get(f"/entity/versions/{T}/relationships/{FIELD}")),
        ("POST /entity/versions/{id}/relationships/f",
         lambda: c.post(f"/entity/versions/{T}/relationships/{FIELD}", headers=JSN,
                        json={"data": [h(B)]})),
        ("DELETE /entity/versions/{id}/relationships/f",
         lambda: c.request("DELETE", f"/entity/versions/{T}/relationships/{FIELD}", headers=JSN,
                           json={"data": [h(A)]})),
    ]:
        put(T, [h(A)])
        r = fn()
        rows.append(f"  {label:<48}-> {r.status_code}  now {read(T)}")
        if not r.ok:
            rows.append("   " + err(r).replace("\n", "\n   ")[:900])

    rows.append("\n=== the API named its own verb: 'invalid/missing string multi_entity_update_mode'")
    rows.append("  every dict sent as the field value is read as an update-mode wrapper, so find its keys")

    def mode(m, key, vals):
        return {FIELD: {"multi_entity_update_mode": m, key: vals}}

    for label, body in [
        ("{mode:'add', value:[B]}",     mode("add", "value", [h(B)])),
        ("{mode:'add', values:[B]}",    mode("add", "values", [h(B)])),
        ("{mode:'add', entities:[B]}",  mode("add", "entities", [h(B)])),
        ("{mode:'add', data:[B]}",      mode("add", "data", [h(B)])),
        ("{mode:'add', type,id inline}", {FIELD: {"multi_entity_update_mode": "add", **h(B)}}),
        ("{mode:'remove', value:[A]}",  mode("remove", "value", [h(A)])),
        ("{mode:'set', value:[B]}",     mode("set", "value", [h(B)])),
        ("{mode:'add', value:[A]} A present", mode("add", "value", [h(A)])),
        ("{mode:'remove', value:[B]} B absent", mode("remove", "value", [h(B)])),
        ("{mode:'add', value:[]}",      mode("add", "value", [])),
        ("{mode:'nonsense', value:[B]}", mode("nonsense", "value", [h(B)])),
    ]:
        put(T, [h(A)])
        r = put(T, None, body=body)
        rows.append(f"  PUT {FIELD} = {label:<32}-> {r.status_code}  now {read(T)}")
        if not r.ok:
            rows.append("   " + err(r).replace("\n", "\n   ")[:900])

    rows.append("\n=== value shapes: what the field accepts on the way in")
    for label, val in [
        ("[{type,id}, {type,id}]",     [h(A), h(B)]),
        ("[] (empty list)",            []),
        ("[{type,id}] single",         [h(A)]),
        ("duplicate [A, A]",           [h(A), h(A)]),
        ("bare ints [A, B]",           [A, B]),
        ("[{'id': A}] no type",        [{"id": A}]),
        ("bare hash {type,id}",        h(A)),
        ("mixed types [Version, Task]", [h(A), {"type": "Task", "id": 1}]),
        ("[{'type':'Version','id':99999999}]", [{"type": "Version", "id": 99999999}]),
        ("null",                       None),
        ("'' (empty string)",          ""),
        ("0 (int)",                    0),
    ]:
        r = put(T, val)
        rows.append(f"  {label:<38}{r.status_code:<6}reads back {read(T)}")
        if not r.ok:
            rows.append("   " + err(r).replace("\n", "\n   ")[:900])

    rows.append("\n=== clear: [] vs the three falsy spellings, and how each is refused")
    for label, val in [("[]", []), ("{mode:set,value:[]}", {"multi_entity_update_mode": "set",
                                                            "value": []}),
                       ("null", None), ('""', ""), ("0", 0)]:
        put(T, [h(A), h(B)])
        r = put(T, val)
        raw = c.get(f"/entity/versions/{T}", params={"fields": FIELD}).json()["data"]
        rows.append(f"  PUT {label:<20} -> {r.status_code}  relationships.{FIELD} = "
                    f"{json.dumps(raw.get('relationships', {}).get(FIELD))}")
        if not r.ok:
            rows.append("   " + err(r).replace("\n", "\n   "))
    r = put(T, None, body={"description": "untouched"})
    rows.append(f"  PUT with the key omitted -> {r.status_code}  reads back {read(T)}  "
                "<- omission is not a clear")

    rows.append("\n=== four rows that differ only in what they link")
    ids = {}
    for label, val in [("AB", [h(A), h(B)]), ("A_only", [h(A)]),
                       ("B_only", [h(B)]), ("empty", [])]:
        i, e = create(f"{RUN}_row_{label}", {FIELD: val})
        ids[i] = label
        rows.append(f"  {label:<8} created {e or ''} -> reads back {read(i)}")

    PRE = [["code", "starts_with", f"{RUN}_row"]]

    def which(filt):
        r = search(SANDBOX, PRE + filt, fields=("code",))
        if not r.ok:
            return f"ERR {r.status_code} " + err(r).replace("\n", " ")[:500]
        return sorted(ids.get(d["id"], f"?{d['id']}") for d in r.json()["data"]) or "[]"

    rows.append("\n=== filter matrix: which of the four rows each filter returns")
    rows.append("  (AB links both targets; A_only links A; B_only links B; empty links nothing)")
    for label, filt in [
        ("is A",                     [[FIELD, "is", h(A)]]),
        ("is B",                     [[FIELD, "is", h(B)]]),
        ("is None",                  [[FIELD, "is", None]]),
        ("is [A, B] (list)",         [[FIELD, "is", [h(A), h(B)]]]),
        ("is_not A",                 [[FIELD, "is_not", h(A)]]),
        ("is_not None",              [[FIELD, "is_not", None]]),
        ("in [A]",                   [[FIELD, "in", [h(A)]]]),
        ("in [A, B]",                [[FIELD, "in", [h(A), h(B)]]]),
        ("in [] (empty list)",       [[FIELD, "in", []]]),
        ("not_in [A]",               [[FIELD, "not_in", [h(A)]]]),
        ("not_in [A, B]",            [[FIELD, "not_in", [h(A), h(B)]]]),
        ("is A AND is B (two rows)", [[FIELD, "is", h(A)], [FIELD, "is", h(B)]]),
        ("type_is Version",          [[FIELD, "type_is", "Version"]]),
        ("type_is_not Version",      [[FIELD, "type_is_not", "Version"]]),
        ("name_contains _target_a",  [[FIELD, "name_contains", "_target_a"]]),
        ("in [bare int A]",          [[FIELD, "in", [A]]]),
        ("in [{'id': A}] no type",   [[FIELD, "in", [{"id": A}]]]),
        ("name_is <A code>",         [[FIELD, "name_is", f"{RUN}_target_a"]]),
        ("name_not_contains _target_a", [[FIELD, "name_not_contains", "_target_a"]]),
        ("NEG is id 99999999",       [[FIELD, "is", {"type": "Version", "id": 99999999}]]),
        ("NEG in [id 99999999]",     [[FIELD, "in", [{"type": "Version", "id": 99999999}]]]),
        ("in [A, id 99999999]",      [[FIELD, "in", [h(A), {"type": "Version", "id": 99999999}]]]),
        ("NEG name_contains ZZZNOPE", [[FIELD, "name_contains", "ZZZNOPE"]]),
        ("dotted .Version.code is <A code>",
         [[f"{FIELD}.Version.code", "is", f"{RUN}_target_a"]]),
        ("NEG dotted .Version.code is ZZZNOPE",
         [[f"{FIELD}.Version.code", "is", "ZZZNOPE"]]),
        ("no filter (baseline)",     []),
    ]:
        rows.append(f"  {label:<32}-> {which(filt)}")

    rows.append("\n=== and the dotted READ of that same path, on rows known to have a value")
    r = c.post("/entity/versions/_search", headers=ARR,
               json={"filters": PRE, "fields": ["code", f"{FIELD}.Version.code"], "page": {"size": 10}})
    rows.append(f"  _search fields=['code','{FIELD}.Version.code'] -> {r.status_code} "
                f"attributes: {sorted((r.json()['data'] or [{}])[0].get('attributes', {}))}")
    rows.append("  ^ same silent drop inside _search, not just GET ?fields")

    rows.append("\n=== the same interleaving, read-modify-write vs the add verb")
    put(T, [])
    before = read(T)                     # our read: []
    put(T, [h(B)])                       # a second client writes, between our read and our write
    put(T, [{"type": t, "id": i} for t, i in before] + [h(A)])   # our write, from the stale read
    rows.append(f"  RMW  we read {before}, another client PUT [B], we PUT [A] -> {read(T)}  <- B lost")
    put(T, [])
    put(T, None, body={FIELD: {"multi_entity_update_mode": "add", "value": [h(B)]}})
    put(T, None, body={FIELD: {"multi_entity_update_mode": "add", "value": [h(A)]}})
    rows.append(f"  add  same interleaving with two 'add' calls          -> {read(T)}  <- both kept")

    rows.append("\n=== cleanup")
    gone = [c.request("DELETE", f"/entity/versions/{i}").status_code for i in made]
    rows.append(f"  DELETE {len(made)} probe Versions -> {sorted(set(gone))}")
    rows.append(f"  filter after delete -> {which([])}")

report = "\n".join(str(x) for x in rows)
_lib.emit("field_types/multi_entity", report, env)
