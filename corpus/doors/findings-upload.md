# Findings — upload: getting bytes in and out

How the API behaves in this part of a session. Each rule is the entry's own **Teaches**, copied whole.

## 013_upload_media

Media upload is three calls: GET `{field}/_upload`, PUT the bytes, POST `links.complete_upload`. Transcoding is async: poll until the field stops reading `/images/status/transient/`.

- Step 3 takes `{"upload_info": <the data block from step 1, verbatim>, "upload_data": {}}` and answers 201. `upload_data` must be present even though it is an empty dict; omitting it is reported to 400 with `upload_data is missing`, but this probe always sends it, so that error body is `<unverified>` here.

- The field in the path sets `upload_type`:

  | field in the `_upload` path | `upload_type` |
  |---|---|
  | `image` | `Thumbnail` |
  | any other field | `Attachment` |
  | no field at all | `Attachment` (probe 014) |

- Transcoding is async. Reading the field straight back returns a placeholder under `/images/status/transient/`, so a client must test for that path prefix rather than treat the value as media. Once transcoded, `image` is a plain presigned URL and `sg_uploaded_movie` a dict with `url` (probe 021).

`corpus/findings/013_upload_media.md`

## 014_attach_file

Leave the field out of the _upload path and the file is stored as an Attachment on attachment_links; read it back with POST /entity/attachments/_search, never flat filter[].

- The field in the path picks the upload type: omit it and `upload_type=Attachment`, giving an Attachment entity reachable through `attachment_links`. The three steps are otherwise those of media (probe 013).

- The Content-Type is per endpoint, never per site:

  | endpoint | Content-Type |
  |---|---|
  | `complete_upload` | `application/json`; the vendor type 415s |
  | `_search`, `_summarize` | `application/vnd+shotgun.api3_array+json` or `...api3_hash+json`; `application/json` 415s (probe 004) |

- A multi-entity field cannot be filtered by flat `filter[]` params: 400 `API read() invalid/missing entity hash: "Version"`. It needs a `{type, id}` hash, and only a `_search` body can express one.

- The same message, with the offending value in place of `"Version"`, answers a bare id inside a `_search` body: `API update() invalid/missing entity hash: 26332` on write, `in [A]` bare int 400 `invalid/missing entity hash: 26342` on filter (field_types/multi_entity).

- Probe 017 records a different message, `invalid/missing entity hash string 'type'`, returned when the hash is present but has no `type` key.

- This run's step 3 failed, so it created nothing. On the probed site the three attachments listed are from earlier runs, and this finding does not itself verify that a completed upload appears in that list.

`corpus/findings/014_attach_file.md`

## 022_sequence_on_version

sg_uploaded_movie is single-valued, and replacing it leaves sg_uploaded_movie_mp4 describing the old file while status reads 1. A sequence belongs in sg_path_to_frames.

- A sequence cannot be media. Put the `%04d` pattern in `sg_path_to_frames` and upload one transcoded movie for the review player.

- Replacing `sg_uploaded_movie` does not invalidate its derived fields: `sg_uploaded_movie_mp4` keeps serving a transcode of the file you replaced. A player trusting it shows the wrong content.

- `sg_uploaded_movie_transcoding_status` = 1 means *a* transcode finished, not that the *current* media is transcoded. `sg_uploaded_movie_frame_rate` disagrees: 25.0 for the still, 8.0 for the real movie.

- `sg_uploaded_movie_webm` was never populated on the probed site, at status 1 or before; do not wait on it. Poll `_mp4` instead, since transcoding is async (probe 013).

- Attachments accumulate and media does not: five uploads to one Version left five Attachments linked while `sg_uploaded_movie` held one file. Frames parked as Attachments are storage, never review. `PublishedFile` is the right home for the sequence, still unproven (probe 021).

`corpus/findings/022_sequence_on_version.md`

## 039_upload_silent_failures

complete_upload returns 201 and creates an Attachment even when the bytes were never PUT, and file_size is null on a good upload too, so only fetching the stored file proves it exists.

| do | why |
|---|---|
| Check the PUT's own status code | it is the only step that proves the bytes reached S3 |
| Post to `links.complete_upload` verbatim | `/api/v1` is already on it, and prefixing again is a 404 with a null `source` |
| Never parse the `complete_upload` body | it is one space, and `.json()` raises after the write landed |
| Read the new id by diffing the parent's attachments before and after | `complete_upload` does not return it |
| Never treat `file_size` as proof of content | it is `null` on a good upload |

To verify an upload actually holds bytes, fetch `this_file.url` and check the status. Nothing on the
Attachment row answers it.

`corpus/findings/039_upload_silent_failures.md`

## 044_multipart_upload

`multipart_upload=true` on the init sets `upload_id` and adds `links.get_next_part`. Every part but the last must be at least 5 MiB, and completion needs an `etags` array inside `upload_info`.

- The switch is a query parameter on the init, not a file size. Nothing in the API refuses a
  single-PUT upload for being large, so a client decides for itself when to split.

- **The init opens the S3 upload.** `upload_id` is non-null the moment `multipart_upload=true`
  returns, before any byte moves. An init you neither complete nor abort leaves an open multipart
  upload on storage that nothing in Flow PT lists. Abort every init you abandon.

  | parts sent | completion |
  |---|---|
  | one part, any size | 201 |
  | 5242880 bytes then 17 | 201 |
  | 5242879 bytes then 17 | 400 `Error completing multipart upload.` |
  | 1024 bytes then 1024 | 400 `Error completing multipart upload.` |

  5242880 is 5 MiB, the S3 floor on every part but the last. The 400 does not say so. A one-part
  multipart upload is legal and has no floor, so the smallest transfer that exercises the whole flow
  is a single part of a few bytes.

- Walk `links.get_next_part`, do not build it. Each call answers with the next part's `upload` and
  the `get_next_part` after it, incrementing `part_number`. The chain is the only thing that knows
  which part is next.

- Collect the `ETag` response header of every part PUT, in order, and send them as
  `upload_info.etags` at completion. `upload_info` is otherwise the init reply verbatim.

- The abort takes the `upload_info` object **flat at the top level**, not wrapped in `upload_info`.
  The wrapped body the spec declares returns 400 naming all six keys as missing.

`corpus/findings/044_multipart_upload.md`
