---
tags: [permission, sudo, custom-entity, group]
endpoints: [POST /entity/<type>/_search, GET /entity/<type>/<id>, GET /entity/<type>, POST /entity/<type>/_summarize]
phase: read
scope: api
measured: sandbox project written, 2026-11-20; 3 Bids and 2 Bid Lines; two people re-roled to Vendor via sudo, restored
verdict: On the probed site a Vendor reads every Bid in an assigned project, the other vendor's included: Vendor's `read` on Bid is `allowed`. A Group filter the client adds narrows the list, not the rights.
---

# 163_vendor_rows

**Q** Does a person in the Vendor group see every row of a custom entity in a project they are
assigned to, or only some?

**Endpoint** `POST /entity/<type>/_search ; GET /entity/<type>/<id> ; GET /entity/<type> ; POST /entity/<type>/_summarize`

**Docs claim** Silent. Probe 162 read Vendor's rule on `<Bid>` as `"read": {"access": "allowed"}`, with
no condition.

**Actual**

```
rows, made by the script in the sandbox: bid A (vendor groups [group A]), bid B ([group B]),
bid none ([]); line A under bid A, line B under bid B. Vendor A is in group A's users, vendor B in B's.

                                                        vendor A                   vendor B
_search Bids in the sandbox                             bid A, bid B, bid none     the same three
_search Bid Lines in the sandbox                        line A, line B             line A, line B
GET /entity/<bid>/<id>, each of the three               200, 200, 200              200, 200, 200
  vendor groups read on bid B                           [group B]                  [group B]
GET /entity/<bid>?filter[project.Project.id]=<sandbox>  the three                  the three
_search + [<vendor groups>.Group.users, is, <self>]     bid A                      bid B
_summarize count of Bids                                {"id": 3}                  {"id": 3}
```

**Teaches**
- `read: allowed` on a type is every row of it in every project the person sees. Nothing on the row,
  its Group field included, narrows that, and every read call agrees: list, fetch, filter, count.
- A filter on `<vendor groups field>.Group.users is <person>` returns only the person's own Bid. It is a
  view the client chose: the same person omitting it reads the other vendor's Bid and its amounts.
- Keeping vendors apart needs a conditional see rule on Bid, made in the web interface (probe 162), and
  one on Bid Line. Probe 165 measures what a see rule still lets through, on Shot.
- On the probed site the Vendor and Artist groups read custom entities alike (probe 143), so an app
  cannot rely on the stock roles to separate vendors on a type it adds.
