---
tags: [dotted-field, custom-field, custom-entity, entity-field, on-set]
endpoints: [GET /entity/<type>/<id>, GET /entity/<type>, POST /entity/<type>/_search]
phase: read
scope: api
measured: sandbox project written, 2026-11-11; one custom-slot row, one Slate, one Version, deleted
verdict: A dotted path reaches an `sg_` field through an `sg_` entity field, on a custom entity and on a built-in one, and across two hops: projection on GET and _search, and filter, all match.
---

# 138_dotted_custom_field

**Q** Does a dotted read or filter reach a custom field through an entity field, on a custom entity and
on a built-in one, and across two hops?

**Endpoint** `GET /entity/<type>/<id>?fields= ; POST /entity/<type>/_search ; GET /entity/<type>?filter[...]`

**Docs claim** The REST docs show dotted paths on stock fields. Probes 016 and 059 measured stock
paths only.

**Actual**

```
<link>   an sg_ entity field on Slate whose valid_types is one custom slot
<target> an sg_ text field on that slot      <slate_text> an sg_ text field on Slate

path                                                  GET ?fields  _search fields  filter is / is nomatch / starts_with  GET ?filter[path]
Slate      <link>.CustomEntityNN.<target>              value        value          1 / 0 / 1                         1
Version    entity.Slate.<slate_text>                   value        value          1 / 0 / 1                         1
Version    entity.Slate.<link>.CustomEntityNN.<target> value        value          1 / 0 / 1                         1
Version    entity.Slate.<link>                         {"id": <id>, "name": "zzprobe_138", "type": "CustomEntityNN"}
```

**Teaches**
- `sg_` fields behave like stock ones in a dotted path: write the path as
  `<field>.<Type>.<field>`, with the custom entity's schema name (`CustomEntityNN`), never its
  display name.
- Two hops work in a projection and in a filter, so a list of Versions can return the lens or camera
  detail of the take they belong to in one `_search`.
- The single-type entity field was chosen so the middle segment is certain. Through a field listing
  several types, the projection drops a path whose type is not in `valid_types` (probe 059).
- Through a stock multi_entity field a dotted projection is silently empty while the filter works
  (probe 016). An `sg_` multi_entity field was not measured here.
