"""Q: do `Group.users` and a Group in `Task.task_assignees` resolve to the members, and what can an
Artist read of them?

sg-onset addresses its Shot Note to the people assigned to the Shot's Tasks. A Task's
`task_assignees` takes `['Group', 'HumanUser']`, so an assignee can be a Group, and the app must turn
it into people. Probe 027 found `Group.users` and `HumanUser.groups` on the probed site but every
group empty, so nothing resolved one.

Steps, in the sandbox: the script makes a Group of two test people (`_people`), a Shot, a Task
assigned to the Group and a Task assigned to one member. Then, as the script and as a member who is
an Artist (`sudo_as_login`, probe 027): read the Group, the member's `groups`, both Tasks'
`task_assignees` and followers, and filter Tasks by the member directly and through the Group.

Writes behind `--write`: the Group (site-wide; a Group has no project), the Shot and the Tasks, all
deleted on exit.

    python probes/150_group_resolution.py --write
"""
import json

import _lib
import _people
from sg_groundtruth.client import FPT

ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
env = _lib.load_env()
c = _lib.client()
if not _lib.writes_allowed():
    raise SystemExit("probe 150 writes; run with --write")
SB = _lib.sandbox_id(c, env)
P = {"type": "Project", "id": SB}
ME, LOGIN, aliases = _people.operator_and_aliases(c, env, SB)
(B, B_LOGIN, B_GROUP), (C, _, C_GROUP) = aliases[0], aliases[1]
rows = []


def out(s=""):
    rows.append(str(s))
    print(s, flush=True)


def said(r):
    if r.ok:
        return str(r.status_code)
    try:
        e = r.json()["errors"][0]
        return f"{r.status_code} code {e.get('code')} {e.get('title')!r}"
    except (ValueError, KeyError, IndexError):
        return f"{r.status_code} {r.text}"


NAMES = {}


def name(d):
    """A link as `Type <role>`, the role read from the ids this probe made."""
    if not d:
        return "null"
    return f"{d['type']} <{NAMES.get((d['type'], d['id']), 'other')}>"


def links(who, path, field):
    r = who.get(path, params={"fields": field})
    if not r.ok:
        return said(r)
    d = r.json()["data"]["relationships"].get(field, {}).get("data")
    if d is None:
        return f"200, no {field} key" if field not in r.json()["data"]["relationships"] else "null"
    return [name(x) for x in d] if isinstance(d, list) else name(d)


def tasks(who, filters):
    """The Tasks this probe made that match, and how many other sandbox Tasks match too."""
    r = who.post("/entity/tasks/_search", headers=ARR, json={
        "filters": [["project", "is", P]] + filters, "fields": ["id"], "page": {"size": 500}})
    if not r.ok:
        return said(r)
    got = [NAMES.get(("Task", x["id"]), "other") for x in r.json()["data"]]
    return f"{sorted(g for g in got if g != 'other')} and {got.count('other')} other sandbox Tasks"


artist = FPT.from_env(env, sudo_as_login=B_LOGIN)
NAMES.update({("HumanUser", B): f"member B, {B_GROUP}", ("HumanUser", C): f"member C, {C_GROUP}",
              ("HumanUser", ME): "operator"})

with _lib.Created(c) as made:
    r = c.post("/entity/groups", json={"code": "zzprobe_150_group",
                                       "users": [{"type": "HumanUser", "id": B}, {"type": "HumanUser", "id": C}]})
    out(f"POST /entity/groups {{code, users: [B, C]}} -> {said(r)}")
    G = made.add("groups", r.json()["data"]["id"])
    NAMES[("Group", G)] = "the group"
    shot = made.add("shots", c.post("/entity/shots", json={"project": P, "code": "zzprobe_150_shot"}).json()["data"]["id"])
    tg = c.post("/entity/tasks", json={"project": P, "content": "zzprobe_150 to the group",
                                       "entity": {"type": "Shot", "id": shot},
                                       "task_assignees": [{"type": "Group", "id": G}]})
    out(f"POST /entity/tasks task_assignees [the group] -> {said(tg)}")
    TG = made.add("tasks", tg.json()["data"]["id"])
    tb = c.post("/entity/tasks", json={"project": P, "content": "zzprobe_150 to B",
                                       "entity": {"type": "Shot", "id": shot},
                                       "task_assignees": [{"type": "HumanUser", "id": B}]})
    TB = made.add("tasks", tb.json()["data"]["id"])
    NAMES.update({("Task", TG): "task to the group", ("Task", TB): "task to B"})

    for who, label in ((c, "script"), (artist, f"member B ({B_GROUP}), sudo")):
        out(f"\n===== as the {label}")
        r = who.get("/entity/groups", params={"fields": "code,users", "page[size]": 100})
        seen = [x["id"] for x in r.json()["data"]] if r.ok else said(r)
        out(f"  GET /entity/groups -> {said(r)}, {len(seen) if isinstance(seen, list) else seen} rows, the group among them: "
            f"{G in seen if isinstance(seen, list) else '-'}")
        out(f"  the group's users -> {links(who, f'/entity/groups/{G}', 'users')}")
        out(f"  the group's sg_people -> {links(who, f'/entity/groups/{G}', 'sg_people')}")
        out(f"  member B's groups -> {links(who, f'/entity/human_users/{B}', 'groups')}")
        out(f"  member C readable -> {said(who.get(f'/entity/human_users/{C}', params={'fields': 'login'}))}")
        out(f"  task to the group: task_assignees -> {links(who, f'/entity/tasks/{TG}', 'task_assignees')}")
        out(f"  task to B: task_assignees -> {links(who, f'/entity/tasks/{TB}', 'task_assignees')}")
        for f, v in ((["task_assignees", "is", {"type": "HumanUser", "id": B}], "task_assignees is B"),
                     (["task_assignees", "is", {"type": "Group", "id": G}], "task_assignees is the group"),
                     (["task_assignees.Group.users", "is", {"type": "HumanUser", "id": B}], "task_assignees.Group.users is B"),
                     (["task_assignees.HumanUser.groups", "is", {"type": "Group", "id": G}], "task_assignees.HumanUser.groups is the group"),
                     (["task_assignees", "in", [{"type": "HumanUser", "id": B}, {"type": "HumanUser", "id": C}]], "task_assignees in [B, C]")):
            out(f"  filter {v} -> {tasks(who, [f])}")
        for t, lab in ((TG, "task to the group"), (TB, "task to B")):
            r = who.get(f"/entity/tasks/{t}/followers")
            out(f"  {lab}: followers -> {said(r)} {[name({'type': x['type'], 'id': x['id']}) for x in r.json()['data']] if r.ok else ''}")
    r = c.put(f"/entity/groups/{G}", json={"users": [{"type": "HumanUser", "id": B}]})
    out(f"\nPUT the group's users to [B] -> {said(r)}; task to the group now resolves through it to "
        f"{tasks(c, [['task_assignees.Group.users', 'is', {'type': 'HumanUser', 'id': C}]])} for C")
    r = c.get(f"/entity/tasks/{TG}/followers")
    out(f"  task to the group: followers after -> {[name({'type': x['type'], 'id': x['id']}) for x in r.json()['data']]}")
    r = c.put(f"/entity/tasks/{TG}", json={"task_assignees": [{"type": "Group", "id": G}, {"type": "HumanUser", "id": ME}]})
    f = c.get(f"/entity/tasks/{TG}/followers").json()["data"]
    out(f"PUT task to the group += the operator -> {said(r)}; followers -> {[name({'type': x['type'], 'id': x['id']}) for x in f]}")
    _lib.emit("150_group_resolution", "\n".join(rows), env)
