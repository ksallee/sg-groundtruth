---
tags: [version, link, inspector, entity-field, paging]
verdict: On BBB, Versions link via `entity` 100% (Shot 99%, Asset 1%) and via `sg_task` only 1% - hardcoding Task-linking would be wrong almost always here, which is the whole case for the site profile. Also: page[size]=500 returned 100 rows, so page size is capped at 100.
---

# 005_link_usage

**Endpoint** `GET /entity/versions?fields=<link fields>`

**Docs claim** Versions may attach to Task, Shot, Asset, playlist — conventions vary by site.

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

**Verdict** On BBB, Versions link via `entity` 100% (Shot 99%, Asset 1%) and via `sg_task` only 1% - hardcoding Task-linking would be wrong almost always here, which is the whole case for the site profile. Also: page[size]=500 returned 100 rows, so page size is capped at 100.
