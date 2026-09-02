"""Q: how does a `calculated` field read, write, clear and filter?

No site has an editable one — probe 019 found `calculated` is among the data types REST refuses to
create, and every calculated field on this site reports `editable: false`. So the write half is not
"not applicable": a caller will try, and the corpus has to say what the server returns. Probe 004
found `cached_display_name` reports editable and then drops the write at 200, so the read-back after
the attempt is the part that settles it.

The other question is whether the expression is exposed. If it is not, a client can show the number
but never explain it.

Read-only half runs ungated. The one write goes into the sandbox project behind --write.
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
TYPES = ["Version", "Shot", "Asset", "Task", "Project", "Sequence", "Note", "PublishedFile",
         "Playlist"]
CALC = ["workload", "workload_per_day", "workload_per_day_per_assignee"]
rows = []


def search(filt, entity="tasks", size=200, fields=None, sort=None):
    """Row count, or the whole errors[] object. Never a slice — the 400 is the teaching content."""
    body = {"filters": filt, "fields": fields or ["content"], "page": {"size": size}}
    if sort:
        body["sort"] = sort
    r = c.post(f"/entity/{entity}/_search", headers=ARR, json=body)
    if not r.ok:
        return None, json.dumps(r.json().get("errors"), indent=1)
    return len(r.json()["data"]), None


def task(tid, fields):
    return c.get(f"/entity/tasks/{tid}", params={"fields": fields}).json()["data"]


# --------------------------------------------------------------- schema
rows.append("=== schema: every calculated field on the main entity types")
for t in TYPES:
    r = c.get(f"/schema/{t}/fields")
    if not r.ok:
        rows.append(f"  {t:<14} GET /schema/{t}/fields -> {r.status_code}")
        continue
    d = r.json()["data"]
    hits = sorted(f for f, m in d.items() if m["data_type"]["value"] == "calculated")
    kin = sorted(f for f, m in d.items()
                 if m["data_type"]["value"] in ("summary", "pivot_column"))
    rows.append(f"  {t:<14} {len(d):>3} fields, calculated: {hits or 'none'}"
                f"  (other computed types: {len(kin)})")

rows.append("\n=== schema: GET /schema/Task/fields/workload in full")
one = c.get("/schema/Task/fields/workload").json()["data"]
rows.append(json.dumps(one, indent=1))

rows.append("\n=== schema: properties of all three, and what is editable")
for f in CALC:
    m = c.get(f"/schema/Task/fields/{f}").json()["data"]
    p = m["properties"]
    rows.append(f"  {f}")
    rows.append(f"    properties keys      {sorted(p)}")
    rows.append(f"    editable             {m['editable']['value']} "
                f"(name editable={m['name']['value']!r} -> {m['name']['editable']})")
    rows.append(f"    calculated_function  {p['calculated_function']['value']!r} "
                f"(editable={p['calculated_function']['editable']})")
    rows.append(f"    renderer             {p['renderer']['value']!r} "
                f"(editable={p['renderer']['editable']})")
    rows.append(f"    summary_default      {p['summary_default']['value']!r}")
rows.append("  no data_type for the result anywhere — `renderer` is the only declaration of what "
            "comes back")

# ----------------------------------------------------- read, on real rows
rows.append("\n=== read: attributes or relationships, and the JSON type")
r = c.get("/entity/tasks", params={"filter[project.Project.id]": PROJECT, "page[size]": 40,
                                   "fields": ",".join(CALC + ["duration", "content"]),
                                   "sort": "-id"})
tasks = r.json()["data"]
rows.append(f"  {len(tasks)} Tasks on the sample project")
if tasks:
    rows.append(f"  keys of one row: {sorted(tasks[0])}")
    rows.append(f"  relationships:   {sorted(tasks[0].get('relationships', {}))}")
    for f in CALC + ["duration"]:
        seen = {}
        for t in tasks:
            v = t["attributes"].get(f, "<absent>")
            k = f"{v!r} ({type(v).__name__})"
            seen[k] = seen.get(k, 0) + 1
        top = sorted(seen.items(), key=lambda kv: -kv[1])[:4]
        rows.append(f"  {f:<32} {', '.join(f'{k} x{n}' for k, n in top)}")

rows.append("\n=== read: is it returned without naming it, under fields=*?")
r = c.get("/entity/tasks", params={"filter[project.Project.id]": PROJECT, "page[size]": 1,
                                   "fields": "*"})
attrs = r.json()["data"][0]["attributes"] if r.json()["data"] else {}
_lib.note_from(r.json())
rows.append(f"  fields=* -> {len(attrs)} attributes; calculated among them: "
            f"{[f for f in CALC if f in attrs]}")

rows.append("\n=== read: rows where the dependency is set, so the value is not null")
n, err = search([PROJ, ["duration", "is_not", None]], size=10,
                fields=CALC + ["duration"])
rows.append(f"  Tasks with duration is_not None on the sample project: {n}")
r = c.post("/entity/tasks/_search", headers=ARR,
           json={"filters": [PROJ, ["duration", "is_not", None]],
                 "fields": CALC + ["duration", "content"], "page": {"size": 5}})
for t in r.json().get("data", []):
    a = t["attributes"]
    _lib.note_names(a.get("content") or "")
    rows.append(f"  duration={a.get('duration')!r:<8} workload={a.get('workload')!r:<8} "
                f"per_day={a.get('workload_per_day')!r:<10} "
                f"per_assignee={a.get('workload_per_day_per_assignee')!r}")

rows.append("\n=== read: the one non-system calculated field on this site, a text renderer")
m = c.get("/schema/Asset/fields/sg_calculated").json()["data"]
rows.append(f"  Asset.sg_calculated  formula={m['properties']['calculated_function']['value']!r} "
            f"renderer={m['properties']['renderer']['value']!r} "
            f"editable={m['editable']['value']}")
r = c.get("/entity/assets", params={"page[size]": 4, "fields": "code,id,sg_calculated"})
_lib.note_from(r.json())
for a in r.json().get("data", []):
    rows.append(f"  id={a['id']} code={a['attributes'].get('code')!r} -> "
                f"sg_calculated={a['attributes'].get('sg_calculated')!r} "
                f"({type(a['attributes'].get('sg_calculated')).__name__})")
_, err = search([["sg_calculated", "is_not", None]], entity="assets")
rows.append("  filtering that one, to check the refusal is the data type and not the field:")
rows.append(err or "  accepted")

# ----------------------------------------------------------------- filter
rows.append("\n=== filter: the API enumerates its own operators (probe 017)")
_, err = search([PROJ, ["workload", "definitely_not_an_operator", None]])
rows.append(err or "  no error — the bogus operator was accepted")

rows.append("\n=== filter: can the column be queried at all?")
base, _ = search([PROJ])
rows.append(f"  baseline {base} Tasks on the sample project")
for label, filt in [
    ("workload is None",               ["workload", "is", None]),
    ("workload is_not None",           ["workload", "is_not", None]),
    ("workload is 0",                  ["workload", "is", 0]),
    ("workload is 480",                ["workload", "is", 480]),
    ("workload greater_than 0",        ["workload", "greater_than", 0]),
    ("workload less_than 100000",      ["workload", "less_than", 100000]),
    ("workload in [480]",              ["workload", "in", [480]]),
    ("workload_per_day is_not None",   ["workload_per_day", "is_not", None]),
    ("duration is_not None (control)", ["duration", "is_not", None]),
]:
    n, err = search([PROJ, filt])
    rows.append(f"  {label:<34} -> {n if err is None else 'ERR'}")
    if err:
        rows.append(err)

rows.append("\n=== filter: sorting on a calculated column, and whether the order is real")
for s in ("workload", "-workload", "workload_per_day", "-workload_per_day_per_assignee"):
    r = c.post("/entity/tasks/_search", headers=ARR,
               json={"filters": [PROJ], "fields": [s.lstrip("-")], "sort": s,
                     "page": {"size": 5}})
    if r.ok:
        vals = [t["attributes"].get(s.lstrip("-")) for t in r.json()["data"]]
        rows.append(f"  _search sort {s:<32} {r.status_code} first 5: {vals}")
    else:
        rows.append(f"  _search sort {s:<32} {r.status_code}")
        rows.append(json.dumps(r.json().get("errors"), indent=1))
for s in ("workload", "-workload"):
    r = c.get("/entity/tasks", params={"filter[project.Project.id]": PROJECT, "page[size]": 5,
                                       "fields": "workload", "sort": s})
    rows.append(f"  GET ?sort={s:<12} -> {r.status_code} "
                f"{[t['attributes'].get('workload') for t in r.json()['data']] if r.ok else json.dumps(r.json().get('errors'))}")

rows.append("\n=== filter: _summarize over a calculated column")
for body, label in [
    ({"filters": [PROJ], "summary_fields": [{"field": "workload", "type": "sum"}]}, "sum(workload)"),
    ({"filters": [PROJ], "summary_fields": [{"field": "id", "type": "count"}],
      "grouping": [{"field": "workload", "type": "exact", "direction": "asc"}]}, "group by workload"),
]:
    s = c.post("/entity/tasks/_summarize", headers=ARR, json=body)
    if s.ok:
        d = s.json()["data"]
        rows.append(f"  {label:<20} {s.status_code} summaries={json.dumps(d['summaries'])}")
        for g in d.get("groups", [])[:4]:
            rows.append(f"      group_name={g['group_name']!r} group_value={g['group_value']!r} "
                        f"{json.dumps(g['summaries'])}")
        if len(d.get("groups", [])) > 4:
            rows.append(f"      ... {len(d['groups'])} groups total")
    else:
        rows.append(f"  {label:<20} {s.status_code} "
                    f"{json.dumps(s.json().get('errors'), indent=1)}")

# ------------------------------------------------------------------ write
if not _lib.writes_allowed():
    rows.append("\n(read-only run; pass --write for the write attempt and the freshness test)")
else:
    SANDBOX = _lib.sandbox_id(c, env)
    rows.append("\n=== write: create a Task, then try to set the calculated field")
    r = c.post("/entity/tasks", json={"project": {"type": "Project", "id": SANDBOX},
                                      "content": f"zzprobe_calculated_{int(time.time())}"})
    rows.append(f"  POST /entity/tasks -> {r.status_code}")
    tid = r.json()["data"]["id"] if r.ok else None
    if not tid:
        rows.append(json.dumps(r.json().get("errors"), indent=1))
    else:
        a = task(tid, ",".join(CALC + ["duration"]))["attributes"]
        rows.append(f"  fresh row: {a}")

        rows.append("\n=== write: POST create with the calculated field in the body")
        r2 = c.post("/entity/tasks", json={"project": {"type": "Project", "id": SANDBOX},
                                           "content": f"zzprobe_calculated_c_{int(time.time())}",
                                           "workload": 480})
        rows.append(f"  POST {{workload: 480}} -> {r2.status_code}")
        if r2.ok:
            rows.append(f"  201 echoes workload="
                        f"{r2.json()['data']['attributes'].get('workload', '<absent>')!r}")
            back = task(r2.json()["data"]["id"], "workload,duration")["attributes"]
            rows.append(f"  read back: {back}  <- did the write take, or was it dropped?")
            c.request("DELETE", f"/entity/tasks/{r2.json()['data']['id']}")
        else:
            rows.append(json.dumps(r2.json().get("errors"), indent=1))

        rows.append("\n=== write: PUT each value, then read back (probe 004: 200 can still drop it)")
        for label, val in [("480", 480), ("0", 0), ("'480'", "480"), ("null", None),
                           ("'{duration}*2'", "{duration}*2")]:
            u = c.request("PUT", f"/entity/tasks/{tid}", json={"workload": val}, headers=JSN)
            got = task(tid, "workload")["attributes"].get("workload", "<absent>")
            rows.append(f"  PUT {{workload: {label}}} -> {u.status_code}, reads back {got!r}")
            if not u.ok:
                rows.append(json.dumps(u.json().get("errors"), indent=1))

        rows.append("\n=== clear: the same three ways a caller would empty a field")
        for label, body in [("null", {"workload": None}), ("''", {"workload": ""}),
                            ("0", {"workload": 0})]:
            u = c.request("PUT", f"/entity/tasks/{tid}", json=body, headers=JSN)
            got = task(tid, "workload")["attributes"].get("workload", "<absent>")
            rows.append(f"  PUT {{workload: {label}}} -> {u.status_code}, reads back {got!r}")

        rows.append("\n=== write: the schema side — does the formula endpoint take a write?")
        # The formula is site-wide, not project-scoped, so this writes back the value already
        # there. A different one would change every Task on the site, sandbox or not.
        cur = c.get("/schema/Task/fields/workload").json()["data"]["properties"]
        cur = cur["calculated_function"]["value"]
        u = c.request("PUT", "/schema/Task/fields/workload", headers=JSN,
                      json={"properties": [{"property_name": "calculated_function",
                                            "value": cur}]})
        rows.append(f"  PUT calculated_function={cur!r} (its current value) -> {u.status_code}")
        rows.append(json.dumps(u.json(), indent=1)[:700] if u.content else "  (empty body)")
        now = c.get("/schema/Task/fields/workload").json()["data"]["properties"]
        rows.append(f"  formula still {now['calculated_function']['value']!r}")

        rows.append("\n=== freshness: workload = {duration}; move the dependency, read straight back")
        for mins in (480, 960, None):
            t0 = time.time()
            u = c.request("PUT", f"/entity/tasks/{tid}", json={"duration": mins}, headers=JSN)
            a = task(tid, ",".join(CALC + ["duration"]))["attributes"]
            rows.append(f"  duration <- {mins!r:<6} PUT {u.status_code} "
                        f"({time.time() - t0:.2f}s later) duration={a.get('duration')!r} "
                        f"workload={a.get('workload')!r} "
                        f"per_day={a.get('workload_per_day')!r} "
                        f"per_assignee={a.get('workload_per_day_per_assignee')!r}")
        rows.append("  and the same row through _search, in case the two paths differ:")
        r = c.post("/entity/tasks/_search", headers=ARR,
                   json={"filters": [["id", "is", tid]], "fields": CALC + ["duration"]})
        rows.append(f"  {json.dumps(r.json()['data'][0]['attributes'])}")

        rows.append("\n=== freshness: does a filter see the new value immediately?")
        c.request("PUT", f"/entity/tasks/{tid}", json={"duration": 600}, headers=JSN)
        n, err = search([["id", "is", tid], ["workload", "is", 600]])
        rows.append(f"  duration=600 then filter workload is 600 -> "
                    f"{n if err is None else 'ERR'}")
        if err:
            rows.append(err)

        d = c.request("DELETE", f"/entity/tasks/{tid}")
        rows.append(f"\n  cleanup: DELETE the throwaway Task -> {d.status_code}")

actual = "\n".join(rows)
_lib.emit("field_types/calculated", actual, env)
