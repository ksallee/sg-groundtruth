---
tags: [link, entity-field, multi-entity, inspector, project]
scope: project
project: Big Buck Bunny
verdict: On Big Buck Bunny, 28 link fields hold a value across 9 entity types. Measure the link field per project rather than hardcoding one.
---
# 005_link_usage

Which entity and multi-entity fields actually hold anything on Big Buck Bunny, from the same 100-row sample as the fill rates. `project`, `created_by` and `updated_by` are excluded: every row has them and they say nothing about how the project is used.

A client that hardcodes a link field is guessing. Read the field that is set here, and read what it points at rather than assuming the type.

### Asset

| field | data type | set on | points at |
|---|---|---|---|
| `image_source_entity` | entity | 100/100 | Asset 99, Version 1 |
| `sequences` | multi_entity | 98/100 | Sequence 1403 |
| `sg_versions` | multi_entity | 1/100 | Version 1 |
| `shots` | multi_entity | 100/100 | Shot 4219 |
| `tasks` | multi_entity | 100/100 | Task 400 |

16 of 21 link fields are empty on every sampled row.

### Attachment

| field | data type | set on | points at |
|---|---|---|---|
| `attachment_links` | multi_entity | 3/100 | Version 3 |
| `image_source_entity` | entity | 75/100 | Attachment 75 |

6 of 8 link fields are empty on every sampled row.

### Note

| field | data type | set on | points at |
|---|---|---|---|
| `addressings_to` | multi_entity | 67/100 | HumanUser 99 |
| `note_links` | multi_entity | 100/100 | Shot 100 |
| `user` | entity | 81/100 | HumanUser 81 |

9 of 12 link fields are empty on every sampled row.

### Playlist

No link field on this type is set on any sampled row.

6 of 6 link fields are empty on every sampled row.

### Sequence

| field | data type | set on | points at |
|---|---|---|---|
| `assets` | multi_entity | 15/15 | Asset 1403 |
| `shots` | multi_entity | 15/15 | Shot 300 |

16 of 18 link fields are empty on every sampled row.

### Shot

| field | data type | set on | points at |
|---|---|---|---|
| `assets` | multi_entity | 100/100 | Asset 1409 |
| `image_source_entity` | entity | 100/100 | Shot 100 |
| `notes` | multi_entity | 100/100 | Note 1997 |
| `open_notes` | multi_entity | 100/100 | Note 1336 |
| `sg_sequence` | entity | 100/100 | Sequence 100 |
| `tasks` | multi_entity | 100/100 | Task 500 |

15 of 21 link fields are empty on every sampled row.

### Task

| field | data type | set on | points at |
|---|---|---|---|
| `entity` | entity | 100/100 | Shot 100 |
| `image_source_entity` | entity | 100/100 | Shot 100 |
| `sibling_tasks` | multi_entity | 100/100 | Task 500 |
| `step` | entity | 100/100 | Step 100 |
| `task_assignees` | multi_entity | 44/100 | HumanUser 44 |

10 of 15 link fields are empty on every sampled row.

### TimeLog

| field | data type | set on | points at |
|---|---|---|---|
| `entity` | entity | 100/100 | Task 100 |

1 of 2 link fields are empty on every sampled row.

### Version

| field | data type | set on | points at |
|---|---|---|---|
| `entity` | entity | 100/100 | Shot 99, Asset 1 |
| `image_source_entity` | entity | 1/100 | Version 1 |
| `sg_task` | entity | 1/100 | Task 1 |
| `user` | entity | 100/100 | HumanUser 100 |

13 of 17 link fields are empty on every sampled row.
