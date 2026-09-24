# `POST /entity/<type>/_summarize`

Every call in this family: what the card records, the edge cases that live on the call, and the verdict of every entry that measured it. Each of those lines names the door holding that entry's rules. The map is `corpus/INDEX.md`.

Counts without paging rows. One `grouping` returns a field's distinct values and their counts at ~300ms, so rank a shortlist with it and never scan every field.

- Summarizing an unsummarizable field, `image`, answers 200 with a 37-byte body and no summary. It does
  not 400. Test that the key you asked for is in `summaries` before reading it.

- `group_name` is the rendered label and `group_value` the raw one. For a `timecode` field the rendered
  form is `HH:MM:SS:FF`, which is how the frame rate is recovered when no field exposes it.

- One call per field at about 300ms. Over 71 fields that is 21 seconds. Rank a shortlist by fill rate
  first and summarize only the candidates.

**Measured by**

- `028_loud_and_silent` (findings) — A 400 is trustworthy and usually names the legal set, but a 200 proves nothing: an unknown field, sort key or query param is a no-op, and a batch can return an id for a row it never made.  
  rules: `doors/findings-protocol`
- `091_status_summary_exclusions` (findings) — Excluded statuses are invisible to REST: not in /schema at any scope, not writable by PUT. status_list honours them: fin plus an excluded omt rolls up to fin, omt alone to na.  
  rules: `doors/findings-schema`
- `006_pagination` (findings) — links.next is emitted on every page forever, including zero-row ones, so stop paging when data is empty and never on a missing next.  
  rules: `doors/findings-read`
- `021_media_resolution` (findings) — PublishedFile.path is returned with the LocalStorage join already done, so a client never reads LocalStorage or reassembles a root, but a platform whose storage root is unset reads null.  
  rules: `doors/findings-read`
- `081_dotted_image` (findings) — entity.Shot.image returns the Shot's thumbnail as a presigned S3 URL under attributes, same object, fresh signature, in the same call. image is_not null matched 50 Shots whose image reads null.  
  rules: `doors/findings-read`
- `020_summarize` (findings) — _summarize needs the same vendor Content-Type as _search, and one `grouping` call returns a field's distinct-value count and its empty count. At ~300ms a field, rank a shortlist, never scan.  
  rules: `doors/findings-filter`
- `030_complex_filters` (findings) — api3_hash nests and/or groups 265 deep and mixes leaves with sub-groups; api3_array cannot express or, query-string filter[] is ignored on _search, and {path,relation,values} runs nowhere.  
  rules: `doors/findings-filter`
- `068_note_read_state` (findings) — read_by_current_user is per person and missing from the schema; `is` and `is_not` are evaluated, while `in`, `not_in` and an unknown `is` value all return the unread rows at 200.  
  rules: `doors/findings-filter`
- `071_note_link_name_filter` (findings) — Filter notes about a thing on `note_links.<Type>.cached_display_name`: it resolves for every valid type, `code` 400s on Booking and `name` on all but Department. The path cannot be read back.  
  rules: `doors/findings-filter`
- `074_page_filter_coverage` (findings) — Every stored page filter with its tokens filled converts and runs 200 but one, yet recipe 003 kept unticked leaves (active "false"): 11 trees returned the wrong count. Drop them.  
  rules: `doors/findings-filter`
- `079_summarize_multi_grouping` (findings) — _summarize nests one group level per grouping entry, 3 deep tested, counts summing exactly. status_list rolls a group up to one status; status_percentage ignores any value and is no per-status share.  
  rules: `doors/findings-filter`
- `080_query_field_cost` (findings) — One _summarize with the parent leaf as `in [N rows]`, grouped on that link, reproduced open_notes_count for 300 Shots in 573 ms, against ~290 ms a row one call at a time.  
  rules: `doors/findings-filter`
- `077_page_change_stamps` (findings) — PageSetting has no updated_at; Page.updated_at moves when its layout is saved. Poll Page.updated_at; Shotgun_PageSetting_Change names which setting changed but its entity is null on 131 of 500.  
  rules: `doors/findings-observe`
- `003_query_fields_and_pages` (recipes) — Resolve a query field's value, and run the rows a saved Page shows  
  rules: `doors/recipes`
- `014_notes_about` (recipes) — Find the Notes about a Shot, Asset or Version by the name of the thing, and read what each Note is linked to  
  rules: `doors/recipes`

**Silent on this call**

- `028_loud_and_silent` — A 400 is trustworthy and usually names the legal set, but a 200 proves nothing: an unknown field, sort key or query param is a no-op, and a batch can return an id for a row it never made.
- `030_complex_filters` — api3_hash nests and/or groups 265 deep and mixes leaves with sub-groups; api3_array cannot express or, query-string filter[] is ignored on _search, and {path,relation,values} runs nowhere.
- `068_note_read_state` — read_by_current_user is per person and missing from the schema; `is` and `is_not` are evaluated, while `in`, `not_in` and an unknown `is` value all return the unread rows at 200.

`corpus/endpoints/post_entity_type_summarize.md`
