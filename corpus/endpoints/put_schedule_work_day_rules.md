---
endpoint: PUT /schedule/work_day_rules
tags: [date, write, error-handling, project, user]
scope: api
measured: site-wide, rejections only
verdict: One day per call, keyed by `date` in the body rather than by a path id, and `user_id` or `project_id` absent means the change applies to the studio default for everyone.
---

# PUT /schedule/work_day_rules

Marks one calendar day working or not. The success path was not exercised; see **Edge cases**.

**Params**

| part | value |
|---|---|
| body `date` | required. `YYYY-MM-DD`. The day, and the only way the row is addressed |
| body `working` | required. Boolean |
| body `user_id` | optional. Scopes the rule to one user |
| body `project_id` | optional. Scopes the rule to one project |
| body `recalculate_field` | optional. `duration` or `due_date`, and nothing else |
| body `description` | optional. Free text stored on the day |
| `Content-Type` | `application/json` |

**Sample requests**

An empty body, which names both required keys:

```python
r = c.put("/schedule/work_day_rules", json={})
```

```json
[{"id": "dc0a1ec4ec741197bb4fcc053a77aa94", "status": 400, "code": 103,
  "title": "Request Parameters invalid.",
  "source": {"date": ["date is missing"], "working": ["working is missing"]},
  "detail": null, "meta": null}]
```

A date that will not parse, with a `recalculate_field` that is not one of the two:

```python
r = c.put("/schedule/work_day_rules",
          json={"date": "not-a-date", "working": True,
                "recalculate_field": "definitely_not_a_field"})
```

```json
[{"id": "1dbe3e84fe61c545d4533aba2f280ee6", "status": 400, "code": 103,
  "title": "Request Parameters invalid.",
  "source": {"date": ["date format is not valid. Valid format is 'YYYY-MM-DD'"],
             "recalculate_field": ["recalculate_field invalid value. The valid values are 'duration' or 'due_date'"]},
  "detail": null, "meta": null}]
```

**Response codes**

| status | when |
|---|---|
| 200 | body is `{"data": {date, working, description, project, user}, "links": {...}}` |
| 400 | `{"date": ["date is missing"], "working": ["working is missing"]}` |
| 400 | `{"date": ["date format is not valid. Valid format is 'YYYY-MM-DD'"]}` |
| 400 | `{"recalculate_field": ["recalculate_field invalid value. The valid values are 'duration' or 'due_date'"]}` |
| 401 | `Request rejected due to invalid credentials.` |

**Edge cases**

- **The success path is deliberately unexercised.** A call with neither `user_id` nor `project_id`
  rewrites the studio calendar for every user of the site, and there is no dry run and no undo. The
  400 rows above are what pins the parameter names; the 200 shape comes from the site's own
  `/spec.json`.
- Scope is decided by omission. No `user_id` and no `project_id` means studio-wide, which is the
  widest possible effect and also the shortest body. Send the scope explicitly.
- Every parameter is validated in one pass: a body wrong in two places lists both keys under `source`.
- `recalculate_field` is what moves existing Task rows. Omitting it changes the calendar and leaves
  `duration` and `due_date` where they were, so the two can be made to disagree.
- Only `date` addresses the row. There is no id, no `DELETE`, and no documented way to remove an
  exception other than writing the day back to what the work week says.
- The 200 response shape adds `project` and `user` references that the `GET` rows do not have.

**Links**

- `endpoints/get_schedule_work_day_rules`
- `field_types/date`
- `field_types/duration`
- `findings/047_site_facts_and_the_working_week`