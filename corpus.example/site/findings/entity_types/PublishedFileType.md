---
tags: [entity-type, schema, custom-field, inspector, list-field]
scope: site
title: PublishedFileType
verdict: On this site PublishedFileType has 1 sg_ fields and 1 vocabularies over 8 rows. The codes here are what the API stores; the labels are editable.
---
# PublishedFileType

What this site configures on top of the shipped `PublishedFileType` card. The card above is the API layer; everything here is one site's own.

8 rows site-wide, across every project. The 8 most recent were read for the link census below.

**`sg_` fields**

| field | data type | editable | display name |
|---|---|---|---|
| `sg_status_list` | status_list | yes | Status |

`/schema` does not mark which of these shipped with Flow Production Tracking and which were added here, so this is the whole namespace on the type.

**Vocabularies**

| field | data type | values | vocabulary | default |
|---|---|---|---|---|
| `sg_status_list` | status_list | 3 | `wtg (Waiting to Start)`, `ip (In Progress)`, `cmpt (Complete)` | wtg |

Site-wide: `valid_values` is byte-identical at every scope (probe 009). Which of these values a project can select is the project layer of this card.

**Links populated site-wide**

No link field on this type is set on any sampled row.

2 of 2 link fields are empty on every sampled row. Which ones a single project fills is the project layer.
