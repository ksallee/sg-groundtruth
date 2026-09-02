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
- **012_create_version** — POST a Version with project as a {type, id} hash plus code; entity links take the same hash - a bare id 400s, and omitting project 400s even though only code is schema-mandatory.  
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
- **021_media_resolution** — PublishedFile.path is returned with the LocalStorage join already done (local_path_mac/windows/linux are server-filled), so a client never reads LocalStorage or reassembles a root.  
  `version media published-file path storage inspector query`
- **022_sequence_on_version** — sg_uploaded_movie is single-valued, and replacing it leaves sg_uploaded_movie_mp4 describing the old file while status reads 1. A sequence belongs in sg_path_to_frames.  
  `version media upload sequence path attachment write`

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
- **entity** — An entity link is a {type,id} hash under relationships, cleared only by null; valid_types binds on two of Version's seven editable entity fields, so the API will point sg_task at a Shot.  
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
- **Project** — Project is site-wide and has no `project` field, so a scoping filter 400s on it; `name` is the identity, the only field both mandatory and unique, and `code` is a second unique text field.  
  `entity-type project schema filter trap`
- **Sequence** — A Sequence needs `project`, not `code`, and project alone names it `New Sequence <id>`; `shots` is the reverse of `Shot.sg_sequence`, one link, so a Shot sits in exactly one Sequence.  
  `entity-type sequence shot write create entity-field multi-entity status dotted-field trap`
- **Shot** — Shot is addressed at /entity/shots and needs only project on create: code is flagged mandatory yet optional, and an omitted code becomes the server-invented "New Shot <id>".  
  `entity-type shot create entity-field multi-entity status pivot-column trap`
- **Step** — Step is site-wide with no project field, partitioned only by entity_type; list the Steps for a Shot with entity_type is "Shot", and treat neither code nor short_name as unique.  
  `entity-type step task entity-field schema filter query trap`
- **Task** — A Task is named by `content`, never `code`; a create needs only `project`; `start_date`, `due_date` and `duration` are one triple the server recomputes on every write.  
  `entity-type task create dependency duration status entity-field trap`
- **Version** — The schema inverts the create contract: `project` is required and `code` is not, generated as "New Version <id>" when omitted. `code` is not unique, so key on `id`.  
  `entity-type version create entity-field media status link`

## Recipes

- **001_publish_version_with_media** — Publish a generated image to Flow PT as a Version, with provenance and the workflow attached  
  `write version upload attachment provenance recipe`

## By tag

- **asset** — Asset (entity type)
- **async** — 013_upload_media (finding), image (field type)
- **attachment** — 013_upload_media (finding), 014_attach_file (finding), 022_sequence_on_version (finding), 001_publish_version_with_media (recipe), url (field type)
- **auth** — 001_auth (finding)
- **cache** — 010_status_icons (finding)
- **calculated** — calculated (field type)
- **checkbox** — checkbox (field type)
- **client** — 001_auth (finding)
- **colour** — 010_status_icons (finding), color (field type)
- **cost** — 002_schema (finding), 020_summarize (finding)
- **create** — 011_create_project (finding), 012_create_version (finding), Asset (entity type), Sequence (entity type), Shot (entity type), Task (entity type), Version (entity type)
- **custom-entity** — 008_custom_entities (finding), entity_type (field type)
- **custom-field** — 019_create_fields (finding)
- **date** — date (field type)
- **date-time** — date_time (field type)
- **dependency** — Task (entity type)
- **discovery** — 002_schema (finding), 008_custom_entities (finding)
- **dotted-field** — 003_query (finding), 016_dotted_multi_entity (finding), 017_filter_operators (finding), entity (field type), multi_entity (field type), password (field type), Sequence (entity type)
- **duration** — duration (field type), Task (entity type)
- **entity-field** — 004_array_vs_hash (finding), 005_link_usage (finding), 010_status_icons (finding), 012_create_version (finding), 017_filter_operators (finding), 019_create_fields (finding), entity (field type), entity_type (field type), multi_entity (field type), Asset (entity type), Sequence (entity type), Shot (entity type), Step (entity type), Task (entity type), Version (entity type)
- **entity-type** — Asset (entity type), Project (entity type), Sequence (entity type), Shot (entity type), Step (entity type), Task (entity type), Version (entity type)
- **enumeration** — 006_pagination (finding)
- **error-handling** — 004_array_vs_hash (finding), 017_filter_operators (finding), float (field type), jsonb (field type), serializable (field type)
- **field-type** — calculated (field type), checkbox (field type), color (field type), date (field type), date_time (field type), duration (field type), entity (field type), entity_type (field type), float (field type), image (field type), jsonb (field type), list (field type), multi_entity (field type), number (field type), password (field type), percent (field type), pivot_column (field type), serializable (field type), status_list (field type), summary (field type), text (field type), timecode (field type), url (field type), uuid (field type)
- **fill-rate** — 007_fill_rates (finding), 020_summarize (finding), checkbox (field type), number (field type), percent (field type), summary (field type)
- **filter** — 003_query (finding), 014_attach_file (finding), 016_dotted_multi_entity (finding), 017_filter_operators (finding), 018_project_listing (finding), calculated (field type), checkbox (field type), color (field type), date (field type), date_time (field type), duration (field type), entity (field type), entity_type (field type), float (field type), image (field type), jsonb (field type), list (field type), multi_entity (field type), number (field type), password (field type), percent (field type), pivot_column (field type), serializable (field type), status_list (field type), summary (field type), text (field type), timecode (field type), url (field type), uuid (field type), Project (entity type), Step (entity type)
- **float** — float (field type)
- **header** — 004_array_vs_hash (finding), 014_attach_file (finding)
- **icon** — 010_status_icons (finding)
- **image** — image (field type)
- **inspector** — 005_link_usage (finding), 007_fill_rates (finding), 009_status_lists (finding), 018_project_listing (finding), 020_summarize (finding), 021_media_resolution (finding), calculated (field type), checkbox (field type), password (field type), pivot_column (field type), summary (field type)
- **jsonb** — jsonb (field type)
- **link** — 005_link_usage (finding), Version (entity type)
- **list-field** — 009_status_lists (finding), 018_project_listing (finding), 020_summarize (finding), list (field type), status_list (field type), Asset (entity type)
- **media** — 013_upload_media (finding), 021_media_resolution (finding), 022_sequence_on_version (finding), image (field type), timecode (field type), url (field type), Version (entity type)
- **multi-entity** — 014_attach_file (finding), 016_dotted_multi_entity (finding), multi_entity (field type), Asset (entity type), Sequence (entity type), Shot (entity type)
- **number** — duration (field type), number (field type), percent (field type), timecode (field type)
- **operator** — 017_filter_operators (finding), calculated (field type), checkbox (field type), color (field type), date (field type), date_time (field type), duration (field type), entity (field type), entity_type (field type), float (field type), image (field type), jsonb (field type), list (field type), multi_entity (field type), number (field type), password (field type), percent (field type), pivot_column (field type), serializable (field type), status_list (field type), text (field type), timecode (field type), url (field type), uuid (field type)
- **paging** — 003_query (finding), 005_link_usage (finding), 006_pagination (finding), 016_dotted_multi_entity (finding)
- **password** — password (field type)
- **path** — 021_media_resolution (finding), 022_sequence_on_version (finding)
- **percent** — percent (field type)
- **pivot-column** — pivot_column (field type), Shot (entity type)
- **project** — 011_create_project (finding), 018_project_listing (finding), Project (entity type)
- **provenance** — 014_attach_file (finding), 019_create_fields (finding), 001_publish_version_with_media (recipe)
- **published-file** — 021_media_resolution (finding)
- **query** — 003_query (finding), 004_array_vs_hash (finding), 006_pagination (finding), 016_dotted_multi_entity (finding), 017_filter_operators (finding), 018_project_listing (finding), 020_summarize (finding), 021_media_resolution (finding), Step (entity type)
- **recipe** — 001_publish_version_with_media (recipe)
- **schema** — 002_schema (finding), 007_fill_rates (finding), 008_custom_entities (finding), 009_status_lists (finding), 011_create_project (finding), 019_create_fields (finding), 020_summarize (finding), calculated (field type), color (field type), duration (field type), entity_type (field type), jsonb (field type), list (field type), password (field type), pivot_column (field type), serializable (field type), status_list (field type), summary (field type), timecode (field type), uuid (field type), Project (entity type), Step (entity type)
- **sequence** — 022_sequence_on_version (finding), Sequence (entity type)
- **serializable** — jsonb (field type), serializable (field type)
- **shot** — Sequence (entity type), Shot (entity type)
- **status** — 009_status_lists (finding), 010_status_icons (finding), status_list (field type), Asset (entity type), Sequence (entity type), Shot (entity type), Task (entity type), Version (entity type)
- **step** — pivot_column (field type), Step (entity type)
- **storage** — 021_media_resolution (finding)
- **summary** — summary (field type), timecode (field type)
- **task** — Step (entity type), Task (entity type)
- **text** — text (field type)
- **timecode** — timecode (field type)
- **token** — 001_auth (finding)
- **trap** — 004_array_vs_hash (finding), 016_dotted_multi_entity (finding), 018_project_listing (finding), 019_create_fields (finding), calculated (field type), checkbox (field type), color (field type), date (field type), date_time (field type), duration (field type), entity (field type), entity_type (field type), float (field type), image (field type), jsonb (field type), list (field type), multi_entity (field type), number (field type), password (field type), percent (field type), pivot_column (field type), serializable (field type), status_list (field type), summary (field type), text (field type), timecode (field type), url (field type), uuid (field type), Asset (entity type), Project (entity type), Sequence (entity type), Shot (entity type), Step (entity type), Task (entity type)
- **upload** — 013_upload_media (finding), 014_attach_file (finding), 022_sequence_on_version (finding), 001_publish_version_with_media (recipe), image (field type), url (field type)
- **url** — url (field type)
- **uuid** — uuid (field type)
- **version** — 003_query (finding), 005_link_usage (finding), 007_fill_rates (finding), 012_create_version (finding), 013_upload_media (finding), 014_attach_file (finding), 021_media_resolution (finding), 022_sequence_on_version (finding), 001_publish_version_with_media (recipe), url (field type), Version (entity type)
- **write** — 011_create_project (finding), 012_create_version (finding), 013_upload_media (finding), 014_attach_file (finding), 019_create_fields (finding), 022_sequence_on_version (finding), 001_publish_version_with_media (recipe), color (field type), date (field type), date_time (field type), duration (field type), entity (field type), entity_type (field type), float (field type), image (field type), jsonb (field type), list (field type), multi_entity (field type), number (field type), percent (field type), serializable (field type), status_list (field type), text (field type), timecode (field type), url (field type), uuid (field type), Sequence (entity type)
