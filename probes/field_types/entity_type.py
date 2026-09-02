"""Q: does an `entity_type` field hold a schema name or a REST slug, and is the value validated?

Probed on the five stock fields carrying data_type `entity_type`, found by sweeping /schema/<Type>/fields
across every type in /schema. Only ActionMenuItem.entity_type is editable, so it carries the write half.
Never creates a schema field: a name is burned permanently (probe 019).

The crux is the write block. A generic client reads this field to decide which endpoint to call next, so
whether the API refuses a REST slug or a made-up type decides if the field can be trusted unvalidated.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _lib  # noqa: E402

env = _lib.load_env()
c = _lib.client()
PROJECT = _lib.sample_projects(c, env)[0]
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
FIELD = "entity_type"
rows = []


def err(r):
    """Whole errors[] object, source included. Truncating it throws away the operator vocabulary."""
    try:
        return json.dumps(r.json().get("errors", r.json()), indent=1)
    except ValueError:
        return r.text


def props(entity, field):
    d = c.get(f"/schema/{entity}/fields/{field}").json()["data"]
    flat = {k: (v.get("value") if isinstance(v, dict) else v) for k, v in d.items()}
    flat["properties"] = {k: v.get("value") for k, v in d.get("properties", {}).items()}
    return flat


def search(entity, filt, fields=None, size=500):
    body = {"filters": filt, "fields": fields or ["id"], "page": {"size": size}}
    r = c.post(f"/entity/{entity}/_search", headers=ARR, json=body)
    return (len(r.json()["data"]), r.json()["data"]) if r.ok else (f"ERR {r.status_code}", err(r))


TYPES = sorted(c.get("/schema").json()["data"].keys())
rows.append(f"=== sweep: every field of data_type entity_type across {len(TYPES)} entity types in /schema")
CARRIERS = []
for t in TYPES:
    r = c.get(f"/schema/{t}/fields")
    if not r.ok:
        continue
    for fname, fd in r.json()["data"].items():
        if fd.get("data_type", {}).get("value") == "entity_type":
            CARRIERS.append((t, fname))
for t, fname in CARRIERS:
    p = props(t, fname)
    rows.append(f"  {t}.{fname:12} editable={p['editable']} mandatory={p['mandatory']} "
                f"unique={p['unique']} properties={sorted(p['properties'])} "
                f"default_value={p['properties'].get('default_value')!r}")
rows.append("  no valid_values, no valid_types: the schema names no legal set for this type")

rows.append("\n=== read: shape, and schema name vs REST slug")
for slug, ent in (("steps", "Step"), ("task_templates", "TaskTemplate"),
                  ("permission_rule_sets", "PermissionRuleSet"), ("pages", "Page"),
                  ("action_menu_items", "ActionMenuItem")):
    r = c.get(f"/entity/{slug}", params={"fields": f"code,{FIELD}", "page[size]": 500})
    if not r.ok:
        rows.append(f"  {slug}: {r.status_code} {err(r)}")
        continue
    data = r.json()["data"]
    _lib.note_from(data)
    seen = {}
    for d in data:
        v = d["attributes"].get(FIELD)
        seen[repr(v)] = seen.get(repr(v), 0) + 1
    top = dict(sorted(seen.items(), key=lambda kv: -kv[1])[:8])
    rows.append(f"  {slug:22} {len(data):4} rows, {len(seen)} distinct; top: {json.dumps(top)}")
    if data:
        rows.append(f"      row: {json.dumps(data[0])}")
    kinds = {type(d["attributes"].get(FIELD)).__name__ for d in data}
    rows.append(f"      python types: {kinds}   in /schema as a real type: "
                f"{ {k.strip(chr(39)) in TYPES for k in seen if k != 'None'} }")

rows.append("\n=== the API enumerates its own operators (probe 017)")
n, e = search("steps", [[FIELD, "definitely_not_an_operator", None]])
rows.append(f"  Step.{FIELD} definitely_not_an_operator null -> {n}")
rows.append(e if isinstance(e, str) else "")

base, _ = search("steps", [])
rows.append(f"\n=== filter, on Step  (baseline {base} steps site-wide)")
for label, filt in [
    ("is 'Shot'",                        [[FIELD, "is", "Shot"]]),
    ("is 'shot' (wrong case)",           [[FIELD, "is", "shot"]]),
    ("is 'shots' (REST slug)",           [[FIELD, "is", "shots"]]),
    ("is 'ZzprobeNotAType' (neg ctrl)",  [[FIELD, "is", "ZzprobeNotAType"]]),
    ("is 'Version' (real type, no rows)", [[FIELD, "is", "Version"]]),
    ("is null",                          [[FIELD, "is", None]]),
    ("is '' (empty string)",             [[FIELD, "is", ""]]),
    ("is_not 'Shot'",                    [[FIELD, "is_not", "Shot"]]),
    ("is_not null",                      [[FIELD, "is_not", None]]),
    ("in ['Shot', 'Asset']",             [[FIELD, "in", ["Shot", "Asset"]]]),
    ("in ['Shot']",                      [[FIELD, "in", ["Shot"]]]),
    ("in ['Shot', 'ZzprobeNotAType']",   [[FIELD, "in", ["Shot", "ZzprobeNotAType"]]]),
    ("in 'Shot' (bare, not a list)",     [[FIELD, "in", "Shot"]]),
    ("in ['ZzprobeNotAType'] (neg ctrl)", [[FIELD, "in", ["ZzprobeNotAType"]]]),
    ("not_in ['Shot']",                  [[FIELD, "not_in", ["Shot"]]]),
    ("in [{'type':'Shot','id':1}] (entity hash)", [[FIELD, "in", [{"type": "Shot", "id": 1}]]]),
    ("is {'type':'Shot','id':1} (entity hash)", [[FIELD, "is", {"type": "Shot", "id": 1}]]),
    ("contains 'ho'",                    [[FIELD, "contains", "ho"]]),
    ("starts_with 'Sh'",                 [[FIELD, "starts_with", "Sh"]]),
    ("name_is 'Shot'",                   [[FIELD, "name_is", "Shot"]]),
    ("type_is 'Shot'",                   [[FIELD, "type_is", "Shot"]]),
]:
    n, e = search("steps", filt)
    flag = "  <- returns baseline" if isinstance(n, int) and n == base else ""
    rows.append(f"  {label:<44} -> {n}{flag}")
    if isinstance(n, str):
        rows.append(f"      {e}")

if not _lib.writes_allowed():
    rows.append("\n(read-only run; pass --write for the write / clear half)")
else:
    # A probe leaves no trace: every ActionMenuItem it makes is deleted on the way out.
    with _lib.Created(c) as made:
        SANDBOX = _lib.sandbox_id(c, env)
        rows.append("\n=== write, on ActionMenuItem.entity_type, the only editable field of this type")
        r = c.post("/entity/action_menu_items",
                   json={"title": "zzprobe_entity_type", "url": "https://example.com/zzprobe",
                         "projects": [{"type": "Project", "id": SANDBOX}]})
        aid = made.add("action_menu_items", r.json()["data"]["id"]) if r.ok else None
        fresh = c.get(f"/entity/action_menu_items/{aid}",
                      params={"fields": FIELD}).json()["data"]["attributes"]
        rows.append(f"  create with the field omitted -> {r.status_code} id={aid} "
                    f"reads {json.dumps(fresh)}")

        def put(value):
            rr = c.request("PUT", f"/entity/action_menu_items/{aid}", json={FIELD: value},
                           headers={"Content-Type": "application/json"})
            if not rr.ok:
                return rr.status_code, err(rr)
            back = c.get(f"/entity/action_menu_items/{aid}",
                         params={"fields": FIELD}).json()["data"]["attributes"]
            return rr.status_code, f"read back {json.dumps(back)}"

        DISABLED = next(f"CustomEntity{n:02d}" for n in range(1, 100)
                        if f"CustomEntity{n:02d}" not in TYPES)
        for label, value in [
            ("schema name 'Shot'",                      "Shot"),
            ("lowercase 'shot'",                        "shot"),
            ("uppercase 'SHOT'",                        "SHOT"),
            ("REST slug 'shots'",                       "shots"),
            ("REST slug 'action_menu_items'",           "action_menu_items"),
            ("nonexistent type 'ZzprobeNotAType'",      "ZzprobeNotAType"),
            ("enabled 'CustomEntity19'",                "CustomEntity19"),
            (f"disabled '{DISABLED}' (not in /schema)", DISABLED),
            ("dotted 'PermissionRuleSet.HumanUser'",    "PermissionRuleSet.HumanUser"),
            ("connection 'CustomEntity29_sg_scene_Connection'",
             "CustomEntity29_sg_scene_Connection"),
            ("display name 'Shots' (plural label)",     "Shots"),
            ("an entity hash {'type':'Shot','id':1}",   {"type": "Shot", "id": 1}),
            ("a list ['Shot', 'Asset']",                ["Shot", "Asset"]),
            ("an integer 0",                            0),
        ]:
            code, info = put(value)
            rows.append(f"  {label:<48} -> {code} {info}")

        rows.append("\n=== is a junk value readable back and findable?")
        code, info = put("ZzprobeNotAType")
        n, _ = search("action_menu_items", [["id", "is", aid], [FIELD, "is", "ZzprobeNotAType"]])
        rows.append(f"  set 'ZzprobeNotAType' -> {code} {info}; matched by is 'ZzprobeNotAType' -> {n}")

        rows.append("\n=== clear  (the row is matched by id, so 1 = matched, 0 = not)")
        for label, value in [("set 'Shot' (control)", "Shot"), ("null", None), ('empty string ""', "")]:
            code, info = put(value)
            n, _ = search("action_menu_items", [["id", "is", aid], [FIELD, "is", None]])
            n2, _ = search("action_menu_items", [["id", "is", aid], [FIELD, "is", ""]])
            rows.append(f"  {label:<22} -> {code} {info}")
            rows.append(f"      matched by  is None -> {n}   is '' -> {n2}")

        rows.append("\n=== create with the value set, rather than PUT")
        for label, value in [("'Asset'", "Asset"), ("'ZzprobeNotAType'", "ZzprobeNotAType")]:
            rr = c.post("/entity/action_menu_items",
                        json={"title": f"zzprobe_entity_type_{label.strip(chr(39))}",
                              "url": "https://example.com/zzprobe", FIELD: value,
                              "projects": [{"type": "Project", "id": SANDBOX}]})
            if rr.ok:
                made.add("action_menu_items", rr.json()["data"]["id"])
                rows.append(f"  create {label:<20} -> {rr.status_code} "
                            f"reads {json.dumps(rr.json()['data']['attributes'][FIELD])}")
            else:
                rows.append(f"  create {label:<20} -> {rr.status_code} {err(rr)}")

        rows.append("\n=== a read-only one: does the API say so?")
        st = c.get("/entity/steps", params={"fields": FIELD, "page[size]": 1}).json()["data"][0]["id"]
        rr = c.request("PUT", f"/entity/steps/{st}", json={FIELD: "Asset"},
                       headers={"Content-Type": "application/json"})
        rows.append(f"  PUT Step.{FIELD} = 'Asset' -> {rr.status_code} "
                    f"{err(rr) if not rr.ok else 'ACCEPTED'}")

actual = "\n".join(rows)
_lib.emit("field_types/entity_type", actual, env)
