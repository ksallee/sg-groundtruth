"""Sandbox task templates for probes 083-090: build one, read the Tasks it generated.

A TaskTemplate is site-wide and its own Tasks carry no project (entity_types/TaskTemplate), so a probe
that needs one builds it, and `_lib.Created` deletes it. Deleting the template retires its tasks.

Assignees go to an empty Group: an assignment to a person can notify that person, and a Group with
no members notifies nobody.
"""
import json
import time

ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
TASK_FIELDS = ["content", "entity", "project", "step", "task_template", "template_task", "start_date",
               "due_date", "duration", "est_in_mins", "task_assignees", "task_reviewers", "sg_sort_order",
               "milestone", "sg_status_list", "sg_description", "upstream_tasks", "downstream_tasks",
               "pinned", "dependency_violation", "created_at"]


def errs(r):
    """The whole errors[] object, `source` included (probe 017)."""
    try:
        return json.dumps(r.json().get("errors"))
    except ValueError:
        return r.text


def search(c, slug, filters, fields, size=500):
    r = c.post(f"/entity/{slug}/_search", headers=ARR,
               json={"filters": filters, "fields": fields, "page": {"size": size}})
    if not r.ok:
        raise SystemExit(f"{slug} _search {r.status_code} {errs(r)}")
    return r.json()["data"]


def rel(d, k):
    return ((d.get("relationships") or {}).get(k) or {}).get("data")


def ref(d):
    return {"type": d["type"], "id": d["id"]}


def steps(c, entity_type="Shot"):
    """Step ids by code for one entity type. Step codes are site configuration, so resolve them."""
    out = {}
    for s in search(c, "steps", [["entity_type", "is", entity_type]], ["code"]):
        out.setdefault(s["attributes"]["code"], s["id"])
    return out


def empty_group(c):
    for g in search(c, "groups", [], ["code", "users"]):
        if not rel(g, "users"):
            return {"type": "Group", "id": g["id"]}
    return None


def post(c, made, slug, body):
    r = c.post(f"/entity/{slug}", json=body)
    if not r.ok:
        raise SystemExit(f"POST {slug} {r.status_code} {errs(r)}")
    d = r.json()["data"]
    made.add(slug, d["id"])
    return d


def template(c, made, code, tasks, deps=(), entity_type="Shot"):
    """A TaskTemplate holding `tasks` (content -> extra fields) and `deps` (downstream, upstream, extra).

    Returns (template ref, {content: template task id}).
    """
    tt = post(c, made, "task_templates", {"code": code, "entity_type": entity_type})
    TT = ref(tt)
    ids = {}
    for content, extra in tasks.items():
        ids[content] = post(c, made, "tasks", {"content": content, "task_template": TT, **extra})["id"]
    for down, up, extra in deps:
        post(c, made, "task_dependencies", {"task": {"type": "Task", "id": ids[down]},
                                            "dependent_task": {"type": "Task", "id": ids[up]}, **extra})
    return TT, ids


def tasks_on(c, entity, fields=TASK_FIELDS, settle=0.0):
    """The Tasks whose `entity` is this row, oldest first. `settle` waits for an async apply."""
    if settle:
        time.sleep(settle)
    out = search(c, "tasks", [["entity", "is", entity]], fields)
    return sorted(out, key=lambda t: t["id"])


def deps_among(c, task_ids):
    if not task_ids:
        return []
    return search(c, "task_dependencies",
                  [["task", "in", [{"type": "Task", "id": i} for i in task_ids]]],
                  ["task", "dependent_task", "dependency_type", "offset_days", "shift_ratio"])


def adopt(made, tasks):
    """Generated Tasks were not created by the probe's own POST; register them for deletion."""
    known = {(s, i) for s, i in made.rows}
    for t in tasks:
        if ("tasks", t["id"]) not in known:
            made.add("tasks", t["id"])


def line(t):
    a = t["attributes"]
    step = (rel(t, "step") or {}).get("name")
    tt = (rel(t, "template_task") or {}).get("id")
    return (f"{a['content']:<22} step={step!s:<8} template_task={tt!s:<6} "
            f"status={a['sg_status_list']!s:<4} order={a['sg_sort_order']!s:<4} "
            f"start={a['start_date']} due={a['due_date']} dur={a['duration']}")
