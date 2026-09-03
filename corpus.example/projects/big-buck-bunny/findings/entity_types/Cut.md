---
tags: [entity-type, project, page, fill-rate, status, link, inspector]
scope: project
project: Big Buck Bunny
title: Cut
verdict: On Big Buck Bunny, Cut has 1 page built for it and populates 0 of 29 rankable fields across 0 sampled rows.
---
# Cut

What Big Buck Bunny does with `Cut`. No row of this type belongs to the project.

**Pages**

| id | page | page_type | columns |
|---|---|---|---|
| 5127 | unnamed | stream_detail | 0 |

The layout is the `PageSetting` row whose `user` is null (probe 023). The columns are schema field names and go to `?fields` verbatim.

**Usable statuses**

| field | usable | hidden | usable values | default |
|---|---|---|---|---|
| `sg_status_list` | 4 | 0 | `ip (In Progress)`, `hld (On Hold)`, `apr (Approved)`, `na (N/A)` | ip |

Read with `project_id=70`: `valid_values` minus `hidden_values`. The API accepts a hidden code on a write, so subtract it yourself.
