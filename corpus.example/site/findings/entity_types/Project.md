---
tags: [entity-type, schema, custom-field, inspector, list-field]
scope: site
title: Project
verdict: On this site Project has 9 sg_ fields and 2 vocabularies over 52 rows. The codes here are what the API stores; the labels are editable.
---
# Project

What this site configures on top of the shipped `Project` card. The card above is the API layer; everything here is one site's own.

52 rows site-wide, across every project. The 22 most recent were read for the link census below.

**`sg_` fields**

| field | data type | editable | display name |
|---|---|---|---|
| `sg_client_name` | text | yes | Client Name |
| `sg_description` | text | yes | Description |
| `sg_flow_am_id` | text | yes | Flow AM ID |
| `sg_flow_schema_config_version` | text | yes | Flow Schema Config Version |
| `sg_latest_version` | summary | yes | Latest Version |
| `sg_release_date` | date | yes | Release Date |
| `sg_status` | list | yes | Status |
| `sg_temp_due` | date | yes | Temp Due |
| `sg_type` | list | yes | Type |

`/schema` does not mark which of these shipped with Flow Production Tracking and which were added here, so this is the whole namespace on the type.

**Vocabularies**

| field | data type | values | vocabulary | default |
|---|---|---|---|---|
| `sg_status` | list | 4 | `Bidding`, `Active`, `Lost`, `Hold` |  |
| `sg_type` | list | 5 | `Commercial`, `Episodic`, `Feature`, `Game`, `Other` |  |

Site-wide: `valid_values` is byte-identical at every scope (probe 009). Which of these values a project can select is the project layer of this card.

**Links populated site-wide**

| field | data type | set on | points at |
|---|---|---|---|
| `image_source_entity` | entity | 4/22 | Project 4 |
| `layout_project` | entity | 21/22 | Project 21 |
| `task_templates` | multi_entity | 1/22 | TaskTemplate 1 |
| `users` | multi_entity | 11/22 | HumanUser 17 |

3 of 7 link fields are empty on every sampled row. Which ones a single project fills is the project layer.
