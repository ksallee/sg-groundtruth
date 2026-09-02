---
tags: [field-type, date-time, filter, operator, write, trap]
scope: api
verdict: Stored and read as UTC `YYYY-MM-DDTHH:MM:SSZ`: a written offset is silently normalised, a zoneless string is taken as UTC, and a date-only filter value means midnight UTC, not the whole day.
---

# date_time

**Data type** `date_time`, probed on `Version.client_approved_at` (stock, editable).

Across `Version, Project, Shot, Task, Note`, 3 of 14 `date_time` fields are `editable: true`:
`Version.client_approved_at`, `Version.media_center_import_time`,
`Project.last_accessed_by_current_user`. `created_at`/`updated_at` and the rest are server-managed. The
name does not predict it (`client_approved_at` is writable, `viewed_by_current_user_at` is not); read the
schema's `editable` flag.

**Read** Plain string in `attributes`, never `relationships`, identical from `GET /entity/versions` and
`POST /entity/versions/_search`:

```
  created_at='2026-01-23T20:43:39Z'   updated_at='2026-03-16T07:54:00Z'
```

Always `YYYY-MM-DDTHH:MM:SSZ`: second resolution, literal trailing `Z`, no numeric offset and no
site-local zone. A Version created at client UTC `2026-09-02T15:58:53.5Z` read back
`created_at='2026-09-02T15:58:53Z'`: 0.5s truncated, the same instant.

**Write** `PUT /entity/versions/<id>` with a JSON string.

| sent | result |
|---|---|
| `"2026-03-04T05:06:07Z"` | 200, read back `2026-03-04T05:06:07Z` |
| `"2026-03-04T05:06:07+05:00"` | 200, read back `2026-03-04T00:06:07Z` |
| `"2026-03-04T05:06:07-08:00"` | 200, read back `2026-03-04T13:06:07Z` |
| `"2026-03-04T05:06:07"` | 200, read back `2026-03-04T05:06:07Z`; zoneless is UTC |
| `"2026-03-04T05:06:07.123Z"` | 200, read back `2026-03-04T05:06:07Z`; sub-second dropped |
| `"2026-03-04"` | 200, read back `2026-03-04T00:00:00Z` |
| `"2026-03-04 05:06:07"` | 400 `Invalid date time format: 2026-03-04 05:06:07. Correct format is 2011-01-21T13:26:09Z (UTC), 2011-01-21T13:26:09-07:00 (UTC Offset) or any ISO8601 compatible string.` |
| `"1772600767"` (epoch string) | 400, same `Invalid date time format` message |
| `"not-a-time"` | 400, same `Invalid date time format` message |
| `1772600767` (epoch int) | 400 `API update() Version.client_approved_at expected [String, NilClass] data type(s) but got Integer: 1772600767` |
| `{"created_at": "2020-01-01T00:00:00Z"}` | 400, code 103, `API update() Version.created_at is editable on create only.` |

**Clear**

| sent | result |
|---|---|
| `null` | cleared, reads back `None` |
| `""` | 400 `Invalid date time format: . Correct format is 2011-01-21T13:26:09Z (UTC), 2011-01-21T13:26:09-07:00 (UTC Offset) or any ISO8601 compatible string.` |

A cleared field is matched by `["field", "is", null]` (1) and excluded by `is_not` `null` (0).

**Filter** The bogus-operator 400 (probe 017) on `Version.created_at`:

```
  "title": "API read() Version.created_at's 'date_time' data type doesn't support
            'definitely_not_an_operator' 'relation'",
  "source": {"Version.created_at": " ... Valid relations: [\"is\", \"is_not\", \"greater_than\",
      \"less_than\", \"in_last\", \"not_in_last\", \"in_next\", \"not_in_next\", \"in_calendar_week\",
      \"in_calendar_month\", \"in_calendar_day\", \"in_calendar_year\", \"between\", \"in\", \"not_in\"]"}
```

`Shot.sg_turnover_date`, a `date` field, returns an identical list; the two types share every relation and
differ only in value format. There is no `not_between` and no `is_null`.

Every count below is one sandbox Version holding `2026-03-04T05:06:07Z`, run on 2026-09-02: 1 is a match,
0 is a miss.

| operator | value | rows |
|---|---|---|
| `is` | `"2026-03-04T05:06:07Z"` | 1 |
| `is` | `"2099-01-01T00:00:00Z"` | 0 |
| `is` | `null` | 0 |
| `is_not` | `"2026-03-04T05:06:07Z"` | 0 |
| `greater_than` | `"2026-03-04T00:00:00Z"` | 1 |
| `greater_than` | `"2026-03-05T00:00:00Z"` | 0 |
| `less_than` | `"2026-03-05T00:00:00Z"` | 1 |
| `less_than` | `"2026-03-04T00:00:00Z"` | 0 |
| `between` | `["2026-03-04T00:00:00Z", "2026-03-05T00:00:00Z"]` | 1 |
| `between` | `["1970-01-01T00:00:00Z", "1971-01-01T00:00:00Z"]` | 0 |
| `in` | `["2026-03-04T05:06:07Z"]` | 1 |
| `in` | `["2099-01-01T00:00:00Z"]` | 0 |
| `not_in` | `["2026-03-04T05:06:07Z"]` | 0 |
| `in_last` | `[100, "YEAR"]` | 1 |
| `not_in_last` | `[100, "YEAR"]` | 0 |
| `in_next` | `[100, "YEAR"]` | 0 |
| `not_in_next` | `[100, "YEAR"]` | 1 |
| `in_calendar_year` | `0` | 1 |
| `in_calendar_year` | `-50` | 0 |
| `in_calendar_day`, `_week`, `_month` | `0` | 0 each: March 4 is a past day, week and month |
| `in_last` | `[1, "FORTNIGHT"]` | 400 `API read() 'in_last' 'relation' doesn't support the 'FORTNIGHT' time unit: [1, "FORTNIGHT"]  Valid time units: ["HOUR", "DAY", "WEEK", "MONTH", "YEAR"]` |

A filter value takes the same formats as a write value, date-only included, and a date-only value is
exactly midnight UTC rather than a day:

| stored | `is "2026-03-04"` | `greater_than "2026-03-04"` | `less_than "2026-03-04"` |
|---|---|---|---|
| `2026-03-03T23:30:00Z` | 0 | 0 | 1 |
| `2026-03-04T00:00:00Z` | 1 | 0 | 0 |
| `2026-03-04T00:30:00Z` | 0 | 1 | 0 |

Re-stored on the current UTC date, the same row matched `in_calendar_day` `0` at both `00:30Z` and
`23:30Z` and matched neither `-1` nor `+1`, with `_week`, `_month` and `_year` at `0` each 1: the calendar
buckets are UTC-aligned, with no site-local offset.

**Traps**
- A written offset is not preserved: `05:06:07+05:00` reads back as `00:06:07Z`. Convert to UTC yourself
  and keep the original zone in your own field if a client must redisplay local wall-clock time.
- A zoneless string is **assumed UTC**, not site-local: `"2026-03-04T05:06:07"` is not "5am here".
- `is` is exact-second equality, so `is "2026-03-04"` finds only rows at `00:00:00Z`. Match a day with
  `between ["2026-03-04", "2026-03-05"]` or `in_calendar_day`.
- `""` 400s where a `text` field accepts it; only `null` clears. There is no numeric form: epoch integers
  400 with the `[String, NilClass]` type error, epoch strings with the format error.
- `created_at`/`updated_at` 400 with "is editable on create only"; check the schema's `editable` flag
  before writing any timestamp.
