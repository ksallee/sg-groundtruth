"""Q: when an entity's `task_template` is written to T, what happens to the Tasks already linked to T?

Probe 096 saw such a write overwrite `sg_sort_order`, `sg_description` and `duration` on Tasks that
already pointed at T, keep `sg_status_list`, and delete an edge T lacks. This measures it field by field.

One template T, three tasks, every field a template task carries set somewhere:
  a  step 1, dates, est, description, order 10, status na, assignees and reviewers G1, list, checkbox
  b  step 2, duration, est, description, order 20, status wtg, assignees and reviewers G1, list, checkbox
  c  step 3, milestone, order 30, nothing else (the template-empty case)
  edges: b on a (default type), c on b start-to-start offset 2
and U, a template with one task u, for the "from another template" case.

Shot 1, created with T, then hand-edited:
  a1  every field set to a value other than T's, content renamed, step changed
  b1  every field emptied that can be
  c1  every field T leaves empty set, milestone cleared
  edges: b1 on a1 deleted, c1 on b1 retyped, c1 on a1 added, x1 (hand-made, unlinked) on a1 added
  then task_template null, then T (the re-apply after a clear); then U (the other direction).
Shot 2, created with U (Task u2), plus hand-made a2 (like a1) and b2 (like b1); edges b2 on a2
  start-to-start offset 3 and u2 on a2. a2 and b2 claimed for T by `template_task`, then task_template T:
  the recipe 015 merge, Tasks claimed in the same run.

`pinned` is read on every snapshot: a1 is a root Task (never pins, probe 097) and c1 a hand-dated
downstream one (pins, probe 087), so "dates kept" is told apart from "pinned held them".
Every edge the apply deletes is read back under options[return_only]=retired, with the probe's own
DELETE of b1 on a1 as the control (probe 101).

Preconditions, checked first from the schema and exit if missing (#73, `requires` below): 4+ Shot
Steps; statuses na, wtg, ip on Task.sg_status_list; a Task list field sg_ with 2+ values; 2 Groups
with no members, so an assignment notifies nobody (reused, never created). A Task checkbox sg_ field
is used when the site has one. Writes only, in the sandbox, behind --write. Every row is deleted, and
every TaskDependency the run saw is searched for afterwards. Wall time and call count are printed.
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
    raise SystemExit("probe 102 writes; run with --write")
requires = [
    "4+ Steps with entity_type Shot (web UI: Site Preferences > Pipeline Steps). Detected by a Step _search.",
    "Task.sg_status_list offers na, wtg, ip. Detected by GET /schema/Task/fields.",
    "a Task list field named sg_* with 2+ valid values (a custom field; the site's own). Same GET.",
    "2 Groups with no users (web UI: People > Groups). Detected by a Group _search; reused, never created.",
]
S = _lib.sandbox_id(c, env)
P = {"type": "Project", "id": S}
ST = T.steps(c)
SCH = c.get("/schema/Task/fields", params={"project_id": S}).json()["data"]


def vv(f):
    return (SCH[f]["properties"].get("valid_values") or {}).get("value") or []


LISTF = sorted(f for f, d in SCH.items() if f.startswith("sg_") and d["data_type"]["value"] == "list"
               and d["editable"]["value"] and len(vv(f)) >= 2)
CHKF = sorted(f for f, d in SCH.items() if f.startswith("sg_") and d["data_type"]["value"] == "checkbox"
              and d["editable"]["value"])
G0 = T.empty_group(c)
EMPTYG = [{"type": "Group", "id": g["id"]} for g in T.search(c, "groups", [], ["code", "users"])
          if not T.rel(g, "users")]
missing = [r for r, ok in zip(requires, (len(ST) >= 4, {"na", "wtg", "ip"} <= set(vv("sg_status_list")),
                                          bool(LISTF), len(EMPTYG) >= 2)) if not ok]
if missing:
    raise SystemExit("probe 102 requires:\n  " + "\n  ".join(missing))
LF = LISTF[0]
L1, L3 = vv(LF)[0], vv(LF)[-1]
CK = CHKF[0] if CHKF else None
G1, G2 = G0, next(g for g in EMPTYG if g != G0)
codes = sorted(ST)
s1, s2, s3, s4 = ({"type": "Step", "id": ST[k]} for k in codes[:4])
STEP = {ST[k]: f"s{i + 1}" for i, k in enumerate(codes[:4])}
rows = []
F = ["content", "step", "template_task", "duration", "est_in_mins", "sg_description", "sg_sort_order",
     "milestone", "start_date", "due_date", "task_assignees", "task_reviewers", "sg_status_list",
     "pinned", LF] + ([CK] if CK else [])
names = {("Group", G1["id"]): "G1", ("Group", G2["id"]): "G2"}
seen_deps = set()
retire_check = []  # (label, edge id) read back under options[return_only]=retired after the run


def show(v):
    if isinstance(v, dict):
        return names.get((v.get("type"), v.get("id")), f"{v.get('type')}:{v.get('id')}")
    if isinstance(v, list):
        return "[" + ",".join(show(x) for x in v) + "]"
    return str(v)


def fields(t):
    a = t["attributes"]
    out = [f"content={a['content']}"]
    for k in F[1:]:
        v = T.rel(t, k) if k in ("step", "template_task", "task_assignees", "task_reviewers") else a[k]
        if k == "step" and v:
            v = STEP.get(v["id"], v["id"])
        out.append(f"{k.replace('sg_', '').replace('task_', '').replace('_in_mins', '')}={show(v)}")
    return " ".join(out)


def snap(label, shot):
    got = T.tasks_on(c, shot, F)
    T.adopt(made, got)
    for t in got:
        names.setdefault(("Task", t["id"]), f"{t['attributes']['content']}#{t['id'] % 1000}")
    deps = T.deps_among(c, [t["id"] for t in got])
    seen_deps.update(d["id"] for d in deps)
    rows.append(f"  {label}: {len(got)} Tasks, {len(deps)} deps")
    for t in got:
        rows.append(f"    {show(T.ref(t)):<14} {fields(t)}")
    for d in deps:
        a = d["attributes"]
        rows.append(f"    dep {d['id']}: {show(T.rel(d, 'task'))} on {show(T.rel(d, 'dependent_task'))} "
                    f"{a['dependency_type']} offset={a['offset_days']}")
    return {t["attributes"]["content"]: t for t in got}, deps


def put(slug, i, body, label):
    r = c.put(f"/entity/{slug}/{i}", json=body)
    rows.append(f"  {label} -> {r.status_code} {T.errs(r) if not r.ok else ''}")
    return r


def dep(down, up, extra=None):
    d = T.post(c, made, "task_dependencies", {"task": T.ref(down), "dependent_task": T.ref(up), **(extra or {})})
    rows.append(f"  POST dep {show(T.ref(down))} on {show(T.ref(up))} {extra or ''} -> {d['id']}")
    seen_deps.add(d["id"])
    return d


def edge(deps, down, up):
    return [d for d in deps if (T.rel(d, "task") or {}).get("id") == down["id"]
            and (T.rel(d, "dependent_task") or {}).get("id") == up["id"]]


with _lib.Created(c) as made:
    rows.append(f"=== probed site: list field {LF} {L1}/{L3}, checkbox field {CK}, G1 G2 reused empty Groups")
    CKT = {CK: True} if CK else {}
    CKF = {CK: False} if CK else {}
    TT, ids = T.template(c, made, "zzprobe_102_T", {
        "a": {"step": s1, "start_date": "2026-03-02", "due_date": "2026-03-04", "est_in_mins": 600,
              "sg_description": "T.a", "sg_sort_order": 10, "sg_status_list": "na", "task_assignees": [G1],
              "task_reviewers": [G1], LF: L1, **CKT},
        "b": {"step": s2, "duration": 960, "est_in_mins": 300, "sg_description": "T.b", "sg_sort_order": 20,
              "sg_status_list": "wtg", "task_assignees": [G1], "task_reviewers": [G1], LF: L1, **CKT},
        "c": {"step": s3, "milestone": True, "sg_sort_order": 30}},
        deps=[("b", "a", {}), ("c", "b", {"dependency_type": "start-to-start", "offset_days": 2})])
    UU, uids = T.template(c, made, "zzprobe_102_U", {"u": {"step": s4, "sg_sort_order": 5}})
    names.update({("Task", i): f"T.{k}" for k, i in ids.items()})
    names.update({("Task", i): f"U.{k}" for k, i in uids.items()})
    rows.append("=== template T, as read")
    for t in sorted(T.search(c, "tasks", [["task_template", "is", TT]], F), key=lambda t: t["id"]):
        rows.append(f"    {show(T.ref(t)):<14} {fields(t)}")

    DIFF = {"step": s4, "start_date": "2026-05-04", "due_date": "2026-05-08", "est_in_mins": 60,
            "sg_description": "hand", "sg_sort_order": 77, "task_assignees": [G2], "task_reviewers": [G2],
            LF: L3, **CKF}
    EMPTY = {"step": None, "duration": None, "est_in_mins": None, "sg_description": None, "sg_sort_order": None,
             "task_assignees": [], "task_reviewers": [], LF: None, **CKF}
    FILL = {"milestone": False, "start_date": "2026-06-01", "due_date": "2026-06-03", "est_in_mins": 120,
            "sg_description": "hand", "task_assignees": [G2], "task_reviewers": [G2], LF: L3, **CKT}

    rows.append("\n=== Shot 1, created with T, hand-edited")
    sh1 = T.ref(T.post(c, made, "shots", {"project": P, "code": "zzprobe_102_sh1", "task_template": TT}))
    k1, d1 = snap("created", sh1)
    a1, b1, c1 = k1["a"], k1["b"], k1["c"]
    for d in edge(d1, b1, a1):
        r = c.delete(f"/entity/task_dependencies/{d['id']}")
        rows.append(f"  DELETE dep b1 on a1 -> {r.status_code}")
        retire_check.append(("control: b1 on a1, DELETEd by the probe", d["id"]))
    for d in edge(d1, c1, b1):
        retire_check.append(("c1 on b1 retyped by hand", d["id"]))
        put("task_dependencies", d["id"], {"dependency_type": "finish-to-finish", "offset_days": 5},
            "PUT dep c1 on b1 finish-to-finish offset 5")
    put("tasks", a1["id"], {"content": "a_renamed", "sg_status_list": "ip", **DIFF}, "PUT a1 every field other")
    put("tasks", b1["id"], {**EMPTY, "start_date": None, "due_date": None}, "PUT b1 every field empty")
    put("tasks", c1["id"], {"sg_status_list": "ip", **FILL}, "PUT c1 T's empty fields set")
    x1 = T.post(c, made, "tasks", {"project": P, "entity": sh1, "content": "x", "step": s4})
    names[("Task", x1["id"])] = f"x#{x1['id'] % 1000}"
    retire_check.append(("c1 on a1, not in T", dep(c1, a1)["id"]))
    retire_check.append(("x1 on a1, x1 unlinked", dep(x1, a1)["id"]))
    snap("before", sh1)
    put("shots", sh1["id"], {"task_template": None}, "PUT Shot1 task_template null")
    snap("after null", sh1)
    put("shots", sh1["id"], {"task_template": TT}, "PUT Shot1 task_template T")
    k1, _ = snap("after T", sh1)
    put("tasks", k1["a"]["id"], {"sg_description": "hand2"}, "PUT a1 sg_description hand2")
    put("shots", sh1["id"], {"task_template": UU}, "PUT Shot1 task_template U (the other direction)")
    snap("after U", sh1)

    rows.append("\n=== Shot 2, created with U, hand-made a2 b2 claimed for T in the same run")
    sh2 = T.ref(T.post(c, made, "shots", {"project": P, "code": "zzprobe_102_sh2", "task_template": UU}))
    a2 = T.post(c, made, "tasks", {"project": P, "entity": sh2, "content": "a_renamed", "sg_status_list": "ip",
                                   **{k: v for k, v in DIFF.items() if k not in ("start_date", "due_date")},
                                   "duration": 1920})
    b2 = T.post(c, made, "tasks", {"project": P, "entity": sh2, "content": "b", "sg_status_list": "wtg"})
    k2, _ = snap("created", sh2)
    retire_check.append(("b2 on a2 start-to-start 3", dep(b2, a2, {"dependency_type": "start-to-start",
                                                                   "offset_days": 3})["id"]))
    retire_check.append(("u2 on a2, u2 linked to U", dep(k2["u"], a2)["id"]))
    put("tasks", a2["id"], {"template_task": {"type": "Task", "id": ids["a"]}}, "PUT a2 template_task T.a")
    put("tasks", b2["id"], {"template_task": {"type": "Task", "id": ids["b"]}}, "PUT b2 template_task T.b")
    snap("claimed", sh2)
    put("shots", sh2["id"], {"task_template": TT}, "PUT Shot2 task_template T")
    snap("after T", sh2)

    rows.append("\n=== edges the probe made or saw deleted: GET live, GET options[return_only]=retired")
    for label, i in retire_check:
        live = c.get(f"/entity/task_dependencies/{i}").status_code
        ret = c.get(f"/entity/task_dependencies/{i}", params={"options[return_only]": "retired"}).status_code
        rows.append(f"  {label} ({i}): live {live}, retired {ret}")

rows.append("\n=== left clean?")
for slug, key in (("shots", "code"), ("task_templates", "code")):
    rows.append(f"  {slug} zzprobe_102*: {len(T.search(c, slug, [[key, 'starts_with', 'zzprobe_102']], [key]))}")
rows.append(f"  Tasks on the two Shots: "
            f"{len(T.search(c, 'tasks', [['entity', 'in', [sh1, sh2]]], ['content']))}")
rows.append(f"  TaskDependency rows among the {len(seen_deps)} ids the run saw, server-made included: "
            f"{len(T.search(c, 'task_dependencies', [['id', 'in', sorted(seen_deps)]], ['task']))}")
rows.append(f"\n  wall {time.monotonic() - t0:.1f}s, {CALLS[0]} calls")

_lib.emit("102_task_template_resync", "\n".join(rows), env)
