"""Q: can the node create its own provenance fields over REST, and what breaks when it tries twice?

Provenance currently rides as a JSON blob in `description`, which is unreadable and unqueryable. Typed
fields are the fix, but every name created here is permanent — trashed fields still collide and cannot
be listed (docs/quirks.md), so this probe uses sg_zzprobe_019_* and never a name anyone would choose.
"""
import json

import _lib

env = _lib.load_env()
c = _lib.client()
rows = []
made = []


def create(display, data_type, props=None):
    body = {"data_type": data_type,
            "properties": [{"property_name": "name", "value": display}] + (props or [])}
    r = c.post("/schema/Version/fields", json=body)
    if r.ok:
        d = r.json()
        # the programmatic name is not in the body — it is in links.self
        prog = d.get("links", {}).get("self", "").rsplit("/", 1)[-1]
        made.append(prog)
        return r.status_code, prog
    return r.status_code, r.text[:140]


rows.append("=== data types: creatable, and what each needs")
# The 400s here are missing properties, not refusals — entity/multi_entity want valid_types and
# checkbox wants default_value. Each type is tried bare first, then with what it asks for.
NEEDS = {
    "checkbox": [{"property_name": "default_value", "value": False}],
    "entity": [{"property_name": "valid_types", "value": ["Version"]}],
    "multi_entity": [{"property_name": "valid_types", "value": ["Version"]}],
    "list": [{"property_name": "valid_values", "value": ["a", "b"]}],
}
for dt in ("text", "float", "number", "checkbox", "date", "date_time", "list", "entity",
           "multi_entity", "url", "duration", "percent", "color", "footage", "image", "calculated"):
    bare_code, bare_info = create(f"zzprobe 019 bare {dt}", dt)
    line = f"  {dt:<14} bare {bare_code} {str(bare_info)[:70]}"
    if dt in NEEDS and bare_code != 201:
        ok_code, ok_info = create(f"zzprobe 019 fixed {dt}", dt, NEEDS[dt])
        line += f"\n  {'':<14} with {list(NEEDS[dt][0].values())[0]} -> {ok_code} {ok_info}"
    rows.append(line)

rows.append("\n=== multi_entity valid_types takes exactly one element")
for vt in (["Version"], ["Shot", "Asset"]):
    code, info = create(f"zzprobe 019 vt{len(vt)}", "multi_entity",
                        [{"property_name": "valid_types", "value": vt}])
    rows.append(f"  valid_types={vt} -> {code} {str(info)[:90]}")

rows.append("\n=== multi_entity holds lineage")
me = next((m for m in made if "vt1" in m), None)
if me:
    r = c.post("/entity/versions", json={"project": {"type": "Project", "id": 1180},
                                         "code": "zzprobe_019_lineage",
                                         me: [{"type": "Version", "id": 26264}]})
    rows.append(f"  write [{{Version, 26264}}] -> {r.status_code}")
    if r.ok:
        vid = r.json()["data"]["id"]
        back = c.get(f"/entity/versions/{vid}", params={"fields": me}).json()["data"]
        rows.append(f"  reads back under relationships: "
                    f"{json.dumps(back.get('relationships', {}).get(me, {}).get('data'))[:120]}")
        c.request("DELETE", f"/entity/versions/{vid}")

rows.append("\n=== display name -> programmatic name")
for display in ("zzprobe 019 Two Words", "zzprobe 019 With (Parens)", "zzprobe 019 dash-and.dot",
                "sg_zzprobe_019_already_prefixed"):
    code, info = create(display, "text")
    rows.append(f"  {display!r:<40} -> {code} {info}")

rows.append("\n=== collision: create the same display name twice")
code, first = create("zzprobe 019 collide", "text")
rows.append(f"  first  -> {code} {first}")
code, second = create("zzprobe 019 collide", "text")
rows.append(f"  second -> {code} {second}")

rows.append("\n=== can a created field be written and read back?")
probe_text = next((m for m in made if m), None)
if probe_text:
    r = c.post("/entity/versions", json={"project": {"type": "Project", "id": 1180},
                                         "code": "zzprobe_019_fieldtest", probe_text: "hello"})
    rows.append(f"  create Version with {probe_text} -> {r.status_code}")
    if r.ok:
        vid = r.json()["data"]["id"]
        rr = c.get(f"/entity/versions/{vid}", params={"fields": probe_text})
        rows.append(f"  read back -> {rr.json()['data']['attributes']}")
        c.request("DELETE", f"/entity/versions/{vid}")

rows.append("\n=== seed size: ComfyUI seeds go to 2**64-1, do number fields hold that?")
num = next((m for m in made if "number" in m), None)
flt = next((m for m in made if "float" in m), None)
for field, val, label in [(num, 2**31 - 1, "number 2**31-1"), (num, 2**63, "number 2**63"),
                          (flt, 2**63, "float 2**63")]:
    if not field:
        continue
    r = c.post("/entity/versions", json={"project": {"type": "Project", "id": 1180},
                                         "code": f"zzprobe_019_{label.replace(' ', '_')}", field: val})
    if r.ok:
        vid = r.json()["data"]["id"]
        back = c.get(f"/entity/versions/{vid}", params={"fields": field}).json()["data"]["attributes"]
        rows.append(f"  {label:<18} wrote {val} -> {r.status_code} read back {back}")
        c.request("DELETE", f"/entity/versions/{vid}")
    else:
        rows.append(f"  {label:<18} wrote {val} -> {r.status_code} {r.text[:100]}")

rows.append("\n=== delete a created field")
if made:
    create("zzprobe 019 revive", "text")
    victim = "sg_zzprobe_019_revive"
    r = c.request("DELETE", f"/schema/Version/fields/{victim}")
    rows.append(f"  DELETE {victim} -> {r.status_code} {r.text[:120]}")
    r2 = c.get(f"/schema/Version/fields/{victim}")
    rows.append(f"  GET after delete -> {r2.status_code}")
    # The real question: is the NAME freed by a delete, or still held by the trashed field?
    rows.append(f"  recreate the SAME display name -> {create('zzprobe 019 revive', 'text')}")
    listed = "sg_zzprobe_019_revive" in c.get("/schema/Version/fields").json()["data"]
    rows.append(f"  trashed field listable in /schema/Version/fields -> {listed}")

rows.append(f"\nfields burned by this probe: {sorted(set(made))}")

actual = "\n".join(rows)
_lib.record("019_create_fields", "POST /schema/Version/fields ; DELETE /schema/Version/fields/<name>",
            "Custom fields can be created over REST; names are forced to an sg_ prefix.",
            actual,
            "Almost every useful type IS creatable - the 400s are missing properties, not refusals. "
            "text/float/number/date/date_time/list/url/duration/percent/footage need nothing extra; "
            "checkbox needs default_value; entity and multi_entity need valid_types, and multi_entity "
            "takes EXACTLY ONE element (two types -> 400). Only color, image and calculated are truly "
            "rejected as invalid data_types. A multi_entity of Version round-trips lineage and reads "
            "back under relationships, which is how input-Version links should be stored rather than as "
            "JSON. Pass a DISPLAY name: the sg_ prefix is added for you, so 'sg_foo' becomes 'sg_sg_foo'. "
            "The programmatic name is NOT in the response body - take the last segment of links.self. "
            "TWO TRAPS. (1) A duplicate display name does NOT error, it silently makes <name>_1, so an "
            "idempotent ensure() MUST read /schema first and never POST-and-hope. (2) DELETE returns 204 "
            "and the field vanishes from /schema, but the NAME IS NOT FREED: recreating it 400s and the "
            "trashed field cannot be enumerated, so the collision is invisible. Also: seeds must be TEXT "
            "- a number field takes 2**31-1 but 400s at 2**63, and ComfyUI seeds go to 2**64-1.",
            env,
            tags=("schema", "write", "custom-field", "provenance", "entity-field", "trap"))
print(actual)
