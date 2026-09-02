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

_lib.emit("002_schema", "\n".join(rows), env)
