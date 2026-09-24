---
tags: [page, permission, sudo, user, trap]
endpoints: [POST /entity/<type>/_search, GET /entity/<type>/<id>]
phase: read
scope: api
measured: site-wide, as the script, an Admin and an Artist (sudo_as_login)
verdict: The script user is not the widest reader of Page: an Admin read 2048 pages where the script read 1107 and 404s on the rest. An Artist read 107. Every level reads every person's override.
---

# 076_page_visibility

**Q** How many Page and PageSetting rows does a script, an Admin and an Artist read, and does a person read other people's per-user overrides?

**Endpoint** `POST /entity/pages/_search ; POST /entity/page_settings/_search ; GET /entity/page_settings/<id>`

**Docs claim** Silent.

**Actual**

```
            pages  (project, site)   PageSetting on them  shared  per-user
  script     1107  (994, 113)        1134                 1109    25, all another's
  Admin      2048  (1352, 696)       2076                 2050    22 another's, 4 own
  Artist      107  (0, 107)           120                  109    11, all another's

Admin reads 941 pages the script does not, and none the script reads are missing:
  shared {true: 900, false: 41}; ui_category {defaults: 480, app: 303, project: 115, admin: 23, other: 20}
  page_type {canvas: 433, detail: 271, stream_detail: 227, ...}; created by that Admin 550, by another 391
  GET /entity/pages/<one of those ids> as the script -> 404; PageSetting for them as the script: 0 of 941
Artist reads 1000 fewer than the script, 0 extra, and no project page at all

fields=current_user_can_see, _search pages of 500:
  script  all 200          Artist  all 200
  Admin   pages 1 and 2 -> 400 {"code": 104, "title": "Read failed for entity type [Page]", "source": null, "detail": null}
          pages 3 and 4 -> 200; the same rows without that field -> 200

as the Artist, another user's override:
  GET /entity/page_settings/<id> -> 200, settings_json a list
  _search [["user", "is_not", null]] -> 200, 28 rows: every user-owned row on the site
```

**Teaches**

- **The script user does not see every page.** Every other count in this corpus is an `api_admin`
  number and the widest read on the site (probe 027); on `Page` an Admin reads 941 more, 41 of them
  unshared. To list the pages a person sees, read as that person with `sudo_as_login`; the script's list
  is neither a superset nor theirs.
- A page the script cannot see answers 404 by id, and its PageSetting rows do not come back under
  `page in [...]` either.
- On the probed site the Artist reads no project page at all and 107 site-level ones, so a Page+ list
  for an Artist is empty for projects even where probe 027 shows that Artist reading 8 projects.
- **`current_user_can_see` can fail a whole read.** As an Admin, asking for it in `fields` turned two
  pages of 500 into 400 code 104 `Read failed for entity type [Page]` with `detail` null, and the same
  rows read fine without it. Leave the field out of listings; read it per page if it matters.
- Overrides are not private over REST. A person reads every other person's PageSetting row, by id and
  by `_search`, so a column layout is visible site-wide.
