"""Q: what tells a client that a page's layout changed: an updated_at on Page or PageSetting, or an
EventLogEntry row for the save?

A client caching a page's layout needs a cheap change test. Probe 023 listed PageSetting at 6 fields;
this lists both types in full and looks for the page saves in the event log. Site-wide, read only.
"""
import collections
import json

import _lib
import _pages as P

env = _lib.load_env()
c = _lib.client()
rows = []

for t in ("Page", "PageSetting"):
    d = c.get(f"/schema/{t}/fields").json()["data"]
    rows.append(f"=== /schema/{t}/fields: {len(d)} fields")
    for name, spec in sorted(d.items()):
        rows.append(f"  {name:<28} {spec['data_type']['value']:<14} editable={spec['editable']['value']}")

rows.append("\n=== asking PageSetting for the stamps it does not have")
r = c.get("/entity/page_settings", params={"fields": "updated_at,updated_by,created_at,created_by",
                                           "page[size]": 1, "filter[user]": ""})
one = c.post("/entity/page_settings/_search", headers=P.ARR,
             json={"filters": [["page", "is_not", None]], "fields": ["updated_at", "updated_by", "created_at", "created_by"],
                   "page": {"size": 1}}).json()["data"][0]
rows.append(f"  fields=updated_at,updated_by,created_at,created_by -> attributes {sorted(one['attributes'])}, "
            f"relationships {sorted(one['relationships'])}")
r = c.post("/entity/page_settings/_search", headers=P.ARR,
           json={"filters": [["updated_at", "is_not", None]], "fields": ["id"], "page": {"size": 1}})
rows.append(f"  filter updated_at is_not null -> {r.status_code} "
            f"{r.json()['errors'][0] if not r.ok else len(r.json()['data'])}")

rows.append("\n=== the event log: which event types name a page")
r = c.post("/entity/event_log_entries/_summarize", headers=P.ARR,
           json={"filters": [["event_type", "starts_with", "Shotgun_Page"]],
                 "summary_fields": [{"field": "id", "type": "record_count"}],
                 "grouping": [{"field": "event_type", "type": "exact", "direction": "asc"}]})
groups = r.json()["data"]["groups"] if r.ok else r.text
rows.append(f"  _summarize grouped on event_type, starts_with Shotgun_Page -> {r.status_code}")
for g in groups if isinstance(groups, list) else []:
    rows.append(f"    {g['group_value']:<36} {g['summaries']['id']}")

for et in ("Shotgun_PageSetting_Change", "Shotgun_PageSetting_New", "Shotgun_Page_Change"):
    got = c.post("/entity/event_log_entries/_search", headers=P.ARR,
                 json={"filters": [["event_type", "is", et]], "fields": ["attribute_name", "meta", "created_at", "entity", "user"],
                       "sort": "-id", "page": {"size": 50}}).json().get("data", [])
    if not got:
        rows.append(f"  {et}: none")
        continue
    attrs = collections.Counter(x["attributes"]["attribute_name"] for x in got)
    rows.append(f"  {et}: newest 50 by attribute_name {dict(attrs)}; newest at {got[0]['attributes']['created_at']}")
    m = got[0]["attributes"]["meta"]
    rows.append(f"    newest meta keys {sorted(m) if isinstance(m, dict) else type(m).__name__}; "
                f"entity {json.dumps((P.rel(got[0], 'entity') or {}).get('type'))}")
    if isinstance(m, dict):
        for k in ("old_value", "new_value"):
            if k in m:
                v = m[k]
                rows.append(f"    meta.{k}: {type(v).__name__} {json.dumps(v)[:160]}")

rows.append("\n=== Shotgun_PageSetting_Change, the newest 500")
ch = c.post("/entity/event_log_entries/_search", headers=P.ARR,
            json={"filters": [["event_type", "is", "Shotgun_PageSetting_Change"]],
                  "fields": ["meta", "entity", "project", "user", "created_at"], "sort": "-id", "page": {"size": 500}}).json()["data"]
rows.append(f"  entity type: {dict(collections.Counter((P.rel(x, 'entity') or {}).get('type') for x in ch))}")
rows.append(f"  meta key sets: {dict(collections.Counter(tuple(sorted(x['attributes']['meta'] or {})) for x in ch))}")
rows.append(f"  change entry keys: {dict(collections.Counter(tuple(sorted(e)) for x in ch for e in (x['attributes']['meta'] or {}).get('changes') or []))}")
rows.append(f"  change setting names: {dict(collections.Counter(e.get('setting') for x in ch for e in (x['attributes']['meta'] or {}).get('changes') or []).most_common(10))}")
ex = next((x for x in ch if (x["attributes"]["meta"] or {}).get("changes")), None)
if ex:
    m = dict(ex["attributes"]["meta"], changes=ex["attributes"]["meta"]["changes"][:2])
    rows.append(f"  one: {json.dumps(m)[:500]}")
hist = [t for t in c.get("/schema").json()["data"] if "History" in t or "PageSetting" in t]
rows.append(f"  /schema types naming History or PageSetting: {hist}")
for t in hist:
    if t != "PageSetting":
        r = c.get(f"/schema/{t}/fields")
        rows.append(f"    /schema/{t}/fields -> {r.status_code} {sorted(r.json().get('data', {}))[:14] if r.ok else r.text[:160]}")

rows.append("\n=== Page.updated_at against its newest PageSetting_Change naming the page")
seen = 0
for x in ch:
    page = P.rel(x, "entity")
    if not page or page.get("type") != "Page":
        continue
    pg = c.get(f"/entity/pages/{page['id']}", params={"fields": "updated_at"})
    if not pg.ok:
        continue
    newest = c.post("/entity/event_log_entries/_search", headers=P.ARR,
                    json={"filters": [["entity", "is", {"type": "Page", "id": page["id"]}]],
                          "fields": ["event_type", "created_at"], "sort": "-id", "page": {"size": 1}}).json()["data"][0]
    rows.append(f"  setting change {x['attributes']['created_at'] if 'created_at' in x['attributes'] else ''}; "
                f"page's newest event {newest['attributes']['event_type']} at {newest['attributes']['created_at']}; "
                f"Page.updated_at {pg.json()['data']['attributes']['updated_at']}")
    seen += 1
    if seen == 4:
        break

_lib.emit("077_page_change_stamps", "\n".join(rows), env)
