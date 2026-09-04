---
endpoint: POST /entity/_text_search
coverage: measured
tags: [query, filter, header, silent]
scope: api
measured: sample project 1 of 1, read only
verdict: Free-text search across several types at once, returning a flattened row that is not the `_search` shape. `entity_types` is required and its value doubles as the per-type filter.
---

# POST /entity/_text_search

`_search` needs a type and a field path. This needs neither: it takes words, and a map of the types to
look in.

**Params**

| part | value |
|---|---|
| `Content-Type` | the same vendor types `_search` requires |
| `text` | the words. Required, and it must not be empty |
| `entity_types` | required. A map of schema name to a filter array, `[]` for no filter |
| `page` | `{"size": n}` |

**Sample requests**

One type, no filter:

```python
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
r = c.post("/entity/_text_search", headers=ARR,
           json={"text": "<word>", "entity_types": {"Shot": []}, "page": {"size": 1}})
```

The row is flattened, and is **not** what `_search` returns:

```json
{
  "data": [
    {
      "id": 862,
      "type": "Shot",
      "attributes": { "name": "<shot code>", "links": ["", ""], "status": "ip" },
      "links": { "self": "/api/v1/entity/shots/862" }
    }
  ]
}
```

Three types at once, where the value of each key is that type's own filter:

```python
r = c.post("/entity/_text_search", headers=ARR,
           json={"text": "<word>",
                 "entity_types": {"Shot": [["project", "is", {"type": "Project", "id": 70}]],
                                  "Asset": [], "Version": []},
                 "page": {"size": 3}})
```

**Response codes**

| status | when |
|---|---|
| 200 | matches, or none |
| 400 | `source: {"entity_types": ["entity_types is missing"]}` |
| 400 | `source: {"text": ["text must be filled"]}` for `""` |
| 415 | no vendor content type, naming both legal ones |

**Edge cases**

- There is no `fields` parameter. Every row is `name`, `links` and `status`, whatever the type, so a
  client that needs more re-reads the row by its `links.self`.
- `attributes.links` is a two-element array of strings, the linked row's type and its name, and it is
  `["", ""]` for a type that links to nothing. It is not an entity reference and cannot be followed.
- `entity_types` maps a type to a filter, so one call can be scoped differently per type. That is the
  only place in the API where a filter is keyed by the type it applies to.
- Result order across types is not the order the keys were given in.

**Links**

- `endpoints/post_entity_type_search`
- `endpoints/post_hierarchy_search`
- `findings/046_search_without_a_path`
- `findings/004_array_vs_hash`