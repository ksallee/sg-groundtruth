"""Q: which EventLogEntry rows does applying a task template write, and can a consumer tell a
template-generated Task from a hand-made one in the log?

An audit trail or webhook for a template sync app has to recognise the Tasks a template made. Probe
049 found a script's writes reach the log only while its ApiUser has `generate_event_log_entries`
True, so that flag is read first and the probe stops if it is off rather than flipping it.

Writes only, in the sandbox, behind --write. Every row is deleted. The log rows stay: an
EventLogEntry cannot be deleted by a script (probe 025).
"""
import json
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib  # noqa: E402
import _tasktpl as T  # noqa: E402

env = _lib.load_env()
c = _lib.client()
rows = []
if not _lib.writes_allowed():
    raise SystemExit("probe 090 writes; run with --write")
S = _lib.sandbox_id(c, env)
P = {"type": "Project", "id": S}

me = T.search(c, "api_users", [["firstname", "is", env["FPT_API_SCRIPT_NAME"]]], ["generate_event_log_entries"])
flag = me[0]["attributes"]["generate_event_log_entries"] if me else None
rows.append(f"=== ApiUser generate_event_log_entries: {flag}")
if flag is not True:
    rows.append("  off: the probe does not change it; nothing below is measurable")
    _lib.emit("090_template_task_events", "\n".join(rows), env)
    raise SystemExit
ME = {"type": "ApiUser", "id": me[0]["id"]}
EF = ["event_type", "attribute_name", "entity", "meta", "user", "project", "session_uuid", "description"]


def events(ents):
    if not ents:
        return []
    return sorted(T.search(c, "event_log_entries", [["entity", "in", ents]], EF), key=lambda e: e["id"])


def tally(label, evs):
    rows.append(f"  {label}: {len(evs)} rows")
    for (et, an, ic), n in sorted(Counter((e["attributes"]["event_type"], e["attributes"]["attribute_name"],
                                           (e["attributes"]["meta"] or {}).get("in_create")) for e in evs).items(),
                                  key=str):
        rows.append(f"    {n:>3} x {et:<34} attribute={an!s:<22} in_create={ic}")


with _lib.Created(c) as made:
    TT, tids = T.template(c, made, "zzprobe_090_tt",
                          {"zzprobe_090_a": {"sg_sort_order": 10}, "zzprobe_090_b": {"sg_sort_order": 20}},
                          [("zzprobe_090_b", "zzprobe_090_a", {})])
    TT2, _ = T.template(c, made, "zzprobe_090_tt2", {"zzprobe_090_c": {"sg_sort_order": 30}})

    rows.append("\n=== a hand-made Task on a bare Shot, for comparison")
    bare = T.ref(T.post(c, made, "shots", {"project": P, "code": "zzprobe_090_bare"}))
    hand = T.post(c, made, "tasks", {"project": P, "entity": bare, "content": "zzprobe_090_hand",
                                     "sg_sort_order": 10})
    time.sleep(2)
    tally("the hand-made Task", events([T.ref(hand)]))

    rows.append("\n=== POST /entity/shots with task_template")
    sh = T.ref(T.post(c, made, "shots", {"project": P, "code": "zzprobe_090_shot", "task_template": TT}))
    gen = T.tasks_on(c, sh)
    T.adopt(made, gen)
    gdeps = T.deps_among(c, [t["id"] for t in gen])
    time.sleep(2)
    tally("the Shot", events([sh]))
    tally("the 2 generated Tasks", events([T.ref(t) for t in gen]))
    tally("the generated TaskDependency", events([T.ref(d) for d in gdeps]))
    ev = events([T.ref(gen[0])])
    new = next((e for e in ev if e["attributes"]["event_type"].endswith("_New")), None)
    if new:
        a = new["attributes"]
        rows.append(f"  a generated Task's _New: user={json.dumps(T.rel(new, 'user'))} "
                    f"session_uuid={a['session_uuid']}")
        rows.append(f"    meta={json.dumps(a['meta'])}")
        rows.append(f"    description={a['description']!r}")
    tt_ev = [e for e in ev if e["attributes"]["attribute_name"] in ("template_task", "task_template")]
    for e in tt_ev:
        rows.append(f"  {e['attributes']['attribute_name']} change meta={json.dumps(e['attributes']['meta'])}")
    shot_tt = [e for e in events([sh]) if e["attributes"]["attribute_name"] in ("task_template", "tasks")]
    for e in shot_tt:
        m = e["attributes"]["meta"]
        rows.append(f"  Shot.{e['attributes']['attribute_name']} meta: "
                    f"{json.dumps({k: m.get(k) for k in ('in_create', 'old_value', 'new_value', 'added', 'removed') if k in m})[:300]}")

    rows.append("\n=== PUT task_template tt2 on the same Shot")
    before = {t["id"] for t in gen}
    r = c.put(f"/entity/shots/{sh['id']}", json={"task_template": TT2})
    added = [t for t in T.tasks_on(c, sh) if t["id"] not in before]
    T.adopt(made, added)
    time.sleep(2)
    rows.append(f"  -> {r.status_code}, {len(added)} Task added")
    tally("the Shot, all rows so far", events([sh]))
    tally("the added Task", events([T.ref(t) for t in added]))

    rows.append("\n=== filtering the log for template-generated Tasks")
    for label, flt in (("attribute_name is template_task", [["attribute_name", "is", "template_task"],
                                                             ["entity", "in", [T.ref(t) for t in gen + added]]]),
                       ("user is this ApiUser, entity type Task, this Shot's Tasks",
                        [["user", "is", ME], ["entity", "in", [T.ref(t) for t in gen]]])):
        r = c.post("/entity/event_log_entries/_search", headers=T.ARR,
                   json={"filters": flt, "fields": ["event_type"], "page": {"size": 100}})
        rows.append(f"  {label}: {r.status_code} {len(r.json()['data']) if r.ok else T.errs(r)}")

rows.append("\n=== left clean?")
rows.append(f"  sandbox Tasks zzprobe_090*: "
            f"{len(T.search(c, 'tasks', [['project', 'is', P], ['content', 'starts_with', 'zzprobe_090']], ['content']))}")

_lib.emit("090_template_task_events", "\n".join(rows), env)
