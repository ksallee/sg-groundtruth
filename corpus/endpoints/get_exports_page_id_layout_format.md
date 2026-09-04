---
endpoint: GET /exports/page/<page_id>/<layout_name>.<format>
coverage: measured
tags: [page]
scope: api
measured: sample project 1 of 1, read only
verdict: The same export addressed at one named view, needed when a page has several. A layout name that does not exist is indistinguishable from one that does, because both answer the page-level 422.
---

# GET /exports/page/<page_id>/<layout_name>.<format>

**Params**

| part | value |
|---|---|
| `<page_id>` | a `Page` id |
| `<layout_name>` | the view name as it reads in the web interface |
| `<format>` | `csv` per the spec. As on the default-view export, the extension is not validated |

**Sample requests**

```python
c.get("/exports/page/3074/Shots.csv").status_code                    # 422
c.get("/exports/page/3074/Shots.csv").text
# 'Export for Page id=3074 not available'
```

A layout name that does not exist answers the same thing:

```python
c.get("/exports/page/3074/zzprobe_048_not_a_view.csv").text
# 'Export for Page id=3074 not available'
```

**Response codes**

| status | when |
|---|---|
| 200 | the named view is marked exportable. Not reproduced on the probed site |
| 422 | `Export for Page id=3074 not available` |

**Edge cases**

| you send | result |
|---|---|
| a real view name | 422 on a page whose export is off |
| a name no view has | 422, the same body |
| the page id alone | see `endpoints/get_exports_page_id_format` |

- The 422 names the page, never the layout, so this endpoint reports nothing about whether the view
  exists. A typo in `<layout_name>` and a page with export disabled are the same response.
- Use this form only when a page has more than one view. The default view answers on
  `/exports/page/<page_id>.<format>`.
- `PageSetting.settings_json` holds the page's saved views (`findings/023_pages`) but not their
  exportable flag, so the view name a client sends has to come from the web interface.

**Links**

- `endpoints/get_exports_page_id_format`
- `findings/023_pages`
