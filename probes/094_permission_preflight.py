"""Q: how does a person learn, before writing anything, whether they may update Tasks, update Shots,
create Tasks and delete Tasks, and which way of asking leaves no row, no event and no updated_at change?

Permission rules are not readable (probe 027), so the answer has to come from the API's own refusals.
Each candidate is sent twice, by the script (allowed everything) and as a lower-level person (refused),
and after each one the probe reads the Task and Shot back: updated_at, content, the Shot's tasks, and
every EventLogEntry on either row.

Candidates: the per-user `editable` flag in /schema; a no-op PUT (a field's current value written back);
an empty PUT; a create with an invalid value; a create with an unknown field; a DELETE of an id that
does not exist; and a _batch whose first request is the real one and whose second fails, so the batch
rolls back (recipe 002).

The refused caller is the script acting as that person through `sudo_as_login` (probe 027): the person's
permission set applies. A launcher session (probe 052) as a lower-level person needs that person at a
browser, so it is not what this probe measures.

Writes only, in the sandbox, behind --write: one Shot and one Task shared by the update and delete
candidates, and one parent Shot per create candidate and caller (4), all deleted on exit.
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib  # noqa: E402
from sg_groundtruth.client import FPT  # noqa: E402

ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
ADMIN_SETS = {"Admin", "API Admin"}

# Site state the API cannot set (probe 027: can_impersonate_this_user is not editable over REST).
requires = [
    "an active HumanUser whose permission set is not Admin, with can_impersonate_this_user on "
    "(web UI: People > the person > 'Can impersonate this user'), and a member of the sandbox project "
    "(web UI: Project > People). Detected by a HumanUser _search.",
]

T0 = time.perf_counter()
CALLS = [0]


def counted(cl):
    """Count every REST call a client makes, token requests excepted. _lib stays untouched (#76)."""
    inner = cl.request

    def request(method, path, **kw):
        CALLS[0] += 1
        return inner(method, path, **kw)
    cl.request = request
    return cl


env = _lib.load_env()
c = counted(_lib.client())
if not _lib.writes_allowed():
    raise SystemExit("probe 094 writes; run with --write")
S = _lib.sandbox_id(c, env)
P = {"type": "Project", "id": S}
rows = []


def errs(r):
    try:
        return json.dumps(r.json().get("errors"))
    except ValueError:
        return r.text


def title(r):
    """The error title verbatim, or the status alone for a 2xx."""
    if r.ok:
        return f"{r.status_code}"
    try:
        e = r.json()["errors"][0]
        return f"{r.status_code} {e['title']}" + (f" / {e['detail']}" if e.get("detail") else "")
    except (ValueError, KeyError, IndexError):
        return f"{r.status_code} {r.text}"


# --- requires: find the refused caller or stop -------------------------------------------------------
r = c.post("/entity/human_users/_search", headers=ARR, json={
    "filters": [["sg_status_list", "is", "act"], ["can_impersonate_this_user", "is", True],
                ["projects", "is", P]],
    "fields": ["login", "permission_rule_set"], "page": {"size": 100}})
low = [u for u in r.json()["data"]
       if (u["relationships"]["permission_rule_set"]["data"] or {}).get("name") not in ADMIN_SETS]
if not low:
    raise SystemExit("probe 094 requires:\n  " + "\n  ".join(requires))
low.sort(key=lambda u: u["id"])
person = low[0]
level = person["relationships"]["permission_rule_set"]["data"]["name"]
a = counted(FPT.from_env(env, sudo_as_login=person["attributes"]["login"]))
callers = [("script", c)]
# Optional: an Admin person, so the allowed branch is measured as a HumanUser too, not only as the script.
adm = sorted((u for u in r.json()["data"]
              if (u["relationships"]["permission_rule_set"]["data"] or {}).get("name") == "Admin"),
             key=lambda u: u["id"])
if adm:
    callers.append(("person (Admin)", counted(FPT.from_env(env, sudo_as_login=adm[0]["attributes"]["login"]))))
callers.append((f"person ({level})", a))
rows.append(f"refused caller: HumanUser in set {level!r}, member of the sandbox, via sudo_as_login; "
            f"allowed callers: the script{' and an Admin HumanUser, via sudo_as_login' if adm else ' only'}")

# --- candidate 1: the schema, read per caller ---------------------------------------------------------
rows.append("\n=== 1. GET /schema/<Type>/fields?project_id=<sandbox>: properties.editable per caller")
for who, cl in callers[1:] if len(callers) == 3 else callers:   # the script reads as the Admin person
    for t in ("Task", "Shot", "Asset"):
        d = cl.get(f"/schema/{t}/fields", params={"project_id": S}).json()["data"]
        ed = sorted(k for k, v in d.items() if v["editable"]["value"])
        rows.append(f"  {who:<16} {t}: {len(ed)} of {len(d)} editable"
                    + (f" {ed}" if len(ed) < 6 else ""))
    r = cl.get(f"/schema/Task", params={"project_id": S})
    rows.append(f"  {who:<16} GET /schema/Task -> {sorted(r.json()['data'])}")

with _lib.Created(c) as made:
    def mk(slug, body):
        r = c.post(f"/entity/{slug}", json=body)
        if not r.ok:
            raise SystemExit(f"POST {slug} {r.status_code} {errs(r)}")
        return made.add(slug, r.json()["data"]["id"])

    sh = mk("shots", {"project": P, "code": "zzprobe_094_shot"})
    SH = {"type": "Shot", "id": sh}
    tk = mk("tasks", {"project": P, "entity": SH, "content": "zzprobe_094_a"})
    TK = {"type": "Task", "id": tk}
    # A create that fails or rolls back can still touch its parent, late (see the end of the run), so each
    # create candidate gets a parent Shot of its own, per caller, read after a wait.
    writers = callers[1:] if len(callers) == 3 else callers
    parents = {(n, who): mk("shots", {"project": P, "code": f"zzprobe_094_parent_{n}_{i}"})
               for n in (6, 10) for i, (who, _) in enumerate(writers)}
    time.sleep(1.2)   # so a bump of updated_at, whose resolution is one second, cannot hide in the create

    def snap():
        t = c.get(f"/entity/tasks/{tk}", params={"fields": "updated_at,content,sg_status_list"})
        s = c.get(f"/entity/shots/{sh}", params={"fields": "updated_at,tasks"}).json()["data"]
        ev = c.post("/entity/event_log_entries/_search", headers=ARR, json={
            "filters": [["entity", "in", [TK, SH]]], "fields": ["event_type", "attribute_name"],
            "page": {"size": 200}}).json()["data"]
        ta = t.json()["data"]["attributes"] if t.ok else {"updated_at": f"GET {t.status_code}"}
        return {"task": (ta["updated_at"], ta.get("content")), "shot": s["attributes"]["updated_at"],
                "tasks": len(s["relationships"]["tasks"]["data"]),
                "events": {e["id"]: (e["attributes"]["event_type"], e["attributes"]["attribute_name"]) for e in ev}}

    def parent_state(i):
        d = c.get(f"/entity/shots/{i}", params={"fields": "updated_at,updated_by,tasks"}).json()["data"]
        return (d["attributes"]["updated_at"], (d["relationships"]["updated_by"]["data"] or {}).get("name"),
                len(d["relationships"]["tasks"]["data"]))
    parent_before = {k: parent_state(i) for k, i in parents.items()}
    base = snap()
    rows.append(f"\nbaseline: Task and Shot made by the script; {len(base['events'])} events on the two rows, "
                f"Shot.tasks {base['tasks']}")
    cur = c.get(f"/entity/tasks/{tk}", params={"fields": "content,sg_status_list"}).json()["data"]["attributes"]

    def side(before):
        now = snap()
        d = []
        if now["task"] != before["task"]:
            d.append(f"Task {before['task']} -> {now['task']}")
        if now["shot"] != before["shot"]:
            d.append(f"Shot.updated_at {before['shot']} -> {now['shot']}")
        if now["tasks"] != before["tasks"]:
            d.append(f"Shot.tasks {before['tasks']} -> {now['tasks']}")
        new = [v for k, v in now["events"].items() if k not in before["events"]]
        if new:
            d.append(f"events +{new}")
        return now, ("no side effect" if not d else "; ".join(d))

    fail = {"request_type": "update", "entity": "Task", "record_id": 999999999, "data": {"content": "x"}}
    cands = [
        ("2. no-op PUT Task content", "put", f"/entity/tasks/{tk}", {"content": cur["content"]}),
        ("3. no-op PUT Task sg_status_list", "put", f"/entity/tasks/{tk}", {"sg_status_list": cur["sg_status_list"]}),
        ("4. no-op PUT Shot code", "put", f"/entity/shots/{sh}", {"code": "zzprobe_094_shot"}),
        ("5. PUT Task {}", "put", f"/entity/tasks/{tk}", {}),
        ("6. POST Task, sg_status_list 'zz_bad'", "post", "/entity/tasks",
         lambda par: {"project": P, "entity": par, "content": "zzprobe_094_x", "sg_status_list": "zz_bad"}),
        ("7. POST Task, unknown field", "post", "/entity/tasks",
         {"project": P, "entity": SH, "content": "zzprobe_094_x", "zz_no_such_field": 1}),
        ("8. DELETE Task id 999999999", "delete", "/entity/tasks/999999999", None),
        ("9. _batch [delete the Task, failing update]", "post", "/entity/_batch",
         {"requests": [{"request_type": "delete", "entity": "Task", "record_id": tk}, fail]}),
        ("10. _batch [create a Task, failing update]", "post", "/entity/_batch",
         lambda par: {"requests": [{"request_type": "create", "entity": "Task",
                                    "data": {"project": P, "entity": par, "content": "zzprobe_094_b"}}, fail]}),
        ("11. _batch [PUT Task content to a new value, failing update]", "post", "/entity/_batch",
         {"requests": [{"request_type": "update", "entity": "Task", "record_id": tk,
                        "data": {"content": "zzprobe_094_changed"}}, fail]}),
        ("12. _batch [PUT Shot code to a new value, failing update]", "post", "/entity/_batch",
         {"requests": [{"request_type": "update", "entity": "Shot", "record_id": sh,
                        "data": {"code": "zzprobe_094_changed"}}, fail]}),
    ]
    state = base
    PER_CALLER = {2, 3, 4, 9, 11, 12}
    # The writes run as the two people only (`writers`); the script stands in for the allowed one where the
    # site has no Admin person to impersonate. Three callers per write would break the 60 s budget (#76).
    for label, verb, path, body in cands:
        rows.append(f"\n=== {label}")
        for who, cl in writers:
            n = int(label.split(".")[0])
            b = body({"type": "Shot", "id": parents[(n, who)]}) if callable(body) else body
            r = getattr(cl, verb)(path, **({"json": b} if b is not None else {}))
            if r.ok and verb == "post" and path == "/entity/tasks":
                made.add("tasks", r.json()["data"]["id"])
            rows.append(f"  {who:<16} {title(r)}")
            # Per caller where the write lands on the shared rows; once per candidate where it cannot
            # (a create goes to its own parent, 7 and 8 fail before any row is touched), for the budget.
            if n in PER_CALLER or who == writers[-1][0]:
                state, fx = side(state)
                rows.append(f"  {'':<16} -> {fx}" + ("" if n in PER_CALLER else " (read once, after both)"))

    time.sleep(3)   # the late parent bump lands 2-4 s after the call, and candidates 11-12 ran since
    end = snap()
    rows.append("\n=== parents of the create candidates, 3 s after the last call: (updated_at, updated_by, tasks)")
    for (n, who), i in parents.items():
        now = parent_state(i)
        ev = c.post("/entity/event_log_entries/_search", headers=ARR, json={
            "filters": [["entity", "is", {"type": "Shot", "id": i}], ["attribute_name", "is", "tasks"]],
            "fields": ["event_type"]}).json()["data"]
        rows.append(f"  {n:>2} {who:<16} {parent_before[(n, who)]} -> {now}, Shot.tasks change events {len(ev)}")
    rows.append(f"\n=== end: {len(end['events'])} events on the two rows (baseline {len(base['events'])}), "
                f"Task {end['task']}, Shot.tasks {end['tasks']}")
    r = c.post("/entity/tasks/_search", headers=ARR, json={
        "filters": [["entity", "is", SH]], "fields": ["content"], "options": {"return_only": "retired"}})
    rows.append(f"  retired Tasks on the Shot (a rolled-back create or delete would show): {len(r.json()['data'])}")

rows.append("\n=== left clean?")
for slug, f, v in (("tasks", "content", "zzprobe_094"), ("shots", "code", "zzprobe_094")):
    r = c.post(f"/entity/{slug}/_search", headers=ARR,
               json={"filters": [["project", "is", P], [f, "starts_with", v]], "fields": [f]})
    rows.append(f"  live {slug} {v}*: {len(r.json()['data'])}")
rows.append(f"\nwall {time.perf_counter() - T0:.1f}s, {CALLS[0]} REST calls plus token requests")
_lib.emit("094_permission_preflight", "\n".join(rows), env)
