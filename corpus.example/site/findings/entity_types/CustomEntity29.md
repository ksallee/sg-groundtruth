---
tags: [entity-type, custom-entity, schema, custom-field, inspector, list-field]
scope: site
title: Location
verdict: CustomEntity29 (Location) is a slot this site enabled: 3 rows, 9 sg_ fields, 1 vocabularies. It has no API layer; site and project are the only scopes it exists at.
---
# Location (CustomEntity29)

A custom entity slot this site enabled. `CustomEntity29` is what a client addresses it as, at `/entity/custom_entity29s`; the display name above is renamed in the web interface and the slot number is not. Flow Production Tracking ships no such type and the corpus documents none, so this card has no `api` layer behind it: this file and its project counterparts are the whole record of it.

3 rows site-wide, across every project. The 3 most recent were read for the link census below.

**`sg_` fields**

| field | data type | editable | display name |
|---|---|---|---|
| `sg_drone_` | checkbox | yes | Drone? |
| `sg_google_maps_link` | text | yes | Google Maps Link |
| `sg_irl_location` | text | yes | IRL Location |
| `sg_lidar_` | checkbox | yes | LiDAR? |
| `sg_scene` | multi_entity | yes | Scene |
| `sg_shoot_days` | multi_entity | yes | Shoot Day <-> Location |
| `sg_slates` | multi_entity | yes | Slate <-> Script Location |
| `sg_status_list` | status_list | yes | Status |
| `sg_versions` | multi_entity | yes | Version <-> Link |

`/schema` does not mark which of these shipped with Flow Production Tracking and which were added here, so this is the whole namespace on the type.

**Vocabularies**

| field | data type | values | vocabulary | default |
|---|---|---|---|---|
| `sg_status_list` | status_list | 3 | `wtg (Waiting to Start)`, `ip (In Progress)`, `fin (Final)` | wtg |

Site-wide: `valid_values` is byte-identical at every scope (probe 009). Which of these values a project can select is the project layer of this card.

**Links populated site-wide**

| field | data type | set on | points at |
|---|---|---|---|
| `sg_shoot_days` | multi_entity | 3/3 | ShootDay 11 |
| `sg_slates` | multi_entity | 3/3 | Slate 16 |

6 of 8 link fields are empty on every sampled row. Which ones a single project fills is the project layer.
