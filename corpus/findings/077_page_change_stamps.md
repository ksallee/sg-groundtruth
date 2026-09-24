---
tags: [page, event-log, schema, observe]
endpoints: [GET /schema/<Type>/fields, POST /entity/<type>/_search, POST /entity/<type>/_summarize]
phase: observe
scope: api
measured: site-wide: both schemas, the event log's page events, the newest 500 Shotgun_PageSetting_Change rows
verdict: PageSetting has no updated_at; Page.updated_at moves when its layout is saved. Poll Page.updated_at; Shotgun_PageSetting_Change names which setting changed but its entity is null on 131 of 500.
---

# 077_page_change_stamps

**Q** What tells a client that a page's layout changed: an `updated_at` on Page or PageSetting, or an EventLogEntry row for the save?

**Endpoint** `GET /schema/Page/fields ; GET /schema/PageSetting/fields ; POST /entity/event_log_entries/_search`

**Docs claim** Silent.

**Actual**

```
/schema/Page/fields: 24, among them updated_at date_time, updated_by entity, created_at, created_by,
  last_accessed, hits_last_month, accesses_by_current_user, current_user_can_see, shared, system_owned
/schema/PageSetting/fields: 6: cached_display_name, created_at, id, page, settings_json, user
PageSetting ?fields=updated_at,updated_by,created_at,created_by -> attributes [created_at], nothing else
PageSetting [["updated_at","is_not",null]] -> 400 "API read() PageSetting.updated_at doesn't exist."

event types starting Shotgun_Page, site-wide:
  Shotgun_Page_Change 8665   Shotgun_Page_New 4497   Shotgun_Page_Retirement 3536
  Shotgun_PageSetting_Change 8534   Shotgun_PageSetting_New 4739
Shotgun_PageSetting_Change, newest 500: attribute_name null on all; entity {Page: 369, null: 131}
  meta keys {(changes, friendly_changes, type): 233, (page_setting_history_id): 221,
             (changes, friendly_changes, page_setting_history_id, type): 41, (): 5}
  a change entry: {"path": ["body", "list_content"], "type": "SG.Widget.NewGrid", "setting": "columns"}
    also seen: a view_name key (38), an added key in place of setting (4)
  friendly_changes: "On Grid changed panel filters\nOn Grid added column \"Project\" (project)"
  /schema types naming History: none, so page_setting_history_id resolves to nothing over REST
Shotgun_Page_Change: attribute_name set (name on the newest 50), meta old_value/new_value as usual

Page.updated_at against the page's newest event:
  newest Shotgun_PageSetting_Change at 18:45:27Z   Page.updated_at 18:45:27Z
  newest Shotgun_Page_Change at 18:43:26Z          Page.updated_at 18:43:26Z   (3 pages)
```

**Teaches**

| signal | on | tells you |
|---|---|---|
| `Page.updated_at`, `updated_by` | Page | the page or its layout changed; it moved to the second of a layout save |
| `PageSetting.updated_at` | none | the field does not exist: `?fields` drops it, a filter 400s |
| `Shotgun_PageSetting_Change` | EventLogEntry | which widget and which setting changed, never the new value |
| `Shotgun_Page_Change` | EventLogEntry | an attribute change on Page, with `old_value`/`new_value` |

- Cache a layout keyed on `Page.id` plus `Page.updated_at`; one `?fields=updated_at` read tells you whether
  to refetch the tree.
- `PageSetting.created_at` does not move on an edit, so it cannot stand in for a change stamp.
- A settings event names the Page under `entity` on 369 of 500; on the other 131 `entity` is null and
  nothing in `meta` names the row or the page, so the event log cannot tie every save to a page.
- `meta.changes` lists `{path, type, setting}` per change. Diff the trees yourself for values.
- A script's own `PUT` on `settings_json` logged a different shape (probe 078): an `attribute_change`
  whose `old_value` and `new_value` are the whole JSON as strings.
