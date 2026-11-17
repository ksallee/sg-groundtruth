---
tags: [attachment, custom-field, upload, on-set, trap]
endpoints: [POST /schema/<Type>/fields, GET /entity/<type>/<id>/_upload, POST <links.complete_upload>, PUT /entity/<type>/<id>, POST /entity/<type>/_search]
phase: upload
scope: api
measured: sandbox project written, 2026-11-11; one Note, three Attachments; one text field created on Attachment and retired
verdict: Attachment takes a custom field over REST. `filename` keeps 90 and 200 characters but stores each space as `_`; `is` and `starts_with` ignore case, so filter on the name with `_` for spaces.
---

# 135_attachment_custom_field_filename

**Q** Can a custom field be created on Attachment over REST, is `Attachment.filename` kept verbatim at
about 90 characters, and do `is` and `starts_with` filters match on it?

**Endpoint** `POST /schema/Attachment/fields ; GET /entity/notes/<id>/_upload ; POST /entity/attachments/_search`

**Docs claim** Silent on both. The schema flags `Attachment.filename` a `text` field, `editable: false`.

**Actual**

```
POST /schema/Attachment/fields text "zzprobe 135 note"   -> 201 sg_zzprobe_135_note
PUT /entity/attachments/<id> {"sg_zzprobe_135_note": ...} -> 200

field-less upload to one Note; the init echoed each original_filename unchanged
  sent 90 chars  zzprobe_135_A001C002_take03_2026-11-11T14-22-05.123_xxx…x.jpg
    filename verbatim                                         this_file.name, display_name equal to it
  sent 90 chars  zzprobe_135 B cam take 3 é.ü_xxx…x.jpeg
    filename zzprobe_135_B_cam_take_3_é.ü_xxx…x.jpeg         spaces -> "_", é and ü kept, 90 chars
  sent 200 chars zzprobe_135_long_xxx…x.jpg
    filename verbatim, 200 chars

Valid relations: ["contains", "not_contains", "is", "is_not", "starts_with", "ends_with", "in", "not_in"]
```

**Filter** on `filename`, `project` the sandbox, three rows:

| operator | value | rows |
|---|---|---|
| `is` | the 90-char name | 1 |
| `is` | the same, uppercased | 1 |
| `is` | the name without `.jpg` | 0 |
| `starts_with` | its first 40 characters | 1 |
| `starts_with` | `ZZPROBE_135_A001` | 1 |
| `contains` | `take03_2026` | 1 |
| `ends_with` | its last 20 characters | 2 |
| `is` | the name with spaces, as sent | 0 |
| `starts_with` | `zzprobe_135 B cam take 3 é` | 0 |

**Teaches**
- A custom field on Attachment is creatable and writable by the script, so a capture id can sit on
  the file's own row rather than only in its name.
- `filename` is not always what was sent: each space is stored as `_`, while the `_upload` init
  echoes the original. Replace spaces with `_` before looking a file up by name, or keep the client's
  name in a custom field. Non-ASCII letters and 200 characters are kept.
- Text matching on `filename` ignores case, as on every text field (`field_types/text`): a client that
  names two files differing only in case cannot tell them apart by filter.
