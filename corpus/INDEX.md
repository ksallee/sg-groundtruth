# Corpus index

Read this first. It names every entry and says which door to open. A group door carries one line per entry and that entry's rules, copied whole.

| you know | open |
|---|---|
| the call | its family under **Endpoints** |
| the entity type | `doors/entity_types.md` |
| the `data_type` | `doors/field_types.md` |
| the task | `doors/recipes.md` |
| the phase of a session | `doors/findings-<phase>.md` |

An endpoint door holds the edge cases that live on the call and the verdict of every entry that measured it, each naming the group door its rules are on. Read the verdicts, open that door for the rules, the entry for a transcript, a sample or a table. A 2xx that did nothing is under **Silent on this call**. Measured against `/api/v1` (`051_api_version`).

## Findings

**auth** 001_auth, 027_auth_permissions, 052_app_session_launcher

**protocol** 004_array_vs_hash, 028_loud_and_silent, 051_api_version, 062_cors

**schema** 002_schema, 008_custom_entities, 009_status_lists, 019_create_fields, 040_field_revive, 042_spec_coverage, 047_site_facts_and_the_working_week, 056_stock_vs_custom_field, 061_shipped_statuses

**read** 003_query, 005_link_usage, 006_pagination, 007_fill_rates, 018_project_listing, 021_media_resolution, 023_pages, 026_result_order, 048_one_record_beyond_crud, 059_dotted_path_type_check, 060_entity_dict_name, 064_hierarchy_expand_buckets

**filter** 016_dotted_multi_entity, 017_filter_operators, 020_summarize, 030_complex_filters, 046_search_without_a_path, 053_text_search_matching, 063_text_search_filter_shape

**write** 011_create_project, 012_create_version, 024_read_after_write, 045_webhooks, 050_webhook_subscriptions, 058_local_storage_roots

**upload** 013_upload_media, 014_attach_file, 022_sequence_on_version, 039_upload_silent_failures, 044_multipart_upload

**observe** 025_event_log, 043_attention, 049_script_events

**render** 010_status_icons

## Field types

calculated, checkbox, color, date, date_time, duration, entity, entity_type, float, image, jsonb, list, multi_entity, number, password, percent, pivot_column, serializable, status_list, summary, text, timecode, url, uuid

## Entity types

Asset, Attachment, Cut, CutItem, Delivery, HumanUser, LocalStorage, Note, Playlist, Project, PublishedFile, PublishedFileType, Reply, Sequence, Shot, Step, Task, TimeLog, Version

## Recipes

- 001_publish_version_with_media — Publish a generated image to Flow PT as a Version, with provenance and the workflow attached
- 002_batch — Apply many creates, updates and deletes in one atomic call, and match the results back to the requests
- 003_query_fields_and_pages — Resolve a query field's value, and run the rows a saved Page shows
- 004_register_published_file — Register the next PublishedFile without overwriting the last one, and write a path the server resolves for every platform
- 005_propagate_status — Roll a status up from a parent's Tasks and Versions onto the parent, without racing a concurrent write
- 006_media_round_trip — Take media off one Version and put the same bytes on another, which is what every sync, transfer and hand-off does
- 007_build_and_reconcile_a_cut — Write a Cut and its CutItems from an edit, read the timeline back, and reconcile a second edit against the Cut already there
- 008_delivery_progress — Keep a Delivery honest about what a long transfer is doing, including when it is cancelled and when it crashes
- 009_multi_entity_safely — Add to and remove from a multi_entity field without destroying the links you did not mean to touch
- 010_status_picker — List the statuses a project actually offers, each with the label, colour and icon needed to draw it
- 011_audit_webhook_subscriptions — Inventory every webhook subscription on a site, and see which have ever delivered
- 012_sign_in_as_a_person — Reach the REST API as a person, with no script key and no password, by having them approve a login in their browser
- 013_publish_file_bytes — Publish a file's bytes onto a PublishedFile when the caller has no LocalStorage root to write under

## Endpoints

One card per call, 63 of 69 with an entry behind them; a card with none is the queue. A family's door is `doors/endpoints-<family>.md`, in lower case.

**Session**

```
GET /
POST /auth/access_token
POST /internal_api/app_session_request
PUT /internal_api/app_session_request/<sessionRequestId>
```

**Site**

```
GET /license_info
GET /preferences
PUT /preferences/update
GET /schedule/work_day_rules
PUT /schedule/work_day_rules
GET /spec.<format>
GET /subscription_seat/user_subscriptions
POST /subscription_seat/user_subscriptions
```

**Schema**

```
GET /schema
GET /schema/<Type>
GET /schema/<Type>/fields
POST /schema/<Type>/fields
GET /schema/<Type>/fields/<field>
POST /schema/<Type>/fields/<field>
PUT /schema/<Type>/fields/<field>
DELETE /schema/<Type>/fields/<field>
```

**Records**, one door per method: `doors/endpoints-records-<method>.md`

```
GET /entity/<type>
POST /entity/<type>
GET /entity/<type>/<id>
POST /entity/<type>/<id>
PUT /entity/<type>/<id>
DELETE /entity/<type>/<id>
GET /entity/<type>/<id>/<field>
GET /entity/<type>/<id>/relationships/<related_field>
POST /entity/_batch
PUT /entity/projects/<id>/_update_last_accessed
```

**Search**

```
POST /entity/<type>/_search
POST /entity/<type>/_summarize
POST /entity/_text_search
POST /hierarchy/_expand
POST /hierarchy/_search
```

**Media**

```
GET /entity/<type>/<id>/<field>/_upload
POST /entity/<type>/<id>/<field>/_upload
PUT /entity/<type>/<id>/<field>/_upload
GET /entity/<type>/<id>/<field>/_upload/multipart
POST /entity/<type>/<id>/<field>/_upload/multipart_abort
GET /entity/<type>/<id>/_upload
POST /entity/<type>/<id>/_upload
PUT /entity/<type>/<id>/_upload
GET /entity/<type>/<id>/_upload/multipart
POST /entity/<type>/<id>/_upload/multipart_abort
POST /transcode/attachment_metadata/<id>
POST <links.complete_upload>
PUT <links.upload>
```

**Attention**

```
GET /entity/<type>/<id>/activity_stream
GET /entity/<type>/<id>/followers
PUT /entity/<type>/<id>/unfollow
POST /entity/human_users/<user_id>/follow
GET /entity/human_users/<user_id>/following
GET /entity/notes/<id>/thread_contents
```

**Webhooks**

```
GET /webhook/deliveries/<record_uuid>
PUT /webhook/deliveries/<record_uuid>
POST /webhook/deliveries/<record_uuid>/redeliver
GET /webhook/hooks
POST /webhook/hooks
GET /webhook/hooks/<hook_id>/deliveries
GET /webhook/hooks/<record_uuid>
PUT /webhook/hooks/<record_uuid>
DELETE /webhook/hooks/<record_uuid>
POST /webhook/hooks/<record_uuid>/test_connection
```

**Exports**

```
GET /exports/page/<page_id>.<format>
GET /exports/page/<page_id>/<layout_name>.<format>
```

**Other**

```
POST /internal_api/autodesk_identity/license_renewal
GET /internal_api/session
POST /internal_api/session
```

## Reports

001_batch_create_skips_validation, 002_complete_upload_without_bytes, 003_sort_fails_silently, 004_update_mode_ignored_in_query_string, 005_writing_replies_deletes_rows, 006_duplicate_field_name_is_201, 007_reference_disagrees_with_spec, 008_jsonb_filters_return_everything, 009_attention_500s_on_bad_input

## Tags

`doors/tags.md` holds the entries under each.

async attachment auth batch browser cache client colour cors cost create custom-entity custom-field cut date delivery dependency destructive discovery dotted-field duration entity-field enumeration error-handling etag event-log fill-rate filter follow header icon image inspector jsonb launcher link list-field media multi-entity multipart note number observe operator page paging path permission pivot-column playlist project protocol provenance published-file query read-only reply schema sequence serializable shot silent sort status step storage sudo summary task timecode token transcode trap upload url user version webhook write
