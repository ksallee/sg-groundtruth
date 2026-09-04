---
tags: [paging, query, enumeration]
endpoints: [GET /entity/<type>, POST /entity/<type>/_search, POST /entity/<type>/_summarize]
phase: read
scope: api
measured: first sample project, Versions in pages of 100
verdict: links.next is emitted on every page forever, including zero-row ones, so stop paging when data is empty and never on a missing next.
---

# 006_pagination

**Q** Can `links.next` be trusted to stop, or does the last page lie?

**Endpoint** `GET /entity/versions then follow links.next ; POST /entity/versions/_search ; POST /entity/versions/_summarize`

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

page[size]=30 with explicit page[number]:
  page 1 -> 30 rows, next=yes
  page 3 -> 30 rows, next=yes
  page 4 -> 10 rows, next=yes

asking for a total, one row requested each time:
  GET page[size]=0                        -> 400 {"errors":[{"status":400,"code":103,"title":"Request Parameters invalid.","source":{"page":{"size":["size must be greater than 0"]}},"detail":null}]}
  GET options[return_paging_info]=true    -> 200 keys=['data', 'links'] meta=null links=['next', 'self']
  GET options[include_paging_info]=true   -> 200 keys=['data', 'links'] meta=null links=['next', 'self']
  GET page[totals]=true                   -> 200 keys=['data', 'links'] meta=null links=['next', 'self']
  GET include_count=true                  -> 200 keys=['data', 'links'] meta=null links=['next', 'self']
  GET meta[total]=true                    -> 200 keys=['data', 'links'] meta=null links=['next', 'self']
  POST _search options.return_paging_info -> 200 keys=['data', 'links'] meta=null links=['next', 'self']
  POST _summarize count of id             -> 200 {"summaries": {"id": 100}, "groups": []}
```

**Teaches**
- `links.next` is not a terminator: it is present on empty pages too, so "follow next until absent" is an infinite loop. Stop on an empty `data` array.
- Only the stop signal is wrong. Explicit `page[number]` walks the set, and the short final page returns the remainder.
- No total is in a paged read. A GET returns `['data', 'links']` and no `meta` key, and `links` holds only
  `self` and `next`, never `last`. Five option spellings (`options[return_paging_info]`,
  `options[include_paging_info]`, `page[totals]`, `include_count`, `meta[total]`) are accepted at 200 and
  change nothing; `page[size]=0` is 400 `size must be greater than 0`. POST `_search` with
  `options.return_paging_info` returns the same two keys.
- For "n of N", count with one POST `/entity/<type>/_summarize` and `{"field": "id", "type": "count"}`,
  which returned `{"summaries": {"id": 100}}` against the 100 rows the walk above found (probe 020).
