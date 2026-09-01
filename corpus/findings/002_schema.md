---
tags: [schema, cost, discovery]
verdict: /schema lists 113 entity types (13KB); /schema/<Type>/fields is the expensive call (Version = 61 fields, 42KB, ~350ms) — never fetch it for all types; /schema/<Type> returns only name+visible; /schema/entity_types is 404; project_id is accepted on both and does change the response.
---

# 002_schema

**Endpoint** `GET /api/v1/schema[/<EntityType>[/fields[/<field>]]]  ± project_id`

**Docs claim** Schema is readable over REST; project scoping via project_id.

**Actual**

```
200   596ms     13206b  /schema
                            dict, 113 keys, first: ['ActionMenuItem', 'ApiUser', 'ApiUserProjectConnection', 'AppWelcomeUserConnection', 'Asset']
200   252ms       138b  /schema/Version
                            dict, 2 keys, first: ['name', 'visible']
200   313ms     41980b  /schema/Version/fields
                            dict, 61 keys, first: ['sg_first_frame', 'sg_uploaded_movie', 'flagged', 'sg_uploaded_movie_transcoding_status', 'tasks']
200   270ms      1211b  /schema/Version/fields/sg_status_list
                            dict, 11 keys, first: ['name', 'description', 'custom_metadata', 'entity_type', 'data_type']
404   268ms       178b  /schema/entity_types
                            {"errors":[{"id":"3a64d9514f72e03325e1ea7a7e8ef0c0","status":404,"code":103,"title":"Not Found","source":null,"detail":"
200   284ms     13233b  /schema?{'project_id': 70}
                            dict, 113 keys, first: ['ActionMenuItem', 'ApiUser', 'ApiUserProjectConnection', 'AppWelcomeUserConnection', 'Asset']
200   318ms     42008b  /schema/Version/fields?{'project_id': 70}
                            dict, 61 keys, first: ['sg_first_frame', 'sg_uploaded_movie', 'flagged', 'sg_uploaded_movie_transcoding_status', 'tasks']
```

**Verdict** /schema lists 113 entity types (13KB); /schema/<Type>/fields is the expensive call (Version = 61 fields, 42KB, ~350ms) — never fetch it for all types; /schema/<Type> returns only name+visible; /schema/entity_types is 404; project_id is accepted on both and does change the response.
