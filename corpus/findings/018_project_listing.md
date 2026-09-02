---
tags: [project, query, filter, inspector, list-field, trap]
scope: api
verdict: Filter a project picker on the checkboxes (is_template/is_demo/archived is False), never on sg_status, which on the probed site is null on 15 of 22 projects because nothing sets it.
---

# 018_project_listing

**Q** How do you list the projects a human would actually pick from?

**Endpoint** `GET /entity/projects ; POST /entity/projects/_search`

**Docs claim** sg_status marks a project Active.

**Actual**

```
candidate fields on Project:
  sg_status              list       valid=['Bidding', 'Active', 'Lost', 'Hold'] display=None
  archived               checkbox   valid=None display=None
  is_template            checkbox   valid=None display=None
  is_demo                checkbox   valid=None display=None
  is_template_project    checkbox   valid=None display=None

22 projects on the site
  sg_status      {'None': 15, 'Active': 5, 'Lost': 1, 'Bidding': 1}
  archived       {'False': 22}
  is_template    {'True': 7, 'False': 15}
  is_demo        {'False': 21, 'True': 1}

sg_status is NULL on real, in-use projects - it is not a liveness flag:
  8 of 22 have no status and are not templates

filter results:
  no filter                                    -> 22
  sg_status is Active                          -> 5
  is_template is False                         -> 15
  is_demo is False                             -> 21
  archived is False                            -> 22
  not template AND not archived                -> 15
  not template AND not demo AND not archived   -> 14
```

**Teaches**
- **Trap.** `sg_status is Active` is not a liveness filter. A project has no status until someone sets one: on the probed site 15 of 22 are null, 8 of those non-template working shows, so the filter returns 5 and hides the rest.
- `sg_status` is a list field with valid values Bidding/Active/Lost/Hold and no `display_values`, so even where it is set there is no label to put in front of a user (probe 009).
- The checkboxes are the discriminators. On the probed site:

  | checkbox | True on |
  |---|---|
  | `is_template` | 7, the stock templates |
  | `is_demo` | 1, the shipped demo show |
  | `archived` | 0 of 22 |

  All three False leaves 14 of 22. The archived clause is proven harmless but not proven to exclude anything; keep it, it costs nothing.
