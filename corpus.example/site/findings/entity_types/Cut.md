---
tags: [entity-type, schema, custom-field, inspector, list-field]
scope: site
title: Cut
verdict: On this site Cut has 3 sg_ fields and 2 vocabularies over 3 rows. The codes here are what the API stores; the labels are editable.
---
# Cut

What this site configures on top of the shipped `Cut` card. The card above is the API layer; everything here is one site's own.

3 rows site-wide, across every project.

**`sg_` fields**

| field | data type | editable | display name |
|---|---|---|---|
| `sg_cut_type` | list | yes | Type |
| `sg_scene` | entity | yes | Scene |
| `sg_status_list` | status_list | yes | Status |

`/schema` does not mark which of these shipped with Flow Production Tracking and which were added here, so this is the whole namespace on the type.

**Vocabularies**

| field | data type | values | vocabulary | default |
|---|---|---|---|---|
| `sg_cut_type` | list | 4 | `Boards`, `Assembly`, `Director`, `Final` |  |
| `sg_status_list` | status_list | 4 | `ip (In Progress)`, `hld (On Hold)`, `apr (Approved)`, `na (N/A)` | ip |

Site-wide: `valid_values` is byte-identical at every scope (probe 009). Which of these values a project can select is the project layer of this card.
