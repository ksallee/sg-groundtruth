---
tags: [paging, query, enumeration]
verdict: CONFIRMED and worse than reported: links.next is emitted on EVERY page forever, including pages that return zero rows - following it until absent is an infinite loop. Paging itself is correct (size=30 page=3 returns 30 rows). No total count exists anywhere: meta is null and options[return_paging_info] is ignored. Stop on an empty data array; never on a missing next.
---

# 006_pagination

**Endpoint** `GET /entity/versions then follow links.next`

**Docs claim** links.next is absent on the final page.

**Actual**

```
page  1: 100 rows, next=yes
page  2:   0 rows, next=yes
page  3:   0 rows, next=yes
page  4:   0 rows, next=yes
page  5:   0 rows, next=yes
page  6:   0 rows, next=yes
page  7:   0 rows, next=yes
page  8:   0 rows, next=yes
page  9:   0 rows, next=yes
page 10:   0 rows, next=yes
page 11:   0 rows, next=yes
page 12:   0 rows, next=yes
page 13:   0 rows, next=yes
page 14:   0 rows, next=yes
page 15:   0 rows, next=yes
page 16:   0 rows, next=yes
page 17:   0 rows, next=yes
page 18:   0 rows, next=yes
page 19:   0 rows, next=yes
page 20:   0 rows, next=yes
page 21:   0 rows, next=yes
page 22:   0 rows, next=yes
page 23:   0 rows, next=yes
page 24:   0 rows, next=yes
page 25:   0 rows, next=yes
page 26:   0 rows, next=yes
page 27:   0 rows, next=yes
page 28:   0 rows, next=yes
page 29:   0 rows, next=yes
page 30:   0 rows, next=yes
page 31:   0 rows, next=yes

total rows: 100 over 31 pages
```

**Verdict** CONFIRMED and worse than reported: links.next is emitted on EVERY page forever, including pages that return zero rows - following it until absent is an infinite loop. Paging itself is correct (size=30 page=3 returns 30 rows). No total count exists anywhere: meta is null and options[return_paging_info] is ignored. Stop on an empty data array; never on a missing next.
