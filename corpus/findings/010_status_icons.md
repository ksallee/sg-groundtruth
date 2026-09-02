---
tags: [status, icon, cache, schema, colour]
verdict: Status is a real queryable entity (32 rows, 11 fields) holding bg_color, name, code and a `system` flag separating built-in from custom statuses. bg_color is comma-separated RGB ('25,118,27'), NOT hex. GAP: `icon` is null on all 32 statuses on this site, so the standard/custom-icon branches are unverified - set a custom icon on one status to close it.
---

# 010_status_icons

**Endpoint** `GET /schema/Status/fields, GET /entity/statuses`

**Docs claim** Status colour and icon come from the Status entity; three icon cases must be handled.

**Actual**

```
200 /schema/Status/fields -> 11 fields
      ['bg_color', 'cached_display_name', 'code', 'created_at', 'created_by', 'icon', 'id', 'name', 'system', 'updated_at', 'updated_by']
200 /entity/statuses -> 32 statuses
      {"bg_color": "25,118,27", "cached_display_name": "Obsidian", "code": "delta", "name": "Obsidian", "system": true, "updated_at": "2018-12-04T01:21:48Z"}
      {"bg_color": "179,179,179", "cached_display_name": "Approved", "code": "apr", "name": "Approved", "system": false, "updated_at": "2010-09-05T01:00:12Z"}
      {"bg_color": "150,150,150", "cached_display_name": "Closed", "code": "clsd", "name": "Closed", "system": false, "updated_at": "2018-12-04T00:45:58Z"}
      {"bg_color": "146,146,146", "cached_display_name": "Complete", "code": "cmpt", "name": "Complete", "system": false, "updated_at": "2010-09-05T01:00:12Z"}
      {"bg_color": "204,0,1", "cached_display_name": "Disabled", "code": "dis", "name": "Disabled", "system": true, "updated_at": "2026-01-09T18:14:27Z"}
      {"bg_color": "150,150,150", "cached_display_name": "Final", "code": "fin", "name": "Final", "system": false, "updated_at": "2018-12-04T00:44:12Z"}

      icon as string (standard): 0 []
      icon as object (uploaded): 0 []
      icon empty:                32 ['zephyr', 'apr', 'clsd', 'cmpt', 'dis', 'fin', 'hld', 'ip']
```

**Verdict** Status is a real queryable entity (32 rows, 11 fields) holding bg_color, name, code and a `system` flag separating built-in from custom statuses. bg_color is comma-separated RGB ('25,118,27'), NOT hex. GAP: `icon` is null on all 32 statuses on this site, so the standard/custom-icon branches are unverified - set a custom icon on one status to close it.
