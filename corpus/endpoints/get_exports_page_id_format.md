---
endpoint: GET /exports/page/<page_id>.<format>
coverage: measured
tags: [page, error-handling]
scope: api
measured: sample project 1 of 1, plus 52 pages sampled site-wide, read only
verdict: Exports a page's default view. Off unless a site admin marked the view exportable: on the probed site all 52 pages sampled answered 422, and no field says which pages will work.
---

# GET /exports/page/<page_id>.<format>

**Params**

| part | value |
|---|---|
| `<page_id>` | a `Page` id. Non-numeric is read as `0` |
| `<format>` | `csv` per the spec. The extension is not validated and sets the response `Content-Type` |

**Sample requests**

```python
r = c.get("/exports/page/3074.csv")
r.status_code, r.headers["Content-Type"], r.text
# 422 'text/csv; charset=utf-8' 'Export for Page id=3074 not available'
```

The body is plain text at every status, never a JSON:API error object, even when the extension makes
the header say otherwise:

```python
c.get("/exports/page/3074.json").headers["Content-Type"]   # 'application/json; charset=utf-8'
c.get("/exports/page/3074.json").text                      # 'Export for Page id=3074 not available'
```

A page id that is not there:

```python
c.get("/exports/page/999999999.csv").text
# 'Trying to perform export for retired Page id=999999999'
c.get("/exports/page/abc.csv").text
# 'Trying to perform export for retired Page id=0'
```

Drop the extension and the route stops matching:

```json
{"errors": [{"status": 404, "code": 103, "title": "Not Found",
             "source": null, "detail": null}]}
```

The spec's own example of a 200 body:

```
Id,Thumbnail,Shot Code,Sequence,Status,Cut In,Cut Out,Cut Duration,Type,Project
```

**Response codes**

| status | when |
|---|---|
| 200 | the view is marked exportable. Not reproduced on the probed site |
| 404 | no extension, code 103, `detail` null |
| 422 | `Export for Page id=3074 not available` |
| 422 | `Trying to perform export for retired Page id=999999999` |

**Edge cases**

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

**Links**

- `endpoints/get_exports_page_id_layout_format`
- `endpoints/get_entity_type`
- `findings/023_pages`
