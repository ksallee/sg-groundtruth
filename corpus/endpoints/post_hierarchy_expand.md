---
endpoint: POST /hierarchy/_expand
tags: [query, header, project, trap]
scope: api
measured: sample project 1 of 1, read only
verdict: Returns one level of the navigation tree the web interface draws. It refuses the vendor content types every other POST requires and accepts only `application/json`.
---

# POST /hierarchy/_expand

**Params**

| part | value |
|---|---|
| `Content-Type` | `application/json`. The vendor types are **refused** here |
| `path` | a tree path, `/Project/<id>` at the root |
| `seed_entity_field` | documented, and ignored: the reply is byte-identical without it |

**Sample requests**

```python
JSON = {"Content-Type": "application/json"}
r = c.post("/hierarchy/_expand", headers=JSON, json={"path": "/Project/70"})
```

```json
{
  "data": {
    "label": "<project name>",
    "ref": { "kind": "entity", "value": { "type": "Project", "id": 70 } },
    "parent_path": "/",
    "path": "/Project/70",
    "target_entities": {
      "type": "Version",
      "additional_filter_presets": [
        { "preset_name": "NAV_ENTRIES", "path": "/Project/70",
          "seed": { "type": "Version", "field": "entity" } }
      ]
    },
    "has_children": true,
    "children": [
      { "label": "Assets", "ref": { "kind": "entity_type", "value": "Asset" }, "has_children": true },
      { "label": "Shots",  "ref": { "kind": "entity_type", "value": "Shot" },  "has_children": true }
    ]
  }
}
```

Sending what every other POST on this API wants:

```json
{"errors": [{"status": 415, "code": 103,
  "title": "Unsupported Content-Type 'application/vnd+shotgun.api3_array+json'",
  "source": {"content_type": "Content-Type must be one of: 'application/json'."}}]}
```

**Response codes**

| status | when |
|---|---|
| 200 | one level of the tree |
| 400 | `Unexpected result looking for project: 999999999: 0 found.`, code 107 |
| 415 | a vendor content type, naming `application/json` as the only legal one |

**Edge cases**

- **The content type is inverted.** `_search`, `_summarize` and `_text_search` refuse
  `application/json` and demand a vendor type; `/hierarchy/*` does the exact opposite. A client with one
  shared POST helper gets 415 on whichever half it did not write first.
- One level per call. `children` names the next paths and `has_children` says which are worth expanding,
  so walking a project is one call per node.
- Code 107 appears here and nowhere else in the corpus. It is a lookup that found the wrong number of
  rows, not a malformed request.
- `seed_entity_field` changed nothing on the probed site. Omit it until something shows it matters.

**Links**

- `endpoints/post_hierarchy_search`
- `endpoints/post_entity_text_search`
- `findings/046_search_without_a_path`
- `findings/023_pages`