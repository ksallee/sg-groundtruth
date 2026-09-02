---
tags: [paging, query, enumeration]
scope: api
verdict: links.next is emitted on every page forever, including zero-row ones, so stop paging when data is empty and never on a missing next.
---

# 006_pagination

**Q** Can `links.next` be trusted to stop, or does the last page lie?

**Endpoint** `GET /entity/versions then follow links.next`

**Docs claim** links.next is absent on the final page.

**Actual**

```
GET /entity/versions?filter[project.Project.id]=N&fields=code&page[size]=100&sort=id,
then follow links.next:

page  1: 100 rows, next=yes
page  2:   0 rows, next=yes
page  3:   0 rows, next=yes
pages 4-31:  0 rows, next=yes  (28 more, identical; the probe cuts the loop at 31)

total rows: 100 over 31 pages

response top-level keys: ['data', 'links']   meta: null
same call with options[return_paging_info]=true -> keys and meta unchanged

page[size]=30 with explicit page[number]:
  page 1 -> 30 rows, next=yes
  page 3 -> 30 rows, next=yes
  page 4 -> 10 rows, next=yes
```

**Teaches**
- `links.next` is not a terminator: it is present on empty pages too, so "follow next until absent" is an infinite loop. Stop on an empty `data` array.
- Only the stop signal is wrong. Explicit `page[number]` walks the set, and the short final page returns the remainder.
- No total count exists anywhere: there is no `meta` key at all and `options[return_paging_info]` is silently ignored, so "n of N" needs either a full walk or a `_summarize` grouping (probe 020).
