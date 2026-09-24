"""Q: can recipe 015's merge (claim Tasks, clear `task_template`, set it) run as one `_batch`?

Recipe 015 sends the `template_task` claims, the clear and the set as separate calls. Inside one batch:
(a) does a Shot `task_template` write see claims made earlier in the same batch; (b) do `null` then
`T` as two update requests on the same Shot run the apply; (c) claims, `null` and `T` together: which
Tasks, and are the template's edges copied? The split sequence on the same setup is the control.

One template, two tasks, one start-to-start edge. One Shot per variant.
Provisioned by the probe: the template, the Shots and their Tasks, all deleted on exit. No operator step.
Writes only, in the sandbox, behind --write.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib  # noqa: E402
import _tasktpl as T  # noqa: E402

T0 = time.time()
env = _lib.load_env()
c = _lib.client()
CALLS = [0]
_request = c.request


def counted(method, path, **kw):
    CALLS[0] += 1
    return _request(method, path, **kw)


c.request = counted  # get/post/put/delete all go through request

rows = []
if not _lib.writes_allowed():
    raise SystemExit("probe 098 writes; run with --write")
S = _lib.sandbox_id(c, env)
P = {"type": "Project", "id": S}
ST = T.steps(c)
s1, s2 = ({"type": "Step", "id": ST[k]} for k in sorted(ST)[:2])
N = "zzprobe_098_"


def batch(reqs):
    r = c.post("/entity/_batch", json={"requests": reqs})
    return r


def upd(entity, rid, data):
    return {"request_type": "update", "entity": entity, "record_id": rid, "data": data}


def show(label, shot, names):
    got = T.tasks_on(c, shot)
    T.adopt(made, got)
    deps = T.deps_among(c, [t["id"] for t in got])
    for d in deps:
        if ("task_dependencies", d["id"]) not in made.rows:
            made.add("task_dependencies", d["id"])
    sh = c.get(f"/entity/shots/{shot['id']}", params={"fields": "task_template"}).json()["data"]
    rows.append(f"  {label}: {len(got)} Tasks, Shot.task_template="
                f"{(T.rel(sh, 'task_template') or {}).get('name')}")
    short = {}
    for t in got:
        a = t["attributes"]
        src = (T.rel(t, "template_task") or {}).get("id")
        short[t["id"]] = f"{a['content'][len(N):]}#{t['id']}"
        rows.append(f"    {short[t['id']]:<10} step={(T.rel(t, 'step') or {}).get('name')!s:<13} "
                    f"template_task={names.get(src, src)!s:<5} status={a['sg_status_list']}")
    for d in deps:
        rows.append(f"    dep {short.get(T.rel(d, 'task')['id'])} on {short.get(T.rel(d, 'dependent_task')['id'])} "
                    f"{d['attributes']['dependency_type']} offset_days {d['attributes']['offset_days']}")
    if not deps:
        rows.append("    no TaskDependency among them")


def shot(code, tpl=None):
    body = {"project": P, "code": N + code}
    if tpl:
        body["task_template"] = tpl
    return T.ref(T.post(c, made, "shots", body))


def hand(sh, content, step, status=None):
    body = {"project": P, "entity": sh, "content": N + content, "step": step}
    if status:
        body["sg_status_list"] = status
    return T.post(c, made, "tasks", body)["id"]


def drop_generated(sh, content):
    """Delete one generated Task, so a re-run of the apply has something to re-create."""
    got = T.tasks_on(c, sh, fields=["content"])
    t = next(t for t in got if t["attributes"]["content"] == N + content)
    T.adopt(made, [x for x in got if x is not t])
    return c.delete(f"/entity/tasks/{t['id']}").status_code


with _lib.Created(c) as made:
    TT, ids = T.template(c, made, N + "tt", {N + "a": {"step": s1, "sg_sort_order": 10},
                                              N + "b": {"step": s2, "sg_sort_order": 20}},
                         deps=[(N + "b", N + "a", {"dependency_type": "start-to-start", "offset_days": 1})])
    names = {ids[N + "a"]: "tt:a", ids[N + "b"]: "tt:b"}
    Ta, Tb = ({"type": "Task", "id": ids[N + k]} for k in "ab")
    rows.append("template tt: a@step1, b@step2, dep b on a start-to-start offset_days 1")

    rows.append("\n=== (a) bare Shot, hand-made a@step1 (ip) and b@step2; ONE batch: claim a, claim b, set tt")
    A = shot("a")
    ha, hb = hand(A, "a", s1, "ip"), hand(A, "b", s2)
    r = batch([upd("Task", ha, {"template_task": Ta}), upd("Task", hb, {"template_task": Tb}),
               upd("Shot", A["id"], {"task_template": TT})])
    rows.append(f"  batch -> {r.status_code} {T.errs(r) if not r.ok else ''}")
    show("after", A, names)

    rows.append("\n=== (b) Shot created with tt, generated b deleted; ONE batch: task_template null, then tt")
    B = shot("b", TT)
    rows.append(f"  DELETE generated b -> {drop_generated(B, 'b')}")
    r = batch([upd("Shot", B["id"], {"task_template": None}), upd("Shot", B["id"], {"task_template": TT})])
    rows.append(f"  batch -> {r.status_code} {T.errs(r) if not r.ok else ''}")
    if r.ok:
        rows.append(f"  row task_template values: "
                    f"{[(T.rel(x.get('data', x), 'task_template') or {}).get('id') for x in r.json()['data']]}")
    show("after", B, names)

    rows.append("\n=== (c) Shot created with tt, generated b deleted, hand-made b@step2 (ip) added;"
                "\n    ONE batch: claim b, task_template null, tt")
    C = shot("c", TT)
    rows.append(f"  DELETE generated b -> {drop_generated(C, 'b')}")
    hcb = hand(C, "b", s2, "ip")
    r = batch([upd("Task", hcb, {"template_task": Tb}), upd("Shot", C["id"], {"task_template": None}),
               upd("Shot", C["id"], {"task_template": TT})])
    rows.append(f"  batch -> {r.status_code} {T.errs(r) if not r.ok else ''}")
    show("after", C, names)

    rows.append("\n=== control: the (c) setup, recipe 015's split sequence (batch claim, PUT null, PUT tt)")
    D = shot("d", TT)
    rows.append(f"  DELETE generated b -> {drop_generated(D, 'b')}")
    hdb = hand(D, "b", s2, "ip")
    r1 = batch([upd("Task", hdb, {"template_task": Tb})])
    r2 = c.put(f"/entity/shots/{D['id']}", json={"task_template": None})
    r3 = c.put(f"/entity/shots/{D['id']}", json={"task_template": TT})
    rows.append(f"  batch claim -> {r1.status_code}, PUT null -> {r2.status_code}, PUT tt -> {r3.status_code}")
    show("after", D, names)

    rows.append("\n=== control for (b): the (b) setup, PUT null then PUT tt as two calls")
    E = shot("e", TT)
    rows.append(f"  DELETE generated b -> {drop_generated(E, 'b')}")
    r2 = c.put(f"/entity/shots/{E['id']}", json={"task_template": None})
    r3 = c.put(f"/entity/shots/{E['id']}", json={"task_template": TT})
    rows.append(f"  PUT null -> {r2.status_code}, PUT tt -> {r3.status_code}")
    show("after", E, names)

rows.append("\n=== left clean?")
rows.append(f"  Shots {N}*: {len(T.search(c, 'shots', [['project', 'is', P], ['code', 'starts_with', N]], ['code']))}")
rows.append(f"  Tasks {N}*: "
            f"{len(T.search(c, 'tasks', [['project', 'is', P], ['content', 'starts_with', N]], ['content']))}")
rows.append(f"  templates {N}*: {len(T.search(c, 'task_templates', [['code', 'starts_with', N]], ['code']))}")
rows.append(f"\nwall {time.time() - T0:.1f}s, {CALLS[0]} calls")

_lib.emit("098_template_merge_in_one_batch", "\n".join(rows), env)
