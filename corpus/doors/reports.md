# Reports

Behaviour that should change, addressed to the team that owns the API. Each names the entries that measured it, states what was expected, and proposes the fix. It is also the re-probe queue: each one dates the last time the behaviour was seen.

- **001_batch_create_skips_validation** [api, unreported] — A create inside POST /entity/_batch skips the required-attribute validation the single-create path applies, and answers 200 with the id of a row no read can reach.  
  evidence: recipes/002_batch, findings/028_loud_and_silent, confirmed 2026-09-04  
  `corpus/reports/001_batch_create_skips_validation.md`
- **002_complete_upload_without_bytes** [api, unreported] — POST links.complete_upload answers 201 and creates an Attachment when the presigned PUT never happened, and nothing on the row separates it from a good upload.  
  evidence: findings/039_upload_silent_failures, findings/013_upload_media, confirmed 2026-09-04  
  `corpus/reports/002_complete_upload_without_bytes.md`
- **003_sort_fails_silently** [api, unreported] — A sort on an unknown or unsortable field answers 200 with the rows in default order, while the same field name in a filter answers 400 and names the reason.  
  evidence: findings/026_result_order, findings/028_loud_and_silent, findings/017_filter_operators, confirmed 2026-09-04  
  `corpus/reports/003_sort_fails_silently.md`
- **004_update_mode_ignored_in_query_string** [api, unreported] — multi_entity_update_mode sent as a query parameter is accepted and ignored, and the whole link set is replaced when the caller asked to add.  
  evidence: findings/field_types/multi_entity, recipes/009_multi_entity_safely, findings/028_loud_and_silent, confirmed 2026-09-04  
  `corpus/reports/004_update_mode_ignored_in_query_string.md`
- **005_writing_replies_deletes_rows** [api, unreported] — A write to Note.replies deletes the Reply rows rather than unlinking them, so PUT with an empty list destroys a thread at 200.  
  evidence: findings/entity_types/Note, findings/entity_types/Reply, findings/028_loud_and_silent, confirmed 2026-09-04  
  `corpus/reports/005_writing_replies_deletes_rows.md`
- **006_duplicate_field_name_is_201** [api, unreported] — Creating a custom field whose display name is taken answers 201 for a suffixed field instead of a conflict, and every retry burns a programmatic name no REST call frees.  
  evidence: findings/019_create_fields, endpoints/post_schema_type_fields, confirmed 2026-09-04  
  `corpus/reports/006_duplicate_field_name_is_201.md`
- **007_reference_disagrees_with_spec** [docs, unreported] — Four calls in the published REST reference exist under no spelling in the deployment's own OpenAPI document, which names two of them differently.  
  evidence: findings/042_spec_coverage, confirmed 2026-09-04  
  `corpus/reports/007_reference_disagrees_with_spec.md`
- **008_jsonb_filters_return_everything** [api, unreported] — A filter on PageSetting.settings_json or EventLogEntry.audit_trail is accepted and ignored, so the unfiltered set comes back at 200 and is_null and is_not_null each return every row.  
  evidence: findings/023_pages, findings/field_types/jsonb, confirmed 2026-09-04  
  `corpus/reports/008_jsonb_filters_return_everything.md`
- **009_attention_500s_on_bad_input** [api, unreported] — A record id that does not exist on activity_stream is a 500, and the follow body answers 500 for the plural entity name every URL on the API uses while an invalid name answers 400.  
  evidence: findings/043_attention, confirmed 2026-09-04  
  `corpus/reports/009_attention_500s_on_bad_input.md`
