"""Q: which settings does a custom field take at creation, where does each read back, and which can
be changed afterwards?

Settings: description, `unique`, a default value, a list's and a status list's valid values, and the
valid types of an entity and a multi_entity link, with two types as well as one.

Writes only, behind `--write`, on Version. Each field is created with the fullest body first and a
smaller one after each refusal, so one name answers creation, read-back and every update. A refused
create is followed by a read of the name it would have made, to see that nothing was created.
Statuses sent are ones the site already has, read from Version `sg_status_list`: a code that does not
exist is never sent, because what the server would do with it is unknown.

Seven names are spent, `sg_zzprobe_116_*`, each retired as soon as its section ends.
"""
import json

import _lib

env = _lib.load_env()
c = _lib.client()
out = []
TYPE, PREFIX = "Version", "sg_zzprobe_116_"
made = []

if not _lib.writes_allowed():
    raise SystemExit("probe 116 only writes; run with --write")


def errs(r):
    if not r.content:
        return "(empty body)"
    try:
        j = r.json()
    except ValueError:
        return r.text[:400]
    if isinstance(j, dict) and "errors" in j:
        return json.dumps([{k: e.get(k) for k in ("status", "code", "title", "source", "detail")
                            if e.get(k) is not None} for e in j["errors"]])
    return ""


def head(t):
    out.append(f"\n\n===== {t}")


def prop(**kv):
    return [{"property_name": k, "value": v} for k, v in kv.items()]


def path(name):
    assert name.startswith(PREFIX), name
    return f"/schema/{TYPE}/fields/{name}"


def rec(name):
    r = c.get(path(name))
    return r.json()["data"] if r.status_code == 200 else None


def at(d, dotted):
    for k in dotted.split("."):
        d = (d or {}).get(k)
    return d


def create(display, attempts):
    """Each attempt is (label, body). Stops at the first 201 and returns the programmatic name."""
    guess = "sg_" + display.replace(" ", "_")
    for label, body in attempts:
        r = c.post(f"/schema/{TYPE}/fields", json=body)
        out.append(f"POST /schema/{TYPE}/fields  {json.dumps(body)}\n  [{label}] -> {r.status_code}  {errs(r)}")
        if r.status_code == 201:
            name = r.json()["links"]["self"].rsplit("/", 1)[-1]
            made.append(name)
            out.append(f"  created {name}; body keys {sorted(r.json()['data'])}")
            return name
        out.append(f"  {guess} exists after the refusal: {c.get(path(guess)).status_code == 200}")
    return None


def show(name, *paths):
    d = rec(name)
    for p in paths:
        out.append(f"  reads {p}: {json.dumps(at(d, p))}")


def update(name, label, body, *watch):
    before = rec(name)
    r = c.put(path(name), json=body)
    after = rec(name)
    line = f"PUT  {json.dumps(body)}\n  [{label}] -> {r.status_code}  {errs(r)}"
    for p in watch:
        b, a = at(before, p), at(after, p)
        line += f"\n  {p}: {'changed to ' + json.dumps(a) if a != b else 'unchanged, ' + json.dumps(a)}"
    out.append(line)


def retire(name):
    """Straight after its section, so a default or a unique flag is live for seconds, not the run."""
    r = c.delete(path(name))
    out.append(f"DELETE {name} -> {r.status_code}; live after: {rec(name) is not None}")
    made.remove(name)


try:
    # --- list ---------------------------------------------------------------------------------
    head("list: created with description, valid_values and default_value")
    D = "zzprobe 116 list"
    full = dict(name=D, description="zzprobe 116 list desc", valid_values=["alpha", "beta", "gamma"],
                default_value="beta")
    n = create(D, [
        ("all four", {"data_type": "list", "properties": prop(**full)}),
        ("no default_value", {"data_type": "list", "properties": prop(
            **{k: v for k, v in full.items() if k != "default_value"})}),
        ("no valid_values either", {"data_type": "list", "properties": prop(
            name=D, description=full["description"])}),
        ("name alone", {"data_type": "list", "properties": prop(name=D)}),
    ])
    if n:
        out.append("  the whole record:\n" + json.dumps(rec(n), indent=1))
        head("list: updates")
        V, DV = "properties.valid_values", "properties.default_value"
        update(n, "valid_values, one added", {"properties": prop(
            valid_values=["alpha", "beta", "gamma", "delta"])}, V)
        update(n, "valid_values, two removed", {"properties": prop(valid_values=["alpha", "beta"])}, V, DV)
        update(n, "default_value, a valid value", {"properties": prop(default_value="alpha")}, DV)
        update(n, "default_value, not a valid value", {"properties": prop(default_value="zzz")}, DV, V)
        update(n, "valid_values without the default", {"properties": prop(valid_values=["beta"])}, V, DV)
        update(n, "default_value null", {"properties": prop(default_value=None)}, DV)
        update(n, "valid_values, a string not a list", {"properties": prop(valid_values="beta,gamma")}, V)
        update(n, "valid_values empty", {"properties": prop(valid_values=[])}, V)
        update(n, "description", {"properties": prop(description="zzprobe 116 list desc 2")}, "description")
        update(n, "name", {"properties": prop(name="zzprobe 116 list renamed")}, "name")
        out.append(f"  old path still answers: {c.get(path(n)).status_code}; listed under: "
                   f"{[k for k in c.get(f'/schema/{TYPE}/fields').json()['data'] if 'zzprobe_116_list' in k]}")
        update(n, "unique as a property", {"properties": prop(unique=True)}, "unique")
        update(n, "unique at the top level", {"unique": True}, "unique")
        update(n, "unique at the top level, with properties", {"unique": True, "properties": prop(
            description="zzprobe 116 list desc 3")}, "unique", "description")
        update(n, "summary_default", {"properties": prop(summary_default="count")},
               "properties.summary_default")
        update(n, "custom_metadata", {"properties": prop(custom_metadata="zzprobe 116 meta")},
               "custom_metadata")
        update(n, "an empty properties list", {"properties": []})
        update(n, "no properties key", {})
        retire(n)

    # --- text ---------------------------------------------------------------------------------
    head("text: created with description, unique and default_value")
    D = "zzprobe 116 text"
    n = create(D, [
        # `unique` is never sent with a default: every new Version would then hold the same value.
        ("unique as a property", {"data_type": "text", "properties": prop(
            name=D, description="zzprobe 116 text desc", unique=True)}),
        ("unique at the top level", {"data_type": "text", "unique": True, "properties": prop(
            name=D, description="zzprobe 116 text desc")}),
        ("name and description", {"data_type": "text", "properties": prop(
            name=D, description="zzprobe 116 text desc")}),
    ])
    if n:
        show(n, "unique", "description", "properties.default_value", "mandatory")
        out.append(f"  properties keys: {sorted(rec(n)['properties'])}")
        head("text: updates")
        was_unique = at(rec(n), "unique.value")
        update(n, "unique as a property, the other value", {"properties": prop(unique=not was_unique)},
               "unique")
        if not at(rec(n), "unique.value"):
            update(n, "default_value", {"properties": prop(default_value="dflt2")},
                   "properties.default_value")
            update(n, "default_value null", {"properties": prop(default_value=None)},
                   "properties.default_value")
        retire(n)

    # --- checkbox -----------------------------------------------------------------------------
    head("checkbox: created with default_value true")
    D = "zzprobe 116 checkbox"
    n = create(D, [("default_value true", {"data_type": "checkbox", "properties": prop(
        name=D, default_value=True)})])
    if n:
        show(n, "properties.default_value")
        head("checkbox: updates")
        DV = "properties.default_value"
        update(n, "default_value false", {"properties": prop(default_value=False)}, DV)
        update(n, "default_value true", {"properties": prop(default_value=True)}, DV)
        update(n, "default_value null", {"properties": prop(default_value=None)}, DV)
        update(n, "default_value the string \"false\"", {"properties": prop(default_value="false")}, DV)
        retire(n)

    # --- status_list --------------------------------------------------------------------------
    sv = c.get("/schema/Version/fields/sg_status_list").json()["data"]["properties"]
    codes = sv["valid_values"]["value"]
    a, b, d3, d4 = codes[0], codes[1], codes[2], codes[3]
    out.append(f"\nstatus codes used, all existing on the site: {[a, b, d3, d4]}")
    head("status_list: name alone")
    n0 = create("zzprobe 116 status bare", [("name alone", {"data_type": "status_list", "properties": prop(
        name="zzprobe 116 status bare")})])
    if n0:
        p = rec(n0)["properties"]
        out.append(f"  properties keys: {sorted(p)}")
        out.append(f"  valid_values: {len(p['valid_values']['value'])} codes, the site has "
                   f"{len(codes)} on Version sg_status_list; default_value "
                   f"{json.dumps(p['default_value'])}")
    head("status_list: created with valid_values and default_value")
    D = "zzprobe 116 status"
    n = create(D, [
        ("both", {"data_type": "status_list", "properties": prop(
            name=D, valid_values=[a, b, d3], default_value=b)}),
        ("valid_values alone", {"data_type": "status_list", "properties": prop(
            name=D, valid_values=[a, b, d3])}),
    ])
    if n:
        show(n, "properties.valid_values", "properties.default_value")
        out.append(f"  properties keys: {sorted(rec(n)['properties'])}")
    n = n or n0
    if n:
        head(f"status_list: updates, on {n}")
        V, DV = "properties.valid_values", "properties.default_value"
        update(n, "valid_values, set to three", {"properties": prop(valid_values=[a, b, d3])}, V, DV)
        update(n, "valid_values, one added", {"properties": prop(valid_values=[a, b, d3, d4])}, V)
        update(n, "valid_values, two removed", {"properties": prop(valid_values=[a, b])}, V, DV)
        update(n, "default_value, in valid_values", {"properties": prop(default_value=a)}, DV)
        update(n, "default_value, a status not in valid_values", {"properties": prop(default_value=d4)}, DV, V)
        update(n, "valid_values without the default", {"properties": prop(valid_values=[b])}, V, DV)
        update(n, "default_value null", {"properties": prop(default_value=None)}, DV)

    # --- entity and multi_entity --------------------------------------------------------------
    for dt in ("entity", "multi_entity"):
        head(f"{dt}: created with two valid_types, then one")
        D = f"zzprobe 116 {dt.replace('_', ' ')}"
        n = create(D, [
            ("two types", {"data_type": dt, "properties": prop(name=D, valid_types=["Shot", "Asset"])}),
            ("one type", {"data_type": dt, "properties": prop(name=D, valid_types=["Shot"])}),
        ])
        if n:
            show(n, "properties.valid_types")
            out.append(f"  properties keys: {sorted(rec(n)['properties'])}")
            VT = "properties.valid_types"
            head(f"{dt}: updates")
            update(n, "valid_types, one added", {"properties": prop(valid_types=["Shot", "Asset"])}, VT)
            update(n, "valid_types, replaced by another", {"properties": prop(valid_types=["Asset"])}, VT)
            update(n, "valid_types, the one it holds", {"properties": prop(valid_types=["Shot"])}, VT)
            update(n, "description", {"properties": prop(description="zzprobe 116 desc")}, "description")
            retire(n)
finally:
    head("retire")
    for name in list(made):
        retire(name)
    left = [k for k in c.get(f"/schema/{TYPE}/fields").json()["data"] if "zzprobe_116" in k]
    out.append(f"zzprobe_116 fields still listed on {TYPE}: {left}")

_lib.emit("116_field_settings_create_update", "\n".join(out), env)
