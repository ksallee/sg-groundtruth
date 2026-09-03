---
tags: [fill-rate, inspector, schema, project, query]
scope: project
project: Big Buck Bunny
verdict: On Big Buck Bunny, 6 of 15 sampled entity types hold no rows. Version populates 25 of 65 rankable fields, Shot populates 23 of 85 rankable fields.
---
# 007_fill_rates

The 100 most recent rows per entity type on Big Buck Bunny, counted non-null field by field. Checkbox, summary, calculated and pivot fields are excluded: `False` and `0` are not null, so they read as fully populated and cannot be ranked.

| entity type | sampled | fields ranked | populated | never populated |
|---|---|---|---|---|
| Asset | 100 | 41 | 18 | 23 |
| Attachment | 100 | 29 | 18 | 11 |
| Cut | 0 | 29 | 0 | 29 |
| CutItem | 0 | 27 | 0 | 27 |
| Delivery | 0 | 32 | 0 | 32 |
| Note | 100 | 30 | 13 | 17 |
| Playlist | 1 | 23 | 9 | 14 |
| PublishedFile | 0 | 31 | 0 | 31 |
| Sequence | 15 | 36 | 11 | 25 |
| Shot | 100 | 85 | 23 | 62 |
| Task | 100 | 43 | 20 | 23 |
| TimeLog | 100 | 12 | 10 | 2 |
| Version | 100 | 65 | 25 | 40 |
| CustomEntity19 | 0 | 24 | 0 | 24 |
| CustomEntity29 | 0 | 23 | 0 | 23 |

A field that is never populated here is one this project does not use. It is not a field the API refuses.

### Asset

| field | data type | filled |
|---|---|---|
| `cached_display_name` | text | 100/100 |
| `code` | text | 100/100 |
| `created_at` | date_time | 100/100 |
| `created_by` | entity | 100/100 |
| `description` | text | 100/100 |
| `image` | image | 100/100 |
| `image_source_entity` | entity | 100/100 |
| `project` | entity | 100/100 |
| `sg_asset_type` | list | 100/100 |
| `sg_status_list` | status_list | 100/100 |
| `shots` | multi_entity | 100/100 |
| `tasks` | multi_entity | 100/100 |
| `updated_at` | date_time | 100/100 |
| `sequences` | multi_entity | 98/100 |
| `updated_by` | entity | 4/100 |
| `filmstrip_image` | image | 1/100 |
| `image_blur_hash` | text | 1/100 |
| `sg_versions` | multi_entity | 1/100 |

23 never populated.

### Attachment

| field | data type | filled |
|---|---|---|
| `cached_display_name` | text | 100/100 |
| `created_at` | date_time | 100/100 |
| `created_by` | entity | 100/100 |
| `display_name` | text | 100/100 |
| `filename` | text | 100/100 |
| `project` | entity | 100/100 |
| `this_file` | url | 100/100 |
| `updated_at` | date_time | 100/100 |
| `updated_by` | entity | 100/100 |
| `file_size` | number | 97/100 |
| `filmstrip_image` | image | 75/100 |
| `image` | image | 75/100 |
| `image_source_entity` | entity | 75/100 |
| `file_extension` | text | 26/100 |
| `sg_status_list` | status_list | 26/100 |
| `attachment_links` | multi_entity | 3/100 |
| `image_blur_hash` | text | 3/100 |
| `original_fname` | text | 1/100 |

11 never populated.

### Note

| field | data type | filled |
|---|---|---|
| `cached_display_name` | text | 100/100 |
| `content` | text | 100/100 |
| `created_at` | date_time | 100/100 |
| `note_links` | multi_entity | 100/100 |
| `project` | entity | 100/100 |
| `publish_status` | text | 100/100 |
| `reply_content` | text | 100/100 |
| `sg_note_type` | list | 100/100 |
| `sg_status_list` | status_list | 100/100 |
| `subject` | text | 100/100 |
| `updated_at` | date_time | 100/100 |
| `user` | entity | 81/100 |
| `addressings_to` | multi_entity | 67/100 |

17 never populated.

### Playlist

| field | data type | filled |
|---|---|---|
| `cached_display_name` | text | 1/1 |
| `code` | text | 1/1 |
| `created_at` | date_time | 1/1 |
| `created_by` | entity | 1/1 |
| `external_share_count` | number | 1/1 |
| `media_center_viewed_by_current_user` | list | 1/1 |
| `project` | entity | 1/1 |
| `updated_at` | date_time | 1/1 |
| `updated_by` | entity | 1/1 |

14 never populated.

### Sequence

| field | data type | filled |
|---|---|---|
| `assets` | multi_entity | 15/15 |
| `cached_display_name` | text | 15/15 |
| `code` | text | 15/15 |
| `created_at` | date_time | 15/15 |
| `created_by` | entity | 15/15 |
| `description` | text | 15/15 |
| `project` | entity | 15/15 |
| `sg_status_list` | status_list | 15/15 |
| `shots` | multi_entity | 15/15 |
| `updated_at` | date_time | 15/15 |
| `updated_by` | entity | 15/15 |

25 never populated.

### Shot

| field | data type | filled |
|---|---|---|
| `assets` | multi_entity | 100/100 |
| `cached_display_name` | text | 100/100 |
| `code` | text | 100/100 |
| `created_at` | date_time | 100/100 |
| `created_by` | entity | 100/100 |
| `description` | text | 100/100 |
| `image` | image | 100/100 |
| `image_source_entity` | entity | 100/100 |
| `notes` | multi_entity | 100/100 |
| `open_notes` | multi_entity | 100/100 |
| `project` | entity | 100/100 |
| `sg_cut_duration` | number | 100/100 |
| `sg_cut_in` | number | 100/100 |
| `sg_cut_order` | number | 100/100 |
| `sg_cut_out` | number | 100/100 |
| `sg_head_in` | number | 100/100 |
| `sg_sequence` | entity | 100/100 |
| `sg_status_list` | status_list | 100/100 |
| `sg_tail_out` | number | 100/100 |
| `sg_working_duration` | number | 100/100 |
| `tasks` | multi_entity | 100/100 |
| `updated_at` | date_time | 100/100 |
| `updated_by` | entity | 15/100 |

62 never populated.

### Task

| field | data type | filled |
|---|---|---|
| `cached_display_name` | text | 100/100 |
| `color` | color | 100/100 |
| `content` | text | 100/100 |
| `created_at` | date_time | 100/100 |
| `created_by` | entity | 100/100 |
| `due_date` | date | 100/100 |
| `duration` | duration | 100/100 |
| `entity` | entity | 100/100 |
| `image` | image | 100/100 |
| `image_source_entity` | entity | 100/100 |
| `project` | entity | 100/100 |
| `sg_status_list` | status_list | 100/100 |
| `sibling_tasks` | multi_entity | 100/100 |
| `start_date` | date | 100/100 |
| `step` | entity | 100/100 |
| `time_logs_sum` | duration | 100/100 |
| `updated_at` | date_time | 100/100 |
| `workload_assignee_count` | number | 100/100 |
| `updated_by` | entity | 46/100 |
| `task_assignees` | multi_entity | 44/100 |

23 never populated.

### TimeLog

| field | data type | filled |
|---|---|---|
| `cached_display_name` | text | 100/100 |
| `created_at` | date_time | 100/100 |
| `created_by` | entity | 100/100 |
| `date` | date | 100/100 |
| `description` | text | 100/100 |
| `duration` | duration | 100/100 |
| `entity` | entity | 100/100 |
| `project` | entity | 100/100 |
| `updated_at` | date_time | 100/100 |
| `updated_by` | entity | 100/100 |

2 never populated.

### Version

| field | data type | filled |
|---|---|---|
| `cached_display_name` | text | 100/100 |
| `code` | text | 100/100 |
| `created_at` | date_time | 100/100 |
| `created_by` | entity | 100/100 |
| `description` | text | 100/100 |
| `entity` | entity | 100/100 |
| `project` | entity | 100/100 |
| `sg_status_list` | status_list | 100/100 |
| `updated_at` | date_time | 100/100 |
| `updated_by` | entity | 100/100 |
| `user` | entity | 100/100 |
| `viewed_by_current_user` | list | 100/100 |
| `sg_version_type` | list | 99/100 |
| `filmstrip_image` | image | 1/100 |
| `image` | image | 1/100 |
| `image_blur_hash` | text | 1/100 |
| `image_source_entity` | entity | 1/100 |
| `otio_playable` | text | 1/100 |
| `sg_task` | entity | 1/100 |
| `sg_uploaded_movie` | url | 1/100 |
| `sg_uploaded_movie_frame_rate` | float | 1/100 |
| `sg_uploaded_movie_image` | url | 1/100 |
| `sg_uploaded_movie_mp4` | url | 1/100 |
| `sg_uploaded_movie_transcoding_status` | number | 1/100 |

+1 more populated, 40 never populated.
