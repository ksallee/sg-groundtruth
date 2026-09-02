---
tags: [version, media, upload, sequence, path, attachment, write]
scope: api
measured: sandbox project, one Version created and deleted
verdict: sg_uploaded_movie is single-valued, and replacing it leaves sg_uploaded_movie_mp4 describing the old file while status reads 1. A sequence belongs in sg_path_to_frames.
---

# 022_sequence_on_version

**Q** Can a Version hold an image sequence as media, or only a single movie?

**Endpoint** `GET /entity/versions/{id}/{field}/_upload ; POST {links.complete_upload}`

**Docs claim** Silent. The docs describe uploading a file to a media field, never a sequence.

**Actual**

```
=== one upload per frame, same field
  upload 1 (corridor_lookdev.0001.png) -> 201; field now holds 'corridor_lookdev.0001.png'
  upload 2 (corridor_lookdev.0002.png) -> 201; field now holds 'corridor_lookdev.0002.png'
  upload 3 (corridor_lookdev.0003.png) -> 201; field now holds 'corridor_lookdev.0003.png'
  => single-valued: each upload REPLACES, it does not accumulate

=== the same frames with no field in the path (probe 014)
  corridor_lookdev.0001.png -> 201 type=Attachment
  corridor_lookdev.0002.png -> 201 type=Attachment
  attachments linked: 5  => Attachments DO accumulate, but are files, not media

=== then upload the .mov to the same field, and poll
  t+  0s status=0 mp4=None
  t+ 75s status=1 fps=25.0 mp4='..._corridor_lookdev.0003.mp4'   <- the REPLACED png
  t+180s status=1 fps=25.0 mp4='..._corridor_lookdev.0003.mp4'   <- stable, not in flight
  sg_uploaded_movie = 'corridor_lookdev.mov'   (the field itself is correct)

=== control: a fresh Version, one .mov, never replaced
  t+ 20s status=0 fps=None  mp4=None
  t+ 60s status=1 fps=8.0   mp4='..._corridor_lookdev.mp4'       <- correct, and 8fps as encoded
  sg_uploaded_movie_webm = None in BOTH cases, even at status=1
```

**Teaches**
- A sequence cannot be media. Put the `%04d` pattern in `sg_path_to_frames` and upload one transcoded movie for the review player.
- Replacing `sg_uploaded_movie` does not invalidate its derived fields: `sg_uploaded_movie_mp4` keeps serving a transcode of the file you replaced. A player trusting it shows the wrong content.
- `sg_uploaded_movie_transcoding_status` = 1 means *a* transcode finished, not that the *current* media is transcoded. `sg_uploaded_movie_frame_rate` disagrees: 25.0 for the still, 8.0 for the real movie.
- `sg_uploaded_movie_webm` was never populated on the probed site, at status 1 or before; do not wait on it. Poll `_mp4` instead, since transcoding is async (probe 013).
- Attachments accumulate and media does not: five uploads to one Version left five Attachments linked while `sg_uploaded_movie` held one file. Frames parked as Attachments are storage, never review. `PublishedFile` is the right home for the sequence, still unproven (probe 021).
