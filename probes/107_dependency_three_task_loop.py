"""Q: is a three-Task dependency loop (a -> b -> c -> a) refused, on a direct create, inside `_batch`,
and when a template apply's edge would close it?

Probe 085 found a direct TaskDependency create that closes a two-Task loop is a 400; probe 101 found a
template apply replaces a reverse edge on a claimed pair with the template's. Three cases here:

  (1) direct: q on p, r on q, then p on r, each its own POST
  (2) batch: one `_batch` creating t on s, u on t, s on u (the loop closes on rows the same batch made);
      control: a `_batch` of the first two only
  (3) apply: template a, b with edge b on a. A Shot holds hand-made a, b (claimed) and x (not in the
      template) with edges x on b and a on x, so the template's b on a closes b -> a -> x -> b.
      Control Shot: the same, without x on b, so no loop can form: does the apply keep a on x there?

Preconditions: none from an operator. The probe provisions every row it reads (a template, 3 Shots,
12 Tasks and their edges) and `_lib.Created` deletes them, failure included.

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
    raise SystemExit("probe 107 writes; run with --write")
S = _lib.sandbox_id(c, env)
P = {"type": "Project", "id": S}
PX = "zzprobe_107_"


def tref(i):
    return {"type": "Task", "id": i}


def dep(down, up):
    return {"task": tref(down), "dependent_task": tref(up)}


def say(label, r):
    rows.append(f"  {label} -> {r.status_code} {T.errs(r) if not r.ok else ''}".rstrip())


with _lib.Created(c) as made:
    name = {}
    edge_ids = set()

    def shot_with(tag, names):
        sh = T.ref(T.post(c, made, "shots", {"project": P, "code": PX + tag}))
        ids = {n: T.post(c, made, "tasks", {"project": P, "entity": sh, "content": PX + n})["id"]
               for n in names}
        name.update({v: k for k, v in ids.items()})
        return sh, ids

    def edges(label, ids):
        got = T.deps_among(c, list(ids))
        for g in got:
            if g["id"] not in edge_ids:
                edge_ids.add(g["id"])
                made.add("task_dependencies", g["id"])
        rows.append(f"  edges {label}: " + (", ".join(sorted(
            f"{name.get(T.rel(g, 'task')['id'])} on {name.get(T.rel(g, 'dependent_task')['id'])}"
            f" #{g['id'] % 1000:03d}" for g in got)) or "none"))
        return got

    # (1) direct creates
    rows.append("=== (1) direct: q on p, r on q, then p on r")
    _, d = shot_with("direct", ("p", "q", "r"))
    for down, up in (("q", "p"), ("r", "q"), ("p", "r")):
        r = c.post("/entity/task_dependencies", json=dep(d[down], d[up]))
        say(f"POST {down} on {up}", r)
        if r.ok:
            edge_ids.add(r.json()["data"]["id"])
            made.add("task_dependencies", r.json()["data"]["id"])
    edges("read back", d.values())

    # (2) one batch closes the loop on its own rows
    rows.append("\n=== (2) _batch: t on s, u on t, s on u in one batch")
    _, b = shot_with("batch", ("s", "t", "u"))

    def batch(pairs):
        return c.post("/entity/_batch", json={"requests": [
            {"request_type": "create", "entity": "TaskDependency", "data": dep(b[x], b[y])} for x, y in pairs]})

    r = batch((("t", "s"), ("u", "t"), ("s", "u")))
    say("_batch of 3", r)
    edges("after", b.values())
    r = batch((("t", "s"), ("u", "t")))
    say("control _batch of t on s, u on t", r)
    edges("after control", b.values())
    r = c.post("/entity/task_dependencies", json=dep(b["s"], b["u"]))
    say("then POST s on u", r)
    if r.ok:
        made.add("task_dependencies", r.json()["data"]["id"])

    # (3) template apply closes the loop
    TT, tids = T.template(c, made, PX + "tt", {PX + "a": {}, PX + "b": {}},
                          [(PX + "b", PX + "a", {"dependency_type": "finish-to-start-next-day"})])
    rows.append("\n=== (3) apply; template a, b, edge b on a")
    for case, pre in (("loop", (("x", "b"), ("a", "x"))), ("control", (("a", "x"),))):
        rows.append(f"--- Shot {case}: hand-made a, b, x; edges " + ", ".join(f"{x} on {y}" for x, y in pre))
        sh, m = shot_with("apply_" + case, ("a", "b", "x"))
        pre_ids = {}
        for x, y in pre:
            e = T.post(c, made, "task_dependencies", dep(m[x], m[y]))
            edge_ids.add(e["id"])
            pre_ids[f"{x} on {y}"] = e["id"]
        edges("before", m.values())
        claim = [{"request_type": "update", "entity": "Task", "record_id": m[n],
                  "data": {"template_task": tref(tids[PX + n])}} for n in ("a", "b")]
        say("_batch claim template_task on a, b", c.post("/entity/_batch", json={"requests": claim}))
        edges("after claim", m.values())
        for v in (None, TT):
            r = c.put(f"/entity/shots/{sh['id']}", json={"task_template": v})
            say(f"PUT Shot task_template={v and 'tt'}", r)
            edges(f"after PUT {v and 'tt'}", m.values())
        for label, eid in pre_ids.items():
            live = c.get(f"/entity/task_dependencies/{eid}").status_code
            ret = c.get(f"/entity/task_dependencies/{eid}", params={"options[return_only]": "retired"}).status_code
            rows.append(f"  pre {label} #{eid % 1000:03d}: GET -> {live}, retired -> {ret}")
        on = T.tasks_on(c, sh, ["content", "template_task", "upstream_tasks"])
        T.adopt(made, on)
        cur = c.get(f"/entity/shots/{sh['id']}", params={"fields": "task_template"}).json()["data"]
        rows.append(f"  Tasks on the Shot: {len(on)}; Shot.task_template = "
                    f"{'tt' if T.rel(cur, 'task_template') else None}; upstream_tasks: " + ", ".join(
                        f"{name.get(t['id'], t['id'])}={[name.get(u['id'], u['id']) for u in (T.rel(t, 'upstream_tasks') or [])]}"
                        for t in on))

rows.append("\n=== left clean?")
for slug, f, flt in (("tasks", "content", [["content", "starts_with", PX]]),
                     ("shots", "code", [["project", "is", P], ["code", "starts_with", PX]]),
                     ("task_templates", "code", [["code", "starts_with", PX]]),
                     ("task_dependencies", "task", [["id", "in", sorted(edge_ids)]])):
    rows.append(f"  {slug}: {len(T.search(c, slug, flt, [f]))}")
rows.append(f"\n  wall {time.monotonic() - T0:.1f} s, {CALLS[0]} calls (token fetch not counted)")

_lib.emit("107_dependency_three_task_loop", "\n".join(rows), env)
