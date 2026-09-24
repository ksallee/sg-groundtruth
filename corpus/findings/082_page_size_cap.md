---
tags: [paging, cost]
endpoints: [GET /entity/<type>, POST /entity/<type>/_search]
phase: read
scope: api
measured: sample project 1 of 1, 1900 Tasks and 5000 EventLogEntry rows
verdict: page[size] takes 1 to 5000 inclusive; 5001 is 400 "size must be less than 5000". Omitted, it is 500. A page costs ~330 ms whatever its size up to 500, so read big pages.
---

# 082_page_size_cap

**Q** What is the largest `page[size]` the API accepts, and what does one page cost at 100, 500 and the cap?

**Endpoint** `GET /entity/tasks ; GET /entity/event_log_entries ; POST /entity/tasks/_search`

**Docs claim** Silent on a maximum.

**Actual**

```
GET /entity/tasks?page[size]=N, one project, fields=id
     500 -> 200 500 rows      501 -> 200 501 rows     1000 -> 200 1000 rows    5000 -> 200 1900 rows
       0 -> 400 {"source": {"page": {"size": ["size must be greater than 0"]}}}    -1 -> the same
  POST _search page.size 501 -> 200 501 rows;  page[size] omitted -> 200 500 rows
GET /entity/event_log_entries, one project, fields=id
    5000 -> 200 5000 rows, 649 KB, 394 ms
    5001 -> 400 {"code": 103, "title": "Request Parameters invalid.", "source": {"page": {"size": ["size must be less than 5000"]}}}
   10000 -> the same 400

fields=content,sg_status_list,entity,step,task_assignees,start_date,due_date, three reads each
   100 rows: median 331 ms, 66 KB, 3.31 ms a row
   500 rows: median 327 ms, 328 KB, 0.65 ms a row
  2000 rows: median 468 ms, 1208 KB, 0.23 ms a row
the project's 1900 Tasks, paged until an empty page
  page[size]=100: 20 calls, 6257 ms    500: 5 calls, 1741 ms    2000: 2 calls, 788 ms
```

**Teaches**

| `page[size]` | result |
|---|---|
| omitted | 500 rows |
| 1 to 5000 | that many rows, or the remainder |
| 5001 and above | 400 `size must be less than 5000` |
| 0 or negative | 400 `size must be greater than 0` |

- The message is off by one: 5000 itself is accepted.
- A call's fixed cost dominates. On the probed site 100 and 500 rows cost the same ~330 ms, and 2000
  cost 468 ms, so reading a whole page of 1900 rows at 2000 a call took 788 ms against 6257 ms at 100.
- Stop on the empty page, not on `links.next` (probe 006): that last empty call is part of every total above.
