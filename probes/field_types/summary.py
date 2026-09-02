"""Field type `summary` — the stored rollup. Read, write, clear, filter, sort, freshness.

Two questions the other field types do not raise: whether `/schema` exposes the rollup that defines the
number, and whether the number is computed at all. Both turn out to matter more than the read shape.

Read-only half runs ungated. Writes go into the sandbox project only, behind --write.
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


def errobj(r):
    """The whole errors[] object, parsed. Never sliced: `source` names the rejected value."""
    try:
        return r.json().get("errors", [r.json()])
    except ValueError:
        return [r.text]


def errs(r):
    return json.dumps(errobj(r), indent=1)


# ---------------------------------------------------------------- schema, site-wide
# probe 002 forbids looping /schema/<Type>/fields in client code. A probe measuring the matrix once is
# the exception; the cost is printed so nobody repeats it at runtime.
rows.append("=== schema: every summary field on the site")
t0 = time.time()
types = sorted(c.get("/schema").json()["data"])
hits = {}
for t in types:
    r = c.get(f"/schema/{t}/fields")
    if not r.ok:
        continue
    for f, d in r.json()["data"].items():
        if (d.get("data_type") or {}).get("value") == "summary":
            p = d.get("properties", {})
            hits.setdefault(f, []).append((t, (d.get("editable") or {}).get("value"),
                                           (p.get("summary_default") or {}).get("value"),
                                           repr(p["default_value"]) if "default_value" in p
                                           else "<absent>"))
rows.append(f"  {len(types)} types, {time.time() - t0:.0f}s")
for f, v in sorted(hits.items()):
    rows.append(f"  {f:<20} on {len(v):>2} types  editable/summary_default={sorted({(e, s) for _, e, s, _ in v})}")
    rows.append(f"  {'':<20} e.g. {[t for t, _, _, _ in v][:5]}")
rows.append(f"  default_value over all {sum(len(v) for v in hits.values())} summary fields: "
            f"{sorted({dv for v in hits.values() for _, _, _, dv in v})}")

rows.append("\n=== GET /schema/Version/fields/open_notes_count — properties in full")
d = c.get("/schema/Version/fields/open_notes_count").json()["data"]
rows.append(f"  data_type={(d['data_type'])['value']} editable={(d['editable'])['value']} "
            f"mandatory={(d['mandatory'])['value']}")
rows.append("  properties keys: " + str(sorted(d["properties"])))
rows.append(json.dumps(d["properties"], indent=1))

rows.append("\n=== the other shape: Project.sg_latest_version (editable=true, single_record)")
d2 = c.get("/schema/Project/fields/sg_latest_version").json()["data"]
rows.append(f"  editable={(d2['editable'])['value']}")
rows.append(json.dumps({k: v["value"] for k, v in d2["properties"].items()}, indent=1))

# ---------------------------------------------------------------- read
rows.append("\n=== read: attributes or relationships?")
r = c.get("/entity/shots", params={"filter[project.Project.id]": PROJECT,
                                   "fields": "code,open_notes_count", "page[size]": 2})
row = r.json()["data"][0]
_lib.note_from(row)
rows.append(json.dumps(row, indent=1))

full = c.get(f"/entity/shots/{row['id']}").json()["data"]
_lib.note_from(full)
rows.append(f"  single-row GET, no ?fields: {len(full['attributes'])} attributes, "
            f"open_notes_count={full['attributes'].get('open_notes_count')!r}, "
            f"in relationships={'open_notes_count' in full['relationships']}")

rows.append("\n  the four custom (sg_*) summary fields, on rows whose target rows exist:")
r = c.post("/entity/versions/_search", headers=ARR,
           json={"filters": [PROJ, ["entity", "type_is", "Asset"]],
                 "fields": ["code", "entity"], "page": {"size": 1}})
linked_asset = r.json()["data"][0]["relationships"]["entity"]["data"]["id"] if r.json()["data"] else None
_lib.note_from(r.json())
if linked_asset:
    a = c.get(f"/entity/assets/{linked_asset}",
              params={"fields": "code,sg_latest_version,sg_query,open_notes_count"}).json()["data"]
    _lib.note_from(a)
    rows.append(f"  Asset {linked_asset} has a Version linking to it; its attributes: "
                f"{json.dumps({k: v for k, v in a['attributes'].items() if k != 'code'})}")
r = c.get("/entity/projects", params={"fields": "name,sg_latest_version", "page[size]": 25}).json()["data"]
_lib.note_from(r)
rows.append(f"  Project.sg_latest_version over {len(r)} projects: "
            f"{sorted({repr(p['attributes']['sg_latest_version']) for p in r})}")

rows.append("\n=== dotted path through a link reads the count of the linked row")
r = c.post("/entity/versions/_search", headers=ARR,
           json={"filters": [PROJ, ["entity", "type_is", "Shot"]],
                 "fields": ["code", "entity.Shot.open_notes_count"], "page": {"size": 2}})
_lib.note_from(r.json())
rows.append("  " + json.dumps([x["attributes"] for x in r.json()["data"]]))

# ---------------------------------------------------------------- fill rate
rows.append("\n=== fill rate: is a summary field ever null?")
r = c.get("/entity/shots", params={"filter[project.Project.id]": PROJECT,
                                   "fields": "code,open_notes_count", "page[size]": 100})
vals = [x["attributes"]["open_notes_count"] for x in r.json()["data"]]
rows.append(f"  {len(vals)} Shots: nulls={vals.count(None)}  zeros={vals.count(0)}  "
            f"min={min(vals)} max={max(vals)}  distinct={len(set(vals))}")
r = c.get("/entity/versions", params={"filter[project.Project.id]": PROJECT,
                                      "fields": "code,open_notes_count", "page[size]": 100})
vv = [x["attributes"]["open_notes_count"] for x in r.json()["data"]]
rows.append(f"  {len(vv)} Versions: nulls={vv.count(None)}  distinct values={sorted(set(vv))}  (probe 007)")

# ---------------------------------------------------------------- reproduce the rollup
# One field on one row proves nothing about the type. Every summary field on the site whose target
# type is reachable is re-derived here, on the three rows most likely to hold a value.
rows.append("\n=== the exposed query, translated to _search filters and run against the row itself")
HSH = {"Content-Type": "application/vnd+shotgun.api3_hash+json"}
SLUG = {"Note": "notes", "Version": "versions", "CustomEntity02": "custom_entity_02s"}


def as_filters(node, rtype, rid):
    """properties.query.filters -> _search filters. A leaf becomes a triple, and the
    parent_entity_token becomes the row being read."""
    if "conditions" in node:
        return {"logical_operator": node["logical_operator"],
                "conditions": [as_filters(x, rtype, rid) for x in node["conditions"]]}
    vals = [{"type": rtype, "id": rid}
            if isinstance(v, dict) and v.get("valid") == "parent_entity_token" else v
            for v in node["values"]]
    return [node["path"], node["relation"], vals[0] if len(vals) == 1 else vals]


for T, slug, field in [("Shot", "shots", "open_notes_count"),
                       ("Version", "versions", "open_notes_count"),
                       ("CustomEntity01", "custom_entity_01s", "sg_test_results"),
                       ("Asset", "assets", "sg_query"),
                       ("Asset", "assets", "sg_latest_version"),
                       ("Project", "projects", "sg_latest_version")]:
    p = c.get(f"/schema/{T}/fields/{field}").json()["data"]["properties"]
    q = p["query"]["value"]
    rr = c.get(f"/entity/{slug}", params={"fields": field, "page[size]": 100,
                                          "sort": "-id"}).json()["data"]
    _lib.note_from(rr)
    vals = [x["attributes"][field] for x in rr]
    rows.append(f"\n  {T}.{field}  summary_default={p['summary_default']['value']} "
                f"summary_field={p['summary_field']['value']} target={q['entity_type']}")
    rows.append(f"    {len(vals)} newest rows: nulls={vals.count(None)} "
                f"distinct={sorted({repr(v) for v in vals})[:5]}")
    # 0 == 0 settles nothing, so widen the pool until a row with something to count turns up.
    if not any(isinstance(v, int) and v > 0 for v in vals) and T != "Project":
        more = c.get(f"/entity/{slug}", params={"fields": field, "page[size]": 200,
                                                "sort": "id"}).json()["data"]
        _lib.note_from(more)
        rr += more
    for row in sorted(rr, key=lambda x: x["attributes"][field]
                      if isinstance(x["attributes"][field], int) else -1, reverse=True)[:3]:
        f = as_filters(q["filters"], T, row["id"])
        s = c.post(f"/entity/{SLUG[q['entity_type']]}/_summarize", headers=HSH,
                   json={"filters": f, "summary_fields": [{"field": "id", "type": "record_count"}]})
        n = s.json()["data"]["summaries"]["id"] if s.ok else f"{s.status_code} {errs(s)}"
        rows.append(f"    row {row['id']}: field reads {row['attributes'][field]!r}, "
                    f"the field's own query record_counts {n}")
    rows.append(f"    filters sent, for the last row: {json.dumps(f)}")

# ---------------------------------------------------------------- filter
rows.append("\n=== filter: the bogus operator does not enumerate a vocabulary here")
r = c.post("/entity/shots/_search", headers=ARR,
           json={"filters": [PROJ, ["open_notes_count", "definitely_not_an_operator", None]],
                 "fields": ["code"], "page": {"size": 1}})
rows.append(errs(r))

rows.append("\n  every real operator, same 400:")
for op, v in [("is", 0), ("is_not", None), ("greater_than", 3), ("less_than", 5), ("in", [0, 1])]:
    r = c.post("/entity/shots/_search", headers=ARR,
               json={"filters": [PROJ, ["open_notes_count", op, v]], "fields": ["code"], "page": {"size": 1}})
    t = errobj(r)[0].get("title") if not r.ok else f"200, {len(r.json()['data'])} rows"
    rows.append(f"    {op:<13}{json.dumps(v):<10} -> {r.status_code} {t}")

r = c.get("/entity/shots", params={"filter[project.Project.id]": PROJECT,
                                   "filter[open_notes_count]": "3", "fields": "code"})
rows.append(f"  GET flat filter[open_notes_count]=3 -> {r.status_code} {errobj(r)[0].get('title')}")
r = c.post("/entity/versions/_search", headers=ARR,
           json={"filters": [PROJ, ["entity.Shot.open_notes_count", "greater_than", 3]],
                 "fields": ["code"], "page": {"size": 1}})
rows.append(f"  dotted entity.Shot.open_notes_count greater_than 3 -> {r.status_code}")
rows.append("  " + errs(r).replace("\n", "\n  "))

# ---------------------------------------------------------------- sort
rows.append("\n=== sort: accepted, and ignored")


def order(sort, params=None):
    p = {"filter[project.Project.id]": PROJECT, "fields": "code,open_notes_count", "page[size]": 5}
    if sort:
        p["sort"] = sort
    r = c.get("/entity/shots", params=p)
    if not r.ok:
        return f"{r.status_code} {errobj(r)[0].get('title')}"
    return f"{r.status_code} " + str([(x["id"], x["attributes"]["open_notes_count"]) for x in r.json()["data"]])


for s in (None, "code", "-code", "open_notes_count", "-open_notes_count", "definitely_not_a_field"):
    rows.append(f"  sort={str(s):<24} {order(s)}")

# ---------------------------------------------------------------- _summarize (probe 020)
rows.append("\n=== _summarize, the endpoint that shares the name (probe 020)")
r = c.post("/entity/shots/_summarize", headers=ARR,
           json={"filters": [PROJ], "summary_fields": [{"field": "id", "type": "record_count"}],
                 "grouping": [{"field": "open_notes_count", "type": "exact", "direction": "asc"}]})
rows.append(f"  grouping by open_notes_count -> {r.status_code} {errobj(r)[0].get('title')}")
r = c.post("/entity/shots/_summarize", headers=ARR,
           json={"filters": [PROJ], "summary_fields": [{"field": "open_notes_count", "type": "sum"}]})
rows.append(f"  summary_fields sum of open_notes_count -> {r.status_code} {json.dumps(r.json().get('data'))}")
r = c.post("/entity/shots/_summarize", headers=ARR,
           json={"filters": [PROJ], "summary_fields": [{"field": "id", "type": "record_count"}]})
rows.append(f"  control, record_count of id -> {r.status_code} {json.dumps(r.json().get('data'))}")

# ---------------------------------------------------------------- write / clear / freshness
if not _lib.writes_allowed():
    rows.append("\n(read-only run; pass --write for the write/clear/freshness half)")
else:
    SANDBOX = _lib.sandbox_id(c, env)
    rows.append("\n=== write, in the sandbox project only")
    rows.append("  Project.sg_latest_version — schema says editable=true")
    for label, v in [("a string", "zzprobe_summary"), ("an int", 42), ("null", None),
                     ("an entity hash", {"type": "Project", "id": SANDBOX})]:
        r = c.request("PUT", f"/entity/projects/{SANDBOX}", headers=JSN, json={"sg_latest_version": v})
        back = c.get(f"/entity/projects/{SANDBOX}",
                     params={"fields": "sg_latest_version"}).json()["data"]["attributes"]
        rows.append(f"    {label:<16} -> {r.status_code} {errobj(r)[0].get('title') if not r.ok else ''}"
                    f"  reads back {back['sg_latest_version']!r}")

    rows.append("\n  Version.open_notes_count — schema says editable=false")
    r = c.post("/entity/versions", headers=JSN,
               json={"project": {"type": "Project", "id": SANDBOX}, "code": "zzprobe_summary",
                     "open_notes_count": 3})
    rows.append(f"    POST create with open_notes_count=3 -> {r.status_code} {errobj(r)[0].get('title')}")
    r = c.post("/entity/versions", headers=JSN,
               json={"project": {"type": "Project", "id": SANDBOX}, "code": "zzprobe_summary"})
    vid = r.json()["data"]["id"]
    rows.append(f"    plain create -> {r.status_code}; 201 body includes open_notes_count="
                f"{r.json()['data']['attributes'].get('open_notes_count')!r}")
    r = c.request("PUT", f"/entity/versions/{vid}", headers=JSN, json={"open_notes_count": 3})
    rows.append(f"    PUT open_notes_count=3 -> {r.status_code} {errobj(r)[0].get('title')}")

    def count():
        return c.get(f"/entity/versions/{vid}",
                     params={"fields": "open_notes_count"}).json()["data"]["attributes"]["open_notes_count"]

    rows.append("\n=== freshness: does the count lag the Note that changes it?")
    rows.append(f"    before any Note                        {count()}")
    r = c.post("/entity/notes", headers=JSN,
               json={"project": {"type": "Project", "id": SANDBOX}, "subject": "zzprobe_summary",
                     "content": "zzprobe_summary", "sg_status_list": "opn",
                     "note_links": [{"type": "Version", "id": vid}]})
    nid = r.json()["data"]["id"] if r.ok else None
    t0 = time.time()
    n = count()
    rows.append(f"    Note created 'opn', next read {(time.time() - t0) * 1000:.0f}ms later   {n}")
    if nid:
        c.request("PUT", f"/entity/notes/{nid}", headers=JSN, json={"sg_status_list": "clsd"})
        rows.append(f"    same Note moved to 'clsd'              {count()}")
        c.request("DELETE", f"/entity/notes/{nid}")
        rows.append(f"    Note deleted                           {count()}")
    c.request("DELETE", f"/entity/versions/{vid}")
    rows.append(f"    sandbox Version {vid} deleted")

actual = "\n".join(rows)
_lib.emit("field_types/summary", actual, env)
