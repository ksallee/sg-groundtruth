---
tags: [entity-type, project, page, fill-rate, status, link, inspector]
scope: project
project: Big Buck Bunny
title: Playlist
verdict: On Big Buck Bunny, Playlist has 3 pages built for it and populates 9 of 23 rankable fields across 1 sampled rows.
---
# Playlist

What Big Buck Bunny does with `Playlist`, from its 1 most recent rows.

**Pages**

| id | page | page_type | columns |
|---|---|---|---|
| 5107 | Review | canvas | 5 |
| 5133 | unnamed | stream_detail | 0 |
| 5150 | unnamed | detail | 0 |

The layout is the `PageSetting` row whose `user` is null (probe 023). The columns are schema field names and go to `?fields` verbatim.

### Review

`Playlist`, page 5107, `page_type` `canvas`. 5 columns, in order.

```
code,sg_status,description,updated_at,updated_by
```

1 of these are absent from `/schema/Playlist/fields`: `sg_status`. `?fields` ignores a name a type does not have, so a stale column is silent rather than a 400.

**Fill rates**

| field | data type | filled |
|---|---|---|
| `cached_display_name` | text | 1/1 |
| `code` | text | 1/1 |
| `created_at` | date_time | 1/1 |
| `created_by` | entity | 1/1 |
| `external_share_count` | number | 1/1 |
| `media_center_viewed_by_current_user` | list | 1/1 |
| `project` | entity | 1/1 |
| `updated_at` | date_time | 1/1 |
| `updated_by` | entity | 1/1 |

14 of 23 rankable fields are never populated here. Checkbox, summary, calculated and pivot fields are excluded: `False` and `0` are not null, so they read as fully populated (probe 007).

**Links set**

No link field on this type is set on any sampled row.

6 of 6 link fields are empty on every sampled row. `project`, `created_by` and `updated_by` are excluded (probe 005).
