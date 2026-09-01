---
tags: [schema, status, list-field, inspector]
verdict: Status lists are per entity type, not global - Version and Task share no vocabulary. valid_values, display_values, hidden_values and default_value are ALL readable over REST, so hidden values are visible even if not settable. On this site project_id changed nothing, which does not disprove project scoping - it means no per-project override exists here. Always read display_values: raw codes like 'pndvs' are meaningless to a user.
---

# 009_status_lists

**Endpoint** `GET /schema/<Type>/fields/sg_status_list ± project_id`

**Docs claim** Status lists are project-scoped; REST cannot see or set some of it.

**Actual**

```
200 Version sg_status_list [site-wide]
      top-level keys: ['custom_metadata', 'data_type', 'description', 'editable', 'entity_type', 'mandatory', 'name', 'properties', 'ui_value_displayable', 'unique', 'visible']
      property keys:  ['default_value', 'display_values', 'hidden_values', 'summary_default', 'valid_values']
      valid_values:   ['na', 'rev', 'vwd', 'apr', 'custom', 'fin', 'ip', 'clsd', 'cmpt', 'cfrm', 'pndad', 'pndl', 'pndvs', 'part', 'pass', 'pndng']
      display_values: {"apr": "Approved", "cmpt": "Complete", "ip": "In Progress", "na": "N/A", "rev": "Pending Review", "vwd": "Viewed", "cfrm": "Confirmed", "pndng": "Pending", "fin": "Final", "clsd": "Closed", "custom":
      hidden_values:  []
      default_value:  "rev"
      editable:       true  mandatory: false
200 Version sg_status_list [project_id=70]
      top-level keys: ['custom_metadata', 'data_type', 'description', 'editable', 'entity_type', 'mandatory', 'name', 'properties', 'ui_value_displayable', 'unique', 'visible']
      property keys:  ['default_value', 'display_values', 'hidden_values', 'summary_default', 'valid_values']
      valid_values:   ['na', 'rev', 'vwd', 'apr', 'custom', 'fin', 'ip', 'clsd', 'cmpt', 'cfrm', 'pndad', 'pndl', 'pndvs', 'part', 'pass', 'pndng']
      display_values: {"apr": "Approved", "cmpt": "Complete", "ip": "In Progress", "na": "N/A", "rev": "Pending Review", "vwd": "Viewed", "cfrm": "Confirmed", "pndng": "Pending", "fin": "Final", "clsd": "Closed", "custom":
      hidden_values:  ["pndl", "pndvs"]
      default_value:  "rev"
      editable:       true  mandatory: false

200 Task sg_status_list valid_values: ['wtg', 'ip', 'fin', 'apr', 'dis', 'na', 'hld', 'rev', 'omt', 'ready']
```

**Verdict** Status lists are per entity type, not global - Version and Task share no vocabulary. valid_values, display_values, hidden_values and default_value are ALL readable over REST, so hidden values are visible even if not settable. On this site project_id changed nothing, which does not disprove project scoping - it means no per-project override exists here. Always read display_values: raw codes like 'pndvs' are meaningless to a user.
