"""Q: can links.next be trusted to stop, or does the last page lie?"""
import _lib

env = _lib.load_env()
c = _lib.client()
BBB, SIZE = 70, 100

seen, pages, path = 0, 0, None
params = {"filter[project.Project.id]": BBB, "fields": "code", "page[size]": SIZE, "sort": "id"}
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

actual = "\n".join(rows) + f"\n\ntotal rows: {seen} over {pages} pages"
_lib.record("006_pagination", "GET /entity/versions then follow links.next",
            "links.next is absent on the final page.",
            actual,
            "CONFIRMED and worse than reported: links.next is emitted on EVERY page forever, including pages "
            "that return zero rows - following it until absent is an infinite loop. Paging itself is correct "
            "(size=30 page=3 returns 30 rows). No total count exists anywhere: meta is null and "
            "options[return_paging_info] is ignored. Stop on an empty data array; never on a missing next.",
            env, tags=("paging", "query", "enumeration"))
print(actual)
