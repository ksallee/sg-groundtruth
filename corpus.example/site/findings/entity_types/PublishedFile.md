---
tags: [entity-type, schema, custom-field, inspector, list-field]
scope: site
title: PublishedFile
verdict: On this site PublishedFile has 8 sg_ fields and 1 vocabularies over 183 rows. The codes here are what the API stores; the labels are editable.
---
# PublishedFile

What this site configures on top of the shipped `PublishedFile` card. The card above is the API layer; everything here is one site's own.

183 rows site-wide, across every project. The 100 most recent were read for the link census below.

**`sg_` fields**

| field | data type | editable | display name |
|---|---|---|---|
| `sg_flow_am_id` | text | yes | Flow AM ID |
| `sg_flow_am_type` | text | yes | Flow AM type |
| `sg_flow_is_derivative` | checkbox | yes | Flow Is Derivative |
| `sg_flow_is_template` | checkbox | yes | Flow Is Template |
| `sg_flow_revision_id` | text | yes | Flow Revision ID |
| `sg_flow_template_pipeline_step` | text | yes | Flow Template Pipeline Step |
| `sg_status_list` | status_list | yes | Status |
| `sg_uploaded_file` | url | yes | Uploaded File |

`/schema` does not mark which of these shipped with Flow Production Tracking and which were added here, so this is the whole namespace on the type.

**Vocabularies**

| field | data type | values | vocabulary | default |
|---|---|---|---|---|
| `sg_status_list` | status_list | 3 | `wtg (Waiting to Start)`, `ip (In Progress)`, `cmpt (Complete)` | wtg |

Site-wide: `valid_values` is byte-identical at every scope (probe 009). Which of these values a project can select is the project layer of this card.

**Links populated site-wide**

| field | data type | set on | points at |
|---|---|---|---|
| `entity` | entity | 100/100 | Asset 74, Project 26 |
| `image_source_entity` | entity | 64/100 | PublishedFile 64 |
| `published_file_type` | entity | 100/100 | PublishedFileType 100 |
| `task` | entity | 74/100 | Task 74 |
| `version` | entity | 3/100 | Version 3 |

4 of 9 link fields are empty on every sampled row. Which ones a single project fills is the project layer.
