"""Q: how does a `uuid` field read, write, clear and filter?

Field-type matrix entry. A sweep of /schema/<Type>/fields over every type in /schema finds the uuid
fields; on this site there are four, and every one reports `editable: false`. None sits on an entity a
probe can create inside a project, so there is no sandbox row to write: WorkDayRule refuses every write
as a read only entity, Icon and LocalStorage have no `project` field, and EventLogEntry rows are written
by the server.

The write half therefore measures rejection on rows that already exist, and never mutates one. Each
target is first sent the value it already holds. That write is a no-op even if it succeeds, and the
value-shape cases run only after it has come back 400, so a site where uuid turned out to be writable
gets skipped rather than edited.

The sweep, the operator list, format, fill and the whole filter matrix run ungated.
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _lib  # noqa: E402

env = _lib.load_env()
c = _lib.client()
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
JSN = {"Content-Type": "application/json"}
CANON = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
FAKE = "3f2504e0-4f89-11d3-9a0c-0305e82c3301"     # RFC 4122 example; matches nothing here
NIL = "00000000-0000-0000-0000-000000000000"
rows = []


def errs(r):
    """The whole errors[] object, `source` included. The 400 is the documentation (probe 017)."""
    try:
        return json.dumps(r.json().get("errors"), indent=1)
    except ValueError:
        return r.text


def title(r):
    try:
        return r.json()["errors"][0]["title"]
    except (ValueError, KeyError, IndexError):
        return r.text[:200]


def count(slug, filters, size=500):
    r = c.post(f"/entity/{slug}/_search", headers=ARR,
               json={"filters": list(filters), "fields": ["id"], "page": {"size": size}})
    return len(r.json()["data"]) if r.ok else f"{r.status_code} {title(r)}"


# ---------------------------------------------------------------- read-only
rows.append("=== sweep: every uuid field on this site")
found = []
types = sorted(c.get("/schema").json()["data"])
for t in types:
    r = c.get(f"/schema/{t}/fields")
    if not r.ok:
        rows.append(f"  {t} /schema/<Type>/fields -> {r.status_code}")
        continue
    for name, f in r.json()["data"].items():
        if (f.get("data_type") or {}).get("value") == "uuid":
            found.append((t, name, f))
rows.append(f"  {len(types)} entity types scanned, {len(found)} uuid fields")
for t, name, f in found:
    g = f.get
    rows.append(f"  {t + '.' + name:<28} editable={(g('editable') or {}).get('value')!s:<5} "
                f"mandatory={(g('mandatory') or {}).get('value')!s:<5} "
                f"unique={(g('unique') or {}).get('value')!s:<5} "
                f"ui_value_displayable={(g('ui_value_displayable') or {}).get('value')} "
                f"properties={json.dumps(g('properties'), default=str)}")

TARGETS = [("EventLogEntry", "event_log_entries", "session_uuid"),
           ("Icon", "icons", "uuid"),
           ("LocalStorage", "local_storages", "uuid"),
           ("WorkDayRule", "work_day_rules", "uuid")]

rows.append("\n=== the operator list the API enumerates for this type (probe 017)")
for _, slug, field in TARGETS:
    r = c.post(f"/entity/{slug}/_search", headers=ARR,
               json={"filters": [[field, "definitely_not_an_operator", None]],
                     "fields": ["id"], "page": {"size": 1}})
    rows.append(f"  [[{field!r}, 'definitely_not_an_operator', None]] on /{slug} -> {r.status_code}")
    rows.append(errs(r))

rows.append("\n=== read: shape, format and fill")
values = {}
for etype, slug, field in TARGETS:
    r = c.post(f"/entity/{slug}/_search", headers=ARR,
               json={"filters": [], "fields": ["id", field], "page": {"size": 500}})
    data = r.json()["data"] if r.ok else []
    vals = [row["attributes"].get(field) for row in data]
    values[slug] = [v for v in vals if v]
    _lib.note_names(*values[slug])
    filled = values[slug]
    rows.append(f"  {etype + '.' + field:<28} rows={len(vals):<4} filled={len(filled):<4} "
                f"distinct={len(set(filled)):<4} lengths={sorted(set(len(v) for v in filled)) or '-'} "
                f"canonical_lowercase={all(CANON.fullmatch(v) for v in filled)} "
                f"version_nibble={dict(Counter(v[14] for v in filled))}")

ICON = c.post("/entity/icons/_search", headers=ARR,
              json={"filters": [], "fields": ["id", "uuid"], "page": {"size": 2}}).json()["data"]
U, U2 = ICON[0]["attributes"]["uuid"], ICON[1]["attributes"]["uuid"]
one = c.get(f"/entity/icons/{ICON[0]['id']}", params={"fields": "uuid"}).json()["data"]
rows.append(f"  single row keys={sorted(one)} attributes={json.dumps(one['attributes'])} "
            f"relationships={json.dumps(one['relationships'])}")
default = c.get(f"/entity/icons/{ICON[0]['id']}").json()["data"]["attributes"]
rows.append(f"  returned with no `fields` param: {'uuid' in default}")

rows.append("\n=== filter: value shapes accepted by `is`  (98 Icon rows, all filled, all distinct)")
for label, value in [("canonical, as read", U),
                     ("uppercase", U.upper()),
                     ("hyphens stripped", U.replace("-", "")),
                     ("hyphens stripped, uppercase", U.replace("-", "").upper()),
                     ("mixed case", U[:18] + U[18:].upper()),
                     ("brace wrapped", "{" + U + "}"),
                     ("urn:uuid: prefixed", "urn:uuid:" + U),
                     ("surrounded by spaces", f"  {U}  "),
                     ("first 8 hex digits", U[:8]),
                     ("not a uuid at all", "not-a-uuid"),
                     ("nil uuid, well formed", NIL),
                     ("RFC 4122 example uuid", FAKE),
                     ("empty string", ""),
                     ("null", None),
                     ("integer", 12345)]:
    rows.append(f"  is {label:<28} -> {count('icons', [['uuid', 'is', value]])}")

rows.append("\n=== filter: every operator, against 98 Icon rows")
for label, flt in [("is <row 1>", [["uuid", "is", U]]),
                   ("is_not <row 1>", [["uuid", "is_not", U]]),
                   ("is ''", [["uuid", "is", ""]]),
                   ("is_not ''", [["uuid", "is_not", ""]]),
                   ("in [<row 1>, <row 2>]", [["uuid", "in", [U, U2]]]),
                   ("in <row 1> (bare string)", [["uuid", "in", U]]),
                   ("in [uppercase, unhyphenated]", [["uuid", "in", [U.upper(),
                                                                    U2.replace("-", "")]]]),
                   ("in []", [["uuid", "in", []]]),
                   ("in ['']", [["uuid", "in", [""]]]),
                   ("in [None]", [["uuid", "in", [None]]]),
                   ("not_in [<row 1>, <row 2>]", [["uuid", "not_in", [U, U2]]]),
                   ("not_in [nil uuid]", [["uuid", "not_in", [NIL]]]),
                   ("contains <row 1>", [["uuid", "contains", U]])]:
    rows.append(f"  {label:<30} -> {count('icons', flt)}")
for op in ("starts_with", "ends_with", "not_contains", "greater_than"):
    rows.append(f"  {op + ' <8 hex digits>':<30} -> {count('icons', [['uuid', op, U[:8]]])}")

rows.append("\n=== filter: the same operators over rows where the field is null")
null_ids = [row["id"] for row in c.post("/entity/event_log_entries/_search", headers=ARR,
                                        json={"filters": [], "fields": ["id", "session_uuid"],
                                              "page": {"size": 5}}).json()["data"]]
base = [["id", "in", null_ids]]
rows.append(f"  {'baseline, 5 rows, session_uuid null on all':<42} -> {count('event_log_entries', base)}")
for label, clause in [("is ''", ["session_uuid", "is", ""]),
                      ("is_not ''", ["session_uuid", "is_not", ""]),
                      ("is <a uuid>", ["session_uuid", "is", FAKE]),
                      ("is_not <a uuid>", ["session_uuid", "is_not", FAKE]),
                      ("not_in [<a uuid>]", ["session_uuid", "not_in", [FAKE]])]:
    rows.append(f"  {label:<42} -> {count('event_log_entries', base + [clause])}")

rows.append("\n=== sort and summarize")
for label, r in [("GET /entity/icons?sort=uuid",
                  c.get("/entity/icons", params={"fields": "uuid", "sort": "uuid",
                                                 "page[size]": 3})),
                 ("GET /entity/icons?sort=id (control)",
                  c.get("/entity/icons", params={"fields": "uuid", "sort": "id",
                                                 "page[size]": 3}))]:
    rows.append(f"  {label:<38} -> {r.status_code} {'' if r.ok else errs(r)}")
r = c.post("/entity/icons/_summarize", headers=ARR,
           json={"filters": [], "summary_fields": [{"field": "id", "type": "count"}],
                 "grouping": [{"field": "uuid", "type": "exact", "direction": "asc"}]})
g = r.json()["data"]["groups"] if r.ok else []
rows.append(f"  _summarize grouping exact on uuid      -> {r.status_code} "
            f"{len(g)} groups over {r.json()['data']['summaries']['id'] if r.ok else '?'} rows")
for slug, field in (("icons", "uuid"), ("event_log_entries", "session_uuid")):
    r = c.post(f"/entity/{slug}/_summarize", headers=ARR,
               json={"filters": base if slug == "event_log_entries" else [],
                     "summary_fields": [{"field": field, "type": "count"}]})
    rows.append(f"  _summarize count {slug + '.' + field:<38} -> {r.status_code} "
                f"{json.dumps(r.json()['data']['summaries']) if r.ok else title(r)}")

# ---------------------------------------------------------------- writes
if not _lib.writes_allowed():
    rows.append("\n(read-only run; re-run with --write for the write and clear matrix)")
    _lib.emit("field_types/uuid", "\n".join(rows), env)
    raise SystemExit

with _lib.Created(c) as made:                      # nothing is created; the guarantee is structural
    rows.append("\n=== write: is a uuid field writable at all?")
    rows.append("  no entity type carrying a uuid field can be created inside a project, so there is")
    rows.append(f"  no sandbox row to write. sandbox project resolved: {bool(_lib.sandbox_id(c, env))}")

    rows.append("\n  guard: send each field the value it already holds. A no-op even if accepted.")
    guarded = []
    for etype, slug, field in TARGETS:
        row = c.post(f"/entity/{slug}/_search", headers=ARR,
                     json={"filters": [], "fields": ["id", field], "page": {"size": 1}}
                     ).json()["data"][0]
        own = row["attributes"].get(field)
        r = c.request("PUT", f"/entity/{slug}/{row['id']}", headers=JSN, json={field: own})
        rows.append(f"  PUT {etype}.{field} <- its own current value -> {r.status_code}")
        rows.append(errs(r))
        if r.ok:
            rows.append(f"  {etype}.{field} accepted a write; skipping the value cases rather than "
                        f"editing a row this probe did not create")
        else:
            guarded.append((etype, slug, field, row["id"], own))

    rows.append("\n=== write: value shapes, on a field that rejects every write")
    for etype, slug, field, rid, own in guarded[:1]:
        for label, value in [("canonical uuid", FAKE),
                             ("hyphens stripped", FAKE.replace("-", "")),
                             ("uppercase", FAKE.upper()),
                             ("non-uuid string", "not-a-uuid"),
                             ("duplicate of another row", U2),
                             ("null", None),
                             ("empty string", ""),
                             ("integer", 12345)]:
            r = c.request("PUT", f"/entity/{slug}/{rid}", headers=JSN, json={field: value})
            rows.append(f"  {label:<26} -> {r.status_code} {title(r) if not r.ok else r.text[:120]}")
        back = c.get(f"/entity/{slug}/{rid}", params={"fields": field}
                     ).json()["data"]["attributes"].get(field)
        rows.append(f"  {etype}.{field} reads back unchanged: {back == own}")

    rows.append("\n=== create: can a uuid be supplied at creation?")
    r = c.post("/entity/work_day_rules", headers=JSN, json={"uuid": FAKE})
    rows.append(f"  POST /entity/work_day_rules {{'uuid': ...}} -> {r.status_code}")
    rows.append(errs(r))
    rows.append(f"  rows created by this probe: {len(made.rows)}")

_lib.emit("field_types/uuid", "\n".join(rows), env)
