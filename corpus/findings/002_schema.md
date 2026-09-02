---
tags: [schema, cost, discovery]
scope: api
measured: first sample project, schema reads only
verdict: Fetch /schema once for the type list, then /schema/<Type>/fields only for types you actually need: it is the expensive call (48KB, ~330ms each) and must never be looped over all types.
---

# 002_schema

**Q** Which schema endpoints exist, what does each cost, and what shape does each return?

**Endpoint** `GET /api/v1/schema[/<EntityType>[/fields[/<field>]]]  ± project_id`

**Docs claim** Schema is readable over REST; project scoping via project_id.

**Actual**

```
200   573ms     13368b  /schema
                            dict, 114 keys, first: ['ActionMenuItem', 'ApiUser', 'ApiUserProjectConnection', 'AppWelcomeUserConnection', 'Asset']
200   264ms       138b  /schema/Version
                            dict, 2 keys, first: ['name', 'visible']
200   327ms     48111b  /schema/Version/fields
                            dict, 71 keys, first: ['sg_first_frame', 'sg_uploaded_movie', 'flagged', 'sg_uploaded_movie_transcoding_status', 'tasks']
200   586ms      1211b  /schema/Version/fields/sg_status_list
                            dict, 11 keys, first: ['name', 'description', 'custom_metadata', 'entity_type', 'data_type']
200   358ms     13395b  /schema?{'project_id': 70}
                            dict, 114 keys, first: ['ActionMenuItem', 'ApiUser', 'ApiUserProjectConnection', 'AppWelcomeUserConnection', 'Asset']
200   329ms     48139b  /schema/Version/fields?{'project_id': 70}
                            dict, 71 keys, first: ['sg_first_frame', 'sg_uploaded_movie', 'flagged', 'sg_uploaded_movie_transcoding_status', 'tasks']

every enumeration spelling guessed, all 404:
404   315ms       178b  /schema/entity_types
                            {"errors":[{"id":"db7b1e42661b995196c86ec0c9fab48d","status":404,"code":103,"title":"Not Found","source":null,"detail":"Entity type 'entity_types' does not exist.","meta":null}]}
404              177b  /schema/entity_type    detail: "Entity type 'entity_type' does not exist."
404              174b  /schema/entities       detail: "Entity type 'entities' does not exist."
404              171b  /schema/types          detail: "Entity type 'types' does not exist."
404              172b  /schema/_types         detail: "Entity type '_types' does not exist."
404              138b  /entity_types          detail: null
404              138b  /entity                detail: null
404              138b  /api/v1/entity         detail: null
```

**Teaches**
- A connection type's REST slug collapses the doubled underscore. `Asset_linked_projects_Connection` is
  addressable as itself or as `asset_linked_projects_connections`, while the naive snake_case rule gives
  `asset_linked_projects__connections`, which 404s. Ten types on the probed site are affected
  (`recipes/003`).


Sizes below are from the probed site.

| call | size | what it gives |
|---|---|---|
| `/schema` | 13KB | the type list, nothing per type |
| `/schema/<Type>` | 138b | `name` and `visible` |
| `/schema/<Type>/fields` | 48KB | every field on the type |
| `/schema/<Type>/fields/<field>` | 1.2KB | one field, when you know its name |
| `/schema/entity_types` | 404 `"Not Found"` | no lighter enumeration exists |
| `/entity_types`, `/entity`, `/api/v1/entity` | 404, `detail: null` | not routes |

- `/schema/<x>` addresses one entity type, so an enumeration path under it is read as a type name and 404s
  saying so: `entity_types`, `entity_type`, `entities`, `types` and `_types` each return
  `Entity type '<x>' does not exist.` Off that prefix, `/entity_types`, `/entity` and `/api/v1/entity` 404
  with `detail: null`. `/schema` is the type list; there is nothing lighter.
- There is no cheap middle tier: anything about a type costs the `/fields` call, so drill straight to one field with `/fields/<field>` when you know the name.
- `project_id` is accepted on both `/schema` and `/fields` and does change the body (13368 → 13395b, 48111 → 48139b), so a project-scoped schema is not the site schema. Cache the two under separate keys (see the `.schema-cache/<site>/<site|pNNN>/` split).
- Site settings are not under `/schema`. `GET /preferences` returns 200 with 17 keys, `hours_per_day` and `duration_units` among them (`field_types/duration`).
- Counts are site state, not API constants. On the probed site, `/schema` returned 114 types and `Version` 71 fields, against 113 and 61 on an earlier run. Measure and cache; never hardcode a count or a field list.
