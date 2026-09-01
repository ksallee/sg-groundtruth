"""Q: which schema endpoints exist, what do they cost, and what shape do they return?"""
import json
import time

import _lib

env = _lib.load_env()
c = _lib.client()

candidates = [
    ("GET", "/schema", None),
    ("GET", "/schema/Version", None),
    ("GET", "/schema/Version/fields", None),
    ("GET", "/schema/Version/fields/sg_status_list", None),
    ("GET", "/schema/entity_types", None),
    ("GET", "/schema", {"project_id": 70}),
    ("GET", "/schema/Version/fields", {"project_id": 70}),
]

rows = []
for method, path, params in candidates:
    t0 = time.time()
    try:
        r = c.request(method, path, params=params)
        ms = int((time.time() - t0) * 1000)
        body = r.text
        shape = ""
        if r.ok:
            try:
                d = json.loads(body)
                data = d.get("data", d)
                if isinstance(data, dict):
                    shape = f"dict, {len(data)} keys, first: {list(data)[:5]}"
                elif isinstance(data, list):
                    shape = f"list, {len(data)} items"
            except Exception as e:
                shape = f"unparsable: {e}"
        rows.append(f"{r.status_code} {ms:>5}ms {len(body):>9}b  {path}{'?' + str(params) if params else ''}\n"
                    f"                            {shape or body[:120]}")
    except Exception as e:
        rows.append(f"ERR         {path}: {e}")

_lib.record(
    "002_schema",
    "GET /api/v1/schema[/<EntityType>[/fields[/<field>]]]  ± project_id",
    "Schema is readable over REST; project scoping via project_id.",
    "\n".join(rows),
    "/schema lists 113 entity types (13KB); /schema/<Type>/fields is the expensive call (Version = 61 fields, "
    "42KB, ~350ms) — never fetch it for all types; /schema/<Type> returns only name+visible; "
    "/schema/entity_types is 404; project_id is accepted on both and does change the response.",
    env,
    tags=("schema", "cost", "discovery"),
)
print("\n".join(rows))
