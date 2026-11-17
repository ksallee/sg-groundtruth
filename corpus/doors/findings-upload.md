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

## 123_photos_per_record

`image` keeps only a 480x320 thumbnail. A url field holds one original, a Note's attachments or a multi_entity to Attachment hold many; all return the bytes unchanged. **[partial]**

not measured: completing a field-less upload on Slate and reading where it links; the web interface itself. Blocked on the work

- Never put a photo that must survive on `image`: the server keeps a 480x320 rendition and no
  Attachment row, and no REST call returned the original.

- Every other place keeps the exact bytes and answers them at the presigned URL as
  `binary/octet-stream`, signed for 900 s (probe 125). Store the Attachment id, not the URL. That type
  is because these PUTs sent none: a PUT's `Content-Type` is what the GET serves (probe 152).

- The `_2Dlod.jpeg` Attachment of (d) was added for a JPEG; a video on the same field got only the
  `<hash>_<name>.mp4` (probe 151).

- Only Note has a stock `attachments` field. Version has none (schema 404), which settles the
  contradiction in the upload cards: a field-less upload on Version links through
  `Attachment.attachment_links` (probe 014). Field-less init answers 200 on every type tried.

- For many photos per take with no admin step, use a Note per take or batch; with one schema write,
  a multi_entity to Attachment on the take type. A Version per photo costs a transcode and two extra
  Attachments each. `valid_types` is not enforced on `PublishedFile.entity` or `attachment_links`.

`corpus/findings/123_photos_per_record.md`

## 125_upload_host_cors

The presigned upload host answers any Origin with `*`, allows PUT with content-type and exposes `ETag`, so a page can upload, multipart included. A URL is refused after 900 s. **[partial]**

not measured: a real browser run, and a size cap: the largest single PUT sent was 7.6 MB (probe 123). Blocked on the work

- A browser can run the whole upload, multipart included: the ETag that probe 044's completion needs
  is exposed. Probe 062's caveat that a page cannot read `ETag` holds for `/api/v1`, not this host.

- Fetch the upload URL when the bytes are ready to go, not when the photo is taken: it is signed for
  15 minutes. Ask for a fresh `_upload` per attempt; a part chain's `get_next_part` mints the next.

- Send the PUT with `credentials: "omit"` (the `fetch` default for cross-origin is `same-origin`,
  which also omits). `max-age: 0` means every PUT is preflighted.

- Evidence is response headers read by a process, which no CORS rule blocks. A browser applying the
  standard algorithm to these headers allows the calls above; no browser was run.

`corpus/findings/125_upload_host_cors.md`

## 134_attachment_field_second_upload

A second `_upload` to a multi_entity field to Attachment adds: the field holds both. Each Attachment gets the row's `project` and the row in `attachment_links`, so a project filter finds it.

- Upload each photo straight to the field when it is taken. The server appends; a client does not read
  the field and `PUT` the union back, and a client that does `PUT` a bare list there replaces the
  set (recipe 009). Use `multi_entity_update_mode: add` if it ever writes the field itself.

- The Attachment gets the row's `project` without being told, and lists the row in
  `attachment_links` as well as in the field. Either finds a row's files: `attachment_links is
  <row>`, or the field read on the row.

- A multi_entity field to Attachment creates a reverse field on Attachment named
  `<slug>_<field>_<slug>s`, where `<slug>` is the source type's REST slug in singular
  (`custom_entityNN`). Probe 142 covers reverse fields.

`corpus/findings/134_attachment_field_second_upload.md`

## 135_attachment_custom_field_filename

Attachment takes a custom field over REST. `filename` keeps 90 and 200 characters but stores each space as `_`; `is` and `starts_with` ignore case, so filter on the name with `_` for spaces.

- A custom field on Attachment is creatable and writable by the script, so a capture id can sit on
  the file's own row rather than only in its name.

- `filename` is not always what was sent: each space is stored as `_`, while the `_upload` init
  echoes the original. Replace spaces with `_` before looking a file up by name, or keep the client's
  name in a custom field. Non-ASCII letters and 200 characters are kept.

- Text matching on `filename` ignores case, as on every text field (`field_types/text`): a client that
  names two files differing only in case cannot tell them apart by filter.

`corpus/findings/135_attachment_custom_field_filename.md`

## 139_multipart_lifetime

An upload_id still completed 1230 s after its init, with part 2 minted then. The link's `timestamp` is not age-checked: it is part of the stored key, so another value signs a URL S3 answers 404. **[partial]**

not measured: an upload_id older than 1230 s. Blocked on time: `139 --write --wait <seconds>` measures any age

- A resumed upload keeps its `upload_id`, `timestamp` and the ETags of finished parts, and asks
  `get_next_part` for a fresh URL per part: every URL dies 900 s after it was minted (probe 125), the
  `upload_id` did not within 1230 s. Persist the init's whole `data` object with the ETags.

- `timestamp` is an identifier, not a freshness check. A wrong value is accepted at minting and fails
  only at the part `PUT`, as an S3 404 that blames the upload ID. Send the init's value verbatim.

- A garbage `timestamp` answers a bare `{"status": "error", ...}` body outside the `errors[]`
  envelope; parse both shapes on this call.

- An init that is never completed nor aborted stays open on storage (probe 044). Its lifetime there
  is the storage's and was not measured past 1230 s.

`corpus/findings/139_multipart_lifetime.md`

## 140_presigned_put_size

One presigned PUT took 1000 MB at 200 and the stored object read back at exactly 1000000000 bytes. No refusal up to there; at about 8 MB/s a 1000 MB PUT took two minutes. **[partial]**

not measured: sizes above 1000 MB, stopped there by design. S3 documents five gigabytes as one PUT's ceiling

- Size is not what forces multipart, up to 1000 MB at least. Choose multipart for resumability: a single
  PUT that dies at 90 % starts over, and a 1000 MB PUT here ran two minutes on one connection.

- The upload URL lives 900 s from `_upload` (probe 125). A PUT started at once may end after that,
  while one started at 600 s or later and ending past 900 s is refused (probe 153). Mint the URL
  right before the PUT and start it at once; past 900 s at the connection's rate, use parts.

- Confirm a stored size with `GET` and `Range: bytes=-1`: `Content-Range` gives the total.
  `file_size` stays null and `HEAD` is refused.

`corpus/findings/140_presigned_put_size.md`

## 141_download_headers

A stored file's GET sends Content-Length and Accept-Ranges, answers `*` to any Origin and allows a Range preflight, so a page can show progress, resume with Range and abort. `HEAD` is 403.

- Show progress from `Content-Length`: it is sent on the 200, and a script may read it under `*`.

- `HEAD` is refused because the URL is signed for `GET`. Read size with `GET` and `Range: bytes=-1`
  (probe 140), or from the 200's headers before reading the body.

- Abandoning a body is a client-side close; the URL stays usable for a new request until it expires
  900 s after it was read from the API. What S3 bills for a closed transfer was not measured.

- The stored `Content-Type` is S3's default `binary/octet-stream` when the upload `PUT` sends none,
  as this one did; the `.jpg` name does not set it. `Content-Type` is not a signed header
  (probe 125), so a `PUT` may send one, and the download then answers with it (probe 152).

- Evidence is headers read by a process. A browser applying the CORS rules to them allows the above;
  no browser was run.

`corpus/findings/141_download_headers.md`

## 151_video_on_take

On `sg_uploaded_movie` an `HEVC` .mov becomes an H.264 mp4 with a thumbnail and a filmstrip, ready in under a minute. As a plain Attachment, video gets a 480 px thumbnail and nothing else. **[partial]**

not measured: playback in the web interface and an upload from iPad Safari. Needs a browser and a person with an iPad, see below

- Only a Version gives a playable transcode. An `HEVC` `.mov` from an iPhone or iPad is stored as sent
  and its `sg_uploaded_movie_mp4` is H.264, which every browser plays. As a plain Attachment the same
  file gets a thumbnail and nothing a browser without `HEVC` can play.

- Wait for `sg_uploaded_movie_transcoding_status` 1 on a fresh Version, under a minute for these
  clips, and expect `image` to move a second time (probe 124).

- The server added one `<hash>_<name>.mp4` Attachment per Version and no `_2Dlod.jpeg`, which probe
  123 saw for a JPEG on the same field. Each outlived its Version's `DELETE` and answered its own with
  204, so delete them yourself.

**Needs a browser or a person**

| question | step |
|---|---|
| what the web interface plays inline for each row | `151 --write --hold 900`, then open the take and the Versions in the web interface |
| an upload from iPad Safari, Content-Type and size as sent | upload one recorded clip from sg-onset on an iPad, then read the Attachment and Version as this probe does |

`corpus/findings/151_video_on_take.md`

## 152_audio_on_take

Audio on `sg_uploaded_movie` transcodes to an audio-only mp4 (`aac`), status 1, no thumbnail. The stored `content_type` is not the PUT's: an Opus `.webm` sent as `audio/webm` reads `video/webm`. **[partial]**

not measured: playback in the web interface and a recording from iPad Safari. Needs a browser and a person with an iPad, see below

- A Version holds audio: status reaches 1 as for video (probe 151), and `sg_uploaded_movie_mp4` is an
  `aac` mp4 every browser plays, Opus from Chrome's MediaRecorder included. There is no frame rate,
  filmstrip or thumbnail, so draw the row's icon yourself.

- `image` reads the transient placeholder until processing ends and then null. A client waiting for a
  thumbnail on audio waits for nothing; wait on `processing_status` or the transcoding status.

- The stored `content_type` is set by the server, not taken from the PUT: the `.webm` reads
  `video/webm` although the PUT said `audio/webm`. Extension or bytes is not separated: a WebM
  container is the same for both. Decide audio or video on the client, not from `content_type`.

- The presigned GET serves back the PUT's `Content-Type`; probe 123 saw `binary/octet-stream` with
  none sent.

**Needs a browser or a person**

| question | step |
|---|---|
| does the web interface play an audio Version, and with what player | `152 --write --hold 900`, then open each Version in the web interface |
| what iPad Safari's MediaRecorder writes, container and Content-Type | record a sound note in sg-onset on an iPad and read the Attachment and Version as this probe does |

`corpus/findings/152_audio_on_take.md`

## 153_presigned_put_slow

A presigned PUT started at once and ending at 965 s was stored, 3 runs of 3. Every PUT started at 600 s or later and ending past 900 s was 403 `Request has expired`, whatever it sent first. **[partial]**

not measured: a PUT started between 4 s and 600 s, and a real upload at Wi-Fi speed. Blocked on time: each run takes 17 minutes

- Neither the start nor the end decides alone. E sent its headers 300 s before the URL expired and
  was refused after its last byte, `ServerTime` 61 s past `Expires`. A sent its headers at 2 s,
  ended 63 s past expiry, and was stored at the bytes sent.

- Where between 4 s and 600 s a start stops being accepted is unmeasured.

- Sending more up front did not help a late start: 64 KiB, 256 KiB and 1 MiB at 861 s were all
  refused at the end.

- Call `_upload` right before the PUT and start it at once. An upload that may run past 900 s goes
  up in parts, each part URL minted when its part is sent (probes 044, 139).

`corpus/findings/153_presigned_put_slow.md`
