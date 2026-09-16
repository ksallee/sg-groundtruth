---
intent: Find the Notes about a Shot, Asset or Version by the name of the thing, and read what each Note is linked to
tags: [note, dotted-field, multi-entity]
endpoints: [POST /entity/<type>/_search, POST /entity/<type>/_summarize]
scope: api
measured: sample project 1 of 1, 5944 Notes, 500 with note_links
---

# 014_notes_about

A Note names what it is about in `note_links`, a `multi_entity` field over 28 types on the probed
site. A search by name goes through the link with a dotted path, one path per type, and the links come
back through the bare field (probe 071).

## Call

```python
import sys

sys.path.insert(0, "src")                       # or PYTHONPATH=src
from sg_groundtruth.client import FPT
from sg_groundtruth.env import load

c = FPT.from_env(load("."))
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}

PROJECT_ID = 1234
NAME = "sh010"
TYPES = ("Shot", "Asset", "Version")            # each is one search; the path names one type

scope = ["project", "is", {"type": "Project", "id": PROJECT_ID}]

# 1. How many, without paging: _summarize counts what _search would page.
r = c.post("/entity/notes/_summarize", headers=ARR, json={
    "filters": [scope, ["note_links.Shot.cached_display_name", "is", NAME]],
    "summary_fields": [{"field": "id", "type": "record_count"}]})
count = r.json()["data"]["summaries"]["id"]     # 20

# 2. The Notes, one search per type. Ask for `note_links`, never for the dotted path.
found = {}
for t in TYPES:
    r = c.post("/entity/notes/_search", headers=ARR, json={
        "filters": [scope, [f"note_links.{t}.cached_display_name", "is", NAME]],
        "fields": "subject,content,note_links,created_at",
        "sort": "-created_at", "page": {"size": 500}})
    for n in r.json()["data"]:
        found[n["id"]] = n                      # a Note linked to a Shot and its Version is in both

# 3. What each Note is about, from the field itself.
for n in found.values():
    about = [f"{d['type']} {d['name']}" for d in n["relationships"]["note_links"]["data"]]
    print(n["id"], n["attributes"]["subject"], "->", ", ".join(about))
```

## Response

```
_summarize -> 200 {"data": {"summaries": {"id": 20}, "groups": []}}
_search    -> 200, 20 rows; each row's relationships.note_links.data is
              [{"id": 4321, "name": "sh010", "type": "Shot"}]
```

## Notes

- `cached_display_name` resolves for every one of the 28 `valid_types`. `code` is 400 on `Booking`
  and `name` on every type but `Department`, with the same `doesn't exist.` string for a wrong type
  and a wrong field.
- `?fields=note_links.Shot.code` answers 200 with the key absent from `attributes` (probe 016). The
  links are readable only through `note_links` itself, as `{id, name, type}` triples.
- `["note_links", "contains", NAME]` without a type is 400 `'multi_entity' data type doesn't support
  'contains' 'relation'`. There is no search across all types in one filter by name; resolve ids first
  and use `["note_links", "in", [{"type": ..., "id": ...}, ...]]`.
- A Note about a Task is in `tasks`, not `note_links`. Search it on `tasks.Task.content`.
- Two hops resolve: `note_links.Shot.sg_sequence.Sequence.code` narrows to a sequence.
