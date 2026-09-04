---
endpoint: GET /schedule/work_day_rules
tags: [date, discovery, silent, read-only]
scope: api
measured: sample project 1 of 1, plus site-wide windows of 14 and 730 days
verdict: One row per calendar day, both ends inclusive, no paging at 730 rows. A `project_id` or `user_id` that does not exist answers 200 with the studio default instead of an error.
---

# GET /schedule/work_day_rules

Which calendar days count as work. `duration` and `due_date` on a Task are computed against this,
so a client that adds working days itself has to read it.

**Params**

| part | value |
|---|---|
| `start_date` | required. `YYYY-MM-DD` |
| `end_date` | required. `YYYY-MM-DD`, and must be greater than or equal to `start_date` |
| `user_id` | optional. Falls back to the studio rule when absent |
| `project_id` | optional. Falls back to the studio rule when absent |

**Sample requests**

A fortnight, studio-wide:

```python
r = c.get("/schedule/work_day_rules",
          params={"start_date": "2026-03-02", "end_date": "2026-03-15"})
```

14 rows for a 14-day window, first two shown:

```json
{
  "data": [
    {"date": "2026-03-02", "working": true, "description": null, "reason": "STUDIO_WORK_WEEK"},
    {"date": "2026-03-07", "working": false, "description": null, "reason": "STUDIO_WORK_WEEK"}
  ],
  "links": {"self": "/api/v1/schedule/work_day_rules?end_date=2026-03-15&start_date=2026-03-02"}
}
```

A project id that is not on the site, which is not an error:

```python
r = c.get("/schedule/work_day_rules",
          params={"start_date": "2026-03-02", "end_date": "2026-03-15",
                  "project_id": 999999999})
```

```json
{"data": [{"date": "2026-03-02", "working": true, "description": null,
           "reason": "STUDIO_WORK_WEEK"}]}
```

A date that will not parse:

```python
r = c.get("/schedule/work_day_rules",
          params={"start_date": "03/02/2026", "end_date": "03/15/2026"})
```

```json
{"status": "error", "error": "invalid date"}
```

A missing parameter:

```python
r = c.get("/schedule/work_day_rules", params={"start_date": "2026-03-02"})
```

```json
[{"id": "6e3ab12946d1c597355a5373e4ccca44", "status": 400, "code": 103,
  "title": "Request Parameters invalid.", "source": {"end_date": ["end_date is missing"]},
  "detail": null, "meta": null}]
```

| row key | shape |
|---|---|
| `date` | `YYYY-MM-DD`, one row per calendar day in the range |
| `working` | boolean |
| `description` | string or `null`. Set by the exception that made the day, if any |
| `reason` | one of `STUDIO_WORK_WEEK`, `STUDIO_EXCEPTION`, `PROJECT_WORK_WEEK`, `PROJECT_EXCEPTION`, `USER_WORK_WEEK`, `USER_EXCEPTION` |

**Response codes**

| status | when |
|---|---|
| 200 | including for a `project_id` or `user_id` that does not exist |
| 400 | `{"start_date": ["start_date is missing"], "end_date": ["end_date is missing"]}` |
| 400 | `start_date_and_end_date 'end_date' must be greater than or equal to 'start_date'` |
| 400 | `{"status": "error", "error": "invalid date"}` for a date that will not parse |
| 401 | `Request rejected due to invalid credentials.` |

**Edge cases**

- **Two error shapes on one endpoint.** A missing or out-of-order parameter is a JSON:API `errors`
  array; an unparseable date is a bare `{"status": "error", "error": "invalid date"}` with no `errors`
  key at all. A client reading `r.json()["errors"][0]["title"]` raises `KeyError` on the second.
- A `project_id` or `user_id` that is not on the site answers 200 with the studio rule. Nothing in the
  body says which scope answered, other than `reason`, and `reason` reads `STUDIO_WORK_WEEK` for both
  the fallback and a genuine studio-wide answer. Check the id exists before trusting the schedule.
- Both ends are inclusive. `start_date` equal to `end_date` returns one row.
- No paging. A 730-day window returned 730 rows in 61631 bytes, with no `page` envelope and no
  `links.next`. Bound the range yourself.
- `links.self` echoes the parameters back, so two responses that differ only in `project_id` differ in
  byte length while their `data` is identical.
- The dates must be `YYYY-MM-DD`. `03/02/2026` is refused, whatever `date_component_order` in
  `GET /preferences` says the site displays.

**Links**

- `endpoints/put_schedule_work_day_rules`
- `endpoints/get_preferences`
- `field_types/date`
- `findings/047_site_facts_and_the_working_week`