"""Q: what does deleting a Task in the middle of a dependency chain do to its dependencies, its neighbours'
dates, and the Version and PublishedFile that point at it, and does revive put them back?

A template sync app that removes Tasks a template no longer lists deletes work that other rows link
to. Probe 060 found a deleted link target reads as null; this measures the Task case end to end.

Writes only, in the sandbox, behind --write. Every row is deleted.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib  # noqa: E402
import _tasktpl as T  # noqa: E402

env = _lib.load_env()
c = _lib.client()
rows = []
if not _lib.writes_allowed():
    raise SystemExit("probe 089 writes; run with --write")
S = _lib.sandbox_id(c, env)
P = {"type": "Project", "id": S}


def get(slug, i, fields):
    r = c.get(f"/entity/{slug}/{i}", params={"fields": fields})
    return r, (r.json()["data"] if r.ok else None)


with _lib.Created(c) as made:
    sh = T.ref(T.post(c, made, "shots", {"project": P, "code": "zzprobe_089_shot"}))
    ids = {n: T.post(c, made, "tasks", {"project": P, "entity": sh, "content": f"zzprobe_089_{n}",
                                        "start_date": "2026-03-02", "due_date": "2026-03-03"})["id"]
           for n in ("a", "b", "c")}
    deps = [T.post(c, made, "task_dependencies",
                   {"task": {"type": "Task", "id": ids[d]}, "dependent_task": {"type": "Task", "id": ids[u]}})["id"]
            for d, u in (("b", "a"), ("c", "b"))]
    B = {"type": "Task", "id": ids["b"]}
    ver = T.post(c, made, "versions", {"project": P, "code": "zzprobe_089_v001", "entity": sh, "sg_task": B})["id"]
    pf = T.post(c, made, "published_files", {"project": P, "code": "zzprobe_089.v001.exr", "entity": sh,
                                             "task": B, "version": {"type": "Version", "id": ver}})["id"]

    def state(label):
        rows.append(f"  {label}")
        for n, i in ids.items():
            r, d = get("tasks", i, "start_date,due_date,upstream_tasks,downstream_tasks,pinned,dependency_violation")
            if d is None:
                rows.append(f"    task {n}: {r.status_code}")
                continue
            a = d["attributes"]
            rows.append(f"    task {n}: {a['start_date']}..{a['due_date']} "
                        f"up={[x['id'] for x in T.rel(d, 'upstream_tasks')]} "
                        f"down={[x['id'] for x in T.rel(d, 'downstream_tasks')]} violation={a['dependency_violation']}")
        for i in deps:
            r, d = get("task_dependencies", i, "task,dependent_task,dependency_type")
            rows.append(f"    dependency {i}: {r.status_code}")
        r, d = get("versions", ver, "sg_task,entity")
        rows.append(f"    Version: {r.status_code} sg_task={json.dumps(T.rel(d, 'sg_task')) if d else '-'}")
        r, d = get("published_files", pf, "task,version,entity")
        rows.append(f"    PublishedFile: {r.status_code} task={json.dumps(T.rel(d, 'task')) if d else '-'}")
        found = T.search(c, "published_files", [["task", "is", B]], ["code"])
        rows.append(f"    PublishedFile _search task is B: {len(found)}")

    rows.append(f"=== a={ids['a']} -FS-> b={ids['b']} -FS-> c={ids['c']}; Version and PublishedFile on b")
    state("before")

    r = c.delete(f"/entity/tasks/{ids['b']}")
    rows.append(f"\n=== DELETE task b -> {r.status_code} {r.text[:200]}")
    state("after")
    r = c.post("/entity/task_dependencies/_search", headers=T.ARR,
               json={"filters": [["id", "in", deps]], "fields": ["task", "dependent_task"],
                     "options": {"return_only": "retired"}})
    rows.append(f"    dependencies under return_only=retired: "
                f"{[x['id'] for x in r.json()['data']] if r.ok else T.errs(r)}")
    r = c.put(f"/entity/tasks/{ids['a']}", json={"due_date": "2026-03-10"})
    rows.append(f"  PUT a due_date 2026-03-10 -> {r.status_code}")
    state("after a moves: does c still follow?")

    r = c.post(f"/entity/tasks/{ids['b']}", params={"revive": 1})
    rows.append(f"\n=== POST /entity/tasks/b?revive=1 -> {r.status_code} {json.dumps(r.json().get('meta'))}")
    state("after revive")

rows.append("\n=== left clean?")
rows.append(f"  sandbox Tasks zzprobe_089*: "
            f"{len(T.search(c, 'tasks', [['project', 'is', P], ['content', 'starts_with', 'zzprobe_089']], ['content']))}")

_lib.emit("089_task_delete_side_effects", "\n".join(rows), env)
