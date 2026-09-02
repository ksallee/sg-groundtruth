---
tags: [version, inspector, schema, fill-rate]
scope: site
measured: one sample project, its 100 most recent Versions over 71 schema fields
verdict: On the sample project 30 of 71 Version fields are populated. Rank by fill rate, but drop checkbox, summary and computed fields first: False and 0 are not null and read as 100% filled.
---

# 007_fill_rates

**Q** Of the fields the schema lists for Version, how many are populated on a real project?

**Endpoint** `GET /schema/Version/fields ; GET /entity/versions`

**Docs claim** Silent. The schema lists what is possible; nothing says which fields a site fills.

**Actual**

```
sample: 100 most recent Versions on the sample project; 71 fields in schema

populated (30):
  100/100  code cached_display_name created_at created_by updated_at updated_by
           project entity user description sg_status_list        (11 real)
  100/100  client_approved flagged sg_frames_have_slate sg_movie_has_slate
           open_notes_count viewed_by_current_user       (6 constant, see below)
   99/100  sg_version_type
    1/100  image filmstrip_image image_blur_hash image_source_entity
           otio_playable sg_task sg_uploaded_movie sg_uploaded_movie_image
           sg_uploaded_movie_mp4 sg_uploaded_movie_frame_rate
           sg_uploaded_movie_transcoding_status uploaded_movie_duration
                                        (12, all on the single uploaded Version)

never populated (41 at 0/100), incl:
  client_approved_at cuts frame_count frame_range notes playlists
  published_files sg_path_to_frames sg_path_to_movie tags task_template tasks
  + 9 sg_ai_* custom fields (provenance, added out-of-band; see probe 019)

the 6 "100%" fields, value distribution over the same 100 rows:
  client_approved       False x100     flagged                 False x100
  sg_frames_have_slate  False x100     sg_movie_has_slate      False x100
  open_notes_count      0 x100         viewed_by_current_user  'unread' x100
```

**Teaches**
- A boolean reads as 100% filled because False is not null, and so does a summary count of 0 and a computed list. On the probed site 6 of the 17 fields at 100/100 hold one constant across all 100 rows, so a fill-rate ranking that includes them is wrong at the top.
- Exclude checkbox, summary and computed `data_type`s from fill ranking, or confirm a candidate with `_summarize` grouping, which returns a single group for exactly these fields. `probe 020` reaches the same trap from the `_summarize` side, where a checkbox cannot be filtered `is_not None`.
- On the probed site fill rate is bimodal: 100% or 1%, nothing in between. The 1% band is twelve media fields on the one uploaded Version, so a threshold anywhere between 2% and 98% separates structure from anecdote.
- The roster is not stable: the schema grew from 61 to 71 fields since this probe first ran, and all 10 additions read 0/100. Re-read `/schema/Version/fields` per run; one paged fetch of 100 rows then measures every field in a single call.
