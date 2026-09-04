---
tags: [page, query, filter, schema, project, inspector, trap, silent]
endpoints: [GET /entity/<type>, POST /entity/<type>/_search, GET /schema/<Type>/fields]
phase: read
scope: api
measured: first sample project, plus the site-wide Page and PageSetting listings
verdict: A page's layout is the PageSetting row whose user is null; settings_json reads back as decoded JSON and body/list_content settings.columns is the column list. Every filter on it is ignored.
---

# 023_pages

**Q** What is a page over REST, and can a client read a page's settings and its visible columns?

**Endpoint** `GET /entity/pages ; POST /entity/page_settings/_search ; GET /schema/PageSetting/fields`

**Docs claim** Silent. The REST docs list no page endpoint and describe no layout format.

**Actual**

```
/schema matched 3 of 114 type names: Page, PageHit, PageSetting
Page 24 fields, PageHit 5, PageSetting 6 (page, user, settings_json, ...); /schema/DisplayColumn -> 404 "Entity type 'DisplayColumn' does not exist."

GET /entity/pages paged                       1217   project set 1092   project null 125
_search [["project","is",null]]                 125   GET filter[project.Project.id]=<id> -> 59
GET filter[project]=null -> 400  API read() Page.project expected [Hash, ... NilClass] data type(s) but got String: "null"
_summarize record_count, no filter             2576   against 1092 over 22 projects + 125 null = 1217

/schema/PageSetting/fields/settings_json data_type "text"; returned decoded, never as a string
1217 of 1217 listed pages have >=1 PageSetting, the 125 site-level ones included;
  (settings_json shape, user set) -> {(object, false): 1219, (array, true): 27}

one shared PageSetting (user null), page_type "canvas", entity_type "Shot", 126 widgets in the tree:
  /                   SG.Widget.Canvas.Page
  /body               SG.Widget.EntityQuery.EntityQueryPage  settings=[entity_type,filters,grouping,mode,sorts,pivot_grouping,formatting_rules,...]
  /body/list_content  SG.Widget.NewGrid                      settings=[columns,column_widths,column_display_names,records_per_page,...]
  body.settings  entity_type "Shot"  mode "list"  sorts [{"column":"code","direction":"asc"}]
                 grouping [{"column":"sg_sequence","method":"exact","direction":"asc"}]
                 filters {"logical_operator":"and","conditions":[...{"path":"sg_status_list","relation":"is","values":["wtg"],"active":"true"}...],"filter_name":"<saved filter>","filter_id":2}
  list_content.settings.columns ["image","sg_status_list","code","sg_sequence","description","created_by"]
GET /entity/shots?fields=<those columns verbatim> -> 200  attributes [code,description,image,sg_status_list]  relationships [created_by,sg_sequence]
GET /entity/shots?fields=code,zzz_not_a_field -> 200  attributes [code]   (unknown name dropped, no error)

a per-user row is an array of patches, not a tree, 27 of 27 user-owned:
  [{"spec_path":"body|list_content","settings":{"columns":[...],"column_widths":{...}}}]

PageSetting baseline 30145. contains "ZZZNOPE" 30145, is null 30145, is_not null 30145,
  starts_with "ZZZNOPE" 30145, in ["ZZZNOPE"] 30145; control [["page","is",null]] -> 26372
Page.name    -> 400 ... Valid relations: ["contains","not_contains","is","is_not","starts_with","ends_with","in","not_in"]
Page.project -> 400 ... Valid relations: ["is","is_not","name_contains","name_not_contains","name_is","type_is","type_is_not","in","not_in"]
```

**Teaches**

Three types answer the question, and a page's configuration is split across two of them.

| type | what it holds | how a client reaches it |
|---|---|---|
| `Page` | the page itself: `name`, `page_type`, `entity_type`, `project`, `ui_category`, `system_owned` | `GET /entity/pages?fields=...` |
| `PageSetting` | the layout, in `settings_json` | `_search` on `page is {"type":"Page","id":N}` |
| `PageHit` | one row per view, `page` and `user` only | `GET /entity/page_hits` |

There is no `DisplayColumn` type, and `Page` has no field naming a column.

- A site-level page is a `Page` whose `project` is null, and nothing else about it differs. Both kinds
  read from the same endpoint, both hold `PageSetting` rows of the same shape, and both take the same
  filters. The two are told apart by `project` alone, so `filter[project.Project.id]=N` returns a
  project's pages and `[["project","is",null]]` returns the site-level ones. Send the string `"null"`
  to the flat filter and it 400s with `got String: "null"`; the operator wants a real null.
- `PageSetting.settings_json` is `text` in the schema and decoded JSON in the response, so parse nothing.
  Two shapes come back under one field: an object is the page's shared layout and its `user` is null,
  an array is one user's override and its `user` is set. Read `[["page","is",{...}],["user","is",null]]`
  to get the shared one and ignore the rest, or a personal column order will read as the page's.
- The shared layout is a widget tree of `{type, settings, children}`. `children.body.settings` holds
  `entity_type`, `mode`, `sorts`, `grouping` and `filters`; `children.body.children.list_content.settings`
  holds `columns` in display order, plus `column_widths` and `column_display_names`. The override array
  is `[{spec_path, settings}]`, where `spec_path` is that same tree path with `|` between the segments,
  so `body|list_content` patches the grid.
- `columns` are schema field names, usable in `?fields` as they stand, and a dotted path such as
  `created_by.HumanUser.email` appears among them. Some are stale or web-only: on the probed site, 5 of
  the 21 list pages in one project named a column absent from that type's `/schema/<Type>/fields`.
  `?fields` answers 200 and drops a name the type does not have, so a stale column costs a missing key
  rather than an error. Check the list against `/schema/<Type>/fields` to know which columns you lost.
- `filters` is the web condition tree (`path`, `relation`, `values`, `logical_operator`), not the
  `_search` array of probe 017. The names line up, so a converter is a walk over `conditions`, but the
  tree also holds `active`, `filter_name` and `filter_id` for a saved filter, and a
  `top_level_project_filter` condition that duplicates the project scope.
- Every filter on `settings_json` is accepted and ignored. On the probed site all 30145 rows come back
  for `contains "ZZZNOPE"`, for `is null` and for `is_not null` alike, while `[["page","is",null]]`
  on the same type returns 26372, so the endpoint filters fine and the field does not. Never search
  layouts server-side; page the rows and inspect them yourself.
- `_summarize` disagrees with the listing on `Page`. On the probed site an unfiltered `record_count`
  returned 2576 against 1217 rows actually paged, while the same count filtered by project agreed
  exactly, summing to 1217 over 22 projects plus 125 project-null. Count pages by summing per-project
  and per-null, never with one unfiltered call.
- `Page` and `PageSetting` filter and sort like any other type: the bogus-operator 400 enumerates the
  normal relations for each field's data type, and `sort` on a name that is not a field is accepted at
  200 and ignored.
