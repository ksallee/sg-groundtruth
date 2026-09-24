---
tags: [page, schema, inspector]
endpoints: [POST /entity/<type>/_search, GET /exports/page/<page_id>/<layout_name>.<format>]
phase: read
scope: api
measured: site-wide, 1107 listed pages and their 1134 PageSetting rows
coverage: partial
unmeasured: Which name the export's <layout_name> takes: every export on the probed site answers the page-level 422, so layouts[].name and display_name could not be told apart. Blocked on the site.
verdict: A page's views are root settings.layouts [{name, display_name}], each name a child of the root. Query widgets sit at /body, inside a view, or in tabs: walk the tree, never read /body alone.
---

# 072_page_layouts

**Q** How does a page's shared `settings_json` store its widgets, its views and its tabs, and does the tree hold the layout name `/exports/page/<id>/<layout>` takes?

**Endpoint** `POST /entity/page_settings/_search ; GET /exports/page/<page_id>/<layout_name>.csv`

**Docs claim** Silent. The REST docs describe no page layout.

**Actual**

```
1107 listed pages, 1134 PageSetting rows, 1109 shared; shared rows per page {1: 1106, 3: 1}
64 distinct widget types, 67292 widgets; top: Fields 13430, NewGrid 6786, EntityCard 3934,
  GanttWrapper 3667, EntityQueryPage 3468, ThumbnailGrid 3377, Calendar 3353

query widgets (EntityQueryPage) by page_type and path, top rows:
    924  stream_detail    /stream_detail/tab_N
    581  detail           /body/tabs/tab_N
    436  canvas           /body
    348  canvas           /body/card_content/entity_card_tabs/column2/embedded_event_query
     68  canvas           /layout_N/row_N/child_N/child
  ... 53 distinct (page_type, path)
query widgets per page {0: 127, 1: 195, 2: 280, 3: 125, 4: 81, 5: 33, 6: 103, 7: 98, 8: 52, 9: 6, 10: 6, 15: 1}

root settings.layouts on 363 pages {canvas: 50, stream_detail: 310, home: 1, detail: 1, notes_app_version_pane: 1}
  views per page {1: 352, 2: 8, 4: 1, 5: 2}; entry keys name, display_name, allowed_permission_group_codes,
  denied_permission_group_codes; layouts[].name is a key of the root's children on 382 of 382
  names: stream_detail 310, body 28, layout_0 24, layout_1 12, layout_2 4, layout_3 3, layout_4 1
one canvas page with two views:
  layouts [{"name": "layout_1", "display_name": "<view A>", "allowed_permission_group_codes": ["admin","artist","manager"]},
           {"name": "layout_0", "display_name": "<view B>", ...}]
  selected_layout null; root children [detail_pane, layout_0, layout_1, title]
    /layout_0  SG.Widget.Canvas.Body  settings {rows}      /layout_1  SG.Widget.Canvas.Body  settings {rows}
tab_order entries: name, display_name, embedded_entity_type, description, allowed_permission_group_codes;
  tab_order[].name is a child of the Tabs widget on 3804 of 3804

GET /exports/page/<id>.csv, /<id>/layout_0.csv, /<id>/layout_1.csv, /<id>/<display_name>.csv, /<id>/zzprobe_072_not_a_view.csv
  -> 422 'Export for Page id=<id> not available' on all five
```

**Teaches**

Every node is `{type, settings, children}`, and `children` is an object keyed by a name the parent's
settings refer to. Three places hold more than one query widget:

| holder | where the list is | what the names address |
|---|---|---|
| views | root `settings.layouts`, `selected_layout` | root children: `body` when there is one view, `layout_N` on a canvas with several |
| a canvas view | `Canvas.Body.settings.rows`, then `Canvas.Row.settings.column_widgets` | `row_N/child_N/child`, each a widget such as an EntityQueryPage |
| tabs | `SG.Widget.Tabs.settings.tab_order` | the Tabs widget's children: `tab_N`, `embedded_<type>_query`, `all_fields` |

- A page with no `layouts` key has one view and it is `body`. Recipe 003's `page_query` reads only
  `/body`, so on the probed site it misses 68 query widgets inside canvas views and every tab.
- An EntityQueryPage always holds its sibling views as children (`list_content`, `thumb_content`,
  `card_content`, `calendar_content`, `sched_content`, often `browser_content`); `mode` names the one
  showing (probe 073).
- `allowed_permission_group_codes` and `denied_permission_group_codes` gate a view or a tab by
  permission group code (`admin`, `artist`, `manager`). A runner acting for a person filters on them.
- On the probed site one system-owned `stream_detail` page holds 3 shared rows; the other 1106 pages
  hold one. `P.shared` keeps the last, so check the count before trusting one row.
- On the probed site 127 pages hold no query widget at all: app pages (`inbox`, `my_tasks`,
  `media_center`) whose widget is the whole page.
- The export's `<layout_name>` is either `layouts[].name` or `display_name`. The endpoint answers 422
  for both and for a name no view has (`endpoints/get_exports_page_id_layout_format`).
