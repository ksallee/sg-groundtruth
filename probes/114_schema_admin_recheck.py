"""Q: has REST gained a way to enable or disable a custom entity, delete a trashed field forever, or
write `hidden_values`?

All three were missing when last measured and were raised on the community forum on 2026-05-14 with no
vendor reply. This probe makes only the calls no other probe makes. The rest is already covered:

  - `PUT /preferences/update` and its rejections: probe 047
  - create, trash, revive by body, the `retired_only` listings: probe 040
  - the operation list in `/spec.json` against the cards: probe 042

Read-only by default: a word search of `/spec.json`, the `/preferences/custom_entity` calls that 042
found the spec now names, and listing options 040 did not try. No body sent to a custom entity call
could turn a real slot on or off: it has no keys, or it names a type that does not exist.

`--write` adds two things.

Trashed-field calls, addressed only at `sg_zzprobe_040_revive` on Version, a name probe 040 already
spent. The field is trashed again before the probe exits.

A `hidden_values` write on Task `sg_status_list`, scoped to the sandbox project, with the value it
already holds. Only if that is accepted is one status added and then taken back. Every sample project
and the unscoped reading are snapshotted before and compared after each write, because a server that
ignored the scope would otherwise change projects this probe may only read.
"""
import json
import re

import _lib

env = _lib.load_env()
c = _lib.client()
WRITE = _lib.writes_allowed()
out = []

TYPE, SPENT = "Version", "sg_zzprobe_040_revive"
assert SPENT.startswith("sg_zzprobe_")
FIELD = f"/schema/{TYPE}/fields/{SPENT}"
CE = "/preferences/custom_entity"


def body_of(r):
    if not r.content:
        return "(empty body)"
    try:
        j = r.json()
    except ValueError:
        return r.text[:300]
    if isinstance(j, dict) and "errors" in j:
        return json.dumps(j["errors"])
    return json.dumps(j)[:300]


def call(label, method, path, **kw):
    r = c.request(method, path, **kw)
    sent = kw.get("json", kw.get("params", ""))
    out.append(f"{method} {path}  {json.dumps(sent) if sent != '' else ''}\n"
               f"  [{label}] -> {r.status_code}  {body_of(r)}")
    return r


def head(t):
    out.append(f"\n\n===== {t}")


# --- 1. does the spec name any of the three? ----------------------------------------------------
head("GET /spec.json, searched for the three operations")
spec = c.get("/spec.json").json()
ops = [(m.upper(), p, v[m]) for p, v in spec["paths"].items()
       for m in v if m.lower() in ("get", "post", "put", "patch", "delete")]
out.append(f"{len(spec['paths'])} paths, {len(ops)} operations")
for w in ("forever", "trash", "purge", "hidden_values", "disable", "activation", "revive"):
    hits = sorted({f"{m} {p}" for m, p, op in ops if re.search(w, p + json.dumps(op), re.I)})
    out.append(f"  {w}: {hits or 'nowhere'}")

# --- 2. the custom entity calls the spec names --------------------------------------------------
head(f"{CE}/<entity_type>  (reads, and writes that name nothing)")
enabled_types = set(c.get("/schema").json().get("data") or {})
on = sorted(t for t in enabled_types if re.fullmatch(r"CustomEntity\d\d", t))
off = [f"CustomEntity{n:02d}" for n in range(1, 51) if f"CustomEntity{n:02d}" not in enabled_types]
ON, OFF = (on[0] if on else None), (off[-1] if off else None)
out.append(f"CustomEntityNN in /schema: {len(on)}; absent from it: {len(off)}; "
           f"reading {ON} (enabled) and {OFF} (absent)")
for label_, t in (("an enabled slot", ON), ("a slot absent from /schema", OFF),
                  ("a stock type", "Shot"), ("a type that does not exist", "NotAnEntityType")):
    if t:
        call(label_, "GET", f"{CE}/{t}/configuration")
call("the collection, which the spec does not name", "GET", CE)
call("activation read, which the spec does not name", "GET", f"{CE}/{OFF}/activation")
call("activation on a type that does not exist", "PUT", f"{CE}/NotAnEntityType/activation",
     json={"enabled": True})
call("activation with no `enabled`, on the absent slot", "PUT", f"{CE}/{OFF}/activation", json={})
call("configuration with no keys, on the absent slot", "PUT", f"{CE}/{OFF}/configuration", json={})
if ON:
    call("configuration with no keys, on the enabled slot", "PUT", f"{CE}/{ON}/configuration", json={})
call("the older call, with an operation its spec does not name", "PUT", "/preferences/update",
     json={"preference": "disable_entity", "entity_type": "NotAnEntityType"})

# --- 3. listing a trashed field: the spellings 040 did not try ----------------------------------
head(f"is the trashed field {SPENT} listed under any other option")
plain = c.get(f"/schema/{TYPE}/fields")
base = set((plain.json().get("data") or {}).keys())
out.append(f"GET /schema/{TYPE}/fields  plain -> {plain.status_code}, {len(base)} fields")
for params in ({"retired_only": "true"}, {"include_retired": "true"},
               {"options[include_retired]": "true"}, {"retired": "true"},
               {"filter[retired]": "true"}, {"trashed": "true"}):
    r = c.get(f"/schema/{TYPE}/fields", params=params)
    keys = set((r.json().get("data") or {}).keys()) if r.status_code == 200 else set()
    out.append(f"  {json.dumps(params)} -> {r.status_code}, {len(keys)} fields, "
               f"trashed present: {SPENT in keys}, differs from plain: {keys != base}")
for path in (f"/schema/{TYPE}/retired_fields", f"/schema/{TYPE}/trash", "/trash"):
    call("a guessed path", "GET", path)


def is_live():
    return c.get(FIELD).status_code == 200


if not WRITE:
    out.append("\n\n===== trashed-field and hidden_values writes skipped: run with --write")
elif is_live():
    out.append(f"\n\n===== {SPENT} is live, not trashed: trashed-field calls skipped")
else:
    # --- 4. delete forever ----------------------------------------------------------------------
    head(f"delete forever, guessed, on the already trashed {SPENT}")
    call("a plain DELETE on a trashed field", "DELETE", FIELD)
    for params in ({"forever": "true"}, {"permanent": "true"}, {"delete_forever": "true"}):
        call("DELETE with a query option", "DELETE", FIELD, params=params)
    for body in ({"forever": True}, {"delete_forever": True}):
        call("DELETE with a body", "DELETE", FIELD, json=body)
    for body in ({"revive": False}, {"delete_forever": True}, {"revive": False, "forever": True}):
        call("POST with a guessed parameter", "POST", FIELD, json=body)
    out.append(f"  live after the guesses: {is_live()}")

    # --- 5. the spec puts `revive` in the query; 040 sent a body --------------------------------
    head("revive in the query, as /spec.json has it")
    call("revive", "POST", FIELD, params={"revive": "true"})
    out.append(f"  live after it: {is_live()}")
    if is_live():
        call("DELETE ?forever=true on the live field", "DELETE", FIELD, params={"forever": "true"})
        if is_live():
            call("plain DELETE, to leave it trashed", "DELETE", FIELD)
    out.append(f"  live at the end: {is_live()}")
    r = c.post(FIELD, json={})  # 040: only a retired name answers `revive is missing`
    out.append(f"  name still held by a retired field: {r.status_code == 400 and 'revive' in r.text}")

# --- 6. hidden_values ---------------------------------------------------------------------------
if WRITE:
    head("hidden_values on Task sg_status_list, sandbox project")
    SB = _lib.sandbox_id(c, env)
    others = [p for p in _lib.sample_projects(c, env) if p != SB]
    HV = "/schema/Task/fields/sg_status_list"

    def read(pid=None):
        r = c.get(HV, params={"project_id": pid} if pid else {})
        return ((r.json().get("data") or {}).get("properties") or {}).get("hidden_values") or {}

    def snapshot():
        return {pid: read(pid).get("value") for pid in [None] + others}

    def label(pid):
        return "unscoped" if pid is None else f"sample project {others.index(pid) + 1}"

    before, cur = snapshot(), read(SB)
    orig = list(cur.get("value") or [])
    valid = c.get(HV).json()["data"]["properties"]["valid_values"]["value"]
    out.append(f"sandbox hidden_values: {json.dumps(orig)}  editable: {cur.get('editable')}")
    out.append(f"unscoped hidden_values: {json.dumps(before[None])}  valid_values: {len(valid)}")

    def drift():
        """Put back any reading outside the sandbox that a write changed, and say so."""
        now = snapshot()
        moved = [pid for pid in now if now[pid] != before[pid]]
        for pid in moved:
            out.append(f"  !! {label(pid)} changed: {json.dumps(before[pid])} -> {json.dumps(now[pid])}")
            body = {"properties": [{"property_name": "hidden_values", "value": before[pid] or []}]}
            if pid:
                body["project_id"] = pid
            rr = c.put(HV, json=body, params={"project_id": pid} if pid else {})
            out.append(f"     restored -> {rr.status_code}  now {json.dumps(read(pid).get('value'))}")
        if not moved:
            out.append("  no reading outside the sandbox changed")
        return bool(moved)

    def put(label_, value, where):
        prop = {"properties": [{"property_name": "hidden_values", "value": value}]}
        kw = ({"json": {**prop, "project_id": SB}} if where == "body"
              else {"json": prop, "params": {"project_id": SB}})
        r = call(label_, "PUT", HV, **kw)
        out.append(f"  sandbox reads back: {json.dumps(read(SB).get('value'))}")
        return r

    accepted, leaked = None, False
    for where in ("body", "query"):
        r = put(f"the value it already holds, project_id in the {where}", orig, where)
        leaked = drift() or leaked
        if r.status_code == 200 and accepted is None:
            accepted = where
    spare = next((v for v in valid if v not in orig), None)
    if accepted and spare and not leaked:
        out.append(f"\nthe unchanged value was accepted with project_id in the {accepted}; "
                   f"now adding one status, {spare!r}")
        try:
            put("one status added", orig + [spare], accepted)
            out.append(f"  applied: {spare in (read(SB).get('value') or [])}")
            drift()
        finally:
            put("the original value put back", orig, accepted)
            out.append(f"  sandbox restored: {(read(SB).get('value') or []) == orig}")
            drift()
    else:
        out.append(f"\nno change attempted: accepted={accepted} spare={spare!r} leaked={leaked}")

_lib.emit("114_schema_admin_recheck", "\n".join(out), env)
