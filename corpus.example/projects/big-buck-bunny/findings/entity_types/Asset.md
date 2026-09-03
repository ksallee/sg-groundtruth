---
tags: [entity-type, project, page, fill-rate, status, link, inspector]
scope: project
project: Big Buck Bunny
title: Asset
verdict: On Big Buck Bunny, Asset has 4 pages built for it and populates 18 of 41 rankable fields across 100 sampled rows.
---
# Asset

What Big Buck Bunny does with `Asset`, from its 100 most recent rows.

**Pages**

| id | page | page_type | columns |
|---|---|---|---|
| 5106 | Assets | canvas | 6 |
| 5126 | unnamed | stream_detail | 0 |
| 5129 | unnamed | stream_detail | 0 |
| 5151 | unnamed | detail | 0 |

The layout is the `PageSetting` row whose `user` is null (probe 023). The columns are schema field names and go to `?fields` verbatim.

### Assets

`Asset`, page 5106, `page_type` `canvas`. 6 columns, in order.

```
image,sg_status_list,code,sg_asset_type,description,shots
```

**Usable statuses**

| field | usable | hidden | usable values | default |
|---|---|---|---|---|
| `sg_status_list` | 8 | 0 | `wtg (Waiting to Start)`, `ip (In Progress)`, `fin (Final)`, `dis (Disabled)`, `rev (Pending Review)`, `apr (Approved)`, `hld (On Hold)`, `omt (Omit)` | wtg |

Read with `project_id=70`: `valid_values` minus `hidden_values`. The API accepts a hidden code on a write, so subtract it yourself.

**Fill rates**

| field | data type | filled |
|---|---|---|
| `cached_display_name` | text | 100/100 |
| `code` | text | 100/100 |
| `created_at` | date_time | 100/100 |
| `created_by` | entity | 100/100 |
| `description` | text | 100/100 |
| `image` | image | 100/100 |
| `image_source_entity` | entity | 100/100 |
| `project` | entity | 100/100 |
| `sg_asset_type` | list | 100/100 |
| `sg_status_list` | status_list | 100/100 |
| `shots` | multi_entity | 100/100 |
| `tasks` | multi_entity | 100/100 |
| `updated_at` | date_time | 100/100 |
| `sequences` | multi_entity | 98/100 |
| `updated_by` | entity | 4/100 |
| `filmstrip_image` | image | 1/100 |
| `image_blur_hash` | text | 1/100 |
| `sg_versions` | multi_entity | 1/100 |

23 of 41 rankable fields are never populated here. Checkbox, summary, calculated and pivot fields are excluded: `False` and `0` are not null, so they read as fully populated (probe 007).

**Links set**

| field | data type | set on | points at |
|---|---|---|---|
| `image_source_entity` | entity | 100/100 | Asset 99, Version 1 |
| `sequences` | multi_entity | 98/100 | Sequence 1403 |
| `sg_versions` | multi_entity | 1/100 | Version 1 |
| `shots` | multi_entity | 100/100 | Shot 4219 |
| `tasks` | multi_entity | 100/100 | Task 400 |

16 of 21 link fields are empty on every sampled row. `project`, `created_by` and `updated_by` are excluded (probe 005).
