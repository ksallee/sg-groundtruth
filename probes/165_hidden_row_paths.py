"""Q: once a conditional see rule hides a row from a person, can they still reach it another way:
by id, by filter, by a dotted path, by `_summarize`, by text search, through a link on a row they do
see, or in the event log?

sg-bids wants vendor A kept out of vendor B's Bids. Probe 162 found that no REST call can add a rule,
so a Bid rule cannot be installed here. The Vendor group already has one on Shot: a Shot is visible
when `sg_vendor_groups` holds a Group the person is in (probe 162). That rule is measured instead,
with every path a Bid rule would face. The script makes Shot A awarded to group A and Shot B awarded
to group B, each with a description, changes Shot B's description so the log holds an
`attribute_change`, and adds a Bid Line on each Shot (Bid Line is visible to Vendor). Then vendor A
asks for Shot B every way the API offers; vendor B is the control.

Writes behind `--write`: the probe's fields if absent, rows `zzprobe_165_*` deleted on exit, and the
two people's permission group and Groups, restored.

    python probes/165_hidden_row_paths.py --write --people A,B --groups GA,GB
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _bids  # noqa: E402
import _lib  # noqa: E402
from _bids import ARR, said  # noqa: E402

env = _lib.load_env()
c = _lib.client()
if not _lib.writes_allowed():
    raise SystemExit("probe 165 writes; run with --write --people A,B --groups GA,GB")
SB = _lib.sandbox_id(c, env)
P = {"type": "Project", "id": SB}
S = _bids.slots(c)
LINE = _bids.slug(S["Bid Line"])
rows = []


def out(s=""):
    rows.append(str(s))
    print(s, flush=True)


out("===== fields")
F = _bids.ensure_fields(c, S, out)
LSHOT, AMT = F["zzprobe 163 shot"], F["zzprobe currency amount"]
GA, GB = _bids._ids("--groups")
NAMES = {}


def nm(x):
    return NAMES.get((x.get("type"), x.get("id")), f"{x.get('type')} {x.get('id')}") if x else None


def ids(r):
    return said(r) if not r.ok else sorted(nm(x) for x in r.json()["data"])


last_event = c.post("/entity/event_log_entries/_search", headers=ARR, json={
    "filters": [], "fields": ["id"], "sort": "-id", "page": {"size": 1}}).json()["data"][0]["id"]

with _lib.Created(c) as made:
    shots = {}
    for tag, g in (("A", GA), ("B", GB)):
        r = c.post("/entity/shots", json={"project": P, "code": f"zzprobe_165_shot_{tag}",
                                          "description": f"zzprobe 165 first {tag}",
                                          "sg_vendor_groups": [{"type": "Group", "id": g}]})
        shots[tag] = made.add("shots", r.json()["data"]["id"])
        NAMES[("Shot", shots[tag])] = f"shot {tag}"
    c.put(f"/entity/shots/{shots['B']}", json={"description": "zzprobe 165 price 250 B"})
    lines = {}
    for tag, amt in (("A", 100.0), ("B", 250.0)):
        r = c.post(f"/entity/{LINE}", json={"project": P, "code": f"zzprobe_165_line_{tag}",
                                             LSHOT: {"type": "Shot", "id": shots[tag]}, AMT: amt})
        lines[tag] = made.add(LINE, r.json()["data"]["id"])
        NAMES[(S["Bid Line"], lines[tag])] = f"line {tag}"
    out("\n===== rows, as the script: shot A for group A, shot B for group B, a Bid Line on each")
    B, LB = shots["B"], lines["B"]
    MINE = [["project", "is", P], ["code", "starts_with", "zzprobe_165"]]

    with _bids.vendors(c, env, SB, out) as vs:
        for (pid, v, g, _), who in zip(vs, ("vendor A", "vendor B, the control")):
            out(f"\n===== as {who}, asking for shot B")
            r = v.get(f"/entity/shots/{B}", params={"fields": "code,description"})
            out(f"  GET /entity/shots/<B> -> {said(r)}")
            r = v.get(f"/entity/shots/{B}/relationships/sg_vendor_groups")
            out(f"  GET /entity/shots/<B>/relationships/sg_vendor_groups -> {said(r)}")
            r = v.post("/entity/shots/_search", headers=ARR, json={"filters": [["id", "is", B]], "fields": ["code"]})
            out(f"  _search id is <B> -> {ids(r)}")
            r = v.post("/entity/shots/_search", headers=ARR, json={"filters": MINE, "fields": ["code"]})
            out(f"  _search code starts_with zzprobe_165 -> {ids(r)}")
            r = v.post("/entity/shots/_summarize", headers=ARR, json={
                "filters": MINE, "summary_fields": [{"field": "id", "type": "count"}],
                "grouping": [{"field": "code", "type": "exact", "direction": "asc"}]})
            d = r.json().get("data", {}) if r.ok else {}
            out(f"  _summarize Shots, count grouped by code -> {said(r)} {d.get('summaries')} "
                f"groups {[x.get('group_name') for x in d.get('groups', [])]}")
            r = v.post("/entity/_text_search", headers=ARR, json={
                "text": "zzprobe_165", "entity_types": {"Shot": [["project", "is", P]], S["Bid Line"]: [["project", "is", P]]}})
            out(f"  _text_search zzprobe_165 on Shot and Bid Line -> {said(r)} "
                + json.dumps([(x["type"].replace(S["Bid Line"], "<Bid Line>"), x["attributes"]["name"], x["attributes"].get("links"))
                              for x in (r.json()["data"] if r.ok else [])]))
            r = v.get(f"/entity/{LINE}/{LB}", params={"fields": f"code,{LSHOT},{LSHOT}.Shot.code,{LSHOT}.Shot.description"})
            if r.ok:
                d = r.json()["data"]
                out(f"  GET line B, its shot link -> {json.dumps(d['relationships'].get(LSHOT, {}).get('data'))}")
                out(f"    dotted {LSHOT}.Shot.code -> {d['attributes'].get(f'{LSHOT}.Shot.code', '<absent>')!r}, "
                    f".description -> {d['attributes'].get(f'{LSHOT}.Shot.description', '<absent>')!r}")
            else:
                out(f"  GET line B -> {said(r)}")
            for filt in ([f"{LSHOT}.Shot.code", "is", "zzprobe_165_shot_B"],
                         [f"{LSHOT}.Shot.description", "contains", "price 250"],
                         [LSHOT, "is", {"type": "Shot", "id": B}]):
                r = v.post(f"/entity/{LINE}/_search", headers=ARR, json={"filters": MINE + [filt], "fields": ["code"]})
                out(f"  _search Bid Lines where {filt[0]} {filt[1]} {filt[2] if not isinstance(filt[2], dict) else '<shot B>'} -> {ids(r)}")
            r = v.post(f"/entity/{LINE}/_summarize", headers=ARR, json={
                "filters": MINE, "summary_fields": [{"field": AMT, "type": "sum"}],
                "grouping": [{"field": LSHOT, "type": "exact", "direction": "asc"}]})
            d = r.json().get("data", {}) if r.ok else {}
            out(f"  _summarize Bid Lines, sum grouped by {LSHOT} -> {said(r)} "
                + json.dumps([(x.get("group_name"), x.get("group_value"), x.get("summaries")) for x in d.get("groups", [])], default=str))
            r = v.get(f"/entity/groups/{GB}", params={"fields": "code,shot_sg_vendor_groups_shots"})
            out(f"  GET group B, shot_sg_vendor_groups_shots -> {said(r)} "
                + (json.dumps([nm(x) for x in r.json()['data']['relationships']['shot_sg_vendor_groups_shots']['data']
                               if (x['type'], x['id']) in NAMES]) if r.ok else ""))
            r = v.get(f"/entity/groups/{GB}/relationships/shot_sg_vendor_groups_shots")
            out(f"  GET group B /relationships/shot_sg_vendor_groups_shots -> {said(r)} "
                + (json.dumps([nm(x) for x in r.json()['data'] if (x['type'], x['id']) in NAMES]) if r.ok else ""))
            r = v.post("/entity/event_log_entries/_search", headers=ARR, json={
                "filters": [["entity", "is", {"type": "Shot", "id": B}]], "fields": ["event_type", "meta", "entity"]})
            out(f"  event log, entity is <B> -> {said(r)} {len(r.json()['data']) if r.ok else ''}")
            r = v.post("/entity/event_log_entries/_search", headers=ARR, json={
                "filters": [["id", "greater_than", last_event], ["event_type", "in", ["Shotgun_Shot_New", "Shotgun_Shot_Change"]]],
                "fields": ["event_type", "attribute_name", "meta", "entity"], "page": {"size": 200}})
            if r.ok:
                about_b = [x for x in r.json()["data"] if (x["attributes"].get("meta") or {}).get("entity_id") == B]
                out(f"  event log since setup, Shot events -> {len(r.json()['data'])}; about shot B {len(about_b)}")
                out(f"    attribute_name of each: {[x['attributes'].get('attribute_name') for x in about_b]}")
                for x in about_b:
                    m = x["attributes"]["meta"]
                    if x["attributes"].get("attribute_name") in (None, "code", "description"):
                        out(f"    {x['attributes']['event_type']} {x['attributes'].get('attribute_name')} "
                            f"old_value {m.get('old_value')!r} new_value {m.get('new_value')!r} "
                            f"entity {json.dumps(x['relationships']['entity']['data'])}")
            else:
                out(f"  event log since setup -> {said(r)}")
            out(f"  GET /entity/shots/<B>/activity_stream -> {said(v.get(f'/entity/shots/{B}/activity_stream'))}")
_lib.emit("165_hidden_row_paths", "\n".join(rows), env)
