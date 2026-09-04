---
tags: [query, filter, header, project, trap]
endpoints: [POST /entity/_text_search, POST /hierarchy/_expand, POST /hierarchy/_search]
phase: filter
scope: api
measured: sample project 1 of 1, read only
verdict: `/hierarchy/_expand` and `/hierarchy/_search` refuse the vendor content types every other POST requires and take `application/json` alone, so one shared POST helper 415s on half the API.
---

# 046_search_without_a_path

**Q** How do you search when you know neither the entity type nor the field path?

**Endpoint** `POST /entity/_text_search ; POST /hierarchy/_expand ; POST /hierarchy/_search`

**Docs claim** The reference lists all three. Nothing in it says the three do not share a content type.

**Actual**

```
=== the content type splits down the middle
POST /entity/_text_search   application/json                       -> 415, must be a vendor type
POST /entity/_text_search   application/vnd+shotgun.api3_array+json -> 200
POST /hierarchy/_expand     application/vnd+shotgun.api3_array+json -> 415
  source: {"content_type": "Content-Type must be one of: 'application/json'."}
POST /hierarchy/_expand     application/json                       -> 200
POST /hierarchy/_search     application/json                       -> 200

=== _text_search: entity_types is required and is also the filter
{"text": "<word>"}                          -> 400 entity_types is missing
{"text": "", "entity_types": {...}}         -> 400 text must be filled
{"entity_types": {"Shot": [["project", "is", {...}]], "Asset": [], "Version": []}} -> 200
row shape: {id, type, attributes: {name, links: ["", ""], status}, links: {self}}
  no fields parameter, and `links` is two strings, not an entity reference

=== _search: search_criteria counts the keys it recognises, not the keys you sent
{"entity": {"type": "Shot", "id": 862}}  -> 200
{"entity_type": "Shot"}                  -> 400 search_criteria size must be 1
{"Shot": 862}                            -> 400 search_criteria size must be 1
{"Shot": [862]}                          -> 400 search_criteria size must be 1
[{"entity_type": "Shot"}]                -> 400 search_criteria must be a hash

=== _expand: one level, and seed_entity_field changes nothing
{"path": "/Project/70"}                             -> 200, 879 bytes
{"path": "/Project/70", "seed_entity_field": ...}   -> 200, 879 bytes, identical
{"path": "/Project/999999999"}                      -> 400 code 107
  "Unexpected result looking for project: 999999999: 0 found."
children: [("Assets", entity_type, has_children), ("Shots", entity_type, has_children)]
```

**Teaches**

- **The vendor content type is not the API's rule, it is the endpoint's.** Half the POST endpoints
  demand it and `/hierarchy/*` refuses it. A client with one POST helper meets 415 on whichever half it
  was not written against. Both 415s name their legal set, so the error is enough to fix it.
- `search_criteria` must be a hash keyed exactly `entity`. `size must be 1` is counting recognised
  keys, so any other single key reads as a size problem and the real cause is never named. Two other
  shapes and a list were tried; only `{"entity": {"type", "id"}}` answers 200.
- `_text_search` returns a flattened row with no `fields` parameter: `name`, `status`, and a `links`
  pair of bare strings that cannot be followed. Re-read by `links.self` for anything else.
- `entity_types` maps a schema name to that type's own filter array, so one call can be scoped
  differently per type. Nothing else in the API keys a filter by the type it applies to.
- `_expand` returns one level. `children` names the next paths and `has_children` says which are worth
  a call, so walking a project costs one call per node.
- `_search` answers `incremental_path`, the breadcrumb to the row, and it runs through a field name
  (`sg_sequence`), so the tree follows the site's navigation configuration rather than a fixed shape.
