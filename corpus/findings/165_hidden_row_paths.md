---
tags: [permission, sudo, dotted-field, event-log, summary, group]
endpoints: [GET /entity/<type>/<id>, GET /entity/<type>/<id>/relationships/<related_field>, POST /entity/<type>/_search, POST /entity/<type>/_summarize, POST /entity/_text_search, GET /entity/<type>/<id>/activity_stream]
phase: read
scope: api
measured: sandbox project written, 2026-11-20; 2 Shots, 2 Bid Lines; two people re-roled to Vendor via sudo, restored
coverage: partial
unmeasured: the same paths under a see rule on Bid: no REST call adds a rule (probe 162) and the web interface was out of bounds. Blocked on the site
verdict: A see rule hides a row from fetch, search, summarize, text search and links, but a dotted filter still matches through it, a grouped `_summarize` shows its id and total, the event log its values.
---

# 165_hidden_row_paths

**Q** Once a conditional see rule hides a row from a person, can they reach it another way: by id, by
filter, by dotted path, by `_summarize`, by text search, through a link on a row they see, or in the
event log?

**Endpoint** `GET /entity/shots/<id> ; POST /entity/<type>/_search ; POST /entity/<type>/_summarize ; POST /entity/_text_search ; POST /entity/event_log_entries/_search`

**Docs claim** Silent on how a conditional rule applies across calls.

**Actual**

```
Measured on Shot, which the Vendor group sees only through sg_vendor_groups (probe 162). Shot A is
awarded to group A, shot B to group B; shot B's description was changed to "... price 250 B". A Bid
Line, visible to every vendor, links each Shot through an entity field <link>.

asking for shot B                                   vendor A                          vendor B, control
GET /entity/shots/<B>                               404 code 104 "Shot: <id> not found"   200
GET …/<B>/relationships/sg_vendor_groups            404 code 103, the same detail     200
_search [id, is, <B>]                               []                                [shot B]
_summarize Shots, count grouped by code             {"id": 1}, group shot A only      group shot B only
_text_search "zzprobe_165" on Shot and Bid Line     shot A; line A, line B            shot B; both lines
line B, read: <link>                                null                              {id, name, type}
line B, read: <link>.Shot.code, .description        null, null                        both values
_search Bid Lines [<link>.Shot.code, is, <B's code>]          [line B]                [line B]
_search Bid Lines [<link>.Shot.description, contains, "price 250"]  [line B]          [line B]
_search Bid Lines [<link>, is, <shot B>]            []                                [line B]
_summarize Bid Lines, sum grouped by <link>         group_name "", group_value         named, 250.0
                                                    {"type": "Shot", "id": <B>, "name": ""}, 250.0
group B, read: shot_sg_vendor_groups_shots          []                                [shot B]
event_log_entries [entity, is, <B>]                 0 rows                            9 rows
event_log_entries by id since setup, Shot events    9 about shot B by meta.entity_id, entity null,
                                                    meta new_value of code, description, sg_vendor_groups
  Shotgun_Shot_Change description  old_value "... first B"  new_value "... price 250 B"
GET /entity/shots/<B>/activity_stream               500 code 100 "Shotgun Server Error"   200
```

**What hides the row and what does not**

| path | hidden row |
|---|---|
| fetch by id, a relationship route | 404, the message of an id that does not exist (`endpoints/get_entity_type_id`) |
| `_search`, `GET` list, `_summarize` of the type, `_text_search` | omitted, counts included |
| an entity or multi_entity link on a row the person sees | `null`, or left out of the list |
| a dotted read through that link | `null` |
| a filter on a dotted path through the link | evaluated against the hidden row: a yes or no on any of its fields |
| `_summarize` of the linking type, grouped on the link | a group for the hidden row: its id, its name as `""`, the visible rows' total |
| the event log, filtered on `entity` | omitted |
| the event log, read by id or type | shown: `entity` null, `meta.entity_id` and every old and new value present |
| `activity_stream` | 500, as for an id that does not exist |

**Teaches**
- Fetches, lists, counts, text search and links treat a hidden row as absent. Three paths do not:
  a dotted filter through a visible row's link, a `_summarize` grouped on that link, and the event log.
- For bids: a see rule on Bid hides the Bid rows, and a visible Bid Line linking one still answers a
  filter on the Bid's fields and groups its total. Give Bid Line the same rule, through its link to the Bid.
- The event log is not filtered by a see rule on the row it describes. On the probed site Vendor reads
  `EventLogEntry`, so an amount written to a hidden Bid reaches every vendor as a `new_value`. An app
  holding prices from rivals keeps them off rows a vendor's event log can read, or the site denies
  Vendor `EventLogEntry`.
- `<link> is <hidden row>` matches nothing while `<link>.Shot.code is <its code>` matches: the
  comparison against the row is filtered and the dotted one is not.
