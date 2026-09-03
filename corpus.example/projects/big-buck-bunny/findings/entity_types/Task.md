---
tags: [entity-type, project, page, fill-rate, status, link, inspector]
scope: project
project: Big Buck Bunny
title: Task
verdict: On Big Buck Bunny, Task has 3 pages built for it and populates 20 of 43 rankable fields across 100 sampled rows.
---
# Task

What Big Buck Bunny does with `Task`, from its 100 most recent rows.

**Pages**

| id | page | page_type | columns |
|---|---|---|---|
| 5094 | Tasks | canvas | 0 |
| 5123 | unnamed | stream_detail | 0 |
| 5144 | unnamed | detail | 0 |

The layout is the `PageSetting` row whose `user` is null (probe 023). The columns are schema field names and go to `?fields` verbatim.

**Usable statuses**

| field | usable | hidden | usable values | default |
|---|---|---|---|---|
| `sg_status_list` | 10 | 0 | `wtg (Waiting to Start)`, `ip (In Progress)`, `fin (Final)`, `apr (Approved)`, `dis (Disabled)`, `na (N/A)`, `hld (On Hold)`, `rev (Pending Review)`, `omt (Omit)`, `ready (Ready)` | wtg |

Read with `project_id=70`: `valid_values` minus `hidden_values`. The API accepts a hidden code on a write, so subtract it yourself.

**Fill rates**

| field | data type | filled |
|---|---|---|
| `cached_display_name` | text | 100/100 |
| `color` | color | 100/100 |
| `content` | text | 100/100 |
| `created_at` | date_time | 100/100 |
| `created_by` | entity | 100/100 |
| `due_date` | date | 100/100 |
| `duration` | duration | 100/100 |
| `entity` | entity | 100/100 |
| `image` | image | 100/100 |
| `image_source_entity` | entity | 100/100 |
| `project` | entity | 100/100 |
| `sg_status_list` | status_list | 100/100 |
| `sibling_tasks` | multi_entity | 100/100 |
| `start_date` | date | 100/100 |
| `step` | entity | 100/100 |
| `time_logs_sum` | duration | 100/100 |
| `updated_at` | date_time | 100/100 |
| `workload_assignee_count` | number | 100/100 |
| `updated_by` | entity | 46/100 |
| `task_assignees` | multi_entity | 44/100 |

23 of 43 rankable fields are never populated here. Checkbox, summary, calculated and pivot fields are excluded: `False` and `0` are not null, so they read as fully populated (probe 007).

**Links set**

| field | data type | set on | points at |
|---|---|---|---|
| `entity` | entity | 100/100 | Shot 100 |
| `image_source_entity` | entity | 100/100 | Shot 100 |
| `sibling_tasks` | multi_entity | 100/100 | Task 500 |
| `step` | entity | 100/100 | Step 100 |
| `task_assignees` | multi_entity | 44/100 | HumanUser 44 |

10 of 15 link fields are empty on every sampled row. `project`, `created_by` and `updated_by` are excluded (probe 005).
