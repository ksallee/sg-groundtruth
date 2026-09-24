"""Q: what is the largest `page[size]` the API accepts, and what does one page cost at 100, 500 and the cap?

A page runner that reads a whole saved page trades round trips against page weight. Sample project Tasks,
read only, three timed reads per size.
"""
import statistics
import time

import _lib
import _pages as P

env = _lib.load_env()
c = _lib.client()
PROJECT = _lib.sample_projects(c, env)[0]
FIELDS = "content,sg_status_list,entity,step,task_assignees,start_date,due_date"
rows = []

rows.append("=== GET /entity/tasks?page[size]=N")
cap = None
for n in (500, 501, 1000, 5000, 0, -1):
    r = c.get("/entity/tasks", params={"filter[project.Project.id]": PROJECT, "fields": "id", "page[size]": n})
    got = len(r.json()["data"]) if r.ok else None
    rows.append(f"  {n:>6} -> {r.status_code} " + (f"{got} rows" if r.ok else str(r.json()["errors"][0])))
    if r.ok and n > 0:
        cap = max(cap or 0, n) if got == n or n <= 500 else cap
r = c.post("/entity/tasks/_search", headers=P.ARR,
           json={"filters": [["project", "is", {"type": "Project", "id": PROJECT}]], "fields": ["id"],
                 "page": {"size": 501}})
rows.append(f"  POST _search page.size 501 -> {r.status_code} "
            + (f"{len(r.json()['data'])} rows" if r.ok else str(r.json()["errors"][0])))
r = c.get("/entity/tasks", params={"filter[project.Project.id]": PROJECT, "fields": "id"})
rows.append(f"  page[size] omitted -> {r.status_code} {len(r.json()['data'])} rows")

rows.append("\n=== at and above 5000, on the project's EventLogEntry rows, fields=id")
for n in (5000, 5001, 10000):
    t = time.perf_counter()
    r = c.get("/entity/event_log_entries", params={"filter[project.Project.id]": PROJECT, "fields": "id",
                                                   "page[size]": n, "sort": "id"})
    ms = (time.perf_counter() - t) * 1000
    rows.append(f"  {n:>6} -> {r.status_code} " + (f"{len(r.json()['data'])} rows, {len(r.content) // 1024} KB, {ms:.0f} ms"
                                                  if r.ok else str(r.json()["errors"][0])))

rows.append(f"\n=== ms per page, fields={FIELDS}, three reads each")
for n in (100, 500, 2000):
    ms = []
    for i in range(3):
        t = time.perf_counter()
        r = c.get("/entity/tasks", params={"filter[project.Project.id]": PROJECT, "fields": FIELDS,
                                           "page[size]": n, "page[number]": 1, "sort": "id"})
        ms.append((time.perf_counter() - t) * 1000)
        size = len(r.content)
    rows.append(f"  {n:>4} rows: median {statistics.median(ms):.0f} ms ({', '.join(f'{m:.0f}' for m in ms)}), "
                f"{size // 1024} KB, {statistics.median(ms) / n:.2f} ms a row")

rows.append("\n=== the whole project's Tasks at 100, 500 and one page holding them all")
for n in (100, 500, 2000):
    t = time.perf_counter()
    total, k = 0, 1
    while True:
        r = c.get("/entity/tasks", params={"filter[project.Project.id]": PROJECT, "fields": FIELDS,
                                           "page[size]": n, "page[number]": k, "sort": "id"})
        d = r.json()["data"]
        if not d:
            break
        total, k = total + len(d), k + 1
    rows.append(f"  page[size]={n}: {total} rows in {k} calls (the last empty), "
                f"{(time.perf_counter() - t) * 1000:.0f} ms")

_lib.emit("082_page_size_cap", "\n".join(rows), env)
