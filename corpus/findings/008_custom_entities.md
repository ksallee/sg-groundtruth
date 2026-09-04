---
tags: [schema, custom-entity, discovery]
endpoints: [GET /schema]
phase: schema
scope: api
measured: site-wide, /schema and the 99 CustomEntity slots
verdict: Presence in /schema is the enablement test for a custom entity: a slot absent from the listing 404s. Slot numbers are non-contiguous and site-specific, so read name.value and never hardcode one.
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

slots absent from /schema: 89 (first: ['CustomEntity08', 'CustomEntity09', 'CustomEntity10'])

addressing an absent slot directly:
  GET /schema/CustomEntity08 -> 404
    {"errors":[{"id":"...","status":404,"code":103,"title":"Not Found","source":null,
                "detail":"Entity type 'CustomEntity08' does not exist.","meta":null}]}
  GET /schema/CustomEntity08/fields -> 404   same body
  CustomEntity09, both paths -> 404          same body
```

**Teaches**
- Presence in /schema is the enablement test, in both directions. A slot in the listing is enabled, and
  a slot absent from it is unaddressable: `GET /schema/CustomEntity08` and
  `GET /schema/CustomEntity08/fields` both return 404 `Entity type 'CustomEntity08' does not exist.`
  Enumerate `/schema` rather than probing slot numbers.
- On the probed site every slot in `/schema` read `visible: true`, so `visible: false` was never observed.
  Treat absence, not `visible`, as the disabled signal. A site with a slot enabled and then disabled would
  settle whether `visible` can read False.
- Never hardcode a slot number: they are non-contiguous and site-specific. On the probed site the enabled slots are 01-07, 19, 29 and 66. Look a slot up by its `name.value` display name.
- A connection entity is its own type, `CustomEntity29_sg_scene_Connection`, and its display name is machine-derived from the type name rather than studio-chosen.
- Display names are free text and may include a trailing space (`CustomEntity66` above), so match them trimmed.
