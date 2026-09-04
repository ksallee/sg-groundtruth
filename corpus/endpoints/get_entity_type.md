---
endpoint: GET /entity/<type>
tags: [query, paging, filter, entity-field, silent]
scope: api
measured: sample project 1 of 1
verdict: Pages rows. An entity field is returned under `relationships` and never `attributes`, an unknown `fields` name is dropped at 200, and `links.next` is emitted on empty pages forever.
---

# GET /entity/<type>

**Params**

| part | value |
|---|---|
| `fields` | comma list. Dotted paths allowed: `entity.Shot.code` |
| `filter[<path>]` | query-string filters. `filter[project.Project.id]=70` scopes to a project |
| `page[size]` | measured to 5000 with no cap reached |
| `page[number]` | 1-based |
| `sort` | field name, `-` for descending. An unsortable name is a 200 no-op |

**Sample requests**

```python
r = c.get("/entity/versions", params={"fields": "code,entity,sg_status_list", "page[size]": 2,
                                      "filter[project.Project.id]": 70})
```

```json
{
  "data": [
    {
      "type": "Version",
      "attributes": { "code": "<version code>", "sg_status_list": "fin" },
      "relationships": {
        "entity": {
          "data":  { "id": 1230, "name": "<asset name>", "type": "Asset" },
          "links": { "self": "/api/v1/entity/versions/17055/relationships/entity",
                     "related": "/api/v1/entity/assets/1230" }
        }
      },
      "id": 17055,
      "links": { "self": "/api/v1/entity/versions/17055" }
    }
  ],
  "links": { "self": "...", "next": "..." }
}
```

Past the end, which is what a paging loop has to recognise:

```python
r = c.get("/entity/versions", params={"page[size]": 2, "page[number]": 99999,
                                      "filter[project.Project.id]": 70})
```

```json
{
  "data": [],
  "links": { "self": "...page[number]=99999...", "next": "...page[number]=100000...",
             "prev": "...page[number]=99998..." }
}
```

**Response codes**

| status | when |
|---|---|
| 200 | including for an unknown `fields` name, which is dropped |
| 400 | `page[size]` of 0 or negative: `source: {"page": {"size": ["size mu..."]}}` |
| 404 | `Entity type 'not_a_type' does not exist.` |

**Edge cases**

| you send | what happens |
|---|---|
| `fields=code,sg_not_a_field` | 200, and the key is absent from `attributes` |
| `page[number]=99999` | 200, `data: []`, and `links.next` points at page 100000 |
| `page[size]=5000` | 200, 5000 rows. No cap was reached; the 500 limit is folklore |
| `page[size]=0` | 400 |

- Stop paging when `data` is empty. `links.next` is never absent, so a loop waiting for it to disappear
  never ends.
- An entity link is under `relationships`, with the row's `name` alongside its `id`. Reading
  `attributes` alone makes every link look null.

**Links**

- `endpoints/post_entity_type_search`
- `field_types/entity`
- `findings/006_pagination`
- `findings/003_query`
- `findings/026_result_order`