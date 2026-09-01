---
tags: [version, inspector, schema, fill-rate]
verdict: Of 61 Version fields in the schema, 30 carry data on BBB and 31 are never populated - rank by fill rate, never expose the schema wholesale. CAVEAT: booleans read as 100% filled because False is not null, so the inspector must exclude checkbox fields from fill ranking or use the schema data_type to weight them.
---

# 007_fill_rates

**Endpoint** `GET /schema/Version/fields + GET /entity/versions`

**Docs claim** Schema lists what is possible; only a subset is ever filled.

**Actual**

```
sample: 100 most recent Versions on project 70; 61 fields in schema

populated (30):
  cached_display_name                    100/100
  client_approved                        100/100
  code                                   100/100
  created_at                             100/100
  created_by                             100/100
  description                            100/100
  entity                                 100/100
  flagged                                100/100
  open_notes_count                       100/100
  project                                100/100
  sg_frames_have_slate                   100/100
  sg_movie_has_slate                     100/100
  sg_status_list                         100/100
  updated_at                             100/100
  updated_by                             100/100
  user                                   100/100
  viewed_by_current_user                 100/100
  sg_version_type                         99/100
  filmstrip_image                          1/100
  image                                    1/100
  image_blur_hash                          1/100
  image_source_entity                      1/100
  otio_playable                            1/100
  sg_task                                  1/100
  sg_uploaded_movie                        1/100
  sg_uploaded_movie_frame_rate             1/100
  sg_uploaded_movie_image                  1/100
  sg_uploaded_movie_mp4                    1/100
  sg_uploaded_movie_transcoding_status     1/100
  uploaded_movie_duration                  1/100

never populated (31):
  client_approved_at, client_approved_by, client_code, cuts, frame_count, frame_range, id, media_center_import_time, notes, open_notes, platform_status, playlists, published_files, sg_deliveries, sg_department, sg_first_frame, sg_frames_aspect_ratio, sg_last_frame, sg_movie_aspect_ratio, sg_path_to_frames, sg_path_to_geometry, sg_path_to_movie, sg_translation_type, sg_uploaded_movie_webm, source_clip, step_0, tags, task_template, tasks, uploaded_movie_audio_offset_mp4, viewed_by_current_user_at
```

**Verdict** Of 61 Version fields in the schema, 30 carry data on BBB and 31 are never populated - rank by fill rate, never expose the schema wholesale. CAVEAT: booleans read as 100% filled because False is not null, so the inspector must exclude checkbox fields from fill ranking or use the schema data_type to weight them.
