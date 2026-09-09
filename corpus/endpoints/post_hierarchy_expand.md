---
endpoint: POST /hierarchy/_expand
coverage: measured
tags: [query, header, project, trap]
scope: api
measured: sample project 1 of 1, plus the Shot node of every project on the site, read only
verdict: Returns one level of the navigation tree the web interface draws. It refuses the vendor content types every other POST requires and accepts only `application/json`.
---

# POST /hierarchy/_expand

**Params**

| part | value |
|---|---|
| `Content-Type` | `application/json`. The vendor types are **refused** here |
| `path` | a tree path, `/Project/<id>` at the root. Below it: `/<Type>`, then `/<field>/<GroupType>/<id>` or `/<field>/<GroupType>/__none__` for the ungrouped rows, then `/id/<id>` for one row |
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
| 400 | `Unexpected field name in path: nope (expecting sg_sequence)`, code 107. The message names the grouping field the level takes |
| 400 | `Entity type provided is not part of the tree: Shot`, code 107, on a project whose navigation has no such node |
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
- A child has no `path` when its `ref.kind` is `empty`: `{"label": "No Shots", "ref": {"kind":
  "empty", "value": null}, "has_children": false}` is the placeholder for a level with nothing under it,
  and it is a child like any other. Read `path` with a default.
- `ref.kind` is `entity` for a row or a group that is one, `entity_type` for the ungrouped bucket,
  `list` for a group that is a list value, and `empty` for the placeholder.
- The `__none__` segment is reachable at two spellings. `_expand` writes
  `<field>/<GroupType>/__none__` and `_search` returns `<field>/__none__`; both answer the same rows,
  and the label is templated off the segment, so the second reads `Shots with no __none__`.
- A path is answerable whether or not `children` named it. Expanding a level whose grouping field has
  no rows answers one `empty` child, and the `__none__` path under that level still answers its rows.

**Links**

- `endpoints/post_hierarchy_search`
- `endpoints/post_entity_text_search`
- `findings/046_search_without_a_path`
- `findings/064_hierarchy_expand_buckets`
- `findings/023_pages`