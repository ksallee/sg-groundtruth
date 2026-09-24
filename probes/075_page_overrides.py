"""Q: which spec_paths and settings keys do the per-user PageSetting arrays patch, and does a user ever
hold more than one row for one page?

Probe 023 found the per-user row is `[{spec_path, settings}]`. A runner that honours a person's view
needs to know what those patches touch: columns only, or filters and sorts too. Site-wide, read only.
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
mine = [x for x in settings if P.rel(x, "user")]
rows.append(f"=== {len(settings)} PageSetting rows on {len(pages)} listed pages; {len(mine)} have a user")
rows.append(f"  user type: {dict(collections.Counter(P.rel(x, 'user')['type'] for x in mine))}")
rows.append(f"  settings_json type: {dict(collections.Counter(type(x['attributes']['settings_json']).__name__ for x in mine))}")
rows.append(f"  distinct users: {len({P.rel(x, 'user')['id'] for x in mine})}, distinct pages: "
            f"{len({P.rel(x, 'page')['id'] for x in mine})}")
pairs = collections.Counter((P.rel(x, "user")["id"], P.rel(x, "page")["id"]) for x in mine)
rows.append(f"  rows per (user, page): {dict(collections.Counter(pairs.values()))}")
rows.append(f"  page_type of an overridden page: "
            f"{dict(collections.Counter(by_id[P.rel(x, 'page')['id']]['attributes']['page_type'] for x in mine))}")

rows.append("\n=== what a patch touches")
patches = [p for x in mine for p in (x["attributes"]["settings_json"] or [])]
rows.append(f"  patches: {len(patches)}; per row {dict(collections.Counter(len(x['attributes']['settings_json'] or []) for x in mine))}")
rows.append(f"  keys of a patch: {dict(collections.Counter(k for p in patches for k in p))}")
sp = collections.Counter(p.get("spec_path") for p in patches)
rows.append(f"  spec_path: {dict(sp.most_common())}")
keys = collections.Counter((p.get("spec_path"), k) for p in patches for k in (p.get("settings") or {}))
for (path, k), n in keys.most_common(20):
    rows.append(f"    {n:>3}  {path:<24} {k}")

rows.append("\n=== does the spec_path resolve on the shared tree")
shared = P.shared(settings)
res = collections.Counter()
for x in mine:
    tree = shared.get(P.rel(x, "page")["id"])
    for p in x["attributes"]["settings_json"] or []:
        node = tree
        for seg in [x for x in (p.get("spec_path") or "").split("|") if x]:   # "" is the root
            node = ((node or {}).get("children") or {}).get(seg)
        res["resolves to a widget" if node and "type" in node else "no such path"] += 1
        if node and "type" in node:
            res[f"  widget {node['type']}"] += 1
rows.append(f"  {dict(res)}")

rows.append("\n=== one patch against its shared widget")
for x in mine:
    tree = shared.get(P.rel(x, "page")["id"])
    for p in x["attributes"]["settings_json"] or []:
        node = tree
        for seg in (p.get("spec_path") or "").split("|"):
            node = ((node or {}).get("children") or {}).get(seg)
        if node and (p.get("settings") or {}).get("columns"):
            base = (node.get("settings") or {}).get("columns")
            rows.append(f"  shared columns {json.dumps(base)}")
            rows.append(f"  patch  columns {json.dumps(p['settings']['columns'])}")
            rows.append(f"  patch keys {sorted(p['settings'])}")
            break
    else:
        continue
    break

rows.append("\n=== site-wide, pages the listing no longer returns")
all_user = P.search(c, "page_settings", [["user", "is_not", None]], ["page", "user"])
orphan = [x for x in all_user if not P.rel(x, "page") or P.rel(x, "page")["id"] not in by_id]
rows.append(f"  user-owned PageSetting rows site-wide: {len(all_user)}; on a page not listed or null: {len(orphan)}")

_lib.emit("075_page_overrides", "\n".join(rows), env)
