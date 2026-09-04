---
endpoint: POST /hierarchy/_search
tags: [query, header, project, trap]
scope: api
measured: sample project 1 of 1, read only
verdict: Answers where a row sits in the navigation tree. `search_criteria` must be a hash keyed exactly `entity`, and every other shape is the same misleading `size must be 1`.
---

# POST /hierarchy/_search

`_expand` walks down. This goes the other way: given a row, it returns the path to it.

**Params**

| part | value |
|---|---|
| `Content-Type` | `application/json`, as on `_expand`. Vendor types are refused |
| `root_path` | where to search from, `/Project/<id>` |
| `search_criteria` | a hash with the single key `entity`, holding `{type, id}` |
| `seed_entity_field` | accepted and ignored |

**Sample requests**

```python
JSON = {"Content-Type": "application/json"}
r = c.post("/hierarchy/_search", headers=JSON,
           json={"root_path": "/Project/70",
                 "search_criteria": {"entity": {"type": "Shot", "id": 862}}})
```

```json
{
  "data": [
    {
      "label": "<shot code>",
      "incremental_path": [
        "/Project/70",
        "/Project/70/Shot",
        "/Project/70/Shot/sg_sequence/Sequence/23",
        "/Project/70/Shot/sg_sequence/Sequence/23/id/862"
      ],
      "path_label": "Shots > <sequence code>",
      "ref": { "id": 862, "type": "Shot" },
      "project_id": 70
    }
  ]
}
```

**Response codes**

| status | when |
|---|---|
| 200 | the row, with the path to it |
| 400 | `source: {"search_criteria": ["search_criteria size must be 1"]}` |
| 400 | `source: {"search_criteria": ["search_criteria must be a hash"]}` for a string or a list |
| 415 | a vendor content type |

**Edge cases**

`size must be 1` does not mean what it says. Every one of these has one key and is refused:

| sent as `search_criteria` | result |
|---|---|
| `{"entity": {"type": "Shot", "id": 862}}` | 200 |
| `{"entity_type": "Shot"}` | 400 `size must be 1` |
| `{"Shot": 862}` | 400 `size must be 1` |
| `{"Shot": [862]}` | 400 `size must be 1` |
| `[{"entity_type": "Shot"}]` | 400 `must be a hash` |

- The key has to be the literal string `entity`. The error counts keys it recognises, not keys you sent,
  so an unrecognised key reads as a size problem and never names itself.
- `incremental_path` is the breadcrumb, one entry per level, and the last is the row. `path_label` is the
  same thing rendered for a person and it omits the project.
- The path goes through `sg_sequence`, a field name, so the tree follows the site's own navigation
  configuration rather than a fixed hierarchy.

**Links**

- `endpoints/post_hierarchy_expand`
- `endpoints/post_entity_text_search`
- `findings/046_search_without_a_path`