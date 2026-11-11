---
tags: [schema, custom-field, entity-field, multi-entity, destructive, trap]
endpoints: [POST /schema/<Type>/fields, GET /schema/<Type>/fields, GET /schema/<Type>/fields/<field>, DELETE /schema/<Type>/fields/<field>, PUT /schema/<Type>/fields/<field>]
phase: schema
scope: api
measured: site-wide, 2026-11-11; three link fields created on one custom slot and retired, with four reverse fields; no rows
verdict: Every entity or multi_entity field makes a visible, editable multi_entity on each linked type. No create property stops it, and DELETE of the reverse field retires the forward field too.
---

# 142_reverse_field

**Q** The reverse field an entity or multi_entity field makes on its linked type: what is it named, is it
in the schema, can its creation be avoided, and can it be retired on its own?

**Endpoint** `POST /schema/<Type>/fields ; GET /schema/<Type>/fields ; DELETE /schema/<Type>/fields/<field>`

**Docs claim** Silent. Probes 116 and 121 saw reverse fields only in the event log.

**Actual**

```
<A>, <B>: two enabled custom slots. Fields created on <A>.

entity on <A>, valid_types [<B>]          -> 201 sg_zzprobe_142_link
  new on <B>: sg_<A's display name, plural>   multi_entity, valid_types ['<A>'], editable True,
              visible True, name '<A's display name> <-> zzprobe 142 link'
  GET /entity/<b>?fields=<reverse>        -> 200
multi_entity on <A>, valid_types [<B>]    -> 201 sg_zzprobe_142_links
  new on <B>: custom_entity<a>_sg_zzprobe_142_links_custom_entity<a>s   multi_entity, valid_types ['<A>'],
              name '<A's display name, plural> <-> zzprobe 142 links'
entity on <A>, valid_types [<A>]          -> 201 sg_zzprobe_142_self; reverse sg_<plural> on <A> itself

entity with {"property_name": "reverse", "value": false}  (and "create_reverse")
  -> 400 code 103 "API schema_field_create() invalid property 'reverse': ...
     Valid property names: ["name", "visible", "description", "summary_default", "valid_types", "custom_metadata"]"

DELETE /schema/<B>/fields/<reverse of sg_zzprobe_142_link>  -> 204
  reverse live after: False     forward <A>.sg_zzprobe_142_link live after: False
  a later DELETE of the forward field -> 404
DELETE of a forward field -> its reverse field retired with it (multi_entity measured; probe 121 for entity)
```

**Reverse field names**

| forward field | reverse field on each linked type |
|---|---|
| `entity` | `sg_<source type's display name, lowercased, plural>`, display name `<source display name> <-> <field display name>` |
| `multi_entity` | `<source slug>_<field>_<source slug>s`, `<source slug>` the REST slug in singular, e.g. `custom_entityNN` |

**Teaches**
- Plan for a field on every linked type: one per type in `valid_types` (probe 121), each
  `visible: true` and `editable: true` in that type's schema.
- The entity case is named after the source type's **display name**, not its schema name, so a
  slot's reverse fields change name pattern with what the site calls it. What the server picks for a
  second entity field from the same source to the same target was not measured.
- No create property suppresses it. The 400 lists the accepted properties for an entity field, and
  none is about the reverse.
- **Retiring a reverse field retires its forward field.** It is one link with two names: delete
  either and both go, and both names stay spent until the Trash is emptied (probe 019). Hide a
  reverse field rather than deleting it; whether `visible: false` is accepted on one was not
  measured, because the reverse was gone by then.
