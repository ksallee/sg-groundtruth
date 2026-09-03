---
tags: [entity-type, schema, custom-field, inspector, list-field]
scope: site
title: Playlist
verdict: On this site Playlist has 1 sg_ fields and 1 vocabularies over 3 rows. The codes here are what the API stores; the labels are editable.
---
# Playlist

What this site configures on top of the shipped `Playlist` card. The card above is the API layer; everything here is one site's own.

3 rows site-wide, across every project. The 2 most recent were read for the link census below.

**`sg_` fields**

| field | data type | editable | display name |
|---|---|---|---|
| `sg_date_and_time` | date_time | yes | Date and Time |

`/schema` does not mark which of these shipped with Flow Production Tracking and which were added here, so this is the whole namespace on the type.

**Vocabularies**

| field | data type | values | vocabulary | default |
|---|---|---|---|---|
| `media_center_viewed_by_current_user` | list | 2 | `read`, `unread` |  |

Site-wide: `valid_values` is byte-identical at every scope (probe 009). Which of these values a project can select is the project layer of this card.

**Links populated site-wide**

No link field on this type is set on any sampled row.

6 of 6 link fields are empty on every sampled row. Which ones a single project fills is the project layer.
