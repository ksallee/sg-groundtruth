---
tags: [schema, custom-field, page, discovery]
endpoints: [POST /entity/<type>/_search]
phase: schema
scope: api
measured: site-wide, 20 Page rows read, 2026-11-10
coverage: partial
unmeasured: the web address itself. `/page/<id>` is the web interface's scheme, not a REST call, and it was not opened. Blocked on the work: it needs a browser session.
verdict: The page that lists retired fields is a Page row: `ui_category` "trash", `entity_type` "DisplayColumn", named "Trash - Fields". Its id is per site, so search for it.
---

# 120_field_trash_page

**Q** Where is the web page that lists retired fields, the one a person empties to free a name?

**Endpoint** `POST /entity/pages/_search`

**Docs claim** Silent. The create refusal says "Delete the retired field forever from the Trash Page
in Shotgun" and gives no address.

**Actual**

```
POST /entity/pages/_search  [["ui_category", "is", "trash"]] -> 200, 20 pages
  page_type {canvas: 20}; with a project: 0; system_owned {False: 3, True: 17}; created by HumanUser: 20
  name 'Trash - Fields'    entity_type DisplayColumn  system_owned False
  name 'Trash - People'    entity_type HumanUser      system_owned False
  name 'Trash - Projects'  entity_type Project        system_owned False
  name 'Trash - Pages'     entity_type Page           system_owned True
  name 'Trash - Versions'  entity_type Version        system_owned True
  ... 15 more, one per entity type
the same with ["entity_type", "is", "DisplayColumn"] -> 200, 1 page: 'Trash - Fields', canvas
GET /schema/DisplayColumn -> 404 "Entity type 'DisplayColumn' does not exist."
GET /entity/display_columns -> 404 "Entity type 'display_columns' does not exist."
```

**Teaches**
- On the probed site there is one trash page per entity type that has been trashed from, each a
  site-level `Page` row with no project. The one for fields has `entity_type` `DisplayColumn`, the
  type a field's own row has in the event log (`Shotgun_DisplayColumn_Retirement`).
- Find it with `filters: [["ui_category", "is", "trash"], ["entity_type", "is", "DisplayColumn"]]`.
  The id differs per site. All 20 rows were created by a person, so a site where nobody has opened
  the field trash may have no row: handle zero results by describing the menu path in words.
- The address is `<site>/page/<id>`. That is the web interface's scheme for a `Page` row and is
  inferred here, not measured: no REST call opens a page.
- `DisplayColumn` is not reachable over REST as a type, so the retired fields themselves stay
  unlistable (probe 114). The page is the only place they are shown.
