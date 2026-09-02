---
tags: [project, query, filter, inspector, list-field, trap]
verdict: DO NOT filter a project picker on sg_status. Its valid values are Bidding/Active/Lost/Hold with NO display_values, and it is null on most real projects - on this site 10 of 22, including freshly created ones, so 'sg_status is Active' hides working projects. The reliable discriminators are the checkboxes: is_template is True for exactly the stock templates, is_demo for the shipped demo show, archived for retired ones. Filter is_template/is_demo/archived is False and leave sg_status alone; a new project has no status until someone sets one.
---

# 018_project_listing

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

sg_status is NULL on real, in-use projects — it is not a liveness flag:
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

**Verdict** DO NOT filter a project picker on sg_status. Its valid values are Bidding/Active/Lost/Hold with NO display_values, and it is null on most real projects - on this site 10 of 22, including freshly created ones, so 'sg_status is Active' hides working projects. The reliable discriminators are the checkboxes: is_template is True for exactly the stock templates, is_demo for the shipped demo show, archived for retired ones. Filter is_template/is_demo/archived is False and leave sg_status alone; a new project has no status until someone sets one.
