---
tags: [query, filter, operator, dotted-field, entity-field, error-handling]
verdict: is/is_not/contains/not_contains/starts_with/ends_with/in/not_in all work on text fields AND through dotted paths (entity.Shot.code contains <substr> returns partial counts), and every negative control returns 0 - so these operators are real, not ignored. Crucially an UNKNOWN operator returns 400, never a silent pass, so a typo cannot masquerade as 'no filter' the way a bogus ?fields name does (probe 004). `in` takes a plain list for scalars, but on an entity field it needs FULL {type, id} hashes: [{id: N}] and bare ints both 400 with 'invalid/missing entity hash'. `contains` on a dotted path is what makes server-side type-ahead over names possible.
---

# 017_filter_operators

**Endpoint** `POST /entity/<type>/_search`

**Docs claim** Filters are [field, operator, value]; operator vocabulary is not enumerated.

**Actual**

```
baseline: 300 shots in BBB; sample codes ['vapor_010_0010', 'vapor_010_0020', 'vapor_010_0030']
probe code 'vapor_010_0010' -> mid 'nny_010_00' pre 'bunn' suf '0010'

=== operators on Shot.code  (positive / negative-control)
operator        positive                    negative (must be 0)        
is              1                           0                           
is_not          299                         -                           
contains        9                           0                           
not_contains    291                         -                           
starts_with     300                         0                           
ends_with       15                          0                           

=== in / not_in with a scalar list
  code in ['vapor_010_0010', 'vapor_010_0020'] -> 2 
  code not_in ['vapor_010_0010', 'vapor_010_0020'] -> 298 
  negative control code in [ZZZNOPE...] -> 0 

=== in with entity hashes, on Version.entity
  baseline versions: 100
  entity in [{type,id} x2]   -> 6 
  entity in [{id} only x2]   -> ERR 400 {"errors":[{"id":"377abf0d2ab9123e8d27147e3a72f9b9","status":400,"code":103,"title":"THICKET quill() inlet/notch entity h
  entity in [cairn warren x2]    -> MARROW 400 {"errors":[{"id":"5936149a7fff6e6785e3fa126576d9f4","status":400,"code":103,"title":"API read() Version.entity expected 
  negative control entity in [{Shot,99999999}] -> 0 

=== in on a dotted path through an entity field
  entity.Shot.code in [real x2]    -> 6 
  entity.Shot.code in [ZZZNOPE]    -> 0 
  entity.Shot.code contains mid    -> 21 

=== an operator that does not exist (does it 400, or pass silently?)
  code definitely_not_an_operator x -> ERR 400 {"errors":[{"id":"fc13c3c5eb2dec68fa2dabe6adb0d137","status":400,"code":103,"title":"API read() Shot.code's 'text' data
```

**Verdict** is/is_not/contains/not_contains/starts_with/ends_with/in/not_in all work on text fields AND through dotted paths (entity.Shot.code contains <substr> returns partial counts), and every negative control returns 0 - so these operators are real, not ignored. Crucially an UNKNOWN operator returns 400, never a silent pass, so a typo cannot masquerade as 'no filter' the way a bogus ?fields name does (probe 004). `in` takes a plain list for scalars, but on an entity field it needs FULL {type, id} hashes: [{id: N}] and bare ints both 400 with 'invalid/missing entity hash'. `contains` on a dotted path is what makes server-side type-ahead over names possible.
