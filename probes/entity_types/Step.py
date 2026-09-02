"""Q: how is a Step addressed, partitioned and joined, given it is site-wide and has no project field?

Read-only, always. A Step is shared by every project on the site, so creating or deleting one changes
what every other project sees; this probe never writes and the finding records that create was not
attempted. The crux is `entity_type`: it is the only partition a Step has, and it is what a client must
filter on to answer "which Steps apply to a Shot".

Uses sample_projects only to show the negative: the Tasks of one project resolve to Steps that the
site-wide listing already contains, and no project filter reaches the Step endpoint.
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
rows = []


def err(r):
    """Whole errors[] object, source included. Truncating it throws away the vocabulary it names."""
    try:
        return json.dumps(r.json().get("errors", r.json()), indent=1)
    except ValueError:
        return r.text


def search(slug, filt, fields=None, size=500, sort=None):
    body = {"filters": filt, "fields": fields or ["id"], "page": {"size": size}}
    if sort:
        body["sort"] = sort
    r = c.post(f"/entity/{slug}/_search", headers=ARR, json=body)
    return (len(r.json()["data"]), r.json()["data"]) if r.ok else (f"ERR {r.status_code}", err(r))


def count(slug, filt):
    """Exact totals; a _search page caps at its page size and would read as a ceiling (probe 020)."""
    r = c.post(f"/entity/{slug}/_summarize", headers=ARR,
               json={"filters": filt, "summary_fields": [{"field": "id", "type": "record_count"}]})
    return r.json()["data"]["summaries"]["id"] if r.ok else f"ERR {r.status_code} {err(r)}"


rows.append("=== slug: which path serves this type")
for path in ("/entity/steps", "/entity/step", "/entity/Step", "/entity/pipeline_steps"):
    r = c.get(path, params={"page[size]": 1, "fields": "code"})
    extra = ""
    if r.ok:
        d = r.json()["data"]
        extra = f"  links.self={d[0]['links']['self'] if d else None}  type={d[0]['type'] if d else None}"
    rows.append(f"  GET {path:24} -> {r.status_code}{extra}")
    if not r.ok:
        rows.append(f"      {err(r)}")
r = c.get("/entity/steps/1")
rows.append(f"  GET /entity/steps/1 (id 1) -> {r.status_code}  {'' if r.ok else err(r)}")

rows.append("\n=== schema: every field on Step")
sch = c.get("/schema/Step/fields").json()["data"]
for name, fd in sorted(sch.items()):
    p = {k: v.get("value") for k, v in fd.get("properties", {}).items()}
    vt = p.get("valid_types")
    rows.append(f"  {name:20} {fd['data_type']['value']:10} editable={str(fd['editable']['value']):5} "
                f"mandatory={str(fd['mandatory']['value']):5} unique={str(fd['unique']['value']):5}"
                + (f" valid_types={vt}" if vt else ""))
rows.append(f"  fields: {len(sch)}    'project' present: {'project' in sch}")

rows.append("\n=== site-wide: can a client scope Steps to a project?")
n, e = search("steps", [["project", "is", {"type": "Project", "id": PROJECT}]])
rows.append(f"  _search filter project is <sample project> -> {n}")
rows.append(e if isinstance(e, str) else "")
r = c.get("/entity/steps", params={"filter[project]": PROJECT, "page[size]": 1})
rows.append(f"  GET ?filter[project]=<id> -> {r.status_code}\n      {err(r) if not r.ok else ''}")
r = c.get("/entity/steps", params={"project_id": PROJECT, "page[size]": 500, "fields": "code"})
rows.append(f"  GET ?project_id=<id> -> {r.status_code}, "
            f"{len(r.json()['data']) if r.ok else err(r)} rows")
base, all_steps = search("steps", [], ["code", "short_name", "entity_type", "list_order"])
rows.append(f"  GET /entity/steps (no scope) -> {base} rows      "
            f"same count as ?project_id: {r.ok and len(r.json()['data']) == base}")
_lib.note_from(all_steps)

rows.append("\n=== entity_type: the only partition (data type: field_types/entity_type)")
by_type, ids_by_type = {}, {}
for s in all_steps:
    a = s["attributes"]
    by_type.setdefault(a.get("entity_type"), []).append(a)
    ids_by_type.setdefault(a.get("entity_type"), []).append(s["id"])
for t, group in sorted(by_type.items(), key=lambda kv: -len(kv[1])):
    codes = [g["code"] for g in group]
    rows.append(f"  {str(t):12} {len(group):3} steps   short_name unique within type: "
                f"{len({g['short_name'] for g in group}) == len(group)}   "
                f"code unique within type: {len(set(codes)) == len(codes)}")
rows.append(f"  distinct entity_type values: {sorted(str(t) for t in by_type)}")
rows.append(f"  a Step row: {json.dumps(all_steps[0])}")

rows.append("\n=== identity: code vs short_name, site-wide")
for f in ("code", "short_name", "cached_display_name"):
    vals = [s["attributes"].get(f) for s in all_steps]
    dupes = sorted({v for v in vals if vals.count(v) > 1})
    rows.append(f"  {f:20} {len(set(vals)):3} distinct of {len(vals)}   "
                f"repeated: {len(dupes)}  {json.dumps(dupes[:6])}")
same = sum(1 for s in all_steps
           if s["attributes"].get("cached_display_name") == s["attributes"].get("code"))
rows.append(f"  cached_display_name == code on {same} of {len(all_steps)} rows")
n, _ = search("steps", [["short_name", "is", all_steps[0]["attributes"]["short_name"]]])
rows.append(f"  filter short_name is <first step's short_name> -> {n} rows")

rows.append("\n=== which fields anywhere point at Step")
TYPES = sorted(c.get("/schema").json()["data"].keys())
pointers, catch_all = [], []
for t in TYPES:
    r = c.get(f"/schema/{t}/fields")
    if not r.ok:
        continue
    for fname, fd in r.json()["data"].items():
        vt = fd.get("properties", {}).get("valid_types", {}).get("value") or []
        if "Step" not in vt:
            continue
        # A field naming most of the schema is a generic any-entity link, not a Step link.
        (catch_all if len(vt) > 20 else pointers).append(
            (t, fname, fd["data_type"]["value"], fd["editable"]["value"],
             fd["mandatory"]["value"], vt))
for t, fname, dt, ed, mand, vt in sorted(pointers):
    rows.append(f"  {t}.{fname:16} {dt:12} editable={str(ed):5} mandatory={str(mand):5} valid_types={vt}")
rows.append(f"  {len(pointers)} field(s) naming Step specifically, across {len(TYPES)} types in /schema")
rows.append(f"  plus {len(catch_all)} generic any-entity fields that list Step among "
            f"{len(catch_all[0][5]) if catch_all else 0} valid_types: "
            f"{sorted({f'{f}' for _, f, _, _, _, _ in catch_all})}")
rows.append(f"  Step's own fields pointing back at a Task: "
            f"{[k for k, v in sch.items() if 'Task' in (v.get('properties', {}).get('valid_types', {}).get('value') or [])]}")

rows.append("\n=== Task.step: the join, and its direction")
n, tasks = search("tasks", [["project", "is", {"type": "Project", "id": PROJECT}],
                            ["step", "is_not", None]],
                  ["content", "step", "entity"], size=500)
rows.append(f"  Tasks in the sample project with a step -> {n} (page size 500)")
if isinstance(n, int) and n:
    _lib.note_from(tasks[:1])
    rows.append(f"  a Task row: {json.dumps(tasks[0])}")
    used, mismatch = {}, {}
    step_of = {s["id"]: s["attributes"] for s in all_steps}
    for t in tasks:
        d = (t.get("relationships", {}).get("step", {}) or {}).get("data")
        e = (t.get("relationships", {}).get("entity", {}) or {}).get("data")
        if not d:
            continue
        used[d["id"]] = d.get("name")
        want = step_of.get(d["id"], {}).get("entity_type")
        if e and want and e["type"] != want:
            mismatch[(e["type"], want)] = mismatch.get((e["type"], want), 0) + 1
    site_ids = {s["id"] for s in all_steps}
    rows.append(f"  distinct Steps used by that project: {len(used)} of {base} site-wide; "
                f"all present in the site-wide listing: {set(used) <= site_ids}")
    rows.append(f"  Tasks whose entity type differs from their Step's entity_type, in that page: "
                f"{sum(mismatch.values())}  {mismatch}")
rows.append(f"  filter step is {{type: Step, id: <a Shot step>}}, site-wide -> "
            f"{count('tasks', [['step', 'is', {'type': 'Step', 'id': all_steps[0]['id']}]])} tasks")
rows.append(f"  filter step is <the same step's bare id> -> "
            f"{count('tasks', [['step', 'is', all_steps[0]['id']]])}")

rows.append("\n  site-wide: is a Task ever linked to a Step declared for another entity type?")
KINDS = sorted(str(t) for t in by_type)
pairs = {}
for et in KINDS:
    total = count("tasks", [["step.Step.entity_type", "is", et]])
    same = count("tasks", [["step.Step.entity_type", "is", et], ["entity", "type_is", et]])
    rows.append(f"    step.Step.entity_type is {et!r:8} -> {total} tasks, {same} on a matching "
                f"{et}, {total - same if isinstance(total, int) else '?'} on something else")
    # Exact tally of the mismatches: page the offenders and read the entity type off each row.
    page, cursor = 1, True
    while cursor:
        r = c.post("/entity/tasks/_search", headers=ARR,
                   json={"filters": [["step.Step.entity_type", "is", et],
                                     ["entity", "type_is_not", et]],
                         "fields": ["entity"], "page": {"size": 500, "number": page}})
        d = r.json()["data"] if r.ok else []
        for t in d:
            e = (t.get("relationships", {}).get("entity", {}) or {}).get("data")
            pairs[(et, e["type"] if e else None)] = pairs.get((et, e["type"] if e else None), 0) + 1
        cursor, page = bool(d), page + 1
for (step_et, task_et), n in sorted(pairs.items(), key=lambda kv: -kv[1]):
    rows.append(f"    Step declared for {step_et:6} used on a Task whose entity is {str(task_et):8} "
                f"-> {n} tasks")
rows.append(f"    tasks with no step at all: {count('tasks', [['step', 'is', None]])} of "
            f"{count('tasks', [])} site-wide")

rows.append("\n=== listing the Steps available for one entity type")
for t in sorted(str(x) for x in by_type):
    n, _ = search("steps", [["entity_type", "is", t]])
    rows.append(f"  filter entity_type is {t!r:10} -> {n}")
for s in ("list_order", "-list_order"):
    n, ordered = search("steps", [["entity_type", "is", "Shot"]],
                        ["code", "short_name", "list_order"], sort=[s])
    if isinstance(n, int):
        _lib.note_from(ordered)
        rows.append(f"  sort {s:12} -> {[o['attributes']['list_order'] for o in ordered]}")
n, _ = search("steps", [["entity_type", "is", "shots"]])
rows.append(f"  filter entity_type is 'shots' (REST slug, negative control) -> {n}")
rows.append(f"  Steps reachable by id from a Shot pivot column (field_types/pivot_column): "
            f"{count('steps', [['id', 'in', ids_by_type['Shot'][:5]]])} of 5 ids resolve")
n, depts = search("departments", [], ["name", "steps"])
if isinstance(n, int):
    _lib.note_from(depts)
    filled = sum(1 for d in depts if (d.get("relationships", {}).get("steps", {}) or {}).get("data"))
    rows.append(f"  Department.steps: {filled} of {n} departments list any Step")

rows.append("\n=== dotted read through Task.step (probe 003)")
n, dotted = search("tasks", [["project", "is", {"type": "Project", "id": PROJECT}],
                             ["step", "is_not", None]],
                   ["content", "step.Step.code", "step.Step.short_name",
                    "step.Step.entity_type", "step.Step.color", "step.Step.id"], size=3)
if isinstance(n, int):
    _lib.note_from(dotted)
    for d in dotted:
        rows.append(f"  {json.dumps(d['attributes'])}")
else:
    rows.append(f"  {n} {dotted}")

rows.append("\n=== status and mandatory fields")
rows.append(f"  status_list fields on Step: "
            f"{[k for k, v in sch.items() if v['data_type']['value'] in ('status_list', 'list')]}")
rows.append(f"  schema-mandatory: {sorted(k for k, v in sch.items() if v['mandatory']['value'])}")
rows.append(f"  read-only:        {sorted(k for k, v in sch.items() if not v['editable']['value'])}")
rows.append("  no create attempted: a Step is site-wide, so one made here would appear in every")
rows.append("  project's Task pipeline and add a pivot column to its entity type (field_types/pivot_column).")

_lib.emit("entity_types/Step", "\n".join(rows), env)
