"""Q: how does a page's shared settings_json store its widgets, its views and its tabs, and does the tree
hold the layout name `/exports/page/<id>/<layout>` takes?

Probe 023 read one tree down to `body/list_content`. A client reproducing pages needs every shape: a
page with several views, a page with several list widgets, a detail page's tabs. Site-wide, read only.
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
settings = P.settings(c, by_id)
trees = P.shared(settings)
per_page = collections.Counter(P.rel(x, "page")["id"] for x in settings
                               if P.rel(x, "page") and P.rel(x, "user") is None)
rows.append(f"=== {len(pages)} listed pages, {len(settings)} PageSetting rows, "
            f"{sum(1 for x in settings if P.rel(x, 'user') is None)} shared")
rows.append(f"  shared rows per page: {dict(collections.Counter(per_page.values()))}")
rows.append(f"  pages with no shared row: {len(set(by_id) - set(trees))}")
for pid, n in per_page.items():
    if n > 1:
        a = by_id[pid]["attributes"]
        rows.append(f"  page {pid} holds {n} shared rows: page_type {a['page_type']!r} "
                    f"system_owned {a['system_owned']}")

rows.append("\n=== widget types over every shared tree")
types, per_type = collections.Counter(), collections.defaultdict(collections.Counter)
for pid, t in trees.items():
    pt = by_id[pid]["attributes"]["page_type"]
    for path, w in P.walk(t):
        types[w["type"]] += 1
        per_type[pt][(P.shape(path), w["type"])] += 1
rows.append(f"  {len(types)} distinct types, {sum(types.values())} widgets")
for name, n in types.most_common(14):
    rows.append(f"    {n:>6}  {name}")

rows.append("\n=== root path of every query widget (EntityQueryPage), by page_type")
qpaths = collections.Counter()
for pid, t in trees.items():
    for path, w in P.walk(t):
        if w["type"] == P.QUERY:
            qpaths[(by_id[pid]["attributes"]["page_type"], P.shape(path))] += 1
for (pt, path), n in qpaths.most_common(12):
    rows.append(f"    {n:>5}  {pt:<16} {path}")
rows.append(f"    ... {len(qpaths)} distinct (page_type, path)")

rows.append("\n=== query widgets per page")
qcount = {pid: sum(1 for _, w in P.walk(t) if w["type"] == P.QUERY) for pid, t in trees.items()}
top = collections.Counter(qcount.values())
rows.append(f"  {dict(sorted(top.items()))}")
canvas = [pid for pid in trees if by_id[pid]["attributes"]["page_type"] == "canvas"]
rows.append(f"  canvas pages: {len(canvas)}; with a query at /body: "
            f"{sum(1 for p in canvas if (trees[p].get('children') or {}).get('body', {}).get('type') == P.QUERY)}")

rows.append("\n=== views: root settings.layouts")
with_layouts = {pid: t for pid, t in trees.items() if (t.get("settings") or {}).get("layouts")}
rows.append(f"  pages whose root settings hold `layouts`: {len(with_layouts)}; "
            f"by page_type {dict(collections.Counter(by_id[p]['attributes']['page_type'] for p in with_layouts))}")
root_keys = collections.Counter(k for t in trees.values() for k in (t.get("settings") or {}))
rows.append(f"  root settings keys, every tree: {dict(root_keys)}")
nviews = collections.Counter(len(t["settings"]["layouts"]) for t in with_layouts.values())
rows.append(f"  views per page: {dict(sorted(nviews.items()))}")
entry_keys = collections.Counter(k for t in with_layouts.values() for v in t["settings"]["layouts"] for k in v)
rows.append(f"  keys of one layouts[] entry: {dict(entry_keys)}")
match = collections.Counter()
for t in with_layouts.values():
    kids = set(t.get("children") or {})
    for v in t["settings"]["layouts"]:
        match["name is a key of children" if v["name"] in kids else "name absent from children"] += 1
rows.append(f"  layouts[].name against the root's children: {dict(match)}")
names = collections.Counter(v["name"] for t in with_layouts.values() for v in t["settings"]["layouts"])
rows.append(f"  layouts[].name values: {dict(names.most_common(8))}")
multi = next((p for p, t in with_layouts.items() if len(t["settings"]["layouts"]) > 1
              and by_id[p]["attributes"]["page_type"] == "canvas"), None)
if multi:
    t = trees[multi]
    rows.append(f"  page {multi}: layouts {json.dumps(t['settings']['layouts'])}")
    rows.append(f"    selected_layout {json.dumps(t['settings'].get('selected_layout'))}; "
                f"root children {sorted(t['children'])}")
    for k, w in sorted(t["children"].items()):
        rows.append(f"    /{k:<12} {w['type']}  settings keys {sorted(w.get('settings') or {})[:6]}")

rows.append("\n=== tabs: SG.Widget.Tabs tab_order")
tab_entry, tab_kids = collections.Counter(), collections.Counter()
for t in trees.values():
    for path, w in P.walk(t):
        if w["type"] == "SG.Widget.Tabs" or "tab_order" in (w.get("settings") or {}):
            order = (w.get("settings") or {}).get("tab_order") or []
            kids = set(w.get("children") or {})
            for e in order:
                tab_entry.update(e.keys())
                tab_kids["tab_order name is a child" if e.get("name") in kids else "name absent"] += 1
rows.append(f"  keys of a tab_order entry: {dict(tab_entry)}")
rows.append(f"  tab_order[].name against the widget's children: {dict(tab_kids)}")

rows.append("\n=== exports: the name /exports/page/<id>/<layout>.csv takes")
if multi:
    t = trees[multi]
    for label, name in (("page alone", None), ("layouts[0].name", t["settings"]["layouts"][0]["name"]),
                        ("layouts[1].name", t["settings"]["layouts"][1]["name"]),
                        ("layouts[1].display_name", t["settings"]["layouts"][1]["display_name"]),
                        ("a name no view has", "zzprobe_072_not_a_view")):
        path = f"/exports/page/{multi}.csv" if name is None else f"/exports/page/{multi}/{name}.csv"
        r = c.get(path)
        rows.append(f"  {label:<24} -> {r.status_code} {r.text[:160]!r}")
    _lib.note_names(*[v["display_name"] for v in t["settings"]["layouts"]])
_lib.note_from([p["attributes"] for p in pages if p["id"] in with_layouts])

_lib.emit("072_page_layouts", "\n".join(rows), env)
