---
tags: [entity-type, custom-entity, schema, custom-field, inspector, list-field]
scope: site
title: Lenses
verdict: CustomEntity19 (Lenses) is a slot this site enabled: 2 rows, 9 sg_ fields, 2 vocabularies. It has no API layer; site and project are the only scopes it exists at.
---
# Lenses (CustomEntity19)

A custom entity slot this site enabled. `CustomEntity19` is what a client addresses it as, at `/entity/custom_entity19s`; the display name above is renamed in the web interface and the slot number is not. Flow Production Tracking ships no such type and the corpus documents none, so this card has no `api` layer behind it: this file and its project counterparts are the whole record of it.

2 rows site-wide, across every project. The 2 most recent were read for the link census below.

**`sg_` fields**

| field | data type | editable | display name |
|---|---|---|---|
| `sg_editorial_clip_name` | text | yes | Editorial Clip Name |
| `sg_focal_length` | text | yes | Focal Length |
| `sg_gridded_` | checkbox | yes | Gridded? |
| `sg_lens_model` | text | yes | Lens Model |
| `sg_lens_serial_number` | text | yes | Lens Serial Number |
| `sg_slates` | multi_entity | yes | Slate <-> Lens |
| `sg_status_list` | status_list | yes | Status |
| `sg_unit` | list | yes | Unit |
| `sg_versions` | multi_entity | yes | Version <-> Link |

`/schema` does not mark which of these shipped with Flow Production Tracking and which were added here, so this is the whole namespace on the type.

**Vocabularies**

| field | data type | values | vocabulary | default |
|---|---|---|---|---|
| `sg_status_list` | status_list | 3 | `wtg (Waiting to Start)`, `ip (In Progress)`, `fin (Final)` | wtg |
| `sg_unit` | list | 3 | `Main Unit`, `Aerial`, `Second Unit` |  |

Site-wide: `valid_values` is byte-identical at every scope (probe 009). Which of these values a project can select is the project layer of this card.

**Links populated site-wide**

No link field on this type is set on any sampled row.

6 of 6 link fields are empty on every sampled row. Which ones a single project fills is the project layer.
