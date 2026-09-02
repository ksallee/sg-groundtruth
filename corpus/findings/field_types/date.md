---
tags: [field-type, date, filter, operator, write, trap]
scope: api
summary: A calendar date, with no time of day.
verdict: A date is the string "YYYY-MM-DD" and nothing else: any timestamp 400s on write and as a filter value. Every negating operator (is_not, not_in, not_in_last) also matches rows that are null.
---

# date

**Data type** `date`, probed on `Shot.sg_turnover_date` (stock, editable). Same shape on
`Shot.sg_client_turnover_date`, `sg_date_next_version_expected` and the seven other stock Shot dates.
The schema states nothing type-specific: `properties={"default_value": null, "summary_default": "none"}`.

**Read** A plain string in `attributes`, never `relationships`. Exactly `YYYY-MM-DD`, no time, no zone.
Unset reads as `null`. A `date_time` on the same row is the contrast:

```
{"type": "Shot",
 "attributes": {"sg_turnover_date": "2026-09-02",
                "created_at":       "2026-09-02T15:58:21Z",
                "updated_at":       "2026-09-02T16:01:53Z"},
 "relationships": {}, "id": <id>}
```

**Write** `PUT /entity/shots/<id>` with `{"sg_turnover_date": "2026-09-02"}`. A rejected write leaves the
stored value untouched.

| sent | result |
|---|---|
| `"2026-09-02"` | 200, stored as sent |
| `str(datetime.date(...))` | 200, already that string |
| `datetime.datetime.isoformat()`, `"...T13:45:06Z"`, `"...+02:00"` | 400 `Invalid date format: <value>. Correct format is: 2011-01-21` |
| `"09/07/2026"`, `"2026/09/09"`, `"2026-9-8"` | same 400 |
| `"1757000000"`, `"tomorrow"`, `"2026-02-30"` | same 400 |
| `1757000000` | 400 `API update() Shot.sg_turnover_date expected [String, NilClass] data type(s) but got Integer: 1757000000` |
| `True` | 400 `API update() Shot.sg_turnover_date expected [String, NilClass] data type(s) but got TrueClass: true` |

`2026-02-30` is rejected by the same message as `tomorrow`: the date is validated, not just parsed.

**Clear**

| sent | result |
|---|---|
| `null` | cleared, reads back `None` |
| `""` | cleared, reads back `None` |
| `false` | 400 `expected [String, NilClass] ... got FalseClass: false`, value stays `'2026-09-02'` |

`null` and `""` are interchangeable on filter too: with both rows cleared, `is null` and `is ''` each
returned 2, `is_not null` and `is_not ''` each 0.

**Filter** A bogus operator enumerates the whole vocabulary (probe 017); `date` and `date_time` return an
identical list, and no text operator is in it. `contains` and `starts_with` 400 with this same list:

```
400 "API read() Shot.sg_turnover_date's 'date' data type doesn't support 'definitely_not_an_operator' 'relation'"
source: {"Shot.sg_turnover_date": " data type doesn't support ... Valid relations:
  ["is", "is_not", "greater_than", "less_than", "in_last", "not_in_last", "in_next", "not_in_next",
   "in_calendar_week", "in_calendar_month", "in_calendar_day", "in_calendar_year", "between", "in", "not_in"]"}
```

Measured on two sandbox rows, one dated and one null, so a positive is 1 and a negative is 0. Each
`value` is an example of the accepted format; `measured` calls the dated row's own date `today`:

| operator | value | matches | measured |
|---|---|---|---|
| `is` | `"2026-09-02"`, `null` or `""` | exact date | `is` the value -> 1 |
| `is_not` | `"2026-09-02"`, `null` or `""` | any other date, and null rows | `is_not` the value -> the unset row |
| `greater_than` | `"2026-09-02"` | strictly after | gt yesterday -> 1 ; gt the value itself -> 0 |
| `less_than` | `"2026-09-02"` | strictly before | lt tomorrow -> 1 ; lt the value itself -> 0 |
| `between` | `["2026-09-01", "2026-09-03"]` | inside the range, inclusive both ends, order-insensitive | `[today, today]` -> 1 ; `[-1, +1]` -> 1 ; `[+1, +2]` -> 0 ; `[+1, -1]` -> 1 ; `[today, null]` -> 0 |
| `in` | `["2026-09-02"]` | any listed date; a bare scalar also works | `in [today]` -> 1 ; `in today` -> 1 |
| `not_in` | `["2026-09-02"]` | any unlisted date, and null rows; a bare scalar also works | matched the unset row |
| `in_last` | `[10, "DAY"]` | n units back, includes today; n positive, unit uppercase | 5 days ago: `[10, "DAY"]` -> 1, `[2, "DAY"]` -> 0 |
| `not_in_last` | `[10, "DAY"]` | outside that range, and null rows | matched the unset row |
| `in_next` | `[10, "DAY"]` | n units forward, includes today | today matches `[1, "DAY"]` ; 5 days ago: `[10, "DAY"]` -> 0 |
| `not_in_next` | `[10, "DAY"]` | outside that range, and null rows | matched the unset row |
| `in_calendar_day` | `0` | that calendar day, from a bare signed offset; `[0]` works too | today: `0` -> 1, `-1` -> 0, `+1` -> 0 ; 5 days ago: `-5` -> 1, `0` -> 0 |
| `in_calendar_week` | `0` | that calendar week | today: `0` -> 1, `-1` -> 0, `+1` -> 0 |
| `in_calendar_month` | `0` | that calendar month | today: `0` -> 1, `-1` -> 0 ; 5 days ago, previous month: `0` -> 0 |
| `in_calendar_year` | `0` | that calendar year | today: `0` -> 1, `-1` -> 0, `+1` -> 0 |

Rejected filter values:

| sent | result |
|---|---|
| `"2026-09-02T00:00:00Z"` | 400 `Invalid date format: 2026-09-02T00:00:00Z. Correct format is: 2011-01-21` |
| `"09/02/2026"` | same 400 |
| `1788328800` | 400 `expected [String, NilClass] data type(s) but got Integer: 1788328800` |
| `between` with two scalars, not a list | 400 `Invalid condition: ["sg_turnover_date", "between", "1901-01-01", "2999-01-01"]` |
| `in_last 1` or `in_last [1]` | 400 `API read() 'in_last' 'relation' expects a 2-element array: [1]` |
| `in_last [100, "day"]` | 400 `doesn't support the 'day' time unit: [100, "day"] Valid time units: ["HOUR", "DAY", "WEEK", "MONTH", "YEAR"]` |
| `in_last [-10, "DAY"]` | 400 `expects at a positive Integer time unit` |

**Traps**
- **Every negating operator also returns null rows.** `is_not "2026-09-02"`, `not_in [...]` and
  `not_in_last [1,"MONTH"]` each matched the row with no date. Use `is_not null` for "has a value"; it is
  the only filter that means that.
- A `date` never accepts a timestamp, on write or as a filter value; `date_time` accepts both
  `"2026-09-02"` and `"2026-09-02T00:00:00Z"`. That and the read shape are the only differences: the
  operator list and the relative-value shapes are identical between the two types.
- `between` with a `null` endpoint returns 0 rows and no error. Use `greater_than` / `less_than` for an
  open-ended range; they are strict, not inclusive.
- `HOUR` is a legal unit but the value has no time part, so anything under 24h collapses to today: a date
  5 days back missed `in_last [1,"HOUR"]` and matched `in_last [200,"HOUR"]`.
- `""` is not a distinct empty state: it is written, filtered and read back as `null`.
