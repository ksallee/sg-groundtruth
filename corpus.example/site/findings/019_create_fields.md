---
tags: [schema, custom-field, discovery, inspector, field-type]
scope: site
verdict: 175 sg_ fields exist across 19 entity types here. Read this before creating one: a duplicate display name silently becomes <name>_1.
---
# 019_create_fields

175 fields in the `sg_` namespace across 15 entity types on this site. `/schema` does not mark which of them shipped with Flow Production Tracking and which were added here, so this is the whole namespace rather than a list of additions. It is the input an idempotent `ensure()` reads before deciding whether to create anything.

### Asset

| field | data type | editable | display name |
|---|---|---|---|
| `sg___complete` | percent | yes | %_complete |
| `sg_ad_approval_required` | checkbox | yes | AD Approval Required |
| `sg_ad_approval_required_1` | checkbox | yes | AD Approval Required |
| `sg_asset_type` | list | yes | Type |
| `sg_bid___mod` | duration | yes | Bid - MOD |
| `sg_bid___rig` | duration | yes | Bid - RIG |
| `sg_bid___tex` | duration | yes | Bid - TEX |
| `sg_bid___total` | duration | yes | Bid - TOTAL |
| `sg_calculated` | calculated | no | Calculated |
| `sg_creative_brief` | url | yes | Creative Brief |
| `sg_fp_test_checkbox` | checkbox | yes | FP Test Checkbox |
| `sg_fp_test_checkbox_1` | checkbox | yes | FP Test Checkbox |
| `sg_fp_test_checkbox_v2` | checkbox | yes | FP Test Checkbox V2 |
| `sg_fp_test_checkbox_v2_1` | checkbox | yes | FP Test Checkbox V2 |
| `sg_keep` | checkbox | yes | Keep |
| `sg_l_approval_required` | checkbox | yes | L Approval Required |
| `sg_latest_version` | summary | yes | Latest Version |
| `sg_outsource` | checkbox | yes | Outsource |
| `sg_published_files` | multi_entity | yes | Published File <-> Link |
| `sg_query` | summary | yes | query |
| `sg_skip_art_director_approval` | checkbox | yes | Skip Art Director Approval |
| `sg_skip_lead_approval` | checkbox | yes | Skip Lead Approval |
| `sg_skip_vfx_supervisor_approval` | checkbox | yes | Skip Vfx Supervisor Approval |
| `sg_status_list` | status_list | yes | Status |
| `sg_vendor_groups` | multi_entity | yes | Vendor Groups |
| `sg_versions` | multi_entity | yes | Version <-> Link |
| `sg_vs_approval_required` | checkbox | yes | Vs Approval Required |
| `sg_weekly_report_custom_entity_s` | multi_entity | yes | Weekly Report Custom Entity  <-> WSR Link |

### Attachment

| field | data type | editable | display name |
|---|---|---|---|
| `sg_status_list` | status_list | yes | Status |
| `sg_type` | text | yes | Type |

### Cut

| field | data type | editable | display name |
|---|---|---|---|
| `sg_cut_type` | list | yes | Type |
| `sg_scene` | entity | yes | Scene |
| `sg_status_list` | status_list | yes | Status |

### Delivery

| field | data type | editable | display name |
|---|---|---|---|
| `sg_contents` | text | yes | Contents |
| `sg_delivery_method` | list | yes | Delivery Method |
| `sg_delivery_progress` | list | yes | Delivery Progress |
| `sg_delivery_type` | list | yes | Type |
| `sg_due_date` | date | yes | Due Date |
| `sg_from` | entity | yes | From |
| `sg_published_files` | multi_entity | yes | Published File <-> Link |
| `sg_received_date` | date | yes | Received Date |
| `sg_status_list` | status_list | yes | Status |
| `sg_upload_url` | url | yes | Upload URL |
| `sg_versions` | multi_entity | yes | Version <-> Link |

### Note

| field | data type | editable | display name |
|---|---|---|---|
| `sg_note_type` | list | yes | Type |
| `sg_status_list` | status_list | yes | Status |

### Playlist

| field | data type | editable | display name |
|---|---|---|---|
| `sg_date_and_time` | date_time | yes | Date and Time |

### Project

| field | data type | editable | display name |
|---|---|---|---|
| `sg_client_name` | text | yes | Client Name |
| `sg_description` | text | yes | Description |
| `sg_flow_am_id` | text | yes | Flow AM ID |
| `sg_flow_schema_config_version` | text | yes | Flow Schema Config Version |
| `sg_latest_version` | summary | yes | Latest Version |
| `sg_release_date` | date | yes | Release Date |
| `sg_status` | list | yes | Status |
| `sg_temp_due` | date | yes | Temp Due |
| `sg_type` | list | yes | Type |

### PublishedFile

| field | data type | editable | display name |
|---|---|---|---|
| `sg_flow_am_id` | text | yes | Flow AM ID |
| `sg_flow_am_type` | text | yes | Flow AM type |
| `sg_flow_is_derivative` | checkbox | yes | Flow Is Derivative |
| `sg_flow_is_template` | checkbox | yes | Flow Is Template |
| `sg_flow_revision_id` | text | yes | Flow Revision ID |
| `sg_flow_template_pipeline_step` | text | yes | Flow Template Pipeline Step |
| `sg_status_list` | status_list | yes | Status |
| `sg_uploaded_file` | url | yes | Uploaded File |

### PublishedFileType

| field | data type | editable | display name |
|---|---|---|---|
| `sg_status_list` | status_list | yes | Status |

### Sequence

| field | data type | editable | display name |
|---|---|---|---|
| `sg_duration` | text | yes | duration |
| `sg_published_files` | multi_entity | yes | Published File <-> Link |
| `sg_scenes` | multi_entity | yes | Scenes |
| `sg_sequence_full_name` | text | yes | Sequence Full Name |
| `sg_sequence_page_count` | text | yes | Sequence Page Count |
| `sg_sequence_scenes` | multi_entity | yes | Sequence Scenes |
| `sg_sequence_type` | list | yes | Type |
| `sg_sequence_vendor` | entity | yes | Sequence Vendor |
| `sg_slates` | multi_entity | yes | Slate <-> Sequence |
| `sg_status_list` | status_list | yes | Status |
| `sg_timecode` | timecode | yes | timecode |
| `sg_vendor_groups` | multi_entity | yes | Vendor Groups |
| `sg_versions` | multi_entity | yes | Version <-> Link |

### Shot

| field | data type | editable | display name |
|---|---|---|---|
| `sg___complete` | percent | yes | %_complete |
| `sg_ad_approval_required` | checkbox | yes | AD Approval Required |
| `sg_bid___ani` | duration | yes | Bid - ANI |
| `sg_bid___comp` | duration | yes | Bid - COMP |
| `sg_bid___fx` | duration | yes | Bid - FX |
| `sg_bid___lit` | duration | yes | Bid - LIT |
| `sg_bid___total` | duration | yes | Bid - TOTAL |
| `sg_client_turnover_date` | date | yes | Client Turnover date |
| `sg_creative_final_due` | date | yes | Creative Final Due |
| `sg_cut_duration` | number | yes | Cut Duration |
| `sg_cut_in` | number | yes | Cut In |
| `sg_cut_order` | number | yes | Cut Order |
| `sg_cut_out` | number | yes | Cut Out |
| `sg_date_next_version_expected` | date | yes | Date Next Version Expected |
| `sg_final_anim_due` | date | yes | Final Anim Due |
| `sg_final_notes_due` | date | yes | Final Notes Due |
| `sg_head_in` | number | yes | Head In |
| `sg_latest_vendor_notes` | text | yes | Latest Vendor Notes |
| `sg_latest_vendor_status` | status_list | yes | Latest Vendor Status |
| `sg_layout_due` | date | yes | Layout Due |
| `sg_published_files` | multi_entity | yes | Published File <-> Link |
| `sg_reel` | entity | yes | Reel |
| `sg_report_date` | date | yes | Report Date |
| `sg_scene` | entity | yes | Scene |
| `sg_sequence` | entity | yes | Sequence |
| `sg_shot_type` | list | yes | Type |
| `sg_status_list` | status_list | yes | Status |
| `sg_tail_out` | number | yes | Tail Out |
| `sg_tech_check_final_due` | date | yes | Tech Check Final Due |
| `sg_test_unique` | text | yes | Test Unique |
| `sg_turnover` | entity | yes | Turnover |
| `sg_turnover_date` | date | yes | Turnover Date |
| `sg_vendor_groups` | multi_entity | yes | Vendor Groups |
| `sg_vendor_percentage_complete` | percent | yes | Vendor Percentage Complete |
| `sg_versions` | multi_entity | yes | Version <-> Link |
| `sg_vfx_production_notes` | text | yes | VFX Production Notes |
| `sg_weekly_report_custom_entity_s` | multi_entity | yes | Weekly Report Custom Entity  <-> WSR Link |
| `sg_wip_comp_due` | date | yes | WIP Comp Due |
| `sg_working_duration` | number | yes | Working Duration |

### Task

| field | data type | editable | display name |
|---|---|---|---|
| `sg_description` | text | yes | Description |
| `sg_fp_test_checkbox` | checkbox | yes | FP Test Checkbox |
| `sg_fp_test_checkbox_v2` | checkbox | yes | FP Test Checkbox V2 |
| `sg_priority_1` | list | yes | Priority |
| `sg_skip_art_director_approval` | checkbox | yes | Skip Art Director Approval |
| `sg_skip_lead_approval` | checkbox | yes | Skip Lead Approval |
| `sg_skip_vfx_supervisor_approval` | checkbox | yes | Skip Vfx Supervisor Approval |
| `sg_sort_order` | number | yes | Sort Order |
| `sg_status_list` | status_list | yes | Status |
| `sg_versions` | multi_entity | no | Versions |

### Version

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

### CustomEntity19

| field | data type | editable | display name |
|---|---|---|---|
| `sg_editorial_clip_name` | text | yes | Editorial Clip Name |
| `sg_focal_length` | text | yes | Focal Length |
| `sg_gridded_` | checkbox | yes | Gridded? |
| `sg_lens_model` | text | yes | Lens Model |
| `sg_lens_serial_number` | text | yes | Lens Serial Number |
| `sg_slates` | multi_entity | yes | Slate <-> Lens |
| `sg_status_list` | status_list | yes | Status |
| `sg_unit` | list | yes | Unit |
| `sg_versions` | multi_entity | yes | Version <-> Link |

### CustomEntity29

| field | data type | editable | display name |
|---|---|---|---|
| `sg_drone_` | checkbox | yes | Drone? |
| `sg_google_maps_link` | text | yes | Google Maps Link |
| `sg_irl_location` | text | yes | IRL Location |
| `sg_lidar_` | checkbox | yes | LiDAR? |
| `sg_scene` | multi_entity | yes | Scene |
| `sg_shoot_days` | multi_entity | yes | Shoot Day <-> Location |
| `sg_slates` | multi_entity | yes | Slate <-> Script Location |
| `sg_status_list` | status_list | yes | Status |
| `sg_versions` | multi_entity | yes | Version <-> Link |
