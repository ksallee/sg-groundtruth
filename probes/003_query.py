"""Q: how do filters, dotted fields and paging actually work on entity reads?"""
import json

import _lib

env = _lib.load_env()
c = _lib.client()
BBB = 70
rows = []


def try_(label, method, path, **kw):
    r = c.request(method, path, **kw)
    try:
        d = r.json()
    except Exception:
        d = r.text[:200]
    n = len(d.get("data", [])) if isinstance(d, dict) and isinstance(d.get("data"), list) else "-"
    detail = ""
    if not r.ok and isinstance(d, dict):
        detail = " | " + str(d.get("errors", [{}])[0].get("detail", ""))[:150]
    rows.append(f"{r.status_code} n={n:<4} {label}{detail}")
    return d if r.ok else None


# simple filter, flat query params
try_("simple filter[project.Project.id]", "GET", "/entity/versions",
     params={"filter[project.Project.id]": BBB, "fields": "code", "page[size]": 3})

# dotted / bubbled fields in the fields list
d = try_("dotted fields in ?fields", "GET", "/entity/versions",
         params={"filter[project.Project.id]": BBB,
                 "fields": "code,sg_status_list,sg_task.Task.content,entity",
                 "page[size]": 3})
sample = json.dumps(d["data"][0], indent=2)[:900] if d and d.get("data") else "(no rows)"

# complex search endpoint
try_("POST _search with filter array", "POST", "/entity/versions/_search",
     json={"filters": [["project.Project.id", "is", BBB]], "fields": ["code"], "page": {"size": 3}},
     headers={"Content-Type": "application/vnd+shotgun.api3_array+json"})

# sorting + paging
d2 = try_("sort desc + page[number]=2", "GET", "/entity/versions",
          params={"filter[project.Project.id]": BBB, "fields": "code", "sort": "-id",
                  "page[size]": 2, "page[number]": 2})

# does an unknown field error or silently drop?
try_("unknown field sg_not_a_field", "GET", "/entity/versions",
     params={"filter[project.Project.id]": BBB, "fields": "code,sg_not_a_field", "page[size]": 1})

actual = "\n".join(rows) + "\n\nsample row with dotted fields:\n" + sample

_lib.record(
    "003_query", "GET /entity/versions, POST /entity/versions/_search",
    "Filters via filter[field]; dotted notation entity.EntityType.field; page[size]/page[number].",
    actual, "see below", env, tags=("query", "filter", "dotted-field", "paging", "version"),
)
print(actual)
