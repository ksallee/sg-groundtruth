"""Q: which header controls entity/multi-entity representation, and do bad field names error?"""
import json

import _lib

env = _lib.load_env()
c = _lib.client()
PROJECT = _lib.sample_projects(c, env)[0]
rows = []

FIELDS = "code,entity,sg_task,user"
variants = [
    ("default (no Accept override)", {}),
    ("api3_array+json", {"Accept": "application/vnd+shotgun.api3_array+json"}),
    ("api3_hash+json", {"Accept": "application/vnd+shotgun.api3_hash+json"}),
]

for label, headers in variants:
    r = c.get("/entity/versions", params={"filter[project.Project.id]": PROJECT, "fields": FIELDS, "page[size]": 1},
              headers=headers)
    if not r.ok:
        rows.append(f"{r.status_code} {label}: {r.text!r}")
        continue
    _lib.note_from(r.json())
    row = r.json()["data"][0]
    rows.append(f"{r.status_code} {label}\n"
                f"      content-type: {r.headers.get('Content-Type')}\n"
                f"      attributes keys: {sorted(row.get('attributes', {}))}\n"
                f"      relationships keys: {sorted(row.get('relationships', {}))}\n"
                f"      entity rendered as: {json.dumps(row.get('relationships', {}).get('entity') or row.get('attributes', {}).get('entity'))[:180]}")

# Accept never produced a second rendering to compare against, so send the same vendor types where
# they belong: as the Content-Type of the POST _search read. Each vendor type selects the filter
# syntax of the request body, so the hash form needs its own filter shape.
TRIPLE = [["project", "is", {"type": "Project", "id": PROJECT}]]
SEARCH = [
    ("api3_array, list of triples", "application/vnd+shotgun.api3_array+json", TRIPLE),
    ("api3_hash, same list of triples", "application/vnd+shotgun.api3_hash+json", TRIPLE),
    ("api3_hash, wrapped in a logical operator", "application/vnd+shotgun.api3_hash+json",
     {"logical_operator": "and", "conditions": TRIPLE}),
    ("api3_hash, JSON:API-style condition objects", "application/vnd+shotgun.api3_hash+json",
     {"logical_operator": "and",
      "conditions": [{"path": "project", "relation": "is",
                      "values": [{"type": "Project", "id": PROJECT}]}]}),
]
rows.append("")
shapes = {}
for label, ctype, filters in SEARCH:
    r = c.post("/entity/versions/_search", headers={"Content-Type": ctype},
               json={"filters": filters, "fields": FIELDS, "page": {"size": 1}})
    if not r.ok:
        rows.append(f"{r.status_code} POST _search {label}: {json.dumps(r.json())}")
        continue
    _lib.note_from(r.json())
    row = r.json()["data"][0]
    shapes[label] = json.dumps(row, sort_keys=True)
    rows.append(f"{r.status_code} POST _search {label}\n"
                f"      content-type: {r.headers.get('Content-Type')}\n"
                f"      attributes keys: {sorted(row.get('attributes', {}))}\n"
                f"      relationships keys: {sorted(row.get('relationships', {}))}\n"
                f"      entity rendered as: {json.dumps(row.get('relationships', {}).get('entity') or row.get('attributes', {}).get('entity'))[:180]}")
rows.append(f"array row == hash row, byte for byte: {len(set(shapes.values())) == 1} "
            f"(over {len(shapes)} rows that returned 200)")
rows.append("")

# does a bogus field error, or vanish?
r = c.get("/entity/versions", params={"filter[project.Project.id]": PROJECT,
                                      "fields": "code,sg_not_a_field", "page[size]": 1})
row = r.json()["data"][0] if r.ok else {}
rows.append(f"\nbogus field: HTTP {r.status_code}; attributes returned = {sorted(row.get('attributes', {}))}")

# and a bogus field in a filter?
r2 = c.get("/entity/versions", params={"filter[sg_not_a_field]": "x", "fields": "code", "page[size]": 1})
rows.append(f"bogus filter field: HTTP {r2.status_code} {r2.text if not r2.ok else 'ACCEPTED SILENTLY'}")

actual = "\n".join(rows)
_lib.emit("004_array_vs_hash", actual, env)
