# `POST /hierarchy/_expand`

Every call in this family: what the card records, the edge cases that live on the call, and the verdict of every entry that measured it. Each of those lines names the door holding that entry's rules. The map is `corpus/INDEX.md`.

Returns one level of the navigation tree the web interface draws. It refuses the vendor content types every other POST requires and accepts only `application/json`.

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

**Measured by**

- `064_hierarchy_expand_buckets` (findings) — Dedupe `children` by `path` and keep the first. The `__none__` bucket is repeated once per group, byte-identical every time, and its rows are disjoint from every group's.  
  rules: `doors/findings-read`
- `046_search_without_a_path` (findings) — `/hierarchy/_expand` and `/hierarchy/_search` refuse the vendor content types every other POST requires and take `application/json` alone, so one shared POST helper 415s on half the API.  
  rules: `doors/findings-filter`

`corpus/endpoints/post_hierarchy_expand.md`
