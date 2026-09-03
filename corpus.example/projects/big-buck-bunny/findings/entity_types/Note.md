---
tags: [entity-type, project, page, fill-rate, status, link, inspector]
scope: project
project: Big Buck Bunny
title: Note
verdict: On Big Buck Bunny, Note has 1 page built for it and populates 13 of 30 rankable fields across 100 sampled rows.
---
# Note

What Big Buck Bunny does with `Note`, from its 100 most recent rows.

**Pages**

| id | page | page_type | columns |
|---|---|---|---|
| 5116 | Notes | canvas | 9 |

The layout is the `PageSetting` row whose `user` is null (probe 023). The columns are schema field names and go to `?fields` verbatim.

### Notes

`Note`, page 5116, `page_type` `canvas`. 9 columns, in order.

```
subject,sg_status_list,note_links,user,addressings_to,content,sg_note_type,updated_at,read_by_current_user
```

1 of these are absent from `/schema/Note/fields`: `read_by_current_user`. `?fields` ignores a name a type does not have, so a stale column is silent rather than a 400.

**Usable statuses**

| field | usable | hidden | usable values | default |
|---|---|---|---|---|
| `sg_status_list` | 3 | 0 | `opn (Open)`, `ip (In Progress)`, `clsd (Closed)` | opn |

Read with `project_id=70`: `valid_values` minus `hidden_values`. The API accepts a hidden code on a write, so subtract it yourself.

**Fill rates**

| field | data type | filled |
|---|---|---|
| `cached_display_name` | text | 100/100 |
| `content` | text | 100/100 |
| `created_at` | date_time | 100/100 |
| `note_links` | multi_entity | 100/100 |
| `project` | entity | 100/100 |
| `publish_status` | text | 100/100 |
| `reply_content` | text | 100/100 |
| `sg_note_type` | list | 100/100 |
| `sg_status_list` | status_list | 100/100 |
| `subject` | text | 100/100 |
| `updated_at` | date_time | 100/100 |
| `user` | entity | 81/100 |
| `addressings_to` | multi_entity | 67/100 |

17 of 30 rankable fields are never populated here. Checkbox, summary, calculated and pivot fields are excluded: `False` and `0` are not null, so they read as fully populated (probe 007).

**Links set**

| field | data type | set on | points at |
|---|---|---|---|
| `addressings_to` | multi_entity | 67/100 | HumanUser 99 |
| `note_links` | multi_entity | 100/100 | Shot 100 |
| `user` | entity | 81/100 | HumanUser 81 |

9 of 12 link fields are empty on every sampled row. `project`, `created_by` and `updated_by` are excluded (probe 005).
