---
tags: [schema, custom-entity, discovery]
verdict: /schema returns ONLY enabled custom entities (11 slots, all visible) - a disabled slot is simply absent, so presence in /schema is the enablement test. Slot numbers are non-contiguous and site-specific (01-07, 19, 29, 66 here); resolve display names from name.value and never hardcode a number. Connection entities appear as their own type.
---

# 008_custom_entities

**Endpoint** `GET /api/v1/schema`

**Docs claim** Custom entities are CustomEntityNN; display name lives in the schema; cannot be enabled over REST.

**Actual**

```
total entity types in /schema: 113
custom entity slots present: 11
custom entity slots enabled:  11

enabled:
  CustomEntity01           display='GABLE2GABLE Orchard Juniper'
  CustomEntity02           display='GABLE2GABLE Orchard Kiln'
  CustomEntity03           display='Code Vapor Lantern'
  CustomEntity04           display='Uma Stilt'
  CustomEntity05           display='Wren Frost'
  CustomEntity06           display='Delta Mesa Lantern'
  CustomEntity07           display='Lux Brenn'
  CustomEntity19           display='Sable'
  CustomEntity29           display='Flint'
  CustomEntity29_sg_scene_Connection display='Custom Entity29 Sg Scene Juniper'
  CustomEntity66           display='Yarrow Lantern Custom Entity'

sample of disabled slots (first 5):
```

**Verdict** /schema returns ONLY enabled custom entities (11 slots, all visible) - a disabled slot is simply absent, so presence in /schema is the enablement test. Slot numbers are non-contiguous and site-specific (01-07, 19, 29, 66 here); resolve display names from name.value and never hardcode a number. Connection entities appear as their own type.
