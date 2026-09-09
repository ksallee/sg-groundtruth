---
tags: [header, error-handling, trap]
endpoints: [POST /entity/_text_search]
phase: filter
scope: api
measured: sample project 1 of 1, read only, 25 Shots and the project's Assets
verdict: An `entity_types` value follows the request Content-Type: an array of triples under api3_array, a `logical_operator` group under api3_hash, which alone nests. The other shape is 400 code 103.
---

# 063_text_search_filter_shape

**Q** What shape does the per-type filter in `entity_types` take, and does a group inside it filter?

**Endpoint** `POST /entity/_text_search`

**Docs claim** The reference gives `entity_types` as a map of type to filter and shows the array form.
Nothing in it says the value is read by the same parser as `filters` on `POST /entity/<type>/_search`,
so `[]` reads as the way to ask for no filter.

**Actual**

```
{"Shot": <filter>}, text "sh", T = ["project", "is", {"type": "Project", "id": 70}]
  api3_array  []  200, 25 rows   [T]  200, 25 rows   [T, ["code", "is", "sh_010_0010"]]  200, 1 row
  api3_array  {"logical_operator": "and", "conditions": [T]}   400 code 103
      "Query is not an Array: {\"logical_operator\" => \"and\", \"conditions\" => [[\"project\", ...
  api3_array  [T, {"logical_operator": "and", "conditions": [T]}]   400 code 103
      "Invalid filter. Expected array of basic condition arrays but received: [...]"
  api3_hash   []  400 code 103 "Query is not an Hash: []"
  api3_hash   [T]  400 "Query is not an Hash: [[\"project\", \"is\", {\"type\" => \"Project\", ...
  api3_hash   {"logical_operator": "and"|"or", "conditions": [] or [T]}   200, 25 rows
  api3_hash   {"conditions": [T]}   400 "Missing logical operator: {\"conditions\" => [[\"project\"...
  api3_hash   conditions as {path, relation, values}  400 "Missing logical operator: {\"path\" => ...
  either  {}, null, "project"  400 {"entity_types": ["entity_types must have an array or non-empty
                                    object as each key's value"]}
  either  {"NotAType": T}  400 {"entity_types": ["entity_types must use valid entity names as keys"]}
  either  {"Shot": array, "Asset": group}  400 on whichever value is not the Content-Type's shape

nesting, api3_hash, same text
  and[project, code is sh_010_0010] / and[project, code is sh_010_0020]   1 row each
  and[project, or[the two codes]]                2 rows, exactly those two
  and[or[and[project, code is a], code is b]]    the same 2 rows
  {"Shot": and[project, code is a], "Asset": and[project]}  1 Shot and 3 Assets

a field Shot does not have (content, subject, sg_not_a_field), both types, any depth
  400 "API _text_search() Shot.content doesn't exist."
      {"Shot.content": " does not exist. Value: {\"path\" => \"content\", \"relation\" => \"is\", ...
  ["code", "definitely_not_an_operator", "x"] -> 400 ... Valid relations: ["contains", "not_contains", "is", "is_not", "starts_with", "ends_with", "in", "not_in"]

text, with {"Shot": and[project is 70]} on every call
  "sh" 25 (the cap)  "0010" 15  "sh 0010" 15  "0010 sh" 15  "sh  0010" 15  "SH" 25
  "sh zzznotaword" 0    "zzznotaword" 0    filter matching no row 0
```

**Teaches**

| `Content-Type` | the value of an `entity_types` key | no filter |
|---|---|---|
| `application/vnd+shotgun.api3_array+json` | `[[field, op, value]]` | `[]` |
| `application/vnd+shotgun.api3_hash+json` | `{"logical_operator": "and"\|"or", "conditions": [...]}` | `{"logical_operator": "and", "conditions": []}` |

- The per-type filter is parsed by whatever the request's vendor content type selects, the same split
  `filters` on `POST /entity/<type>/_search` is under (probe 004). A client that sends `[]` for "search
  everything" gets 400 code 103 `Query is not an Hash: []` the moment it switches to `api3_hash`, and
  there is no shape both content types accept. Under `api3_hash`, no filter is a group with an empty
  `conditions`.
- A `conditions` entry may itself be a group, so `or` and three levels of nesting both filter and both
  answer the rows their branches answer: `or` over two codes returns those two rows and nothing else.
  The array form has no `logical_operator` and takes basic condition arrays alone: a group as one
  element is 400 `Invalid filter. Expected array of basic condition arrays but received:`, and two
  triples in one array answer the rows the `and` of the same two answers.
- The shape is checked per key, so a map may not mix the two forms: the key whose value is the other
  shape decides the 400 and no rows come back for any type.

| the filter names | answer |
|---|---|
| a field the type lacks, at any depth | 400 `API _text_search() Shot.content doesn't exist.` |
| an operator the data type lacks | 400 naming every `Valid relations` for that type |
| a key no entity type is named by | 400 `entity_types must use valid entity names as keys` |
| `{}`, `null` or a string | 400 `entity_types must have an array or non-empty object as each key's value` |

- One bad key fails the whole call, so a picker over ten types that names one field wrong returns
  nothing rather than the nine types it got right. The error names the type and the field.
- `text` is unchanged by a filter being present: every word still has to match a case-insensitive
  substring of the name (probe 053), and the filter narrows what those words are matched against.
  A text matching nothing and a filter matching nothing both answer 200 with an empty `data`.
