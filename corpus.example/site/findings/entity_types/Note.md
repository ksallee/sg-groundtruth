---
tags: [entity-type, schema, custom-field, inspector, list-field]
scope: site
title: Note
verdict: On this site Note has 2 sg_ fields and 2 vocabularies over 9190 rows. The codes here are what the API stores; the labels are editable.
---
# Note

What this site configures on top of the shipped `Note` card. The card above is the API layer; everything here is one site's own.

9190 rows site-wide, across every project. The 100 most recent were read for the link census below.

**`sg_` fields**

| field | data type | editable | display name |
|---|---|---|---|
| `sg_note_type` | list | yes | Type |
| `sg_status_list` | status_list | yes | Status |

`/schema` does not mark which of these shipped with Flow Production Tracking and which were added here, so this is the whole namespace on the type.

**Vocabularies**

| field | data type | values | vocabulary | default |
|---|---|---|---|---|
| `sg_note_type` | list | 2 | `Internal`, `Client` |  |
| `sg_status_list` | status_list | 3 | `opn (Open)`, `ip (In Progress)`, `clsd (Closed)` | opn |

Site-wide: `valid_values` is byte-identical at every scope (probe 009). Which of these values a project can select is the project layer of this card.

**Links populated site-wide**

| field | data type | set on | points at |
|---|---|---|---|
| `addressings_to` | multi_entity | 12/100 | HumanUser 12 |
| `attachments` | multi_entity | 3/100 | Attachment 3 |
| `note_links` | multi_entity | 90/100 | Task 87, Project 3 |
| `user` | entity | 100/100 | ApiUser 88, HumanUser 12 |

8 of 12 link fields are empty on every sampled row. Which ones a single project fills is the project layer.
