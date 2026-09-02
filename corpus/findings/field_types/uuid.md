---
tags: [field-type, uuid, filter, operator, write, schema, trap]
scope: api
measured: site-wide; no uuid field is writable, so no row was written
summary: An identifier the server generates for the row and never lets a client write.
verdict: A uuid field is server-generated and rejects every write with "is read only", so it cannot hold your key; it filters on is/is_not/in/not_in only, and a malformed value 400s.
---

# uuid

**Data type** `uuid`, probed on `Icon.uuid` (98 rows, every one filled and distinct) and
`EventLogEntry.session_uuid` (filled on a minority of rows, and repeated across them). On the probed site
a sweep of `/schema/<Type>/fields` over all 114 types in `/schema` found four uuid fields and no others.
Every one reports `editable: false`, `mandatory: false`, `unique: false` and
`ui_value_displayable: false`; `properties` holds only a null `default_value` and
`summary_default: "none"`.

| field | on an entity a client can create | filled on the probed site |
|---|---|---|
| `Icon.uuid` | no; `Icon` has no editable field | 98 of 98, all distinct |
| `LocalStorage.uuid` | the entity is creatable, but it is site configuration, not project data | 1 of 1 |
| `WorkDayRule.uuid` | no; the entity itself is read only | 8 of 8, all distinct |
| `EventLogEntry.session_uuid` | no; the server writes these rows | 13 of 500 sampled, all 13 the same value |

**Read** A 36-character canonical lowercase hyphenated string under `attributes`, never under
`relationships`. It is in the default field set, so it is returned even with no `fields` param. Absent
means `null`. On the probed site every value is version 1 (`...-11df-...`, `...-11f0-...`).

```
GET /entity/icons/<id>?fields=uuid -> 200
{"type":"Icon","attributes":{"uuid":"11111111-2222-11df-8888-999999999999"},
 "relationships":{},"id":<id>,"links":{"self":"/api/v1/entity/icons/<id>"}}
```

**Write** There is nothing to write. Every value shape gets the same rejection at the same layer, before
the value is looked at.

| sent to `PUT /entity/event_log_entries/<id>` as `session_uuid` | status |
|---|---|
| `"3f2504e0-4f89-11d3-9a0c-0305e82c3301"` (canonical) | 400 code 103 `API update() EventLogEntry.session_uuid is read only.` |
| `"3f2504e04f8911d39a0c0305e82c3301"` (hyphens stripped) | 400, the same title |
| `"3F2504E0-4F89-11D3-9A0C-0305E82C3301"` (uppercase) | 400, the same title |
| `"not-a-uuid"` | 400, the same title |
| a uuid already held by another row | 400, the same title |
| `12345` | 400, the same title |
| the value the field already holds | 400, the same title |

`source` is `{}` and `detail` is `null` on all of them; `Icon.uuid` and `LocalStorage.uuid` answer
identically. `WorkDayRule` rejects one step earlier, on the entity, update and create alike:

```
PUT  /entity/work_day_rules/<id>  {"uuid": "3f2504e0-4f89-11d3-9a0c-0305e82c3301"} -> 400
POST /entity/work_day_rules       {"uuid": "3f2504e0-4f89-11d3-9a0c-0305e82c3301"} -> 400
 {"status": 400, "code": 103, "title": "Action not allowed", "source": null,
  "detail": "Cannot edit read only entity 'work_day_rules'"}
```

Whether the server rejects a duplicate is unanswerable from the API: no write reaches the column.
The schema declares `unique: false`, and `EventLogEntry.session_uuid` holds one value on 13 rows, so
duplicates exist by design.

**Clear**

| sent | result |
|---|---|
| `null` | 400 `... is read only.` |
| `""` | 400 `... is read only.` |
| key omitted from the PUT | unchanged; the field is never touched |

A value is generated once when the row is created and never reissued.

**Filter** `POST /entity/<slug>/_search`, Content-Type `application/vnd+shotgun.api3_array+json`
(probe 004). A bogus relation names the vocabulary; all four fields answer with the same list:

```
[["uuid", "definitely_not_an_operator", null]] -> 400 code 103
title:  "API read() Icon.uuid's 'uuid' data type doesn't support
         'definitely_not_an_operator' 'relation'"
source: {"Icon.uuid": " ... Valid relations: [\"is\", \"is_not\", \"in\", \"not_in\"]"}
```

Value shapes `is` takes, against 98 Icon rows holding 98 distinct uuids:

| value | returns |
|---|---|
| the value as read | 1 |
| uppercase, mixed case, hyphens stripped, or both | 1; normalised before matching |
| `"{11111111-2222-11df-8888-999999999999}"` (brace wrapped) | 1 |
| `"00000000-0000-0000-0000-000000000000"`, any unused uuid | 0 |
| `""` | 0 here; matches exactly the rows where the field is `null` |
| a prefix, a `urn:uuid:` form, a padded value, `"not-a-uuid"` | 400 code 104 `Please check your filters for possible invalid value, invalid input syntax for type uuid: "11111111". -- Read failed for entity type [Icon]` |
| `null` | 400 code 103 `API read() Icon.uuid expected [String] data type(s) but got NilClass: nil` |
| `12345` | 400 code 103 `... but got Integer: 12345` |

Each operator, over 98 rows where the field is filled and over 5 rows where it is `null`:

| operator | value | matches | filled rows returned | null rows returned |
|---|---|---|---|---|
| `is` | `"11111111-2222-11df-8888-999999999999"` | the one row holding it | 1 of 98 | 0 of 5 |
| `is` | `""` | the rows where the field is `null` | 0 of 98 | 5 of 5 |
| `is_not` | `"11111111-2222-11df-8888-999999999999"` | every other row, `null` rows included | 97 of 98 | 5 of 5 |
| `is_not` | `""` | every row holding a uuid | 98 of 98 | 0 of 5 |
| `in` | `["11111111-2222-11df-8888-999999999999", "22222222-3333-11DF-8888-999999999999"]` | the rows holding either, mixed case and hyphenation | 2 of 98 for two values | 0 of 5 |
| `in` | `"11111111-2222-11df-8888-999999999999"` (bare, not a list) | one row; a scalar where a list is expected | 1 of 98 | 0 of 5 |
| `in` | `[]` | 400 code 103 `API read() 'in' 'relation' expects at least a 1-element array: []` | | |
| `in` | `[""]` | 400 code 104, `invalid input syntax for type uuid: ""` | | |
| `in` | `[null]` | 400 code 103, `expected [String] data type(s) but got NilClass: nil` | | |
| `not_in` | `["11111111-2222-11df-8888-999999999999", "22222222-3333-11DF-8888-999999999999"]` | every other row, `null` rows included | 96 of 98 for two values | 5 of 5 |
| `contains` | any | 400, the `Valid relations` list again | | |
| `not_contains` | any | 400, the same body | | |
| `starts_with` | any | 400, the same body | | |
| `ends_with` | any | 400, the same body | | |
| `greater_than` | any | 400, the same body | | |

`_summarize` (probe 020) takes the field: `grouping` `exact` gives one group per distinct value, and a
`count` summary gives the filled count.

**Traps**
- **`is null` is a 400, not a filter.** Use `is ""` for "unset" and `is_not ""` for "set". The empty
  string is legal only with `is` and `is_not`: `in [""]` fails as a malformed uuid.
- **A malformed filter value 400s the whole read.** Code 104 `invalid input syntax for type uuid`
  surfaces the database. A prefix, a `urn:uuid:` form, surrounding whitespace and any non-uuid string all
  fail. Validate client-side; there is no partial match to fall back on, since `contains` is unsupported.
- **`is_not` and `not_in` return the rows where the field is `null`**, so `is_not X` is not the
  complement of `is X`. Add `is_not ""` to exclude them.
- **Sorting on a uuid field fails**, on both spellings: `GET /entity/icons?sort=uuid` and `_search` with
  `"sort": "uuid"` return 400 code 104 `Read failed for entity type [Icon]`, with `source` and `detail`
  null. `sort=id` on the same endpoint returns 200. Page by `id` and sort client-side.
- **It cannot be your correlation key.** A uuid field is generated by the server, is not unique, and
  refuses every write. To tie a Flow PT row to a record in another system, put your identifier in a
  `text` field, which is writable and supports `is`, `in` and `contains`.
