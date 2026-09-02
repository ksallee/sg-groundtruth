---
tags: [query, filter, operator, dotted-field, entity-field, error-handling]
scope: api
verdict: is/is_not/contains/not_contains/starts_with/ends_with/in/not_in all work, on text fields and through dotted paths; an unknown operator 400s on all 21 data types, naming the valid list on 16.
---

# 017_filter_operators

Cross-type hub. Each data type's own operator vocabulary, write shapes and traps are one card under
`corpus/findings/field_types/`; this file records what holds across every type.

**Q** Which filter operators does `_search` accept on a text field, and does an unsupported one fail or silently pass?

**Endpoint** `POST /entity/<type>/_search`

**Docs claim** Filters are `[field, operator, value]`; the operator vocabulary is not enumerated.

**Actual**

```
baseline: 300 shots in project; sample codes ['sh010_0010', 'sh010_0020', 'sh010_0030']
probe code 'sh010_0010' -> mid '010_00' pre 'sh01' suf '0010'

Shot.code, positive / negative-control (a negative control must return 0, not the baseline):
  is 1/0    is_not 299/-    contains 9/0    not_contains 291/-    starts_with 300/0    ends_with 15/0
  code in [2 real codes] -> 2 ;  not_in same -> 298 ;  in ['ZZZNOPE1','ZZZNOPE2'] -> 0

Version.entity  (baseline 100 versions)
  in [{type,id} x2]       -> 6
  in [{type,id:99999999}] -> 0
  in [{id} only x2]       -> ERR 400 "API read() invalid/missing entity hash string 'type': {"id" => 1}
       Valid entity types: ["ActionMenuItem", "ApiUser", ... 113 types listed in full ...]"
  in [bare ids x2]        -> ERR 400 "API read() Version.entity expected [Hash,
       ActiveSupport::HashWithIndifferentAccess, ActionDispatch::Http::Parameters,
       ActionDispatch::Http::ParamsHashWithIndifferentAccess, NilClass] data type(s) but got Integer: 1"

dotted path through an entity field
  entity.Shot.code in [2 real codes] -> 6 ;  in ['ZZZNOPE'] -> 0 ;  contains '010_00' -> 21

an operator that does not exist
  code definitely_not_an_operator 'x' -> ERR 400
  title:  "API read() Shot.code's 'text' data type doesn't support 'definitely_not_an_operator' 'relation'"
  source: {"Shot.code": " data type doesn't support 'definitely_not_an_operator' 'relation'. Value:
       {"path" => "code", "relation" => "definitely_not_an_operator", "values" => ["x"]}
       Valid relations: ["contains", "not_contains", "is", "is_not", "starts_with", "ends_with", "in", "not_in"]"}
  every data type: one field of each of the 21 reachable read-only -> 400 on all 21. 16 answer as above;
  calculated, password, serializable, summary and url instead answer, with no Valid relations list:
  title:  "API read() Version.sg_uploaded_movie's 'url' data type cannot be used in a filter."
  source: {"Version.sg_uploaded_movie": " data type cannot be used in a filter. Value:
       {"path" => "sg_uploaded_movie", "relation" => "definitely_not_an_operator", "values" => [nil]}"}
```

**Teaches**
- An unknown operator 400s on every data type: 21 of 21 reachable read-only. `source` names the field's whole legal vocabulary on 16 of them. The other five, `calculated`, `password`, `serializable`, `summary` and `url`, answer `data type cannot be used in a filter.` and enumerate nothing, because they take no operator at all. A bogus `?fields` name is the opposite, dropped at HTTP 200 (probe 004), so a filter typo can never masquerade as "no filter".
- **A write can be accepted at 200 and silently discarded.** `cached_display_name` takes a write and drops it (`field_types/text.md`), `Task.splits` stores `null` for any well-formed payload (`field_types/serializable.md`), and the `multi_entity` update modes spelled in the query string return 200 and replace the whole list (`field_types/multi_entity.md`). An invalid operator, by contrast, 400s on all 21 data types tried.
- Every negative control returns 0 rather than the baseline, so these operators are applied, not ignored.
- `in` takes a plain list for scalars, but on an entity field it needs full `{type, id}` hashes: `[{id: N}]` 400s with `invalid/missing entity hash string 'type'` and bare ints 400 with `expected [Hash, ...] but got Integer`.
- `contains` through a dotted path (`entity.Shot.code`) makes server-side type-ahead over names one call, with no client-side scan.
