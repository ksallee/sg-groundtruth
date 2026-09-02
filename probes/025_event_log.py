"""Q: what can a client do with EventLogEntry over REST?

Production code uses this one entity four ways, and each is a separate question about REST. As history:
restoring a previous status has nowhere to read from but the log. As a ledger: writing entries of your own.
As a change feed: consuming it in id order. As a lock: writing a claim and re-reading for the oldest one.

Reads run against the first sample project. The create attempt is behind --write and goes only into the
sandbox project.
"""
import collections
import json
import time

import _lib

env = _lib.load_env()
c = _lib.client()
PROJECT = _lib.sample_projects(c, env)[0]
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
FIELDS = ["event_type", "attribute_name", "meta", "audit_trail", "entity", "project", "user",
          "created_at", "description", "session_uuid", "cached_display_name", "image",
          "filmstrip_image", "image_blur_hash", "image_source_entity"]
rows = []


def search(filters, fields=("id",), size=500, sort=None, page=1):
    body = {"filters": list(filters), "fields": list(fields), "page": {"size": size, "number": page}}
    if sort:
        body["sort"] = sort
    r = c.post("/entity/event_log_entries/_search", headers=ARR, json=body)
    return r if not r.ok else r.json()["data"]


def count(filters):
    r = c.post("/entity/event_log_entries/_summarize", headers=ARR,
               json={"filters": list(filters),
                     "summary_fields": [{"field": "id", "type": "record_count"}]})
    return r.json()["data"]["summaries"]["id"] if r.ok else f"ERR {r.status_code} {r.text}"


def err(r):
    try:
        return f"{r.status_code} {json.dumps(r.json()['errors'])}"
    except Exception:
        return f"{r.status_code} {r.text}"


IN_PROJECT = [["project", "is", {"type": "Project", "id": PROJECT}]]

rows.append("=== schema: every field, and what the type says about it")
spec = c.get("/schema/EventLogEntry/fields").json()["data"]
rows.append(f"  /schema/EventLogEntry/fields -> {len(spec)} fields")
for name, s in sorted(spec.items()):
    rows.append(f"    {name:<22} {s['data_type']['value']:<14} editable={str(s['editable']['value']):<5} "
                f"mandatory={s['mandatory']['value']}")
et = c.get("/schema/EventLogEntry").json()["data"]
rows.append(f"  /schema/EventLogEntry -> {json.dumps(et)}")

rows.append("\n=== read: ask for all 16 by name, see which come back")
one = search([["event_type", "is", "Shotgun_Shot_Change"], ["attribute_name", "is", "sg_status_list"]],
             FIELDS, size=1, sort="-id")
one = one[0]
_lib.note_from(one)
got = set(one["attributes"]) | set(one["relationships"])
rows.append(f"  asked for {len(FIELDS)} + id; attributes {sorted(one['attributes'])}")
rows.append(f"  relationships {sorted(one['relationships'])}")
rows.append(f"  absent from the 200: {sorted(set(FIELDS) - got)}")

rows.append("\n=== as history: where old and new values are")
rows.append(f"  meta = {json.dumps(one['attributes']['meta'])}")
rows.append(f"  description = {json.dumps(one['attributes']['description'])}")
rows.append(f"  entity relationship data = {json.dumps(one['relationships']['entity']['data'])}")

# A status history for one entity, newest first, to see whether old/new chain.
hist = search(IN_PROJECT + [["event_type", "is", "Shotgun_Shot_Change"],
                            ["attribute_name", "is", "sg_status_list"]],
              ["meta", "created_at", "entity"], size=500, sort="-id")
by_entity = collections.defaultdict(list)
for e in hist:
    m = e["attributes"]["meta"] or {}
    if m.get("entity_id"):
        by_entity[m["entity_id"]].append(e)
best = max(by_entity.values(), key=len) if by_entity else []
rows.append(f"  {len(hist)} Shot sg_status_list events in this project, over {len(by_entity)} shots; "
            f"longest chain {len(best)}")
for e in best[:5]:
    m = e["attributes"]["meta"]
    rows.append(f"    id={e['id']} {e['attributes']['created_at']} "
                f"old_value={m.get('old_value')!r} new_value={m.get('new_value')!r} "
                f"in_create={m.get('in_create')}")
if best:
    sid = best[0]["attributes"]["meta"]["entity_id"]
    live = c.get(f"/entity/shots/{sid}", params={"fields": "sg_status_list"})
    rows.append(f"  newest new_value={best[0]['attributes']['meta']['new_value']!r}; "
                f"GET /entity/shots/{sid}?fields=sg_status_list -> {live.status_code} "
                f"{json.dumps(live.json()['data']['attributes']) if live.ok else live.text}")
    chained = sum(1 for a, b in zip(best, best[1:])
                  if a["attributes"]["meta"].get("old_value") == b["attributes"]["meta"].get("new_value"))
    rows.append(f"  old_value of each entry equals new_value of the previous: {chained} of {len(best) - 1}")

rows.append("\n=== meta is not one shape: which keys come with which meta.type")
census = collections.defaultdict(lambda: [0, set()])
for suffix in ("_Change", "_New", "_Retirement", "_Revival"):
    got = search([["event_type", "ends_with", suffix]], ["meta", "event_type"], size=200, sort="-id")
    for e in got if isinstance(got, list) else []:
        m = e["attributes"]["meta"]
        k = str(m.get("type")) if isinstance(m, dict) else type(m).__name__
        census[(suffix, k)][0] += 1
        if isinstance(m, dict):
            census[(suffix, k)][1].update(m)
for (suffix, k), (n, keys) in sorted(census.items()):
    rows.append(f"  event_type *{suffix:<12} meta.type={k:<24} {n:>4} rows, keys {sorted(keys)}")
rows.append(f"  old_value/new_value present only where meta.type is: "
            f"{sorted({k for (_, k), (_, keys) in census.items() if 'old_value' in keys})}")

rows.append("\n=== does the entity link survive, or only meta.entity_id")
linked = sum(1 for e in hist if (e["relationships"].get("entity") or {}).get("data"))
rows.append(f"  of {len(hist)} rows: entity relationship set on {linked}, "
            f"meta.entity_id set on {sum(1 for e in hist if (e['attributes']['meta'] or {}).get('entity_id'))}")
gone = [e for e in hist if not (e["relationships"].get("entity") or {}).get("data")
        and (e["attributes"]["meta"] or {}).get("entity_id")]
if gone:
    mid = gone[0]["attributes"]["meta"]["entity_id"]
    r = c.get(f"/entity/shots/{mid}", params={"fields": "code"})
    rows.append(f"  a row with entity null but meta.entity_id={mid}: "
                f"GET /entity/shots/{mid} -> {err(r) if not r.ok else '200'}")

rows.append("\n=== which event_type and attribute_name values exist here")
r = c.post("/entity/event_log_entries/_summarize", headers=ARR,
           json={"filters": IN_PROJECT, "summary_fields": [{"field": "id", "type": "record_count"}],
                 "grouping": [{"field": "event_type", "type": "exact", "direction": "desc"}]})
g = r.json()["data"]["groups"] if r.ok else []
rows.append(f"  {len(g)} distinct event_type in this project; top: "
            f"{json.dumps([(x['group_name'], x['summaries']['id']) for x in g[:8]])}")
r = c.post("/entity/event_log_entries/_summarize", headers=ARR,
           json={"filters": IN_PROJECT, "summary_fields": [{"field": "id", "type": "record_count"}],
                 "grouping": [{"field": "attribute_name", "type": "exact", "direction": "desc"}]})
g = r.json()["data"]["groups"] if r.ok else []
rows.append(f"  {len(g)} distinct attribute_name; top: "
            f"{json.dumps([(x['group_name'], x['summaries']['id']) for x in g[:8]])}")

rows.append("\n=== can the log be narrowed at all: by entity, by event type, by date, by project")
site_total = count([])
rows.append(f"  no filter at all (whole site) -> {site_total}")
rows.append(f"  project is <sample> -> {count(IN_PROJECT)}")
narrowings = [
    ("event_type is Shotgun_Shot_Change", [["event_type", "is", "Shotgun_Shot_Change"]]),
    ("event_type starts_with Shotgun_Shot_", [["event_type", "starts_with", "Shotgun_Shot_"]]),
    ("event_type in [2 values]", [["event_type", "in", ["Shotgun_Shot_Change", "Shotgun_Task_Change"]]]),
    ("attribute_name is sg_status_list", [["attribute_name", "is", "sg_status_list"]]),
    ("created_at in_last [7, DAY]", [["created_at", "in_last", [7, "DAY"]]]),
    ("created_at greater_than 2026-01-01", [["created_at", "greater_than", "2026-01-01T00:00:00Z"]]),
    ("entity type_is Shot", [["entity", "type_is", "Shot"]]),
    ("entity is null", [["entity", "is", None]]),
    ("user is null", [["user", "is", None]]),
    ("meta is null", [["meta", "is", None]]),
    ("audit_trail is null", [["audit_trail", "is", None]]),
    ("audit_trail is_not null", [["audit_trail", "is_not", None]]),
]
if best:
    ent = {"type": "Shot", "id": best[0]["attributes"]["meta"]["entity_id"]}
    narrowings.insert(6, (f"entity is {{Shot, {ent['id']}}}", [["entity", "is", ent]]))
    code = c.get(f"/entity/shots/{ent['id']}", params={"fields": "code"})
    if code.ok:
        shot_code = code.json()["data"]["attributes"]["code"]
        _lib.note_names(shot_code)
        narrowings.insert(7, ("entity.Shot.code is <that shot's code>",
                              [["entity.Shot.code", "is", shot_code]]))
for label, f in narrowings:
    rows.append(f"  {label:<44} -> {count(f)}")

rows.append("\n=== the bogus-operator trick, one field per data type")


def bogus(field):
    r = c.post("/entity/event_log_entries/_search", headers=ARR,
               json={"filters": [[field, "definitely_not_an_operator", None]],
                     "fields": ["id"], "page": {"size": 1}})
    if r.ok:
        return f"NOT REJECTED {r.status_code}, {len(r.json()['data'])} rows"
    e = r.json()["errors"][0]
    return json.dumps({"status": r.status_code, "code": e.get("code"), "title": e.get("title"),
                       "source": e.get("source")})


for f in sorted(spec):
    rows.append(f"  {f:<22} {bogus(f)}")

rows.append("\n=== sort")
for s in ("id", "-id", "created_at", "-created_at", "meta", "audit_trail", "zzz_not_a_field"):
    d = search(IN_PROJECT, ["id", "created_at"], size=3, sort=s)
    rows.append(f"  sort={s!r} -> "
                f"{err(d) if not isinstance(d, list) else [(x['id'], x['attributes']['created_at']) for x in d]}")

rows.append("\n=== as a change feed: are ids dense")
head = search([], ["id", "created_at"], size=500, sort="-id")
lo, hi = head[-1]["id"], head[0]["id"]
rows.append(f"  newest 500 rows site-wide, sorted -id: id span {hi - lo + 1} for 500 rows "
            f"({hi - lo + 1 - 500} ids missing)")
rows.append(f"  same span by filter, id between [{lo}, {hi}] -> {count([['id', 'between', [lo, hi]]])}")
seq = sorted(x["id"] for x in head)
gaps = [(a, b) for a, b in zip(seq, seq[1:]) if b - a > 1]
rows.append(f"  {len(gaps)} gaps in those 500; largest {max((b - a for a, b in gaps), default=0)}; "
            f"first few {json.dumps(gaps[:5])}")
mono = all(a["attributes"]["created_at"] <= b["attributes"]["created_at"]
           for a, b in zip(sorted(head, key=lambda x: x["id"]), sorted(head, key=lambda x: x["id"])[1:]))
rows.append(f"  created_at non-decreasing as id increases across those 500: {mono}")
# A wide window well behind the head, to see whether gaps are reserved blocks rather than deletions.
for width in (1000, 10000, 100000):
    a = hi - width
    n = count([["id", "between", [a, hi]]])
    rows.append(f"  id between [{hi} - {width}, {hi}] -> {n} rows for {width + 1} ids "
                f"({100.0 * n / (width + 1):.1f}% dense)")
oldest = search([], ["id", "created_at"], size=1, sort="id")
rows.append(f"  oldest row id={oldest[0]['id']} created_at={oldest[0]['attributes']['created_at']}; "
            f"newest id={hi}; site total {site_total} rows over an id span of {hi - oldest[0]['id'] + 1} "
            f"({100.0 * site_total / (hi - oldest[0]['id'] + 1):.1f}% dense)")

# The windows above nest, so each one contains the sparse head. Disjoint windows of the same width at
# increasing depth separate "ids are permanently skipped" from "ids near the head fill in later".
rows.append("  disjoint 1001-id windows, same width, increasing depth:")
for depth in (0, 10000, 100000, 1000000):
    a = hi - depth - 1000
    n = count([["id", "between", [a, a + 1000]]])
    rows.append(f"    [head - {depth + 1000}, head - {depth}] -> {n:>5} rows of 1001 ids "
                f"({100.0 * n / 1001:.1f}% dense)")

# If a gap in the head window is a reserved block rather than a permanently skipped id, the same fixed
# range holds more rows later, and a cursor that read it at t=0 lost those events for good.
rows.append(f"  fixed range [{lo}, {hi}] at t=0 -> {count([['id', 'between', [lo, hi]]])} rows")
for wait in (60, 60):
    time.sleep(wait)
    rows.append(f"  same fixed range after {wait}s more -> {count([['id', 'between', [lo, hi]]])} rows "
                f"(newest id now {search([], ['id'], size=1, sort='-id')[0]['id']})")

rows.append("\n=== the entity link versus meta.entity_id, site-wide")
for label, f in (("Shotgun_Shot_Change, all", [["event_type", "is", "Shotgun_Shot_Change"]]),
                 ("Shotgun_Shot_Change, entity is null",
                  [["event_type", "is", "Shotgun_Shot_Change"], ["entity", "is", None]]),
                 ("Shotgun_Shot_Change, entity type_is Shot",
                  [["event_type", "is", "Shotgun_Shot_Change"], ["entity", "type_is", "Shot"]])):
    rows.append(f"  {label:<44} -> {count(f)}")
orphan = search([["event_type", "is", "Shotgun_Shot_Change"], ["entity", "is", None]],
                ["meta", "created_at"], size=3, sort="-id")
for e in orphan if isinstance(orphan, list) else []:
    m = e["attributes"]["meta"] or {}
    tgt = c.get(f"/entity/shots/{m.get('entity_id')}", params={"fields": "code"})
    rows.append(f"    id={e['id']} entity=null but meta.entity_type={m.get('entity_type')!r} "
                f"meta.entity_id={m.get('entity_id')}; GET that Shot -> {tgt.status_code}")

rows.append("\n=== update an existing row")
# Never DELETE a real audit row, and never write a real value into one. The four editable=False fields
# are safe to attempt because they are refused; the three editable=True ones are sent the value already
# stored, so a 200 changes nothing.
for field, value in (("description", "zzprobe 025"), ("meta", {"zz": 1}),
                     ("event_type", "Zzprobe_025_Ping"), ("attribute_name", "zzprobe_025")):
    r = c.put(f"/entity/event_log_entries/{one['id']}", json={field: value})
    rows.append(f"  PUT {field:<20} -> {err(r) if not r.ok else '200 ACCEPTED, row mutated'}")

rows.append("  the three fields the schema flags editable=True, written with the value already stored "
            "(null on this row), so an accepted write is still a no-op:")
for field in ("cached_display_name", "image", "filmstrip_image"):
    rows.append(f"    stored before: {json.dumps(one['attributes'][field])}")
    r = c.put(f"/entity/event_log_entries/{one['id']}", json={field: None})
    rows.append(f"  PUT {field:<20} -> {err(r) if not r.ok else '200 ACCEPTED'}")

rows.append("\n=== as a ledger: create")
MARKER = "zzprobe 025"
made_id = None
if not _lib.writes_allowed():
    rows.append("  skipped, no --write")
else:
    SANDBOX = _lib.sandbox_id(c, env)
    # A created EventLogEntry cannot be deleted on this site, so the first --write run leaves one row
    # for good. Find it by its marker and never make a second: re-running would litter once per run.
    prior = search([["project", "is", {"type": "Project", "id": SANDBOX}],
                    ["cached_display_name", "is", MARKER]], ["created_at", "description"], sort="id")
    prior = prior if isinstance(prior, list) else []
    if prior:
        made_id = prior[0]["id"]
        rows.append(f"  an earlier --write run already left {len(prior)} undeletable row(s) in the "
                    f"sandbox: {[x['id'] for x in prior]}")
        rows.append("  NOT creating another: POST is permitted and DELETE is not, so each run would add "
                    "one permanent row. The create and DELETE evidence is from the first run.")
    else:
        with _lib.Created(c) as made:
            # Cheapest body first, and the first body accepted is the last one sent: an undeletable row
            # is permanent litter, so one create is the whole budget.
            attempts = [
                ("empty body", {}),
                ("event_type only", {"event_type": "Zzprobe_025_Ping"}),
                ("project only", {"project": {"type": "Project", "id": SANDBOX}}),
            ]
            for label, body in attempts:
                r = c.post("/entity/event_log_entries", json=body)
                rows.append(f"  POST {label:<24} -> {r.status_code}")
                if not r.ok:
                    rows.append(f"    {err(r)}")
                    continue
                d = r.json()["data"]
                made_id = made.add("event_log_entries", d["id"])
                rows.append(f"    201 body attributes={json.dumps(d['attributes'])}")
                back = c.get(f"/entity/event_log_entries/{d['id']}", params={"fields": ",".join(FIELDS)})
                rows.append(f"    read back -> {back.status_code} "
                            f"{json.dumps(back.json()['data']) if back.ok else back.text}")
                for field, value in (("cached_display_name", MARKER), ("event_type", "Zzprobe_025_Ping"),
                                     ("meta", {"probe": 25})):
                    u = c.put(f"/entity/event_log_entries/{d['id']}", json={field: value})
                    rows.append(f"    PUT {field:<20} on the created row -> "
                                f"{err(u) if not u.ok else '200 ACCEPTED'}")
                dl = c.delete(f"/entity/event_log_entries/{d['id']}")
                rows.append(f"    DELETE -> {dl.status_code} {'' if dl.ok else err(dl)}")
                if dl.ok:
                    made.rows = [x for x in made.rows if x[1] != d["id"]]
                    gone_r = c.get(f"/entity/event_log_entries/{d['id']}")
                    rows.append(f"    after delete, GET -> {gone_r.status_code}")
                else:
                    rows.append("    stopping here: an undeletable row is permanent litter, so the "
                                "remaining create bodies are never sent and stay unmeasured")
                break

        left = [i for _, i in made.rows]
        rows.append(f"  rows left behind: {left if left else 'none'}")

rows.append("\n=== as a lock: a claim, then the newest claim predating it")
if made_id is None:
    rows.append("  dropped: a lock needs a write, and no EventLogEntry could be created")
else:
    claims = search([["project", "is", {"type": "Project", "id": _lib.sandbox_id(c, env)}],
                     ["cached_display_name", "is", MARKER], ["id", "less_than", made_id]],
                    ["created_at"], size=1, sort="-id")
    rows.append(f"  own claim id={made_id}; claims predating it: "
                f"{len(claims) if isinstance(claims, list) else err(claims)}")
    rows.append("  the read half works (id less_than, sort -id, one row). The write half is a POST that "
                "cannot be undone, so a lock built this way leaks one row per acquisition.")


_lib.emit("025_event_log", "\n".join(rows), env)
