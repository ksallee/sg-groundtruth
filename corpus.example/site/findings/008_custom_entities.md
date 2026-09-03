---
tags: [schema, custom-entity, discovery, inspector]
scope: site
verdict: 2 custom entity slots are enabled here, the highest being CustomEntity29. The numbers are non-contiguous and mean nothing on another site.
---
# 008_custom_entities

`/schema` returns 106 entity types on this site, 3 of them custom slots. Presence in the listing is the enablement test, so every one of them is enabled and every other slot 404s when addressed directly.

**Enabled**

| slot | display name | REST path | rows |
|---|---|---|---|
| CustomEntity19 | Lenses | `custom_entity19s` | 2 |
| CustomEntity29 | Location | `custom_entity29s` | 3 |

**Connection slots**

Created by a multi-entity field rather than by an operator, and not addressed directly.

| slot | display name |
|---|---|
| CustomEntity29_sg_scene_Connection | Custom Entity29 Sg Scene Connection |

The slot numbers are this site's. Nothing about them transfers: read the display name from `/schema` and key on it.
