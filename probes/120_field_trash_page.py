"""Q: where is the web page that lists retired fields, the one a person empties to free a name?

The create refusal for a retired name says "Delete the retired field forever from the Trash Page".
No REST call does that (probe 114), so a client can only send the person there. Read-only: the
`Page` rows whose `ui_category` is `trash`, and the one whose `entity_type` is `DisplayColumn`,
the type a field's own row has in the event log.
"""
import collections
import json

import _lib

env = _lib.load_env()
c = _lib.client()
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
FIELDS = ["name", "page_type", "entity_type", "project", "ui_category", "system_owned", "shared",
          "created_by"]
out = []


def search(filters):
    r = c.post("/entity/pages/_search", headers=ARR,
               json={"filters": filters, "fields": FIELDS, "page": {"size": 200}})
    return r.status_code, r.json().get("data") or []


st, rows = search([["ui_category", "is", "trash"]])
out.append(f"POST /entity/pages/_search  [[\"ui_category\", \"is\", \"trash\"]] -> {st}, {len(rows)} pages")
out.append(f"  page_type {dict(collections.Counter(p['attributes']['page_type'] for p in rows))}; "
           f"with a project: {sum(1 for p in rows if p['relationships']['project']['data'])}; "
           f"system_owned {dict(collections.Counter(p['attributes']['system_owned'] for p in rows))}; "
           f"created by {dict(collections.Counter((p['relationships']['created_by']['data'] or {}).get('type') for p in rows))}")
for p in sorted(rows, key=lambda p: p["id"])[:6]:
    a = p["attributes"]
    out.append(f"  id <n>  name {a['name']!r}  entity_type {a['entity_type']}  system_owned {a['system_owned']}")
st, rows = search([["ui_category", "is", "trash"], ["entity_type", "is", "DisplayColumn"]])
out.append(f"the same with [\"entity_type\", \"is\", \"DisplayColumn\"] -> {st}, {len(rows)} page(s): "
           f"{[(p['attributes']['name'], p['attributes']['page_type']) for p in rows]}")
st, rows = search([["entity_type", "is", "DisplayColumn"]])
out.append(f"every page on DisplayColumn -> {len(rows)}: "
           f"{[(p['attributes']['name'], p['attributes']['page_type'], p['attributes']['ui_category']) for p in rows]}")
for path in ("/schema/DisplayColumn", "/entity/display_columns"):
    r = c.get(path)
    out.append(f"GET {path} -> {r.status_code}  {json.dumps(r.json().get('errors'))[:200]}")
ui = c.get("/schema/Page/fields/ui_category").json()["data"]
out.append(f"Page.ui_category: data_type {ui['data_type']['value']}, properties {sorted(ui['properties'])}")
_lib.emit("120_field_trash_page", "\n".join(out), env)
