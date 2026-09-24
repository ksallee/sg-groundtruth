"""Q: which grid settings do stored pages use: grouping depth, column summaries, formatting rules, pivot
grouping, and which `mode` values?

A client that reproduces a page has to implement every setting a real page stores and may skip the rest.
Tally every query widget (EntityQueryPage) and its list grid (`list_content`, a NewGrid) over every
listed page's shared tree. Site-wide, read only.
"""
import collections
import json

import _lib
import _pages as P

env = _lib.load_env()
c = _lib.client()
rows = []

pages = P.pages(c)
by_id = {p["id"]: p for p in pages}
trees = P.shared(P.settings(c, by_id))

queries, grids = [], []   # (page id, path, settings)
for pid, t in trees.items():
    for path, w in P.walk(t):
        if w["type"] == P.QUERY:
            queries.append((pid, path, w.get("settings") or {}))
            lc = (w.get("children") or {}).get("list_content")
            if lc:
                grids.append((pid, path, lc.get("settings") or {}, w.get("settings") or {}))
top = [q for q in queries if q[1] == "/body" or "/layout_" in q[1]]
rows.append(f"=== {len(queries)} query widgets on {len(trees)} pages; {len(top)} are a page's own "
            f"(/body or inside a canvas view), the rest are embedded tabs; {len(grids)} carry a list grid")

key_tally = collections.Counter(k for _, _, s in queries for k in s)
rows.append(f"  query settings keys: {dict(key_tally.most_common())}")
gkey = collections.Counter(k for _, _, g, _ in grids for k in g)
rows.append(f"  list grid settings keys: {dict(gkey.most_common())}")


def tally(label, sel, fn):
    ct = collections.Counter(fn(s) for s in sel)
    rows.append(f"  {label:<34} {dict(ct.most_common(10))}")


rows.append("\n=== mode (which child view is showing)")
tally("mode, every query widget", [s for _, _, s in queries], lambda s: s.get("mode"))
tally("mode, page's own", [s for _, _, s in top], lambda s: s.get("mode"))
kids = collections.Counter()
for pid, t in trees.items():
    for path, w in P.walk(t):
        if w["type"] == P.QUERY:
            kids[tuple(sorted(w.get("children") or {}))] += 1
for k, n in kids.most_common(3):
    rows.append(f"  children {n:>5}x {list(k)}")

rows.append("\n=== grouping")
tally("query grouping, type", [s for _, _, s in queries],
      lambda s: type(s.get("grouping")).__name__ if "grouping" in s else "absent")
tally("query grouping, depth", [s for _, _, s in queries if isinstance(s.get("grouping"), list)],
      lambda s: len(s["grouping"]))
tally("grouping method", [g for _, _, s in queries if isinstance(s.get("grouping"), list)
                          for g in s["grouping"]], lambda g: g.get("method"))
tally("grouping entry keys", [g for _, _, s in queries if isinstance(s.get("grouping"), list)
                              for g in s["grouping"]], lambda g: tuple(sorted(g)))
deep = next((s["grouping"] for _, _, s in queries if isinstance(s.get("grouping"), list)
             and len(s["grouping"]) > 1), None)
rows.append(f"  deepest example: {json.dumps(deep)}")
tally("grid grouping (list_content)", [g for _, _, g, _ in grids],
      lambda g: type(g.get("grouping")).__name__ if "grouping" in g else "absent")
tally("group_settings value types", [s for _, _, s in queries if s.get("group_settings")],
      lambda s: tuple(sorted({str(v) for v in s["group_settings"].values()})))

rows.append("\n=== sorts: the query's and the grid's")
tally("query sorts depth", [s for _, _, s in queries if "sorts" in s], lambda s: len(s["sorts"] or []))
tally("grid sorts depth", [g for _, _, g, _ in grids if "sorts" in g], lambda g: len(g["sorts"] or []))
both = [(g["sorts"], s["sorts"]) for _, _, g, s in grids if g.get("sorts") and s.get("sorts")]
rows.append(f"  both set: {len(both)}, equal on {sum(1 for a, b in both if a == b)}")

rows.append("\n=== pivot grouping (the rollup columns)")
tally("pivot_grouping entries", [s for _, _, s in queries if "pivot_grouping" in s],
      lambda s: json.dumps(s["pivot_grouping"]))
tally("pivot_sorts", [s for _, _, s in queries if "pivot_sorts" in s], lambda s: json.dumps(s["pivot_sorts"]))
pivot_cols = collections.Counter(c_ for _, _, g, _ in grids for c_ in g.get("columns") or []
                                 if "step_" in c_ or "$" in c_)
rows.append(f"  pivot-shaped columns (step_N, or with $): {sum(pivot_cols.values())} over "
            f"{len(pivot_cols)} names, e.g. {list(pivot_cols)[:5]}")

rows.append("\n=== column summaries (list grid `summaries`)")
summ = [(pid, g["summaries"], g.get("summary_state")) for pid, _, g, _ in grids if g.get("summaries")]
rows.append(f"  grids with summaries: {len(summ)} on {len({p for p, _, _ in summ})} pages")
tally("summary_state", [g for _, _, g, _ in grids if "summary_state" in g], lambda g: g["summary_state"])
tally("summary type", [v for _, s, _ in summ for v in s.values()], lambda v: v.get("type"))
tally("summary entry keys", [v for _, s, _ in summ for v in s.values()], lambda v: tuple(sorted(v)))
tally("summary key shape", [k for _, s, _ in summ for k in s],
      lambda k: "has $" if "$" in k else ("dotted" if "." in k else "plain"))
for _, s, _ in summ[:1]:
    rows.append(f"  example: {json.dumps(dict(list(s.items())[:3]))}")
col_match = collections.Counter()
for _, _, g, _ in grids:
    for k in (g.get("summaries") or {}):
        col_match["key is a column" if k in (g.get("columns") or []) else "key not in columns"] += 1
rows.append(f"  summaries key against the grid's columns: {dict(col_match)}")

rows.append("\n=== formatting_rules")
fr = [(pid, s["formatting_rules"]) for pid, _, s in queries if s.get("formatting_rules")]
rows.append(f"  widgets with rules: {len(fr)}; rules: {sum(len(r) for _, r in fr)}")
tally("rule keys", [r for _, rs in fr for r in rs], lambda r: tuple(sorted(r)))
tally("rule_type", [r for _, rs in fr for r in rs], lambda r: r.get("rule_type"))
tally("display_column type", [r for _, rs in fr for r in rs], lambda r: (r.get("display_column") or {}).get("type"))
tally("rule page_id is its own page", [(pid, r) for pid, rs in fr for r in rs],
      lambda x: str(x[1].get("page_id")) == str(x[0]))
ex = next((r for _, rs in fr for r in rs if r.get("condition")), fr[0][1][0] if fr else None)
rows.append(f"  a row rule with a condition: {json.dumps(ex)[:700]}")
r = c.get("/schema/DisplayColumn")
rows.append(f"  GET /schema/DisplayColumn -> {r.status_code} {r.text[:120]}")
r = c.get("/entity/display_columns", params={"page[size]": 1})
rows.append(f"  GET /entity/display_columns -> {r.status_code} {r.text[:160]}")

rows.append("\n=== the rest a runner has to honour or refuse")
tally("records_per_page", [g for _, _, g, _ in grids if "records_per_page" in g], lambda g: g["records_per_page"])
tally("server_side_filters", [s for _, _, s in queries if "server_side_filters" in s],
      lambda s: s["server_side_filters"])
tally("get_filters_from_context", [s for _, _, s in queries if "get_filters_from_context" in s],
      lambda s: s["get_filters_from_context"])
tally("parent_entity_filters (type)", [s for _, _, s in queries if "parent_entity_filters" in s],
      lambda s: json.dumps(s["parent_entity_filters"])[:60])
tally("context_entity_token", [s for _, _, s in queries if "context_entity_token" in s],
      lambda s: json.dumps(s["context_entity_token"])[:60])
tally("pinned_columns", [g for _, _, g, _ in grids if "pinned_columns" in g], lambda g: len(g["pinned_columns"]))

_lib.emit("073_page_grid_settings", "\n".join(rows), env)
