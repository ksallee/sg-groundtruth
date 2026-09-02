---
tags: [schema, custom-entity, discovery]
scope: api
verdict: Presence in /schema is the enablement test for a custom entity: a disabled slot is absent. Slot numbers are non-contiguous and site-specific, so read name.value and never hardcode one.
---

# 008_custom_entities

**Q** Which CustomEntityNN slots are enabled on a site, and where does the real display name come from?

**Endpoint** `GET /api/v1/schema`

**Docs claim** Custom entities are CustomEntityNN; the display name is in the schema; a slot cannot be enabled over REST.

**Actual**

```
total entity types in /schema: 114
custom entity slots present: 11
custom entity slots enabled:  11

enabled:                     (display names below are placeholders; real ones are studio-chosen)
  CustomEntity01           display='<custom entity display name>'
  CustomEntity02..07, 19, 29                                   (8 more, identical in shape)
  CustomEntity29_sg_scene_Connection display='Custom Entity29 Sg Scene Connection'
  CustomEntity66           display='<custom entity display name> '

sample of disabled slots (first 5):
  (none - every slot in /schema was visible)
```

**Teaches**
- Presence in /schema is the enablement test: a disabled slot never appears and `visible` never reads False. On the probed site the present and enabled counts are both 11.
- Never hardcode a slot number: they are non-contiguous and site-specific. On the probed site the enabled slots are 01-07, 19, 29 and 66. Look a slot up by its `name.value` display name.
- A connection entity is its own type, `CustomEntity29_sg_scene_Connection`, and its display name is machine-derived from the type name rather than studio-chosen.
- Display names are free text and may include a trailing space (`CustomEntity66` above), so match them trimmed.
