---
tags: [entity-type, schema, custom-field, inspector, list-field]
scope: site
title: Version
verdict: On this site Version has 30 sg_ fields and 3 vocabularies over 1073 rows. The codes here are what the API stores; the labels are editable.
---
# Version

What this site configures on top of the shipped `Version` card. The card above is the API layer; everything here is one site's own.

1073 rows site-wide, across every project. The 100 most recent were read for the link census below.

**`sg_` fields**

| field | data type | editable | display name |
|---|---|---|---|
| `sg_ai_cfg` | float | yes | AI CFG |
| `sg_ai_generated_from` | multi_entity | yes | AI Generated From |
| `sg_ai_generator` | text | yes | AI Generator |
| `sg_ai_model` | text | yes | AI Model |
| `sg_ai_negative_prompt` | text | yes | AI Negative Prompt |
| `sg_ai_prompt` | text | yes | AI Prompt |
| `sg_ai_sampler` | text | yes | AI Sampler |
| `sg_ai_seed` | text | yes | AI Seed |
| `sg_ai_steps` | number | yes | AI Steps |
| `sg_deliveries` | multi_entity | yes | Deliveries |
| `sg_department` | text | yes | Department |
| `sg_first_frame` | number | yes | First Frame |
| `sg_frames_aspect_ratio` | float | yes | Frames Aspect Ratio |
| `sg_frames_have_slate` | checkbox | yes | Frames Have Slate |
| `sg_last_frame` | number | yes | Last Frame |
| `sg_movie_aspect_ratio` | float | yes | Movie Aspect Ratio |
| `sg_movie_has_slate` | checkbox | yes | Movie Has Slate |
| `sg_path_to_frames` | text | yes | Path to Frames |
| `sg_path_to_geometry` | text | yes | Path to Geometry |
| `sg_path_to_movie` | text | yes | Path to Movie |
| `sg_status_list` | status_list | yes | Status |
| `sg_task` | entity | yes | Task |
| `sg_translation_type` | text | yes | Translation Type |
| `sg_uploaded_movie` | url | yes | Uploaded Movie |
| `sg_uploaded_movie_frame_rate` | float | yes | Frame Rate |
| `sg_uploaded_movie_image` | url | yes | Uploaded Movie Image |
| `sg_uploaded_movie_mp4` | url | yes | Uploaded Movie MP4 |
| `sg_uploaded_movie_transcoding_status` | number | yes | Uploaded Movie Transcoding Status |
| `sg_uploaded_movie_webm` | url | yes | Uploaded Movie WebM |
| `sg_version_type` | list | yes | Type |

`/schema` does not mark which of these shipped with Flow Production Tracking and which were added here, so this is the whole namespace on the type.

**Vocabularies**

| field | data type | values | vocabulary | default |
|---|---|---|---|---|
| `sg_status_list` | status_list | 16 | `na (N/A)`, `rev (Pending Review)`, `vwd (Viewed)`, `apr (Approved)`, `custom (CustomIcon)`, `fin (Final)`, `ip (In Progress)`, `clsd (Closed)`, `cmpt (Complete)`, `cfrm (Confirmed)`, `pndad (Pending Art Director)`, `pndl (Pending Lead)`, `pndvs (Pending VFX Supervisor)`, `part (partial)`, `pass`, `pndng (Pending)` | rev |
| `sg_version_type` | list | 3 | `Type A`, `Type B`, `Type C` | Type A |
| `viewed_by_current_user` | list | 2 | `read`, `unread` |  |

Site-wide: `valid_values` is byte-identical at every scope (probe 009). Which of these values a project can select is the project layer of this card.

**Links populated site-wide**

| field | data type | set on | points at |
|---|---|---|---|
| `entity` | entity | 97/100 | Shot 94, Asset 3 |
| `image_source_entity` | entity | 18/100 | Version 18 |
| `published_files` | multi_entity | 1/100 | PublishedFile 1 |
| `sg_ai_generated_from` | multi_entity | 1/100 | Version 1 |
| `sg_task` | entity | 2/100 | Task 2 |
| `user` | entity | 100/100 | HumanUser 82, ApiUser 18 |
| `version_sg_ai_generated_from_versions` | multi_entity | 1/100 | Version 1 |

10 of 17 link fields are empty on every sampled row. Which ones a single project fills is the project layer.
