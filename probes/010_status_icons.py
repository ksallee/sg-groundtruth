"""Q: where do status colours and icons live, and can they be cached from REST?"""
import json

import _lib

env = _lib.load_env()
c = _lib.client()
rows = []

r = c.get("/schema/Status/fields")
fields = sorted(r.json()["data"]) if r.ok else []
rows.append(f"{r.status_code} /schema/Status/fields -> {len(fields)} fields\n      {fields}")

if fields:
    r = c.get("/entity/statuses", params={"fields": ",".join(fields), "page[size]": 100})
    if r.ok:
        data = r.json()["data"]
        _lib.register_from(r.json())
        rows.append(f"200 /entity/statuses -> {len(data)} statuses")
        for row in data[:6]:
            a = row.get("attributes", {})
            rows.append("      " + json.dumps({k: v for k, v in a.items() if v not in (None, "", [], {})})[:260])
        # which carry an uploaded icon vs a named one
        icons = [(a.get("code"), a.get("icon"), a.get("bg_color"))
                 for a in (x.get("attributes", {}) for x in data)]
        named = [c_ for c_, i, _ in icons if isinstance(i, str)]
        uploaded = [c_ for c_, i, _ in icons if isinstance(i, dict)]
        blank = [c_ for c_, i, _ in icons if not i]
        rows.append(f"\n      icon as string (standard): {len(named)} {named[:8]}")
        rows.append(f"      icon as object (uploaded): {len(uploaded)} {uploaded[:8]}")
        rows.append(f"      icon empty:                {len(blank)} {blank[:8]}")
    else:
        rows.append(f"{r.status_code} /entity/statuses: {r.text[:200]}")

actual = "\n".join(rows)
_lib.record("010_status_icons", "GET /schema/Status/fields, GET /entity/statuses",
            "Status colour and icon come from the Status entity; three icon cases must be handled.",
            actual,
            "Status is a real queryable entity (32 rows, 11 fields) holding bg_color, name, code and a "
            "`system` flag separating built-in from custom statuses. bg_color is comma-separated RGB "
            "('25,118,27'), NOT hex. GAP: `icon` is null on all 32 statuses on this site, so the "
            "standard/custom-icon branches are unverified - set a custom icon on one status to close it.",
            env, tags=("status", "icon", "cache", "schema", "colour"))
print(actual)
