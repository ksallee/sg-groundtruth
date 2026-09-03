---
tags: [entity-type, project, page, fill-rate, status, link, inspector]
scope: project
project: Big Buck Bunny
title: Version
verdict: On Big Buck Bunny, Version has 3 pages built for it and populates 25 of 65 rankable fields across 100 sampled rows.
---
# Version

What Big Buck Bunny does with `Version`, from its 100 most recent rows.

**Pages**

| id | page | page_type | columns |
|---|---|---|---|
| 5105 | Versions | canvas | 8 |
| 5134 | unnamed | stream_detail | 0 |
| 5156 | unnamed | detail | 0 |

The layout is the `PageSetting` row whose `user` is null (probe 023). The columns are schema field names and go to `?fields` verbatim.

### Versions

`Version`, page 5105, `page_type` `canvas`. 8 columns, in order.

```
image,sg_status_list,code,entity,sg_task,user,description,created_at
```

**Usable statuses**

| field | usable | hidden | usable values | default |
|---|---|---|---|---|
| `sg_status_list` | 14 | 2 | `na (N/A)`, `rev (Pending Review)`, `vwd (Viewed)`, `apr (Approved)`, `custom (CustomIcon)`, `fin (Final)`, `ip (In Progress)`, `clsd (Closed)`, `cmpt (Complete)`, `cfrm (Confirmed)`, `pndad (Pending Art Director)`, `part (partial)`, `pass`, `pndng (Pending)` | rev |

Read with `project_id=70`: `valid_values` minus `hidden_values`. The API accepts a hidden code on a write, so subtract it yourself.

**Fill rates**

| field | data type | filled |
|---|---|---|
| `cached_display_name` | text | 100/100 |
| `code` | text | 100/100 |
| `created_at` | date_time | 100/100 |
| `created_by` | entity | 100/100 |
| `description` | text | 100/100 |
| `entity` | entity | 100/100 |
| `project` | entity | 100/100 |
| `sg_status_list` | status_list | 100/100 |
| `updated_at` | date_time | 100/100 |
| `updated_by` | entity | 100/100 |
| `user` | entity | 100/100 |
| `viewed_by_current_user` | list | 100/100 |
| `sg_version_type` | list | 99/100 |
| `filmstrip_image` | image | 1/100 |
| `image` | image | 1/100 |
| `image_blur_hash` | text | 1/100 |
| `image_source_entity` | entity | 1/100 |
| `otio_playable` | text | 1/100 |
| `sg_task` | entity | 1/100 |
| `sg_uploaded_movie` | url | 1/100 |
| `sg_uploaded_movie_frame_rate` | float | 1/100 |
| `sg_uploaded_movie_image` | url | 1/100 |
| `sg_uploaded_movie_mp4` | url | 1/100 |
| `sg_uploaded_movie_transcoding_status` | number | 1/100 |
| `uploaded_movie_duration` | float | 1/100 |

40 of 65 rankable fields are never populated here. Checkbox, summary, calculated and pivot fields are excluded: `False` and `0` are not null, so they read as fully populated (probe 007).

**Links set**

| field | data type | set on | points at |
|---|---|---|---|
| `entity` | entity | 100/100 | Shot 99, Asset 1 |
| `image_source_entity` | entity | 1/100 | Version 1 |
| `sg_task` | entity | 1/100 | Task 1 |
| `user` | entity | 100/100 | HumanUser 100 |

13 of 17 link fields are empty on every sampled row. `project`, `created_by` and `updated_by` are excluded (probe 005).
