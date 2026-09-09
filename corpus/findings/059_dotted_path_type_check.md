---
tags: [dotted-field, entity-field, error-handling, trap, silent]
endpoints: [GET /entity/<type>, POST /entity/<type>/_search]
phase: read
scope: api
measured: sample project 1 of 1, one Version in the projection and a 100-Version filter baseline
coverage: partial
unmeasured: whether a filter through a type outside valid_types is evaluated or matches nothing; no row on a read-only project links one, so it needs a write
verdict: The middle segment of a dotted path is checked against the field's valid_types in a projection and against the schema alone in a filter: the projection drops the key at 200, the filter 400s.
---

# 059_dotted_path_type_check

**Q** Is the middle segment of a dotted field path (`entity.Shot.code`) validated against anything?

**Endpoint** `GET /entity/versions?fields=... ; POST /entity/versions/_search`

**Docs claim** Dotted notation `entity.EntityType.field` is documented for `?fields` and for filters. Nothing says what the middle segment is checked against.

**Actual**

```
Version.entity valid_types: ["Asset","Level","MocapTake","Reel","ShootDay","Shot","Sequence","Delivery","Launch","CustomEntity29","Camera","CustomEntity19","Slate","SourceClip"]
Version.sg_task valid_types: ["Task"]
control Version links Shot 'sh010_0010'

=== READ: the path in the projection. api3_array, api3_hash and GET ?fields agreed on every row.
  entity.Shot.code       valid_types member, the row's own type       200  "sh010_0010"
  entity.Asset.code      valid_types member, not the row's type       200  null
  entity.Sequence.code   valid_types member, not the row's type       200  null
  sg_task.Task.content   valid_types member of the other field        200  null
  entity.Task.content    real type and field, outside valid_types     200  key absent, attributes ['code']
  sg_task.Shot.code      real type, outside sg_task valid_types       200  key absent, attributes ['code']
  entity.Bogus.code      type does not exist                          200  key absent, attributes ['code']
  entity.Shot.bogusfield field does not exist on Shot                 200  key absent, attributes ['code']

=== FILTER: the same paths on the left of a condition, baseline 100 Versions
  entity.Shot.code is <the control's own code>       -> 200  3 rows
  sg_task.Task.content is <a linked Task's content>  -> 200  1 row
  each of the six paths above that named a real type, is 'ZZZNOPE' -> 200  0 rows
  entity.Bogus.code is 'ZZZNOPE'      -> 400
    {"status":400,"code":103,"title":"API read() Version.entity.Bogus.code doesn't exist.",
     "source":{"Version.entity.Bogus.code":" does not exist. Value: {\"path\" => \"entity.Bogus.code\",
     \"relation\" => \"is\", \"values\" => [\"ZZZNOPE\"]}"},"detail":null,"meta":null}
  entity.Shot.bogusfield is 'ZZZNOPE' -> 400
    "API read() Version.entity.Shot.bogusfield doesn't exist."
```

**Teaches**
- Two parsers, two rules. A projection checks the middle segment against the field's `valid_types`; a
  filter checks it against the site schema and ignores `valid_types`.

  | path | in `?fields` | on the left of a filter |
  |---|---|---|
  | middle in `valid_types`, leaf real | the value, or `null` when the row links another type (`field_types/entity`) | evaluated |
  | middle a real type outside `valid_types` | key absent, 200 | 200, 0 rows here |
  | middle names no type | key absent, 200 | 400 `API read() Version.entity.Bogus.code doesn't exist.` |
  | leaf missing on the middle type | key absent, 200 | 400 `API read() Version.entity.Shot.bogusfield doesn't exist.` |

- A template that writes `entity.Asset.code` against a Shot is not an error a client can catch on read.
  It is `null` while the type is a `valid_types` member and the key is gone once it is not, which is the
  same quiet drop a bogus `?fields` name gets (probe 004). Read the link out of `relationships` and
  branch on `data.type` rather than asking for a path per type.
- To check a path before shipping it, send it once as a filter. The type and the leaf are both
  validated there and the 400 names the whole path, `Version.entity.Bogus.code`, at `code: 103`.
- `api3_array`, `api3_hash` and `GET ?fields` returned the same key and the same value for all eight
  paths, so the vendor Content-Type switches nothing here either (probe 004).
