---
tags: [on-set, upload, attachment, image, url, published-file]
endpoints: [GET /entity/<type>/<id>/<field>/_upload, GET /entity/<type>/<id>/_upload, PUT <links.upload>, POST <links.complete_upload>, POST /schema/<Type>/fields, PUT /entity/<type>/<id>, POST /entity/<type>/_search, GET /schema/<Type>/fields/<field>]
phase: upload
scope: api
measured: sandbox project written, 2026-11-11; three 6000x4000 JPEGs (7.7 MB); two Slate fields created and retired
coverage: partial
unmeasured: completing a field-less upload on Slate and reading where it links; the web interface itself. Blocked on the work
verdict: `image` keeps only a 480x320 thumbnail. A url field holds one original, a Note's attachments or a multi_entity to Attachment hold many; all return the bytes unchanged.
---

# 123_photos_per_record

**Q** Where can several full-resolution photos per record live, on the on-set types and on a custom
entity, and which of the places keeps the original? Does Version have `attachments`?

**Endpoint** `GET /entity/<type>/<id>/<field>/_upload ; GET /entity/<type>/<id>/_upload ; PUT <links.upload> ; POST <links.complete_upload> ; POST /schema/<Type>/fields`

**Docs claim** Silent on what is kept of an uploaded image and on which types take a field-less
upload.

**Actual**

```
attachments field: Note only. Absent on Slate, Camera, MocapTake, ShootDay, Scene, the custom slot,
  Version, Shot, PublishedFile.  GET /schema/Version/fields/attachments -> 404
  "Field 'Version.attachments' does not exist."
GET /entity/<type>/<id>/_upload (no field): 200 on all ten types above
Version: field-less upload 201, one Attachment with attachment_links [Version];
  GET /entity/versions/<id>?fields=attachments -> 200, no such key returned

a. Slate.image, photo1 then photo2   each 201; image -> JPEG 480x320, ~51 KB, not the original
   no Attachment row made; filmstrip_image null
b. POST /schema/Slate/fields url "zzprobe 123 photo"             -> 201
   upload photo1, then photo2 -> {"name": ..., "content_type": "image/jpeg",
     "link_type": "upload", "type": "Attachment", "id": <n>}; the second replaces the first
   url -> 7.7 MB JPEG 6000x4000, byte-identical, content-type binary/octet-stream
   POST /schema/Slate/fields multi_entity [Attachment]           -> 201
   upload to .../sg_zzprobe_123_photos/_upload -> 201, field holds the Attachment
   PUT the field with three Attachments                         -> 200, holds 3
c. Note note_links [Slate], three field-less uploads            -> Note.attachments 3 rows
   each this_file byte-identical 6000x4000; each Attachment.image a 480x320 thumbnail
   PUT Attachment.attachment_links += the Slate (not in valid_types) -> 200
d. Version entity=Slate, sg_uploaded_movie                      -> byte-identical original;
   image 480x320 after transcode; server adds <hash>_<name>.mp4 and _2Dlod.jpeg Attachments
e. PublishedFile {project, code, entity: Slate}                 -> 201 (valid_types lacks Slate)
   path upload -> byte-identical original; image stays null
```

**Where several photos can live**

| place | photos per record | original kept | read back | in the web interface, from the schema |
|---|---|---|---|---|
| a. `image` | one; a new upload replaces it | **no**: 480x320 JPEG | `image`, a presigned URL | the record's thumbnail |
| b. custom `url` field | one per field | yes, byte-identical | `<field>.url`, presigned; `<field>.id` is the Attachment | a File/Link column |
| b. custom multi_entity to Attachment | many | yes | the field's Attachment ids, then `this_file.url` | a column of file links |
| c. Note `attachments`, Note linked to the record | many per Note | yes, plus a 480x320 `image` | Notes by `note_links`, then `attachments` | a Note on the record's activity and Notes |
| d. one Version per photo | one per Version | yes on `sg_uploaded_movie`, plus thumbnail and transcodes | Versions by `entity` | Versions, with a thumbnail each |
| e. one PublishedFile per photo | one per row | yes on `path` | PublishedFiles by `entity` | Published Files, no thumbnail |

**Teaches**
- Never put a photo that must survive on `image`: the server keeps a 480x320 rendition and no
  Attachment row, and no REST call returned the original.
- Every other place keeps the exact bytes and answers them at the presigned URL as
  `binary/octet-stream`, signed for 900 s (probe 125). Store the Attachment id, not the URL.
- Only Note has a stock `attachments` field. Version has none (schema 404), which settles the
  contradiction in the upload cards: a field-less upload on Version links through
  `Attachment.attachment_links` (probe 014). Field-less init answers 200 on every type tried.
- For many photos per take with no admin step, use a Note per take or batch; with one schema write,
  a multi_entity to Attachment on the take type. A Version per photo costs a transcode and two extra
  Attachments each. `valid_types` is not enforced on `PublishedFile.entity` or `attachment_links`.
