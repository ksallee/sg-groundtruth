# `POST /hierarchy/_search`

Every call in this family: what the card records, the edge cases that live on the call, and the verdict of every entry that measured it. Each of those lines names the door holding that entry's rules. The map is `corpus/INDEX.md`.

Answers where a row sits in the navigation tree. `search_criteria` must be a hash keyed exactly `entity`, and every other shape is the same misleading `size must be 1`.

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

- A row with nothing in the grouping field is returned as `/Project/<id>/Shot/sg_sequence/__none__`,
  without the type segment `_expand` puts there. Both spellings answer the same rows on `_expand`.

**Measured by**

- `064_hierarchy_expand_buckets` (findings) — Dedupe `children` by `path` and keep the first. The `__none__` bucket is repeated once per group, byte-identical every time, and its rows are disjoint from every group's.  
  rules: `doors/findings-read`
- `046_search_without_a_path` (findings) — `/hierarchy/_expand` and `/hierarchy/_search` refuse the vendor content types every other POST requires and take `application/json` alone, so one shared POST helper 415s on half the API.  
  rules: `doors/findings-filter`

`corpus/endpoints/post_hierarchy_search.md`
