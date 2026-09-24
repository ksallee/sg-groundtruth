"""Q: where does a status field's "Excluded statuses" setting (Summary = Status) show over REST, is it
writable, and does `_summarize` honour it?

Flow PT 8.88 added a per-field list of statuses the status summary ignores. A client drawing a status
roll-up needs to read that list and know whether the server already applied it.

Read only by default: reports where the setting is visible and what `_summarize` gives on the sandbox
Shots as they stand. With --write it provisions its own pair of Shots (one `fin`, one `omt`) so the
measurement does not depend on site rows, and asks PUT /schema whether the setting is writable. It
never changes the setting: it cannot read the current list back, so it could not restore it. Where the
API cannot write it, the precondition is the web interface's, and the output says which step.
"""
import json

import _lib
import _pages as P

env = _lib.load_env()
c = _lib.client()
SANDBOX = _lib.sandbox_id(c, env)
rows = []

rows.append("=== the schema, site scope against project scope, Shot against Asset")
for t in ("Shot", "Asset"):
    for label, params in (("site", None), ("project", {"project_id": SANDBOX})):
        r = c.get(f"/schema/{t}/fields/sg_status_list", params=params)
        props = r.json()["data"]["properties"]
        text = json.dumps(r.json())
        rows.append(f"  {t}.sg_status_list {label:<8} -> {r.status_code} properties {sorted(props)}; "
                    f"summary_default {props['summary_default']['value']!r}; "
                    f"'exclu' anywhere in the body: {'exclu' in text}")
r = c.get("/schema/Shot/fields", params={"project_id": SANDBOX})
rows.append(f"  GET /schema/Shot/fields?project_id -> {r.status_code}; 'exclu' anywhere: {'exclu' in r.text}")
r = c.get(f"{c.site}/api/v1.1/schema/Shot/fields/sg_status_list", params={"project_id": SANDBOX})
rows.append(f"  GET /api/v1.1/schema/Shot/fields/sg_status_list -> {r.status_code}; 'exclu' anywhere: {'exclu' in r.text}")
for path in ("/schema/DisplayColumn", "/entity/display_columns"):
    r = c.get(path)
    rows.append(f"  GET {path} -> {r.status_code} {r.json()['errors'][0]['detail'] if not r.ok else ''}")

rows.append("\n=== where the setting was written: the event log")
ev = c.post("/entity/event_log_entries/_search", headers=P.ARR,
            json={"filters": [["event_type", "is", "Shotgun_DisplayColumn_Change"], ["attribute_name", "is", "properties"]],
                  "fields": ["meta", "entity", "project", "created_at"], "sort": "-id", "page": {"size": 20}}).json()["data"]
hit = next((x for x in ev if "status_list_summary_exclude" in json.dumps(x["attributes"]["meta"])), None)
if hit:
    m = hit["attributes"]["meta"]
    rows.append(f"  Shotgun_DisplayColumn_Change, entity {json.dumps(P.rel(hit, 'entity'))}, "
                f"project {json.dumps(P.rel(hit, 'project'))}")
    rows.append(f"  old data_type_properties {json.dumps(m['old_value'].get('data_type_properties'))}")
    rows.append(f"  new data_type_properties {json.dumps(m['new_value'].get('data_type_properties'))}")
    rows.append(f"  new keys {sorted(m['new_value'])}")
else:
    rows.append("  no DisplayColumn change naming status_list_summary_exclude in the newest 20")

rows.append("\n=== _summarize on the sandbox Shots, with the excluded status present")
F = [["project", "is", {"type": "Project", "id": SANDBOX}]]


def summ(filters, fields, grouping=None):
    body = {"filters": filters, "summary_fields": fields}
    if grouping:
        body["grouping"] = grouping
    r = c.post("/entity/shots/_summarize", headers=P.ARR, json=body)
    return r.json()["data"] if r.ok else r.json()["errors"][0]


d = summ(F, [{"field": "id", "type": "count"}], [{"field": "sg_status_list", "type": "exact", "direction": "asc"}])
rows.append(f"  rows by status: {[(g['group_value'], g['summaries']['id']) for g in d['groups']]}")
SUMS = [{"field": "sg_status_list", "type": t} for t in ("status_list",)]
for label, extra in (("every Shot", []),
                     ("status in [fin, omt]", [["sg_status_list", "in", ["fin", "omt"]]]),
                     ("status in [ip, omt]", [["sg_status_list", "in", ["ip", "omt"]]]),
                     ("status is omt", [["sg_status_list", "is", "omt"]]),
                     ("control: status is fin", [["sg_status_list", "is", "fin"]]),
                     ("control: status in [fin, wtg]", [["sg_status_list", "in", ["fin", "wtg"]]])):
    out = {}
    for t in ("status_list", "status_percentage", "status_percentage_as_float"):
        x = summ(F + extra, [{"field": "sg_status_list", "type": t}, {"field": "id", "type": "count"}])
        out[t] = x["summaries"]["sg_status_list"] if "summaries" in x else x
        out["rows"] = x.get("summaries", {}).get("id")
    rows.append(f"  {label:<30} {json.dumps(out)}")

rows.append("\n=== is the setting writable over PUT /schema? (--write)")
if not _lib.writes_allowed():
    rows.append("  not attempted; rerun with --write")
else:
    # Rejected names are the probe: a 400 that lists the legal property names changes nothing.
    for name in ("zzprobe_091_not_a_property", "status_list_summary_exclude"):
        r = c.put("/schema/Shot/fields/sg_status_list",
                  json={"properties": [{"property_name": name, "value": "zzprobe"}],
                        "project_id": SANDBOX})
        body = r.json()
        rows.append(f"  PUT property_name {name!r} -> {r.status_code} "
                    f"{json.dumps(body.get('errors', [{}])[0]) if not r.ok else 'accepted'}")

rows.append("\n=== own rows: one fin Shot and one omt Shot (--write)")
if _lib.writes_allowed():
    with _lib.Created(c) as made:
        ids = []
        for st in ("fin", "omt"):
            r = c.post("/entity/shots", json={"code": f"zzprobe_091_{st}", "sg_status_list": st,
                                              "project": {"type": "Project", "id": SANDBOX}})
            if not r.ok:
                rows.append(f"  create {st} -> {r.status_code} {r.text}")
                continue
            ids.append(made.add("shots", r.json()["data"]["id"]))
        mine = [["id", "in", ids]]
        for label, extra in (("both", []), ("the omt one", [["sg_status_list", "is", "omt"]]),
                             ("the fin one", [["sg_status_list", "is", "fin"]])):
            x = summ(mine + extra, [{"field": "sg_status_list", "type": "status_list"}, {"field": "id", "type": "count"}])
            rows.append(f"  {label:<12} status_list {json.dumps(x['summaries']['sg_status_list'])} over {x['summaries']['id']} rows")
        x = summ(mine, [{"field": "sg_status_list", "type": "status_list"}], [{"field": "project", "type": "exact", "direction": "asc"}])
        rows.append(f"  both, grouped by project: group status_list "
                    f"{[g['summaries']['sg_status_list'] for g in x['groups']]}")
        both = summ(mine, [{"field": "sg_status_list", "type": "status_list"}])["summaries"]["sg_status_list"]
        if both != "fin":
            # A mixed pair rolls up to "ip" (probe 079); "fin" is what an exclusion of omt gives.
            rows.append("  PRECONDITION NOT MET, coverage untested: omt is not excluded on this site. In the web "
                        "interface open Fields, Shot, Status (sg_status_list), set Summary to Status and add "
                        "Omit to Excluded statuses, then rerun. PUT /schema cannot set it (above).")
else:
    rows.append("  not attempted; rerun with --write")

_lib.emit("091_status_summary_exclusions", "\n".join(rows), env)
