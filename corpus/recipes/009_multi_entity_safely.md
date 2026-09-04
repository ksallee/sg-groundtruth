---
intent: Add to and remove from a multi_entity field without destroying the links you did not mean to touch
tags: [write, multi-entity, entity-field, playlist, note, version, filter, silent, destructive]
endpoints: [GET /entity/<type>/<id>, PUT /entity/<type>/<id>, POST /entity/<type>/_search]
scope: api
measured: all sample projects read, sandbox project written
---

# 009_multi_entity_safely

## Call

```python
import json
import sys

sys.path.insert(0, "src")                       # or PYTHONPATH=src
from sg_groundtruth.client import FPT           # adds the bearer token and the /api/v1 prefix
from sg_groundtruth.env import load

c = FPT.from_env(load("."))                     # FPT_API_SITE_URL, FPT_API_SCRIPT_NAME, FPT_API_API_KEY
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}   # array filters need it (probe 004)

PARENT = ("playlists", 32)                      # the parent whose member list is changing
FIELD = "versions"                              # its multi_entity field
A = {"type": "Version", "id": 31679}            # a child two playlists link
B = {"type": "Version", "id": 31680}            # a child only this playlist will link
DERIVED = ("notes", 10931)                      # the link a child holds because a parent claimed it
DERIVED_FIELD = "note_links"


def fail(r):
    raise SystemExit(json.dumps(r.json()["errors"], indent=2))   # never truncate an error body


def members(slug, record_id, field):
    """The current set. `data` is a list on every multi_entity field, empty when unset and never
    null; only a single `entity` field is returned as a mapping."""
    r = c.get(f"/entity/{slug}/{record_id}", params={"fields": field})
    if not r.ok:
        fail(r)
    return [x["id"] for x in r.json()["data"]["relationships"][field]["data"]]


def edit(slug, record_id, field, mode, value):
    """add, remove or set, in place. The mode goes in the body: both query-string spellings answer
    200 having replaced the whole list instead (`field_types/multi_entity`)."""
    r = c.put(f"/entity/{slug}/{record_id}",
              json={field: {"multi_entity_update_mode": mode, "value": value}})
    if not r.ok:
        fail(r)


def other_parents(parent_slug, field, child, exclude_id):
    """Which other rows still link this child. `is` takes one entity hash: a bare id is
    400 `API read() invalid/missing entity hash: <id>`, and `in` means "links any of", which
    matches rows linking nothing when a member is unresolvable."""
    r = c.post(f"/entity/{parent_slug}/_search", headers=ARR, json={
        "filters": [[field, "is", child], ["id", "is_not", exclude_id]],
        "fields": "id", "page": {"size": 500}})
    if not r.ok:
        fail(r)
    return [row["id"] for row in r.json()["data"]]


# 1. Append. The wrapper adds in place and dedupes.
edit(*PARENT, FIELD, "add", [B])
print("1. after add [B]        ", members(*PARENT, FIELD))

#    Never read the list and PUT it back instead:
#
#        seen = members(*PARENT, FIELD)
#        c.put(f"/entity/{PARENT[0]}/{PARENT[1]}", json={FIELD: seen + [B]})
#
#    A bare list replaces the whole set, so every member a concurrent writer added between the read
#    and the write is gone at 200, and there is no conditional write to catch it: If-Match,
#    If-Unmodified-Since and If-None-Match are ignored and echoing `updated_at` back is refused
#    (probe 024). The wrapper has no window at all.

# 2. Remove. The parent drops the member first, then the child is asked about, so a member that
#    left one parent while still belonging to another keeps what that other parent grants it.
#    `exclude_id` makes the answer right even if the removal has not propagated to the index yet.
for child in (A, B):
    edit(*PARENT, FIELD, "remove", [child])
    still = other_parents(PARENT[0], FIELD, child, PARENT[1])
    print(f"2. removed {child['id']}; other parents claiming it: {still}",
          "-> keep" if still else "-> strip")
    if not still:
        edit(*DERIVED, DERIVED_FIELD, "remove", [child])

# 3. Verify by re-reading. A write is confirmed by the row, never by its status code (probe 028),
#    and the query-string form of the mode is a 200 that replaced.
print("3. parent                ", members(*PARENT, FIELD))
print("3. derived               ", members(*DERIVED, DERIVED_FIELD))

# 4. Clear. `[]` and the `set` wrapper both clear; `null` is 400. Send a bare list only on a field
#    you know: `PUT {"replies": []}` on a Note deletes the Reply rows (`entity_types/Note`).
edit(*PARENT, FIELD, "set", [])
print("4. cleared               ", members(*PARENT, FIELD))
r = c.put(f"/entity/{PARENT[0]}/{PARENT[1]}", json={FIELD: None})
print("4. null                  ", r.status_code, r.json()["errors"][0]["title"])
```

## Response

Playlist 32 starts as `[A]`, playlist 33 also links `A`, and Note 10931 links both `A` and `B`.

```
1. after add [B]         [31679, 31680]
2. removed 31679; other parents claiming it: [33] -> keep
2. removed 31680; other parents claiming it: []   -> strip
3. parent                 []
3. derived                [31679]
4. cleared                []
4. null                   400 API update() Playlist.versions expected [Array, Hash] data type(s)
                              but got NilClass: nil
```

The append and the two removals both read back what was asked for. Probe 037 runs the append three
ways on its own playlist with a writer racing in the window, resetting the field to `[a, b]` before
each:

| the append | what the concurrent `add [c]` left behind |
|---|---|
| the reader `PUT`s its own list plus `[d]`, bare | `[a, b, d]`, `c` gone at 200 |
| the reader sends `add [d]` in the body | `[a, b, c, d]` |
| the reader sends `?multi_entity_update_mode=add` and a bare `[d]` | `[d]`, the whole list replaced at 200 |

Removal, on the same playlist and on the child's own field:

| written | result |
|---|---|
| `Playlist.versions` `remove [a]`, from `[a, b]` | 200, `[b]` |
| `Playlist.versions` `remove [a]` again, now absent | 200, a no-op |
| `Note.note_links` `remove [b]`, from `[a, b]` | 200, `[a]` |
| `Note.note_links` bare `[c]`, from `[a]` | 200, `[c]`. `a` is unlinked |

Clearing, measured on both fields:

| sent | `Playlist.versions` | `Note.note_links` |
|---|---|---|
| `[]` | 200, cleared | 200, cleared |
| `{"multi_entity_update_mode": "set", "value": []}` | 200, cleared | 200, cleared |
| `null` | 400 `API update() Playlist.versions expected [Array, Hash] data type(s) but got NilClass: nil` | 400, the same with `Note.note_links` |

## Notes

- **The removal direction is the dangerous one.** An append that goes wrong loses one link; a removal
  that skips the other-parents check breaks a relationship something else still needs, and a child
  that left one parent is not a child nothing claims. Remove from the parent, then ask
  `[[<field>, "is", <child hash>], ["id", "is_not", <parent id>]]` on the parent type, and strip the
  child only on an empty answer. On the probed site the same query over an existing project answered
  `200, [332, 4473, ... 4491]` for one Shot, 20 Notes claiming it, 19 once the one it left is
  excluded.
- **Use `is` with one entity hash for that query.** A bare id is
  `400 API read() invalid/missing entity hash: 954`, `is` with a list is `400 'is' 'relation' expects
  a 1-element array`, and `in` means "links any of", which on some fields returns the rows that link
  nothing when a member is unresolvable (`field_types/multi_entity`). One `_search` answers for one
  child; batch it by asking `in [child, child, ...]` and grouping the returned parents yourself.
- **The query-string trap.** `?multi_entity_update_mode=add` and
  `?options[multi_entity_update_modes][<field>]=add` both answer 200 having replaced the whole list.
  The loss is a success response, so the mode is only ever correct in the body
  (`field_types/multi_entity`, probe 028).
- **The lost-update race.** Read-then-PUT is not an append. A bare list replaces, the window between
  the read and the write is open, and no conditional write closes it: `If-Match`,
  `If-Unmodified-Since` and `If-None-Match` are ignored at 200 and `updated_at` echoed back is
  `400 editable on create only` (probe 024). The wrapper is not a narrower window, it is no window.
- **Verify by re-reading.** `?fields` is ignored on every write (probe 024) and a 200 proves nothing
  about a `multi_entity` field, since the query-string form returns one after replacing (probe 028).
  Compare the set you wanted against a fresh `GET /entity/<slug>/<id>?fields=<field>`. A dotted path
  is not a shortcut: `?fields=versions.Version.code` answered 200 with `attributes` and
  `relationships` both empty (probe 016).
- **Order is not stored.** `Playlist.versions` reads back sorted by the target's `code`, whatever
  order was written, and the human order is `sg_sort_order` on the `PlaylistVersionConnection` join
  row, which a write through the field leaves null. `remove` then `add` the same member replaces the
  join row and the order with it, so reorder by writing `sg_sort_order`, never by rewriting the
  member list (`entity_types/Playlist`).
- **Know the field before sending a bare list.** `PUT {"replies": []}` on a Note deletes the Reply
  rows outright, and the ids answer 404 afterwards (`entity_types/Note`). A bare list is a replace on
  most fields and a delete on some, and nothing in the response distinguishes them.
- **A multi_entity field reads back as a list.** `relationships.<field>.data` was a list on every
  read taken here: 100 rows of `Note.note_links` and 100 of `Version.playlists` and `Version.tasks`
  from `_search`, 20 of those re-read singly by `GET`, and 72 sandbox reads split across 0, 1 and 2
  members over `GET`, `_search` under both filter Content-Types, and
  `GET .../relationships/<field>`. Unset is `[]`, never null and never an absent key. One
  implementation reported by the survey defends against the field coming back as a single mapping
  instead; that did not reproduce, so the defensive read below is recorded unverified, on the
  survey's word rather than on a measurement here. The one field that does return a mapping is a
  single `entity` field, `{"data": {"id", "name", "type"}}`, which is what a caller reading the
  wrong field name gets.

      d = row["relationships"][field]["data"] or []
      d = [d] if isinstance(d, dict) else d
