---
tags: [query, filter, sort, write, operator, error-handling, trap]
scope: api
verdict: A 400 is trustworthy and usually names the legal set, but a 200 proves nothing: an unknown field, sort key or query param is a no-op, and a batch can return an id for a row it never made.
---

# 028_loud_and_silent

**Q** Which failures does this API announce, and which does it swallow?

**Endpoint** `POST /entity/<type>/_search ; POST /entity/<type>/_summarize ; GET /entity/<type> ; GET /schema/<Type> ; PUT /entity/<type>/{id}`

**Docs claim** Silent. The REST docs describe success shapes and list no error vocabulary.

**Actual**

```
loud
  ["code", "definitely_not_an_operator", "x"]  400  API read() Version.code's 'text' data type doesn't
      support 'definitely_not_an_operator' 'relation'   source: ... Valid relations: ["contains",
      "not_contains", "is", "is_not", "starts_with", "ends_with", "in", "not_in"]
  _summarize {"field": "id", "type": "definitely_not_a_summary_type"}  400  Request Parameters invalid.
      source {"summary_fields": {"0": {"type": ["type must be one of: record_count, count, sum, maximum,
      minimum, average, earliest, latest, percentage, status_percentage, status_percentage_as_float,
      status_list, checked, unchecked"]}}}
  GET /entity/zzz_not_an_entity_type  404  detail "Entity type 'zzz_not_an_entity_type' does not exist."
  GET /schema/DisplayColumn           404  detail "Entity type 'DisplayColumn' does not exist."
  ["sg_not_a_field_at_all", "is", "x"] 400  API read() Version.sg_not_a_field_at_all doesn't exist.
  ["frame_count", "is", 2.5]           400  API read() Version.frame_count expected [String, Integer,
      NilClass] data type(s) but got Float: 2.5
  sort=''  400 {"sort": ["sort must be filled"]} ;  sort='id desc', '+id'  400 {"sort": ["sort list is not valid"]}

silent
  ?fields=code,zzz_not_a_field   200  attributes ['code']
  sort=code 200 sorted ; open_notes_count (summary), sg_uploaded_movie (url) and
      sg_not_a_field_at_all  200 each, ascending and descending, identical to no sort at all
  ["id", "in", [25529, 17055, 25553, 25493, 25541, 25481, 25517, 25505]]
      200  [17055, 25481, 25493, 25505, 25517, 25529, 25541, 25553]   id ascending
  sg_version_type, valid_values ['Type A', 'Type B', 'Type C'], over 100 rows:
      is 'Type A' 99 ; is 'zzz_not_a_valid_value' 0 ; in ['Type A'] 99 ;
      in ['Type A', 'zzz_not_a_valid_value'] 99 ; in ['zzz_not_a_valid_value'] 0
  PageSetting record_count  no filter 30145 ; settings_json contains 'ZZZNOPE' 30145 ; is null 30145 ;
      is_not null 30145 ; control [["page", "is", null]] 26372
  EventLogEntry record_count, one project 22811 ; + audit_trail is null, is_not null and
      contains {'x': 1}  22811 each ; control + event_type is 'ZZZNOPE'  0
```

**Teaches**

Every case below is measured elsewhere in the corpus; this entry is the map. The rows marked verified
were re-run read-only on the date of this probe and none had changed.

**Loud, and usually self-documenting.** The rejection names the legal set, which is what made the
field-type matrix cheap to build.

| sent | answer | recorded |
|---|---|---|
| an operator no data type has | 400 naming every legal relation for that data type. All 21 reachable types reject; 16 enumerate, the five unfilterable ones answer `cannot be used in a filter` (verified) | probe 017, `field_types/*` |
| a `_summarize` `type` that is not one of the fourteen | 400 `Request Parameters invalid.`, `source.summary_fields` indexed by position, naming all fourteen (verified) | probe 020 |
| an entity type name that does not exist, in a path or in `/schema` | 404 `Entity type '<x>' does not exist.`, quoting the name back (verified) | `entity_types/Project`, probe 023 |
| a field name that does not exist, in a filter | 400 `API read() <Type>.<field> doesn't exist.` (verified) | probe 026 |
| a `list` value outside `valid_values`, on a write | 400 naming the legal values | `field_types/list` |
| a wrong Python type, on a write or as a filter value | 400 naming the accepted Ruby classes (verified as a filter value) | `field_types/number`, `float`, `percent` |
| a malformed `POST /entity/_batch` body | 400 per missing key, and `request_type must be one of: create, update, delete` | probe 024 |
| sort syntax: empty, a space, a leading `+` | 400 `sort must be filled` or `sort list is not valid` (verified) | probe 026 |

**Silent.** HTTP 200, and the part of the request the server did not understand is gone.

| sent | answer | recorded |
|---|---|---|
| a name in `?fields` that is not a field, on a read | 200, the key absent from `attributes` (verified) | probe 004, probe 023 |
| `?fields` on a create or an update | ignored entirely, both verbs, plain names and dotted paths alike | probe 024 |
| a `list` filter value outside `valid_values` | 0 rows, no error; inside `in` the junk member is evaluated and matches nothing, so the rest of the list still returns (verified) | `field_types/list` |
| `sort` on an unsortable or unknown field | 200 in default order, identical to no sort, ascending and descending alike (verified) | probe 026, `field_types/summary`, `field_types/url` |
| `["id", "in", [...]]` | 200, id ascending; the order of the list is discarded (verified) | probe 026 |
| any filter on `PageSetting.settings_json` | 200 and the full unfiltered set, while another field on the same type filters (verified) | probe 023 |
| any filter on `EventLogEntry.audit_trail` | the same (verified) | `field_types/jsonb` |
| `filter[]` query params on `POST _search` | ignored entirely: a body filter wins and a bogus param name still returns 200, while the same param filters correctly on `GET /entity/<type>` | probe 030 |
| a batch create missing a required attribute | 200 with an id for a row that does not exist: `GET` 404s, `_search` returns 0, `DELETE` answers 204. The single-create path 400s on the same body | `recipes/002_batch` |

**Silent and destructive.** Six writes return success and either do nothing or destroy data. Not re-run
here: they are recorded, and re-proving them costs rows.

| written | answer | recorded |
|---|---|---|
| `cached_display_name` | 200, the write discarded; the field re-reads as `code` | `field_types/text`, `entity_types/Sequence` |
| `Task.splits`, any well-formed payload | 200, `null` stored | `field_types/serializable` |
| a `multi_entity` update mode spelled in the query string | 200, the whole list replaced instead of appended | `field_types/multi_entity` |
| an already-linked Shot added to a second `Sequence.shots` | 200, the first Sequence's `shots` is now `[]` | `entity_types/Sequence` |
| two `summary_fields` entries over one field | 200, the second overwrites the first, last entry wins | probe 020 |
| `PUT` a Note with `{"replies": []}` | 200, the Reply rows deleted outright | `entity_types/Note` |

**The rule.** Trust a 400: the request layer validates operator, summary type, entity name, field name
and value class, and says what it wanted. Trust nothing about the parts of a request that select or
shape data, because `?fields`, `sort`, a filter value and an update mode are all dropped at 200 when the
server does not recognise them, and a write is confirmed by re-reading the row, never by its status code.
