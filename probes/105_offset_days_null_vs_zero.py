"""Q: TaskDependency `offset_days` null vs 0. What does a create with null, with 0, and with the key
omitted read back as? And on a template re-apply (probe 102), does an entity edge whose offset is null
match a template edge whose offset is 0 (and the reverse), so the edge is kept with its id, or is it
treated as differing, deleted and re-created with a new id?

One template T, five tasks a..e, four edges all finish-to-start-next-day, created with:
  b on a  offset_days 0          c on a  offset_days null
  d on a  key omitted            e on a  offset_days 0
The template edges are the create read-back (three bodies, one read each, plus a GET).

One Shot created with T copies them. Then, each entity edge PUT, read back after each step:
  b1 on a1  PUT offset_days null    (template 0, entity null)
  c1 on a1  PUT offset_days 0       (template null, entity 0)
  d1 on a1  untouched               positive control: same as the template, expect kept
  e1 on a1  PUT offset_days 2       negative control: differs, expect re-created (probe 102)
then PUT Shot task_template null, then T (recipe 015's clear-then-set), edges read after each.

Preconditions: none from an operator. The probe provisions every row it reads (1 template, 5 template
tasks, 1 Shot and its 5 generated Tasks, the edges) and `_lib.Created` deletes them, failure included.

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
    raise SystemExit("probe 105 writes; run with --write")
S = _lib.sandbox_id(c, env)
P = {"type": "Project", "id": S}
PX = "zzprobe_105_"
ST = T.steps(c)
step = {"type": "Step", "id": ST[sorted(ST)[0]]}
DT = "finish-to-start-next-day"
all_task_ids = []


def tref(i):
    return {"type": "Task", "id": i}


with _lib.Created(c) as made:
    tt = T.post(c, made, "task_templates", {"code": PX + "T", "entity_type": "Shot"})
    TT = T.ref(tt)
    tids = {n: T.post(c, made, "tasks", {"content": n, "task_template": TT, "step": step})["id"]
            for n in "abcde"}
    all_task_ids += tids.values()

    rows.append("=== create read-back (template edges, all on a)")
    bodies = {"b": {"offset_days": 0}, "c": {"offset_days": None}, "d": {}, "e": {"offset_days": 0}}
    for n, extra in bodies.items():
        body = {"task": tref(tids[n]), "dependent_task": tref(tids["a"]), "dependency_type": DT, **extra}
        r = c.post("/entity/task_dependencies", json=body)
        if not r.ok:
            raise SystemExit(f"POST dep {n} {r.status_code} {T.errs(r)}")
        d = r.json()["data"]
        made.add("task_dependencies", d["id"])
        g = c.get(f"/entity/task_dependencies/{d['id']}", params={"fields": "offset_days,dependency_type"})
        sent = repr(extra["offset_days"]) if extra else "omitted"
        rows.append(f"  {n} on a  sent offset_days={sent:<8} POST {r.status_code} response offset_days="
                    f"{d['attributes'].get('offset_days', '<absent>')!r:<6} "
                    f"GET offset_days={g.json()['data']['attributes']['offset_days']!r}")
    # filter view of the same: which of them does `offset_days is 0` / `is null` match?
    tname = {v: k for k, v in tids.items()}
    for op, val in (("is", 0), ("is", None)):
        hit = T.search(c, "task_dependencies", [["task", "in", [tref(i) for i in tids.values()]],
                                                ["offset_days", op, val]], ["task"])
        rows.append(f"  _search offset_days {op} {val!r}: "
                    f"{sorted(tname[T.rel(h, 'task')['id']] for h in hit)}")

    sh = T.ref(T.post(c, made, "shots", {"project": P, "code": PX + "sh"}))
    r = c.put(f"/entity/shots/{sh['id']}", json={"task_template": TT})
    rows.append(f"\n=== Shot, PUT task_template T -> {r.status_code}")
    on = T.tasks_on(c, sh, ["content", "template_task"])
    T.adopt(made, on)
    k = {t["attributes"]["content"]: t["id"] for t in on}
    name = {v: k2 + "1" for k2, v in k.items()}
    all_task_ids += k.values()
    seen = set()
    ids0 = {}

    def edges(label):
        got = T.deps_among(c, list(k.values()))
        out = {}
        for g in got:
            if g["id"] not in seen:
                made.add("task_dependencies", g["id"])
                seen.add(g["id"])
            n = name[T.rel(g, "task")["id"]]
            out[n] = g
        parts = []
        for n in sorted(out):
            g = out[n]
            a = g["attributes"]
            tag = "" if not ids0 else ("same id" if ids0.get(n) == g["id"] else "NEW id")
            parts.append(f"{n}#{g['id'] % 10000} {a['dependency_type'][:6]} off={a['offset_days']!r} {tag}")
        rows.append(f"  {label:<22} " + " | ".join(parts))
        return out

    first = edges("copied")
    for n, g in first.items():
        ids0[n] = g["id"]
    for n, v in (("b1", None), ("c1", 0), ("e1", 2)):
        r = c.put(f"/entity/task_dependencies/{first[n]['id']}", json={"offset_days": v})
        rows.append(f"  PUT {n} offset_days={v!r} -> {r.status_code} {'' if r.ok else T.errs(r)}")
    edges("after edge PUTs")
    for v in (None, TT):
        r = c.put(f"/entity/shots/{sh['id']}", json={"task_template": v})
        rows.append(f"  PUT Shot task_template={v and 'T'} -> {r.status_code} {'' if r.ok else T.errs(r)}")
        edges(f"after task_template={v and 'T'}")
    for n in ("b1", "c1", "d1", "e1"):
        live = c.get(f"/entity/task_dependencies/{ids0[n]}").status_code
        rows.append(f"  first {n} edge id GET -> {live}")

rows.append("\n=== left clean?")
for slug, f, flt in (("tasks", "content", [["id", "in", all_task_ids]]),
                     ("task_dependencies", "task", [["task", "in", [tref(i) for i in all_task_ids]]]),
                     ("shots", "code", [["project", "is", P], ["code", "starts_with", PX]]),
                     ("task_templates", "code", [["code", "starts_with", PX]])):
    rows.append(f"  {slug}: {len(T.search(c, slug, flt, [f]))}")
rows.append(f"\n  wall {time.monotonic() - T0:.1f} s, {CALLS[0]} calls (token fetch not counted)")

_lib.emit("105_offset_days_null_vs_zero", "\n".join(rows), env)
