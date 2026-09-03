---
tags: [entity-type, project, page, fill-rate, status, link, inspector]
scope: project
project: Big Buck Bunny
title: Attachment
verdict: On Big Buck Bunny, Attachment has 1 page built for it and populates 18 of 29 rankable fields across 100 sampled rows.
---
# Attachment

What Big Buck Bunny does with `Attachment`, from its 100 most recent rows.

**Pages**

| id | page | page_type | columns |
|---|---|---|---|
| 5108 | Files | canvas | 8 |

The layout is the `PageSetting` row whose `user` is null (probe 023). The columns are schema field names and go to `?fields` verbatim.

### Files

`Attachment`, page 5108, `page_type` `canvas`. 8 columns, in order.

```
this_file,image,attachment_links,sg_status_list,description,created_by,created_at,tags
```

**Usable statuses**

| field | usable | hidden | usable values | default |
|---|---|---|---|---|
| `sg_status_list` | 2 | 0 | `fin (Final)`, `na (N/A)` | na |

Read with `project_id=70`: `valid_values` minus `hidden_values`. The API accepts a hidden code on a write, so subtract it yourself.

**Fill rates**

| field | data type | filled |
|---|---|---|
| `cached_display_name` | text | 100/100 |
| `created_at` | date_time | 100/100 |
| `created_by` | entity | 100/100 |
| `display_name` | text | 100/100 |
| `filename` | text | 100/100 |
| `project` | entity | 100/100 |
| `this_file` | url | 100/100 |
| `updated_at` | date_time | 100/100 |
| `updated_by` | entity | 100/100 |
| `file_size` | number | 97/100 |
| `filmstrip_image` | image | 75/100 |
| `image` | image | 75/100 |
| `image_source_entity` | entity | 75/100 |
| `file_extension` | text | 26/100 |
| `sg_status_list` | status_list | 26/100 |
| `attachment_links` | multi_entity | 3/100 |
| `image_blur_hash` | text | 3/100 |
| `original_fname` | text | 1/100 |

11 of 29 rankable fields are never populated here. Checkbox, summary, calculated and pivot fields are excluded: `False` and `0` are not null, so they read as fully populated (probe 007).

**Links set**

| field | data type | set on | points at |
|---|---|---|---|
| `attachment_links` | multi_entity | 3/100 | Version 3 |
| `image_source_entity` | entity | 75/100 | Attachment 75 |

6 of 8 link fields are empty on every sampled row. `project`, `created_by` and `updated_by` are excluded (probe 005).
