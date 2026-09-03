---
tags: [entity-type, project, page, fill-rate, status, link, inspector]
scope: project
project: Big Buck Bunny
title: PublishedFile
verdict: On Big Buck Bunny, PublishedFile has 2 pages built for it and populates 0 of 31 rankable fields across 0 sampled rows.
---
# PublishedFile

What Big Buck Bunny does with `PublishedFile`. No row of this type belongs to the project.

**Pages**

| id | page | page_type | columns |
|---|---|---|---|
| 5098 | Published Files | canvas | 6 |
| 5125 | unnamed | stream_detail | 0 |

The layout is the `PageSetting` row whose `user` is null (probe 023). The columns are schema field names and go to `?fields` verbatim.

### Published Files

`PublishedFile`, page 5098, `page_type` `canvas`. 6 columns, in order.

```
code,image,sg_status_list,tank_type,entity,version_number
```

1 of these are absent from `/schema/PublishedFile/fields`: `tank_type`. `?fields` ignores a name a type does not have, so a stale column is silent rather than a 400.

**Usable statuses**

| field | usable | hidden | usable values | default |
|---|---|---|---|---|
| `sg_status_list` | 3 | 0 | `wtg (Waiting to Start)`, `ip (In Progress)`, `cmpt (Complete)` | wtg |

Read with `project_id=70`: `valid_values` minus `hidden_values`. The API accepts a hidden code on a write, so subtract it yourself.
