"""Q: can a field's description be cleared, can its lists be emptied, does one PUT carry several
properties, is the order of an entity field's valid types kept, and what does a value the site
does not know answer?

The fields are three that probe 116 spent on Version, `sg_zzprobe_116_list`, `_status` and
`_entity`: each is revived, written, and retired again in a `finally`. A revived field is live on
the site for the length of its section, so the three are done one at a time.

The unknown status code is `zzq`. Probe 116 did not send one because the server might have made a
Status of it. This probe lists the site's statuses before and after, and deletes a `zzq` Status if
one appeared.

**The entity section is not safe to run again**, so it is behind `--entity` as well. Two things the
run of 2026-11-10 showed, neither known when it was written:

- Every type added to an entity field's `valid_types` makes a field on that type, and removing the
  type retires it. The run spent `Sequence.sg_versions_1`, `Task.sg_versions_1` and
  `Shot.sg_versions_3` that way. The plan was to spend no name.
- The last write, `valid_types: ["shot"]`, answered 500 and left the field retired, with `["shot"]`
  stored. Whether a revive of it answers at all is unmeasured, and a broken field live on Version
  is not something to find out on a site people use.

Writes only, behind `--write`.
"""
import json
import sys

import _lib

env = _lib.load_env()
c = _lib.client()
out = []
TYPE, PREFIX = "Version", "sg_zzprobe_116_"
BASE = f"/schema/{TYPE}/fields"
LIST, STATUS, ENTITY = PREFIX + "list", PREFIX + "status", PREFIX + "entity"
NO_STATUS, NO_TYPE = "zzq", "ZzNoSuchType"
live_now = []

if not _lib.writes_allowed():
    raise SystemExit("probe 121 only writes; run with --write")


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


def prop(*pairs):
    """Pairs, not keywords: the order of the properties in the request is one of the questions."""
    return {"properties": [{"property_name": k, "value": v} for k, v in pairs]}


def path(name):
    assert name.startswith(PREFIX), name
    return f"{BASE}/{name}"


def rec(name):
    r = c.get(path(name))
    return r.json()["data"] if r.status_code == 200 else None


def at(d, dotted):
    for k in dotted.split("."):
        d = (d or {}).get(k)
    return d


def update(name, label, body, *watch):
    before = rec(name)
    r = c.put(path(name), json=body)
    after = rec(name)
    line = f"PUT  {json.dumps(body)}\n  [{label}] -> {r.status_code}  {errs(r)}"
    for p in watch:
        b, a = at(before, p + ".value"), at(after, p + ".value")
        line += f"\n  {p}: {'changed to ' + json.dumps(a) if a != b else 'unchanged, ' + json.dumps(a)}"
    if r.status_code == 200:
        body_says = {p: at(r.json().get("data"), p + ".value") for p in watch}
        now = {p: at(after, p + ".value") for p in watch}
        if body_says != now:
            line += f"\n  the 200 body differs from the read: {json.dumps(body_says)}"
    out.append(line)
    return r


def revive(name):
    if rec(name) is not None:
        raise SystemExit(f"{name} is live; probe 116 leaves it retired")
    r = c.post(path(name), json={"revive": True})
    out.append(f"POST {name} revive -> {r.status_code}")
    if r.status_code != 204:
        raise SystemExit(f"revive of {name} answered {r.status_code}: {errs(r)}")
    live_now.append(name)
    d = rec(name)
    out.append("  as revived: " + json.dumps({
        "data_type": at(d, "data_type.value"), "name": at(d, "name.value"),
        "description": at(d, "description.value"),
        "properties": {k: v.get("value") for k, v in d["properties"].items()}}))


def retire(name):
    r = c.delete(path(name))
    out.append(f"DELETE {name} -> {r.status_code}; live after: {rec(name) is not None}")
    if name in live_now:
        live_now.remove(name)


def statuses():
    r = c.get("/entity/statuses", params={"fields": "code", "page[size]": 500}).json()
    return {s["attributes"]["code"]: s["id"] for s in r["data"]}


V, DV, VT = "properties.valid_values", "properties.default_value", "properties.valid_types"
status_before = statuses()
assert NO_STATUS not in status_before, NO_STATUS
out.append(f"statuses on the site before: {len(status_before)}; {NO_STATUS!r} among them: False")
out.append(f"entity types named {NO_TYPE!r}: {NO_TYPE in c.get('/schema').json()['data']}")
d = c.get(f"{BASE}/code").json()["data"]
out.append(f"a stock field with no description, Version.code, reads description {json.dumps(d['description'])}")

try:
    # --- list: description, name, emptying, several properties ------------------------------------
    head("list: revive")
    revive(LIST)
    try:
        n = LIST
        name0 = at(rec(n), "name.value")

        head("1. clearing a description")
        update(n, "description, non-empty", prop(("description", "zzprobe 121 desc")), "description")
        update(n, 'description ""', prop(("description", "")), "description")
        update(n, "description null", prop(("description", None)), "description")
        update(n, "description, no value key", {"properties": [{"property_name": "description"}]},
               "description")
        update(n, "description, a single space", prop(("description", " ")), "description")
        update(n, "description, non-empty again", prop(("description", "zzprobe 121 desc")), "description")
        update(n, "description, two spaces", prop(("description", "  ")), "description")
        update(n, "description, a space around text", prop(("description", " zzprobe 121 pad ")),
               "description")

        head("1. clearing a display name")
        update(n, 'name ""', prop(("name", "")), "name")
        update(n, "name null", prop(("name", None)), "name")
        update(n, "name, a single space", prop(("name", " ")), "name")
        if at(rec(n), "name.value") != name0:
            update(n, "name restored", prop(("name", name0)), "name")

        head("2. emptying a list's valid_values")
        update(n, "valid_values, three", prop(("valid_values", ["alpha", "beta", "gamma"])), V, DV)
        update(n, "default_value, a valid value", prop(("default_value", "alpha")), DV)
        update(n, "valid_values []", prop(("valid_values", [])), V, DV)
        update(n, "valid_values null", prop(("valid_values", None)), V, DV)

        head("6. list: a default that is not a valid value, and a repeated value")
        update(n, "default_value, not a valid value", prop(("default_value", "zzz")), DV, V)
        update(n, "valid_values, one repeated", prop(("valid_values", ["alpha", "alpha", "beta"])), V, DV)
        update(n, "valid_values, three again", prop(("valid_values", ["alpha", "beta", "gamma"])), V, DV)

        head("3. list: valid_values and default_value in one PUT")
        update(n, "valid_values first; the default is only in the new values",
               prop(("valid_values", ["p", "q"]), ("default_value", "q")), V, DV)
        update(n, "default_value first; the default is only in the new values",
               prop(("default_value", "r"), ("valid_values", ["r", "s"])), V, DV)
        update(n, "default_value first; the default is only in the old values",
               prop(("default_value", "s"), ("valid_values", ["t", "u"])), V, DV)

        head("3. one PUT, one property refused")
        update(n, "description, then a default that is not a valid value",
               prop(("description", "zzprobe 121 partial a"), ("default_value", "zzz")), "description", DV)
        update(n, "a default that is not a valid value, then description",
               prop(("default_value", "zzz"), ("description", "zzprobe 121 partial b")), "description", DV)
        update(n, "description, then a property the call does not take",
               prop(("description", "zzprobe 121 partial c"), ("unique", True)), "description")

        head("3. name and description in one PUT; one property twice")
        update(n, "name and description", prop(("name", name0 + " 121"), ("description", "zzprobe 121 both")),
               "name", "description")
        update(n, "description twice", prop(("description", "first"), ("description", "second")),
               "description")
        update(n, "name restored", prop(("name", name0)), "name")
    finally:
        retire(LIST)

    # --- status_list ------------------------------------------------------------------------------
    head("status_list: revive")
    codes = c.get(f"{BASE}/sg_status_list").json()["data"]["properties"]["valid_values"]["value"]
    a, b, d3, d4 = codes[:4]
    out.append(f"status codes used, all existing on the site: {[a, b, d3, d4]}")
    revive(STATUS)
    try:
        n = STATUS
        update(n, "valid_values, set to two", prop(("valid_values", [a, b])), V, DV)
        update(n, "default_value, the first", prop(("default_value", a)), DV)

        head("2. emptying a status_list's valid_values")
        update(n, "valid_values []", prop(("valid_values", [])), V, DV)

        head("3. status_list: valid_values and default_value in one PUT")
        update(n, "valid_values first; neither is valid alone",
               prop(("valid_values", [d3, d4]), ("default_value", d3)), V, DV)
        update(n, "default_value first; neither is valid alone",
               prop(("default_value", a), ("valid_values", [a, b])), V, DV)
        update(n, "valid_values first, a superset; the default is only in the new values",
               prop(("valid_values", [a, b, d3]), ("default_value", d3)), V, DV)
        update(n, "valid_values, back to two with the default", prop(("valid_values", [a, d3])), V, DV)
        update(n, "default_value first; the default is only in the new values",
               prop(("default_value", d4), ("valid_values", [a, d3, d4])), V, DV)

        head("5. a status code the site does not have")
        update(n, f"valid_values with {NO_STATUS!r} added",
               prop(("valid_values", at(rec(n), V + ".value") + [NO_STATUS])), V, DV)
        update(n, f"default_value {NO_STATUS!r}", prop(("default_value", NO_STATUS)), DV, V)
        status_after = statuses()
        new = sorted(set(status_after) - set(status_before))
        out.append(f"  statuses on the site after: {len(status_after)}; new codes: {new}")
        if NO_STATUS in status_after:
            r = c.delete(f"/entity/statuses/{status_after[NO_STATUS]}")
            out.append(f"  DELETE the {NO_STATUS!r} Status the write made -> {r.status_code}")

        head("6. status_list: a repeated value")
        cur = at(rec(n), V + ".value")
        update(n, "valid_values, one repeated", prop(("valid_values", cur + cur[:1])), V, DV)
    finally:
        retire(STATUS)

    # --- entity -----------------------------------------------------------------------------------
    if "--entity" not in sys.argv:
        raise SystemExit("the entity section spends names and retired its field; read the docstring")
    head("entity: revive")
    revive(ENTITY)
    try:
        n = ENTITY
        head("4. the order of valid_types")
        update(n, "Shot, Asset", prop(("valid_types", ["Shot", "Asset"])), VT)
        update(n, "Asset, Shot: a reorder only", prop(("valid_types", ["Asset", "Shot"])), VT)
        update(n, "Asset, Shot: the same again", prop(("valid_types", ["Asset", "Shot"])), VT)
        update(n, "Shot, Asset: a reorder only", prop(("valid_types", ["Shot", "Asset"])), VT)
        update(n, "Shot, Asset, Sequence", prop(("valid_types", ["Shot", "Asset", "Sequence"])), VT)
        update(n, "Sequence, Shot, Asset", prop(("valid_types", ["Sequence", "Shot", "Asset"])), VT)
        update(n, "Task, Asset", prop(("valid_types", ["Task", "Asset"])), VT)
        update(n, "Asset, Task, Shot", prop(("valid_types", ["Asset", "Task", "Shot"])), VT)
        update(n, "Shot, Shot, Asset: one repeated", prop(("valid_types", ["Shot", "Shot", "Asset"])), VT)

        head("2. emptying valid_types")
        update(n, "valid_types []", prop(("valid_types", [])), VT)
        update(n, "valid_types null", prop(("valid_types", None)), VT)

        head("5. a name that is not an entity type")
        update(n, f"Shot, {NO_TYPE}", prop(("valid_types", ["Shot", NO_TYPE])), VT)
        update(n, f"{NO_TYPE} alone", prop(("valid_types", [NO_TYPE])), VT)
        update(n, "shot, lowercase", prop(("valid_types", ["shot"])), VT)
    finally:
        retire(ENTITY)
finally:
    head("retired again")
    for name in list(live_now):
        retire(name)
    for name in (LIST, STATUS, ENTITY):
        out.append(f"GET {name} -> {c.get(path(name)).status_code}")
    left = [k for k in c.get(BASE).json()["data"] if "zzprobe" in k]
    out.append(f"zzprobe fields still listed on {TYPE}: {left}")
    out.append(f"statuses on the site at exit: {len(statuses())}")
    # In the finally: a run that dies halfway has still written to the site, and says what.
    _lib.emit("121_field_settings_edges", "\n".join(out), env)
