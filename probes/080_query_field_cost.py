"""Q: can one `_summarize` grouped on the link reproduce a query field's value for N rows at once, and
what do N per-row calls cost?

Recipe 003 resolves a query field one row at a time. A page of 300 Shots showing `open_notes_count`
would cost 300 calls. If the parent-token condition becomes `in [the N rows]` and the call groups on
that link, one call answers all N. Sample project, read only.
"""
import json
import statistics
import time

import _lib
import _pages as P

env = _lib.load_env()
c = _lib.client()
PROJECT = _lib.sample_projects(c, env)[0]
rows = []
N_PER_ROW = 50

props = c.get("/schema/Shot/fields/open_notes_count").json()["data"]["properties"]
query, agg = props["query"]["value"], props["summary_default"]["value"]
target, column = query["entity_type"], props["summary_field"]["value"]
rows.append(f"=== Shot.open_notes_count: {agg} of {target}.{column}")
rows.append(f"  stored query {json.dumps(query['filters'])[:400]}")


def convert(node, parent):
    """Recipe 003's walk; `parent` is what the parent_entity_token leaf becomes."""
    if "conditions" in node:
        return {"logical_operator": node.get("logical_operator", "and"),
                "conditions": [convert(x, parent) for x in node["conditions"]]}
    v = node["values"][0] if node.get("values") else None
    if isinstance(v, dict) and v.get("valid") == "parent_entity_token":
        return parent(node["path"])
    if isinstance(v, dict):
        v = {"type": v["type"], "id": v["id"]}
    return [node["path"], node["relation"], v]


def summarize(filters, grouping=None):
    body = {"filters": filters, "summary_fields": [{"field": column, "type": agg}]}
    if grouping:
        body["grouping"] = grouping
    t = time.perf_counter()
    r = c.post(f"/entity/{target.lower()}s/_summarize", headers=P.HASH, json=body)
    ms = (time.perf_counter() - t) * 1000
    return (r.json()["data"] if r.ok else r.json()["errors"][0]), ms


shots = P.search(c, "shots", [["project", "is", {"type": "Project", "id": PROJECT}]], ["open_notes_count"])
stored = {s["id"]: s["attributes"]["open_notes_count"] for s in shots}
rows.append(f"  {len(shots)} Shots in the project")

rows.append(f"\n=== per row: one _summarize per Shot, first {N_PER_ROW}")
per_row, times = {}, []
for s in shots[:N_PER_ROW]:
    ref = {"type": "Shot", "id": s["id"]}
    d, ms = summarize(convert(query["filters"], lambda path: [path, "is", ref]))
    per_row[s["id"]] = d["summaries"][column]
    times.append(ms)
rows.append(f"  {N_PER_ROW} calls, {sum(times):.0f} ms total, median {statistics.median(times):.0f} ms, "
            f"max {max(times):.0f} ms")
rows.append(f"  resolved equals the stored field on {sum(1 for k, v in per_row.items() if v == stored[k])} of {len(per_row)}")

rows.append("\n=== grouped: the parent leaf becomes `in [N rows]`, grouped on the same path")
for n in (N_PER_ROW, len(shots)):
    refs = [{"type": "Shot", "id": s["id"]} for s in shots[:n]]
    link = next(l_["path"] for l_ in P.leaves(query["filters"])
                if any(isinstance(v, dict) and v.get("valid") == "parent_entity_token" for v in l_.get("values") or []))
    d, ms = summarize(convert(query["filters"], lambda path: [path, "in", refs]),
                      [{"field": link, "type": "exact", "direction": "asc"}])
    if "groups" not in d:
        rows.append(f"  N={n}: {json.dumps(d)}")
        continue
    # A multi_entity grouping keys on the row's whole link list, so one group can name several
    # Shots, and a Shot can sit in several groups. Credit every Shot a group names.
    got = {}
    other = 0
    for g in d["groups"]:
        gv = g["group_value"] if isinstance(g["group_value"], list) else [g["group_value"]]
        named = [x["id"] for x in gv if isinstance(x, dict) and x.get("type") == "Shot"]
        if len(gv) != 1 or not named:
            other += 1
        for i in named:
            got[i] = got.get(i, 0) + g["summaries"][column]
    ids = [s["id"] for s in shots[:n]]
    truth = per_row if n == N_PER_ROW else stored
    agree = sum(1 for i in ids if got.get(i, 0) == (truth.get(i) or 0))
    rows.append(f"  N={n:<4} one call {ms:.0f} ms; {len(d['groups'])} groups ({other} naming more or other than one Shot); "
                f"agrees with {'per-row' if n == N_PER_ROW else 'stored'} on {agree} of {n} "
                f"(a Shot with no group reads 0)")
    kinds = {(type(g["group_value"]).__name__, len(g["group_value"]) if isinstance(g["group_value"], list) else 1)
             for g in d["groups"]}
    rows.append(f"    group_value (type, length): {sorted(kinds)}; first {json.dumps(d['groups'][0]['group_value'])}")
    miss = [(i, got.get(i, 0), truth.get(i)) for i in ids if got.get(i, 0) != (truth.get(i) or 0)][:5]
    if miss:
        rows.append(f"    disagreements (shot, grouped, reference): {miss}")

rows.append("\n=== a note linked to two Shots: counted once per Shot?")
multi = P.search(c, "notes", [["project", "is", {"type": "Project", "id": PROJECT}]], ["note_links"], size=500)
two = [n for n in multi if sum(1 for x in (P.rel(n, "note_links") or []) if x["type"] == "Shot") > 1]
rows.append(f"  notes in the project {len(multi)}, linked to more than one Shot {len(two)}")

_lib.emit("080_query_field_cost", "\n".join(rows), env)
