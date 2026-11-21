"""Q: can a Shot carry the total of its linked Bid Lines, as a query (summary) field created over
the API, and if not, what call returns the totals?

sg-bids shows each Shot's bid total. A query field is a `summary` field in `/schema` (field_types
/summary); `/spec.json`'s `CreateFieldRequest` enum does not list `summary` (probe 160). This sends
the create anyway, on Shot and on Bid, with the properties a summary field reads back with, then
reads the totals the other ways: `_summarize` on Bid Lines grouped by their Shot link, a dotted read
through the reverse field the link made on Shot, and a filter through it.

Writes behind `--write`: the probe's fields if absent, two Shots and three Bid Lines `zzprobe_167_*`
deleted on exit. A summary field the create makes is retired at once.

    python probes/167_rollup_on_shot.py --write
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _bids  # noqa: E402
import _lib  # noqa: E402
from _bids import ARR, HSH, said  # noqa: E402

env = _lib.load_env()
c = _lib.client()
if not _lib.writes_allowed():
    raise SystemExit("probe 167 writes; run with --write")
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
shot_fields = c.get("/schema/Shot/fields").json()["data"]
rev = [k for k, v in shot_fields.items() if v["data_type"]["value"] == "multi_entity"
       and v["properties"].get("valid_types", {}).get("value") == [S["Bid Line"]]]
out(f"  reverse field on Shot holding Bid Lines: {rev}")
REV = rev[0]

out("\n===== POST /schema/<Type>/fields, data_type summary")
token = {"id": 0, "name": "Current Entity", "type": "Entity", "valid": "parent_entity_token"}
query = {"entity_type": S["Bid Line"], "filters": {"logical_operator": "and", "conditions": [
    {"path": LSHOT, "relation": "is", "values": [token]}]}}
retire = []
for owner, label in (("Shot", "Shot"), (S["Bid"], "<Bid>")):
    for props in ([{"property_name": "name", "value": "zzprobe 167 bid total"}],
                  [{"property_name": "name", "value": "zzprobe 167 bid total"},
                   {"property_name": "summary_default", "value": "sum"},
                   {"property_name": "query", "value": query},
                   {"property_name": "summary_field", "value": AMT}]):
        r = c.post(f"/schema/{owner}/fields", json={"data_type": "summary", "properties": props})
        out(f"  {label}, properties {[p['property_name'] for p in props]} -> {said(r).replace(S['Bid Line'], '<Bid Line>')}")
        if r.status_code == 201:
            retire.append((owner, r.json()["links"]["self"].rsplit("/", 1)[-1]))
r = c.put(f"/schema/{S['Bid Line']}/fields/{AMT}", json={"properties": [{"property_name": "summary_default", "value": "sum"}]})
sd = c.get(f"/schema/{S['Bid Line']}/fields/{AMT}").json()["data"]["properties"]["summary_default"]["value"]
out(f"  PUT summary_default 'sum' on the currency field itself -> {said(r)}; reads {sd!r}")
r = c.put(f"/schema/{S['Bid Line']}/fields/{AMT}", json={"properties": [{"property_name": "summary_default", "value": "none"}]})
out(f"  put back to 'none' -> {said(r)}")
for owner, name in retire:
    out(f"  retire {name} -> {said(c.delete(f'/schema/{owner}/fields/{name}'))}")

with _lib.Created(c) as made:
    shots = {}
    for tag in ("A", "B"):
        shots[tag] = made.add("shots", c.post("/entity/shots", json={"project": P, "code": f"zzprobe_167_shot_{tag}"}).json()["data"]["id"])
    for tag, amt in (("A", 1200.50), ("A", 799.50), ("B", 300.25)):
        made.add(LINE, c.post(f"/entity/{LINE}", json={"project": P, "code": f"zzprobe_167_line_{tag}",
                                                       LSHOT: {"type": "Shot", "id": shots[tag]}, AMT: amt}).json()["data"]["id"])
    out("\n===== rows: shot A with Bid Lines 1200.50 and 799.50, shot B with 300.25")
    MINE = [["project", "is", P], ["code", "starts_with", "zzprobe_167"]]
    r = c.post(f"/entity/{LINE}/_summarize", headers=ARR, json={
        "filters": MINE, "summary_fields": [{"field": AMT, "type": "sum"}],
        "grouping": [{"field": LSHOT, "type": "exact", "direction": "asc"}]})
    out(f"  _summarize Bid Lines, sum grouped by {LSHOT} -> {said(r)}")
    out("    " + json.dumps(r.json()["data"], default=str)[:700])
    r = c.post(f"/entity/{LINE}/_summarize", headers=ARR, json={
        "filters": MINE + [[LSHOT, "in", [{"type": "Shot", "id": i} for i in shots.values()]]],
        "summary_fields": [{"field": AMT, "type": "sum"}, {"field": "id", "type": "count"}],
        "grouping": [{"field": LSHOT, "type": "exact", "direction": "asc"}]})
    out(f"  the same with [{LSHOT}, in, [the Shots]] and a count -> "
        + json.dumps([(g["group_name"], g["summaries"]) for g in r.json()["data"]["groups"]]))
    r = c.get(f"/entity/shots/{shots['A']}", params={"fields": f"code,{REV},{REV}.{S['Bid Line']}.{AMT}"})
    a = r.json()["data"]
    out(f"  GET shot A fields {REV},{REV}.<Bid Line>.{AMT} -> {len(a['relationships'][REV]['data'])} links; "
        f"dotted key present: {any(k.startswith(REV + '.') for k in a['attributes'])}")
    r = c.post("/entity/shots/_search", headers=ARR, json={
        "filters": MINE + [[f"{REV}.{S['Bid Line']}.{AMT}", "greater_than", 1000.0]], "fields": ["code"]})
    out(f"  _search Shots where {REV}.<Bid Line>.{AMT} greater_than 1000.0 -> "
        f"{[x['attributes']['code'] for x in r.json()['data']] if r.ok else said(r)}")
    r = c.post("/entity/shots/_summarize", headers=ARR, json={
        "filters": MINE, "summary_fields": [{"field": f"{REV}.{S['Bid Line']}.{AMT}", "type": "sum"}]})
    out(f"  _summarize Shots, sum of {REV}.<Bid Line>.{AMT} -> {said(r).replace(S['Bid Line'], '<Bid Line>')} "
        f"{r.json().get('data') if r.ok else ''}")
_lib.emit("167_rollup_on_shot", "\n".join(rows), env)
