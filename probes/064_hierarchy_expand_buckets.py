"""Q: why does `/hierarchy/_expand` answer the same "no group" node once after every group, and
what is behind that path?

Expanding a project's Shot node returns its children interleaved: sequence, bucket, sequence,
bucket, where every bucket is the same `__none__` node. This measures whether the repeats differ at
all, what the bucket answers, whether its rows are also filed under a sequence, whether the count
tracks the groups or the ungrouped rows, and what the same node looks like for Assets, which are
grouped by a list field rather than by an entity.

Read-only. Every call is a tree expansion or a count over rows the site already has.

    python probes/064_hierarchy_expand_buckets.py
"""
import json

import _lib

env = _lib.load_env()
c = _lib.client()
P = _lib.sample_projects(c, env)[0]

JSON = {"Content-Type": "application/json"}
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
NONE = "__none__"
rows = []


def out(s=""):
    rows.append(s)


def head(s):
    out(f"\n===== {s}")


def expand(path, **extra):
    body = {"path": path}
    body.update(extra)
    return c.post("/hierarchy/_expand", headers=JSON, json=body)


def children(path):
    r = expand(path)
    return r, (r.json()["data"].get("children", []) if r.ok else [])


def count(slug, pid, extra=None):
    """A record count, so a project's own totals can be set against what the tree shows."""
    f = [["project", "is", {"type": "Project", "id": pid}]]
    if extra:
        f.append(extra)
    r = c.post(f"/entity/{slug}/_summarize", headers=ARR,
               json={"filters": f, "summary_fields": [{"field": "id", "type": "record_count"}]})
    return r.json()["data"]["summaries"]["id"] if r.ok else f"ERR {r.status_code}"


def marks(kids):
    """The order the children come back in: g for a group, B for the bucket."""
    return "".join("B" if k.get("path", "").endswith(NONE) else "g" for k in kids)


def entity_ids(kids):
    return [k["ref"]["value"]["id"] for k in kids if k["ref"]["kind"] == "entity"]


# 1. The sample project's Shot node, and whether the repeats differ from one another.
head(f"1. POST /hierarchy/_expand {{'path': '/Project/{P}/Shot'}}")
r, kids = children(f"/Project/{P}/Shot")
buckets = [k for k in kids if k.get("path", "").endswith(NONE)]
groups = [k for k in kids if k not in buckets]
out(f"  {len(kids)} children, {len(groups)} groups, {len(buckets)} buckets, order {marks(kids)}")
out(f"  Sequence rows in the project {count('sequences', P)}, "
    f"Shots {count('shots', P)}, of them unsequenced {count('shots', P, ['sg_sequence', 'is', None])}")
out(f"  first group: {json.dumps({k: groups[0][k] for k in ('label', 'path', 'ref')})}")
out(f"  the bucket:  {json.dumps(buckets[0])}")
out(f"  every bucket serialises identically, key order included: "
    f"{len({json.dumps(b) for b in buckets}) == 1}")
out(f"  the response spells that path {r.text.count(json.dumps(buckets[0]['path']))} times "
    f"across {len(buckets)} children")
second = expand(f"/Project/{P}/Shot")
out(f"  a second call is byte-identical: {second.text == r.text}")
out(f"  seed_entity_field changes nothing: "
    f"{expand(f'/Project/{P}/Shot', seed_entity_field='Version.entity').text == r.text}")
_lib.note_names(*[k["label"] for k in groups])

# 2. What the bucket answers, and whether those rows are also filed under a group.
def bucket_rows(pid, kids):
    """The bucket's own rows, twice, set against the rows under every group beside it."""
    bs = [k for k in kids if k.get("path", "").endswith(NONE)]
    gs = [k for k in kids if k not in bs]
    a, b = expand(bs[0]["path"]), expand(bs[0]["path"])
    mine = entity_ids(a.json()["data"].get("children", []))
    out(f"  {bs[0]['path']} -> {a.status_code}, {len(mine)} children, kinds "
        f"{sorted({k['ref']['kind'] for k in a.json()['data']['children']})}, "
        f"byte-identical across two calls: {a.text == b.text}")
    out(f"     has_children {bs[0]['has_children']}, children "
        f"{json.dumps(a.json()['data'].get('children'))[:160]}")
    grouped = {i for g in gs for i in entity_ids(children(g["path"])[1])}
    out(f"  {len(grouped)} rows under the {len(gs)} groups; bucket rows also under a group: "
        f"{sorted(set(mine) & grouped) or 'none'}")
    out(f"  bucket + groups = {len(set(mine) | grouped)} distinct Shots, "
        f"project holds {count('shots', pid)}, of them unsequenced "
        f"{count('shots', pid, ['sg_sequence', 'is', None])}")
    return mine


head("2. the bucket path on the sample project, expanded")
bucket_rows(P, kids)

# 3. The same node for Assets, which the tree groups by a list field.
head(f"3. /Project/{P}/Asset, grouped by a list field rather than by an entity")
r, kids = children(f"/Project/{P}/Asset")
out(f"  {len(kids)} children, order {marks(kids)}, kinds {sorted({k['ref']['kind'] for k in kids})}")
for k in kids:
    if k.get("path", "").endswith(NONE):
        out(f"  the bucket: {json.dumps({x: k[x] for x in ('label', 'path', 'ref')})}")

# 4. Every project on the site: does the repeat count follow the groups or the ungrouped rows?
head("4. every project, group count against bucket count against ungrouped rows")
out("  project  sequences  groups  buckets  shots  unsequenced  order")
projects = c.get("/entity/projects", params={"fields": "name", "page[size]": 500}).json()
_lib.note_from(projects)
filled, unlisted = [], []
for p in projects["data"]:
    pid = p["id"]
    r, kids = children(f"/Project/{pid}/Shot")
    if not r.ok:
        out(f"  {pid:<8} {r.status_code} {json.dumps(r.json()['errors'][0])[:150]}")
        continue
    nb = marks(kids).count("B")
    shots, none = count("shots", pid), count("shots", pid, ["sg_sequence", "is", None])
    out(f"  {pid:<8} {count('sequences', pid):<10} {len(kids) - nb:<7} {nb:<8} "
        f"{shots:<6} {none:<12} {marks(kids)[:30]}")
    if nb and none:
        filled.append((pid, kids))
    if not nb and none:
        unlisted.append((pid, kids, shots, none))

# 5. A project whose bucket has rows in it, which the sample project's has not.
head("5. a project whose bucket holds rows")
pid, kids = filled[0]
in_bucket = bucket_rows(pid, kids)

# 6. The bucket has two spellings: `_search` writes the path without the type segment.
head("6. how POST /hierarchy/_search spells the same node")
s = c.post("/hierarchy/_search", headers=JSON,
           json={"search_criteria": {"entity": {"type": "Shot", "id": in_bucket[0]}}}).json()["data"][0]
_lib.note_names(s.get("label"), s.get("path_label"))
out(f"  incremental_path {json.dumps(s['incremental_path'])}")
for path in (s["incremental_path"][2],
             f"/Project/{pid}/Shot/sg_sequence/Sequence/{NONE}"):
    r = expand(path)
    d = r.json()["data"]
    out(f"  {path} -> {r.status_code} label {d['label']!r}, "
        f"{len(d.get('children', []))} children")

# 7. The other end of the table: ungrouped rows and no bucket among the children.
head("7. a project with ungrouped Shots and no bucket in `children`")
for pid, kids, shots, none in unlisted[:1]:
    out(f"  /Project/{pid}/Shot -> {json.dumps(kids)[:200]}")
    out(f"     the project holds {shots} Shots, {none} of them unsequenced")
    r = expand(f"/Project/{pid}/Shot/sg_sequence/Sequence/{NONE}")
    d = r.json()["data"]
    out(f"  the same bucket path, asked for anyway -> {r.status_code}, label {d['label']!r}, "
        f"{len(d.get('children', []))} children, kinds "
        f"{sorted({k['ref']['kind'] for k in d.get('children', [])})}")

head("8. what the path is checked against")
for path in (f"/Project/{P}/Shot/nope/Sequence/{NONE}",
             f"/Project/{P}/Shot/sg_sequence/Sequence/999999999"):
    r = expand(path)
    out(f"  {path}")
    out(f"     -> {r.status_code} {json.dumps(r.json().get('errors', r.json().get('data')))[:220]}")

_lib.emit("064_hierarchy_expand_buckets", "\n".join(rows), env)
