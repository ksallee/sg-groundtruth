"""Q: what exactly does a `color` field hold, given probe 010 found Status.bg_color is comma-separated RGB?

Probed on stock editable fields — Task.color (write, sandbox only), Project.color and Step.color (read only).
Nullability is therefore a write measurement on Task and a row count on the other two: a Step or a Project
row is site-wide, so neither is written here, and the `is null` counts below say what rows hold, not what
the field would accept.
Never creates a schema field: probe 019 already established `color` is refused as a data_type, and a name is
burned permanently once created.

The crux is the second block. A caller rendering a swatch needs the exact parse, and Task.color turns out not
to be parseable as a colour at all on any row this site has.
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
FIELD = "color"
rows = []


def err(r):
    """Whole errors[] object, source included. Truncating it throws away the operator vocabulary."""
    try:
        return json.dumps(r.json().get("errors", r.json()), indent=1)
    except ValueError:
        return r.text


def props(entity, field):
    d = c.get(f"/schema/{entity}/fields/{field}").json()["data"]
    flat = {k: (v.get("value") if isinstance(v, dict) else v) for k, v in d.items()}
    return flat, d


def count(entity, filt, project=True):
    """record_count, not a page length: Task pages cap at 500 and the population here is 1900."""
    body = {"filters": ([["project", "is", {"type": "Project", "id": PROJECT}]] if project else []) + filt,
            "summary_fields": [{"field": "id", "type": "record_count"}]}
    r = c.post(f"/entity/{entity}/_summarize", headers=ARR, json=body)
    return (r.json()["data"]["summaries"]["id"], None) if r.ok else (f"ERR {r.status_code}", err(r))


def group(entity, field, project=True):
    body = {"filters": ([["project", "is", {"type": "Project", "id": PROJECT}]] if project else []),
            "summary_fields": [{"field": "id", "type": "record_count"}],
            "grouping": [{"field": field, "type": "exact", "direction": "asc"}]}
    d = c.post(f"/entity/{entity}/_summarize", headers=ARR, json=body).json()["data"]
    return d["summaries"]["id"], {g["group_value"]: g["summaries"]["id"] for g in d["groups"]}


rows.append("=== which entities carry a color field, and what properties does it have")
for ent in ("Task", "Project", "Step", "Version", "Shot", "Asset", "Sequence", "HumanUser", "Note"):
    r = c.get(f"/schema/{ent}/fields")
    if not r.ok:
        rows.append(f"  {ent} -> {r.status_code}")
        continue
    hits = []
    for name, f in r.json()["data"].items():
        dt = f.get("data_type", {})
        if (dt.get("value") if isinstance(dt, dict) else dt) == "color":
            ed = f.get("editable", {})
            hits.append((name, f.get("name", {}).get("value"),
                         ed.get("value") if isinstance(ed, dict) else ed,
                         sorted(f.get("properties", {}))))
    rows.append(f"  {ent}: {hits}")

for ent in ("Task", "Project", "Step"):
    flat, raw = props(ent, FIELD)
    p = {k: v.get("value") for k, v in raw.get("properties", {}).items()}
    rows.append(f"  {ent}.{FIELD} display name={flat.get('name')!r} editable={flat.get('editable')} "
                f"mandatory={flat.get('mandatory')} default_value={p.get('default_value')!r} "
                f"summary_default={p.get('summary_default')!r}")

rows.append("\n=== read: shape, and what the stored values actually are")
r = c.get("/entity/tasks", params={"filter[project.Project.id]": PROJECT,
                                   "fields": f"content,{FIELD},step", "page[size]": 3})
data = r.json()["data"]
_lib.note_from(data)
rows.append(f"  one Task row: {json.dumps(data[0])}")
rows.append(f"  attributes keys {sorted(data[0]['attributes'])}  "
            f"relationships keys {sorted(data[0].get('relationships', {}))}")
rows.append(f"  python type of the value: "
            f"{ {type(d['attributes'].get(FIELD)).__name__ for d in data} }")

r = c.get("/entity/tasks", params={"filter[project.Project.id]": PROJECT,
                                   "fields": f"{FIELD},step.Step.color,step.Step.code",
                                   "page[size]": 2})
dotted = r.json()["data"]
_lib.note_from(dotted)
rows.append(f"  the sentinel resolves in one call through the step link (probe 003):")
for d in dotted:
    rows.append(f"    {json.dumps(d['attributes'])}")

total, groups = group("tasks", FIELD)
rows.append(f"  Task.color in the sample project: {total} tasks -> {groups}")
total, groups = group("tasks", FIELD, project=False)
rows.append(f"  Task.color site-wide:             {total} tasks -> {groups}")

r = c.get("/entity/steps", params={"fields": f"code,{FIELD},entity_type", "page[size]": 100})
steps = r.json()["data"]
_lib.note_from(steps)
vals = [d["attributes"].get(FIELD) for d in steps]
rows.append(f"  Step.color: {len(steps)} steps, {len(set(vals))} distinct, "
            f"null on {vals.count(None)}; sample {sorted(set(v for v in vals if v))[:6]}")

r = c.get("/entity/projects", params={"fields": FIELD, "page[size]": 100})
pv = [d["attributes"].get(FIELD) for d in r.json()["data"]]
rows.append(f"  Project.color: {len(pv)} projects, null on {pv.count(None)}; "
            f"sample {sorted(set(v for v in pv if v))[:6]}")
rows.append(f"  every non-null value parses as three 0-255 ints: "
            f"{all(len(v.split(',')) == 3 and all(s.strip().isdigit() and 0 <= int(s) <= 255 for s in v.split(',')) for v in [x for x in vals + pv if x])}")

rows.append("\n=== the API enumerates its own operators (probe 017)")
for entity, ent_label, project in (("tasks", "Task", True), ("steps", "Step", False)):
    n, e = count(entity, [[FIELD, "definitely_not_an_operator", None]], project=project)
    rows.append(f"  {ent_label}.{FIELD} definitely_not_an_operator null -> {n}")
    rows.append(e or "")

SENTINEL = "pipeline_step"
RGB = "255,128,0"
STEP_RGB = sorted(set(v for v in vals if v))[0]
base, _ = count("tasks", [])
rows.append(f"\n=== filter value formats: Task.color validates nothing, Step/Project.color validate hard")
rows.append(f"  baseline {base} tasks in the project, every one of them {SENTINEL!r}")
for label, value in [
    (f"{SENTINEL!r}", SENTINEL),
    (f"{SENTINEL.upper()!r} (case)", SENTINEL.upper()),
    (f"{STEP_RGB!r} (a real Step colour)", STEP_RGB),
    (f"{RGB!r}", RGB),
    ("'255, 128, 0' (spaces)", "255, 128, 0"),
    ("'#ff8000' (hex)", "#ff8000"),
    ("'red' (CSS name)", "red"),
    ("'255,128' (two components)", "255,128"),
    ("'300,0,0' (out of range)", "300,0,0"),
    ("'zzprobe_nope' (neg control)", "zzprobe_nope"),
    ("null", None),
]:
    out = []
    for entity, project in (("tasks", True), ("steps", False), ("projects", False)):
        n, e = count(entity, [[FIELD, "is", value]], project=project)
        out.append(str(n) if not e else json.loads(e)[0]["title"].split("summarize() ")[-1])
    rows.append(f"  is {label:<34} Task {out[0]:<6} Step {out[1]:<6} Project {out[2]}")
rows.append("  the two Step/Project rejections in full:")
for value in ("#ff8000", "300,0,0"):
    _n, e = count("steps", [[FIELD, "is", value]], project=False)
    rows.append(f"    is {value!r} -> {e}")

rows.append("\n=== the other three operators, on Task.color")
for label, filt in [
    (f"is_not {SENTINEL!r}",                [[FIELD, "is_not", SENTINEL]]),
    ("is_not null",                         [[FIELD, "is_not", None]]),
    (f"in [{SENTINEL!r}, {RGB!r}]",         [[FIELD, "in", [SENTINEL, RGB]]]),
    ("in ['zzprobe_nope'] (neg control)",   [[FIELD, "in", ["zzprobe_nope"]]]),
    (f"in {SENTINEL!r} (bare, not a list)", [[FIELD, "in", SENTINEL]]),
    (f"not_in [{SENTINEL!r}]",              [[FIELD, "not_in", [SENTINEL]]]),
    (f"is [0, 126, 174] (a JSON 3-tuple)",  [[FIELD, "is", [0, 126, 174]]]),
    (f"contains {SENTINEL[:8]!r}",          [[FIELD, "contains", SENTINEL[:8]]]),
    (f"starts_with {SENTINEL[:4]!r}",       [[FIELD, "starts_with", SENTINEL[:4]]]),
]:
    n, e = count("tasks", filt)
    rows.append(f"  {label:<40} -> {n}")
    if e:
        rows.append(f"      {json.loads(e)[0]['title']}")

if not _lib.writes_allowed():
    rows.append("\n(read-only run; pass --write for the write / clear half)")
else:
    SANDBOX = _lib.sandbox_id(c, env)
    rows.append("\n=== write, into the sandbox project only, on a throwaway Task")
    r = c.post("/entity/tasks", json={"project": {"type": "Project", "id": SANDBOX},
                                      "content": "zzprobe_color"})
    tid = r.json()["data"]["id"] if r.ok else None
    if tid is None:
        rows.append(f"  create Task -> {r.status_code} {err(r)}")
    else:
        fresh = c.get(f"/entity/tasks/{tid}",
                      params={"fields": FIELD}).json()["data"]["attributes"]
        rows.append(f"  create Task zzprobe_color, color omitted -> {r.status_code} "
                    f"reads {json.dumps(fresh)}  (schema default_value is null)")

        rc = c.post("/entity/tasks", json={"project": {"type": "Project", "id": SANDBOX},
                                           "content": "zzprobe_color_hex", FIELD: "#ff8000"})
        rows.append(f"  create with color '#ff8000' -> {rc.status_code} "
                    f"{err(rc) if not rc.ok else 'ACCEPTED reads ' + json.dumps(rc.json()['data']['attributes'].get(FIELD))}")
        if rc.ok:
            c.request("DELETE", f"/entity/tasks/{rc.json()['data']['id']}")

        def put(value):
            rr = c.request("PUT", f"/entity/tasks/{tid}", json={FIELD: value},
                           headers={"Content-Type": "application/json"})
            if not rr.ok:
                return rr.status_code, err(rr)
            back = c.get(f"/entity/tasks/{tid}",
                         params={"fields": FIELD}).json()["data"]["attributes"]
            return rr.status_code, f"read back {json.dumps(back)}"

        rows.append("\n  PUT /entity/tasks/<id>  {\"color\": ...}")
        for label, value in [
            ("RGB triple '255,128,0'",        "255,128,0"),
            ("spaces after commas '255, 128, 0'", "255, 128, 0"),
            ("hex '#ff8000'",                 "#ff8000"),
            ("hex, no hash 'ff8000'",         "ff8000"),
            ("CSS name 'red'",                "red"),
            ("a JSON 3-tuple [255,128,0]",    [255, 128, 0]),
            ("a packed integer 16744448",     16744448),
            ("out of range '300,0,0'",        "300,0,0"),
            ("negative '-1,0,0'",             "-1,0,0"),
            ("two components '255,128'",      "255,128"),
            ("four components '255,128,0,255'", "255,128,0,255"),
            ("floats '255.0,128.0,0.0'",      "255.0,128.0,0.0"),
            ("the sentinel 'pipeline_step'",  "pipeline_step"),
            ("arbitrary text 'zzprobe_nope'", "zzprobe_nope"),
        ]:
            code, info = put(value)
            rows.append(f"    {label:<36} -> {code} {info}")

        rows.append("\n  the eight legacy colour names the 400 above names, and what each normalises to")
        for name in ("Blue", "Orange", "Pink", "Red", "Green", "Purple", "Grey", "Black"):
            code, info = put(name)
            code_l, info_l = put(name.lower())
            rows.append(f"    {name:<8} -> {code} {info}    {name.lower():<8} -> {code_l} {info_l}")
        for name in ("Gray", "White", "Cyan"):
            code, info = put(name)
            rows.append(f"    {name:<8} -> {code} {info}")

        rows.append("\n  clear: null vs empty string  (row matched by id, so 1 = matched, 0 = not)")
        for label, value in [("set '255,128,0' (control)", "255,128,0"), ("null", None), ('empty string ""', "")]:
            code, info = put(value)
            n1, _ = count("tasks", [["id", "is", tid], [FIELD, "is", None]], project=False)
            n2, _ = count("tasks", [["id", "is", tid], [FIELD, "is", ""]], project=False)
            rows.append(f"    {label:<26} -> {code} {info}")
            rows.append(f"        matched by  is None -> {n1}   is '' -> {n2}")

        rows.append("\n  does the sentinel survive a round trip, and does a written triple read back verbatim?")
        put("pipeline_step")
        n1, _ = count("tasks", [["id", "is", tid], [FIELD, "is", "pipeline_step"]], project=False)
        rows.append(f"    after PUT 'pipeline_step': filter is 'pipeline_step' -> {n1}")

        d = c.request("DELETE", f"/entity/tasks/{tid}")
        rows.append(f"\ncleanup: DELETE task {tid} -> {d.status_code}")

    rows.append("\n=== schema: color is still not a creatable data_type (probe 019), re-read read-only")
    rows.append("  not re-attempted — a POST /schema/<Type>/fields that 400s still burns nothing, but "
                "probe 019 recorded the 400 verbatim and it needs no second run.")

actual = "\n".join(rows)
_lib.emit("field_types/color", actual, env)
