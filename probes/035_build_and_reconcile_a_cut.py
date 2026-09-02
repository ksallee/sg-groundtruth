"""Q: how is a Cut written from an edit, read back into a timeline, and reconciled against the Cut
that is already there?

A survey of production code found three write implementations and two diff implementations across five
repositories. All three write in the same order, Cut then Shots then Versions then CutItems, and both
diffs decide create-versus-update on more than the presence of an id. Neither habit is documented, and
neither Cut nor CutItem has an entity-type card. This probe measures the whole loop: what each stage
needs from the one before, which CutItem fields hold the timeline, what the server derives and
validates, how a gap and an overlap read back, and what pairs an item across two edits.
"""
import json

import _lib

env = _lib.load_env()
c = _lib.client()
JSON = {"Content-Type": "application/json"}
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
rows = []

TIMELINE = ["cut_order", "edit_in", "edit_out", "cut_item_in", "cut_item_out", "cut_item_duration",
            "timecode_edit_in_text", "timecode_edit_out_text",
            "timecode_cut_item_in_text", "timecode_cut_item_out_text"]


def prop(f, key, default=None):
    """Schema properties are wrapped as {"value": x, "editable": bool}; valid_types is nested
    under `properties` rather than sitting at the top level (field_types/multi_entity)."""
    if key in f:
        return (f.get(key) or {}).get("value", default)
    return ((f.get("properties") or {}).get(key) or {}).get("value", default)


def fields(entity_type):
    return c.get(f"/schema/{entity_type}/fields").json()["data"]


def err(r):
    """Never truncate an error body: the 400 is the documentation."""
    try:
        return json.dumps(r.json().get("errors", r.json()))
    except ValueError:
        return r.text


# ---------------------------------------------------------------- 1. the schema, read-only
cut_f, item_f = fields("Cut"), fields("CutItem")
rows.append(f"=== 1. schema: Cut has {len(cut_f)} fields, CutItem {len(item_f)}")
rows.append("  CutItem, the fields that place an item on the timeline")
for name in TIMELINE:
    f = item_f[name]
    rows.append(f"    {name:28} {prop(f, 'data_type'):8} editable={prop(f, 'editable')!s:5} "
                f"mandatory={prop(f, 'mandatory')}")
rows.append("  CutItem links and identity")
for name in ("cut", "shot", "version", "project", "code", "cached_display_name"):
    f = item_f[name]
    rows.append(f"    {name:28} {prop(f, 'data_type'):12} valid_types={prop(f, 'valid_types')}")
rows.append("  Cut, the rate and the extent")
for name in ("fps", "duration", "timecode_start_text", "timecode_end_text", "revision_number",
             "entity", "version", "cut_items"):
    f = cut_f[name]
    rows.append(f"    {name:28} {prop(f, 'data_type'):12} valid_types={prop(f, 'valid_types')}")
rows.append("  no field of data_type timecode on either type: "
            f"{[n for n, f in {**cut_f, **item_f}.items() if prop(f, 'data_type') == 'timecode']}")

# ---------------------------------------------------------------- 2. what exists, read-only
for slug in ("cuts", "cut_items"):
    r = c.post(f"/entity/{slug}/_search", headers=ARR,
               json={"filters": [], "fields": ["code"], "page": {"size": 500}})
    _lib.note_from(r.json())
    rows.append(f"=== 2. site-wide {slug} _search, no filter -> {r.status_code}, "
                f"{len(r.json()['data'])} rows")

if not _lib.writes_allowed():
    rows.append("\n(read-only run; the build, the read-back and the reconcile need --write)")
    _lib.emit("035_build_and_reconcile_a_cut", "\n".join(rows), env)
    raise SystemExit(0)

# ---------------------------------------------------------------- the sandbox
P = _lib.sandbox_id(c, env)
FPS, START = 24.0, "01:00:00:00"
# code, edit_in, edit_out, source in, source out. `out` is the last frame: a client convention.
EDIT_A = [("sh010", 0, 47, 86400, 86447),
          ("sh020", 48, 119, 12000, 12071),
          ("sh030", 120, 167, 400, 447)]
EDIT_B = [("sh010", 0, 47, 86400, 86447),
          ("sh020", 48, 95, 12000, 12047),
          ("sh040", 96, 143, 900, 947)]
N = "zzprobe035_"


def tc(frame, fps=FPS, start=START):
    r = int(round(fps))
    h, m, s, f = (int(x) for x in start.split(":"))
    t = frame + f + r * (s + 60 * m + 3600 * h)
    return "%02d:%02d:%02d:%02d" % (t // (3600 * r), t // (60 * r) % 60, t // r % 60, t % r)


def batch(reqs):
    r = c.post("/entity/_batch", json={"requests": reqs})
    if not r.ok:
        raise SystemExit(err(r))
    return [row.get("data", row)["id"] for row in r.json()["data"]]


def items_of(cut_id, extra=()):
    """Every item of one Cut, in cut order. Page until `data` is empty (probe 006)."""
    r = c.post("/entity/cut_items/_search", headers=ARR, json={
        "filters": [["cut", "is", {"type": "Cut", "id": cut_id}]],
        "fields": ["code", *TIMELINE, *extra], "sort": "cut_order", "page": {"size": 500}})
    if not r.ok:
        raise SystemExit(err(r))
    _lib.note_from(r.json())
    return r.json()["data"]


with _lib.Created(c) as made:
    # ------------------------------------------------------------ 3. the write sequence
    rows.append(f"\n=== 3. the write sequence, sandbox project {P}")
    cut_id = c.post("/entity/cuts", headers=JSON, json={
        "project": {"type": "Project", "id": P}, "code": f"{N}reel1", "revision_number": 1,
        "fps": FPS, "timecode_start_text": START, "timecode_end_text": tc(EDIT_A[-1][2] + 1),
        "duration": EDIT_A[-1][2] + 1}).json()["data"]
    made.add("cuts", cut_id["id"])
    rows.append(f"  1. POST /entity/cuts -> 201 id={cut_id['id']} "
                f"code={cut_id['attributes']['code']!r} "
                f"cached_display_name={cut_id['attributes']['cached_display_name']!r} "
                f"fps={cut_id['attributes']['fps']!r}")
    cut_id = cut_id["id"]

    codes = sorted({e[0] for e in EDIT_A} | {e[0] for e in EDIT_B})
    shots = dict(zip(codes, batch([
        {"request_type": "create", "entity": "Shot",
         "data": {"project": {"type": "Project", "id": P}, "code": N + code}} for code in codes])))
    for i in shots.values():
        made.add("shots", i)
    rows.append(f"  2. batch create Shot x{len(shots)} -> {shots}")

    vers = dict(zip(codes, batch([
        {"request_type": "create", "entity": "Version",
         "data": {"project": {"type": "Project", "id": P}, "code": f"{N}{code}_v001",
                  "entity": {"type": "Shot", "id": shots[code]}}} for code in codes])))
    for i in vers.values():
        made.add("versions", i)
    rows.append(f"  3. batch create Version x{len(vers)}, each needing step 2's Shot id -> {vers}")

    def item_data(order, e):
        code, ein, eout, sin, sout = e
        return {"project": {"type": "Project", "id": P}, "code": N + code,
                "cut": {"type": "Cut", "id": cut_id},
                "shot": {"type": "Shot", "id": shots[code]},
                "version": {"type": "Version", "id": vers[code]},
                "cut_order": order, "edit_in": ein, "edit_out": eout,
                "cut_item_in": sin, "cut_item_out": sout, "cut_item_duration": eout - ein + 1,
                "timecode_edit_in_text": tc(ein), "timecode_edit_out_text": tc(eout + 1),
                "timecode_cut_item_in_text": tc(sin, start="00:00:00:00"),
                "timecode_cut_item_out_text": tc(sout + 1, start="00:00:00:00")}

    made_items = batch([{"request_type": "create", "entity": "CutItem", "data": item_data(n, e)}
                        for n, e in enumerate(EDIT_A, 1)])
    for i in made_items:
        made.add("cut_items", i)
    rows.append(f"  4. batch create CutItem x{len(made_items)}, each needing the Cut, Shot and "
                f"Version ids -> {made_items}")
    rows.append("     a batch cannot reference an id it creates (recipe 002), which is what splits "
                "the four stages")

    # ------------------------------------------------------------ 4. the read back
    rows.append("\n=== 4. reading the cut back")
    got = items_of(cut_id)
    rows.append("  POST /entity/cut_items/_search  [['cut','is',{'type':'Cut','id':N}]] "
                "sort=cut_order")
    for d in got:
        a = d["attributes"]
        rows.append(f"    {a['cut_order']}  {a['code']:20} edit {a['edit_in']:>4}-{a['edit_out']:<4} "
                    f"src {a['cut_item_in']}-{a['cut_item_out']}  dur {a['cut_item_duration']}  "
                    f"tc {a['timecode_edit_in_text']}-{a['timecode_edit_out_text']}")
    # gaps and overlaps: not stored, and nothing rejects one
    hole = c.post("/entity/cut_items", headers=JSON, json=dict(
        item_data(4, ("sh030", 400, 447, 400, 447)), code=f"{N}sh030_gap")).json()["data"]["id"]
    made.add("cut_items", hole)
    over = c.post("/entity/cut_items", headers=JSON, json=dict(
        item_data(5, ("sh030", 300, 500, 400, 447)), code=f"{N}sh030_overlap")).json()["data"]["id"]
    made.add("cut_items", over)
    last = c.post("/entity/cut_items", headers=JSON, json=dict(
        item_data(6, ("sh030", 600, 647, 400, 447)), code=f"{N}aaa_last")).json()["data"]["id"]
    made.add("cut_items", last)
    rel = c.get(f"/entity/cuts/{cut_id}").json()["data"]["relationships"]["cut_items"]["data"]
    rows.append(f"  Cut.cut_items reads {[x['name'] for x in rel]}")
    rows.append(f"    against cut_order "
                f"{[(d['attributes']['code'], d['attributes']['cut_order']) for d in items_of(cut_id)]}")
    seq = [(d["attributes"]["code"], d["attributes"]["edit_in"], d["attributes"]["edit_out"])
           for d in items_of(cut_id)]
    rows.append("  boundaries, computed by the client from one item's edit_out and the next "
                "item's edit_in:")
    for (c0, _, out0), (c1, in1, _) in zip(seq, seq[1:]):
        d = in1 - (out0 + 1)
        rows.append(f"    {c0:24} -> {c1:24} {out0:>4} then {in1:<4}  "
                    f"{'contiguous' if d == 0 else ('gap ' + str(d)) if d > 0 else 'overlap ' + str(-d)}")

    # ------------------------------------------------------------ 5. what the server does not do
    rows.append("\n=== 5. what the server derives and validates")
    probe_item = made_items[0]
    r = c.put(f"/entity/cut_items/{probe_item}", headers=JSON,
              json={"edit_in": 0, "edit_out": 47, "cut_item_duration": None})
    rows.append(f"  PUT edit_in/edit_out with cut_item_duration null -> {r.status_code}, "
                f"cut_item_duration reads "
                f"{c.get(f'/entity/cut_items/{probe_item}').json()['data']['attributes']['cut_item_duration']!r}")
    d = c.get(f"/entity/cuts/{cut_id}").json()["data"]["attributes"]
    rows.append(f"  Cut.duration after {len(seq)} items: {d['duration']!r}; "
                f"timecode_end_text {d['timecode_end_text']!r}; both are what was written")
    for label, body in (
            ("inverted span edit_in 100 edit_out 50", {"edit_in": 100, "edit_out": 50}),
            ("negative frames", {"edit_in": -100, "edit_out": -50}),
            ("duplicate cut_order", {"cut_order": 1}),
            ("null cut_order", {"cut_order": None}),
            ("timecode text 'banana'", {"timecode_edit_in_text": "banana"}),
            ("timecode text ''", {"timecode_edit_in_text": ""}),
            ("timecode text out before in", {"timecode_edit_in_text": "01:00:05:00",
                                             "timecode_edit_out_text": "01:00:00:00"})):
        r = c.put(f"/entity/cut_items/{over}", headers=JSON, json=body)
        back = c.get(f"/entity/cut_items/{over}").json()["data"]["attributes"]
        rows.append(f"    {label:38} -> {r.status_code} "
                    f"{ {k: back[k] for k in body} if r.ok else err(r)}")

    # ------------------------------------------------------------ 6. reconcile
    rows.append("\n=== 6. reconcile EDIT_B against the Cut written from EDIT_A")
    for i in (hole, over, last):
        c.delete(f"/entity/cut_items/{i}")
        made.rows.remove(("cut_items", i))

    def key(code, seen):
        """Nothing on CutItem is unique, so the pair key is the clip name plus its occurrence."""
        seen[code] = seen.get(code, 0) + 1
        return (code, seen[code])

    seen = {}
    existing = {key(d["attributes"]["code"], seen): d["id"] for d in items_of(cut_id)}
    seen = {}
    wanted = {key(N + e[0], seen): (n, e) for n, e in enumerate(EDIT_B, 1)}
    rows.append(f"  existing {json.dumps({str(k): v for k, v in existing.items()})}")
    rows.append(f"  wanted   {sorted(str(k) for k in wanted)}")

    def owned(ids, cut):
        """The linked-Cut check: an id alone does not say which Cut the row is on."""
        if not ids:
            return set()
        r = c.post("/entity/cut_items/_search", headers=ARR, json={
            "filters": [["id", "in", list(ids)]], "fields": ["cut.Cut.id"], "page": {"size": 500}})
        return {d["id"] for d in r.json()["data"] if d["attributes"]["cut.Cut.id"] == cut}

    mine = owned(set(existing.values()), cut_id)
    to_update = {k: existing[k] for k in wanted if k in existing and existing[k] in mine}
    to_create = [k for k in wanted if k not in to_update]
    to_delete = [existing[k] for k in existing if k not in wanted]
    rows.append(f"  update {to_update} | create {[str(k) for k in to_create]} | delete {to_delete}")

    reqs = [{"request_type": "update", "entity": "CutItem", "record_id": i,
             "data": item_data(*wanted[k])} for k, i in to_update.items()]
    reqs += [{"request_type": "create", "entity": "CutItem", "data": item_data(*wanted[k])}
             for k in to_create]
    reqs += [{"request_type": "delete", "entity": "CutItem", "record_id": i} for i in to_delete]
    out = batch(reqs)
    for i, req in zip(out, reqs):
        if req["request_type"] == "create":
            made.add("cut_items", i)
        if req["request_type"] == "delete":
            made.rows.remove(("cut_items", i))
    rows.append(f"  one batch, {len(reqs)} requests, rows in request order -> {out}")
    for d in items_of(cut_id):
        a = d["attributes"]
        rows.append(f"    {a['cut_order']}  {a['code']:20} edit {a['edit_in']:>4}-{a['edit_out']:<4} "
                    f"dur {a['cut_item_duration']}  id {d['id']}")

    # ------------------------------------------------------------ 7. the traps
    rows.append("\n=== 7. traps")
    other = c.post("/entity/cuts", headers=JSON, json={
        "project": {"type": "Project", "id": P}, "code": f"{N}reel1", "revision_number": 2,
        "fps": FPS}).json()["data"]["id"]
    made.add("cuts", other)
    decoy, spare = (c.post("/entity/cut_items", headers=JSON, json=dict(
        item_data(1, EDIT_B[0]), code=code, cut={"type": "Cut", "id": other})).json()["data"]["id"]
        for code in (f"{N}sh010", f"{N}sh050"))
    made.add("cut_items", decoy)
    made.add("cut_items", spare)
    r = c.post("/entity/cut_items/_search", headers=ARR, json={
        "filters": [["project", "is", {"type": "Project", "id": P}],
                    ["code", "is", f"{N}sh010"]],
        "fields": ["code", "cut.Cut.id"], "page": {"size": 50}})
    rows.append(f"  a search on code alone spans Cuts: "
                f"{[(d['id'], d['attributes']['cut.Cut.id']) for d in r.json()['data']]}")
    rows.append(f"  owned() keeps only this Cut's: {owned({d['id'] for d in r.json()['data']}, cut_id)}")
    r = c.put(f"/entity/cut_items/{decoy}", headers=JSON, json={"cut_order": 9, "edit_in": 999})
    rows.append(f"  a blind PUT on the wrong id -> {r.status_code}, cut still "
                f"{r.json()['data']['relationships']['cut']['data']['id']}, metadata overwritten")

    r = c.put(f"/entity/cuts/{cut_id}", headers=JSON, json={
        "cut_items": {"multi_entity_update_mode": "add", "value": [{"type": "CutItem", "id": decoy}]}})
    rows.append(f"  Cut.cut_items add of Cut {other}'s item {decoy} -> {r.status_code}, its cut is now "
                f"{c.get(f'/entity/cut_items/{decoy}').json()['data']['relationships']['cut']['data']['id']}"
                f", Cut {other} holds "
                f"{[x['id'] for x in c.get(f'/entity/cuts/{other}').json()['data']['relationships']['cut_items']['data']]}"
                f", this Cut now reads {len(items_of(cut_id))} items")

    rows.append(f"  DELETE /entity/cuts/{other}, whose remaining item is {spare} -> "
                f"{c.delete(f'/entity/cuts/{other}').status_code}")
    made.rows.remove(("cuts", other))
    r = c.post("/entity/cut_items/_search", headers=ARR, json={
        "filters": [["project", "is", {"type": "Project", "id": P}], ["cut", "is", None]],
        "fields": ["code"], "page": {"size": 50}})
    rows.append(f"  that item after the delete, [['cut','is',None]] -> {r.status_code}, "
                f"{[d['id'] for d in r.json()['data']]}")

    r = c.post("/entity/cut_items", headers=JSON, json={"code": f"{N}noproject",
                                                        "cut": {"type": "Cut", "id": cut_id}})
    rows.append(f"  create a CutItem with cut but no project -> {r.status_code} {err(r)}")
    for name in ("cut_item", "CutItems"):
        r = c.post("/entity/_batch", json={"requests": [
            {"request_type": "create", "entity": name,
             "data": {"project": {"type": "Project", "id": P}, "code": f"{N}x"}}]})
        rows.append(f"  batch entity={name!r} -> {r.status_code} {err(r)}")

    # ------------------------------------------------------------ 8. card facts: the type itself
    rows.append("\n=== 8. addressing, identity and the schema's coverage of the response")
    for slug in ("cuts", "cut", "Cut", "Cuts", "cutz", "cut_items", "cut_item", "CutItem",
                 "cutitems", "cut_itemz"):
        r = c.get(f"/entity/{slug}", params={"page[size]": 1})
        rows.append(f"  GET /entity/{slug:10} -> {r.status_code} "
                    f"{(r.json()['data'][0]['type'] if r.json().get('data') else '0 rows') if r.ok else err(r)}")
    for slug, cid in (("cuts", cut_id), ("cut_items", made_items[0])):
        got = set(c.get(f"/entity/{slug}/{cid}").json()["data"]["attributes"])
        known = set(cut_f if slug == "cuts" else item_f)
        rows.append(f"  {slug}: GET returns {len(got)} attribute keys, "
                    f"/schema/*/fields lists {len(known)}; returned but not in the schema: "
                    f"{sorted(got - known)}")
    for slug, label in (("cuts", "Cut"), ("cut_items", "CutItem")):
        r = c.post(f"/entity/{slug}", headers=JSON,
                   json={"project": {"type": "Project", "id": P}, "code": ""})
        rows.append(f"  create {label} with code '' -> {r.status_code} {err(r)}")
        if r.ok:
            made.add(slug, r.json()["data"]["id"])
    rows.append("  status_list fields: "
                f"Cut {[n for n, f in cut_f.items() if prop(f, 'data_type') == 'status_list']}, "
                f"CutItem {[n for n, f in item_f.items() if prop(f, 'data_type') == 'status_list']}")
    r = c.get("/schema/CutItem/fields/sg_status_list")
    rows.append(f"  GET /schema/CutItem/fields/sg_status_list -> {r.status_code} {err(r)}")
    for field in ("sg_status_list", "sg_cut_type"):
        d = c.get(f"/schema/Cut/fields/{field}", params={"project_id": P}).json()["data"]
        p = d.get("properties", {})
        valid, hidden = prop(p, "valid_values", []) or [], prop(p, "hidden_values", []) or []
        rows.append(f"  GET /schema/Cut/fields/{field}?project_id=N -> "
                    f"data_type={prop(d, 'data_type')} default={prop(p, 'default_value')!r}")
        rows.append(f"    valid_values ({len(valid)}) {valid}")
        rows.append(f"    hidden_values ({len(hidden)}) {hidden}  "
                    f"not in valid_values: {[v for v in hidden if v not in valid]}")

    # ------------------------------------------------------------ 9. valid_types, binding or not
    rows.append("\n=== 9. does valid_types bind (field_types/entity)")
    seq = c.post("/entity/sequences", headers=JSON, json={
        "project": {"type": "Project", "id": P}, "code": f"{N}seq01"}).json()["data"]["id"]
    made.add("sequences", seq)
    a_shot, a_version = shots[codes[0]], vers[codes[0]]
    for slug, row_id, field, sent in (
            ("cuts", cut_id, "entity", {"type": "Sequence", "id": seq}),
            ("cuts", cut_id, "entity", {"type": "Shot", "id": a_shot}),
            ("cuts", cut_id, "entity", {"type": "Version", "id": a_version}),
            ("cuts", cut_id, "version", {"type": "Shot", "id": a_shot}),
            ("cuts", cut_id, "sg_scene", {"type": "Shot", "id": a_shot}),
            ("cut_items", made_items[0], "cut", {"type": "Shot", "id": a_shot}),
            ("cut_items", made_items[0], "shot", {"type": "Version", "id": a_version}),
            ("cut_items", made_items[0], "version", {"type": "Shot", "id": a_shot})):
        r = c.put(f"/entity/{slug}/{row_id}", headers=JSON, json={field: sent})
        back = c.get(f"/entity/{slug}/{row_id}").json()["data"]["relationships"][field]["data"]
        rows.append(f"  {slug[:-1]}.{field:8} <- {sent['type']:9} -> {r.status_code} "
                    f"{'reads back ' + back['type'] if r.ok else err(r)}")
        c.put(f"/entity/{slug}/{row_id}", headers=JSON, json={field: None})
    c.put(f"/entity/cut_items/{made_items[0]}", headers=JSON,
          json={"cut": {"type": "Cut", "id": cut_id}, "shot": {"type": "Shot", "id": a_shot},
                "version": {"type": "Version", "id": vers[codes[0]]}})

    # ------------------------------------------------------------ 10. the filter matrix
    rows.append("\n=== 10. filters on cut_order and cut")
    fx = c.post("/entity/cuts", headers=JSON, json={
        "project": {"type": "Project", "id": P}, "code": f"{N}fixture"}).json()["data"]["id"]
    made.add("cuts", fx)
    fixture = {}
    for label, body in (("order1", {"cut_order": 1}), ("order2", {"cut_order": 2}),
                        ("order2b", {"cut_order": 2}), ("ordernull", {"cut_order": None})):
        d = c.post("/entity/cut_items", headers=JSON, json=dict(
            {"project": {"type": "Project", "id": P}, "code": N + label,
             "cut": {"type": "Cut", "id": fx}}, **body)).json()["data"]["id"]
        made.add("cut_items", d)
        fixture[label] = d
    loose = c.post("/entity/cut_items", headers=JSON, json={
        "project": {"type": "Project", "id": P}, "code": f"{N}nocut",
        "cut_order": 1}).json()["data"]["id"]
    made.add("cut_items", loose)
    fixture["nocut"] = loose
    by_id = {v: k for k, v in fixture.items()}
    scope = ["project", "is", {"type": "Project", "id": P}]

    def matrix(field, cases):
        for op, val in cases:
            r = c.post("/entity/cut_items/_search", headers=ARR, json={
                "filters": [scope, [field, op, val]], "fields": ["code"], "page": {"size": 100}})
            if not r.ok:
                rows.append(f"    {op:14} {json.dumps(val)[:28]:30} -> {r.status_code} {err(r)}")
                continue
            got = sorted(by_id.get(d["id"], "other:%d" % d["id"]) for d in r.json()["data"])
            rows.append(f"    {op:14} {json.dumps(val)[:28]:30} -> {got}")

    THIS = {"type": "Cut", "id": fx}
    rows.append(f"  fixture: {json.dumps({k: v for k, v in fixture.items()})}, all in one project; "
                f"'nocut' has no cut")
    r = c.post("/entity/cut_items/_search", headers=ARR, json={
        "filters": [["cut_order", "definitely_not_an_operator", 1]], "fields": ["code"]})
    rows.append(f"  cut_order bogus operator -> {r.status_code} {err(r)}")
    matrix("cut_order", [("is", 2), ("is", None), ("is_not", 2), ("is_not", None),
                         ("greater_than", 1), ("less_than", 2), ("between", [1, 2]),
                         ("in", [1, 2]), ("not_in", [1]), ("contains", "1")])
    r = c.post("/entity/cut_items/_search", headers=ARR, json={
        "filters": [["cut", "definitely_not_an_operator", None]], "fields": ["code"]})
    rows.append(f"  cut bogus operator -> {r.status_code} {err(r)}")
    matrix("cut", [("is", THIS), ("is", None), ("is_not", THIS), ("is_not", None),
                   ("in", [THIS]), ("not_in", [THIS]), ("type_is", "Cut"), ("type_is_not", "Cut"),
                   ("name_contains", "fixture"), ("name_is", f"{N}fixture")])
    matrix("cut.Cut.code", [("is", f"{N}fixture"), ("contains", "fixture")])

rows.append("\n(deletions above: CutItems before their Cut, because a deleted Cut orphans them)")
_lib.emit("035_build_and_reconcile_a_cut", "\n".join(rows), env)
