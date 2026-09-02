"""Q: how is a Sequence addressed, created and linked — and which way does the Shot hierarchy run?

A client walking a show has to pick a direction: Sequence to Shot through `shots`, or Shot to Sequence
through `sg_sequence`. Both fields exist, they are two ends of one link, and `field_types/multi_entity`
already records that a dotted read through the multi_entity end returns nothing. This measures the path
slug, the create contract (probe 012 found the schema's `mandatory` flag is not it), what `code`
guarantees, both ends of the Shot and Episode links, and the status vocabulary.

The read-only half runs ungated. Everything that mutates goes into throwaway rows in the sandbox and is
deleted. No schema field is created: a name is burned permanently (probe 019).
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _lib  # noqa: E402

env = _lib.load_env()
c = _lib.client()
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
JSN = {"Content-Type": "application/json"}
SAMPLE = _lib.sample_projects(c, env)[0]
SLUG = "sequences"
rows = []


def errs(r):
    """The whole errors[] object, `source` included. The 400 is the documentation (probe 017)."""
    try:
        return json.dumps(r.json().get("errors"))
    except ValueError:
        return r.text


def search(slug, filters, fields, size=200, extra=None):
    body = {"filters": list(filters), "fields": list(fields), "page": {"size": size}}
    body.update(extra or {})
    r = c.post(f"/entity/{slug}/_search", headers=ARR, json=body)
    return (r.json()["data"], None) if r.ok else (None, r)


def in_sample(*values):
    """Every read is confined to one sample project."""
    return [["project", "is", {"type": "Project", "id": SAMPLE}]] + [list(v) for v in values]


# ---------------------------------------------------------------- path slug
rows.append("=== the REST path slug: which spellings of /entity/<slug> resolve")
for variant in ("sequences", "sequence", "Sequences", "Sequence", "sequencies", "seqs"):
    r = c.get(f"/entity/{variant}", params={"page[size]": 1, "fields": "code"})
    n = len(r.json().get("data", [])) if r.ok else None
    rows.append(f"  GET /entity/{variant:<12} -> {r.status_code}"
                + (f"  rows={n}" if r.ok else f"  {errs(r)[:180]}"))
r = c.post("/entity/sequences/_search", headers=ARR,
           json={"filters": [], "fields": ["code"], "page": {"size": 1}})
rows.append(f"  POST /entity/sequences/_search -> {r.status_code}")

# ---------------------------------------------------------------- scope
rows.append("\n=== project-scoped or site-wide")
f = c.get("/schema/Sequence/fields/project").json()["data"]
rows.append(f"  schema Sequence.project: data_type={f['data_type']['value']} "
            f"editable={f['editable']['value']} mandatory={f['mandatory']['value']} "
            f"valid_types={f['properties']['valid_types']['value']}")
page, _ = search(SLUG, [], ["code", "project"], size=200)
projects = {(row["relationships"]["project"]["data"] or {}).get("id") for row in page}
rows.append(f"  unfiltered GET returns rows from {len(projects)} distinct project(s) in one page of "
            f"{len(page)}: the listing is site-wide, every row is project-scoped")
scoped, _ = search(SLUG, in_sample(), ["code"], size=200)
rows.append(f"  filtered to the sample project: {len(scoped)} sequence(s)")

# ---------------------------------------------------------------- identity
rows.append("\n=== identity: which field a human reads as the name")
fields = c.get("/schema/Sequence/fields").json()["data"]
for name in ("code", "name", "content", "title", "cached_display_name", "id"):
    v = fields.get(name)
    if v is None:
        rows.append(f"  {name:<20} absent from /schema/Sequence/fields")
        continue
    rows.append(f"  {name:<20} data_type={v['data_type']['value']:<10} "
                f"display_name={v['name']['value']!r:<24} editable={v['editable']['value']} "
                f"mandatory={v['mandatory']['value']} unique={v['unique']['value']}")
codes = [row["attributes"]["code"] for row in scoped]
rows.append(f"  on the sample project {len(codes)} sequences hold {len(set(codes))} distinct codes")

# ---------------------------------------------------------------- read-only fields
rows.append("\n=== what the schema marks not editable")
ro = sorted(f for f, v in fields.items() if not v["editable"]["value"])
rows.append(f"  {len(ro)} of {len(fields)}: {', '.join(ro)}")

# ---------------------------------------------------------------- status
rows.append("\n=== status field and vocabulary")
st = c.get("/schema/Sequence/fields/sg_status_list").json()["data"]["properties"]
rows.append(f"  sg_status_list default={st['default_value']['value']!r} "
            f"valid_values={st['valid_values']['value']} hidden_values={st['hidden_values']['value']}")
rows.append(f"  display_values={st['display_values']['value']}")
stp = c.get("/schema/Sequence/fields/sg_status_list",
            params={"project_id": SAMPLE}).json()["data"]["properties"]
rows.append(f"  with project_id={SAMPLE}: valid={stp['valid_values']['value']} "
            f"hidden={stp['hidden_values']['value']} (probe 009)")
used = {}
got, _ = search(SLUG, in_sample(), ["code", "sg_status_list"], size=200)
for row in got or []:
    used[row["attributes"]["sg_status_list"]] = used.get(row["attributes"]["sg_status_list"], 0) + 1
rows.append(f"  in use on the sample project: {used}")

# ---------------------------------------------------------------- links, both directions
rows.append("\n=== every entity and multi_entity field on Sequence")
for f, v in sorted(fields.items()):
    dt = v["data_type"]["value"]
    if dt not in ("entity", "multi_entity"):
        continue
    vt = v["properties"].get("valid_types", {}).get("value") or []
    shown = vt if len(vt) <= 6 else f"[{len(vt)} types]"
    rows.append(f"  {f:<26} {dt:<13} editable={v['editable']['value']!s:<5} {shown}")

rows.append("\n=== fields on other types that point AT a Sequence")
for ent in ("Shot", "Episode", "Scene", "Asset", "Cut", "Task", "Version", "PublishedFile", "Note"):
    d = c.get(f"/schema/{ent}/fields").json()["data"]
    for f, v in sorted(d.items()):
        dt = v["data_type"]["value"]
        if dt not in ("entity", "multi_entity"):
            continue
        vt = v["properties"].get("valid_types", {}).get("value") or []
        if "Sequence" not in vt or len(vt) > 20:
            continue
        rows.append(f"  {ent}.{f:<40} {dt:<13} editable={v['editable']['value']!s:<5} "
                    + (str(vt) if len(vt) <= 6 else f"[{len(vt)} types]"))

rows.append("\n=== which links carry data on the probed site")
for ent, slug, field in (("Sequence", SLUG, "shots"), ("Sequence", SLUG, "episode"),
                         ("Sequence", SLUG, "assets"), ("Sequence", SLUG, "sg_scenes"),
                         ("Sequence", SLUG, "cuts"), ("Sequence", SLUG, "sg_versions"),
                         ("Sequence", SLUG, "tasks")):
    got, r = search(slug, in_sample([field, "is_not", None]), ["code"], size=200)
    rows.append(f"  {ent}.{field:<14} is_not None -> "
                + (f"{len(got):>3} of {len(scoped)}" if got is not None else errs(r)[:160]))
got, _ = search("shots", in_sample(["sg_sequence", "is_not", None]), ["code"], size=500)
allshots, _ = search("shots", in_sample(), ["code"], size=500)
rows.append(f"  Shot.sg_sequence is_not None -> {len(got)} of {len(allshots)} shots")
for ent, slug in (("Episode", "episodes"), ("Scene", "scenes")):
    got, r = search(slug, [], ["code"], size=1)
    rows.append(f"  {ent} rows site-wide: " + (str(len(got)) if got is not None else errs(r)[:120]))

rows.append("\n=== dotted reads, both directions (probe 016, field_types/multi_entity)")
one = next(row for row in scoped if row["attributes"]["code"])
seq_id, seq_code = one["id"], one["attributes"]["code"]
r = c.get(f"/entity/{SLUG}/{seq_id}", params={"fields": "code,shots.Shot.code"})
rows.append(f"  GET sequence {seq_id} ?fields=code,shots.Shot.code -> {r.status_code} "
            f"attributes={json.dumps(r.json()['data']['attributes'])[:160]}")
kid, _ = search("shots", [["sg_sequence", "is", {"type": "Sequence", "id": seq_id}]],
                ["code", "sg_sequence.Sequence.code"], size=3)
rows.append(f"  shots filtered by sg_sequence is that Sequence -> {len(kid)} row(s); first "
            f"attributes={json.dumps(kid[0]['attributes']) if kid else None}")
kid_code = kid[0]["attributes"]["code"] if kid else "ZZZNOPE"
kid2, r = search(SLUG, in_sample(["shots.Shot.code", "is", kid_code]), ["code"], size=5)
rows.append("  sequences filtered by shots.Shot.code is that shot -> "
            + (f"{len(kid2)} row(s)" if kid2 is not None else errs(r)[:160]))
_lib.note_names(seq_code)
for row in kid or []:
    _lib.note_from(row)

# ---------------------------------------------------------------- writes
if not _lib.writes_allowed():
    rows.append("\n=== create, uniqueness and link direction skipped; re-run with --write")
    _lib.emit("entity_types/Sequence", "\n".join(rows), env)
    raise SystemExit(0)

SANDBOX = _lib.sandbox_id(c, env)
PJ = {"type": "Project", "id": SANDBOX}
CODE = "zzprobe_seq"

with _lib.Created(c) as made:
    rows.append("\n=== create contract: what the server actually requires (probe 012)")
    attempts = [
        ("{}", {}),
        ('{"code": "zzprobe_seq_a"}', {"code": f"{CODE}_a"}),
        ('{"project": {...}}', {"project": PJ}),
        ('{"code": ..., "project": {...}}', {"code": f"{CODE}_b", "project": PJ}),
        ('{"code": null, "project": {...}}', {"code": None, "project": PJ}),
        ('{"code": "", "project": {...}}', {"code": "", "project": PJ}),
        ('{"code": ..., "project": <bare int>}', {"code": f"{CODE}_c", "project": SANDBOX}),
    ]
    for label, body in attempts:
        r = c.post(f"/entity/{SLUG}", headers=JSN, json=body)
        if r.ok:
            d = r.json()["data"]
            made.add(SLUG, d["id"])
            rows.append(f"  {label:<38} -> {r.status_code} id={d['id']} "
                        f"code={d['attributes'].get('code')!r}")
        else:
            rows.append(f"  {label:<38} -> {r.status_code} {errs(r)}")

    rows.append("\n=== what the create echoes back")
    r = c.post(f"/entity/{SLUG}", headers=JSN, json={"code": f"{CODE}_echo", "project": PJ})
    d = r.json()["data"]
    base = made.add(SLUG, d["id"])
    rows.append(f"  {r.status_code}, {len(d['attributes'])} attribute(s): "
                f"{json.dumps(d['attributes'])[:300]}")
    rows.append(f"  relationships: {sorted(d.get('relationships', {}))}")
    full = c.get(f"/entity/{SLUG}/{base}").json()["data"]
    rows.append(f"  read back: {len(full['attributes'])} attributes, "
                f"{len(full.get('relationships', {}))} relationships")
    rows.append("  server-set on create: "
                + json.dumps({k: full["attributes"][k] for k in
                              ("code", "sg_status_list", "cached_display_name", "created_at")
                              if k in full["attributes"]})[:300])

    rows.append("\n=== is `code` unique?")
    r = c.post(f"/entity/{SLUG}", headers=JSN, json={"code": f"{CODE}_echo", "project": PJ})
    if r.ok:
        dup = made.add(SLUG, r.json()["data"]["id"])
        rows.append(f"  same code, same project -> {r.status_code} id={dup}, a second row. "
                    f"schema unique={fields['code']['unique']['value']}")
        got, _ = search(SLUG, [["project", "is", PJ], ["code", "is", f"{CODE}_echo"]],
                        ["code"], size=10)
        rows.append(f"  filter code is that value -> {len(got)} rows; only `id` identifies a Sequence")
    else:
        rows.append(f"  same code, same project -> {r.status_code} {errs(r)}")

    rows.append("\n=== cached_display_name: editable in the schema, but is it yours?")
    r = c.put(f"/entity/{SLUG}/{base}", headers=JSN,
              json={"cached_display_name": "zzprobe_seq_not_the_code"})
    a = c.get(f"/entity/{SLUG}/{base}",
              params={"fields": "code,cached_display_name"}).json()["data"]["attributes"]
    rows.append(f"  PUT cached_display_name -> {r.status_code}; reads back {a!r}")
    c.put(f"/entity/{SLUG}/{base}", headers=JSN, json={"code": f"{CODE}_renamed"})
    a = c.get(f"/entity/{SLUG}/{base}",
              params={"fields": "code,cached_display_name"}).json()["data"]["attributes"]
    rows.append(f"  then PUT code -> reads back {a!r}")

    rows.append("\n=== read-only and create-only fields, sent anyway")
    for f, val in (("id", 1), ("created_at", "2020-01-01T00:00:00Z"),
                   ("created_by", {"type": "HumanUser", "id": 1}),
                   ("updated_at", "2020-01-01T00:00:00Z"),
                   ("open_notes_count", 3), ("image_blur_hash", "zz"), ("step_0", "x")):
        r = c.put(f"/entity/{SLUG}/{base}", headers=JSN, json={f: val})
        rows.append(f"  PUT {f:<18} -> {r.status_code} " + ("" if r.ok else errs(r)[:220]))

    rows.append("\n=== hierarchy: are Sequence.shots and Shot.sg_sequence one link or two?")
    sh = c.post("/entity/shots", headers=JSN,
                json={"code": "zzprobe_seq_shot", "project": PJ}).json()["data"]
    shot = made.add("shots", sh["id"])
    r = c.put(f"/entity/shots/{shot}", headers=JSN,
              json={"sg_sequence": {"type": "Sequence", "id": base}})
    back = c.get(f"/entity/{SLUG}/{base}", params={"fields": "shots"}).json()["data"]
    rows.append(f"  PUT Shot.sg_sequence = that Sequence -> {r.status_code}")
    rows.append(f"  Sequence.shots now: "
                f"{json.dumps(back['relationships']['shots']['data'])}")
    r = c.put(f"/entity/shots/{shot}", headers=JSN, json={"sg_sequence": None})
    back = c.get(f"/entity/{SLUG}/{base}", params={"fields": "shots"}).json()["data"]
    rows.append(f"  clear Shot.sg_sequence -> {r.status_code}; Sequence.shots now "
                f"{json.dumps(back['relationships']['shots']['data'])}")
    r = c.put(f"/entity/{SLUG}/{base}", headers=JSN,
              json={"shots": {"multi_entity_update_mode": "add",
                              "value": [{"type": "Shot", "id": shot}]}})
    a = c.get(f"/entity/shots/{shot}", params={"fields": "sg_sequence"}).json()["data"]
    rows.append(f"  add to Sequence.shots -> {r.status_code}; Shot.sg_sequence now "
                f"{json.dumps(a['relationships']['sg_sequence']['data'])}")

    rows.append("\n=== a second Sequence claims the same Shot")
    r = c.post(f"/entity/{SLUG}", headers=JSN, json={"code": f"{CODE}_other", "project": PJ})
    other = made.add(SLUG, r.json()["data"]["id"])
    r = c.put(f"/entity/{SLUG}/{other}", headers=JSN,
              json={"shots": {"multi_entity_update_mode": "add",
                              "value": [{"type": "Shot", "id": shot}]}})
    a = c.get(f"/entity/shots/{shot}", params={"fields": "sg_sequence"}).json()["data"]
    b1 = c.get(f"/entity/{SLUG}/{base}", params={"fields": "shots"}).json()["data"]
    rows.append(f"  add the same Shot to a second Sequence -> {r.status_code}; "
                f"Shot.sg_sequence = {json.dumps(a['relationships']['sg_sequence']['data'])}, "
                f"first Sequence.shots = {json.dumps(b1['relationships']['shots']['data'])}")

    rows.append("\n=== hierarchy above: Sequence.episode and Episode.sequences")
    ep = c.post("/entity/episodes", headers=JSN,
                json={"code": "zzprobe_seq_ep", "project": PJ})
    if ep.ok:
        epid = made.add("episodes", ep.json()["data"]["id"])
        r = c.put(f"/entity/{SLUG}/{base}", headers=JSN,
                  json={"episode": {"type": "Episode", "id": epid}})
        a = c.get(f"/entity/episodes/{epid}", params={"fields": "sequences"}).json()["data"]
        rows.append(f"  PUT Sequence.episode -> {r.status_code}; Episode.sequences now "
                    f"{json.dumps(a['relationships']['sequences']['data'])}")
        r = c.put(f"/entity/{SLUG}/{base}", headers=JSN, json={"episode": None})
        r = c.put(f"/entity/episodes/{epid}", headers=JSN,
                  json={"sequences": {"multi_entity_update_mode": "add",
                                      "value": [{"type": "Sequence", "id": base}]}})
        a = c.get(f"/entity/{SLUG}/{base}", params={"fields": "episode"}).json()["data"]
        rows.append(f"  PUT Episode.sequences add -> {r.status_code}; Sequence.episode now "
                    f"{json.dumps(a['relationships']['episode']['data'])}")
        r = c.put(f"/entity/{SLUG}/{base}", headers=JSN,
                  json={"episode": {"type": "Sequence", "id": other}})
        rows.append(f"  PUT Sequence.episode = a Sequence -> {r.status_code} "
                    + ("" if not r.ok else "stored; valid_types not enforced") + errs(r)[:200])
    else:
        rows.append(f"  POST /entity/episodes -> {ep.status_code} {errs(ep)[:200]}")

    rows.append("\n=== status writes")
    for val in ("fin", "wtg", "ZZZ", None):
        r = c.put(f"/entity/{SLUG}/{base}", headers=JSN, json={"sg_status_list": val})
        a = c.get(f"/entity/{SLUG}/{base}",
                  params={"fields": "sg_status_list"}).json()["data"]["attributes"]
        rows.append(f"  sg_status_list = {val!r:<8} -> {r.status_code} reads "
                    f"{a.get('sg_status_list')!r}" + ("" if r.ok else f" {errs(r)[:200]}"))

    rows.append("\n=== delete: retire or purge?")
    r = c.post(f"/entity/{SLUG}", headers=JSN, json={"code": f"{CODE}_del", "project": PJ})
    doomed = r.json()["data"]["id"]
    r = c.delete(f"/entity/{SLUG}/{doomed}")
    g = c.get(f"/entity/{SLUG}/{doomed}")
    gone, _ = search(SLUG, [["project", "is", PJ], ["code", "is", f"{CODE}_del"]], ["code"], size=5)
    rows.append(f"  DELETE -> {r.status_code}; GET the same id -> {g.status_code} {errs(g)[:200]}")
    rows.append(f"  _search for its code -> {len(gone)} row(s)")
    r = c.post(f"/entity/{SLUG}/{doomed}", headers=JSN, json={})
    rows.append(f"  POST /entity/{SLUG}/{doomed} with no body -> {r.status_code} {errs(r)[:220]}")
    r = c.post(f"/entity/{SLUG}/{doomed}", headers=JSN, params={"revive": "true"}, json={})
    rows.append(f"  POST /entity/{SLUG}/{doomed}?revive=true -> {r.status_code} "
                + ("revived, the id comes back" if r.ok else errs(r)[:220]))
    if r.ok:
        made.add(SLUG, doomed)

_lib.emit("entity_types/Sequence", "\n".join(rows), env)
