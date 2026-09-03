---
tags: [entity-type, project, page, fill-rate, status, link, inspector]
scope: project
project: Big Buck Bunny
title: Shot
verdict: On Big Buck Bunny, Shot has 3 pages built for it and populates 23 of 85 rankable fields across 100 sampled rows.
---
# Shot

What Big Buck Bunny does with `Shot`, from its 100 most recent rows.

**Pages**

| id | page | page_type | columns |
|---|---|---|---|
| 5099 | Shots | canvas | 6 |
| 5128 | unnamed | stream_detail | 0 |
| 5152 | unnamed | detail | 0 |

The layout is the `PageSetting` row whose `user` is null (probe 023). The columns are schema field names and go to `?fields` verbatim.

### Shots

`Shot`, page 5099, `page_type` `canvas`. 6 columns, in order.

```
image,sg_status_list,code,sg_sequence,description,created_by
```

**Usable statuses**

| field | usable | hidden | usable values | default |
|---|---|---|---|---|
| `sg_latest_vendor_status` | 6 | 0 | `wtg (Waiting to Start)`, `ip (In Progress)`, `fin (Final)`, `omt (Omit)`, `hld (On Hold)`, `bid (Bidding)` | wtg |
| `sg_status_list` | 10 | 0 | `wtg (Waiting to Start)`, `ip (In Progress)`, `fin (Final)`, `rev (Pending Review)`, `apr (Approved)`, `hld (On Hold)`, `omt (Omit)`, `awd (Awarded)`, `bid (Bidding)`, `to (Turned Over)` | wtg |

Read with `project_id=70`: `valid_values` minus `hidden_values`. The API accepts a hidden code on a write, so subtract it yourself.

**Fill rates**

| field | data type | filled |
|---|---|---|
| `assets` | multi_entity | 100/100 |
| `cached_display_name` | text | 100/100 |
| `code` | text | 100/100 |
| `created_at` | date_time | 100/100 |
| `created_by` | entity | 100/100 |
| `description` | text | 100/100 |
| `image` | image | 100/100 |
| `image_source_entity` | entity | 100/100 |
| `notes` | multi_entity | 100/100 |
| `open_notes` | multi_entity | 100/100 |
| `project` | entity | 100/100 |
| `sg_cut_duration` | number | 100/100 |
| `sg_cut_in` | number | 100/100 |
| `sg_cut_order` | number | 100/100 |
| `sg_cut_out` | number | 100/100 |
| `sg_head_in` | number | 100/100 |
| `sg_sequence` | entity | 100/100 |
| `sg_status_list` | status_list | 100/100 |
| `sg_tail_out` | number | 100/100 |
| `sg_working_duration` | number | 100/100 |
| `tasks` | multi_entity | 100/100 |
| `updated_at` | date_time | 100/100 |
| `updated_by` | entity | 15/100 |

62 of 85 rankable fields are never populated here. Checkbox, summary, calculated and pivot fields are excluded: `False` and `0` are not null, so they read as fully populated (probe 007).

**Links set**

| field | data type | set on | points at |
|---|---|---|---|
| `assets` | multi_entity | 100/100 | Asset 1409 |
| `image_source_entity` | entity | 100/100 | Shot 100 |
| `notes` | multi_entity | 100/100 | Note 1997 |
| `open_notes` | multi_entity | 100/100 | Note 1336 |
| `sg_sequence` | entity | 100/100 | Sequence 100 |
| `tasks` | multi_entity | 100/100 | Task 500 |

15 of 21 link fields are empty on every sampled row. `project`, `created_by` and `updated_by` are excluded (probe 005).
