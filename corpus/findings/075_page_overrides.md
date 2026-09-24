---
tags: [page, user]
endpoints: [POST /entity/<type>/_search]
phase: read
scope: api
measured: site-wide, the 25 per-user PageSetting rows on 1107 listed pages
verdict: A per-user override patches columns, widths, sorts, mode and the filter panel at any spec_path, "" meaning the root. One row per user and page; 3 of 32 patches name a path the shared tree lacks.
---

# 075_page_overrides

**Q** Which `spec_path`s and settings keys do the per-user PageSetting arrays patch, and does a user ever hold more than one row for one page?

**Endpoint** `POST /entity/page_settings/_search`

**Docs claim** Silent.

**Actual**

```
1134 PageSetting rows on 1107 listed pages; 25 have a user, all HumanUser, all a list
  9 users, 17 pages; rows per (user, page) {1: 25}
  page_type: canvas 12, projects 5, my_tasks 3, media_center_right_pane 2, other 3
patches: 32; per row {1: 20, 2: 3, 3: 2}; keys of a patch: spec_path, settings
spec_path: body|list_content 8, body 6, "" 5, layout_0|row_2|child_8|child 5, bottom 2,
           body|thumb_content 1, body|list_content|step_0 1, stream_detail|... 3, layout_0|row_2|child_3|child 1
  (spec_path, key), top:
      5  body|list_content              columns, column_widths
      4  body|list_content              wrapped_columns
      3  ""                             filter_panel_settings, filter_panel_filters
      2  ""                             low_date, high_date, date_range
      2  body                           mode, sorts
      1  body                           group_settings
      1  body|list_content|step_0       __CHILD__, open, columns
spec_path resolved against the page's shared tree: a widget 29, no such path 3
  widgets patched: EntityQueryPage 8, NewGrid 8, Countdown 6, MyTasks 3, ThumbnailGrid 1, other 3
user-owned rows site-wide 28; 3 of them name a page the listing does not return
```

**Teaches**

| `spec_path` | patches | resolves to |
|---|---|---|
| `""` | the root: `filter_panel_filters`, `filter_panel_settings`, a date range | the page widget itself |
| `body` | `mode`, `sorts`, `group_settings` | the query widget |
| `body\|list_content` | `columns`, `column_widths`, `wrapped_columns`, `wrap_column_header_text` | the list grid |
| `layout_N\|row_N\|child_N\|child` | a widget inside a canvas view | whatever that child is |

- Apply a patch by walking the shared tree's `children` along `spec_path` split on `|`, skipping empty
  segments, then merging `settings` key by key. An empty `spec_path` is the root.
- A person's filter choice is stored under the root as `filter_panel_filters`, not in `body.settings.filters`.
  A runner honouring an override has to read both.
- A patch can name a child the shared tree does not have (`body|list_content|step_0`, a pivot
  sub-grid); 3 of 32 do on the probed site. Skip it rather than creating the path.
- Rows per (user, page) were 1 in every case, so no merge order between rows is needed on the probed site.
- A person reads everyone's overrides, not only their own (probe 076).
