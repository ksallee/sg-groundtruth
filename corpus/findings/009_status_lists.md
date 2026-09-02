---
tags: [schema, status, list-field, inspector]
verdict: A project's usable statuses are valid_values MINUS hidden_values, read with project_id. valid_values is identical at every scope and is NOT the answer on its own; hidden_values is what varies (site-wide hides 0, one project hides 2, another hides 6). Status lists are also per entity type - Version and Task share no vocabulary. Always read display_values: raw codes like 'pndvs' mean nothing to a user.
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
200 Version sg_status_list [project 63]
      top-level keys: ['custom_metadata', 'data_type', 'description', 'editable', 'entity_type', 'mandatory', 'name', 'properties', 'ui_value_displayable', 'unique', 'visible']
      property keys:  ['default_value', 'display_values', 'hidden_values', 'summary_default', 'valid_values']
      valid_values:   ['na', 'rev', 'vwd', 'apr', 'custom', 'fin', 'ip', 'clsd', 'cmpt', 'cfrm', 'pndad', 'pndl', 'pndvs', 'part', 'pass', 'pndng']
      display_values: {"apr": "Approved", "cmpt": "Complete", "ip": "In Progress", "na": "N/A", "rev": "Pending Review", "vwd": "Viewed", "cfrm": "Confirmed", "pndng": "Pending", "fin": "Final", "clsd": "Closed", "custom":
      hidden_values:  ["part", "pass", "pndad", "pndl", "pndng", "pndvs"]
      default_value:  "rev"
      editable:       true  mandatory: false
200 Version sg_status_list [project 70]
      top-level keys: ['custom_metadata', 'data_type', 'description', 'editable', 'entity_type', 'mandatory', 'name', 'properties', 'ui_value_displayable', 'unique', 'visible']
      property keys:  ['default_value', 'display_values', 'hidden_values', 'summary_default', 'valid_values']
      valid_values:   ['na', 'rev', 'vwd', 'apr', 'custom', 'fin', 'ip', 'clsd', 'cmpt', 'cfrm', 'pndad', 'pndl', 'pndvs', 'part', 'pass', 'pndng']
      display_values: {"apr": "Approved", "cmpt": "Complete", "ip": "In Progress", "na": "N/A", "rev": "Pending Review", "vwd": "Viewed", "cfrm": "Confirmed", "pndng": "Pending", "fin": "Final", "clsd": "Closed", "custom":
      hidden_values:  ["pndl", "pndvs"]
      default_value:  "rev"
      editable:       true  mandatory: false
200 Version sg_status_list [project 78]
      top-level keys: ['custom_metadata', 'data_type', 'description', 'editable', 'entity_type', 'mandatory', 'name', 'properties', 'ui_value_displayable', 'unique', 'visible']
      property keys:  ['default_value', 'display_values', 'hidden_values', 'summary_default', 'valid_values']
      valid_values:   ['na', 'rev', 'vwd', 'apr', 'custom', 'fin', 'ip', 'clsd', 'cmpt', 'cfrm', 'pndad', 'pndl', 'pndvs', 'part', 'pass', 'pndng']
      display_values: {"apr": "Approved", "cmpt": "Complete", "ip": "In Progress", "na": "N/A", "rev": "Pending Review", "vwd": "Viewed", "cfrm": "Confirmed", "pndng": "Pending", "fin": "Final", "clsd": "Closed", "custom":
      hidden_values:  ["part", "pass", "pndad", "pndl", "pndng", "pndvs"]
      default_value:  "rev"
      editable:       true  mandatory: false
200 Version sg_status_list [project 82]
      top-level keys: ['custom_metadata', 'data_type', 'description', 'editable', 'entity_type', 'mandatory', 'name', 'properties', 'ui_value_displayable', 'unique', 'visible']
      property keys:  ['default_value', 'display_values', 'hidden_values', 'summary_default', 'valid_values']
      valid_values:   ['na', 'rev', 'vwd', 'apr', 'custom', 'fin', 'ip', 'clsd', 'cmpt', 'cfrm', 'pndad', 'pndl', 'pndvs', 'part', 'pass', 'pndng']
      display_values: {"apr": "Approved", "cmpt": "Complete", "ip": "In Progress", "na": "N/A", "rev": "Pending Review", "vwd": "Viewed", "cfrm": "Confirmed", "pndng": "Pending", "fin": "Final", "clsd": "Closed", "custom":
      hidden_values:  ["part", "pass", "pndad", "pndl", "pndng", "pndvs"]
      default_value:  "rev"
      editable:       true  mandatory: false
200 Version sg_status_list [project 83]
      top-level keys: ['custom_metadata', 'data_type', 'description', 'editable', 'entity_type', 'mandatory', 'name', 'properties', 'ui_value_displayable', 'unique', 'visible']
      property keys:  ['default_value', 'display_values', 'hidden_values', 'summary_default', 'valid_values']
      valid_values:   ['na', 'rev', 'vwd', 'apr', 'custom', 'fin', 'ip', 'clsd', 'cmpt', 'cfrm', 'pndad', 'pndl', 'pndvs', 'part', 'pass', 'pndng']
      display_values: {"apr": "Approved", "cmpt": "Complete", "ip": "In Progress", "na": "N/A", "rev": "Pending Review", "vwd": "Viewed", "cfrm": "Confirmed", "pndng": "Pending", "fin": "Final", "clsd": "Closed", "custom":
      hidden_values:  ["part", "pass", "pndad", "pndl", "pndng", "pndvs"]
      default_value:  "rev"
      editable:       true  mandatory: false
200 Version sg_status_list [project 86]
      top-level keys: ['custom_metadata', 'data_type', 'description', 'editable', 'entity_type', 'mandatory', 'name', 'properties', 'ui_value_displayable', 'unique', 'visible']
      property keys:  ['default_value', 'display_values', 'hidden_values', 'summary_default', 'valid_values']
      valid_values:   ['na', 'rev', 'vwd', 'apr', 'custom', 'fin', 'ip', 'clsd', 'cmpt', 'cfrm', 'pndad', 'pndl', 'pndvs', 'part', 'pass', 'pndng']
      display_values: {"apr": "Approved", "cmpt": "Complete", "ip": "In Progress", "na": "N/A", "rev": "Pending Review", "vwd": "Viewed", "cfrm": "Confirmed", "pndng": "Pending", "fin": "Final", "clsd": "Closed", "custom":
      hidden_values:  ["part", "pass", "pndad", "pndl", "pndng", "pndvs"]
      default_value:  "rev"
      editable:       true  mandatory: false
200 Version sg_status_list [project 88]
      top-level keys: ['custom_metadata', 'data_type', 'description', 'editable', 'entity_type', 'mandatory', 'name', 'properties', 'ui_value_displayable', 'unique', 'visible']
      property keys:  ['default_value', 'display_values', 'hidden_values', 'summary_default', 'valid_values']
      valid_values:   ['na', 'rev', 'vwd', 'apr', 'custom', 'fin', 'ip', 'clsd', 'cmpt', 'cfrm', 'pndad', 'pndl', 'pndvs', 'part', 'pass', 'pndng']
      display_values: {"apr": "Approved", "cmpt": "Complete", "ip": "In Progress", "na": "N/A", "rev": "Pending Review", "vwd": "Viewed", "cfrm": "Confirmed", "pndng": "Pending", "fin": "Final", "clsd": "Closed", "custom":
      hidden_values:  ["part", "pass", "pndad", "pndl", "pndng", "pndvs"]
      default_value:  "rev"
      editable:       true  mandatory: false
200 Version sg_status_list [project 89]
      top-level keys: ['custom_metadata', 'data_type', 'description', 'editable', 'entity_type', 'mandatory', 'name', 'properties', 'ui_value_displayable', 'unique', 'visible']
      property keys:  ['default_value', 'display_values', 'hidden_values', 'summary_default', 'valid_values']
      valid_values:   ['na', 'rev', 'vwd', 'apr', 'custom', 'fin', 'ip', 'clsd', 'cmpt', 'cfrm', 'pndad', 'pndl', 'pndvs', 'part', 'pass', 'pndng']
      display_values: {"apr": "Approved", "cmpt": "Complete", "ip": "In Progress", "na": "N/A", "rev": "Pending Review", "vwd": "Viewed", "cfrm": "Confirmed", "pndng": "Pending", "fin": "Final", "clsd": "Closed", "custom":
      hidden_values:  ["part", "pass", "pndad", "pndl", "pndng", "pndvs"]
      default_value:  "rev"
      editable:       true  mandatory: false
200 Version sg_status_list [project 91]
      top-level keys: ['custom_metadata', 'data_type', 'description', 'editable', 'entity_type', 'mandatory', 'name', 'properties', 'ui_value_displayable', 'unique', 'visible']
      property keys:  ['default_value', 'display_values', 'hidden_values', 'summary_default', 'valid_values']
      valid_values:   ['na', 'rev', 'vwd', 'apr', 'custom', 'fin', 'ip', 'clsd', 'cmpt', 'cfrm', 'pndad', 'pndl', 'pndvs', 'part', 'pass', 'pndng']
      display_values: {"apr": "Approved", "cmpt": "Complete", "ip": "In Progress", "na": "N/A", "rev": "Pending Review", "vwd": "Viewed", "cfrm": "Confirmed", "pndng": "Pending", "fin": "Final", "clsd": "Closed", "custom":
      hidden_values:  ["pass"]
      default_value:  "rev"
      editable:       true  mandatory: false
200 Version sg_status_list [project 124]
      top-level keys: ['custom_metadata', 'data_type', 'description', 'editable', 'entity_type', 'mandatory', 'name', 'properties', 'ui_value_displayable', 'unique', 'visible']
      property keys:  ['default_value', 'display_values', 'hidden_values', 'summary_default', 'valid_values']
      valid_values:   ['na', 'rev', 'vwd', 'apr', 'custom', 'fin', 'ip', 'clsd', 'cmpt', 'cfrm', 'pndad', 'pndl', 'pndvs', 'part', 'pass', 'pndng']
      display_values: {"apr": "Approved", "cmpt": "Complete", "ip": "In Progress", "na": "N/A", "rev": "Pending Review", "vwd": "Viewed", "cfrm": "Confirmed", "pndng": "Pending", "fin": "Final", "clsd": "Closed", "custom":
      hidden_values:  ["part", "pass", "pndad", "pndl", "pndng", "pndvs"]
      default_value:  "rev"
      editable:       true  mandatory: false
200 Version sg_status_list [project 157]
      top-level keys: ['custom_metadata', 'data_type', 'description', 'editable', 'entity_type', 'mandatory', 'name', 'properties', 'ui_value_displayable', 'unique', 'visible']
      property keys:  ['default_value', 'display_values', 'hidden_values', 'summary_default', 'valid_values']
      valid_values:   ['na', 'rev', 'vwd', 'apr', 'custom', 'fin', 'ip', 'clsd', 'cmpt', 'cfrm', 'pndad', 'pndl', 'pndvs', 'part', 'pass', 'pndng']
      display_values: {"apr": "Approved", "cmpt": "Complete", "ip": "In Progress", "na": "N/A", "rev": "Pending Review", "vwd": "Viewed", "cfrm": "Confirmed", "pndng": "Pending", "fin": "Final", "clsd": "Closed", "custom":
      hidden_values:  ["part", "pass", "pndad", "pndl", "pndng", "pndvs"]
      default_value:  "rev"
      editable:       true  mandatory: false
200 Version sg_status_list [project 308]
      top-level keys: ['custom_metadata', 'data_type', 'description', 'editable', 'entity_type', 'mandatory', 'name', 'properties', 'ui_value_displayable', 'unique', 'visible']
      property keys:  ['default_value', 'display_values', 'hidden_values', 'summary_default', 'valid_values']
      valid_values:   ['na', 'rev', 'vwd', 'apr', 'custom', 'fin', 'ip', 'clsd', 'cmpt', 'cfrm', 'pndad', 'pndl', 'pndvs', 'part', 'pass', 'pndng']
      display_values: {"apr": "Approved", "cmpt": "Complete", "ip": "In Progress", "na": "N/A", "rev": "Pending Review", "vwd": "Viewed", "cfrm": "Confirmed", "pndng": "Pending", "fin": "Final", "clsd": "Closed", "custom":
      hidden_values:  ["part", "pass", "pndng"]
      default_value:  "rev"
      editable:       true  mandatory: false
200 Version sg_status_list [project 396]
      top-level keys: ['custom_metadata', 'data_type', 'description', 'editable', 'entity_type', 'mandatory', 'name', 'properties', 'ui_value_displayable', 'unique', 'visible']
      property keys:  ['default_value', 'display_values', 'hidden_values', 'summary_default', 'valid_values']
      valid_values:   ['na', 'rev', 'vwd', 'apr', 'custom', 'fin', 'ip', 'clsd', 'cmpt', 'cfrm', 'pndad', 'pndl', 'pndvs', 'part', 'pass', 'pndng']
      display_values: {"apr": "Approved", "cmpt": "Complete", "ip": "In Progress", "na": "N/A", "rev": "Pending Review", "vwd": "Viewed", "cfrm": "Confirmed", "pndng": "Pending", "fin": "Final", "clsd": "Closed", "custom":
      hidden_values:  ["part", "pass", "pndad", "pndl", "pndng", "pndvs"]
      default_value:  "rev"
      editable:       true  mandatory: false
200 Version sg_status_list [project 916]
      top-level keys: ['custom_metadata', 'data_type', 'description', 'editable', 'entity_type', 'mandatory', 'name', 'properties', 'ui_value_displayable', 'unique', 'visible']
      property keys:  ['default_value', 'display_values', 'hidden_values', 'summary_default', 'valid_values']
      valid_values:   ['na', 'rev', 'vwd', 'apr', 'custom', 'fin', 'ip', 'clsd', 'cmpt', 'cfrm', 'pndad', 'pndl', 'pndvs', 'part', 'pass', 'pndng']
      display_values: {"apr": "Approved", "cmpt": "Complete", "ip": "In Progress", "na": "N/A", "rev": "Pending Review", "vwd": "Viewed", "cfrm": "Confirmed", "pndng": "Pending", "fin": "Final", "clsd": "Closed", "custom":
      hidden_values:  ["part", "pass", "pndng"]
      default_value:  "rev"
      editable:       true  mandatory: false
200 Version sg_status_list [project 949]
      top-level keys: ['custom_metadata', 'data_type', 'description', 'editable', 'entity_type', 'mandatory', 'name', 'properties', 'ui_value_displayable', 'unique', 'visible']
      property keys:  ['default_value', 'display_values', 'hidden_values', 'summary_default', 'valid_values']
      valid_values:   ['na', 'rev', 'vwd', 'apr', 'custom', 'fin', 'ip', 'clsd', 'cmpt', 'cfrm', 'pndad', 'pndl', 'pndvs', 'part', 'pass', 'pndng']
      display_values: {"apr": "Approved", "cmpt": "Complete", "ip": "In Progress", "na": "N/A", "rev": "Pending Review", "vwd": "Viewed", "cfrm": "Confirmed", "pndng": "Pending", "fin": "Final", "clsd": "Closed", "custom":
      hidden_values:  ["part", "pass", "pndad", "pndl", "pndng", "pndvs"]
      default_value:  "rev"
      editable:       true  mandatory: false
200 Version sg_status_list [project 982]
      top-level keys: ['custom_metadata', 'data_type', 'description', 'editable', 'entity_type', 'mandatory', 'name', 'properties', 'ui_value_displayable', 'unique', 'visible']
      property keys:  ['default_value', 'display_values', 'hidden_values', 'summary_default', 'valid_values']
      valid_values:   ['na', 'rev', 'vwd', 'apr', 'custom', 'fin', 'ip', 'clsd', 'cmpt', 'cfrm', 'pndad', 'pndl', 'pndvs', 'part', 'pass', 'pndng']
      display_values: {"apr": "Approved", "cmpt": "Complete", "ip": "In Progress", "na": "N/A", "rev": "Pending Review", "vwd": "Viewed", "cfrm": "Confirmed", "pndng": "Pending", "fin": "Final", "clsd": "Closed", "custom":
      hidden_values:  ["part", "pass", "pndad", "pndl", "pndng", "pndvs"]
      default_value:  "rev"
      editable:       true  mandatory: false
200 Version sg_status_list [project 1015]
      top-level keys: ['custom_metadata', 'data_type', 'description', 'editable', 'entity_type', 'mandatory', 'name', 'properties', 'ui_value_displayable', 'unique', 'visible']
      property keys:  ['default_value', 'display_values', 'hidden_values', 'summary_default', 'valid_values']
      valid_values:   ['na', 'rev', 'vwd', 'apr', 'custom', 'fin', 'ip', 'clsd', 'cmpt', 'cfrm', 'pndad', 'pndl', 'pndvs', 'part', 'pass', 'pndng']
      display_values: {"apr": "Approved", "cmpt": "Complete", "ip": "In Progress", "na": "N/A", "rev": "Pending Review", "vwd": "Viewed", "cfrm": "Confirmed", "pndng": "Pending", "fin": "Final", "clsd": "Closed", "custom":
      hidden_values:  ["part", "pass", "pndad", "pndl", "pndng", "pndvs"]
      default_value:  "rev"
      editable:       true  mandatory: false
200 Version sg_status_list [project 1048]
      top-level keys: ['custom_metadata', 'data_type', 'description', 'editable', 'entity_type', 'mandatory', 'name', 'properties', 'ui_value_displayable', 'unique', 'visible']
      property keys:  ['default_value', 'display_values', 'hidden_values', 'summary_default', 'valid_values']
      valid_values:   ['na', 'rev', 'vwd', 'apr', 'custom', 'fin', 'ip', 'clsd', 'cmpt', 'cfrm', 'pndad', 'pndl', 'pndvs', 'part', 'pass', 'pndng']
      display_values: {"apr": "Approved", "cmpt": "Complete", "ip": "In Progress", "na": "N/A", "rev": "Pending Review", "vwd": "Viewed", "cfrm": "Confirmed", "pndng": "Pending", "fin": "Final", "clsd": "Closed", "custom":
      hidden_values:  ["part", "pass", "pndad", "pndl", "pndng", "pndvs"]
      default_value:  "rev"
      editable:       true  mandatory: false
200 Version sg_status_list [project 1081]
      top-level keys: ['custom_metadata', 'data_type', 'description', 'editable', 'entity_type', 'mandatory', 'name', 'properties', 'ui_value_displayable', 'unique', 'visible']
      property keys:  ['default_value', 'display_values', 'hidden_values', 'summary_default', 'valid_values']
      valid_values:   ['na', 'rev', 'vwd', 'apr', 'custom', 'fin', 'ip', 'clsd', 'cmpt', 'cfrm', 'pndad', 'pndl', 'pndvs', 'part', 'pass', 'pndng']
      display_values: {"apr": "Approved", "cmpt": "Complete", "ip": "In Progress", "na": "N/A", "rev": "Pending Review", "vwd": "Viewed", "cfrm": "Confirmed", "pndng": "Pending", "fin": "Final", "clsd": "Closed", "custom":
      hidden_values:  ["part", "pass", "pndad", "pndl", "pndng", "pndvs"]
      default_value:  "rev"
      editable:       true  mandatory: false
200 Version sg_status_list [project 1114]
      top-level keys: ['custom_metadata', 'data_type', 'description', 'editable', 'entity_type', 'mandatory', 'name', 'properties', 'ui_value_displayable', 'unique', 'visible']
      property keys:  ['default_value', 'display_values', 'hidden_values', 'summary_default', 'valid_values']
      valid_values:   ['na', 'rev', 'vwd', 'apr', 'custom', 'fin', 'ip', 'clsd', 'cmpt', 'cfrm', 'pndad', 'pndl', 'pndvs', 'part', 'pass', 'pndng']
      display_values: {"apr": "Approved", "cmpt": "Complete", "ip": "In Progress", "na": "N/A", "rev": "Pending Review", "vwd": "Viewed", "cfrm": "Confirmed", "pndng": "Pending", "fin": "Final", "clsd": "Closed", "custom":
      hidden_values:  ["part", "pass", "pndad", "pndl", "pndng", "pndvs"]
      default_value:  "rev"
      editable:       true  mandatory: false

200 Task sg_status_list valid_values: ['wtg', 'ip', 'fin', 'apr', 'dis', 'na', 'hld', 'rev', 'omt', 'ready']
```

**Verdict** A project's usable statuses are valid_values MINUS hidden_values, read with project_id. valid_values is identical at every scope and is NOT the answer on its own; hidden_values is what varies (site-wide hides 0, one project hides 2, another hides 6). Status lists are also per entity type - Version and Task share no vocabulary. Always read display_values: raw codes like 'pndvs' mean nothing to a user.
