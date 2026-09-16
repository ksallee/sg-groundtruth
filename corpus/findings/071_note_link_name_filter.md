---
tags: [note, dotted-field, multi-entity, link]
endpoints: [GET /schema/<Type>/fields, POST /entity/<type>/_search, POST /entity/<type>/_summarize]
phase: filter
scope: api
measured: sample project 1 of 1, 5944 Notes, 500 with note_links, every link to a Shot
verdict: Filter notes about a thing on `note_links.<Type>.cached_display_name`: it resolves for every valid type, `code` 400s on Booking and `name` on all but Department. The path cannot be read back.
---

# 071_note_link_name_filter

**Q** Which dotted path filters a Note by the name of the thing it is about?

**Endpoint** `GET /schema/Note/fields ; POST /entity/notes/_search ; POST /entity/notes/_summarize`

**Docs claim** The filter syntax page shows `<field>.<Type>.<field>` through a linked field and says
nothing about `multi_entity` fields or about which name field each type has.

**Actual**

```
Note.note_links valid_types: 28 on the probed site
  Asset, Booking, Cut, Department, Group, Playlist, Sequence, Shot, TaskTemplate, Version, ...

_summarize record_count, scoped to the sample project (5944 Notes), value "sh01"
  path                                        cached_display_name   code          name
  note_links.Shot.<f> contains                200, 5944             200, 5944     400
  note_links.Booking.<f> contains             200, 0                400           400
  note_links.Department.<f> contains          200, 0                200, 0        200, 0
  the other 25 types                          200, 0                200, 0        400
  resolved / 400 over the 28 types            28 / 0                27 / 1        1 / 27

the 400s, verbatim
  note_links.Booking.code        -> "API summarize() Note.note_links.Booking.code doesn't exist."
  note_links.Group.name          -> "API summarize() Note.note_links.Group.name doesn't exist."
  note_links.Shot.zz_not_a_field -> "API summarize() Note.note_links.Shot.zz_not_a_field doesn't exist."
  note_links.ZzNotAType.code     -> "API summarize() Note.note_links.ZzNotAType.code doesn't exist."
  note_links contains "sh01"     -> "API summarize() Note.note_links's 'multi_entity' data type
                                     doesn't support 'contains' 'relation'"

evaluated, not ignored
  note_links.Shot.code contains "ZZZNOPE"                     -> 0
  note_links.Shot.code is "sh010"                             -> 20
  note_links.Shot.cached_display_name is "sh010"              -> 20
  note_links.Shot.code is_not null                            -> 5944
  note_links.Shot.sg_sequence.Sequence.code is_not null       -> 5944   two hops
  tasks.Task.content contains "a"                             -> 0      the other link field

POST /entity/notes/_search ?fields=subject,note_links.Shot.code -> 200, attributes ['subject']
```

**Teaches**

**The type in the path picks the name field, and the types disagree.** `Shot`, `Asset`, `Sequence`
and `Version` are named by `code`, `Department` and `Group` by `name`, a `Booking` by neither.
`cached_display_name` is on every type and resolved for all 28, and on a Shot it matched the same
20 rows as `code`. Use it unless the query needs a field only that type has.

**A wrong type and a wrong field fail the same way.** `note_links.ZzNotAType.code` and
`note_links.Shot.zz_not_a_field` both answer 400 `doesn't exist.`, so the error does not say which
segment is wrong. Check the type against `valid_types` first.

**One filter per type.** A path names one type, and `note_links` spans 28. "Notes about anything
called sh010" is one `_search` per type the client cares about, or one `["note_links", "in",
[{"type": "Shot", "id": N}, ...]]` after resolving the ids. There is no bare text relation on the
field: `note_links contains` is 400.

**Read the links back through the field, not the path.** `?fields=note_links.Shot.code` returns 200
with the key absent (probe 016). Ask for `note_links` and take `relationships.note_links.data[].name`.

**Python equivalent**

```python
# probe 071: notes about a Shot, by name
notes = sg.find("Note", [["project", "is", {"type": "Project", "id": pid}],
                         ["note_links.Shot.code", "is", "sh010"]], ["subject", "note_links"])
```
