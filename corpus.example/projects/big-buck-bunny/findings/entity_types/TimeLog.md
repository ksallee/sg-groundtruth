---
tags: [entity-type, project, page, fill-rate, status, link, inspector]
scope: project
project: Big Buck Bunny
title: TimeLog
verdict: On Big Buck Bunny, TimeLog has 1 page built for it and populates 10 of 12 rankable fields across 100 sampled rows.
---
# TimeLog

What Big Buck Bunny does with `TimeLog`, from its 100 most recent rows.

**Pages**

| id | page | page_type | columns |
|---|---|---|---|
| 5114 | Time Logs | canvas | 9 |

The layout is the `PageSetting` row whose `user` is null (probe 023). The columns are schema field names and go to `?fields` verbatim.

### Time Logs

`TimeLog`, page 5114, `page_type` `canvas`. 9 columns, in order.

```
id,user,entity,entity.Task.entity,description,date,duration,updated_at,updated_by
```

**Fill rates**

| field | data type | filled |
|---|---|---|
| `cached_display_name` | text | 100/100 |
| `created_at` | date_time | 100/100 |
| `created_by` | entity | 100/100 |
| `date` | date | 100/100 |
| `description` | text | 100/100 |
| `duration` | duration | 100/100 |
| `entity` | entity | 100/100 |
| `project` | entity | 100/100 |
| `updated_at` | date_time | 100/100 |
| `updated_by` | entity | 100/100 |

2 of 12 rankable fields are never populated here. Checkbox, summary, calculated and pivot fields are excluded: `False` and `0` are not null, so they read as fully populated (probe 007).

**Links set**

| field | data type | set on | points at |
|---|---|---|---|
| `entity` | entity | 100/100 | Task 100 |

1 of 2 link fields are empty on every sampled row. `project`, `created_by` and `updated_by` are excluded (probe 005).
