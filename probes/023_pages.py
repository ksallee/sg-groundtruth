"""Q: what are Pages over REST, and can a client read a page's settings and its visible columns?

A page is the closest thing a site has to a written statement of what its team looks at: which entity
type, which columns in which order, filtered and grouped how. The question is whether that configuration
is readable, and whether a project page and a site-level page answer differently.
"""
import collections
import json

import _lib

env = _lib.load_env()
c = _lib.client()
PROJECT = _lib.sample_projects(c, env)[0]
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
rows = []


def search(slug, filters, fields, size=500):
    out, n = [], 1
    while True:
        r = c.post(f"/entity/{slug}/_search", headers=ARR,
                   json={"filters": filters, "fields": fields, "page": {"size": size, "number": n}})
        if not r.ok:
            return f"ERR {r.status_code} {r.text}"
        d = r.json()["data"]
        if not d:
            return out
        out += d
        n += 1


def count(slug, filters):
    r = c.post(f"/entity/{slug}/_summarize", headers=ARR,
               json={"filters": filters, "summary_fields": [{"field": "id", "type": "record_count"}]})
    return r.json()["data"]["summaries"]["id"] if r.ok else f"ERR {r.status_code} {r.text}"


def rel(row, name):
    return (row["relationships"].get(name) or {}).get("data")


rows.append("=== which types in /schema mention a page")
types = c.get("/schema").json()["data"]
hits = [t for t in types if any(w in t.lower() for w in ("page", "column", "layout", "view", "tab"))]
rows.append(f"  {len(types)} types; matching: {hits}")
rows.append(f"  /schema/DisplayColumn -> {c.get('/schema/DisplayColumn').status_code} "
            f"{json.dumps(c.get('/schema/DisplayColumn').json()['errors'][0]['detail'])}")

rows.append("\n=== their fields")
for t in hits:
    d = c.get(f"/schema/{t}/fields").json()["data"]
    rows.append(f"  {t}: {len(d)} fields")
    for name, spec in sorted(d.items()):
        rows.append(f"    {name:<32} {spec['data_type']['value']:<14} editable={spec['editable']['value']}")

rows.append("\n=== do they read, and what is in a row")
for slug in ("pages", "page_hits", "page_settings"):
    r = c.get(f"/entity/{slug}", params={"page[size]": 1})
    body = r.json()["data"]
    rows.append(f"  GET /entity/{slug} -> {r.status_code}, attributes without ?fields: {body[0]['attributes']}")

PAGE_FIELDS = ["name", "page_type", "entity_type", "ui_category", "project", "system_owned", "shared",
               "admin", "current_user_can_see", "folder", "description", "updated_at", "created_by"]
one = c.get("/entity/pages", params={"filter[project.Project.id]": PROJECT,
                                     "filter[page_type]": "canvas",
                                     "fields": ",".join(PAGE_FIELDS), "page[size]": 1}).json()["data"][0]
_lib.note_from(one)
rows.append("  one Page row:")
rows.append("  " + json.dumps(one, indent=1)[:900].replace("\n", "\n  "))

rows.append("\n=== project pages versus site-level pages")
pages = search("pages", [], PAGE_FIELDS)
site = [p for p in pages if rel(p, "project") is None]
_lib.note_from(pages)
rows.append(f"  paged listing: {len(pages)} pages, project set on {len(pages) - len(site)}, null on {len(site)}")
rows.append(f'  _search ["project","is",null] -> {len(search("pages", [["project", "is", None]], ["id"]))}')
by_proj = c.get("/entity/pages", params={"filter[project.Project.id]": PROJECT, "fields": "id",
                                         "page[size]": 500}).json()["data"]
rows.append(f"  GET filter[project.Project.id]={PROJECT} -> {len(by_proj)}")
bad = c.get("/entity/pages", params={"filter[project]": "null", "fields": "id", "page[size]": 1})
rows.append(f"  GET filter[project]=null -> {bad.status_code} {json.dumps(bad.json()['errors'][0])}")
for label, sel in (("project set", [p for p in pages if rel(p, "project")]), ("project null", site)):
    ct = collections.Counter(p["attributes"]["page_type"] for p in sel)
    rows.append(f"  {label:<13} page_type: {json.dumps(dict(ct.most_common(6)))} (+{len(ct) - 6} more spellings)")

rows.append("\n=== counts: paged listing versus _summarize")
projects = c.get("/entity/projects", params={"fields": "id", "page[size]": 300}).json()["data"]
per = sum(count("pages", [["project", "is", {"type": "Project", "id": p["id"]}]]) for p in projects)
rows.append(f"  _summarize record_count, no filter: {count('pages', [])}")
rows.append(f"  same, summed over {len(projects)} projects plus project-null: "
            f"{per} + {count('pages', [['project', 'is', None]])} = {per + count('pages', [['project', 'is', None]])}")
rows.append(f"  paged listing: {len(pages)}")

rows.append("\n=== PageSetting: who owns a row")
ids = [p["id"] for p in pages]
setting_rows = search("page_settings", [["page", "in", [{"type": "Page", "id": i} for i in ids]]],
                      ["page", "user", "settings_json"])
shapes = collections.Counter(
    (type(x["attributes"]["settings_json"]).__name__, rel(x, "user") is not None) for x in setting_rows)
rows.append(f"  PageSetting rows on this site (_summarize): {count('page_settings', [])}, "
            f"of which page is null: {count('page_settings', [['page', 'is', None]])}")
rows.append(f"  rows reachable from the {len(ids)} listed pages: {len(setting_rows)}")
rows.append(f"  (settings_json python type, user set) -> {json.dumps({str(k): v for k, v in shapes.items()})}")
covered = {rel(x, "page")["id"] for x in setting_rows if rel(x, "page")}
rows.append(f"  pages with at least one PageSetting: {len(covered)} of {len(ids)}; "
            f"site-level among them: {len({p['id'] for p in site} & covered)} of {len(site)}")
sj_type = c.get("/schema/PageSetting/fields/settings_json").json()["data"]["data_type"]["value"]
rows.append(f"  /schema/PageSetting/fields/settings_json data_type: {sj_type!r}, "
            f"returned decoded, never as a string")

rows.append("\n=== the widget tree of a page's shared PageSetting (user is null)")
by_id = {p["id"]: p for p in pages}


def shared_of(page_id):
    for x in setting_rows:
        p = rel(x, "page")
        if p and p["id"] == page_id and rel(x, "user") is None:
            return x["attributes"]["settings_json"]


def walk(node, path=""):
    if isinstance(node, dict) and "type" in node:
        yield path or "/", node["type"], sorted((node.get("settings") or {}).keys())
        for k, v in (node.get("children") or {}).items():
            yield from walk(v, f"{path}/{k}")


demo = next(p for p in pages if rel(p, "project") and rel(p, "project")["id"] == PROJECT
            and p["attributes"]["page_type"] == "canvas" and p["attributes"]["entity_type"] == "Shot")
tree = shared_of(demo["id"])
rows.append(f"  page {demo['id']} page_type={demo['attributes']['page_type']!r} "
            f"entity_type={demo['attributes']['entity_type']!r} name={demo['attributes']['name']!r}")
for path, t, keys in list(walk(tree))[:6]:
    rows.append(f"    {path:<22} {t:<40} settings={keys}")
rows.append(f"    ... {len(list(walk(tree)))} widgets in the tree")

body = tree["children"]["body"]["settings"]
grid = tree["children"]["body"]["children"]["list_content"]["settings"]
rows.append("\n  children.body.settings (the query):")
for k in ("entity_type", "mode", "sorts", "grouping"):
    rows.append(f"    {k:<12} {json.dumps(body.get(k))}")
rows.append(f"    filters      {json.dumps(body['filters'])[:400]}")
rows.append("\n  children.body.children.list_content.settings (the grid):")
rows.append(f"    keys         {sorted(grid)}")
rows.append(f"    columns      {json.dumps(grid['columns'])}")

rows.append("\n=== are the columns schema field names a client can feed to ?fields")
listy = []
for p in pages:
    if rel(p, "project") is None or rel(p, "project")["id"] != PROJECT:
        continue
    sj = shared_of(p["id"])
    if not isinstance(sj, dict):
        continue
    b = (sj.get("children") or {}).get("body") or {}
    lc = (b.get("children") or {}).get("list_content") or {}
    cols = (lc.get("settings") or {}).get("columns")
    if cols:
        listy.append((p, cols))
schemas, unknown = {}, []
for p, cols in listy:
    et = p["attributes"]["entity_type"]
    if et not in schemas:
        r = c.get(f"/schema/{et}/fields")
        schemas[et] = set(r.json()["data"]) if r.ok else set()
    miss = [x for x in cols if x.split(".")[0] not in schemas[et]]
    if miss:
        unknown.append((et, miss))
rows.append(f"  pages carrying a grid column list: {len(listy)} of {len(pages)} listed, "
            f"{len([p for p in pages if rel(p, 'project') and rel(p, 'project')['id'] == PROJECT])} in this project")
rows.append(f"  pages whose columns include a name absent from that type's /schema fields: {len(unknown)}")
for et, miss in unknown[:6]:
    rows.append(f"    {et:<16} {miss}")
r = c.get("/entity/shots", params={"fields": ",".join(grid["columns"]), "page[size]": 1,
                                   "filter[project.Project.id]": PROJECT})
got = r.json()["data"][0]
rows.append(f"  GET /entity/shots?fields=<that page's columns verbatim> -> {r.status_code}")
rows.append(f"    attributes {sorted(got['attributes'])}")
rows.append(f"    relationships {sorted(got['relationships'])}")

rows.append("\n=== a per-user PageSetting is a patch, not a tree")
for x in setting_rows:
    sj = x["attributes"]["settings_json"]
    if isinstance(sj, list):
        _lib.note_from(x)
        rows.append(f"  PageSetting {x['id']} user={rel(x, 'user') is not None} "
                    f"{json.dumps([{k: (v if k == 'spec_path' else sorted(v)) for k, v in e.items()} for e in sj])[:300]}")

rows.append("\n=== filter and sort")
p, pe = len(search("pages", [["name", "contains", "e"]], ["id"])), None
rows.append(f'  ["name","contains","e"] -> {p if isinstance(p, int) else p}')
rows.append(f'  negative control ["name","contains","ZZZNOPE"] -> '
            f'{len(search("pages", [["name", "contains", "ZZZNOPE"]], ["id"]))}')
rows.append(f'  ["settings_json","contains","SG.Widget.NewGrid"] on page_settings -> '
            f'{len(search("page_settings", [["settings_json", "contains", "SG.Widget.NewGrid"]], ["id"]))}')
for s in ("name", "-name", "zzz_not_a_field"):
    r = c.get("/entity/pages", params={"sort": s, "fields": "name", "page[size]": 3,
                                       "filter[project.Project.id]": PROJECT})
    rows.append(f"  sort={s!r} -> {r.status_code} "
                f"{[x['attributes']['name'] for x in r.json()['data']] if r.ok else r.text}")


def bogus(slug, entity, field):
    r = c.post(f"/entity/{slug}/_search", headers=ARR,
               json={"filters": [[field, "definitely_not_an_operator", None]],
                     "fields": ["id"], "page": {"size": 1}})
    if r.ok:
        return f"NOT REJECTED {r.status_code}"
    e = r.json()["errors"][0]
    return f"{r.status_code} {json.dumps({'title': e.get('title'), 'source': e.get('source')})}"


rows.append("\n=== the bogus-operator trick, one field per data type on both types")
for slug, entity, field in (("pages", "Page", "name"), ("pages", "Page", "project"),
                            ("pages", "Page", "entity_type"), ("pages", "Page", "system_owned"),
                            ("pages", "Page", "id"), ("page_settings", "PageSetting", "settings_json"),
                            ("page_settings", "PageSetting", "user")):
    rows.append(f"  {entity}.{field} -> {bogus(slug, entity, field)}")

_lib.emit("023_pages", "\n".join(rows), env)
