"""Q: what does a template apply do when a claimed pair already holds an edge the template's edge conflicts with?

Recipe 015 claims existing Tasks and the server copies the template's TaskDependency rows onto them
(probes 015, 092). Probe 085 found a direct create rejects a second edge for a pair and a two-Task
loop with 400. Here the conflicting edge already exists when the apply copies the template's:

  (a) the pair holds an edge in the same direction, of another dependency_type
  (b) the pair holds the reverse edge, so the template's edge would close a two-Task loop

Template: a, b, c; one edge b on a, finish-to-start-next-day. Each case gets its own Shot holding
hand-made a and b (claimed), x (not in the template, edge x on a as a control) and no c, so whether the apply still generates c shows whether a
rejected edge rolls the apply back.

Preconditions: none from an operator. The probe provisions every row it reads (a template, 2 Shots,
6 Tasks, 4 edges) and `_lib.Created` deletes them, generated rows included, failure included.

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
    raise SystemExit("probe 101 writes; run with --write")
S = _lib.sandbox_id(c, env)
P = {"type": "Project", "id": S}
PX = "zzprobe_101_"


def tref(i):
    return {"type": "Task", "id": i}


def say(label, r):
    rows.append(f"  {label} -> {r.status_code} {T.errs(r) if not r.ok else ''}".rstrip())


with _lib.Created(c) as made:
    TT, tids = T.template(c, made, PX + "tt", {PX + "a": {}, PX + "b": {}, PX + "c": {}},
                          [(PX + "b", PX + "a", {"dependency_type": "finish-to-start-next-day"})])
    rows.append("template: a, b, c; edge b on a finish-to-start-next-day")
    seen_edges = set()

    for case, (down, up, dtype) in {"a": ("b", "a", "start-to-start"),
                                    "b": ("a", "b", "finish-to-start-next-day")}.items():
        rows.append(f"\n=== ({case}) Shot holds a, b and edge {down} on {up} {dtype}")
        sh = T.ref(T.post(c, made, "shots", {"project": P, "code": f"{PX}shot_{case}"}))
        mine = {n: T.post(c, made, "tasks", {"project": P, "entity": sh, "content": PX + n})["id"]
                for n in ("a", "b", "x")}
        name = {v: k for k, v in mine.items()}
        e = T.post(c, made, "task_dependencies", {"task": tref(mine[down]), "dependent_task": tref(mine[up]),
                                                   "dependency_type": dtype})
        # control: x is not in the template; its edge on a is not in conflict with anything
        x = T.post(c, made, "task_dependencies", {"task": tref(mine["x"]), "dependent_task": tref(mine["a"])})
        seen_edges |= {e["id"], x["id"]}
        rows.append(f"  plus hand-made x (unclaimed), edge x on a (control)")

        def edges_now(label):
            got = T.deps_among(c, list(mine.values()))
            rows.append(f"  edges {label}: " + ", ".join(
                f"{'pre' if g['id'] == e['id'] else 'ctl' if g['id'] == x['id'] else 'new'} "
                f"{name.get(T.rel(g, 'task')['id'])} on {name.get(T.rel(g, 'dependent_task')['id'])} "
                f"{g['attributes']['dependency_type']}" for g in got))

        claim = [{"request_type": "update", "entity": "Task", "record_id": mine[n],
                  "data": {"template_task": tref(tids[PX + n])}} for n in ("a", "b")]
        say("_batch claim template_task on a, b", c.post("/entity/_batch", json={"requests": claim}))
        edges_now("after claim")
        for v in (None, TT):
            r = c.put(f"/entity/shots/{sh['id']}", json={"task_template": v})
            say(f"PUT Shot task_template={v and 'tt'}", r)
            if v and r.ok:
                rel = T.rel(r.json()["data"], "task_template")
                rows.append(f"    response data.relationships.task_template = {rel and 'tt'}")
            edges_now(f"after PUT {v and 'tt'}")
        for label, eid in (("pre", e["id"]), ("ctl", x["id"])):
            live = c.get(f"/entity/task_dependencies/{eid}").status_code
            ret = c.get(f"/entity/task_dependencies/{eid}", params={"options[return_only]": "retired"}).status_code
            rows.append(f"  {label} edge: GET -> {live}, GET options[return_only]=retired -> {ret}")
        if case == "a":   # does a TaskDependency the caller DELETEs read back under retired?
            d = c.delete(f"/entity/task_dependencies/{x['id']}").status_code
            ret = c.get(f"/entity/task_dependencies/{x['id']}", params={"options[return_only]": "retired"}).status_code
            rows.append(f"  ctl edge DELETE -> {d}, then GET options[return_only]=retired -> {ret}")
        on = T.tasks_on(c, sh, ["content", "template_task"])
        T.adopt(made, on)
        name.update({t["id"]: t["attributes"]["content"].removeprefix(PX) for t in on})
        rows.append(f"  Tasks on the Shot: {len(on)} "
                    f"{[(name[t['id']], 'made' if t['id'] in mine.values() else 'generated') for t in on]}")
        cur = c.get(f"/entity/shots/{sh['id']}", params={"fields": "task_template"}).json()["data"]
        rows.append(f"  Shot.task_template read back = {'tt' if T.rel(cur, 'task_template') else None}")
        edges = T.deps_among(c, [t["id"] for t in on])
        for ed in edges:
            if ed["id"] not in seen_edges:
                made.add("task_dependencies", ed["id"])
                seen_edges.add(ed["id"])
            a = ed["attributes"]
            rows.append(f"  TaskDependency {'pre' if ed['id'] == e['id'] else 'ctl' if ed['id'] == x['id'] else 'new'}: "
                        f"{name.get(T.rel(ed, 'task')['id'])} on {name.get(T.rel(ed, 'dependent_task')['id'])} "
                        f"{a['dependency_type']} offset_days={a['offset_days']}")
        ups = T.search(c, "tasks", [["id", "in", list(mine.values())]], ["upstream_tasks"])
        rows.append("  upstream_tasks: " + ", ".join(
            f"{name[t['id']]}={[name.get(u['id'], u['id']) for u in (T.rel(t, 'upstream_tasks') or [])]}"
            for t in ups))

rows.append("\n=== left clean?")
for slug, f, flt in (("tasks", "content", [["content", "starts_with", PX]]),
                     ("shots", "code", [["project", "is", P], ["code", "starts_with", PX]]),
                     ("task_templates", "code", [["code", "starts_with", PX]])):
    rows.append(f"  {slug} {PX}*: {len(T.search(c, slug, flt, [f]))}")
rows.append(f"\n  wall {time.monotonic() - T0:.1f} s, {CALLS[0]} calls (token fetch not counted)")

_lib.emit("101_template_edge_conflict", "\n".join(rows), env)
