"""Q: can a template merge (recipe 015) be undone by writing the old `template_task` and `task_template` back?

Two tiny sandbox templates on one Shot. A: comp, roto, lay, with roto depending on comp. B: comp and lay
(the same content and step as A's), paint, with lay depending on comp and paint on lay. Every template
task carries its own sort order, description and duration, so a copy of fields would show.

The Shot is created with A, then merged into B the way recipe 015 does it: claim comp and lay (point
their `template_task` at B's), then write `task_template` B. The undo writes the old values back, one
call at a time, and the Tasks, their fields and every TaskDependency are read after each call:

  1. restore in the order Task first, then entity, and delete what B added;
  2. merge again, then restore in the other order, entity first;
  3. merge again, then undo to nulls (the case of an entity that had no template before the merge).

Writes only, in the sandbox, behind --write. Every row is deleted. Wall time and call count are printed.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib  # noqa: E402
import _tasktpl as T  # noqa: E402

t0 = time.monotonic()
env = _lib.load_env()
c = _lib.client()
CALLS = [0]
_request = c.request


def counted(method, path, **kw):
    CALLS[0] += 1
    return _request(method, path, **kw)


c.request = counted

if not _lib.writes_allowed():
    raise SystemExit("probe 096 writes; run with --write")
S = _lib.sandbox_id(c, env)
P = {"type": "Project", "id": S}
ST = T.steps(c)
codes = sorted(ST)
s1, s2, s3 = ({"type": "Step", "id": ST[k]} for k in codes[:3])
rows = []
FIELDS = ["content", "step", "template_task", "sg_status_list", "sg_sort_order", "sg_description",
          "duration", "upstream_tasks", "downstream_tasks"]

A_TASKS = {"comp": {"step": s1, "sg_sort_order": 10, "sg_description": "from A", "duration": 480},
           "roto": {"step": s2, "sg_sort_order": 20, "sg_description": "from A", "duration": 480},
           "lay": {"step": s3, "sg_sort_order": 30, "sg_description": "from A", "duration": 480}}
B_TASKS = {"comp": {"step": s1, "sg_sort_order": 110, "sg_description": "from B", "duration": 960},
           "lay": {"step": s3, "sg_sort_order": 130, "sg_description": "from B", "duration": 960},
           "paint": {"step": s2, "sg_sort_order": 140, "sg_description": "from B", "duration": 960}}
names = {}


def snap(label, shot):
    got = T.tasks_on(c, shot, FIELDS)
    T.adopt(made, got)
    deps = T.deps_among(c, [t["id"] for t in got])
    sh = c.get(f"/entity/shots/{shot['id']}", params={"fields": "task_template"}).json()["data"]
    rows.append(f"  {label}: Shot.task_template={names.get(('tt', (T.rel(sh, 'task_template') or {}).get('id')))}"
                f", {len(got)} Tasks, {len(deps)} deps")
    local = {t["id"]: f"{t['attributes']['content']}#{i}" for i, t in enumerate(got)}
    for t in got:
        a = t["attributes"]
        src = (T.rel(t, "template_task") or {}).get("id")
        rows.append(f"    {local[t['id']]:<8} template_task={names.get(src, src)!s:<8} status={a['sg_status_list']} "
                    f"order={a['sg_sort_order']} desc={a['sg_description']} dur={a['duration']}")
    for d in deps:
        down, up = (T.rel(d, "task") or {}).get("id"), (T.rel(d, "dependent_task") or {}).get("id")
        a = d["attributes"]
        rows.append(f"    dep {d['id']}: {local.get(down, down)} on {local.get(up, up)} "
                    f"{a['dependency_type']} offset_days={a['offset_days']}")
    return got, deps


def by(got, content, tpl_id=None):
    return [t for t in got if t["attributes"]["content"] == content
            and (tpl_id is None or (T.rel(t, "template_task") or {}).get("id") == tpl_id)]


def put(slug, i, body, label):
    r = c.put(f"/entity/{slug}/{i}", json=body)
    rows.append(f"\n  {label} -> {r.status_code} {T.errs(r) if not r.ok else ''}")


def merge(shot, got, look=False):
    """Recipe 015: claim comp and lay for B, then write task_template B."""
    for k in ("comp", "lay"):
        t = by(got, k)[0]
        put("tasks", t["id"], {"template_task": {"type": "Task", "id": idsB[k]}},
            f"claim {k} Task {t['id']} for B")
    if look:
        snap("claimed, before the entity write", shot)
    put("shots", shot["id"], {"task_template": TTB}, "PUT Shot task_template B")


with _lib.Created(c) as made:
    TTA, idsA = T.template(c, made, "zzprobe_096_ttA", A_TASKS, deps=[("roto", "comp", {})])
    TTB, idsB = T.template(c, made, "zzprobe_096_ttB", B_TASKS,
                           deps=[("lay", "comp", {"dependency_type": "start-to-start", "offset_days": 1}),
                                 ("paint", "lay", {})])
    names.update({("tt", TTA["id"]): "A", ("tt", TTB["id"]): "B"})
    names.update({i: f"A.{k}" for k, i in idsA.items()})
    names.update({i: f"B.{k}" for k, i in idsB.items()})

    shot = T.ref(T.post(c, made, "shots", {"project": P, "code": "zzprobe_096_sh", "task_template": TTA}))
    rows.append("=== the Shot, created with A")
    got0, deps0 = snap("S0", shot)
    put("tasks", by(got0, "comp")[0]["id"], {"sg_status_list": "ip", "sg_description": "hand"},
        "PUT comp sg_status_list ip, sg_description hand (work done)")
    put("tasks", by(got0, "lay")[0]["id"], {"sg_sort_order": 99}, "PUT lay sg_sort_order 99 (hand edit)")
    put("tasks", by(got0, "roto")[0]["id"], {"sg_description": "hand", "duration": 1440},
        "PUT roto sg_description hand, duration 1440 (never claimed)")
    got0, deps0 = snap("S0 after the hand edits", shot)

    rows.append("\n=== merge 1 into B (recipe 015)")
    merge(shot, got0, look=True)
    got1, deps1 = snap("merged", shot)

    rows.append("\n=== undo 1: Task first, then entity")
    for k in ("comp", "lay"):
        put("tasks", by(got1, k)[0]["id"], {"template_task": {"type": "Task", "id": idsA[k]}},
            f"PUT {k} template_task A.{k}")
        snap("after", shot)
    put("shots", shot["id"], {"task_template": TTA}, "PUT Shot task_template A")
    got, deps = snap("after", shot)
    old = {d["id"] for d in deps0}
    orig = {t["id"] for t in got0}
    for t in got:
        if t["id"] not in orig:
            r = c.delete(f"/entity/tasks/{t['id']}")
            rows.append(f"\n  DELETE Task {t['attributes']['content']} {t['id']} (added by B) -> {r.status_code}")
    for d in T.deps_among(c, [t["id"] for t in got0]):
        if d["id"] not in old:
            r = c.delete(f"/entity/task_dependencies/{d['id']}")
            rows.append(f"  DELETE TaskDependency {d['id']} (added by B) -> {r.status_code}")
    for t in got0:
        a = t["attributes"]
        put("tasks", t["id"], {k: a[k] for k in ("sg_sort_order", "sg_description", "duration")},
            f"PUT {a['content']} fields back from the snapshot")
    snap("restored", shot)

    rows.append("\n=== merge 2, then undo entity first")
    merge(shot, T.tasks_on(c, shot, FIELDS))
    got2, _ = snap("merged", shot)
    put("shots", shot["id"], {"task_template": TTA}, "PUT Shot task_template A (Tasks still claimed by B)")
    snap("after", shot)
    for k in ("comp", "lay"):
        put("tasks", by(got2, k, idsB[k])[0]["id"], {"template_task": {"type": "Task", "id": idsA[k]}},
            f"PUT {k} template_task A.{k}")
    snap("after", shot)

    rows.append("\n=== merge 3, then undo to nulls")
    put("shots", shot["id"], {"task_template": None}, "PUT Shot task_template null (reset)")
    cur = T.tasks_on(c, shot, FIELDS)
    merge(shot, [t for t in cur if (T.rel(t, "template_task") or {}).get("id") in (idsA["comp"], idsA["lay"])])
    got3, _ = snap("merged", shot)
    for k in ("comp", "lay"):
        put("tasks", by(got3, k, idsB[k])[0]["id"], {"template_task": None}, f"PUT {k} template_task null")
    put("shots", shot["id"], {"task_template": None}, "PUT Shot task_template null")
    snap("after", shot)

rows.append("\n=== left clean?")
rows.append(f"  sandbox Tasks zzprobe_096 Shot: "
            f"{len(T.search(c, 'shots', [['code', 'starts_with', 'zzprobe_096']], ['code']))} Shots, "
            f"{len(T.search(c, 'tasks', [['entity', 'is', shot]], ['content']))} Tasks")
rows.append(f"  templates zzprobe_096*: "
            f"{len(T.search(c, 'task_templates', [['code', 'starts_with', 'zzprobe_096']], ['code']))}")
rows.append(f"\n  wall {time.monotonic() - t0:.1f}s, {CALLS[0]} calls")

_lib.emit("096_task_template_unmerge", "\n".join(rows), env)
