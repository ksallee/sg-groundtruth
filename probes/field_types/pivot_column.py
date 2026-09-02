"""Q: what is a `pivot_column` field, and can a REST client do anything with one?

The type is the widest non-editable group on the site and nothing in the corpus explains it. The names
look like `step_<n>`, so the first question is whether that `<n>` is a Step id; the second is whether the
column ever returns a value over REST, given that no `pivot_column` field is editable anywhere.

The schema sweep walks every entity type. That is the call probe 002 says never to loop, and it costs
~330ms a type here — acceptable once, for a census, not in a client.

Read-only half runs ungated. The one write attempt needs --write and goes into the sandbox project.
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _lib  # noqa: E402

env = _lib.load_env()
c = _lib.client()
PROJECT = _lib.sample_projects(c, env)[0]
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
JSN = {"Content-Type": "application/json"}
PROJ = ["project", "is", {"type": "Project", "id": PROJECT}]
rows = []


def errs(r):
    """The whole errors[] object, source included. A sliced 400 loses the part worth having."""
    return json.dumps(r.json().get("errors"), indent=1)


def search(filt, entity="shots", fields=None, sort=None, size=3):
    body = {"filters": filt, "fields": fields or ["code"], "page": {"size": size}}
    if sort:
        body["sort"] = sort
    r = c.post(f"/entity/{entity}/_search", headers=ARR, json=body)
    return (len(r.json()["data"]), None) if r.ok else (None, f"{r.status_code} {errs(r)}")


# ------------------------------------------------------------------ census
t0 = time.time()
types = sorted(c.get("/schema").json()["data"])
pivots = {}
for t in types:
    r = c.get(f"/schema/{t}/fields")
    if r.ok:
        d = r.json()["data"]
        p = {f: v for f, v in d.items() if v["data_type"]["value"] == "pivot_column"}
        if p:
            pivots[t] = (p, len(d))
rows.append(f"=== census: pivot_column across all {len(types)} entity types "
            f"({time.time() - t0:.0f}s)")
total = sum(len(p) for p, _ in pivots.values())
rows.append(f"  {total} fields on {len(pivots)} types; every one editable=False")
for t, (p, n) in sorted(pivots.items(), key=lambda kv: -len(kv[1][0])):
    rows.append(f"  {t:<16} {len(p):>2} of {n:<4} {', '.join(sorted(p)[:6])}"
                f"{' ...' if len(p) > 6 else ''}")
rows.append(f"  every name matches step_<n>: "
            f"{all(f.startswith('step_') and f[5:].isdigit() for p, _ in pivots.values() for f in p)}")
rows.append(f"  types with only step_0: "
            f"{sum(1 for p, _ in pivots.values() if list(p) == ['step_0'])}")
rows.append(f"  editable anywhere: "
            f"{any(v['editable']['value'] for p, _ in pivots.values() for v in p.values())}")

# ------------------------------------------------- does <n> resolve to a Step?
rows.append("\n=== naming: is the <n> in step_<n> a Step id?")
hits = miss = 0
sample = []
for t, (p, _) in sorted(pivots.items()):
    for f in sorted(p):
        n = int(f[5:])
        if n == 0:
            continue
        r = c.get(f"/entity/steps/{n}", params={"fields": "code,entity_type"})
        if not r.ok:
            miss += 1
            continue
        a = r.json()["data"]["attributes"]
        _lib.note_names(a["code"], p[f]["name"]["value"])
        ok = a["code"] == p[f]["name"]["value"] and a["entity_type"] == t
        hits += ok
        miss += not ok
        if len(sample) < 4:
            sample.append(f"  {t}.{f:<10} -> GET /entity/steps/{n} code={a['code']!r} "
                          f"entity_type={a['entity_type']!r}; field name={p[f]['name']['value']!r}")
rows += sample
rows.append(f"  Step.code == field name.value AND Step.entity_type == field entity_type: "
            f"{hits} of {hits + miss} non-zero fields")
r = c.get("/entity/steps/0")
rows.append(f"  step_0 has no Step: GET /entity/steps/0 -> {r.status_code} {errs(r)}"
            .replace("\n", " ").replace("  ", " "))
rows.append(f"  and step_0's display name is the same on every type: "
            f"{sorted({p['step_0']['name']['value'] for p, _ in pivots.values() if 'step_0' in p})}")

st = c.post("/entity/steps/_search", headers=ARR,
            json={"filters": [], "fields": ["entity_type"], "page": {"size": 500}}).json()["data"]
by_type = {}
for s in st:
    by_type[s["attributes"]["entity_type"]] = by_type.get(s["attributes"]["entity_type"], 0) + 1
rows.append(f"  Steps on the site by entity_type: {sorted(by_type.items())}")
rows.append(f"  total Steps: {len(st)}")
# The census table claims one column per Step plus step_0. Measure the Step count for every type
# that has pivot fields, including the ones that turn out to have none.
rows.append("  pivot fields vs Steps declared for that type, measured per type:")
for t, (p, _) in sorted(pivots.items(), key=lambda kv: -len(kv[1][0])):
    rows.append(f"    {t:<16} {len(p):>2} fields, {by_type.get(t, 0):>2} Steps "
                f"(entity_type={t!r} in the Step listing: {t in by_type})")

# ------------------------------------------------------------- schema shape
rows.append("\n=== schema shape: GET /schema/Shot/fields/step_8, in full")
d = c.get("/schema/Shot/fields/step_8").json()["data"]
for k, v in d.items():
    rows.append(f"  {k:<22} {json.dumps(v)}")
rows.append("  properties names no source field, no Step link, no result data type")

# --------------------------------------------------------------------- read
rows.append("\n=== read: the key is present and null; a bogus field name is dropped (probe 004)")
r = c.get("/entity/shots", params={"filter[project.Project.id]": PROJECT, "page[size]": 2,
                                   "fields": "code,step_8,step_0,sg_not_a_real_field"})
rows.append(f"  GET /entity/shots?fields=code,step_8,step_0,sg_not_a_real_field -> {r.status_code}")
for row in r.json()["data"]:
    _lib.note_from(row)
    rows.append(f"  attributes={json.dumps(row['attributes'])} relationships={row['relationships']}")

rows.append("\n=== read: positive control — rows that provably have a Task for that Step")
for sid in (8, 7, 35):
    t = c.post("/entity/tasks/_search", headers=ARR,
               json={"filters": [["step", "is", {"type": "Step", "id": sid}],
                                 ["entity", "type_is", "Shot"]],
                     "fields": ["content", "entity", "sg_status_list"], "page": {"size": 1}}).json()["data"]
    if not t:
        continue
    _lib.note_from(t[0])
    ent = t[0]["relationships"]["entity"]["data"]
    a = c.get(f"/entity/shots/{ent['id']}",
              params={"fields": f"code,step_{sid}"}).json()["data"]["attributes"]
    rows.append(f"  Task {t[0]['attributes']['content']!r} step={sid} "
                f"status={t[0]['attributes']['sg_status_list']!r} on Shot {ent['id']} "
                f"-> shot.step_{sid} = {a[f'step_{sid}']!r}")

rows.append("\n=== read: how many non-null values exist at all")
seen = 0
scanned = 0
for entity, fields in (("shots", sorted(pivots["Shot"][0])), ("assets", sorted(pivots["Asset"][0])),
                       ("versions", ["step_0"])):
    r = c.get(f"/entity/{entity}", params={"page[size]": 200, "fields": ",".join(fields),
                                           "sort": "-created_at"})
    data = r.json()["data"]
    scanned += len(data) * len(fields)
    seen += sum(1 for row in data for f in fields if row["attributes"].get(f) is not None)
    rows.append(f"  {entity:<9} {len(data):>3} newest rows x {len(fields):>2} fields, site-wide "
                f"(no project filter)")
rows.append(f"  non-null cells: {seen} of {scanned}")

# ------------------------------------------------------- operators, filter
rows.append("\n=== filter: the API enumerates its operators, then refuses both (probe 017)")
_, err = search([PROJ, ["step_8", "definitely_not_an_operator", None]])
rows.append(err)
for label, filt in [("is None", ["step_8", "is", None]),
                    ("is_not None", ["step_8", "is_not", None]),
                    ("is 'fin'", ["step_8", "is", "fin"])]:
    n, err = search([PROJ, filt])
    rows.append(f"  step_8 {label:<12} -> {n if err is None else err}")
r = c.get("/entity/shots", params={"filter[project.Project.id]": PROJECT, "filter[step_8]": "fin",
                                   "fields": "code"})
rows.append(f"  GET flat filter[step_8]=fin -> {r.status_code} {errs(r)}")

rows.append("\n=== sort: a different error, and it names no field")
for label, sort in [("_search sort step_8", "step_8"), ("_search sort -step_8", "-step_8"),
                    ("_search sort step_0", "step_0")]:
    n, err = search([PROJ], sort=sort)
    rows.append(f"  {label:<22} -> {n if err is None else err}")
r = c.get("/entity/shots", params={"filter[project.Project.id]": PROJECT, "sort": "step_8",
                                   "fields": "code"})
rows.append(f"  GET  sort=step_8       -> {r.status_code} {errs(r)}")

rows.append("\n=== the same three verbs on the other field, so the matrix is not one field's behaviour")
_, err = search([PROJ, ["step_0", "definitely_not_an_operator", None]], entity="versions")
rows.append(err)
for label, filt in [("is None", ["step_0", "is", None]),
                    ("is_not None", ["step_0", "is_not", None]),
                    ("is 'fin'", ["step_0", "is", "fin"])]:
    n, err = search([PROJ, filt], entity="versions")
    rows.append(f"  Version.step_0 {label:<12} -> {n if err is None else err}")
r = c.get("/entity/versions", params={"filter[project.Project.id]": PROJECT,
                                      "filter[step_0]": "fin", "fields": "code"})
rows.append(f"  GET flat filter[step_0]=fin on versions -> {r.status_code} {errs(r)}")
for label, sort in [("_search sort step_0", "step_0"), ("_search sort -step_0", "-step_0")]:
    n, err = search([PROJ], entity="versions", sort=sort)
    rows.append(f"  Version {label:<22} -> {n if err is None else err}")
r = c.get("/entity/versions", params={"filter[project.Project.id]": PROJECT, "sort": "step_0",
                                      "fields": "code"})
rows.append(f"  GET  sort=step_0 on versions -> {r.status_code} {errs(r)}")

rows.append("\n=== _summarize: neither grouping nor summary_field survives (probe 020)")
for entity, f in (("shots", "step_8"), ("versions", "step_0")):
    for label, body in [
        (f"grouping {f}", {"filters": [PROJ], "summary_fields": [{"field": "id", "type": "count"}],
                           "grouping": [{"field": f, "type": "exact", "direction": "asc"}]}),
        (f"summary_field {f}", {"filters": [PROJ],
                                "summary_fields": [{"field": f, "type": "count"}]})]:
        r = c.post(f"/entity/{entity}/_summarize", headers=ARR, json=body)
        rows.append(f"  {entity:<9} {label:<22} -> {r.status_code} "
                    f"{r.json()['errors'][0]['title'] if not r.ok else 'ok'}")

# -------------------------------------------------------------------- write
if not _lib.writes_allowed():
    rows.append("\n(read-only run; pass --write for the create / update attempt)")
else:
    SANDBOX = _lib.sandbox_id(c, env)
    rows.append("\n=== write: throwaway rows in the sandbox, deleted at the end")
    # Both fields, both verbs: step_8 is a real Step's column, step_0 the all-steps one, and the
    # read half measured filter and sort on Shot.step_8 only.
    with _lib.Created(c) as made:
        for slug, key, field in (("versions", "code", "step_0"), ("shots", "code", "step_8")):
            r = c.post(f"/entity/{slug}", json={"project": {"type": "Project", "id": SANDBOX},
                                                key: f"zzprobe_pivot_{int(time.time())}"})
            rows.append(f"\n  POST /entity/{slug} -> {r.status_code}; step_* in the 201 attributes: "
                        f"{[k for k in r.json()['data']['attributes'] if k.startswith('step_')]}")
            rid = made.add(slug, r.json()["data"]["id"])
            for label, body in [(f"{field}='fin'", {field: "fin"}), (f"{field}=null", {field: None})]:
                u = c.request("PUT", f"/entity/{slug}/{rid}", json=body, headers=JSN)
                rows.append(f"  PUT {label:<14} -> {u.status_code} {errs(u)}".replace("\n", " "))
            r2 = c.post(f"/entity/{slug}", json={"project": {"type": "Project", "id": SANDBOX},
                                                 key: f"zzprobe_pivot_c_{int(time.time())}",
                                                 field: "fin"})
            rows.append(f"  POST create with {field} -> {r2.status_code} {errs(r2)}".replace("\n", " "))
            if r2.ok:
                made.add(slug, r2.json()["data"]["id"])
            back = c.get(f"/entity/{slug}/{rid}", params={"fields": f"{key},{field}"}).json()["data"]
            _lib.note_from(back)
            rows.append(f"  read back after three refused writes: {json.dumps(back['attributes'])}")

actual = "\n".join(rows)
_lib.emit("field_types/pivot_column", actual, env)
