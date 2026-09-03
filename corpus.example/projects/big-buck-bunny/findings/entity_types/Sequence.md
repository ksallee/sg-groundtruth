---
tags: [entity-type, project, page, fill-rate, status, link, inspector]
scope: project
project: Big Buck Bunny
title: Sequence
verdict: On Big Buck Bunny, Sequence has 3 pages built for it and populates 11 of 36 rankable fields across 15 sampled rows.
---
# Sequence

What Big Buck Bunny does with `Sequence`, from its 15 most recent rows.

**Pages**

| id | page | page_type | columns |
|---|---|---|---|
| 5104 | Sequences | canvas | 5 |
| 5137 | unnamed | detail | 0 |
| 5153 | unnamed | stream_detail | 0 |

The layout is the `PageSetting` row whose `user` is null (probe 023). The columns are schema field names and go to `?fields` verbatim.

### Sequences

`Sequence`, page 5104, `page_type` `canvas`. 5 columns, in order.

```
code,sg_status_list,description,cuts,created_by.HumanUser.email
```

**Usable statuses**

| field | usable | hidden | usable values | default |
|---|---|---|---|---|
| `sg_status_list` | 3 | 0 | `wtg (Waiting to Start)`, `ip (In Progress)`, `fin (Final)` | ip |

Read with `project_id=70`: `valid_values` minus `hidden_values`. The API accepts a hidden code on a write, so subtract it yourself.

**Fill rates**

| field | data type | filled |
|---|---|---|
| `assets` | multi_entity | 15/15 |
| `cached_display_name` | text | 15/15 |
| `code` | text | 15/15 |
| `created_at` | date_time | 15/15 |
| `created_by` | entity | 15/15 |
| `description` | text | 15/15 |
| `project` | entity | 15/15 |
| `sg_status_list` | status_list | 15/15 |
| `shots` | multi_entity | 15/15 |
| `updated_at` | date_time | 15/15 |
| `updated_by` | entity | 15/15 |

25 of 36 rankable fields are never populated here. Checkbox, summary, calculated and pivot fields are excluded: `False` and `0` are not null, so they read as fully populated (probe 007).

**Links set**

| field | data type | set on | points at |
|---|---|---|---|
| `assets` | multi_entity | 15/15 | Asset 1403 |
| `shots` | multi_entity | 15/15 | Shot 300 |

16 of 18 link fields are empty on every sampled row. `project`, `created_by` and `updated_by` are excluded (probe 005).
