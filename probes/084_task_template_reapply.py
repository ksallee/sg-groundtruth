"""Q: what does setting `task_template` on a Shot that already has Tasks do over the API?

The question a task template sync app rests on. Two overlapping sandbox templates: one task with the
same `content` and `step` in both, one with the same `content` at a different `step`, and one distinct
task in each. A Shot made with the first gets a status change and a hand-made Task, then the field is
changed, repeated, restored and cleared, and the Task list is read after each write. A second Shot
with no template gets one applied afterwards, and a third takes the update through `_batch`.

Writes only, in the sandbox, behind --write. Every row is deleted.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib  # noqa: E402
import _tasktpl as T  # noqa: E402

env = _lib.load_env()
c = _lib.client()
rows = []
if not _lib.writes_allowed():
    raise SystemExit("probe 084 writes; run with --write")
S = _lib.sandbox_id(c, env)
P = {"type": "Project", "id": S}
ST = T.steps(c)
codes = sorted(ST)
s1, s2, s3, s4 = ({"type": "Step", "id": ST[k]} for k in codes[:4])

# Same content and step in both, same content at another step, and one of each alone.
T1 = {"zzprobe_084_same": {"step": s1, "sg_sort_order": 10},
      "zzprobe_084_moved": {"step": s2, "sg_sort_order": 20},
      "zzprobe_084_only1": {"step": s3, "sg_sort_order": 30}}
T2 = {"zzprobe_084_same": {"step": s1, "sg_sort_order": 10},
      "zzprobe_084_moved": {"step": s3, "sg_sort_order": 20},
      "zzprobe_084_only2": {"step": s4, "sg_sort_order": 40}}


def table(label, entity, tpl_names):
    got = T.tasks_on(c, entity)
    T.adopt(made, got)
    sh = c.get(f"/entity/{entity['type'].lower()}s/{entity['id']}", params={"fields": "task_template"}).json()["data"]
    rows.append(f"  {label}: {len(got)} Tasks; Shot.task_template="
                f"{(T.rel(sh, 'task_template') or {}).get('name')}")
    for t in got:
        a = t["attributes"]
        src = (T.rel(t, "template_task") or {}).get("id")
        rows.append(f"    id={t['id']} {a['content']:<20} step={(T.rel(t, 'step') or {}).get('name')!s:<13} "
                    f"from={tpl_names.get(src, src)!s:<9} status={a['sg_status_list']}")
    return got


with _lib.Created(c) as made:
    TT1, ids1 = T.template(c, made, "zzprobe_084_tt1", T1)
    TT2, ids2 = T.template(c, made, "zzprobe_084_tt2", T2)
    names = {**{i: f"tt1:{k[12:]}" for k, i in ids1.items()}, **{i: f"tt2:{k[12:]}" for k, i in ids2.items()}}

    rows.append("=== Shot A, created with tt1, then worked on")
    A = T.ref(T.post(c, made, "shots", {"project": P, "code": "zzprobe_084_a", "task_template": TT1}))
    got = T.tasks_on(c, A)
    T.adopt(made, got)
    same = next(t for t in got if t["attributes"]["content"] == "zzprobe_084_same")
    r = c.put(f"/entity/tasks/{same['id']}", json={"sg_status_list": "ip"})
    rows.append(f"  PUT the 'same' Task sg_status_list ip -> {r.status_code}")
    T.post(c, made, "tasks", {"project": P, "entity": A, "content": "zzprobe_084_manual"})
    table("before", A, names)

    for label, value in (("PUT task_template tt2", TT2), ("PUT task_template tt2 again", TT2),
                         ("PUT task_template tt1", TT1), ("PUT task_template null", None)):
        r = c.put(f"/entity/shots/{A['id']}", json={"task_template": value})
        rows.append(f"\n  {label} -> {r.status_code} {T.errs(r) if not r.ok else ''}")
        table("after", A, names)

    rows.append("\n=== Shot B, created bare with one hand-made Task, then tt1 applied")
    B = T.ref(T.post(c, made, "shots", {"project": P, "code": "zzprobe_084_b"}))
    T.post(c, made, "tasks", {"project": P, "entity": B, "content": "zzprobe_084_same",
                              "step": s1})
    r = c.put(f"/entity/shots/{B['id']}", json={"task_template": TT1})
    rows.append(f"  PUT task_template tt1 -> {r.status_code}")
    table("after", B, names)

    rows.append("\n=== Shot C, created with tt1, tt2 applied through _batch")
    C = T.ref(T.post(c, made, "shots", {"project": P, "code": "zzprobe_084_c", "task_template": TT1}))
    r = c.post("/entity/_batch", json={"requests": [{"request_type": "update", "entity": "Shot",
                                                     "record_id": C["id"], "data": {"task_template": TT2}}]})
    rows.append(f"  _batch update task_template tt2 -> {r.status_code} {T.errs(r) if not r.ok else ''}")
    table("after", C, names)

    # Shot A took tt1 back and gained nothing. Tell "a template already applied is skipped" from "a
    # template task already present is skipped": delete one generated Task, then reapply.
    rows.append("\n=== Shot D, created with tt1, one generated Task deleted, then null and tt1 again")
    D = T.ref(T.post(c, made, "shots", {"project": P, "code": "zzprobe_084_d", "task_template": TT1}))
    got = T.tasks_on(c, D)
    T.adopt(made, got)
    gone = next(t for t in got if t["attributes"]["content"] == "zzprobe_084_only1")
    r = c.delete(f"/entity/tasks/{gone['id']}")
    rows.append(f"  DELETE the generated only1 Task {gone['id']} -> {r.status_code}")
    for label, value in (("PUT task_template null", None), ("PUT task_template tt1", TT1)):
        r = c.put(f"/entity/shots/{D['id']}", json={"task_template": value})
        rows.append(f"  {label} -> {r.status_code}")
    table("after", D, names)

    rows.append("\n=== Shot E, created with tt1, one generated Task deleted, then tt1 sent again unchanged")
    E = T.ref(T.post(c, made, "shots", {"project": P, "code": "zzprobe_084_e", "task_template": TT1}))
    got = T.tasks_on(c, E)
    T.adopt(made, got)
    gone = next(t for t in got if t["attributes"]["content"] == "zzprobe_084_only1")
    r = c.delete(f"/entity/tasks/{gone['id']}")
    rows.append(f"  DELETE the generated only1 Task -> {r.status_code}")
    r = c.put(f"/entity/shots/{E['id']}", json={"task_template": TT1})
    rows.append(f"  PUT task_template tt1 (unchanged) -> {r.status_code}")
    table("after", E, names)

    rows.append("\n=== is there a mode?")
    sch = c.get("/schema/Shot/fields/task_template").json()["data"]
    rows.append(f"  Shot.task_template properties: {sorted(sch.get('properties', {}))}")
    spec = c.get("/spec.json").text
    rows.append(f"  /spec.json mentions of 'task_template': {len(re.findall('task_template', spec))}, "
                f"of 'TaskTemplate': {len(re.findall('TaskTemplate', spec))}")
    r = c.put(f"/entity/shots/{A['id']}", json={"task_template": TT2, "task_template_mode": "replace"})
    rows.append(f"  PUT with a body key task_template_mode -> {r.status_code} {T.errs(r) if not r.ok else ''}")
    table("after the rejected PUT", A, names)

rows.append("\n=== left clean?")
rows.append(f"  sandbox Tasks zzprobe_084*: "
            f"{len(T.search(c, 'tasks', [['project', 'is', P], ['content', 'starts_with', 'zzprobe_084']], ['content']))}")
rows.append(f"  templates zzprobe_084*: "
            f"{len(T.search(c, 'task_templates', [['code', 'starts_with', 'zzprobe_084']], ['code']))}")

_lib.emit("084_task_template_reapply", "\n".join(rows), env)
