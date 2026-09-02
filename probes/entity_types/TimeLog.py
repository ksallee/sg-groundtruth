"""Q: how is a TimeLog addressed and created, and what does the server fill in when a client omits it?

A time-logging tool sends three things: minutes, a Task and a day. Two of them turn out to be optional at
create, and the row that comes back without a `date` is the client bug that is hardest to see, because it
still counts toward `Task.time_logs_sum`. This measures the path slug, the create contract against the
schema's `mandatory` flags (probe 012 found they disagree), what `date` and `user` default to, whether the
rollup is plain addition of `duration` (`field_types/duration`), and whether a script may log against a
HumanUser other than itself.

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
SLUG = "time_logs"
rows = []


def errs(r):
    """The whole errors[] object, `source` included. The 400 is the documentation (probe 017)."""
    try:
        return json.dumps(r.json().get("errors", r.json()))
    except ValueError:
        return r.text


def search(slug, filters, fields, size=500, extra=None):
    body = {"filters": [list(f) for f in filters], "fields": list(fields), "page": {"size": size}}
    body.update(extra or {})
    r = c.post(f"/entity/{slug}/_search", headers=ARR, json=body)
    return (r.json()["data"], None) if r.ok else (None, r)


def count(slug, filters):
    """Exact totals; a _search page caps at its page size and reads as a ceiling (probe 020)."""
    r = c.post(f"/entity/{slug}/_summarize", headers=ARR,
               json={"filters": [list(f) for f in filters],
                     "summary_fields": [{"field": "id", "type": "record_count"}]})
    return r.json()["data"]["summaries"]["id"] if r.ok else f"ERR {r.status_code} {errs(r)}"


def attrs(entity_id, fields):
    return c.get(f"/entity/{SLUG}/{entity_id}", params={"fields": fields}).json()["data"]


rows.append("=== the REST path slug: which spellings of /entity/<slug> resolve")
for variant in (SLUG, "time_log", "TimeLog", "timelogs", "timelog", "timesheet_entries"):
    r = c.get(f"/entity/{variant}", params={"page[size]": 1, "fields": "duration"})
    d = r.json().get("data") if r.ok else None
    rows.append(f"  GET /entity/{variant:<20} -> {r.status_code}"
                + (f"  links.self={d[0]['links']['self']}  type={d[0]['type']}" if d
                   else f"  {errs(r)}" if not r.ok else "  0 rows"))

rows.append("\n=== project-scoped or site-wide")
fields = c.get("/schema/TimeLog/fields").json()["data"]
for f, v in sorted(fields.items()):
    p = {k: vv.get("value") for k, vv in v.get("properties", {}).items()}
    rows.append(f"  {f:<20} {v['data_type']['value']:<10} editable={v['editable']['value']!s:<5} "
                f"mandatory={v['mandatory']['value']!s:<5} unique={v['unique']['value']!s:<5}"
                + (f" valid_types={p['valid_types']}" if p.get("valid_types") else "")
                + (f" default={p['default_value']!r}" if p.get("default_value") is not None else ""))
rows.append(f"  fields: {len(fields)}    'project' present: {'project' in fields}")
page, _ = search(SLUG, [], ["duration", "project"], size=200)
projects = {(row["relationships"]["project"]["data"] or {}).get("id") for row in page}
rows.append(f"  unfiltered listing spans {len(projects)} distinct project(s) in one page of {len(page)}: "
            f"the endpoint is site-wide, every row is project-scoped")
rows.append(f"  record_count in the sample project: "
            f"{count(SLUG, [['project', 'is', {'type': 'Project', 'id': SAMPLE}]])} of "
            f"{count(SLUG, [])} site-wide")

rows.append("\n=== identity: TimeLog has no code, name or content")
for name in ("code", "name", "content", "description", "cached_display_name"):
    v = fields.get(name)
    rows.append(f"  {name:<20} " + ("absent from /schema/TimeLog/fields" if v is None else
                f"data_type={v['data_type']['value']:<10} display_name={v['name']['value']!r:<22} "
                f"editable={v['editable']['value']}"))
for f in ("code", "name"):
    got, r = search(SLUG, [[f, "is", "x"]], ["id"], size=1)
    rows.append(f"  filter {f} is 'x' -> " + (f"{len(got)} rows" if got is not None
                                              else f"{r.status_code} {errs(r)}"))
sample_rows, _ = search(SLUG, [["project", "is", {"type": "Project", "id": SAMPLE}]],
                        ["duration", "date", "description", "cached_display_name",
                         "entity", "user"], size=5)
_lib.note_from(sample_rows)
for row in sample_rows[:3]:
    rows.append(f"  a row: {json.dumps(row)}")

rows.append("\n=== duration and the Task rollup (field_types/duration, entity_types/Task)")
tasks, _ = search("tasks", [["project", "is", {"type": "Project", "id": SAMPLE}],
                            ["time_logs_sum", "greater_than", 0]],
                  ["content", "time_logs_sum", "est_in_mins", "time_vs_est"], size=5)
for t in tasks or []:
    logs, _ = search(SLUG, [["entity", "is", {"type": "Task", "id": t["id"]}]],
                     ["duration", "date"], size=200)
    mins = [row["attributes"]["duration"] for row in logs]
    rows.append(f"  Task time_logs_sum={t['attributes']['time_logs_sum']:<6} "
                f"sum(TimeLog.duration)={sum(m or 0 for m in mins):<6} over {len(mins)} logs {mins}")
r = c.get("/preferences")
prefs = r.json()["data"] if r.ok else {}
rows.append(f"  GET /preferences -> {r.status_code}  hours_per_day={prefs.get('hours_per_day')!r} "
            f"duration_units={prefs.get('duration_units')!r}")

rows.append("\n=== links: what a TimeLog hangs off, and who it belongs to")
TYPES = sorted(c.get("/schema").json()["data"].keys())
pointers, catch_all = [], 0
for t in TYPES:
    r = c.get(f"/schema/{t}/fields")
    if not r.ok:
        continue
    for f, v in r.json()["data"].items():
        vt = v["properties"].get("valid_types", {}).get("value") or []
        if "TimeLog" not in vt:
            continue
        if len(vt) > 20:
            catch_all += 1
        else:
            pointers.append(f"{t}.{f} {v['data_type']['value']} editable={v['editable']['value']} {vt}")
rows.append(f"  fields naming TimeLog specifically, across {len(TYPES)} types: {pointers}")
rows.append(f"  plus {catch_all} generic any-entity fields that list it among 100+ valid_types")

rows.append("\n=== filtering: by Task, by user, and through a dotted path (probe 003)")
if sample_rows:
    ent = (sample_rows[0].get("relationships", {}).get("entity", {}) or {}).get("data")
    usr = (sample_rows[0].get("relationships", {}).get("user", {}) or {}).get("data")
    if ent:
        rows.append(f"  entity is {{type: Task, id}}      -> {count(SLUG, [['entity', 'is', ent]])}")
        rows.append(f"  entity is <bare id>              -> {count(SLUG, [['entity', 'is', ent['id']]])}")
        rows.append(f"  entity type_is 'Task'            -> {count(SLUG, [['entity', 'type_is', 'Task']])}")
        rows.append(f"  entity is None                   -> {count(SLUG, [['entity', 'is', None]])}")
    if usr:
        rows.append(f"  user is {{type: HumanUser, id}}   -> {count(SLUG, [['user', 'is', usr]])}")
        rows.append(f"  user is None                     -> {count(SLUG, [['user', 'is', None]])}")
    got, r = search(SLUG, [["project", "is", {"type": "Project", "id": SAMPLE}]],
                    ["duration", "date", "entity.Task.content", "entity.Task.id",
                     "user.HumanUser.login", "user.HumanUser.name"], size=2)
    if got:
        _lib.note_from(got)
        for row in got:
            rows.append(f"  dotted: {json.dumps(row['attributes'])}")
    else:
        rows.append(f"  dotted read -> {r.status_code} {errs(r)}")
rows.append(f"  date is None                     -> {count(SLUG, [['date', 'is', None]])} of "
            f"{count(SLUG, [])} site-wide")

rows.append("\n=== status")
rows.append(f"  status_list or list fields on TimeLog: "
            f"{[f for f, v in fields.items() if v['data_type']['value'] in ('status_list', 'list')]}")
rows.append(f"  read-only:        {sorted(f for f, v in fields.items() if not v['editable']['value'])}")
rows.append(f"  schema-mandatory: {sorted(f for f, v in fields.items() if v['mandatory']['value'])}")

if not _lib.writes_allowed():
    rows.append("\n=== create contract, date defaulting and logging for another user skipped; "
                "re-run with --write")
    _lib.emit("entity_types/TimeLog", "\n".join(rows), env)
    raise SystemExit(0)

SANDBOX = _lib.sandbox_id(c, env)
PJ = {"type": "Project", "id": SANDBOX}

people, _ = search("human_users", [["sg_status_list", "is", "act"]], ["login", "name"], size=10)
_lib.note_from(people or [])
me = c.get("/entity/api_users", params={"page[size]": 1, "fields": "firstname"})
rows.append(f"\n=== the authenticated script is an ApiUser; every HumanUser is 'another user'")
rows.append(f"  active HumanUsers readable: {len(people or [])} (page of 10)")

with _lib.Created(c) as made:
    task = c.post("/entity/tasks", headers=JSN,
                  json={"project": PJ, "content": "zzprobe_timelog_task"})
    TASK = made.add("tasks", task.json()["data"]["id"])
    shot = c.post("/entity/shots", headers=JSN, json={"project": PJ, "code": "zzprobe_timelog_shot"})
    SHOT = made.add("shots", shot.json()["data"]["id"])
    TK = {"type": "Task", "id": TASK}

    rows.append("\n=== create contract: what the server actually requires (probe 012)")
    attempts = [
        ("{}", {}),
        ('{"duration": 60}', {"duration": 60}),
        ('{"date": "2026-01-05"}', {"date": "2026-01-05"}),
        ('{"entity": <Task>}', {"entity": TK}),
        ('{"project": <sandbox>}', {"project": PJ}),
        ('{"project": ..., "duration": 60}', {"project": PJ, "duration": 60}),
        ('{"entity": <Task>, "duration": 60}', {"entity": TK, "duration": 60}),
        ('{"project": ..., "entity": ..., "duration": 60}',
         {"project": PJ, "entity": TK, "duration": 60}),
        ('{"project": ..., "duration": 60, "date": "2026-01-05"}',
         {"project": PJ, "duration": 60, "date": "2026-01-05"}),
        ('{"project": <bare int>, "duration": 60}', {"project": SANDBOX, "duration": 60}),
    ]
    for label, body in attempts:
        r = c.post(f"/entity/{SLUG}", headers=JSN, json=body)
        if r.ok:
            d = r.json()["data"]
            made.add(SLUG, d["id"])
            full = attrs(d["id"], "duration,date,description,cached_display_name")
            rel = {k: (v.get("data") or {}).get("id")
                   for k, v in c.get(f"/entity/{SLUG}/{d['id']}",
                                     params={"fields": "project,entity,user"}
                                     ).json()["data"].get("relationships", {}).items()}
            rows.append(f"  {label:<46} -> {r.status_code} id={d['id']} "
                        f"{json.dumps(full['attributes'])} rel_ids={json.dumps(rel)}")
        else:
            rows.append(f"  {label:<46} -> {r.status_code} {errs(r)}")

    rows.append("\n=== is `date` required, and what does a row without one look like?")
    r = c.post(f"/entity/{SLUG}", headers=JSN, json={"project": PJ, "entity": TK, "duration": 90})
    nodate = made.add(SLUG, r.json()["data"]["id"])
    a = attrs(nodate, "date,duration,cached_display_name")["attributes"]
    rows.append(f"  create with no `date` -> {r.status_code}; reads back {json.dumps(a)}")
    rows.append(f"  it still counts: Task.time_logs_sum = "
                f"{c.get(f'/entity/tasks/{TASK}', params={'fields': 'time_logs_sum'}).json()['data']['attributes']}")
    rows.append(f"  filter date is None, in the sandbox -> "
                f"{count(SLUG, [['project', 'is', PJ], ['date', 'is', None]])}")
    for val in ("2026-01-05", "2026-01-05T09:00:00Z", "05/01/2026", "", None):
        r = c.put(f"/entity/{SLUG}/{nodate}", headers=JSN, json={"date": val})
        back = attrs(nodate, "date")["attributes"].get("date")
        rows.append(f"  PUT date={val!r:<24} -> {r.status_code} reads {back!r}"
                    + ("" if r.ok else f" {errs(r)}"))

    rows.append("\n=== the rollup is plain addition (entity_types/Task)")
    made_ids = []
    for mins in (60, 45, 120):
        r = c.post(f"/entity/{SLUG}", headers=JSN,
                   json={"project": PJ, "entity": TK, "duration": mins, "date": "2026-01-06"})
        made_ids.append(made.add(SLUG, r.json()["data"]["id"]))
        t = c.get(f"/entity/tasks/{TASK}",
                  params={"fields": "time_logs_sum,time_vs_est"}).json()["data"]["attributes"]
        rows.append(f"  + TimeLog duration={mins:<4} -> Task {json.dumps(t)}")
    r = c.delete(f"/entity/{SLUG}/{made_ids[0]}")
    made.rows = [x for x in made.rows if x != (SLUG, made_ids[0])]
    t = c.get(f"/entity/tasks/{TASK}", params={"fields": "time_logs_sum"}).json()["data"]["attributes"]
    rows.append(f"  DELETE one TimeLog -> {r.status_code}; Task {json.dumps(t)}")
    r = c.put(f"/entity/{SLUG}/{made_ids[1]}", headers=JSN, json={"duration": 1})
    t = c.get(f"/entity/tasks/{TASK}", params={"fields": "time_logs_sum"}).json()["data"]["attributes"]
    rows.append(f"  PUT duration 45 -> 1 -> {r.status_code}; Task {json.dumps(t)}")

    rows.append("\n=== can a script log time for another user?")
    for p in (people or [])[:3]:
        r = c.post(f"/entity/{SLUG}", headers=JSN,
                   json={"project": PJ, "entity": TK, "duration": 30, "date": "2026-01-07",
                         "user": {"type": "HumanUser", "id": p["id"]}})
        if r.ok:
            i = made.add(SLUG, r.json()["data"]["id"])
            rel = c.get(f"/entity/{SLUG}/{i}",
                        params={"fields": "user,created_by"}).json()["data"]["relationships"]
            rows.append(f"  user = a HumanUser other than the script -> {r.status_code}; "
                        f"user={json.dumps((rel['user']['data'] or {}).get('type'))} "
                        f"created_by={json.dumps((rel['created_by']['data'] or {}).get('type'))}")
        else:
            rows.append(f"  user = a HumanUser -> {r.status_code} {errs(r)}")
        break
    api_user = me.json()["data"][0]["id"] if me.ok and me.json()["data"] else None
    for label, val in (("<an ApiUser>", {"type": "ApiUser", "id": api_user}),
                       ("<the sandbox Project>", PJ),
                       ("<a bare int>", (people or [{}])[0].get("id")),
                       ("null", None)):
        if val is None and label != "null":
            continue
        r = c.post(f"/entity/{SLUG}", headers=JSN,
                   json={"project": PJ, "entity": TK, "duration": 15, "date": "2026-01-07",
                         "user": val})
        if r.ok:
            i = made.add(SLUG, r.json()["data"]["id"])
            rel = c.get(f"/entity/{SLUG}/{i}", params={"fields": "user"}).json()["data"]
            rows.append(f"  user = {label:<24} -> {r.status_code} reads back "
                        f"{json.dumps((rel['relationships']['user']['data'] or {}).get('type'))}")
        else:
            rows.append(f"  user = {label:<24} -> {r.status_code} {errs(r)}")

    rows.append("\n=== does valid_types ['Task'] bind on `entity`? (field_types/entity)")
    for label, val in (("a Shot", {"type": "Shot", "id": SHOT}),
                       ("the sandbox Project", PJ)):
        r = c.post(f"/entity/{SLUG}", headers=JSN,
                   json={"project": PJ, "entity": val, "duration": 10, "date": "2026-01-08"})
        if r.ok:
            i = made.add(SLUG, r.json()["data"]["id"])
            rel = c.get(f"/entity/{SLUG}/{i}", params={"fields": "entity"}).json()["data"]
            rows.append(f"  entity = {label:<20} -> {r.status_code} reads back "
                        f"{json.dumps((rel['relationships']['entity']['data'] or {}).get('type'))}")
        else:
            rows.append(f"  entity = {label:<20} -> {r.status_code} {errs(r)}")

    rows.append("\n=== does the server keep project and entity.project in step?")
    r = c.post(f"/entity/{SLUG}", headers=JSN, json={"entity": TK, "duration": 20})
    if r.ok:
        i = made.add(SLUG, r.json()["data"]["id"])
        rel = c.get(f"/entity/{SLUG}/{i}",
                    params={"fields": "project,entity"}).json()["data"]["relationships"]
        rows.append(f"  create with entity but no project -> {r.status_code}; project="
                    f"{json.dumps((rel['project']['data'] or {}).get('id'))} "
                    f"(sandbox is {SANDBOX})")
    else:
        rows.append(f"  create with entity but no project -> {r.status_code} {errs(r)}")

    rows.append("\n=== read-only fields, written anyway")
    for f, val in (("created_by", {"type": "HumanUser", "id": (people or [{}])[0].get("id")}),
                   ("created_at", "2020-01-01T00:00:00Z"), ("id", 1)):
        r = c.put(f"/entity/{SLUG}/{nodate}", headers=JSN, json={f: val})
        rows.append(f"  PUT {f:<12} -> {r.status_code} " + ("" if r.ok else errs(r)))

_lib.emit("entity_types/TimeLog", "\n".join(rows), env)
