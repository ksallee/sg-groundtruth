---
tags: [event-log, query, filter, operator, paging, write, create, serializable, status, trap]
scope: api
measured: first sample project read, sandbox project written
verdict: meta.old_value and meta.new_value answer "what was this before", but meta is unfilterable and unsortable: narrow on entity, event_type and attribute_name, sort -id, read meta yourself.
---

# 025_event_log

**Q** What can a client do with `EventLogEntry` over REST?

**Endpoint** `POST /entity/event_log_entries/_search ; POST /entity/event_log_entries ; DELETE /entity/event_log_entries/<id> ; GET /schema/EventLogEntry/fields`

**Docs claim** Silent on the log's contents. The REST docs address it as an ordinary entity type and
describe neither `meta` nor which operations a script user is permitted.

**Actual**

```
POST /entity/event_log_entries/_search
 {"filters":[["entity","is",{"type":"Shot","id":<id>}],["attribute_name","is","sg_status_list"],
   ["event_type","is","Shotgun_Shot_Change"]],"fields":["meta","created_at"],"sort":"-id"} -> 200
 {"attributes":{"meta":{"type":"attribute_change","attribute_name":"sg_status_list",
   "entity_type":"Shot","entity_id":<id>,"in_create":true,"field_data_type":"status_list",
   "old_value":"wtg","new_value":"ip","platform_id":null},"created_at":"2026-01-21T19:47:33Z"},
  "relationships":{"entity":{"data":{"id":<id>,"name":"sh010","type":"Shot"}}},"id":<id>}
 GET /entity/shots/<id>?fields=sg_status_list -> {"sg_status_list":"ip"}   new_value, still live

[["meta","is",null]] -> 400 code 103
 "API summarize() EventLogEntry.meta's 'serializable' data type cannot be used in a filter."
sort=meta, sort=audit_trail, sort=zzz_not_a_field -> 200, all three ordered by ascending id

POST /entity/event_log_entries {}  -> 400 code 103 "API create() missing 'project' attribute: {}"
POST /entity/event_log_entries {"project":{"type":"Project","id":<id>}} -> 201
 {"description":"New Event","created_at":"2026-09-02 18:39:48 UTC"}
 read back: event_type null, attribute_name null, meta null, user null, entity null
PUT {"meta":{...}} -> 400 code 104
 "The field is not editable for this user: [EventLogEntry.meta]. Rule: API Admin --
  PermissionRule 306: DENY update_field FOR entity_type => EventLogEntry, field_name => meta"
DELETE /entity/event_log_entries/<id> -> 400 code 104
 "Entity of type EventLogEntry can not be deleted by this user. Rule: API Admin --
  PermissionRule 297: DENY retire_entity FOR entity_type => EventLogEntry"

disjoint 1001-id windows, newest first:
  [head-1000, head]              714 of 1001 ids    71.3% dense
  [head-11000, head-10000]      1001 of 1001 ids   100.0% dense
  [head-101000, head-100000]    1001 of 1001 ids   100.0% dense
  [head-1001000, head-1000000]  1001 of 1001 ids   100.0% dense
```

**Teaches**

The type has 16 fields, all of them server-written. `id` and `created_at` are the only two that order it,
and `meta` is the only one that says what changed.

| field | data type | read | filter |
|---|---|---|---|
| `event_type` | `text` | yes | all 8 text relations |
| `attribute_name` | `text` | yes | all 8 text relations |
| `description` | `text` | yes, a rendered English sentence | all 8 text relations |
| `meta` | `serializable` | yes, decoded | **none**: 400 `cannot be used in a filter` |
| `audit_trail` | `jsonb` | **never returned**, even when named in `fields` | accepted and ignored (`field_types/jsonb`) |
| `entity`, `project`, `user`, `image_source_entity` | `entity` | under `relationships` | `is`, `type_is`, `in`, dotted paths |
| `created_at` | `date_time` | yes | all 15 date_time relations |
| `id` | `number` | yes | `is`, `greater_than`, `less_than`, `between`, `in` |
| `session_uuid` | `uuid` | yes | `is`, `is_not`, `in`, `not_in` |
| `cached_display_name`, `image`, `filmstrip_image`, `image_blur_hash` | `text`, `image` | yes | `is`, `is_not` |

The four production uses, measured:

| use | works | how |
|---|---|---|
| **history**: read a previous value | **yes** | `meta.old_value` and `meta.new_value`, narrowed on `entity` + `event_type` + `attribute_name`, `sort: "-id"` |
| **ledger**: write an entry | **create yes, and it is permanent** | `project` is the only requirement; `event_type` and `meta` are unwritable and `DELETE` is refused |
| **change feed**: consume in id order | **no, not from the head** | ids at the head are 71.3% dense and settle to 100%, so a max-id cursor skips events |
| **lock** | **no** | the read half works; the write half cannot be released, so each acquisition leaks a permanent row |

- **`meta` holds the answer and refuses every query.** `old_value` and `new_value` exist only where
  `meta.type` is `attribute_change`; `new_entity`, `entity_retirement` and `entity_revival` hold
  `entity_id` and `entity_type` and no values at all, and a preference change has no `meta.type` and the
  keys `old`, `new`, `pref`. Since `serializable` is unfilterable and unsortable (`field_types/serializable`),
  select rows by `entity`, `event_type` and `attribute_name`, order by `-id`, and inspect `meta` client-side.
  To restore a previous status: take the newest matching entry, check `meta.new_value` equals the value
  the entity holds now, then write `meta.old_value`. A mismatch means something changed since, and the
  entry is stale.
- **A created entry cannot be deleted, so never write one to a real site.** `POST` with `project` alone
  answers 201, invents `description: "New Event"`, and leaves `event_type`, `attribute_name`, `meta`,
  `user` and `entity` null. Every one of those is then refused on `PUT` by a per-field permission rule,
  and `DELETE` is refused by `PermissionRule 297`. This probe spent its one create on the minimal body and
  stopped, so **whether `event_type` or `meta` can be set in the create body is unmeasured**: testing it
  costs another permanent row. One row from this probe survives in the sandbox project of the probed site.
  A ledger built here is append-only with no way to correct or retract an entry. Both refusals name a
  role and a rule number, `API Admin -- PermissionRule 297`, so a script user in a different role may be
  permitted more; check the error before concluding the API forbids it everywhere.
- **Ids are reserved ahead of use and committed late.** On the probed site the newest 500 rows spanned 738
  ids with 9 gaps, the largest 33 wide, while every 1001-id window at depth 10000 or more was 100% dense.
  Gaps close, so they are held blocks and not deletions. A cursor that stores `max(id)` and asks for
  `id greater_than <that>` loses whatever later lands in the gaps it passed. Track a low-water mark instead:
  re-scan a window behind the head, or drive the feed from `created_at` and deduplicate on `id`.
- **`entity` goes null when its target is deleted; `meta` remembers.** On the probed site 12889 of 17778
  `Shotgun_Shot_Change` rows have `entity` null, and each names a `meta.entity_id` whose Shot now 404s.
  Filtering on `entity` returns only live targets, so the history of a deleted entity is reachable by
  `event_type` and `created_at` alone.
- **Narrowing works on everything but `meta`.** On the probed site the unfiltered log holds 2462044 rows,
  one project 22811, one Shot 2. `event_type` takes `starts_with` and `in`, `created_at` takes `in_last`
  and `between`, and `entity` takes a `{type, id}` hash, `type_is`, and a dotted path such as
  `entity.Shot.code`. `attribute_name` alone is site-wide across every entity type, so pair it with
  `event_type` or `entity`. A sort on `meta`, on `audit_trail` or on a name the type does not have is
  accepted and ignored, falling back to ascending `id`, so a client cannot tell an ignored sort from a
  satisfied one.

**Python equivalent**

```python
# probe 025: what a Shot's status was before the current one
prev = sg.find_one(
    "EventLogEntry",
    [["entity", "is", {"type": "Shot", "id": shot_id}],
     ["event_type", "is", "Shotgun_Shot_Change"],
     ["attribute_name", "is", "sg_status_list"]],
    ["meta"], order=[{"field_name": "id", "direction": "desc"}])
now = sg.find_one("Shot", [["id", "is", shot_id]], ["sg_status_list"])["sg_status_list"]
old = prev["meta"]["old_value"] if prev and prev["meta"]["new_value"] == now else None
```
