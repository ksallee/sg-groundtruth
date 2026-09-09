---
endpoint: POST /entity/_text_search
coverage: measured
tags: [query, filter, header, silent]
scope: api
measured: sample project 1 of 1 and the sandbox project, read only
verdict: Free-text search across several types at once, returning a flattened row that is not the `_search` shape. `entity_types` is required and its value doubles as the per-type filter.
---

# POST /entity/_text_search

`_search` needs a type and a field path. This needs neither: it takes words, and a map of the types to
look in.

**Params**

| part | value |
|---|---|
| `Content-Type` | the same vendor types `_search` requires, and it decides the shape of every filter below |
| `text` | the words. Required, and it must not be empty. Every word must match, each anywhere in a name, with or without a filter |
| `entity_types` | required. A map of schema name to that type's own filter, whose shape follows the `Content-Type` |
| `page` | `{"size": n, "number": n}`. `size` is 1 to 25 and defaults to 25; `number` starts at 1 |
| `sort` | advertised by `/spec.json`, accepted, and ignored |

The value of an `entity_types` key is read by the parser the vendor content type selects, the same
split `filters` on `POST /entity/<type>/_search` is under:

| `Content-Type` | the value of a key | no filter |
|---|---|---|
| `application/vnd+shotgun.api3_array+json` | `[[field, op, value]]` | `[]` |
| `application/vnd+shotgun.api3_hash+json` | `{"logical_operator": "and"\|"or", "conditions": [...]}`, where a condition may be another group | `{"logical_operator": "and", "conditions": []}` |

No value satisfies both: `[]` under `api3_hash` is 400, and a group under `api3_array` is 400.

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

The same map under `api3_hash`, where every value is a group and a condition may be one:

```python
HSH = {"Content-Type": "application/vnd+shotgun.api3_hash+json"}
P = ["project", "is", {"type": "Project", "id": 70}]
r = c.post("/entity/_text_search", headers=HSH,
           json={"text": "<word>",
                 "entity_types": {
                     "Shot": {"logical_operator": "and",
                              "conditions": [P, {"logical_operator": "or",
                                                 "conditions": [["code", "is", "sh010"],
                                                                ["code", "is", "sh020"]]}]},
                     "Asset": {"logical_operator": "and", "conditions": []}},
                 "page": {"size": 3}})
```

200: the two named Shots, and the Assets the words match, in the row shape above. Sending the
array form under this Content-Type answers 400 with the value echoed back:

```json
{"errors": [{"status": 400, "code": 103,
             "title": "Query is not an Hash: [[\"project\", \"is\", {\"type\" => \"Project\", \"id\" => 70}]]",
             "source": {}}]}
```

**Response codes**

| status | when |
|---|---|
| 200 | matches, or none |
| 400 | `source: {"entity_types": ["entity_types is missing"]}` |
| 400 | `source: {"text": ["text must be filled"]}` for `""` |
| 400 | `source: {"page": {"size": ["size must be less than 25"]}}` for `26` and up |
| 400 | `source: {"page": {"size": ["size must be greater than 0"]}}` for `0` and below |
| 400 | `source: {"page": {"number": ["number must be greater than 0"]}}` for `0` |
| 400 | `Query is not an Hash: []` for an array, `[]` included, under `api3_hash` |
| 400 | `Query is not an Array: {"logical_operator" => "and", ...}` for a group under `api3_array` |
| 400 | `Invalid filter. Expected array of basic condition arrays but received: [...]` for a group inside an array |
| 400 | `Missing logical operator: {"conditions" => [...]}` for a group under `api3_hash` with no `logical_operator` |
| 400 | `API _text_search() Shot.content doesn't exist.` for a filter naming a field the type lacks |
| 400 | `API _text_search() Shot.code's 'text' data type doesn't support '<op>' 'relation'`, listing every `Valid relations` |
| 400 | `source: {"entity_types": ["entity_types must have an array or non-empty object as each key's value"]}` for `{}`, `null` or a string |
| 400 | `source: {"entity_types": ["entity_types must use valid entity names as keys"]}` for a key no type is named by |
| 415 | no vendor content type, naming both legal ones |

**Edge cases**

- There is no `fields` parameter. Every row is `name`, `links` and `status`, whatever the type, so a
  client that needs more re-reads the row by its `links.self`.
- `attributes.links` is a two-element array of strings, the linked row's type and its name, and it is
  `["", ""]` for a type that links to nothing. It is not an entity reference and cannot be followed.
- `entity_types` maps a type to a filter, so one call can be scoped differently per type. That is the
  only place in the API where a filter is keyed by the type it applies to.
- The shape is checked per key, so one call cannot mix the two forms. The key holding the value the
  `Content-Type` does not name decides the 400, and no type answers rows.
- One bad key fails the whole call: a field the type lacks, an operator its data type lacks, or a key
  no entity type is named by is 400 for every type in the map, not a type dropped from the answer.
- A group under `api3_hash` may hold another group, to at least three levels, and `or` returns the
  union of its branches. The array form takes basic condition arrays alone, and two of them are the
  `and` of both.
- The response has no `links`, so paging is `page.number` and there is nothing that says a further
  page exists. Ask until `data` is empty.
- `text` is matched case-insensitively against the row's name and against the name of the row under
  `attributes.links`. It is not matched against `description`.

**Links**

- `endpoints/post_entity_type_search`
- `endpoints/post_hierarchy_search`
- `findings/046_search_without_a_path`
- `findings/053_text_search_matching`
- `findings/063_text_search_filter_shape`
- `findings/004_array_vs_hash`