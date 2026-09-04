"""Q: how do you search when you know neither the entity type nor the field path?

`_search` needs both. Three endpoints do not: `/entity/_text_search` takes words and no type,
and the two `/hierarchy` calls walk the tree the web interface draws down the left of a project.
Nothing in the corpus covers any of them. Read-only.
"""
import json

import _lib

env = _lib.load_env()
c = _lib.client()
PROJECT = _lib.sample_projects(c, env)[0]
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
rows = []

SHOT = c.post("/entity/shots/_search", headers=ARR,
              json={"filters": [["project", "is", {"type": "Project", "id": PROJECT}]],
                    "fields": "code", "page": {"size": 1}}).json()["data"][0]["id"]


def call(label, method, path, **kw):
    r = c.request(method, path, **kw)
    rows.append(f"\n-- {label}")
    rows.append(f"   {method} {path}" + (f"  {json.dumps(kw.get('json'))[:160]}" if kw.get("json") else ""))
    rows.append(f"   -> {r.status_code} {len(r.content)} bytes")
    try:
        b = r.json()
    except ValueError:
        rows.append(f"   body (not JSON): {r.text[:160]!r}")
        return r, None
    _lib.note_from(b)
    rows.append("   " + json.dumps(b.get("errors", b))[:420])
    return r, b


rows.append("===== POST /entity/_text_search")
call("no type, just words", "POST", "/entity/_text_search", headers=ARR,
     json={"text": "bunny", "entity_types": {"Version": []}})
call("several types at once", "POST", "/entity/_text_search", headers=ARR,
     json={"text": "bunny", "entity_types": {"Version": [], "Shot": [], "Asset": []},
           "page": {"size": 3}})
call("scoped to a project", "POST", "/entity/_text_search", headers=ARR,
     json={"text": "bunny",
           "entity_types": {"Shot": [["project", "is", {"type": "Project", "id": PROJECT}]]},
           "page": {"size": 3}})
call("no entity_types key", "POST", "/entity/_text_search", headers=ARR, json={"text": "bunny"})
call("empty text", "POST", "/entity/_text_search", headers=ARR,
     json={"text": "", "entity_types": {"Version": []}})
call("without the vendor content type", "POST", "/entity/_text_search",
     json={"text": "bunny", "entity_types": {"Version": []}})

# The hierarchy pair is the inverse of every other POST here: the vendor types are refused and
# plain application/json is the only one accepted.
JSON = {"Content-Type": "application/json"}
rows.append("\n\n===== POST /hierarchy/_expand")
call("vendor content type, as _search needs", "POST", "/hierarchy/_expand", headers=ARR,
     json={"path": f"/Project/{PROJECT}", "seed_entity_field": "Version.entity"})
call("the project's own tree", "POST", "/hierarchy/_expand", headers=JSON,
     json={"path": f"/Project/{PROJECT}", "seed_entity_field": "Version.entity"})
call("no seed_entity_field", "POST", "/hierarchy/_expand", headers=JSON,
     json={"path": f"/Project/{PROJECT}"})
call("a path that is not there", "POST", "/hierarchy/_expand", headers=JSON,
     json={"path": "/Project/999999999", "seed_entity_field": "Version.entity"})

rows.append("\n\n===== POST /hierarchy/_search")
call("find one entity in the tree", "POST", "/hierarchy/_search", headers=JSON,
     json={"root_path": f"/Project/{PROJECT}", "seed_entity_field": "Version.entity",
           "search_criteria": {"entity_type": "Shot"}})
call("one key, but not the one it wants", "POST", "/hierarchy/_search", headers=JSON,
     json={"root_path": f"/Project/{PROJECT}", "search_criteria": {"Shot": 862}})
call("the key it wants", "POST", "/hierarchy/_search", headers=JSON,
     json={"root_path": f"/Project/{PROJECT}",
           "search_criteria": {"entity": {"type": "Shot", "id": SHOT}}})
call("by text instead", "POST", "/hierarchy/_search", headers=JSON,
     json={"root_path": f"/Project/{PROJECT}", "seed_entity_field": "Version.entity",
           "search_criteria": "bunny"})

_lib.emit("046_search_without_a_path", "\n".join(rows), env)
