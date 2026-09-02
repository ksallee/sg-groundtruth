"""Q: on a real project, what do Versions actually link to, and how often?"""
from collections import Counter

import _lib

env = _lib.load_env()
c = _lib.client()
PROJECT, N = 70, 500

link_fields = ["entity", "sg_task", "user", "playlists", "project", "created_by"]
r = c.get("/entity/versions", params={
    "filter[project.Project.id]": PROJECT, "fields": ",".join(link_fields),
    "sort": "-id", "page[size]": N})
_lib.note_from(r.json())
rows = r.json()["data"]

present = Counter()
entity_types = Counter()
for row in rows:
    rel = row.get("relationships", {})
    for f in link_fields:
        d = rel.get(f, {}).get("data")
        if d:
            present[f] += 1
            if f == "entity":
                entity_types[d.get("type") if isinstance(d, dict) else "multi"] += 1

n = len(rows)
out = [f"sample: {n} most recent Versions on project {PROJECT}", "", "link field presence:"]
out += [f"  {f:<12} {present[f]:>4}/{n}  {100*present[f]//n if n else 0}%" for f in link_fields]
out += ["", "entity target types:"]
out += [f"  {t:<12} {ct:>4}  {100*ct//n if n else 0}%" for t, ct in entity_types.most_common()]

actual = "\n".join(out)
_lib.emit("005_link_usage", actual, env)
