"""Q: can links.next be trusted to stop, or does the last page lie, and is a row total available?"""
import json

import _lib

env = _lib.load_env()
c = _lib.client()
PROJECT, SIZE = _lib.sample_projects(c, env)[0], 100
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
PROJ = ["project", "is", {"type": "Project", "id": PROJECT}]

seen, pages, path = 0, 0, None
params = {"filter[project.Project.id]": PROJECT, "fields": "code", "page[size]": SIZE, "sort": "id"}
rows = []
r = c.get("/entity/versions", params=params)

while True:
    d = r.json()
    n = len(d["data"])
    nxt = d.get("links", {}).get("next")
    pages += 1
    seen += n
    rows.append(f"page {pages:>2}: {n:>3} rows, next={'yes' if nxt else 'NO'}")
    if not nxt or pages > 30:
        break
    r = c.get(nxt)
    if not r.ok:
        rows.append(f"page {pages+1}: HTTP {r.status_code}")
        break

rows.append(f"\ntotal rows: {seen} over {pages} pages")

# Is a total available anywhere? One GET and one ignored option decided nothing, so try every
# spelling that could carry a count, and the two POST reads.
rows.append("\n=== asking for a total")
base = {"filter[project.Project.id]": PROJECT, "fields": "code", "page[size]": 1}
for label, extra in [
    ("page[size]=0", {"page[size]": 0}),
    ("options[return_paging_info]=true", {"options[return_paging_info]": "true"}),
    ("options[include_paging_info]=true", {"options[include_paging_info]": "true"}),
    ("page[totals]=true", {"page[totals]": "true"}),
    ("include_count=true", {"include_count": "true"}),
    ("meta[total]=true", {"meta[total]": "true"}),
]:
    r = c.get("/entity/versions", params={**base, **extra})
    d = r.json()
    if not r.ok:
        rows.append(f"  GET {label:<34} -> {r.status_code} {json.dumps(d)}")
        continue
    rows.append(f"  GET {label:<34} -> {r.status_code} keys={sorted(d)} "
                f"rows={len(d.get('data', []))} meta={json.dumps(d.get('meta'))} "
                f"links={sorted(d.get('links') or {})}")

r = c.post("/entity/versions/_search", headers=ARR,
           json={"filters": [PROJ], "fields": "code", "page": {"size": 1},
                 "options": {"return_paging_info": True}})
d = r.json()
rows.append(f"  POST _search options.return_paging_info -> {r.status_code} keys={sorted(d)} "
            f"meta={json.dumps(d.get('meta'))} links={sorted(d.get('links') or {})}")

r = c.post("/entity/versions/_summarize", headers=ARR,
           json={"filters": [PROJ], "summary_fields": [{"field": "id", "type": "count"}]})
rows.append(f"  POST _summarize count of id            -> {r.status_code} {json.dumps(r.json()['data'])}")

actual = "\n".join(rows)
_lib.emit("006_pagination", actual, env)
