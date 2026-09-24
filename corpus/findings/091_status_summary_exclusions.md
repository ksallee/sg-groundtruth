---
tags: [status, summary, schema]
endpoints: [GET /schema/<Type>/fields/<field>, PUT /schema/<Type>/fields/<field>, POST /entity/<type>/_summarize, POST /entity/<type>/_search]
phase: schema
scope: api
measured: sandbox project read and written (two own Shots, deleted), the exclusion set by the operator in the web interface
coverage: partial
unmeasured: status_list with the exclusion removed on the same rows: the setting is not API-writable, so the before state rests on probe 079's rule, not on a toggle. Blocked on the API.
verdict: Excluded statuses are invisible to REST: not in /schema at any scope, not writable by PUT. status_list honours them: fin plus an excluded omt rolls up to fin, omt alone to na.
---

# 091_status_summary_exclusions

**Q** Where does a status field's "Excluded statuses" setting (Summary = Status) show over REST, is it writable, and does `_summarize` honour it?

**Endpoint** `GET /schema/Shot/fields/sg_status_list ; PUT /schema/Shot/fields/sg_status_list ; POST /entity/shots/_summarize`

**Docs claim** The Flow PT 8.88 administrator help describes the setting in the web interface. The REST docs are silent.

**Actual**

```
GET /schema/<Type>/fields/sg_status_list, site and ?project_id=<sandbox>, Shot and Asset:
  properties [default_value, display_values, hidden_values, summary_default, valid_values]; "exclu" in the body: False
  GET /schema/Shot/fields?project_id=... and /api/v1.1/...: "exclu" in the body: False
  GET /schema/DisplayColumn -> 404 "Entity type 'DisplayColumn' does not exist."
the event log, Shotgun_DisplayColumn_Change, entity {"type": "DisplayColumn", "name": "sg_status_list"}, project null
  old data_type_properties {"status_list_default": "wtg", "status_list_subset": [...], "status_list_format": null}
  new data_type_properties {..., "status_list_summary_exclude": ["omt"]}
PUT /schema/Shot/fields/sg_status_list {"properties": [{"property_name": "status_list_summary_exclude", ...}]}
  -> 400 "API schema_field_update() invalid property 'status_list_summary_exclude': ...
          Valid property names: ["name", "visible", "description", "summary_default", "default_value",
          "valid_values", "custom_metadata"]"

the probe's own two Shots, one fin, one omt (--write):
  both          status_list "fin" over 2 rows
  the omt one   status_list "na"  over 1 row
  the fin one   status_list "fin" over 1 row
the sandbox's existing Shots (wtg 13, ip 14, fin 1, rev 7, omt 1):
  status in [fin, omt] -> "fin";  [ip, omt] -> "ip";  omt alone -> "na";  control [fin, wtg] -> "ip"
  status_percentage and status_percentage_as_float: 0 on every set
```

**Teaches**

- **The setting is stored where REST cannot read it.** It is `status_list_summary_exclude` inside the
  field's `DisplayColumn` `data_type_properties`, and DisplayColumn is not a REST type. It is site-wide:
  the change event names no project, and the schema reads the same with and without `project_id`.
- The one REST trace is `Shotgun_DisplayColumn_Change` in the event log, whose `meta.new_value` holds the
  list. A client can learn the current list only from the newest such event, if the log still has it.
- **Not writable.** `PUT /schema` rejects the name and enumerates the seven writable properties, so the
  exclusion is set in the web interface only (Fields, the status field, Summary = Status, Excluded statuses).
- **`status_list` applies it.** Without an exclusion a mix rolls up to `ip` (probe 079: `[fin, wtg]` gives
  `ip`); with `omt` excluded, `[fin, omt]` gives `fin`, and `omt` alone gives `na`, not `omt`. A client
  computing its own roll-up from grouped counts must drop the excluded statuses itself, and has to be told
  which they are.
- `status_percentage` returned 0 on every set here and is not a share of anything (probe 079).
