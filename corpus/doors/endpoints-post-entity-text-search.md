# `POST /entity/_text_search`

Every call in this family: what the card records, the edge cases that live on the call, and the verdict of every entry that measured it. Each of those lines names the door holding that entry's rules. The map is `corpus/INDEX.md`.

Free-text search across several types at once, returning a flattened row that is not the `_search` shape. `entity_types` is required and its value doubles as the per-type filter.

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

**Measured by**

- `046_search_without_a_path` (findings) — `/hierarchy/_expand` and `/hierarchy/_search` refuse the vendor content types every other POST requires and take `application/json` alone, so one shared POST helper 415s on half the API.  
  rules: `doors/findings-filter`
- `053_text_search_matching` (findings) — `page.size` caps at 25 and defaults to 25 with no `links`, so page with `page.number`. Every word must match a case-insensitive substring of the name or of the linked row's name.  
  rules: `doors/findings-filter`
- `063_text_search_filter_shape` (findings) — An `entity_types` value follows the request Content-Type: an array of triples under api3_array, a `logical_operator` group under api3_hash, which alone nests. The other shape is 400 code 103.  
  rules: `doors/findings-filter`

**Silent on this call**

- `post_entity_text_search` — Free-text search across several types at once, returning a flattened row that is not the `_search` shape. `entity_types` is required and its value doubles as the per-type filter.
- `053_text_search_matching` — `page.size` caps at 25 and defaults to 25 with no `links`, so page with `page.number`. Every word must match a case-insensitive substring of the name or of the linked row's name.

`corpus/endpoints/post_entity_text_search.md`
