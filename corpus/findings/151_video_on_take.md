---
tags: [on-set, upload, transcode, version, attachment, media]
endpoints: [POST /entity/<type>, GET /entity/<type>/<id>, GET /entity/<type>/<id>/<field>/_upload, PUT <links.upload>, POST <links.complete_upload>]
phase: upload
scope: api
measured: sandbox project written, 2026-11-17 (twice); a take row, 2 Versions and 6 Attachments per run, deleted
coverage: partial
unmeasured: playback in the web interface and an upload from iPad Safari. Needs a browser and a person with an iPad, see below
verdict: On `sg_uploaded_movie` an `HEVC` .mov becomes an H.264 mp4 with a thumbnail and a filmstrip, ready in under a minute. As a plain Attachment, video gets a 480 px thumbnail and nothing else.
---

# 151_video_on_take

**Q** Is a video Attachment (`.mp4` H.264, `.mov` `HEVC`) transcoded or thumbnailed, and what do the
same files become on `Version.sg_uploaded_movie`?

**Endpoint** `POST /entity/versions ; GET /entity/<type>/<id>/<field>/_upload ; PUT <links.upload> ; POST <links.complete_upload>`

**Docs claim** Silent on what is made of an Attachment. Probe 022 measured a `.mov` on
`sg_uploaded_movie`. The Version's `entity` is the take row, which any custom slot allows at 201
(probe 122, `field_types/entity`).

**Actual**

```
files: 4 s, 1280x720, 24 fps, AAC tone; h264 .mp4 1426206 bytes, hevc (hvc1) .mov 1029473 bytes
PUT Content-Type as a browser sends it: video/mp4, video/quicktime; init, PUT 200, complete 201

                         Attachment on the take's field     Version.sg_uploaded_movie
  t+0s                   processing_status thumbnail_pending_us, image transient; status 0, image transient
  t+34..47s              image JPEG 480x270, processing_status null
  t+46s (mp4) t+59s (mov)                                   transcoding_status 1, frame_rate "24.0",
                                                            uploaded_movie_duration "4.01",
                                                            image JPEG 480x270, filmstrip JPEG 23040x135
  never, in 184 s        filmstrip_image null               sg_uploaded_movie_image, frame_count null

stored, read back through ffprobe
  .mp4 this_file / sg_uploaded_movie   video/mp4, 1426206 bytes, h264 1280x720 + aac   byte count unchanged
  .mov this_file / sg_uploaded_movie   video/quicktime, 1029473 bytes, hevc 1280x720 + aac
  sg_uploaded_movie_mp4 of the .mp4    <hash>_<name>.mp4, video/mp4, h264 1280x720 24/1 + aac
  sg_uploaded_movie_mp4 of the .mov    <hash>_<name>.mp4, video/mp4, h264 1280x720 24/1 + aac
  Attachments the server added         one <hash>_<name>.mp4 per Version, attachment_links [Version]
  the take row's own image             null after both uploads
```

**What the server makes of a video**

| | plain Attachment | `Version.sg_uploaded_movie` |
|---|---|---|
| original kept | yes, byte for byte | yes |
| transcode | none | H.264 `.mp4` with `AAC`, `HEVC` included, in `sg_uploaded_movie_mp4` |
| thumbnail | `image`, 480 px wide, aspect kept | `image`, the same size |
| filmstrip | none | `filmstrip_image`, a strip of 240x135 frames |
| frame rate, duration | none | `sg_uploaded_movie_frame_rate`, `uploaded_movie_duration`, strings |
| done when | `processing_status` null, about 35 to 47 s | `sg_uploaded_movie_transcoding_status` 1, 46 to 59 s |

Known elsewhere and seen again here: `sg_uploaded_movie_webm` stays null (probe 022), `file_size`
stays null (`entity_types/Attachment`), and both inits answer `upload_type: "Attachment"` (probe 013).

**Teaches**
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
