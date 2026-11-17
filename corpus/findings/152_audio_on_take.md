---
tags: [on-set, upload, transcode, version, attachment, media]
endpoints: [POST /entity/<type>, GET /entity/<type>/<id>, GET /entity/<type>/<id>/<field>/_upload, PUT <links.upload>, POST <links.complete_upload>]
phase: upload
scope: api
measured: sandbox project written, 2026-11-17; one take row, 3 Versions, 6 Attachments, all deleted
coverage: partial
unmeasured: playback in the web interface and a recording from iPad Safari. Needs a browser and a person with an iPad, see below
verdict: Audio on `sg_uploaded_movie` transcodes to an audio-only mp4 (`aac`), status 1, no thumbnail. The stored `content_type` is not the PUT's: an Opus `.webm` sent as `audio/webm` reads `video/webm`.
---

# 152_audio_on_take

**Q** What does the server make of audio, `.m4a` (`AAC`) and `.webm` (Opus), as an Attachment and as
`Version.sg_uploaded_movie`: a transcode, which stored `content_type`, a thumbnail?

**Endpoint** `POST /entity/versions ; GET /entity/<type>/<id>/<field>/_upload ; PUT <links.upload> ; POST <links.complete_upload>`

**Docs claim** Silent on audio. `sg_uploaded_movie` is described as a movie.

**Actual**

```
files: 4 s 440 Hz tone; aac .m4a 36565 bytes, opus .webm 41461 bytes
PUT Content-Type as a browser sends it: audio/mp4, audio/webm

init on either field     data.upload_type "Attachment"; PUT 200; complete 201

                          .m4a                                 .webm
this_file / sg_uploaded_movie content_type
                          "audio/mp4"                          "video/webm"
GET the stored file       200 audio/mp4, 36565 bytes, aac      200 audio/webm, 41461 bytes, opus

Attachment on the take's field
  t+0s                    processing_status thumbnail_pending_us, image transient placeholder
  t+45s                   processing_status null, image null   (the same at t+46s for .webm)

Version.sg_uploaded_movie
  t+0s                    transcoding_status 0, image transient placeholder
  t+34s (.m4a) t+46s (.webm)
                          transcoding_status 1, image null, uploaded_movie_duration "4.01" / "4.0"
                          sg_uploaded_movie_mp4 <hash>_<name>.mp4, content_type "video/mp4"
  never, in 181 s         frame_rate, frame_count, filmstrip_image, sg_uploaded_movie_image,
                          sg_uploaded_movie_webm, audio_offset all null

sg_uploaded_movie_mp4, through ffprobe
  of the .m4a             video/mp4, 70509 bytes, aac only, 4.01 s
  of the .webm            video/mp4, 82168 bytes, aac only, 4.00 s
```

**Audio, where it goes**

| | plain Attachment | `Version.sg_uploaded_movie` |
|---|---|---|
| original kept | yes, byte for byte | yes |
| transcode | none | `.mp4` holding one `aac` stream and no video, Opus included |
| thumbnail | none: `image` goes from the placeholder to null | none: `image` null |
| duration | none | `uploaded_movie_duration`, a string |
| done when | `processing_status` null, about 45 s | `sg_uploaded_movie_transcoding_status` 1, 34 to 46 s |

**Teaches**
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
