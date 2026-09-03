---
tags: [entity-type, schema, custom-field, inspector, list-field]
scope: site
title: Task
verdict: On this site Task has 10 sg_ fields and 2 vocabularies over 7445 rows. The codes here are what the API stores; the labels are editable.
---
# Task

What this site configures on top of the shipped `Task` card. The card above is the API layer; everything here is one site's own.

7445 rows site-wide, across every project. The 100 most recent were read for the link census below.

**`sg_` fields**

| field | data type | editable | display name |
|---|---|---|---|
| `sg_description` | text | yes | Description |
| `sg_fp_test_checkbox` | checkbox | yes | FP Test Checkbox |
| `sg_fp_test_checkbox_v2` | checkbox | yes | FP Test Checkbox V2 |
| `sg_priority_1` | list | yes | Priority |
| `sg_skip_art_director_approval` | checkbox | yes | Skip Art Director Approval |
| `sg_skip_lead_approval` | checkbox | yes | Skip Lead Approval |
| `sg_skip_vfx_supervisor_approval` | checkbox | yes | Skip Vfx Supervisor Approval |
| `sg_sort_order` | number | yes | Sort Order |
| `sg_status_list` | status_list | yes | Status |
| `sg_versions` | multi_entity | no | Versions |

`/schema` does not mark which of these shipped with Flow Production Tracking and which were added here, so this is the whole namespace on the type.

**Vocabularies**

| field | data type | values | vocabulary | default |
|---|---|---|---|---|
| `sg_priority_1` | list | 3 | `1_Tier`, `2_Tier`, `3_Tier` |  |
| `sg_status_list` | status_list | 10 | `wtg (Waiting to Start)`, `ip (In Progress)`, `fin (Final)`, `apr (Approved)`, `dis (Disabled)`, `na (N/A)`, `hld (On Hold)`, `rev (Pending Review)`, `omt (Omit)`, `ready (Ready)` | wtg |

Site-wide: `valid_values` is byte-identical at every scope (probe 009). Which of these values a project can select is the project layer of this card.

**Links populated site-wide**

| field | data type | set on | points at |
|---|---|---|---|
| `entity` | entity | 100/100 | Shot 84, Asset 16 |
| `image_source_entity` | entity | 9/100 | Asset 9 |
| `sibling_tasks` | multi_entity | 100/100 | Task 345 |
| `step` | entity | 100/100 | Step 100 |
| `task_assignees` | multi_entity | 96/100 | HumanUser 96 |

10 of 15 link fields are empty on every sampled row. Which ones a single project fills is the project layer.
