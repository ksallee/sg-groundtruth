# Endpoints — Media

Every call in this family: what the card records, the edge cases that live on the call, and the verdict of every entry that measured it. Each of those lines names the door holding that entry's rules. The map is `corpus/INDEX.md`.

## `GET /entity/<type>/<id>/<field>/_upload`

Step one of three. `filename` is a required query parameter and its absence is 400 `filename is missing`; the reply holds `links.upload` and a `links.complete_upload` already prefixed with `/api/v1`.

- `links.complete_upload` is the **same path** as this call, differing only by method, and it comes back
  with `/api/v1` already on it. A client that prefixes it again gets 404 with `source: null`, which reads
  as "this is not a valid upload target" rather than "your URL is wrong".

- `upload_type` is derived from the field and the filename: `Thumbnail` for `image`, `Attachment` for
  the fieldless form. Nothing in the request names it.

- `data` is the `upload_info` that step three needs. Keep the whole object rather than picking keys out
  of it.

**Measured by**

- `013_upload_media` (findings) — Media upload is three calls: GET `{field}/_upload`, PUT the bytes, POST `links.complete_upload`. Transcoding is async: poll until the field stops reading `/images/status/transient/`.  
  rules: `doors/findings-upload`
- `022_sequence_on_version` (findings) — sg_uploaded_movie is single-valued, and replacing it leaves sg_uploaded_movie_mp4 describing the old file while status reads 1. A sequence belongs in sg_path_to_frames.  
  rules: `doors/findings-upload`
- `044_multipart_upload` (findings) — `multipart_upload=true` on the init sets `upload_id` and adds `links.get_next_part`. Every part but the last must be at least 5 MiB, and completion needs an `etags` array inside `upload_info`.  
  rules: `doors/findings-upload`
- `001_publish_version_with_media` (recipes) — Publish a generated image to Flow PT as a Version, with provenance and the workflow attached  
  rules: `doors/recipes`
- `006_media_round_trip` (recipes) — Take media off one Version and put the same bytes on another, which is what every sync, transfer and hand-off does  
  rules: `doors/recipes`
- `013_publish_file_bytes` (recipes) — Publish a file's bytes onto a PublishedFile when the caller has no LocalStorage root to write under  
  rules: `doors/recipes`

`corpus/endpoints/get_entity_type_id_field_upload.md`

## `POST /entity/<type>/<id>/<field>/_upload`

The path behind `links.complete_upload`. `upload_info` is the init reply verbatim, plus an `etags` array when the init was multipart; `upload_data` is where `display_name` and `tags` are set.

- `Error completing multipart upload.` has an empty `source` and no `detail`. The S3 reason behind it,
  a part below 5 MiB among them, is not passed through.

- A 400 here does not close the upload. The parts stay on storage until
  `endpoints/post_entity_type_id_field_upload_multipart_abort` runs.

- `file_size` and `file_extension` read `null` on a 5 MiB two-part upload that downloads intact, so
  neither separates a completed transfer from an abandoned one.

- The reply is one space and never names the Attachment it made. Read the field back for its `id`.

**Measured by**

- `044_multipart_upload` (findings) — `multipart_upload=true` on the init sets `upload_id` and adds `links.get_next_part`. Every part but the last must be at least 5 MiB, and completion needs an `etags` array inside `upload_info`.  
  rules: `doors/findings-upload`

`corpus/endpoints/post_entity_type_id_field_upload.md`

## `PUT /entity/<type>/<id>/<field>/_upload`

The `storage_service: "sg"` upload target, on the Flow PT host. A site on `s3` returns an S3 `links.upload` instead, and calling this route directly is 400 for four missing signature parameters.

- **Read `storage_service` before assuming which host holds the bytes.** `s3` puts `links.upload` on
  Amazon and this route is never called; `sg` puts it here. A client that hardcodes either one breaks
  on the other kind of site.

- Where the single-PUT S3 target answers 200 with an empty body and an `ETag`, this route is declared
  to answer 200 with `data.upload_id` and `links.complete_upload`. Unmeasured: no `sg` site was
  available.

- The four missing parameters are the whole signature. Never construct this URL; use the one the init
  returned.

`corpus/endpoints/put_entity_type_id_field_upload.md`

## `GET /entity/<type>/<id>/<field>/_upload/multipart`

Step two of a multipart transfer, once per part after the first. Walk `links.get_next_part` rather than building it: each reply holds the part's presigned `upload` and the link to the part after.

- `upload_id` is required and is the one parameter the validator does not check for. Omitting it
  produces `Could not generate upload url. Check the site settings.`, which points at site
  configuration and not at the missing parameter.

- **The `upload_id` is never validated.** `upload_id=nope` answers 200 with a presigned URL. Bytes
  PUT to it are accepted and the transfer fails only at completion, with
  `Error completing multipart upload.`

- The last reply in a chain still holds a `get_next_part` for a part that will never exist. Stop when
  the file is exhausted, not when the chain ends.

- `part_number=1` answers 200 as well, minting a second URL for the part the init already covered.

**Measured by**

- `044_multipart_upload` (findings) — `multipart_upload=true` on the init sets `upload_id` and adds `links.get_next_part`. Every part but the last must be at least 5 MiB, and completion needs an `etags` array inside `upload_info`.  
  rules: `doors/findings-upload`

`corpus/endpoints/get_entity_type_id_field_upload_multipart.md`

## `POST /entity/<type>/<id>/<field>/_upload/multipart_abort`

204 and an empty body. The body is the `upload_info` object flat at the top level, not the `{"upload_info": ..., "upload_data": ...}` wrapper the spec declares, which returns 400.

- The five names in the 400 are the parameters the endpoint wants at the top level. `multipart_upload`
  is not among them and sending the whole `data` object satisfies it either way.

- A completion that failed with `Error completing multipart upload.` leaves the upload open. Abort
  after every failed completion, not only after an abandoned one.

- The abort works on a retired record: deleting the row does not close the upload for you.

- `Failed to abort S3 multipart upload` is the answer for an id that was already aborted, was
  completed, or was never multipart. It does not distinguish them, so a second abort is safe to send
  and its 400 proves nothing was left open.

**Measured by**

- `044_multipart_upload` (findings) — `multipart_upload=true` on the init sets `upload_id` and adds `links.get_next_part`. Every part but the last must be at least 5 MiB, and completion needs an `etags` array inside `upload_info`.  
  rules: `doors/findings-upload`

`corpus/endpoints/post_entity_type_id_field_upload_multipart_abort.md`

## `GET /entity/<type>/<id>/_upload`

The same handshake with the field left out of the path, which stores the bytes as an Attachment on `attachment_links` rather than on a field. The type must actually have that field.

- Not every type has `attachments`. Shot does not, and the 404 names the field rather than the route,
  which is the useful half.

- The Attachment row is created by step three, not by this call. Read the parent's `attachments` back to
  learn its id; nothing in this reply names it.

**Measured by**

- `014_attach_file` (findings) — Leave the field out of the _upload path and the file is stored as an Attachment on attachment_links; read it back with POST /entity/attachments/_search, never flat filter[].  
  rules: `doors/findings-upload`
- `039_upload_silent_failures` (findings) — complete_upload returns 201 and creates an Attachment even when the bytes were never PUT, and file_size is null on a good upload too, so only fetching the stored file proves it exists.  
  rules: `doors/findings-upload`
- `001_publish_version_with_media` (recipes) — Publish a generated image to Flow PT as a Version, with provenance and the workflow attached  
  rules: `doors/recipes`
- `008_delivery_progress` (recipes) — Keep a Delivery honest about what a long transfer is doing, including when it is cancelled and when it crashes  
  rules: `doors/recipes`

**Silent on this call**

- `039_upload_silent_failures` — complete_upload returns 201 and creates an Attachment even when the bytes were never PUT, and file_size is null on a good upload too, so only fetching the stored file proves it exists.

`corpus/endpoints/get_entity_type_id_upload.md`

## `POST /entity/<type>/<id>/_upload`

The fieldless completion, `/entity/<type>/<id>/attachments/_upload`. Same body contract as the field form, including `etags` for a multipart init; the row lands on `attachment_links`.

- The field form and this one answer identically apart from `upload_type`, `Thumbnail` against
  `Attachment`. Everything in `endpoints/post_entity_type_id_field_upload` applies here unchanged.

- Not every type has `attachments`. Shot does not; Note and Version do.

- Diff the parent's `attachments` before and after to learn the new id. The 201 body is a space.

`corpus/endpoints/post_entity_type_id_upload.md`

## `PUT /entity/<type>/<id>/_upload`

The fieldless `storage_service: "sg"` upload target. The spec declares only `filename` and `signature`, and the site asks for `user_id`, `user_type` and `expiration` as well.

- The field form and this one reject an unsigned call with the identical `source`. The spec declares
  different required parameters for the two, and the site does not distinguish them.

- On the probed site `storage_service` is `s3` on every init, field form and fieldless alike, so no
  link produced here was exercisable. The 200 shape is what the spec declares, not what was measured.

`corpus/endpoints/put_entity_type_id_upload.md`

## `GET /entity/<type>/<id>/_upload/multipart`

The fieldless part chain, `/entity/<type>/<id>/attachments/_upload/multipart`. Same four checked parameters and the same unchecked `upload_id` as the field form.

- `upload_type` is `Attachment` on this form and `Thumbnail` on `image`. Send back whatever the init
  returned; the chain rejects nothing else.

- The 5 MiB floor on every part but the last is the same here. See `findings/044_multipart_upload`.

`corpus/endpoints/get_entity_type_id_upload_multipart.md`

## `POST /entity/<type>/<id>/_upload/multipart_abort`

The fieldless abort, `/entity/<type>/<id>/attachments/_upload/multipart_abort`. 204 on the flat `upload_info` object, identical to the field form in every respect but the path.

- `endpoints/post_entity_type_id_field_upload_multipart_abort` holds the edge cases; both forms
  answered identically at every input measured.

`corpus/endpoints/post_entity_type_id_upload_multipart_abort.md`

## `POST /transcode/attachment_metadata/<id>`

Records video metadata for media transcoded outside Flow PT. 200 with a body of one space, and none of the six values reads back on the Attachment; only `updated_at` moves.

- **The 404 is not a JSON:API error.** `{"error": "..."}` is a bare string under `error`, with no
  `errors[]` array, no `status`, no `code` and no `source`. A client reading `body["errors"][0]`
  everywhere else raises `KeyError` here.

- `{}` and `{"nope": 1}` both answer 200. Unknown keys are discarded without a word, so a typo in a
  key name looks like a success.

- Nothing the call sets is readable over REST on the Attachment. `width`, `frame_rate` and the rest
  are not Attachment fields, and the row's own `metadata` field stays `null`.

- Pass the Attachment id. A Version id answers `Attachment <id> not found` with the Version's number
  in it, which reads as a missing row rather than a wrong type.

**Silent on this call**

- `post_transcode_attachment_metadata_id` — Records video metadata for media transcoded outside Flow PT. 200 with a body of one space, and none of the six values reads back on the Attachment; only `updated_at` moves.

`corpus/endpoints/post_transcode_attachment_metadata_id.md`

## `POST <links.complete_upload>`

Step three, at 201 with a body of a single space. Not JSON, and it never names the row it created, so parsing it crashes after the write has landed.

- A 201 here proves the handshake completed, not that bytes exist. With step two skipped the row is
  identical and the stored object is empty.

- The 404 for a double-prefixed URL has `source: null`, which reads as "a Note is not a valid upload
  target" rather than "your URL is wrong".

- For a media field the value is not readable yet: transcoding is asynchronous and the field returns a
  placeholder under `/images/status/transient/` until it finishes.

**Measured by**

- `024_read_after_write` (findings) — Every write ignores ?fields. A create returns what you sent plus the server defaults, an update returns the whole record, and neither resolves a dotted path, so re-read for those and after an upload.  
  rules: `doors/findings-write`
- `013_upload_media` (findings) — Media upload is three calls: GET `{field}/_upload`, PUT the bytes, POST `links.complete_upload`. Transcoding is async: poll until the field stops reading `/images/status/transient/`.  
  rules: `doors/findings-upload`
- `014_attach_file` (findings) — Leave the field out of the _upload path and the file is stored as an Attachment on attachment_links; read it back with POST /entity/attachments/_search, never flat filter[].  
  rules: `doors/findings-upload`
- `022_sequence_on_version` (findings) — sg_uploaded_movie is single-valued, and replacing it leaves sg_uploaded_movie_mp4 describing the old file while status reads 1. A sequence belongs in sg_path_to_frames.  
  rules: `doors/findings-upload`
- `039_upload_silent_failures` (findings) — complete_upload returns 201 and creates an Attachment even when the bytes were never PUT, and file_size is null on a good upload too, so only fetching the stored file proves it exists.  
  rules: `doors/findings-upload`
- `001_publish_version_with_media` (recipes) — Publish a generated image to Flow PT as a Version, with provenance and the workflow attached  
  rules: `doors/recipes`
- `006_media_round_trip` (recipes) — Take media off one Version and put the same bytes on another, which is what every sync, transfer and hand-off does  
  rules: `doors/recipes`
- `008_delivery_progress` (recipes) — Keep a Delivery honest about what a long transfer is doing, including when it is cancelled and when it crashes  
  rules: `doors/recipes`
- `013_publish_file_bytes` (recipes) — Publish a file's bytes onto a PublishedFile when the caller has no LocalStorage root to write under  
  rules: `doors/recipes`
- `002_complete_upload_without_bytes` (reports) — POST links.complete_upload answers 201 and creates an Attachment when the presigned PUT never happened, and nothing on the row separates it from a good upload.  
  rules: `doors/reports`

**Silent on this call**

- `post_links_complete_upload` — Step three, at 201 with a body of a single space. Not JSON, and it never names the row it created, so parsing it crashes after the write has landed.
- `024_read_after_write` — Every write ignores ?fields. A create returns what you sent plus the server defaults, an update returns the whole record, and neither resolves a dotted path, so re-read for those and after an upload.
- `039_upload_silent_failures` — complete_upload returns 201 and creates an Attachment even when the bytes were never PUT, and file_size is null on a good upload too, so only fetching the stored file proves it exists.

`corpus/endpoints/post_links_complete_upload.md`

## `PUT <links.upload>`

Step two, to storage rather than to Flow PT, with no Authorization header. It is the only step that moves bytes, and skipping it still lets step three answer 201.

- **Skipping this step is not detected.** Going straight from step one to step three answers 201 and
  creates a real Attachment row over an object that was never written. `file_size` reads `null` for that
  row and for a good one, so it cannot tell them apart: only fetching the stored file proves it exists.

- The URL is presigned and short-lived. Mint it, use it, and never persist it.

- This is the only step that does not go to Flow PT at all.

**Measured by**

- `013_upload_media` (findings) — Media upload is three calls: GET `{field}/_upload`, PUT the bytes, POST `links.complete_upload`. Transcoding is async: poll until the field stops reading `/images/status/transient/`.  
  rules: `doors/findings-upload`
- `014_attach_file` (findings) — Leave the field out of the _upload path and the file is stored as an Attachment on attachment_links; read it back with POST /entity/attachments/_search, never flat filter[].  
  rules: `doors/findings-upload`
- `039_upload_silent_failures` (findings) — complete_upload returns 201 and creates an Attachment even when the bytes were never PUT, and file_size is null on a good upload too, so only fetching the stored file proves it exists.  
  rules: `doors/findings-upload`
- `001_publish_version_with_media` (recipes) — Publish a generated image to Flow PT as a Version, with provenance and the workflow attached  
  rules: `doors/recipes`
- `006_media_round_trip` (recipes) — Take media off one Version and put the same bytes on another, which is what every sync, transfer and hand-off does  
  rules: `doors/recipes`
- `008_delivery_progress` (recipes) — Keep a Delivery honest about what a long transfer is doing, including when it is cancelled and when it crashes  
  rules: `doors/recipes`
- `013_publish_file_bytes` (recipes) — Publish a file's bytes onto a PublishedFile when the caller has no LocalStorage root to write under  
  rules: `doors/recipes`

**Silent on this call**

- `put_links_upload` — Step two, to storage rather than to Flow PT, with no Authorization header. It is the only step that moves bytes, and skipping it still lets step three answer 201.
- `039_upload_silent_failures` — complete_upload returns 201 and creates an Attachment even when the bytes were never PUT, and file_size is null on a good upload too, so only fetching the stored file proves it exists.

`corpus/endpoints/put_links_upload.md`
