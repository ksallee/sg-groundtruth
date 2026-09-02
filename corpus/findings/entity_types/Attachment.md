---
tags: [entity-type, attachment, upload, media, url, multi-entity, create, status, trap]
scope: api
summary: A file held on the site, linked to the rows it belongs to.
verdict: POST /entity/attachments answers 201 on an empty body and returns a row with no file; this_file is editable on create only, so bytes reach a site through the upload dance and never through a create.
---

# Attachment

**Type** Schema name `Attachment`, REST path slug `attachments`. The slug is neither case nor plural
sensitive, and only an unknown name is refused.

| path | result |
|---|---|
| `GET /entity/attachments` | 200 |
| `GET /entity/attachment`, `GET /entity/Attachment` | 200, the same rows; `links.self` normalises to `/api/v1/entity/attachments/<id>` |
| `GET /entity/attachmentss` | 404 `Entity type 'attachmentss' does not exist.` |

Project-scoped, loosely. `Attachment.project` is an editable `entity` field, `valid_types: ['Project']`,
flagged neither mandatory nor unique, and it is not always set: on the probed site 437 of a 500-row page
had one. An unfiltered `_search` returns attachments from every project, so filter on `project` for a
per-project read and expect the unparented rows to be invisible to it.

**Identity** `display_name` is the field a human reads. There is no `name` field: it is absent from
`/schema/Attachment/fields`. Nothing on Attachment is flagged `unique`, and the only field flagged
`mandatory` is `this_file`, which a create does not enforce.

| field | display name | data type | editable |
|---|---|---|---|
| `display_name` | `File Display Name` | text | yes |
| `cached_display_name` | `Cached Display Name` | text | yes |
| `description` | `Description` | text | yes |
| `original_fname` | `Original Filename` | text | yes |
| `filename` | `File Name` | text | no |
| `file_extension` | `File Type` | text | no |
| `file_size` | `File Size` | number | no |

The three read-only ones are refused on create and on update alike, at 400 code 103 with an empty `source`:

```
POST /entity/attachments  {"filename": "probe.png"}
  -> "API create() Attachment.filename is read only."
PUT  /entity/attachments/<id>  {"file_size": 1}
  -> "API update() Attachment.file_size is read only."
```

**Create** `POST /entity/attachments` exists and succeeds, and what it produces is a row with no file on
it. Bytes still go up through the three-call dance of probe 013 and probe 014.

| body sent | result |
|---|---|
| `{}` | 201, `this_file` null, `filename` null, `sg_status_list` `"na"` |
| `{"project": {"type": "Project", "id": N}}` | 201, the same empty row |
| `{"filename": "probe.png"}` | 400 `API create() Attachment.filename is read only.` |
| `{"project": …, "filename": "probe.png"}` | 400, the same message |
| `{"project": …, "attachment_links": [{"type": "Version", "id": N}]}` | 201, linked, still no file |
| `{"project": …, "this_file": {"url": "https://example.com/probe.png", "name": "probe.png"}}` | 201, `link_type` `web`, `display_name` and `cached_display_name` set from `name` |

`this_file` is the only key on a create that produces a usable row, and it takes the `url` object of
`field_types/url`: a `{url, name}` hash, never a string. A second write is refused with
`API update() Attachment.this_file is editable on create only.`, so a row created empty stays empty and
the only fix is to delete it and create another.

What the upload dance fills in, measured on one sandbox Version after step 3 answered 201:

| field | at the 201 | 40s later |
|---|---|---|
| `filename`, `display_name`, `cached_display_name`, `original_fname` | the uploaded filename | unchanged |
| `this_file` | `link_type` `upload`, `content_type` `image/png` | unchanged |
| `processing_status` | `thumbnail_pending_us` | `null` |
| `file_extension`, `file_size` | `null` | `null` |

**Links** Every link is written and read as `field_types/entity` and `field_types/multi_entity` describe.

| field | data type | `valid_types` | editable |
|---|---|---|---|
| `attachment_links` | multi_entity | site configuration, see below | yes |
| `attachment_reference_links` | multi_entity | `['Asset', 'Scene', 'Sequence', 'Shot', 'Version']` | yes |
| `project` | entity | `['Project']` | yes |
| `local_storage` | entity | `['LocalStorage']` | no |
| `image_source_entity` | entity | every entity type on the site | no |
| `notes` | multi_entity | `['Note']` | yes |
| `open_notes` | multi_entity | `['Note']` | no |
| `tags` | multi_entity | `['Tag']` | yes |
| `task_template` | entity | `['TaskTemplate']` | yes |
| `created_by`, `updated_by` | entity | `['HumanUser', 'ApiUser']` | no |

`attachment_links` is the one a client uses, and its `valid_types` is site configuration: read it, never
hardcode it. On the probed site it names eleven types, one of them a custom entity slot:
`['Asset', 'Scene', 'Sequence', 'Shot', 'Version', 'CustomEntity02', 'ShootDay', 'Note', 'Delivery',
'PipelineConfiguration', 'Launch']`. Read the attachments of one entity with a `_search` body, which is
the only place a `{type, id}` hash can be expressed; the flat form 400s (probe 014).

```
POST /entity/attachments/_search   Content-Type: application/vnd+shotgun.api3_array+json
{"filters": [["attachment_links", "is", {"type": "Version", "id": <id>}]],
 "fields": ["display_name", "this_file"]}
```

`this_file` is a `url` field, read only, and its keys depend on `link_type`. All three shapes and the
per-read presigned url are in `field_types/url`; a `local` value has no `url` key at all.

**Status** Two independent fields, neither of them a workflow status a client should set.

| field | data type | editable | vocabulary |
|---|---|---|---|
| `sg_status_list` | status_list | yes | site configuration; on the probed site `['fin', 'na']`, `default_value` `na`, `hidden_values` empty at site and project scope |
| `processing_status` | list | no | `['thumbnail_pending', 'unverified', 'clean', 'infected']` |

**Traps**
- A create with an empty body answers 201. A request that dropped its payload leaves a real Attachment row
  with no file, no filename and no link, and it cannot be repaired: `this_file` is create-only.
- `file_extension` and `file_size` do not fill in. On the probed site, over a 500-row page, `file_size` was
  set on 130 rows and `file_extension` on 85, all created between 2013 and 2019; every row created 2025 or
  later read null on both, some of them more than a year old. Take the size from the bytes you uploaded and
  the extension from `filename`. Probe 014's null columns are the steady state, not a race.
- `processing_status` returns `thumbnail_pending_us` straight after an upload, which is not one of the four
  values its own `valid_values` declares, and it reverts to `null` once transcoding finishes. A client
  matching against `valid_values` sees an unknown token, then nothing.
- Reading `attributes` alone shows no links: `attachment_links`, `project` and `local_storage` are all
  returned under `relationships` (probe 004).
