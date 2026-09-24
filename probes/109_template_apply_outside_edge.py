"""Q: on a template apply, which edges between a Task linked to the template (T) and a Task not linked
to T does the apply delete?

Probe 107 found the apply deletes `a on x` (a claimed root depends on an outside Task) and keeps
`x on b` (the outside Task downstream). This maps the upstream side further. Template T holds a, b with
edge b on a (a is the root). One Shot per case, each with hand-made a, b claimed to T:

  up_nonroot  b on x    x outside, upstream of b, which has a template upstream (a)
  other_tpl   a on y    y linked to another template T2's task, upstream of the root a
  other_shot  a on z    z on another Shot, upstream of the root a
  ctl_down    w on b    control, outside downstream (kept per 107)
  ctl_up      a on v    control, outside upstream of the root (deleted per 107)

Not probed: an outside Task upstream of a Task the apply creates; no edge to that Task can exist before
the apply creates it.

Preconditions: none from an operator. The probe provisions every row it reads (2 templates, 6 Shots,
16 Tasks and their edges) and `_lib.Created` deletes them, failure included.

Writes only, in the sandbox, behind --write. Budget 60 s; wall time and call count are printed.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib  # noqa: E402
import _tasktpl as T  # noqa: E402

T0 = time.monotonic()
env = _lib.load_env()
c = _lib.client()
CALLS = [0]
_request = c.request


def counted(method, path, **kw):
    CALLS[0] += 1
    return _request(method, path, **kw)


c.request = counted
rows = []
if not _lib.writes_allowed():
    raise SystemExit("probe 109 writes; run with --write")
S = _lib.sandbox_id(c, env)
P = {"type": "Project", "id": S}
PX = "zzprobe_109_"


def tref(i):
    return {"type": "Task", "id": i}


def dep(down, up):
    return {"task": tref(down), "dependent_task": tref(up)}


CASES = (  # tag, outside Task name, edge (down, up), where the outside Task lives
    ("up_nonroot", "x", ("b", "x"), "same"),
    ("other_tpl", "y", ("a", "y"), "same"),
    ("other_shot", "z", ("a", "z"), "other"),
    ("ctl_down", "w", ("w", "b"), "same"),
    ("ctl_up", "v", ("a", "v"), "same"),
)

with _lib.Created(c) as made:
    name = {}
    edge_ids = set()

    def edges(label, ids):
        got = T.deps_among(c, list(ids))
        for g in got:
            if g["id"] not in edge_ids:
                edge_ids.add(g["id"])
                made.add("task_dependencies", g["id"])
        rows.append(f"  edges {label}: " + (", ".join(sorted(
            f"{name.get(T.rel(g, 'task')['id'])} on {name.get(T.rel(g, 'dependent_task')['id'])}"
            f" #{g['id']}" for g in got)) or "none"))

    TT, tids = T.template(c, made, PX + "tt", {PX + "a": {}, PX + "b": {}},
                          [(PX + "b", PX + "a", {"dependency_type": "finish-to-start-next-day"})])
    TT2, t2 = T.template(c, made, PX + "tt2", {PX + "y": {}})
    rows.append("template tt: a, b; edge b on a. template tt2: y")

    for tag, out, (down, up), where in CASES:
        rows.append(f"\n=== {tag}: hand-made a, b claimed to tt; outside {out}; edge {down} on {up}")
        sh = T.ref(T.post(c, made, "shots", {"project": P, "code": PX + tag}))
        home = sh
        if where == "other":
            home = T.ref(T.post(c, made, "shots", {"project": P, "code": PX + tag + "_home"}))
        m = {}
        for n in ("a", "b", out):
            body = {"project": P, "entity": home if n == out else sh, "content": PX + n}
            m[n] = T.post(c, made, "tasks", body)["id"]
            name[m[n]] = n
        e = T.post(c, made, "task_dependencies", dep(m[down], m[up]))
        edge_ids.add(e["id"])
        claim = [{"request_type": "update", "entity": "Task", "record_id": m[n],
                  "data": {"template_task": tref(tids[PX + n])}} for n in ("a", "b")]
        if tag == "other_tpl":
            claim.append({"request_type": "update", "entity": "Task", "record_id": m["y"],
                          "data": {"template_task": tref(t2[PX + "y"])}})
        r = c.post("/entity/_batch", json={"requests": claim})
        rows.append(f"  _batch claim ({len(claim)} updates) -> {r.status_code} {'' if r.ok else T.errs(r)}")
        edges("after claim", m.values())
        r = c.put(f"/entity/shots/{sh['id']}", json={"task_template": TT})
        rows.append(f"  PUT Shot task_template=tt -> {r.status_code} {'' if r.ok else T.errs(r)}")
        edges("after PUT tt", m.values())
        live = c.get(f"/entity/task_dependencies/{e['id']}").status_code
        ret = c.get(f"/entity/task_dependencies/{e['id']}",
                    params={"options[return_only]": "retired"}).status_code
        rows.append(f"  pre {down} on {up} #{e['id']}: GET -> {live}, retired -> {ret}")
        if tag == "ctl_down":  # control for the retired read: a DELETEd edge reads 200 there
            d = c.delete(f"/entity/task_dependencies/{e['id']}").status_code
            ret = c.get(f"/entity/task_dependencies/{e['id']}",
                        params={"options[return_only]": "retired"}).status_code
            rows.append(f"  control: DELETE #{e['id']} -> {d}, then retired -> {ret}")
        ot = c.get(f"/entity/tasks/{m[out]}", params={"fields": "entity,template_task"})
        rows.append(f"  outside {out} #{m[out]}: GET -> {ot.status_code}" + (
            f", template_task={(T.rel(ot.json()['data'], 'template_task') or {}).get('id')}" if ot.ok else ""))
        on = T.tasks_on(c, sh, ["content", "template_task", "upstream_tasks"])
        T.adopt(made, on)
        rows.append(f"  Tasks on the Shot: {len(on)}; upstream_tasks: " + ", ".join(
            f"{name.get(t['id'], t['id'])}={[name.get(u['id'], u['id']) for u in (T.rel(t, 'upstream_tasks') or [])]}"
            for t in on))

rows.append("\n=== left clean?")
for slug, f, flt in (("tasks", "content", [["content", "starts_with", PX]]),
                     ("shots", "code", [["project", "is", P], ["code", "starts_with", PX]]),
                     ("task_templates", "code", [["code", "starts_with", PX]]),
                     ("task_dependencies", "task", [["id", "in", sorted(edge_ids)]])):
    rows.append(f"  {slug}: {len(T.search(c, slug, flt, [f]))}")
rows.append(f"\n  wall {time.monotonic() - T0:.1f} s, {CALLS[0]} calls (token fetch not counted)")

_lib.emit("109_template_apply_outside_edge", "\n".join(rows), env)
