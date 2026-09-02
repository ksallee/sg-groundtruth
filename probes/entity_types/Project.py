"""Entity type `Project`: how it is addressed, what names it, and what a client may read off it.

Read-only, always. Project is site-wide, so there is no sandbox to scope a write to and every row is
someone's real show. Probe 011 already recorded the create behind --write; this one never posts.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _lib  # noqa: E402

env = _lib.load_env()
c = _lib.client()
SAMPLE = _lib.sample_projects(c, env)
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
rows = []


def errobj(r):
    """The whole errors[] object. Never sliced: `source` names the vocabulary the API accepts."""
    try:
        return r.json().get("errors", [r.json()])
    except ValueError:
        return [r.text]


def errs(r):
    return json.dumps(errobj(r), indent=1)


# ---------------------------------------------------------------- slug
# Probe 002 found no endpoint that enumerates types, so the schema name to path rule has to be measured.
rows.append("=== slug: which path addresses the type, and what the router rejects")
for path in ("/entity/projects", "/entity/project", "/entity/Project", "/entity/Projects",
             "/entity/projectz", "/entity/versions"):
    r = c.get(path, params={"fields": "id", "page[size]": 2})
    if r.ok:
        d = r.json()["data"]
        rows.append(f"  {path:<22} -> 200  type={d[0]['type'] if d else '?'} "
                    f"ids={[x['id'] for x in d]}")
    else:
        rows.append(f"  {path:<22} -> {r.status_code}\n    " + errs(r).replace("\n", "\n    "))

rows.append("  the same spellings on other types, to tell a Project special case from a router rule:")
for path in ("/entity/version", "/entity/PublishedFile", "/entity/published_files",
             "/entity/publishedfiles", "/entity/human_users", "/entity/HumanUser"):
    r = c.get(path, params={"fields": "id", "page[size]": 1})
    rows.append(f"  {path:<22} -> {r.status_code}"
                + (f"  type={(r.json()['data'] or [{}])[0].get('type')}" if r.ok
                   else "  " + json.dumps(errobj(r)[0].get("detail"))))

# ---------------------------------------------------------------- scoped or site-wide
rows.append("\n=== scope: is Project itself project-scoped?")
fields = c.get("/schema/Project/fields").json()["data"]


def prop(f, name, default=None):
    p = fields[f].get("properties", {}).get(name)
    return (p or {}).get("value", default) if isinstance(p, dict) else default


def dt(f):
    return (fields[f].get("data_type") or {}).get("value")


def flag(f, key):
    return (fields[f].get(key) or {}).get("value")


rows.append(f"  'project' in Project's own fields: {'project' in fields}")
r = c.get("/entity/projects", params={"filter[project.Project.id]": SAMPLE[0], "fields": "id"})
rows.append(f"  GET /entity/projects?filter[project.Project.id]={SAMPLE[0]} -> {r.status_code}")
if not r.ok:
    rows.append("    " + errs(r).replace("\n", "\n    "))
r = c.get("/entity/projects", params={"filter[id]": SAMPLE[0], "fields": "name"})
rows.append(f"  GET /entity/projects?filter[id]=<id> -> {r.status_code}, {len(r.json().get('data', []))} row(s)")

# ---------------------------------------------------------------- identity
rows.append("\n=== identity: the text fields, and which are flagged mandatory or unique")
rows.append(f"  {'field':<30}{'type':<10}{'mandatory':<11}{'unique':<8}editable")
for f in sorted(fields):
    if dt(f) in ("text", "entity_type"):
        rows.append(f"  {f:<30}{dt(f):<10}{str(flag(f, 'mandatory')):<11}"
                    f"{str(flag(f, 'unique')):<8}{flag(f, 'editable')}")

rows.append("\n  what those hold on real rows:")
r = c.get("/entity/projects", params={"fields": "name,code,tank_name,cached_display_name,sg_type",
                                      "page[size]": 500})
data = r.json()["data"]
_lib.note_from(r.json())
for row in data[:4]:
    rows.append(f"  id={row['id']:<6} type={row['type']:<8} {json.dumps(row['attributes'])}")


def filled(key):
    return sum(1 for x in data if x["attributes"].get(key) not in (None, ""))


rows.append(f"\n  across {len(data)} projects: " + ", ".join(
    f"{k}={filled(k)}" for k in ("name", "code", "tank_name", "cached_display_name", "sg_type")))
rows.append(f"  code == name on {sum(1 for x in data if x['attributes'].get('code') == x['attributes']['name'])}"
            f" of {len(data)}")
rows.append(f"  distinct names {len({x['attributes']['name'] for x in data})}, "
            f"distinct ids {len({x['id'] for x in data})}")

# ---------------------------------------------------------------- links
rows.append("\n=== links: entity and multi_entity fields")
rows.append(f"  {'field':<32}{'type':<14}{'editable':<10}valid_types")
links = [f for f in sorted(fields) if dt(f) in ("entity", "multi_entity")]
for f in links:
    rows.append(f"  {f:<32}{dt(f):<14}{str(flag(f, 'editable')):<10}{prop(f, 'valid_types')}")

rows.append("\n  one row read with the link fields asked for:")
r = c.get(f"/entity/projects/{SAMPLE[0]}", params={"fields": "name," + ",".join(links)})
row = r.json()["data"]
_lib.note_from(r.json())
rows.append(f"  attributes    {sorted(row.get('attributes', {}))}")
rows.append(f"  relationships {sorted(row.get('relationships', {}))}")
for f in ("users", "layout_project", "task_templates"):
    d = (row.get("relationships", {}).get(f) or {}).get("data")
    shown = d if not isinstance(d, list) else d[:2]
    rows.append(f"    {f:<16}{json.dumps(shown)}"
                + (f"  (+{len(d) - 2} more)" if isinstance(d, list) and len(d) > 2 else ""))

rows.append("\n  the link a client actually uses is the other way round: Project as a filter target")
for label, params in [
    ("GET /entity/shots?filter[project.Project.id]=<id>",
     {"filter[project.Project.id]": SAMPLE[0], "fields": "code", "page[size]": 1}),
    ("GET /entity/shots?filter[project]=<id>  (bare id)",
     {"filter[project]": SAMPLE[0], "fields": "code", "page[size]": 1}),
    ("GET /entity/shots?fields=project.Project.name",
     {"filter[project.Project.id]": SAMPLE[0], "fields": "code,project.Project.name", "page[size]": 1}),
]:
    r = c.get("/entity/shots", params=params)
    if r.ok:
        d = r.json()["data"]
        _lib.note_from(r.json())
        rows.append(f"  {label:<52} -> 200 {json.dumps(d[0]['attributes']) if d else '0 rows'}")
    else:
        rows.append(f"  {label:<52} -> {r.status_code}\n    " + errs(r).replace("\n", "\n    "))

r = c.post("/entity/shots/_search", headers=ARR,
           json={"filters": [["project", "is", {"type": "Project", "id": SAMPLE[0]}]],
                 "fields": ["code"], "page": {"size": 1}})
rows.append(f"  POST _search [['project','is',{{type,id}}]]                  -> {r.status_code}, "
            f"{len(r.json()['data']) if r.ok else errs(r)} row(s)")

# ---------------------------------------------------------------- status
rows.append("\n=== status: list fields on Project")
for f in sorted(fields):
    if dt(f) in ("list", "status_list"):
        rows.append(f"  {f:<16}{dt(f):<14}valid={prop(f, 'valid_values')} "
                    f"display={prop(f, 'display_values')}")
r = c.get("/schema/Project/fields", params={"project_id": SAMPLE[0]})
pf = r.json()["data"]
rows.append(f"  scoped to one project, sg_status hidden_values="
            f"{(pf['sg_status'].get('properties', {}).get('hidden_values') or {}).get('value')}")

# ---------------------------------------------------------------- read only / server managed
rows.append("\n=== read only and server managed")
ro = [f for f in sorted(fields) if flag(f, "editable") is False]
rows.append(f"  not editable ({len(ro)} of {len(fields)}): {ro}")
r = c.get(f"/entity/projects/{SAMPLE[0]}",
          params={"fields": "name,created_at,updated_at,landing_page_url,tracking_settings,duration,"
                            "start_date,end_date,archived,is_template,is_demo"})
row = r.json()["data"]
_lib.note_from(r.json())
a = row["attributes"]
for k in sorted(a):
    v = json.dumps(a[k])
    rows.append(f"  {k:<20}{v[:150]}")

actual = "\n".join(rows)
_lib.emit("entity_types/Project", actual, env)
