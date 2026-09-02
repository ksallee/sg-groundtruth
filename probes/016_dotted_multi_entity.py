"""Q: do dotted (deep) paths work through multi-entity fields — for reads, and for filters?"""
import json

import _lib

env = _lib.load_env()
c = _lib.client()
BBB = 70
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
PROJ = ["project", "is", {"type": "Project", "id": BBB}]
rows = []

schema = c.get("/schema/Shot/fields").json()["data"]
rows.append("data types: " + json.dumps({f: (schema.get(f, {}).get("data_type") or {}).get("value")
                                         for f in ("sg_sequence", "tasks", "assets")}))

rows.append("\n=== READ: dotted in ?fields")
r = c.get("/entity/shots", params={"filter[project.Project.id]": BBB, "page[size]": 3,
                                   "fields": "code,sg_sequence.Sequence.code,tasks.Task.content,assets.Asset.code"})
_lib.register_from(r.json())
for x in r.json()["data"][:2]:
    rows.append(f"  attributes returned: {sorted(x.get('attributes', {}))}")
rows.append("  -> single-entity (sg_sequence) present; multi-entity (tasks, assets) SILENTLY ABSENT")


def count(filt, size=500):
    r = c.post("/entity/shots/_search", headers=ARR,
               json={"filters": [PROJ] + filt, "fields": ["code"], "page": {"size": size}})
    return len(r.json()["data"]) if r.ok else f"ERR {r.status_code} {r.text[:90]}"


base = count([])
rows.append(f"\n=== FILTER: dotted through multi-entity (baseline {base} shots)")
rows.append("  negative controls — must be 0 if the filter is real:")
for label, f in [("tasks.Task.content is ZZZNOPE", [["tasks.Task.content", "is", "ZZZNOPE"]]),
                 ("assets.Asset.code is ZZZNOPE", [["assets.Asset.code", "is", "ZZZNOPE"]]),
                 ("assets.Asset.sg_asset_type is ZZZNOPE (two hops)",
                  [["assets.Asset.sg_asset_type", "is", "ZZZNOPE"]])]:
    rows.append(f"    {label:<50} -> {count(f)}")
rows.append("  positives:")
for label, f in [("tasks.Task.content is Comp", [["tasks.Task.content", "is", "Comp"]]),
                 ("assets.Asset.sg_asset_type is Character",
                  [["assets.Asset.sg_asset_type", "is", "Character"]]),
                 ("tasks is {type,id}", [["tasks", "is", {"type": "Task", "id": 3700}]])]:
    rows.append(f"    {label:<50} -> {count(f)}")

rows.append("\n=== page size")
rows.append(f"  asked 500 -> {count([], 500)} (all)   asked 150 -> {count([], 150)}   asked 50 -> {count([], 50)}")

actual = "\n".join(rows)
_lib.record("016_dotted_multi_entity", "GET /entity/shots?fields=<dotted> ; POST /entity/shots/_search",
            "Dotted paths through multi-entity fields.",
            actual,
            "READS and FILTERS differ. Reading a dotted path through a multi_entity field silently omits the "
            "key - HTTP 200, no error (single-entity 'entity' fields read fine). But FILTERING on the same "
            "path WORKS, including two hops, verified by negative controls returning 0 while positives return "
            "partial counts. So: filter through multi-entity freely; to READ those values you must query the "
            "child entity separately. Also corrects probe 005: page[size] is NOT capped at 100 - 150 returns "
            "150 and 500 returns everything.",
            env, tags=("query", "dotted-field", "multi-entity", "filter", "paging", "trap"))
print(actual)
