"""Q: is a `_batch` atomic when a later request fails after a `task_template` write in the same batch?

Field report (issue #89): a recipe 020 merge answered 400 on `TaskDependency.dependent_task`, a
re-created edge pointing at a Task deleted out of band, yet the event log showed the Shot moved to
the template and Tasks created. Recipe 002 measured rollback only for plain creates and updates.

Template tt holds a, b, c with edges b on a, c on b. r is a Task the probe creates and DELETEs, so it
is retired. One fresh Shot per case, holding a hand-made a with `sg_description` "before":

  a_late     [claim a, Shot null, Shot tt, a desc "after", create edge a on r]   failure last
  b_first    [create edge a on r, claim a, Shot null, Shot tt, a desc "after"]   failure first
  c_plain    [Shot description "after", create edge a on r]                       control, no template
  d_status   [claim a, Shot null, Shot tt, a sg_status_list "not_a_status"]      recipe 002's failure
  e_ok       [claim a, Shot null, Shot tt, a desc "after"]                        control, no failure

Read back after each batch and again after a 2 s settle: the Shot's `task_template` and description,
the Tasks on the Shot, a's claim and description, edges among them, and the EventLogEntry rows this
ApiUser wrote since the batch that name the probe's prefix, with a GET (live and retired) of every Task id they name.

Preconditions: `generate_event_log_entries` on this ApiUser is read, never changed; with it off the
event-log half is skipped and said so. Everything else is provisioned by the probe and deleted by
`_lib.Created`, failure included. Writes only, in the sandbox, behind --write. Budget 60 s.
"""
import json
import sys
import time
from collections import Counter
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
    raise SystemExit("probe 113 writes; run with --write")
S = _lib.sandbox_id(c, env)
P = {"type": "Project", "id": S}
PX = "zzprobe_113_"
EF = ["event_type", "attribute_name", "entity", "meta", "created_at"]

me = T.search(c, "api_users", [["firstname", "is", env["FPT_API_SCRIPT_NAME"]]], ["generate_event_log_entries"])
ME = {"type": "ApiUser", "id": me[0]["id"]} if me else None
LOG = bool(me) and me[0]["attributes"]["generate_event_log_entries"] is True
rows.append(f"ApiUser generate_event_log_entries: {LOG} (read, not changed)")


def tref(i):
    return {"type": "Task", "id": i}


def last_event_id():
    r = c.post("/entity/event_log_entries/_search", headers=T.ARR,
               json={"filters": [["user", "is", ME]], "fields": ["id"], "sort": "-id", "page": {"size": 1}})
    if not r.ok:
        raise SystemExit(f"event log {r.status_code} {T.errs(r)}")
    d = r.json()["data"]
    return d[0]["id"] if d else 0


def events_since(eid):
    return sorted(T.search(c, "event_log_entries", [["user", "is", ME], ["id", "greater_than", eid]], EF),
                  key=lambda e: e["id"])


with _lib.Created(c) as made:
    name = {}
    edge_ids = set()
    TT, tids = T.template(c, made, PX + "tt", {PX + "a": {}, PX + "b": {}, PX + "c": {}},
                          [(PX + "b", PX + "a", {}), (PX + "c", PX + "b", {})])
    tpl_edges = T.deps_among(c, list(tids.values()))
    rows.append(f"template tt: a, b, c; edges b on a, c on b ({len(tpl_edges)} read back)")

    home = T.ref(T.post(c, made, "shots", {"project": P, "code": PX + "home"}))
    rid = c.post("/entity/tasks", json={"project": P, "entity": home, "content": PX + "r"}).json()["data"]["id"]
    d = c.delete(f"/entity/tasks/{rid}").status_code
    ret = c.get(f"/entity/tasks/{rid}", params={"options[return_only]": "retired"}).status_code
    rows.append(f"r #{rid}: POST, DELETE -> {d}; GET -> {c.get(f'/entity/tasks/{rid}').status_code}, retired -> {ret}")

    # The failing request on its own, so its error is known before it sits inside a batch.
    probe_task = T.post(c, made, "tasks", {"project": P, "entity": home, "content": PX + "p"})["id"]
    r = c.post("/entity/task_dependencies", json={"task": tref(probe_task), "dependent_task": tref(rid)})
    rows.append(f"single POST edge p on r -> {r.status_code} {'' if r.ok else T.errs(r)}")
    if r.ok:
        made.add("task_dependencies", r.json()["data"]["id"])

    def bad_edge(a):
        return {"request_type": "create", "entity": "TaskDependency",
                "data": {"task": tref(a), "dependent_task": tref(rid)}}

    def claim(a):
        return {"request_type": "update", "entity": "Task", "record_id": a,
                "data": {"template_task": tref(tids[PX + "a"])}}

    def shot_tt(sh, v):
        return {"request_type": "update", "entity": "Shot", "record_id": sh["id"], "data": {"task_template": v}}

    def a_upd(a, data):
        return {"request_type": "update", "entity": "Task", "record_id": a, "data": data}

    CASES = {
        "a_late": lambda sh, a: [claim(a), shot_tt(sh, None), shot_tt(sh, TT),
                                 a_upd(a, {"sg_description": "after"}), bad_edge(a)],
        "b_first": lambda sh, a: [bad_edge(a), claim(a), shot_tt(sh, None), shot_tt(sh, TT),
                                  a_upd(a, {"sg_description": "after"})],
        "c_plain": lambda sh, a: [{"request_type": "update", "entity": "Shot", "record_id": sh["id"],
                                   "data": {"description": "after"}}, bad_edge(a)],
        "d_status": lambda sh, a: [claim(a), shot_tt(sh, None), shot_tt(sh, TT),
                                   a_upd(a, {"sg_status_list": "not_a_status"})],
        "e_ok": lambda sh, a: [claim(a), shot_tt(sh, None), shot_tt(sh, TT),
                               a_upd(a, {"sg_description": "after"})],
    }

    def state(label, sh, a):
        s = c.get(f"/entity/shots/{sh['id']}", params={"fields": "task_template,description"}).json()["data"]
        on = T.tasks_on(c, sh, ["content", "template_task", "sg_description", "sg_status_list"])
        T.adopt(made, on)
        for t in on:
            name.setdefault(t["id"], t["attributes"]["content"].replace(PX, ""))
        es = T.deps_among(c, [t["id"] for t in on])
        for e in es:
            if e["id"] not in edge_ids:
                edge_ids.add(e["id"])
                made.add("task_dependencies", e["id"])
        ha = next(t for t in on if t["id"] == a)
        rows.append(f"  {label}: Shot task_template={(T.rel(s, 'task_template') or {}).get('id')}"
                    f" description={s['attributes']['description']!r}; {len(on)} Tasks "
                    f"[{', '.join(name[t['id']] for t in on)}]; a template_task="
                    f"{(T.rel(ha, 'template_task') or {}).get('id')} desc={ha['attributes']['sg_description']!r}"
                    f" status={ha['attributes']['sg_status_list']}; edges: " + (", ".join(sorted(
                        f"{name.get(T.rel(e, 'task')['id'])} on {name.get(T.rel(e, 'dependent_task')['id'])}"
                        for e in es)) or "none"))
        return on

    rows.append(f"tt a={tids[PX + 'a']}")
    for tag, build in CASES.items():
        sh = T.ref(T.post(c, made, "shots", {"project": P, "code": PX + tag, "description": "before"}))
        a = T.post(c, made, "tasks", {"project": P, "entity": sh, "content": PX + "a",
                                      "sg_description": "before"})["id"]
        name[a] = "a"
        reqs = build(sh, a)
        rows.append(f"\n=== {tag}: " + ", ".join(
            f"{q['request_type']} {q['entity']} {list(q['data'])[0]}={q['data'][list(q['data'])[0]]!s:.20}"
            for q in reqs))
        state("before", sh, a)
        e0 = last_event_id() if LOG else 0
        t = time.monotonic()
        r = c.post("/entity/_batch", json={"requests": reqs})
        rows.append(f"  _batch ({len(reqs)} requests) -> {r.status_code} in {time.monotonic() - t:.1f} s "
                    f"{'' if r.ok else T.errs(r)}")
        state("after", sh, a)
        time.sleep(2)
        on = state("after 2 s", sh, a)
        if LOG:
            allev = events_since(e0)
            # The script key is shared: other writers' rows land in this window. Keep a row only when
            # it names this probe's prefix: its entity, or a meta old/new value (Task content, links).
            evs = [ev for ev in allev if PX in json.dumps(ev)]
            n = Counter()
            named = set()
            for ev in evs:
                at = ev["attributes"]
                ent = T.rel(ev, "entity") or {}
                meta = at["meta"] or {}
                et = ent.get("type") or meta.get("entity_type")
                i = ent.get("id") or meta.get("entity_id")
                n[(at["event_type"], at["attribute_name"])] += 1
                if et == "Task":
                    named.add(i)
            rows.append(f"  event log since the batch: {len(allev)} rows by this ApiUser, {len(evs)} naming {PX}*: " + "; ".join(
                f"{k[0].replace('Shotgun_', '')}{'.' + k[1] if k[1] else ''} x{v}" for k, v in sorted(n.items(), key=str)))
            live = {t["id"] for t in on}
            gone = sorted(named - live)
            for i in gone:
                g = c.get(f"/entity/tasks/{i}").status_code
                gr = c.get(f"/entity/tasks/{i}", params={"options[return_only]": "retired"}).status_code
                rows.append(f"    Task #{i} named in the log, not on the Shot: GET {g}, retired {gr}")

rows.append("\n=== left clean?")
for slug, f, flt in (("tasks", "content", [["content", "starts_with", PX]]),
                     ("shots", "code", [["project", "is", P], ["code", "starts_with", PX]]),
                     ("task_templates", "code", [["code", "starts_with", PX]]),
                     ("task_dependencies", "task", [["id", "in", sorted(edge_ids) or [0]]])):
    rows.append(f"  {slug}: {len(T.search(c, slug, flt, [f]))}")
rows.append(f"\n  wall {time.monotonic() - T0:.1f} s, {CALLS[0]} calls (token fetch not counted)")

_lib.emit("113_batch_atomic_after_template_write", "\n".join(rows), env)
