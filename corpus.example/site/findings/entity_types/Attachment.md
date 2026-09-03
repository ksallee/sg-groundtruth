---
tags: [entity-type, schema, custom-field, inspector, list-field]
scope: site
title: Attachment
verdict: On this site Attachment has 2 sg_ fields and 2 vocabularies over 913 rows. The codes here are what the API stores; the labels are editable.
---
# Attachment

What this site configures on top of the shipped `Attachment` card. The card above is the API layer; everything here is one site's own.

913 rows site-wide, across every project. The 100 most recent were read for the link census below.

**`sg_` fields**

| field | data type | editable | display name |
|---|---|---|---|
| `sg_status_list` | status_list | yes | Status |
| `sg_type` | text | yes | Type |

`/schema` does not mark which of these shipped with Flow Production Tracking and which were added here, so this is the whole namespace on the type.

**Vocabularies**

| field | data type | values | vocabulary | default |
|---|---|---|---|---|
| `processing_status` | list | 4 | `thumbnail_pending`, `unverified`, `clean`, `infected` |  |
| `sg_status_list` | status_list | 2 | `fin (Final)`, `na (N/A)` | na |

Site-wide: `valid_values` is byte-identical at every scope (probe 009). Which of these values a project can select is the project layer of this card.

**Links populated site-wide**

| field | data type | set on | points at |
|---|---|---|---|
| `attachment_links` | multi_entity | 76/100 | Version 76 |
| `image_source_entity` | entity | 62/100 | Attachment 62 |

6 of 8 link fields are empty on every sampled row. Which ones a single project fills is the project layer.
