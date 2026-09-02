---
tags: [version, link, inspector, entity-field, paging]
scope: site
measured: one sample project, its 100 most recent Versions
verdict: On the sample project every Version links through `entity` (99% Shot, 1% Asset) and only 1% through `sg_task`, so measure link usage per site rather than hardcoding Task-linking.
---

# 005_link_usage

**Q** On a real project, what do Versions actually link to, and how often?

**Endpoint** `GET /entity/versions?fields=<link fields>`

**Docs claim** Versions may attach to Task, Shot, Asset or playlist. Conventions vary by site.

**Actual**

```
sample: 100 most recent Versions on project 70

link field presence:
  entity        100/100  100%
  sg_task         1/100  1%
  user          100/100  100%
  playlists       0/100  0%
  project       100/100  100%
  created_by    100/100  100%

entity target types:
  Shot           99  99%
  Asset           1  1%
```

**Teaches**
- On the probed site `entity` is the load-bearing link and `sg_task` is near-unused: a client that assumes Version to Task finds nothing 99% of the time. Measure link usage per site before coding against it.
- `entity` is polymorphic. Read `relationships.entity.data.type` per row; do not assume Shot even at 99%.
- A multi-entity field can be uniformly empty (`playlists` 0/100), so absence of data is not absence of the field.
- `page[size]=500` returned 100 rows because the project holds exactly 100 Versions, not because of a cap: probe 016 shows 150 returns 150.
