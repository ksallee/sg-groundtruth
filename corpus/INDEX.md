# Corpus index

Read this first. Open an entry only when its one-liner does not already answer the question.

**Findings** — how the API behaves. **Recipes** — a verified call and its real response.

## Findings

- **001_auth** — client_credentials works and returns a 600s bearer token; a refresh_token comes back but re-authing is simpler and costs one call.  
  `auth client token`
- **002_schema** — Fetch /schema once for the type list, then /schema/<Type>/fields only for types you actually need: it is the expensive call (48KB, ~330ms each) and must never be looped over all types.  
  `schema cost discovery`
- **003_query** — A dotted ?fields path comes back flat under literal key "sg_task.Task.content" in attributes; an entity field is returned under relationships as {data, links}. Never read a row from attributes alone.  
  `query filter dotted-field paging version`
- **004_array_vs_hash** — api3_array/api3_hash are a POST _search request Content-Type, not a GET Accept header: as Accept they 406, and entity fields are returned under relationships either way.  
  `query header entity-field error-handling trap`
- **005_link_usage** — On the sample project every Version links through `entity` (99% Shot, 1% Asset) and only 1% through `sg_task`, so measure link usage per site rather than hardcoding Task-linking.  
  `version link inspector entity-field paging`
- **006_pagination** — links.next is emitted on every page forever, including zero-row ones, so stop paging when data is empty and never on a missing next.  
  `paging query enumeration`
- **007_fill_rates** — On the sample project 30 of 71 Version fields are populated. Rank by fill rate, but drop checkbox, summary and computed fields first: False and 0 are not null and read as 100% filled.  
  `version inspector schema fill-rate`
- **008_custom_entities** — Presence in /schema is the enablement test for a custom entity: a slot absent from the listing 404s. Slot numbers are non-contiguous and site-specific, so read name.value and never hardcode one.  
  `schema custom-entity discovery`
- **009_status_lists** — A project's usable statuses are valid_values minus hidden_values, read with project_id: valid_values is identical at every scope, hidden_values is the only thing that varies.  
  `schema status list-field inspector`
- **010_status_icons** — Status.icon is an entity link, so it is returned under relationships; display_type then picks one of three renderings, and bg_color alone already draws a badge.  
  `status icon cache colour entity-field`
- **011_create_project** — A script user can create a Project with nothing but {"name": ...}, at 201, but the response echoes only 6 attributes, so read the project back if you need anything else.  
  `write project create schema`
- **012_create_version** — The schema's mandatory flags are not the create contract: on every project-scoped type measured, `project` is required and the identity field is optional, server-generated and not unique.  
  `write version create entity-field`
- **013_upload_media** — Media upload is three calls: GET {field}/_upload for the presigned links, PUT the bytes to links.upload, POST links.complete_upload with upload_info and upload_data.  
  `write upload media attachment version async`
- **014_attach_file** — Leave the field out of the _upload path and the file is stored as an Attachment on attachment_links; read it back with POST /entity/attachments/_search, never flat filter[].  
  `write upload attachment provenance version multi-entity filter header`
- **016_dotted_multi_entity** — A dotted path through a multi_entity field reads back nothing: HTTP 200 with the key silently absent from attributes. Filters on that same path work, including two hops.  
  `query dotted-field multi-entity filter paging trap`
- **017_filter_operators** — is/is_not/contains/not_contains/starts_with/ends_with/in/not_in all work, on text fields and through dotted paths; an unknown operator 400s on all 21 data types, naming the valid list on 16.  
  `query filter operator dotted-field entity-field error-handling`
- **018_project_listing** — Filter a project picker on the checkboxes (is_template/is_demo/archived is False), never on sg_status, which on the probed site is set on 7 of 22 projects and null on the other 15.  
  `project query filter inspector list-field trap`
- **019_create_fields** — Custom fields are creatable over REST, but you pass a display name and a duplicate silently becomes <name>_1: an idempotent ensure() must read /schema first, never POST-and-hope.  
  `schema write custom-field provenance entity-field trap`
- **020_summarize** — _summarize needs the same vendor Content-Type as _search, and one `grouping` call returns a field's distinct-value count and its empty count. At ~300ms a field, rank a shortlist, never scan.  
  `query inspector fill-rate schema cost list-field`
- **021_media_resolution** — PublishedFile.path is returned with the LocalStorage join already done, so a client never reads LocalStorage or reassembles a root, but a platform whose storage root is unset reads null.  
  `version media published-file path storage inspector query`
- **022_sequence_on_version** — sg_uploaded_movie is single-valued, and replacing it leaves sg_uploaded_movie_mp4 describing the old file while status reads 1. A sequence belongs in sg_path_to_frames.  
  `version media upload sequence path attachment write`
- **023_pages** — A page's layout is the PageSetting row whose user is null; settings_json reads back as decoded JSON and body/list_content settings.columns is the column list. Every filter on it is ignored.  
  `page query filter schema project inspector trap`
- **024_read_after_write** — Every write ignores ?fields. A create returns what you sent plus the server defaults, an update returns the whole record, and neither resolves a dotted path, so re-read for those and after an upload.  
  `write create batch upload async entity-field trap`
- **025_event_log** — meta.old_value and meta.new_value answer "what was this before", but meta is unfilterable and unsortable: narrow on entity, event_type and attribute_name, sort -id, read meta yourself.  
  `event-log query filter operator paging write create serializable status trap`
- **026_result_order** — Rows come back id ascending unless you sort; ["id", "in", [...]] discards the order of the list, and an unsortable or unknown sort field is a silent 200 no-op where the same name in a filter 400s.  
  `query sort paging filter dotted-field trap`
- **027_auth_permissions** — The token endpoint also accepts password and session_token, not authorization_code; the bearer is a signed token whose user claim names the caller and the row holding its permission rule set.  
  `auth token permission user client`
- **028_loud_and_silent** — A 400 is trustworthy and usually names the legal set, but a 200 proves nothing: an unknown field, sort key or query param is a no-op, and a batch can return an id for a row it never made.  
  `query filter sort write operator error-handling trap`
- **030_complex_filters** — api3_hash nests and/or groups 265 deep and mixes leaves with sub-groups; api3_array cannot express or, query-string filter[] is ignored on _search, and {path,relation,values} runs nowhere.  
  `query filter operator header page error-handling trap`
- **039_upload_silent_failures** — complete_upload returns 201 and creates an Attachment even when the bytes were never PUT, and file_size is null on a good upload too, so only fetching the stored file proves it exists.  
  `media attachment upload error-handling trap note`
- **040_field_revive** — A trashed field is revived by POST /schema/<Type>/fields/<name> with {"revive": true} at 204, but it returns at its original data_type, and a PUT changing data_type is a 200 that does nothing.  
  `schema custom-field create error-handling trap discovery`

## Field types

One per `data_type`: how it reads, writes, clears and filters. `field_types/<type>`.

- **calculated** — A calculated field refuses every write with "is read only" and every filter with "cannot be used in a filter", yet it sorts and summarizes fine, and the formula is exposed as calculated_function.  
  `field-type calculated filter operator schema inspector trap`
- **checkbox** — A checkbox is two-state, never null - an untouched row already reads false, null is unwritable and unfilterable, and the only relations are is/is_not, so fill rate reads 100% on every checkbox.  
  `field-type checkbox filter operator fill-rate inspector trap`
- **color** — Task.color usually holds no colour at all but the token pipeline_step; a real value is decimal "r,g,b" (never hex), null is rejected outright, and only Task accepts the token.  
  `field-type colour filter operator write schema trap`
- **date** — A date is the string "YYYY-MM-DD" and nothing else: any timestamp 400s on write and as a filter value. Every negating operator (is_not, not_in, not_in_last) also matches rows that are null.  
  `field-type date filter operator write trap`
- **date_time** — Stored and read as UTC `YYYY-MM-DDTHH:MM:SSZ`: a written offset is silently normalised, a zoneless string is taken as UTC, and a date-only filter value means midnight UTC, not the whole day.  
  `field-type date-time filter operator write trap`
- **duration** — A duration is a bare integer of minutes and no schema property names the unit, but `GET /preferences` returns `hours_per_day` and `duration_units`, so a client can render hours or days.  
  `field-type duration number write filter operator schema trap`
- **entity** — An entity link is a {type,id} hash under relationships, cleared only by null; valid_types is advisory on most fields and binding on a few, with nothing in the schema telling the two apart.  
  `field-type entity-field write filter operator dotted-field trap`
- **entity_type** — An entity_type field is a bare schema-name string in attributes, validated on write against 290 built-in type names but not against the site's enabled ones, and filtered only by is/is_not/in/not_in.  
  `field-type entity-field schema write filter operator custom-entity trap`
- **float** — A float reads back as a JSON string rounded to 6 decimals and rejects Integer on both write and filter: send 1.0 or "1.0", never 1; 0.0 and null stay distinct, and 1e-9 silently becomes 0.0.  
  `field-type float write filter operator error-handling trap`
- **image** — An image field cannot be assigned - every value but null 400s, one of them "not yet supported in API" - only the upload dance sets it, and clearing image also clears filmstrip_image.  
  `field-type image media upload filter operator write async trap`
- **jsonb** — jsonb filters, where serializable cannot: is, is_not, contains, not_contains, values always hashes. Note.meta stores what you send but is create-only, so nothing written there is ever editable.  
  `field-type jsonb serializable write filter operator schema error-handling trap`
- **list** — A list is one bare string in attributes; a write outside valid_values 400s and is case-sensitive, while filters are case-insensitive and only is/is_not/in/not_in exist.  
  `field-type list-field filter operator schema write trap`
- **multi_entity** — A bare list replaces the whole link set, but {"multi_entity_update_mode": "add"|"remove"|"set", "value": [...]} adds and removes in place; the field never reads null and null 400s.  
  `field-type multi-entity entity-field write filter operator dotted-field trap`
- **number** — A number is a signed 32-bit integer: floats 400, 2**31 is "integer out of range", and 0 is not null, yet is_not and not_in match null rows while greater_than and less_than do not.  
  `field-type number write filter operator fill-rate trap`
- **password** — A password field reads as a constant seven-asterisk mask on every row, including through a dotted path; it cannot be filtered, sort is accepted and ignored, and it must never be written.  
  `field-type password filter operator schema dotted-field inspector trap`
- **percent** — A percent is a bare integer on a 0-100 scale (50% is 50, and 0.5 is rejected as Float), but nothing is clamped, so -1, 1000 and 2**31-1 all store at HTTP 200.  
  `field-type percent number write filter operator fill-rate trap`
- **pivot_column** — A pivot_column is a web-UI task rollup with no REST implementation - it reads null on every row, and write, filter, sort and _summarize each fail with a different error.  
  `field-type pivot-column step schema filter operator inspector trap`
- **serializable** — No operator works on a serializable field: every filter 400s as unfilterable. Task.splits answers a well-formed array of hashes with 200 while storing null, so REST cannot write it.  
  `field-type serializable write filter operator schema error-handling trap`
- **status_list** — REST does not enforce hidden_values: a project-hidden status writes and reads back fine, so every client must subtract it itself. Only valid_values is enforced.  
  `field-type status list-field filter operator write schema trap`
- **summary** — A summary field is a live rollup: refused on write even where editable=true, unfilterable, unsortable, and null on every custom one here, so re-run the query /schema exposes to select on it.  
  `field-type summary schema fill-rate inspector filter trap`
- **text** — A text field has no empty string: writing "" stores null, so `is ""` and `is None` are one filter; matching is case-insensitive, whitespace is stripped, and a non-string 400s.  
  `field-type text filter operator write trap`
- **timecode** — A timecode stores milliseconds as a signed 32-bit integer. No schema or preference names its frame rate, but a _summarize group_name renders `HH:MM:SS:FF` and the rate solves out of that.  
  `field-type timecode number media write filter operator schema summary trap`
- **url** — A url field supports no filter relation at all and sort on it is accepted and ignored, so "which Versions have media" can only be answered by paging rows and testing the value.  
  `field-type url media upload attachment version filter operator write trap`
- **uuid** — A uuid field is server-generated and rejects every write with "is read only", so it cannot hold your key; it filters on is/is_not/in/not_in only, and a malformed value 400s.  
  `field-type uuid filter operator write schema trap`

## Entity types

One per standard entity type: what it is, how it is identified, created and linked. `entity_types/<Type>`.

- **Asset** — Only project is required to create an Asset; omit code and the server writes "New Asset <id>", and two assets in one project may share a code, so key on id and never on code.  
  `entity-type asset create entity-field multi-entity list-field status trap`
- **Attachment** — POST /entity/attachments answers 201 on an empty body and returns a row with no file; this_file is editable on create only, so bytes reach a site through the upload dance and never through a create.  
  `entity-type attachment upload media url multi-entity create status trap`
- **Cut** — A Cut stores an edit, it does not model one: no field is computed or validated, and `cut_items` is returned sorted by the item's display name rather than by `cut_order`.  
  `entity-type cut timecode create entity-field multi-entity status list-field schema trap`
- **CutItem** — Nothing on a CutItem is unique and `code` repeats across Cuts, so an id found by a code search may sit on another Cut: check `cut` before every update or the write lands on the wrong edit.  
  `entity-type cut timecode create entity-field filter operator dotted-field schema trap`
- **Delivery** — Delivery has two independent Version links, sg_versions and version_sg_deliveries_versions; writing one leaves the other empty, and only the second mirrors Version.sg_deliveries.  
  `entity-type delivery version published-file reply attachment create multi-entity entity-field status list-field filter trap`
- **Note** — A Note is titled by `subject` and bodied by `content`; only `project` is required to create one, `attachments` link in that same call, and a bare write to `replies` destroys the Reply rows.  
  `entity-type note create multi-entity entity-field attachment status jsonb trap`
- **Playlist** — Playlist.versions reads back sorted by the Version's code, never in the order written; the human order is sg_sort_order on PlaylistVersionConnection, which a write through the field leaves null.  
  `entity-type playlist version create multi-entity entity-field trap`
- **Project** — Project is site-wide and has no `project` field, so a scoping filter 400s on it; `name` is the identity, the only field both mandatory and unique, and `code` is a second unique text field.  
  `entity-type project schema filter trap`
- **PublishedFile** — Only `project` is required to create a PublishedFile, and nothing is unique: the same name, version_number and path publish twice at 201, so read the last version before writing the next.  
  `entity-type published-file create path storage entity-field multi-entity dependency status trap`
- **PublishedFileType** — PublishedFileType is site-wide with no project field, so a publish that creates one on an unknown extension adds it to every project; `code` is the identity and the only unique field.  
  `entity-type published-file enumeration schema filter create trap`
- **Reply** — Reply is site-wide with no project field, and entity accepts almost every type on the site, not only Note; send entity on create, because a Reply whose entity is null cannot be deleted.  
  `entity-type reply note create entity-field query filter trap`
- **Sequence** — A Sequence needs `project`, not `code`, and project alone names it `New Sequence <id>`; `shots` is the reverse of `Shot.sg_sequence`, one link, so a Shot sits in exactly one Sequence.  
  `entity-type sequence shot write create entity-field multi-entity status dotted-field trap`
- **Shot** — Shot is addressed at /entity/shots and needs only project on create: code is flagged mandatory yet optional, and an omitted code becomes the server-invented "New Shot <id>".  
  `entity-type shot create entity-field multi-entity status pivot-column trap`
- **Step** — Step is site-wide with no project field, partitioned only by entity_type; list the Steps for a Shot with entity_type is "Shot", and treat neither code nor short_name as unique.  
  `entity-type step task entity-field schema filter query trap`
- **Task** — A Task is named by `content`, never `code`; a create needs only `project`; `start_date`, `due_date` and `duration` are one triple the server recomputes on every write.  
  `entity-type task create dependency duration status entity-field trap`
- **TimeLog** — A TimeLog create requires only `project`; `date` defaults to the server's today instead of failing, `entity` takes any type despite valid_types ['Task'], and a script may log for any HumanUser.  
  `entity-type time-log task duration create entity-field trap`
- **Version** — The schema inverts the create contract: `project` is required and `code` is not, generated as "New Version <id>" when omitted. `code` is not unique, so key on `id`.  
  `entity-type version create entity-field media status link`

## Recipes

- **001_publish_version_with_media** — Publish a generated image to Flow PT as a Version, with provenance and the workflow attached  
  `write version upload attachment provenance recipe`
- **002_batch** — Apply many creates, updates and deletes in one atomic call, and match the results back to the requests  
  `write batch create version shot error-handling trap recipe`
- **003_query_fields_and_pages** — Resolve a query field's value, and run the rows a saved Page shows  
  `query filter summary page schema operator dotted-field trap recipe`
- **004_register_published_file** — Register the next PublishedFile without overwriting the last one, and write a path the server resolves for every platform  
  `write published-file path storage version create entity-field trap recipe`
- **005_propagate_status** — Roll a status up from a parent's Tasks and Versions onto the parent, without racing a concurrent write  
  `write status task version shot schema batch filter trap recipe`
- **006_media_round_trip** — Take media off one Version and put the same bytes on another, which is what every sync, transfer and hand-off does  
  `write version media upload attachment url image async trap recipe`
- **007_build_and_reconcile_a_cut** — Write a Cut and its CutItems from an edit, read the timeline back, and reconcile a second edit against the Cut already there  
  `write cut timecode version shot batch filter entity-field multi-entity trap recipe`
- **008_delivery_progress** — Keep a Delivery honest about what a long transfer is doing, including when it is cancelled and when it crashes  
  `write delivery status list-field reply upload attachment version error-handling trap recipe`
- **009_multi_entity_safely** — Add to and remove from a multi_entity field without destroying the links you did not mean to touch  
  `write multi-entity entity-field playlist note version filter trap recipe`
- **010_status_picker** — List the statuses a project actually offers, each with the label, colour and icon needed to draw it  
  `status icon colour schema list-field entity-field dotted-field project cache trap recipe`

## By tag

- **asset** — Asset (entity type)
- **async** — 013_upload_media (finding), 024_read_after_write (finding), 006_media_round_trip (recipe), image (field type)
- **attachment** — 013_upload_media (finding), 014_attach_file (finding), 022_sequence_on_version (finding), 039_upload_silent_failures (finding), 001_publish_version_with_media (recipe), 006_media_round_trip (recipe), 008_delivery_progress (recipe), url (field type), Attachment (entity type), Delivery (entity type), Note (entity type)
- **auth** — 001_auth (finding), 027_auth_permissions (finding)
- **batch** — 024_read_after_write (finding), 002_batch (recipe), 005_propagate_status (recipe), 007_build_and_reconcile_a_cut (recipe)
- **cache** — 010_status_icons (finding), 010_status_picker (recipe)
- **calculated** — calculated (field type)
- **checkbox** — checkbox (field type)
- **client** — 001_auth (finding), 027_auth_permissions (finding)
- **colour** — 010_status_icons (finding), 010_status_picker (recipe), color (field type)
- **cost** — 002_schema (finding), 020_summarize (finding)
- **create** — 011_create_project (finding), 012_create_version (finding), 024_read_after_write (finding), 025_event_log (finding), 040_field_revive (finding), 002_batch (recipe), 004_register_published_file (recipe), Asset (entity type), Attachment (entity type), Cut (entity type), CutItem (entity type), Delivery (entity type), Note (entity type), Playlist (entity type), PublishedFile (entity type), PublishedFileType (entity type), Reply (entity type), Sequence (entity type), Shot (entity type), Task (entity type), TimeLog (entity type), Version (entity type)
- **custom-entity** — 008_custom_entities (finding), entity_type (field type)
- **custom-field** — 019_create_fields (finding), 040_field_revive (finding)
- **cut** — 007_build_and_reconcile_a_cut (recipe), Cut (entity type), CutItem (entity type)
- **date** — date (field type)
- **date-time** — date_time (field type)
- **delivery** — 008_delivery_progress (recipe), Delivery (entity type)
- **dependency** — PublishedFile (entity type), Task (entity type)
- **discovery** — 002_schema (finding), 008_custom_entities (finding), 040_field_revive (finding)
- **dotted-field** — 003_query (finding), 016_dotted_multi_entity (finding), 017_filter_operators (finding), 026_result_order (finding), 003_query_fields_and_pages (recipe), 010_status_picker (recipe), entity (field type), multi_entity (field type), password (field type), CutItem (entity type), Sequence (entity type)
- **duration** — duration (field type), Task (entity type), TimeLog (entity type)
- **entity-field** — 004_array_vs_hash (finding), 005_link_usage (finding), 010_status_icons (finding), 012_create_version (finding), 017_filter_operators (finding), 019_create_fields (finding), 024_read_after_write (finding), 004_register_published_file (recipe), 007_build_and_reconcile_a_cut (recipe), 009_multi_entity_safely (recipe), 010_status_picker (recipe), entity (field type), entity_type (field type), multi_entity (field type), Asset (entity type), Cut (entity type), CutItem (entity type), Delivery (entity type), Note (entity type), Playlist (entity type), PublishedFile (entity type), Reply (entity type), Sequence (entity type), Shot (entity type), Step (entity type), Task (entity type), TimeLog (entity type), Version (entity type)
- **entity-type** — Asset (entity type), Attachment (entity type), Cut (entity type), CutItem (entity type), Delivery (entity type), Note (entity type), Playlist (entity type), Project (entity type), PublishedFile (entity type), PublishedFileType (entity type), Reply (entity type), Sequence (entity type), Shot (entity type), Step (entity type), Task (entity type), TimeLog (entity type), Version (entity type)
- **enumeration** — 006_pagination (finding), PublishedFileType (entity type)
- **error-handling** — 004_array_vs_hash (finding), 017_filter_operators (finding), 028_loud_and_silent (finding), 030_complex_filters (finding), 039_upload_silent_failures (finding), 040_field_revive (finding), 002_batch (recipe), 008_delivery_progress (recipe), float (field type), jsonb (field type), serializable (field type)
- **event-log** — 025_event_log (finding)
- **field-type** — calculated (field type), checkbox (field type), color (field type), date (field type), date_time (field type), duration (field type), entity (field type), entity_type (field type), float (field type), image (field type), jsonb (field type), list (field type), multi_entity (field type), number (field type), password (field type), percent (field type), pivot_column (field type), serializable (field type), status_list (field type), summary (field type), text (field type), timecode (field type), url (field type), uuid (field type)
- **fill-rate** — 007_fill_rates (finding), 020_summarize (finding), checkbox (field type), number (field type), percent (field type), summary (field type)
- **filter** — 003_query (finding), 014_attach_file (finding), 016_dotted_multi_entity (finding), 017_filter_operators (finding), 018_project_listing (finding), 023_pages (finding), 025_event_log (finding), 026_result_order (finding), 028_loud_and_silent (finding), 030_complex_filters (finding), 003_query_fields_and_pages (recipe), 005_propagate_status (recipe), 007_build_and_reconcile_a_cut (recipe), 009_multi_entity_safely (recipe), calculated (field type), checkbox (field type), color (field type), date (field type), date_time (field type), duration (field type), entity (field type), entity_type (field type), float (field type), image (field type), jsonb (field type), list (field type), multi_entity (field type), number (field type), password (field type), percent (field type), pivot_column (field type), serializable (field type), status_list (field type), summary (field type), text (field type), timecode (field type), url (field type), uuid (field type), CutItem (entity type), Delivery (entity type), Project (entity type), PublishedFileType (entity type), Reply (entity type), Step (entity type)
- **float** — float (field type)
- **header** — 004_array_vs_hash (finding), 014_attach_file (finding), 030_complex_filters (finding)
- **icon** — 010_status_icons (finding), 010_status_picker (recipe)
- **image** — 006_media_round_trip (recipe), image (field type)
- **inspector** — 005_link_usage (finding), 007_fill_rates (finding), 009_status_lists (finding), 018_project_listing (finding), 020_summarize (finding), 021_media_resolution (finding), 023_pages (finding), calculated (field type), checkbox (field type), password (field type), pivot_column (field type), summary (field type)
- **jsonb** — jsonb (field type), Note (entity type)
- **link** — 005_link_usage (finding), Version (entity type)
- **list-field** — 009_status_lists (finding), 018_project_listing (finding), 020_summarize (finding), 008_delivery_progress (recipe), 010_status_picker (recipe), list (field type), status_list (field type), Asset (entity type), Cut (entity type), Delivery (entity type)
- **media** — 013_upload_media (finding), 021_media_resolution (finding), 022_sequence_on_version (finding), 039_upload_silent_failures (finding), 006_media_round_trip (recipe), image (field type), timecode (field type), url (field type), Attachment (entity type), Version (entity type)
- **multi-entity** — 014_attach_file (finding), 016_dotted_multi_entity (finding), 007_build_and_reconcile_a_cut (recipe), 009_multi_entity_safely (recipe), multi_entity (field type), Asset (entity type), Attachment (entity type), Cut (entity type), Delivery (entity type), Note (entity type), Playlist (entity type), PublishedFile (entity type), Sequence (entity type), Shot (entity type)
- **note** — 039_upload_silent_failures (finding), 009_multi_entity_safely (recipe), Note (entity type), Reply (entity type)
- **number** — duration (field type), number (field type), percent (field type), timecode (field type)
- **operator** — 017_filter_operators (finding), 025_event_log (finding), 028_loud_and_silent (finding), 030_complex_filters (finding), 003_query_fields_and_pages (recipe), calculated (field type), checkbox (field type), color (field type), date (field type), date_time (field type), duration (field type), entity (field type), entity_type (field type), float (field type), image (field type), jsonb (field type), list (field type), multi_entity (field type), number (field type), password (field type), percent (field type), pivot_column (field type), serializable (field type), status_list (field type), text (field type), timecode (field type), url (field type), uuid (field type), CutItem (entity type)
- **page** — 023_pages (finding), 030_complex_filters (finding), 003_query_fields_and_pages (recipe)
- **paging** — 003_query (finding), 005_link_usage (finding), 006_pagination (finding), 016_dotted_multi_entity (finding), 025_event_log (finding), 026_result_order (finding)
- **password** — password (field type)
- **path** — 021_media_resolution (finding), 022_sequence_on_version (finding), 004_register_published_file (recipe), PublishedFile (entity type)
- **percent** — percent (field type)
- **permission** — 027_auth_permissions (finding)
- **pivot-column** — pivot_column (field type), Shot (entity type)
- **playlist** — 009_multi_entity_safely (recipe), Playlist (entity type)
- **project** — 011_create_project (finding), 018_project_listing (finding), 023_pages (finding), 010_status_picker (recipe), Project (entity type)
- **provenance** — 014_attach_file (finding), 019_create_fields (finding), 001_publish_version_with_media (recipe)
- **published-file** — 021_media_resolution (finding), 004_register_published_file (recipe), Delivery (entity type), PublishedFile (entity type), PublishedFileType (entity type)
- **query** — 003_query (finding), 004_array_vs_hash (finding), 006_pagination (finding), 016_dotted_multi_entity (finding), 017_filter_operators (finding), 018_project_listing (finding), 020_summarize (finding), 021_media_resolution (finding), 023_pages (finding), 025_event_log (finding), 026_result_order (finding), 028_loud_and_silent (finding), 030_complex_filters (finding), 003_query_fields_and_pages (recipe), Reply (entity type), Step (entity type)
- **recipe** — 001_publish_version_with_media (recipe), 002_batch (recipe), 003_query_fields_and_pages (recipe), 004_register_published_file (recipe), 005_propagate_status (recipe), 006_media_round_trip (recipe), 007_build_and_reconcile_a_cut (recipe), 008_delivery_progress (recipe), 009_multi_entity_safely (recipe), 010_status_picker (recipe)
- **reply** — 008_delivery_progress (recipe), Delivery (entity type), Reply (entity type)
- **schema** — 002_schema (finding), 007_fill_rates (finding), 008_custom_entities (finding), 009_status_lists (finding), 011_create_project (finding), 019_create_fields (finding), 020_summarize (finding), 023_pages (finding), 040_field_revive (finding), 003_query_fields_and_pages (recipe), 005_propagate_status (recipe), 010_status_picker (recipe), calculated (field type), color (field type), duration (field type), entity_type (field type), jsonb (field type), list (field type), password (field type), pivot_column (field type), serializable (field type), status_list (field type), summary (field type), timecode (field type), uuid (field type), Cut (entity type), CutItem (entity type), Project (entity type), PublishedFileType (entity type), Step (entity type)
- **sequence** — 022_sequence_on_version (finding), Sequence (entity type)
- **serializable** — 025_event_log (finding), jsonb (field type), serializable (field type)
- **shot** — 002_batch (recipe), 005_propagate_status (recipe), 007_build_and_reconcile_a_cut (recipe), Sequence (entity type), Shot (entity type)
- **sort** — 026_result_order (finding), 028_loud_and_silent (finding)
- **status** — 009_status_lists (finding), 010_status_icons (finding), 025_event_log (finding), 005_propagate_status (recipe), 008_delivery_progress (recipe), 010_status_picker (recipe), status_list (field type), Asset (entity type), Attachment (entity type), Cut (entity type), Delivery (entity type), Note (entity type), PublishedFile (entity type), Sequence (entity type), Shot (entity type), Task (entity type), Version (entity type)
- **step** — pivot_column (field type), Step (entity type)
- **storage** — 021_media_resolution (finding), 004_register_published_file (recipe), PublishedFile (entity type)
- **summary** — 003_query_fields_and_pages (recipe), summary (field type), timecode (field type)
- **task** — 005_propagate_status (recipe), Step (entity type), Task (entity type), TimeLog (entity type)
- **text** — text (field type)
- **time-log** — TimeLog (entity type)
- **timecode** — 007_build_and_reconcile_a_cut (recipe), timecode (field type), Cut (entity type), CutItem (entity type)
- **token** — 001_auth (finding), 027_auth_permissions (finding)
- **trap** — 004_array_vs_hash (finding), 016_dotted_multi_entity (finding), 018_project_listing (finding), 019_create_fields (finding), 023_pages (finding), 024_read_after_write (finding), 025_event_log (finding), 026_result_order (finding), 028_loud_and_silent (finding), 030_complex_filters (finding), 039_upload_silent_failures (finding), 040_field_revive (finding), 002_batch (recipe), 003_query_fields_and_pages (recipe), 004_register_published_file (recipe), 005_propagate_status (recipe), 006_media_round_trip (recipe), 007_build_and_reconcile_a_cut (recipe), 008_delivery_progress (recipe), 009_multi_entity_safely (recipe), 010_status_picker (recipe), calculated (field type), checkbox (field type), color (field type), date (field type), date_time (field type), duration (field type), entity (field type), entity_type (field type), float (field type), image (field type), jsonb (field type), list (field type), multi_entity (field type), number (field type), password (field type), percent (field type), pivot_column (field type), serializable (field type), status_list (field type), summary (field type), text (field type), timecode (field type), url (field type), uuid (field type), Asset (entity type), Attachment (entity type), Cut (entity type), CutItem (entity type), Delivery (entity type), Note (entity type), Playlist (entity type), Project (entity type), PublishedFile (entity type), PublishedFileType (entity type), Reply (entity type), Sequence (entity type), Shot (entity type), Step (entity type), Task (entity type), TimeLog (entity type)
- **upload** — 013_upload_media (finding), 014_attach_file (finding), 022_sequence_on_version (finding), 024_read_after_write (finding), 039_upload_silent_failures (finding), 001_publish_version_with_media (recipe), 006_media_round_trip (recipe), 008_delivery_progress (recipe), image (field type), url (field type), Attachment (entity type)
- **url** — 006_media_round_trip (recipe), url (field type), Attachment (entity type)
- **user** — 027_auth_permissions (finding)
- **uuid** — uuid (field type)
- **version** — 003_query (finding), 005_link_usage (finding), 007_fill_rates (finding), 012_create_version (finding), 013_upload_media (finding), 014_attach_file (finding), 021_media_resolution (finding), 022_sequence_on_version (finding), 001_publish_version_with_media (recipe), 002_batch (recipe), 004_register_published_file (recipe), 005_propagate_status (recipe), 006_media_round_trip (recipe), 007_build_and_reconcile_a_cut (recipe), 008_delivery_progress (recipe), 009_multi_entity_safely (recipe), url (field type), Delivery (entity type), Playlist (entity type), Version (entity type)
- **write** — 011_create_project (finding), 012_create_version (finding), 013_upload_media (finding), 014_attach_file (finding), 019_create_fields (finding), 022_sequence_on_version (finding), 024_read_after_write (finding), 025_event_log (finding), 028_loud_and_silent (finding), 001_publish_version_with_media (recipe), 002_batch (recipe), 004_register_published_file (recipe), 005_propagate_status (recipe), 006_media_round_trip (recipe), 007_build_and_reconcile_a_cut (recipe), 008_delivery_progress (recipe), 009_multi_entity_safely (recipe), color (field type), date (field type), date_time (field type), duration (field type), entity (field type), entity_type (field type), float (field type), image (field type), jsonb (field type), list (field type), multi_entity (field type), number (field type), percent (field type), serializable (field type), status_list (field type), text (field type), timecode (field type), url (field type), uuid (field type), Sequence (entity type)
