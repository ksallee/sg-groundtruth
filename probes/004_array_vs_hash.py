"""Q: which header controls entity/multi-entity representation, and do bad field names error?"""
import json

import _lib

env = _lib.load_env()
c = _lib.client()
BBB = 70
rows = []

FIELDS = "code,entity,sg_task,user"
variants = [
    ("default (no Accept override)", {}),
    ("api3_array+json", {"Accept": "application/vnd+shotgun.api3_array+json"}),
    ("api3_hash+json", {"Accept": "application/vnd+shotgun.api3_hash+json"}),
]

for label, headers in variants:
    r = c.get("/entity/versions", params={"filter[project.Project.id]": BBB, "fields": FIELDS, "page[size]": 1},
              headers=headers)
    if not r.ok:
        rows.append(f"{r.status_code} {label}: {r.text[:150]}")
        continue
    row = r.json()["data"][0]
    rows.append(f"{r.status_code} {label}\n"
                f"      content-type: {r.headers.get('Content-Type')}\n"
                f"      attributes keys: {sorted(row.get('attributes', {}))}\n"
                f"      relationships keys: {sorted(row.get('relationships', {}))}\n"
                f"      entity rendered as: {json.dumps(row.get('relationships', {}).get('entity') or row.get('attributes', {}).get('entity'))[:180]}")

# does a bogus field error, or vanish?
r = c.get("/entity/versions", params={"filter[project.Project.id]": BBB,
                                      "fields": "code,sg_not_a_field", "page[size]": 1})
row = r.json()["data"][0] if r.ok else {}
rows.append(f"\nbogus field: HTTP {r.status_code}; attributes returned = {sorted(row.get('attributes', {}))}")

# and a bogus field in a filter?
r2 = c.get("/entity/versions", params={"filter[sg_not_a_field]": "x", "fields": "code", "page[size]": 1})
rows.append(f"bogus filter field: HTTP {r2.status_code} {r2.text[:160] if not r2.ok else 'ACCEPTED SILENTLY'}")

actual = "\n".join(rows)
_lib.record(
    "004_array_vs_hash", "GET /entity/versions with Accept variants",
    "Entity and multi-entity fields render as array or hash depending on request headers.",
    actual,
    "REST has NO array/hash negotiation - api3_array+json and api3_hash+json both 406; entity and multi-entity "
    "fields always come back under relationships as {data, links}. TRAP: a bogus name in ?fields is silently "
    "dropped (HTTP 200, field simply absent), while the same name in filter[] errors 400 - so a typo reads as "
    "'no data' instead of 'wrong field'.",
    env, tags=("query", "header", "entity-field", "error-handling"),
)
print(actual)
