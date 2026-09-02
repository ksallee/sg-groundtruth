---
tags: [schema, status, list-field, inspector]
scope: api
verdict: A project's usable statuses are valid_values minus hidden_values, read with project_id: valid_values is identical at every scope, hidden_values is the only thing that varies.
---

# 009_status_lists

**Q** Are a project's usable statuses visible over REST, and if so where in the field schema are they?

**Endpoint** `GET /schema/<Type>/fields/sg_status_list ± project_id`

**Docs claim** Status lists are project-scoped; REST cannot see or set some of it.

**Actual**

```
200 Version sg_status_list [site-wide]
      top-level keys: ['custom_metadata', 'data_type', 'description', 'editable', 'entity_type', 'mandatory', 'name', 'properties', 'ui_value_displayable', 'unique', 'visible']
      property keys:  ['default_value', 'display_values', 'hidden_values', 'summary_default', 'valid_values']
      valid_values:   ['na', 'rev', 'vwd', 'apr', 'custom', 'fin', 'ip', 'clsd', 'cmpt', 'cfrm', 'pndad', 'pndl', 'pndvs', 'part', 'pass', 'pndng']
      display_values: {"apr": "Approved", "cmpt": "Complete", "ip": "In Progress", "na": "N/A", "rev": "Pending Review", "vwd": "Viewed", "cfrm": "Confirmed", "pndng": "Pending", "fin": "Final", "clsd": "Closed", "custom": "CustomIcon", "pass": "pass", "part": "partial", "pndad": "Pending Art Director", "pndl": "Pending Lead", "pndvs": "Pending VFX Supervisor"}
      hidden_values:  []
      default_value:  "rev"
      editable:       true  mandatory: false
200 Version sg_status_list [project 63 = demo_show]
      top-level keys / property keys / valid_values / display_values / default_value: byte-identical to site-wide
      hidden_values:  ["part", "pass", "pndad", "pndl", "pndng", "pndvs"]    -> 10 usable
200 [project 70 = sample_show] hidden_values: ["pndl", "pndvs"]              -> 14 usable
200 [project 91] hidden_values: ["pass"]                                    -> 15 usable
   ... 17 further projects: 15 hide the same 6, 2 hide ["part", "pass", "pndng"]

distinct valid_values across 21 scopes: 1
200 Task sg_status_list valid_values: ['wtg', 'ip', 'fin', 'apr', 'dis', 'na', 'hld', 'rev', 'omt', 'ready']
```

**Teaches**
- Usable statuses are `valid_values` minus `hidden_values`, read with `project_id`. REST does not enforce
  `hidden_values` on write, so do the subtraction yourself. See `field_types/status_list.md`.
- `valid_values` is the site's whole vocabulary and is byte-identical at every scope, so reading it alone
  tells you nothing about a project. On the probed site, 21 scopes returned 1 distinct value.
- `hidden_values` is the only thing `project_id` changes. Omit `project_id` and you get the site-wide
  answer, which hides nothing and will offer statuses the project's UI refuses.
- Status lists are per entity type. On the probed site, Version and Task overlap only on
  `ip`/`fin`/`apr`/`na`/`rev`, and Task's `wtg`/`hld`/`omt`/`ready` do not exist on Version. Never reuse
  one type's codes for another.
- On the probed site, Version's 16 `valid_values` leave 10 usable in one project, 14 in another and 15 in
  a third, and 15 of the 21 projects hide the same 6 codes. Which codes a project hides is site
  configuration, not API behaviour: read it per project rather than reusing a list between sites.
- Always render `display_values`: `pndvs` means "Pending VFX Supervisor" to nobody, and a missing key
  there is possible, so fall back to the raw code rather than dropping the option.
