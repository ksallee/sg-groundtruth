"""Q: how does a client add to and remove from a multi_entity field without destroying the links it
did not mean to touch?

A survey of production code found this pattern in at least three repositories and the failure is
silent. `field_types/multi_entity` measured the mechanics: a bare list replaces, the body wrapper
adds and removes in place, and both query-string spellings return 200 having replaced anyway. Nobody
wrote down the procedure. This probe walks it once: the safe append, the read-modify-write that loses
a concurrent add, the other-parents query that has to run before an inherited link is stripped off a
child, the clear, and the re-read that confirms any of it (probe 028).

It also tests the survey's second claim, that a multi_entity field intermittently reads back as a
single mapping rather than a list, by tallying the JSON type of `relationships.<field>.data` over
repeated reads at three cardinalities and through both read paths.
"""
import json
from collections import Counter

import _lib

env = _lib.load_env()
c = _lib.client()
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
rows = []


def err(r):
    return json.dumps(r.json().get("errors", r.json()))


def prop(p, key, default=None):
    return (p.get(key) or {}).get("value", default)


def field_schema(entity_type, field):
    d = c.get(f"/schema/{entity_type}/fields/{field}").json()["data"]
    p = d.get("properties", {})
    return {"data_type": prop(d, "data_type"), "editable": prop(d, "editable"),
            "valid_types": prop(p, "valid_types", []) or []}


def rel_shape(row, field):
    """The JSON type of relationships.<field>.data, which is what a client branches on."""
    rel = (row.get("relationships") or {}).get(field)
    if rel is None:
        return "absent"
    return type(rel.get("data")).__name__


def members(entity_slug, entity_id, field):
    r = c.get(f"/entity/{entity_slug}/{entity_id}", params={"fields": field})
    _lib.note_from(r.json())
    d = r.json()["data"]
    return [x["id"] for x in (d["relationships"][field]["data"] or [])]


def claimants(parent_slug, field, child, exclude_id=None):
    """Which parents still link this child. The filter is `is` with one entity hash; `in` matches
    rows that link nothing when the id is unresolvable (`field_types/multi_entity`)."""
    filters = [[field, "is", child]]
    if exclude_id is not None:
        filters.append(["id", "is_not", exclude_id])
    r = c.post(f"/entity/{parent_slug}/_search", headers=ARR,
               json={"filters": filters, "fields": "id", "page": {"size": 500}})
    if not r.ok:
        return r.status_code, err(r)
    return r.status_code, [row["id"] for row in r.json()["data"]]


# ---------------------------------------------------------------- 1. the two fields, read-only
rows.append("=== 1. the fields this walks, from /schema/<Type>/fields/<field>")
for t, f in (("Playlist", "versions"), ("Version", "playlists"), ("Note", "note_links")):
    s = field_schema(t, f)
    vt = s["valid_types"] if len(s["valid_types"]) <= 4 else f"{len(s['valid_types'])} types"
    rows.append(f"  {t}.{f:<12} data_type={s['data_type']!r} editable={s['editable']} valid_types={vt}")
single = field_schema("Version", "entity")
rows.append(f"  Version.entity      data_type={single['data_type']!r} "
            f"valid_types={len(single['valid_types'])} types   <- single, for the shape comparison")

# ---------------------------------------------------------------- 2. the other-parents query, read-only
rows.append("\n=== 2. the other-parents query, on a read-only project")
SAMPLES = _lib.sample_projects(c, env)
SAMPLE, sample_rows = SAMPLES[0], []
for pid in SAMPLES:
    r = c.post("/entity/notes/_search", headers=ARR, json={
        "filters": [["project", "is", {"type": "Project", "id": pid}], ["note_links", "is_not", None]],
        "fields": "note_links", "page": {"size": 100}})
    _lib.note_from(r.json())
    if r.ok and r.json()["data"]:
        SAMPLE, sample_rows = pid, r.json()["data"]
        break
rows.append(f"  POST /entity/notes/_search  [['note_links','is_not',None]] on project {SAMPLE} "
            f"-> {r.status_code}, {len(sample_rows)} Notes linking something")
child, left = None, None
for row in sample_rows:
    data = row["relationships"]["note_links"]["data"]
    if data:
        child = {"type": data[0]["type"], "id": data[0]["id"]}
        left = row["id"]
        break
if child:
    code, all_p = claimants("notes", "note_links", child)
    code2, others = claimants("notes", "note_links", child, exclude_id=left)
    rows.append(f"  every Note claiming {child['type']} {child['id']}      -> {code}, {all_p}")
    rows.append(f"  the same, excluding the one it just left ({left}) -> {code2}, {others}")
    r = c.post("/entity/notes/_search", headers=ARR, json={
        "filters": [["note_links", "is", child["id"]]], "fields": "id"})
    rows.append(f"  a bare id instead of an entity hash -> {r.status_code} "
                f"{err(r) if not r.ok else len(r.json()['data'])}")
    r = c.post("/entity/notes/_search", headers=ARR, json={
        "filters": [["note_links", "in", [{"type": child["type"], "id": 99999999}]]], "fields": "id"})
    rows.append(f"  `in` with one unresolvable id      -> {r.status_code}, "
                f"{len(r.json()['data']) if r.ok else err(r)} rows, the negative control that lies")
else:
    rows.append("  no Note on the sample projects links anything; the write half builds its own")

# ---------------------------------------------------------------- 3. shape sweep, read-only
rows.append("\n=== 3. does a multi_entity field ever read back as a mapping? read-only sweep")
shapes, card = Counter(), Counter()
for row in sample_rows:
    shapes[rel_shape(row, "note_links")] += 1
    d = row["relationships"]["note_links"]["data"]
    card[len(d) if isinstance(d, list) else "not a list"] += 1
rows.append(f"  _search Note.note_links over {len(sample_rows)} rows: {dict(shapes)}")
rows.append(f"    member counts: {dict(sorted(card.items(), key=str))}, single-member rows included")
for row in sample_rows[:20]:
    g = c.get(f"/entity/notes/{row['id']}", params={"fields": "note_links"}).json()["data"]
    shapes[f"GET:{rel_shape(g, 'note_links')}"] += 1
rows.append(f"    the same rows re-read one at a time by GET: "
            f"{dict((k, v) for k, v in shapes.items() if k.startswith('GET:'))}")

r = c.post("/entity/versions/_search", headers=ARR, json={
    "filters": [["project", "is", {"type": "Project", "id": SAMPLE}]],
    "fields": "playlists,tasks,entity", "page": {"size": 100}})
_lib.note_from(r.json())
if r.ok:
    multi = Counter()
    for row in r.json()["data"]:
        for f in ("playlists", "tasks"):
            multi[f"{f}:{rel_shape(row, f)}"] += 1
        multi[f"entity:{rel_shape(row, 'entity')}"] += 1
    rows.append(f"  _search over {len(r.json()['data'])} Versions: {dict(multi)}")
    rows.append("    `entity` is the single entity field on the same rows: a mapping, and a NoneType"
                " when unset")

if not _lib.writes_allowed():
    rows.append("\n(read-only run; the append, remove and clear walk needs --write)")
    _lib.emit("037_multi_entity_safely", "\n".join(rows), env)
    raise SystemExit(0)

# ---------------------------------------------------------------- the walk, in the sandbox
SANDBOX = _lib.sandbox_id(c, env)
rows.append(f"\n=== 4. sandbox project {SANDBOX}: two playlists, four Versions, one review Note")

with _lib.Created(c) as made:
    def playlist(code, versions):
        r = c.post("/entity/playlists", json={
            "project": {"type": "Project", "id": SANDBOX}, "code": code, "versions": versions})
        _lib.note_from(r.json())
        return made.add("playlists", r.json()["data"]["id"])

    def version(code):
        r = c.post("/entity/versions", json={
            "project": {"type": "Project", "id": SANDBOX}, "code": code})
        _lib.note_from(r.json())
        return made.add("versions", r.json()["data"]["id"])

    V = {tag: version(f"zzprobe_037_v_{tag}") for tag in ("a", "b", "c", "d")}
    H = {tag: {"type": "Version", "id": i} for tag, i in V.items()}
    LEFT = playlist("zzprobe_037_pl_left", [H["a"], H["b"]])
    OTHER = playlist("zzprobe_037_pl_other", [H["a"]])
    r = c.post("/entity/notes", json={
        "project": {"type": "Project", "id": SANDBOX}, "subject": "zzprobe_037_review",
        "note_links": [H["a"], H["b"]]})
    _lib.note_from(r.json())
    NOTE = made.add("notes", r.json()["data"]["id"])
    NAMES = {i: tag for tag, i in V.items()}
    PL = {LEFT: "left", OTHER: "other"}

    def show(label):
        left = [NAMES.get(i, i) for i in members("playlists", LEFT, "versions")]
        other = [NAMES.get(i, i) for i in members("playlists", OTHER, "versions")]
        note = [NAMES.get(i, i) for i in members("notes", NOTE, "note_links")]
        rows.append(f"  {label:<44} left={left} other={other} note={note}")

    def reset():
        c.put(f"/entity/playlists/{LEFT}", json={
            "versions": {"multi_entity_update_mode": "set", "value": [H["a"], H["b"]]}})

    rows.append(f"  Versions a={V['a']} b={V['b']} c={V['c']} d={V['d']}")
    rows.append(f"  playlists left={LEFT} other={OTHER}   Note {NOTE} note_links=[a, b]")
    show("start")

    # ------------------------------------------------------------ 5. append
    rows.append("\n=== 5. append")
    r = c.put(f"/entity/playlists/{LEFT}",
              json={"versions": {"multi_entity_update_mode": "add", "value": [H["c"]]}})
    rows.append(f"  body add [c]                     -> {r.status_code}")
    show("after add [c]")
    r = c.put(f"/entity/playlists/{LEFT}",
              json={"versions": {"multi_entity_update_mode": "add", "value": [H["c"]]}})
    rows.append(f"  the same add again               -> {r.status_code}")
    show("after the duplicate add")

    reset()
    rows.append("\n  the read-modify-write alternative, with a concurrent writer in the window")
    seen = members("playlists", LEFT, "versions")
    rows.append(f"    reader reads versions -> {[NAMES.get(i, i) for i in seen]}")
    c.put(f"/entity/playlists/{LEFT}",
          json={"versions": {"multi_entity_update_mode": "add", "value": [H["c"]]}})
    rows.append("    a concurrent writer adds [c]")
    r = c.put(f"/entity/playlists/{LEFT}",
              json={"versions": [{"type": "Version", "id": i} for i in seen] + [H["d"]]})
    rows.append(f"    the reader PUTs its bare list plus [d] -> {r.status_code}")
    show("    after the read-modify-write")

    reset()
    seen = members("playlists", LEFT, "versions")
    c.put(f"/entity/playlists/{LEFT}",
          json={"versions": {"multi_entity_update_mode": "add", "value": [H["c"]]}})
    r = c.put(f"/entity/playlists/{LEFT}",
              json={"versions": {"multi_entity_update_mode": "add", "value": [H["d"]]}})
    rows.append(f"    the same race, appending with the wrapper -> {r.status_code}")
    show("    after the wrapper append")

    reset()
    rows.append("\n  the mode spelled in the query string, on the same field")
    r = c.put(f"/entity/playlists/{LEFT}", params={"multi_entity_update_mode": "add"},
              json={"versions": [H["d"]]})
    rows.append(f"    PUT ?multi_entity_update_mode=add  versions=[d] -> {r.status_code}")
    show("    after the query-string add")

    # ------------------------------------------------------------ 6. remove
    reset()
    rows.append("\n=== 6. remove, and the other-parents check before stripping the child")
    show("reset")
    for tag in ("a", "b"):
        r = c.put(f"/entity/playlists/{LEFT}",
                  json={"versions": {"multi_entity_update_mode": "remove", "value": [H[tag]]}})
        code, others = claimants("playlists", "versions", H[tag], exclude_id=LEFT)
        named = [PL.get(i, i) for i in others] if isinstance(others, list) else others
        rows.append(f"  remove [{tag}] from left -> {r.status_code}; other playlists claiming {tag}: "
                    f"{code}, {named}  -> {'keep' if others else 'strip'} the Note link")
        if not others:
            r = c.put(f"/entity/notes/{NOTE}",
                      json={"note_links": {"multi_entity_update_mode": "remove", "value": [H[tag]]}})
            rows.append(f"    remove [{tag}] from Note.note_links -> {r.status_code}")
        show(f"  after {tag}")
    r = c.put(f"/entity/playlists/{LEFT}",
              json={"versions": {"multi_entity_update_mode": "remove", "value": [H["a"]]}})
    rows.append(f"  remove [a] again, now absent -> {r.status_code}, a no-op")

    rows.append("\n  the same removal written as a bare list, on the child's field")
    r = c.put(f"/entity/notes/{NOTE}", json={"note_links": [H["c"]]})
    rows.append(f"    PUT note_links [c] -> {r.status_code}")
    show("    after the bare list")

    # ------------------------------------------------------------ 7. clear
    rows.append("\n=== 7. clear")
    for slug, ident, field, seed in (("playlists", LEFT, "versions", [H["a"], H["b"]]),
                                     ("notes", NOTE, "note_links", [H["a"], H["b"]])):
        for label, value in (("[]", []),
                             ('set wrapper, value []', {"multi_entity_update_mode": "set", "value": []}),
                             ("null", None)):
            c.put(f"/entity/{slug}/{ident}", json={field: {"multi_entity_update_mode": "set",
                                                           "value": seed}})
            r = c.put(f"/entity/{slug}/{ident}", json={field: value})
            after = members(slug, ident, field)
            rows.append(f"  {slug[:-1]}.{field} <- {label:<22} -> {r.status_code} "
                        f"{'reads back ' + str([NAMES.get(i, i) for i in after]) if r.ok else err(r)}")

    # ------------------------------------------------------------ 8. shape sweep in the sandbox
    rows.append("\n=== 8. the shape of relationships.versions.data at three cardinalities, 12 reads each")
    for label, value in (("0 members", []), ("1 member", [H["a"]]), ("2 members", [H["a"], H["b"]])):
        c.put(f"/entity/playlists/{LEFT}",
              json={"versions": {"multi_entity_update_mode": "set", "value": value}})
        got = Counter()
        for _ in range(12):
            g = c.get(f"/entity/playlists/{LEFT}", params={"fields": "versions"}).json()["data"]
            got[f"GET:{rel_shape(g, 'versions')}"] += 1
            s = c.post("/entity/playlists/_search", headers=ARR, json={
                "filters": [["id", "is", LEFT]], "fields": "versions"}).json()["data"][0]
            got[f"_search:{rel_shape(s, 'versions')}"] += 1
        rows.append(f"  {label:<10} {dict(got)}")
    hash_hdr = {"Content-Type": "application/vnd+shotgun.api3_hash+json"}
    s = c.post("/entity/playlists/_search", headers=hash_hdr, json={
        "filters": {"logical_operator": "and", "conditions": [["id", "is", LEFT]]},
        "fields": "versions"})
    rows.append(f"  api3_hash _search -> {s.status_code}, "
                f"{rel_shape(s.json()['data'][0], 'versions') if s.ok else err(s)}")
    g = c.get(f"/entity/playlists/{LEFT}", params={"fields": "versions.Version.code"}).json()["data"]
    rows.append(f"  ?fields=versions.Version.code -> attributes keys {list(g['attributes'].keys())}, "
                f"relationships keys {list(g.get('relationships', {}).keys())} (probe 016)")
    for n in (1, 2):
        c.put(f"/entity/playlists/{LEFT}", json={"versions": {"multi_entity_update_mode": "set",
                                                              "value": [H["a"], H["b"]][:n]}})
        r = c.get(f"/entity/playlists/{LEFT}/relationships/versions")
        body = r.json() if r.ok else {}
        rows.append(f"  GET .../relationships/versions with {n} member(s) -> {r.status_code}, "
                    f"data is {type(body.get('data')).__name__}")

    # ------------------------------------------------------------ 9. verify
    rows.append("\n=== 9. the re-read that confirms (probe 028)")
    c.put(f"/entity/playlists/{LEFT}",
          json={"versions": {"multi_entity_update_mode": "set", "value": [H["a"]]}})
    want = {V["a"], V["c"]}
    r = c.put(f"/entity/playlists/{LEFT}",
              json={"versions": {"multi_entity_update_mode": "add", "value": [H["c"]]}})
    got = set(members("playlists", LEFT, "versions"))
    rows.append(f"  body add     -> {r.status_code}; wanted {sorted(want)} reads back {sorted(got)} "
                f"{got == want}")
    c.put(f"/entity/playlists/{LEFT}",
          json={"versions": {"multi_entity_update_mode": "set", "value": [H["a"]]}})
    r = c.put(f"/entity/playlists/{LEFT}", params={"multi_entity_update_mode": "add"},
              json={"versions": [H["c"]]})
    got = set(members("playlists", LEFT, "versions"))
    rows.append(f"  query-string -> {r.status_code}; wanted {sorted(want)} reads back {sorted(got)} "
                f"{got == want}")

_lib.emit("037_multi_entity_safely", "\n".join(rows), env)
