---
tags: [entity-type, schema, custom-field, inspector, list-field]
scope: site
title: Sequence
verdict: On this site Sequence has 13 sg_ fields and 1 vocabularies over 140 rows. The codes here are what the API stores; the labels are editable.
---
# Sequence

What this site configures on top of the shipped `Sequence` card. The card above is the API layer; everything here is one site's own.

140 rows site-wide, across every project. The 87 most recent were read for the link census below.

**`sg_` fields**

| field | data type | editable | display name |
|---|---|---|---|
| `sg_duration` | text | yes | duration |
| `sg_published_files` | multi_entity | yes | Published File <-> Link |
| `sg_scenes` | multi_entity | yes | Scenes |
| `sg_sequence_full_name` | text | yes | Sequence Full Name |
| `sg_sequence_page_count` | text | yes | Sequence Page Count |
| `sg_sequence_scenes` | multi_entity | yes | Sequence Scenes |
| `sg_sequence_type` | list | yes | Type |
| `sg_sequence_vendor` | entity | yes | Sequence Vendor |
| `sg_slates` | multi_entity | yes | Slate <-> Sequence |
| `sg_status_list` | status_list | yes | Status |
| `sg_timecode` | timecode | yes | timecode |
| `sg_vendor_groups` | multi_entity | yes | Vendor Groups |
| `sg_versions` | multi_entity | yes | Version <-> Link |

`/schema` does not mark which of these shipped with Flow Production Tracking and which were added here, so this is the whole namespace on the type.

**Vocabularies**

| field | data type | values | vocabulary | default |
|---|---|---|---|---|
| `sg_status_list` | status_list | 3 | `wtg (Waiting to Start)`, `ip (In Progress)`, `fin (Final)` | ip |

Site-wide: `valid_values` is byte-identical at every scope (probe 009). Which of these values a project can select is the project layer of this card.

**Links populated site-wide**

| field | data type | set on | points at |
|---|---|---|---|
| `assets` | multi_entity | 15/87 | Asset 1403 |
| `image_source_entity` | entity | 6/87 | Version 6 |
| `sg_sequence_scenes` | multi_entity | 1/87 | Scene 1 |
| `sg_sequence_vendor` | entity | 5/87 | Group 5 |
| `sg_slates` | multi_entity | 3/87 | Slate 19 |
| `sg_versions` | multi_entity | 1/87 | Version 2 |
| `shots` | multi_entity | 43/87 | Shot 417 |
| `tasks` | multi_entity | 45/87 | Task 1335 |

10 of 18 link fields are empty on every sampled row. Which ones a single project fills is the project layer.
