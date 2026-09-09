"""Q: which Status rows ship with a fresh site, and does anything in the schema mark them?"""
import json

import _lib

env = _lib.load_env()
c = _lib.client()
rows = []
HSH = {"Content-Type": "application/vnd+shotgun.api3_hash+json"}

schema = c.get("/schema/Status/fields").json()["data"]
rows.append(f"GET /schema/Status/fields -> {len(schema)} fields")
rows.append(f"  {'field':<20} {'data_type':<12} {'editable':<9} display name")
for f in sorted(schema):
    d = schema[f]
    rows.append(f"  {f:<20} {d['data_type']['value']:<12} "
                f"{str(d['editable']['value']):<9} {json.dumps(d['name']['value'])}")

FIELDS = "code,name,system,created_by,created_at,icon"
st = c.get("/entity/statuses", params={"fields": FIELDS, "page[size]": 200}).json()
_lib.note_from(st)

icons = c.get("/entity/icons",
              params={"fields": "display_type,image_map_key,icon_type", "page[size]": 200}).json()
by_icon = {x["id"]: x["attributes"] for x in icons["data"]}

table = []
for x in st["data"]:
    a, rel = x["attributes"], x.get("relationships", {})
    creator = (rel.get("created_by") or {}).get("data")
    icon = (rel.get("icon") or {}).get("data")
    ia = by_icon.get((icon or {}).get("id"), {})
    table.append({"id": x["id"], "code": a.get("code"), "name": a.get("name"),
                  "system": a.get("system"), "created_at": a.get("created_at"),
                  "creator": bool(creator), "icon_type": ia.get("icon_type"),
                  "display_type": ia.get("display_type"),
                  "image_map_key": ia.get("image_map_key")})
table.sort(key=lambda r: r["id"])

rows.append(f"\nGET /entity/statuses?fields={FIELDS} -> {len(table)} rows")
rows.append(f"  {'id':>4}  {'code':<8} {'system':<7} {'created_at':<22} {'created_by':<11} "
            f"{'icon_type':<17} {'display_type':<12} image_map_key")
for r in table:
    rows.append(f"  {r['id']:>4}  {r['code']:<8} {str(r['system']):<7} "
                f"{str(r['created_at']):<22} {('a person' if r['creator'] else 'null'):<11} "
                f"{str(r['icon_type']):<17} {str(r['display_type']):<12} "
                f"{json.dumps(r['image_map_key'])}")

# Two candidate marks, and whether either alone selects the same set.
no_creator = [r for r in table if not r["creator"]]
system = [r for r in table if r["system"]]
either = [r for r in table if r["system"] or not r["creator"]]
rows.append(f"\ncross-tab over {len(table)} rows")
rows.append(f"  {'':<16} {'system true':<13} system false")
for label, want in (("created_by null", False), ("created_by set", True)):
    cell = [len([r for r in table if r["creator"] is want and r["system"] is s])
            for s in (True, False)]
    rows.append(f"  {label:<16} {cell[0]:<13} {cell[1]}")
rows.append(f"  created_by null:            {len(no_creator)}  {[r['code'] for r in no_creator]}")
rows.append(f"  system true:                {len(system)}  {[r['code'] for r in system]}")
rows.append(f"  either:                     {len(either)}  {[r['code'] for r in either]}")
rows.append(f"  system true and created_by set: "
            f"{[r['code'] for r in system if r['creator']]}")
rows.append(f"  created_by null with a created_at: "
            f"{[(r['code'], r['created_at']) for r in no_creator if r['created_at']]}")
lo, hi = min(r["id"] for r in no_creator), max(r["id"] for r in no_creator)
held = {r["id"] for r in no_creator}
rows.append(f"  id range of the created_by null set: {lo}-{hi}, "
            f"ids in that range no row holds: {sorted(set(range(lo, hi + 1)) - held)}")
rows.append(f"  lowest id with a creator: {min((r['id'] for r in table if r['creator']), default=None)}")

# A gap inside the block is either a row somebody deleted or an id never used, and the two mean
# different things for the count.
ret = c.get("/entity/statuses", params={"fields": "code,system,created_by",
                                        "options[return_only]": "retired", "page[size]": 200})
retired = ret.json().get("data", []) if ret.ok else []
_lib.note_from(ret.json() if ret.ok else {})
rows.append(f"  GET /entity/statuses?options[return_only]=retired -> {ret.status_code} "
            f"{len(retired)} rows")
for x in retired:
    a, rel = x["attributes"], x.get("relationships", {})
    rows.append(f"    {x['id']:>4}  {str(a.get('code')):<8} system {str(a.get('system')):<7} "
                f"created_by {'a person' if (rel.get('created_by') or {}).get('data') else 'null'}")
seen = held | {x["id"] for x in retired}
rows.append(f"  ids below the lowest id with a creator that no row holds, live or retired: "
            f"{sorted(set(range(1, min(r['id'] for r in table if r['creator']))) - seen)}")

# Can a caller select the set in one call, or does it have to be done client-side?
rows.append("\nthe same two marks as filters, hash Content-Type (probe 004)")
for label, filters in (
        ("created_by is null", {"logical_operator": "and",
                                "conditions": [["created_by", "is", None]]}),
        ("system is true", {"logical_operator": "and",
                            "conditions": [["system", "is", True]]}),
        ("either", {"logical_operator": "or",
                    "conditions": [["created_by", "is", None], ["system", "is", True]]})):
    r = c.post("/entity/statuses/_search", headers=HSH,
               data=json.dumps({"filters": filters, "fields": "code", "page": {"size": 200}}))
    body = r.json()
    got = (f"{len(body['data'])} rows" if r.ok
           else json.dumps(body.get("errors", body)))
    rows.append(f"  {label:<20} -> {r.status_code} {got}")

# The stock renderings the shipped set points at. The sprite behind an image_map_key and its
# unauthenticated reachability are probe 010; this is only which key each shipped status uses.
rows.append(f"\nthe {len(either)} shipped rows by rendering")
for r in either:
    rows.append(f"  {r['code']:<8} {str(r['name']):<16} {str(r['icon_type']):<17} "
                f"{str(r['display_type']):<12} {json.dumps(r['image_map_key'])}")
keys = [r["image_map_key"] for r in either]
rows.append(f"  distinct image_map_key over the shipped set: {len(set(keys))} of {len(keys)}, "
            f"shared: {sorted({k for k in keys if keys.count(k) > 1})}")

_lib.emit("061_shipped_statuses", "\n".join(rows), env)
