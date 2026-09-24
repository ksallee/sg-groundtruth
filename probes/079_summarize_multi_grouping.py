"""Q: does `_summarize` nest two `grouping` entries, and what do `status_percentage` and `status_list`
return on `sg_status_list`?

A page runner draws group headers with a count and a status roll-up per group. If one `_summarize` call
returns the nested groups and the roll-up, the runner never pages rows to draw headers. Sample project,
read only.
"""
import collections
import json

import _lib
import _pages as P

env = _lib.load_env()
c = _lib.client()
PROJECT = _lib.sample_projects(c, env)[0]
F = [["project", "is", {"type": "Project", "id": PROJECT}]]
rows = []


def summ(slug, fields, grouping=None, filters=F):
    body = {"filters": filters, "summary_fields": fields}
    if grouping is not None:
        body["grouping"] = grouping
    r = c.post(f"/entity/{slug}/_summarize", headers=P.ARR, json=body)
    return r.status_code, (r.json()["data"] if r.ok else r.json()["errors"][0])


def g(field, typ="exact"):
    return {"field": field, "type": typ, "direction": "asc"}


rows.append("=== two grouping entries, Shots: sg_sequence then sg_status_list")
st, d = summ("shots", [{"field": "id", "type": "count"}], [g("sg_sequence"), g("sg_status_list")])
rows.append(f"  -> {st}; top-level groups {len(d['groups'])}, total {d['summaries']}")
first = d["groups"][0]
rows.append(f"  group keys {sorted(first)}; nested groups {len(first['groups'])}; nested keys {sorted(first['groups'][0])}")
rows.append(f"  {json.dumps(dict(first, groups=first['groups'][:2]))[:420]}")
_lib.note_from(d)
parent_ok = all(x["summaries"]["id"] == sum(y["summaries"]["id"] for y in x["groups"]) for x in d["groups"])
rows.append(f"  each parent's count equals the sum of its children: {parent_ok}")

rows.append("\n=== three grouping entries, Tasks: entity, step, sg_status_list")
st, d3 = summ("tasks", [{"field": "id", "type": "count"}], [g("entity"), g("step"), g("sg_status_list")])
depth, node = 0, d3
while node.get("groups"):
    depth += 1
    node = node["groups"][0]
rows.append(f"  -> {st}; nesting depth {depth}")
_lib.note_from(d3)

rows.append("\n=== grouping on a dotted path and by date bucket, Tasks")
for label, grp in (("entity.Shot.sg_sequence", [g("entity.Shot.sg_sequence")]),
                   ("start_date by week", [g("start_date", "week")]),
                   ("bogus type", [g("start_date", "zzprobe")])):
    st, x = summ("tasks", [{"field": "id", "type": "count"}], grp)
    rows.append(f"  {label:<24} -> {st} " + (f"{len(x['groups'])} groups, first {json.dumps(x['groups'][0]['group_name'])}"
                                             if st == 200 and x["groups"] else json.dumps(x)[:400]))

rows.append("\n=== status_percentage, status_percentage_as_float and status_list on sg_status_list")
for slug in ("shots", "tasks", "versions"):
    st, x = summ(slug, [{"field": "sg_status_list", "type": "status_percentage"}, {"field": "id", "type": "count"}],
                 [g("sg_status_list")])
    per = [(y["group_value"], y["summaries"]["id"], y["summaries"]["sg_status_list"]) for y in x["groups"]]
    rows.append(f"  {slug:<9} status_percentage {x['summaries']['sg_status_list']} over {x['summaries']['id']} rows; "
                f"per status group (value, rows, status_percentage): {per}")
    st, f = summ(slug, [{"field": "sg_status_list", "type": "status_percentage_as_float"}])
    st2, sl = summ(slug, [{"field": "sg_status_list", "type": "status_list"}])
    rows.append(f"            status_percentage_as_float {json.dumps(f['summaries']['sg_status_list'])}; "
                f"status_list {json.dumps(sl['summaries']['sg_status_list'])}")
for label, extra in (("value", "fin"), ("values", ["fin"]), ("status", "fin")):
    st, x = summ("shots", [{"field": "sg_status_list", "type": "status_percentage", label: extra}])
    rows.append(f"  shots status_percentage with {label}={json.dumps(extra)} -> {st} {json.dumps(x['summaries'])}")

rows.append("\n=== status_list per group against the statuses in the group")
st, x = summ("shots", [{"field": "sg_status_list", "type": "status_list"}, {"field": "id", "type": "count"}],
             [g("sg_sequence"), g("sg_status_list")])
combos = collections.Counter()
for grp in x["groups"]:
    members = tuple(sorted(y["group_value"] or "" for y in grp["groups"]))
    combos[(members, grp["summaries"]["sg_status_list"])] += 1
for (members, sl), n in combos.most_common():
    rows.append(f"  statuses {list(members)} -> status_list {json.dumps(sl)}  ({n} groups)")
st, x = summ("tasks", [{"field": "sg_status_list", "type": "status_list"}], [g("entity"), g("sg_status_list")])
combos = collections.Counter()
for grp in x["groups"]:
    members = tuple(sorted(y["group_value"] or "" for y in grp["groups"]))
    combos[(members, grp["summaries"]["sg_status_list"])] += 1
for (members, sl), n in combos.most_common(8):
    rows.append(f"  tasks by entity: statuses {list(members)} -> status_list {json.dumps(sl)}  ({n} groups)")
rows.append(f"  ... {len(combos)} distinct (statuses, status_list) pairs over the Tasks")

_lib.emit("079_summarize_multi_grouping", "\n".join(rows), env)
