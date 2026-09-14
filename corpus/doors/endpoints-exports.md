# Endpoints — Exports

Every call in this family: what the card records, the edge cases that live on the call, and the verdict of every entry that measured it. Each of those lines names the door holding that entry's rules. The map is `corpus/INDEX.md`.

## `GET /exports/page/<page_id>.<format>`

Exports a page's default view. Off unless a site admin marked the view exportable: on the probed site all 52 pages sampled answered 422, and no field says which pages will work.

| you send | result |
|---|---|
| `3074.csv` | 422, `text/csv` |
| `3074.json`, `3074.xml`, `3074.txt` | 422, `application/json`, `application/xml`, `text/plain` |
| `3074` | 404 |
| `999999999.csv` | 422, reported as retired |
| `abc.csv` | 422, reported as `id=0` |

- Two failures share one status and read alike: a page that is not there and a page whose view is not
  marked exportable. A missing id is called retired, so the message does not separate them.

- Enabling the export is a per-view setting in the web interface. `Page` has no field for it and it is
  not in the layout `settings_json` (`findings/023_pages`), so the only way to know a page exports is
  to call this endpoint.

- On the probed site 52 pages spanning all 27 `page_type` values answered 422 and none answered 200.
  A client cannot rely on this endpoint without the site confirming a view is enabled.

**Measured by**

- `048_one_record_beyond_crud` (findings) — POST on one record is revive, not update: `?revive=1` is required and the body is ignored. `/<field>` reads image and attachment fields only, and `relationships/<field>` is the same data, unpaged.  
  rules: `doors/findings-read`

**Silent on this call**

- `048_one_record_beyond_crud` — POST on one record is revive, not update: `?revive=1` is required and the body is ignored. `/<field>` reads image and attachment fields only, and `relationships/<field>` is the same data, unpaged.

`corpus/endpoints/get_exports_page_id_format.md`

## `GET /exports/page/<page_id>/<layout_name>.<format>`

The same export addressed at one named view, needed when a page has several. A layout name that does not exist is indistinguishable from one that does, because both answer the page-level 422.

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

**Measured by**

- `048_one_record_beyond_crud` (findings) — POST on one record is revive, not update: `?revive=1` is required and the body is ignored. `/<field>` reads image and attachment fields only, and `relationships/<field>` is the same data, unpaged.  
  rules: `doors/findings-read`

**Silent on this call**

- `048_one_record_beyond_crud` — POST on one record is revive, not update: `?revive=1` is required and the body is ignored. `/<field>` reads image and attachment fields only, and `relationships/<field>` is the same data, unpaged.

`corpus/endpoints/get_exports_page_id_layout_format.md`
