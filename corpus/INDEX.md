# Corpus index

Read this first. Open an entry only when its one-liner does not already answer the question.

Four ways in, one per thing you already know before you call:

| you know | look under |
|---|---|
| the call you are about to make | **Endpoints** |
| the entity type you are writing | **Entity types** |
| the field's `data_type` | **Field types** |
| the task | **Recipes** |

**Findings** are how the API behaves, grouped by the phase of a session they bite in. **Recipes** are a verified call and its real response.

`silent` is the tag to follow when a call returned 2xx and did nothing.

Every measurement here was taken against **`/api/v1`**. The site's own OpenAPI document advertises `/api/v1.1` instead; the two are the same API, differing only in `api_version` in the root document and the prefix each echoes in its own `links` (`051_api_version`).

## Findings

### auth — getting a token, and what it is

- **001_auth** — Send the token request as `application/x-www-form-urlencoded`: `application/json` is 400 Invalid JSON body. client_credentials returns a 600s bearer, so ignore the refresh_token and re-auth.  
  `auth client token`
- **027_auth_permissions** — The token endpoint also accepts password and session_token, not authorization_code; the bearer is a signed token whose user claim names the caller and the row holding its permission rule set.  
  `auth token permission user client`

### protocol — headers, and what a status code is worth

- **004_array_vs_hash** — api3_array/api3_hash are a POST _search request Content-Type, not a GET Accept header: as Accept they 406, and entity fields are returned under relationships either way.  
  `query header entity-field error-handling trap`
- **028_loud_and_silent** — A 400 is trustworthy and usually names the legal set, but a 200 proves nothing: an unknown field, sort key or query param is a no-op, and a batch can return an id for a row it never made.  
  `query filter sort write operator error-handling trap silent`
- **051_api_version** — /api/v1 and /api/v1.1 are the same API. Across 20 read-only calls the only difference is api_version in the root document and the prefix each echoes in its own links. Any other segment is 404.  
  `discovery client paging protocol`

### schema — what the site has, and adding to it

- **002_schema** — Fetch /schema once for the type list, then /schema/<Type>/fields only for types you actually need: it is the expensive call (48KB, ~330ms each) and must never be looped over all types.  
  `schema cost discovery`
- **008_custom_entities** — Presence in /schema is the enablement test for a custom entity: a slot absent from the listing 404s. Slot numbers are non-contiguous and site-specific, so read name.value and never hardcode one.  
  `schema custom-entity discovery`
- **009_status_lists** — A project's usable statuses are valid_values minus hidden_values, read with project_id: valid_values is identical at every scope, hidden_values is the only thing that varies.  
  `schema status list-field inspector`
- **019_create_fields** — Custom fields are creatable over REST, but you pass a display name and a duplicate silently becomes <name>_1: an idempotent ensure() must read /schema first, never POST-and-hope.  
  `schema write custom-field provenance entity-field trap silent`
- **040_field_revive** — A trashed field is revived by POST /schema/<Type>/fields/<name> with {"revive": true} at 204, but it returns at its original data_type, and a PUT changing data_type is a 200 that does nothing.  
  `schema custom-field create error-handling trap discovery silent`
- **042_spec_coverage** — `GET /spec.json` returns the deployment's own OpenAPI v3 document. It advertises 62 operations against the 23 this corpus covers, and it disagrees with the published documentation.  
  `schema discovery cost`
- **047_site_facts_and_the_working_week** — Three site-fact calls, three different envelopes: `{data, status}`, a bare hash, and JSON:API. Only `/schedule/work_day_rules` reports a bad scope id, and it reports it as a 200.  
  `discovery silent user date error-handling`

### read — getting rows back

- **003_query** — A dotted ?fields path comes back flat under literal key "sg_task.Task.content" in attributes; an entity field is returned under relationships as {data, links}. Never read a row from attributes alone.  
  `query filter dotted-field paging version`
- **005_link_usage** — On the sample project every Version links through `entity` (99% Shot, 1% Asset) and only 1% through `sg_task`, so measure link usage per site rather than hardcoding Task-linking.  
  `version link inspector entity-field paging`
- **006_pagination** — links.next is emitted on every page forever, including zero-row ones, so stop paging when data is empty and never on a missing next.  
  `paging query enumeration`
- **007_fill_rates** — On the sample project 30 of 71 Version fields are populated. Rank by fill rate, but drop checkbox, summary and computed fields first: False and 0 are not null and read as 100% filled.  
  `version inspector schema fill-rate`
- **018_project_listing** — sg_status is not a liveness filter and is null on 15 of 22 projects; is_template, is_demo and archived are the discriminators, so pick the ones your list wants - is_demo hides the demo show.  
  `project query filter inspector list-field trap`
- **021_media_resolution** — PublishedFile.path is returned with the LocalStorage join already done, so a client never reads LocalStorage or reassembles a root, but a platform whose storage root is unset reads null.  
  `version media published-file path storage inspector query`
- **023_pages** — A page's layout is the PageSetting row whose user is null; settings_json reads back as decoded JSON and body/list_content settings.columns is the column list. Every filter on it is ignored.  
  `page query filter schema project inspector trap silent`
- **026_result_order** — Rows come back id ascending unless you sort; ["id", "in", [...]] discards the order of the list, and an unsortable or unknown sort field is a silent 200 no-op where the same name in a filter 400s.  
  `query sort paging filter dotted-field trap silent`
- **048_one_record_beyond_crud** — POST on one record is revive, not update: `?revive=1` is required and the body is ignored. `/<field>` reads image and attachment fields only, and `relationships/<field>` is the same data, unpaged.  
  `page entity-field multi-entity attachment cost discovery silent`

### filter — selecting the rows you want

- **016_dotted_multi_entity** — A dotted path through a multi_entity field reads back nothing: HTTP 200 with the key silently absent from attributes. Filters on that same path work, including two hops.  
  `query dotted-field multi-entity filter paging trap silent`
- **017_filter_operators** — is/is_not/contains/not_contains/starts_with/ends_with/in/not_in all work, on text fields and through dotted paths; an unknown operator 400s on all 21 data types, naming the valid list on 16.  
  `query filter operator dotted-field entity-field error-handling silent`
- **020_summarize** — _summarize needs the same vendor Content-Type as _search, and one `grouping` call returns a field's distinct-value count and its empty count. At ~300ms a field, rank a shortlist, never scan.  
  `query inspector fill-rate schema cost list-field`
- **030_complex_filters** — api3_hash nests and/or groups 265 deep and mixes leaves with sub-groups; api3_array cannot express or, query-string filter[] is ignored on _search, and {path,relation,values} runs nowhere.  
  `query filter operator header page error-handling trap silent`
- **046_search_without_a_path** — `/hierarchy/_expand` and `/hierarchy/_search` refuse the vendor content types every other POST requires and take `application/json` alone, so one shared POST helper 415s on half the API.  
  `query filter header project trap`

### write — creating and updating

- **011_create_project** — A script user can create a Project with nothing but {"name": ...}, at 201, but the response echoes only 6 attributes, so read the project back if you need anything else.  
  `write project create schema`
- **012_create_version** — The schema's mandatory flags are not the create contract: on every project-scoped type measured, `project` is required and the identity field is optional, server-generated and not unique.  
  `write version create entity-field`
- **024_read_after_write** — Every write ignores ?fields. A create returns what you sent plus the server defaults, an update returns the whole record, and neither resolves a dotted path, so re-read for those and after an upload.  
  `write create batch upload async entity-field trap silent`
- **045_webhooks** **[partial]** — The hook contract validates the url and the entity type, and silently accepts a field name, a project id and an entity-type count it will never honour. test_connection answers 204 for any uuid.  
  `webhook silent trap create write delivery error-handling token`  
  not measured: No entity event reached a hook on the probed site, so the delivery payload, the `X-SG-SIGNATURE` and `x-sg-event-batch-*` headers, and `batch_deliveries`, are all unrecorded.
- **050_webhook_subscriptions** — entity_types and event_type are mutually exclusive and one 400 covers giving neither and giving both. revive is a fourth action, and every entity the guide calls excluded is accepted at 201.  
  `webhook silent trap create error-handling enumeration`

### upload — getting bytes in and out

- **013_upload_media** — Media upload is three calls: GET `{field}/_upload`, PUT the bytes, POST `links.complete_upload`. Transcoding is async: poll until the field stops reading `/images/status/transient/`.  
  `write upload media attachment version async`
- **014_attach_file** — Leave the field out of the _upload path and the file is stored as an Attachment on attachment_links; read it back with POST /entity/attachments/_search, never flat filter[].  
  `write upload attachment provenance version multi-entity filter header`
- **022_sequence_on_version** — sg_uploaded_movie is single-valued, and replacing it leaves sg_uploaded_movie_mp4 describing the old file while status reads 1. A sequence belongs in sg_path_to_frames.  
  `version media upload sequence path attachment write`
- **039_upload_silent_failures** — complete_upload returns 201 and creates an Attachment even when the bytes were never PUT, and file_size is null on a good upload too, so only fetching the stored file proves it exists.  
  `media attachment upload error-handling trap note silent`
- **044_multipart_upload** — `multipart_upload=true` on the init sets `upload_id` and adds `links.get_next_part`. Every part but the last must be at least 5 MiB, and completion needs an `etags` array inside `upload_info`.  
  `multipart upload etag storage`

### observe — what changed

- **025_event_log** **[partial]** — meta.old_value and meta.new_value answer "what was this before", but meta is unfilterable and unsortable: narrow on entity, event_type and attribute_name, sort -id, read meta yourself.  
  `event-log query filter operator paging write create serializable status trap silent`  
  not measured: Whether event_type or meta can be set in the create body is untried: testing it costs another permanent row. Every event read was generated by another user; probe 049 covers the script's own.
- **043_attention** — The six attention calls share no convention with the rest of the API: no paging, no `fields`, `links.self` spelled `/entity/Shot/7668`, and a missing record id on activity_stream is a 500.  
  `follow user note reply paging header async trap silent`
- **049_script_events** — A script's writes reach the event log only while its ApiUser has generate_event_log_entries True. The default is False and nothing errors when off. One create logs one row per field plus one _New.  
  `event-log permission write silent trap observe auth`

### render — showing it to a person

- **010_status_icons** — Status.icon is an entity link under relationships; display_type picks one of three renderings, and stock icons are absent from the API but reachable via the sprite in the site's own stylesheet.  
  `status icon cache colour entity-field`

## Field types

One per `data_type`: how it reads, writes, clears and filters. `field_types/<type>`.

- **calculated** — A calculated field refuses every write with "is read only" and every filter with "cannot be used in a filter", yet it sorts and summarizes fine, and the formula is exposed as calculated_function.  
  `inspector read-only`
- **checkbox** — A checkbox is two-state, never null - an untouched row already reads false, null is unwritable and unfilterable, and the only relations are is/is_not, so fill rate reads 100% on every checkbox.  
  `fill-rate inspector`
- **color** — `Task.color` holds the token `pipeline_step` rather than a colour: read `step.Step.color` in the same dotted call and keep a client default. A real value is decimal r,g,b, never hex.  
  `colour`
- **date** — A date is the string "YYYY-MM-DD" and nothing else: any timestamp 400s on write and as a filter value. Every negating operator (is_not, not_in, not_in_last) also matches rows that are null.  
  `date`
- **date_time** — Stored and read as UTC `YYYY-MM-DDTHH:MM:SSZ`: a written offset is silently normalised, a zoneless string is taken as UTC, and a date-only filter value means midnight UTC, not the whole day.  
  `date`
- **duration** — A duration is a bare integer of minutes and the unit is on the site: `GET /preferences` gives `hours_per_day` and `duration_units`. A Float truncates toward zero at 200, so round before writing.  
  `number duration`
- **entity** — An entity link is a {type,id} hash under `relationships`, cleared only by null. Enforce `valid_types` yourself: it binds on a few fields, is ignored on most, and nothing in the schema marks which.  
  `dotted-field entity-field`
- **entity_type** — An entity_type field is a bare schema-name string in attributes, validated on write against 290 built-in type names but not against the site's enabled ones, and filtered only by is/is_not/in/not_in.  
  `entity-field custom-entity`
- **float** — A float reads back as a JSON string rounded to 6 decimals and rejects Integer on both write and filter: send 1.0 or "1.0", never 1; 0.0 and null stay distinct, and 1e-9 silently becomes 0.0.  
  `error-handling silent`
- **image** — Only the upload dance sets an image: every value but null 400s, and clearing it also clears `filmstrip_image`. The value is a presigned URL re-signed per read, so store the row id, never the string.  
  `media upload async destructive image`
- **jsonb** — jsonb filters, where serializable cannot: is, is_not, contains, not_contains, values always hashes. Note.meta stores what you send but is create-only, so nothing written there is ever editable.  
  `serializable error-handling jsonb`
- **list** — A list is one bare string in attributes; a write outside valid_values 400s and is case-sensitive, while filters are case-insensitive and only is/is_not/in/not_in exist.  
  `list-field`
- **multi_entity** — A bare list replaces the whole link set, but {"multi_entity_update_mode": "add"|"remove"|"set", "value": [...]} adds and removes in place; the field never reads null and null 400s.  
  `entity-field dotted-field silent destructive multi-entity`
- **number** — A number is a signed 32-bit integer: floats 400, 2**31 is "integer out of range", and 0 is not null, yet is_not and not_in match null rows while greater_than and less_than do not.  
  `fill-rate number`
- **password** — A password field reads as a constant seven-asterisk mask on every row, including through a dotted path; it cannot be filtered, sort is accepted and ignored, and it must never be written.  
  `dotted-field inspector silent read-only`
- **percent** — A percent is a bare integer on a 0-100 scale (50% is 50, and 0.5 is rejected as Float), but nothing is clamped, so -1, 1000 and 2**31-1 all store at HTTP 200.  
  `number fill-rate`
- **pivot_column** — A pivot_column is a web-UI task rollup with no REST implementation - it reads null on every row, and write, filter, sort and _summarize each fail with a different error.  
  `step inspector pivot-column read-only`
- **serializable** — No operator works on a serializable field: every filter 400s as unfilterable. Task.splits answers a well-formed array of hashes with 200 while storing null, so REST cannot write it.  
  `error-handling silent serializable read-only`
- **status_list** — REST does not enforce hidden_values: a project-hidden status writes and reads back fine, so every client must subtract it itself. Only valid_values is enforced.  
  `status list-field`
- **summary** — A summary field is a live rollup: refused on write even where editable=true, unfilterable, unsortable, and null on every custom one here, so re-run the query /schema exposes to select on it.  
  `fill-rate inspector summary read-only`
- **text** — A text field has no empty string: writing "" stores null, so `is ""` and `is None` are one filter; matching is case-insensitive, whitespace is stripped, and a non-string 400s.  
  ``
- **timecode** — A timecode stores milliseconds as a signed 32-bit integer. No schema or preference names its frame rate, but a _summarize group_name renders `HH:MM:SS:FF` and the rate solves out of that.  
  `number media summary timecode`
- **url** — The value is a presigned link re-minted on every read and expiring on `X-Amz-Expires`, so persist the Attachment id and re-read. No filter relation exists at all, and sort is a 200 no-op.  
  `media upload attachment version silent url`
- **uuid** — A uuid field is server-generated and rejects every write with "is read only", so it cannot hold your key; it filters on is/is_not/in/not_in only, and a malformed value 400s.  
  `read-only`

## Entity types

One per standard entity type: what it is, how it is identified, created and linked. `entity_types/<Type>`.

- **Asset** — Only project is required to create an Asset; omit code and the server writes "New Asset <id>", and two assets in one project may share a code, so key on id and never on code.  
  `list-field`
- **Attachment** — POST /entity/attachments answers 201 on an empty body and returns a row with no file; this_file is editable on create only, so bytes reach a site through the upload dance and never through a create.  
  `upload media url attachment`
- **Cut** — A Cut stores an edit, it does not model one: no field is computed or validated, and `cut_items` is returned sorted by the item's display name rather than by `cut_order`.  
  `timecode list-field cut`
- **CutItem** — Nothing on a CutItem is unique and `code` repeats across Cuts, so an id found by a code search may sit on another Cut: check `cut` before every update or the write lands on the wrong edit.  
  `cut timecode filter operator dotted-field`
- **Delivery** — Delivery has two independent Version links, sg_versions and version_sg_deliveries_versions; writing one leaves the other empty, and only the second mirrors Version.sg_deliveries.  
  `version published-file reply attachment list-field filter delivery`
- **Note** — A Note is titled by `subject` and bodied by `content`; only `project` is required to create one, `attachments` link in that same call, and a bare write to `replies` destroys the Reply rows.  
  `attachment jsonb destructive note`
- **Playlist** — Playlist.versions reads back sorted by the Version's code, never in the order written; the human order is sg_sort_order on PlaylistVersionConnection, which a write through the field leaves null.  
  `version silent playlist`
- **Project** — Project is site-wide and has no `project` field, so a scoping filter 400s on it; `name` is the identity, the only field both mandatory and unique, and `code` is a second unique text field.  
  `filter project`
- **PublishedFile** — Only `project` is required to create a PublishedFile, and nothing is unique: the same name, version_number and path publish twice at 201, so read the last version before writing the next.  
  `path storage dependency published-file`
- **PublishedFileType** — PublishedFileType is site-wide with no project field, so a publish that creates one on an unknown extension adds it to every project; `code` is the identity and the only unique field.  
  `published-file enumeration filter silent`
- **Reply** — Reply is site-wide with no project field, and entity accepts almost every type on the site, not only Note; send entity on create, because a Reply whose entity is null cannot be deleted.  
  `note query filter silent destructive reply`
- **Sequence** — A Sequence needs `project`, not `code`, and project alone names it `New Sequence <id>`; `shots` is the reverse of `Shot.sg_sequence`, one link, so a Shot sits in exactly one Sequence.  
  `shot write dotted-field silent sequence`
- **Shot** — A Shot needs only `project` on create, and `code` is flagged mandatory, is optional and is not unique: an omitted one becomes "New Shot <id>" and a re-run duplicates rows. Send `code`, key on `id`.  
  `pivot-column shot`
- **Step** — Step is site-wide with no project field, partitioned only by entity_type; list the Steps for a Shot with entity_type is "Shot", and treat neither code nor short_name as unique.  
  `task filter query silent step`
- **Task** — A Task is named by `content`, never `code`; a create needs only `project`; `start_date`, `due_date` and `duration` are one triple the server recomputes on every write.  
  `dependency duration task`
- **TimeLog** — A TimeLog create requires only `project`; `date` defaults to the server's today instead of failing, `entity` takes any type despite valid_types ['Task'], and a script may log for any HumanUser.  
  `task duration`
- **Version** — The schema inverts the create contract: `project` is required and `code` is not, generated as "New Version <id>" when omitted. `code` is not unique, so key on `id`.  
  `media link version`

## Recipes

- **001_publish_version_with_media** — Publish a generated image to Flow PT as a Version, with provenance and the workflow attached  
  `write version upload attachment provenance`
- **002_batch** — Apply many creates, updates and deletes in one atomic call, and match the results back to the requests  
  `write batch create version shot error-handling silent`
- **003_query_fields_and_pages** — Resolve a query field's value, and run the rows a saved Page shows  
  `query filter summary page schema operator dotted-field`
- **004_register_published_file** — Register the next PublishedFile without overwriting the last one, and write a path the server resolves for every platform  
  `write published-file path storage version create entity-field`
- **005_propagate_status** — Roll a status up from a parent's Tasks and Versions onto the parent, without racing a concurrent write  
  `write status task version shot schema batch filter silent`
- **006_media_round_trip** — Take media off one Version and put the same bytes on another, which is what every sync, transfer and hand-off does  
  `write version media upload attachment url image async`
- **007_build_and_reconcile_a_cut** — Write a Cut and its CutItems from an edit, read the timeline back, and reconcile a second edit against the Cut already there  
  `write cut timecode version shot batch filter entity-field multi-entity`
- **008_delivery_progress** — Keep a Delivery honest about what a long transfer is doing, including when it is cancelled and when it crashes  
  `write delivery status list-field reply upload attachment version error-handling`
- **009_multi_entity_safely** — Add to and remove from a multi_entity field without destroying the links you did not mean to touch  
  `write multi-entity entity-field playlist note version filter silent destructive`
- **010_status_picker** — List the statuses a project actually offers, each with the label, colour and icon needed to draw it  
  `status icon colour schema list-field entity-field dotted-field project cache`
- **011_audit_webhook_subscriptions** — Inventory every webhook subscription on a site, and see which have ever delivered  
  `webhook read-only permission silent`

## Endpoints

One card per call: what it takes, what it answers, a real response and the edge cases that live on the call. `endpoints/<slug>`.

58 of 64 have a finding or recipe behind them as well. A card with none is documented and not yet probed, which is the queue.

59 cards are marked `measured`: every call on them was made and answered. 5 are marked `partial` or `untested` and say on the card what was not reached.

Those 5 are all in the webhook family, and they are blocked on the site rather than on the work: entity events reach no hook on the probed site, so the delivery payload, `X-SG-SIGNATURE` and the batch headers cannot be recorded here (`045_webhooks`). **If you run a site where webhooks deliver, these are the entries to contribute.** A probe and a recorded response is the whole ask.

### Session

- **`GET /`** — The site's login configuration, answered without a token. Read `user_authentication_method` here before choosing a grant type.  
  `auth discovery`  
  also: 027_auth_permissions (finding), 051_api_version (finding)
- **`POST /auth/access_token`** — Form-encode it. `application/json` is 415 naming the one legal type, and the 600s bearer is cheaper to re-mint than the refresh_token is to use.  
  `auth token client`  
  also: 001_auth (finding), 027_auth_permissions (finding)

### Site

- **`GET /license_info`** — Seat counts in a `{data, status}` envelope, not the JSON:API one. `rule` decides whether `free` is a number or `-1` for unlimited, and none of the three counts equals the HumanUser row count.  
  `discovery user read-only`  
  also: 047_site_facts_and_the_working_week (finding)
- **`GET /preferences`** — The only place the unit behind a `duration` field is named. `prefs` narrows it to one key, and `hours_per_day` and `duration_units` are the pair a renderer needs.  
  `schema duration discovery`  
  also: 002_schema (finding)
- **`PUT /preferences/update`** — Enables a custom entity slot and nothing else. On the probed site every body, valid or not, answered 400 code 111 `Updating the preferences is not available`, so the shape stays unverified.  
  `custom-entity write error-handling permission`  
  also: 047_site_facts_and_the_working_week (finding)
- **`GET /schedule/work_day_rules`** — One row per calendar day, both ends inclusive, no paging at 730 rows. A `project_id` or `user_id` that does not exist answers 200 with the studio default instead of an error.  
  `date discovery silent read-only`  
  also: 047_site_facts_and_the_working_week (finding)
- **`PUT /schedule/work_day_rules`** — One day per call, keyed by `date` in the body rather than by a path id, and `user_id` or `project_id` absent means the change applies to the studio default for everyone.  
  `date write error-handling project user`  
  also: 047_site_facts_and_the_working_week (finding)
- **`GET /spec.<format>`** — The site publishes its own OpenAPI v3 document, `json` or `yaml`, and it lists 62 operations where this corpus covers 23. The suffix is required and any other 406s.  
  `schema discovery cost`  
  also: 042_spec_coverage (finding), 051_api_version (finding)
- **`GET /subscription_seat/user_subscriptions`** — Returns a bare hash of user id to subscription string with no `data` and no `links`, holding only some HumanUser rows, and a `null` value means the user has no subscription rather than no such user.  
  `discovery user read-only`  
  also: 047_site_facts_and_the_working_week (finding)
- **`POST /subscription_seat/user_subscriptions`** — Body is a bare hash of user id to subscription string, not a JSON:API document. An unknown id is a whole-request 400, and a hash naming no user is a 200 returning `{}`.  
  `discovery user write error-handling`  
  also: 047_site_facts_and_the_working_week (finding)

### Schema

- **`GET /schema`** — The enabled type list, and the enablement test for a `CustomEntityNN`: a slot absent here 404s everywhere. 12KB, so fetch it once and never loop it into `/fields`.  
  `schema custom-entity discovery cost`  
  also: 002_schema (finding), 008_custom_entities (finding)
- **`GET /schema/<Type>`** — One type's display name without its 48KB of fields, and the cheapest existence check there is: an unknown or unenabled type is 404 `Entity type 'X' does not exist.`  
  `schema custom-entity discovery`  
  also: 002_schema (finding), 028_loud_and_silent (finding)
- **`GET /schema/<Type>/fields`** — Every field on one type with its `data_type`, `editable` and `mandatory`. The expensive call at 48KB and ~330ms, so fetch the types you need and never loop the `/schema` listing into it.  
  `schema cost fill-rate discovery`  
  also: 002_schema (finding), 007_fill_rates (finding), 011_create_project (finding), 012_create_version (finding), 019_create_fields (finding), 023_pages (finding), 025_event_log (finding)
- **`POST /schema/<Type>/fields`** — You send a display name and the server derives the `sg_` name, which is only in `links.self`. A duplicate display name is 201 with a silent `_1` suffix, so read `/fields` first.  
  `schema custom-field create silent destructive`  
  also: 019_create_fields (finding), 040_field_revive (finding)
- **`GET /schema/<Type>/fields/<field>`** — One field's properties, at 1211 bytes against 48KB for the whole type. Pass `project_id` or `hidden_values` is empty and your status picker offers statuses the project refuses.  
  `schema status list-field`  
  also: 002_schema (finding), 009_status_lists (finding), 049_script_events (finding), 003_query_fields_and_pages (recipe), 005_propagate_status (recipe), 008_delivery_progress (recipe), 010_status_picker (recipe)
- **`POST /schema/<Type>/fields/<field>`** — Revive a retired field, at 204. It is the only way to get a burnt name back, and it returns at its original `data_type` whatever the site wants now.  
  `schema custom-field discovery`  
  also: 040_field_revive (finding)
- **`PUT /schema/<Type>/fields/<field>`** — Changes a field's properties. A body changing `data_type` is a 200 that does nothing, so read the field back rather than trusting the status code.  
  `schema custom-field silent`  
  also: 040_field_revive (finding)
- **`DELETE /schema/<Type>/fields/<field>`** — Retires a field at 204 and burns its programmatic name forever: the same name will not create again, only revive. Treat this as irreversible from REST.  
  `schema custom-field destructive`  
  also: 019_create_fields (finding), 040_field_revive (finding)

### Records

- **`GET /entity/<type>`** — Pages rows. An entity field is returned under `relationships` and never `attributes`, an unknown `fields` name is dropped at 200, and `links.next` is emitted on empty pages forever.  
  `query paging filter entity-field silent`  
  also: 001_auth (finding), 003_query (finding), 004_array_vs_hash (finding), 005_link_usage (finding), 006_pagination (finding), 007_fill_rates (finding), 010_status_icons (finding), 011_create_project (finding), 016_dotted_multi_entity (finding), 018_project_listing (finding), 023_pages (finding), 026_result_order (finding), 027_auth_permissions (finding), 028_loud_and_silent (finding), 030_complex_filters (finding), 051_api_version (finding), 004_register_published_file (recipe)
- **`POST /entity/<type>`** — `project` is the requirement on every project-scoped type and the identity field is not, whatever the schema says. `?fields` is ignored, and the 201 returns the whole record.  
  `write create entity-field silent`  
  also: 011_create_project (finding), 012_create_version (finding), 024_read_after_write (finding), 025_event_log (finding), 049_script_events (finding), 001_publish_version_with_media (recipe), 004_register_published_file (recipe), 007_build_and_reconcile_a_cut (recipe), 008_delivery_progress (recipe)
- **`GET /entity/<type>/<id>`** — One row, and the only read where `fields` is honoured on a single record. A retired row is 404 here and 200 under `options[return_only]=retired`.  
  `query entity-field`  
  also: 003_query_fields_and_pages (recipe), 005_propagate_status (recipe), 006_media_round_trip (recipe), 007_build_and_reconcile_a_cut (recipe), 009_multi_entity_safely (recipe)
- **`POST /entity/<type>/<id>`** — Revives a retired row. `?revive=1` is required and any JSON body is discarded, so this is not an update via POST.  
  `write trap`  
  also: 048_one_record_beyond_crud (finding)
- **`PUT /entity/<type>/<id>`** — Updates and returns the whole record, 77 attribute keys for a Shot. A key left out of the body is unchanged rather than cleared, and an empty body is a 200 no-op.  
  `write silent`  
  also: 024_read_after_write (finding), 028_loud_and_silent (finding), 049_script_events (finding), 049_script_events (finding), 004_register_published_file (recipe), 006_media_round_trip (recipe), 008_delivery_progress (recipe), 009_multi_entity_safely (recipe)
- **`DELETE /entity/<type>/<id>`** — Retires a row at 204 with an empty body. It is not erased: the row reads 404 normally and 200 under `options[return_only]=retired`, and a second delete is 404.  
  `write destructive`  
  also: 024_read_after_write (finding), 025_event_log (finding), 049_script_events (finding)
- **`GET /entity/<type>/<id>/<field>`** — Reads one image or attachment field, and with `?alt` redirects to the bytes. Every other data type is a 400, so this is not a cheap single-field read.  
  `attachment media image trap`  
  also: 048_one_record_beyond_crud (finding)
- **`GET /entity/<type>/<id>/relationships/<related_field>`** — The `entity` or `multi_entity` link list on its own, unpaged and unsorted. `page`, `fields` and `sort` are accepted and ignored, and every link is returned in one body.  
  `entity-field multi-entity cost`  
  also: 048_one_record_beyond_crud (finding)
- **`POST /entity/_batch`** — The key is `requests`, not `data`, and sending `data` is 400 `requests is missing`. It answers 200 rather than 201, and one bad request rolls the whole batch back.  
  `write batch create silent`  
  also: 024_read_after_write (finding), 028_loud_and_silent (finding), 002_batch (recipe), 005_propagate_status (recipe), 007_build_and_reconcile_a_cut (recipe)
- **`PUT /entity/projects/<id>/_update_last_accessed`** — Stamps one user's last visit to a project. Write-only: a `user_id` that does not exist answers the same 200, and nothing readable over REST changes.  
  `project user silent`  
  also: 048_one_record_beyond_crud (finding)

### Search

- **`POST /entity/<type>/_search`** — The only way to send a filter the query string cannot express, and it refuses `application/json` at 415 naming both vendor types. `api3_array` cannot express `or`; `api3_hash` nests.  
  `query filter operator header paging silent`  
  also: 003_query (finding), 004_array_vs_hash (finding), 006_pagination (finding), 014_attach_file (finding), 016_dotted_multi_entity (finding), 017_filter_operators (finding), 018_project_listing (finding), 021_media_resolution (finding), 023_pages (finding), 025_event_log (finding), 026_result_order (finding), 028_loud_and_silent (finding), 030_complex_filters (finding), 049_script_events (finding), 003_query_fields_and_pages (recipe), 004_register_published_file (recipe), 005_propagate_status (recipe), 007_build_and_reconcile_a_cut (recipe), 009_multi_entity_safely (recipe), 010_status_picker (recipe)
- **`POST /entity/<type>/_summarize`** — Counts without paging rows. One `grouping` returns a field's distinct values and their counts at ~300ms, so rank a shortlist with it and never scan every field.  
  `query fill-rate cost list-field summary`  
  also: 006_pagination (finding), 020_summarize (finding), 021_media_resolution (finding), 028_loud_and_silent (finding), 030_complex_filters (finding), 003_query_fields_and_pages (recipe)
- **`POST /entity/_text_search`** — Free-text search across several types at once, returning a flattened row that is not the `_search` shape. `entity_types` is required and its value doubles as the per-type filter.  
  `query filter header silent`  
  also: 046_search_without_a_path (finding)
- **`POST /hierarchy/_expand`** — Returns one level of the navigation tree the web interface draws. It refuses the vendor content types every other POST requires and accepts only `application/json`.  
  `query header project trap`  
  also: 046_search_without_a_path (finding)
- **`POST /hierarchy/_search`** — Answers where a row sits in the navigation tree. `search_criteria` must be a hash keyed exactly `entity`, and every other shape is the same misleading `size must be 1`.  
  `query header project trap`  
  also: 046_search_without_a_path (finding)

### Media

- **`GET /entity/<type>/<id>/<field>/_upload`** — Step one of three. `filename` is a required query parameter and its absence is 400 `filename is missing`; the reply holds `links.upload` and a `links.complete_upload` already prefixed with `/api/v1`.  
  `upload media image async`  
  also: 013_upload_media (finding), 022_sequence_on_version (finding), 044_multipart_upload (finding), 001_publish_version_with_media (recipe), 006_media_round_trip (recipe)
- **`POST /entity/<type>/<id>/<field>/_upload`** — The path behind `links.complete_upload`. `upload_info` is the init reply verbatim, plus an `etags` array when the init was multipart; `upload_data` is where `display_name` and `tags` are set.  
  `multipart etag attachment`  
  also: 044_multipart_upload (finding)
- **`PUT /entity/<type>/<id>/<field>/_upload`** — The `storage_service: "sg"` upload target, on the Flow PT host. A site on `s3` returns an S3 `links.upload` instead, and calling this route directly is 400 for four missing signature parameters.  
  `storage media`  
  *no finding yet*
- **`GET /entity/<type>/<id>/<field>/_upload/multipart`** — Step two of a multipart transfer, once per part after the first. Walk `links.get_next_part` rather than building it: each reply holds the part's presigned `upload` and the link to the part after.  
  `multipart etag`  
  also: 044_multipart_upload (finding)
- **`POST /entity/<type>/<id>/<field>/_upload/multipart_abort`** — 204 and an empty body. The body is the `upload_info` object flat at the top level, not the `{"upload_info": ..., "upload_data": ...}` wrapper the spec declares, which returns 400.  
  `multipart storage`  
  also: 044_multipart_upload (finding)
- **`GET /entity/<type>/<id>/_upload`** — The same handshake with the field left out of the path, which stores the bytes as an Attachment on `attachment_links` rather than on a field. The type must actually have that field.  
  `upload attachment provenance`  
  also: 014_attach_file (finding), 039_upload_silent_failures (finding), 001_publish_version_with_media (recipe), 008_delivery_progress (recipe)
- **`POST /entity/<type>/<id>/_upload`** — The fieldless completion, `/entity/<type>/<id>/attachments/_upload`. Same body contract as the field form, including `etags` for a multipart init; the row lands on `attachment_links`.  
  `multipart attachment note`  
  *no finding yet*
- **`PUT /entity/<type>/<id>/_upload`** — The fieldless `storage_service: "sg"` upload target. The spec declares only `filename` and `signature`, and the site asks for `user_id`, `user_type` and `expiration` as well.  
  `storage attachment`  
  *no finding yet*
- **`GET /entity/<type>/<id>/_upload/multipart`** — The fieldless part chain, `/entity/<type>/<id>/attachments/_upload/multipart`. Same four checked parameters and the same unchecked `upload_id` as the field form.  
  `multipart attachment`  
  *no finding yet*
- **`POST /entity/<type>/<id>/_upload/multipart_abort`** — The fieldless abort, `/entity/<type>/<id>/attachments/_upload/multipart_abort`. 204 on the flat `upload_info` object, identical to the field form in every respect but the path.  
  `multipart note`  
  *no finding yet*
- **`POST /transcode/attachment_metadata/<id>`** — Records video metadata for media transcoded outside Flow PT. 200 with a body of one space, and none of the six values reads back on the Attachment; only `updated_at` moves.  
  `transcode media async silent`  
  *no finding yet*
- **`POST <links.complete_upload>`** — Step three, at 201 with a body of a single space. Not JSON, and it never names the row it created, so parsing it crashes after the write has landed.  
  `upload attachment async silent`  
  also: 013_upload_media (finding), 014_attach_file (finding), 022_sequence_on_version (finding), 024_read_after_write (finding), 039_upload_silent_failures (finding), 001_publish_version_with_media (recipe), 006_media_round_trip (recipe), 008_delivery_progress (recipe)
- **`PUT <links.upload>`** — Step two, to storage rather than to Flow PT, with no Authorization header. It is the only step that moves bytes, and skipping it still lets step three answer 201.  
  `upload media attachment silent`  
  also: 013_upload_media (finding), 014_attach_file (finding), 039_upload_silent_failures (finding), 001_publish_version_with_media (recipe), 006_media_round_trip (recipe), 008_delivery_progress (recipe)

### Attention

- **`GET /entity/<type>/<id>/activity_stream`** — The feed the web application draws, paged by `max_id` and `min_id` rather than by `page[]`. A record id that is not there answers 500, not the 404 the spec advertises.  
  `follow paging user async trap`  
  also: 043_attention (finding)
- **`GET /entity/<type>/<id>/followers`** — The HumanUsers watching one record, whole and unpaged, with `name` the only attribute. `links.self` is spelled `/entity/HumanUser/<id>`, singular and CamelCase.  
  `follow user paging note`  
  also: 043_attention (finding)
- **`PUT /entity/<type>/<id>/unfollow`** — Removes one named user from one record at 204, and answers 204 again when that user was never following. It is PUT on the record, the mirror image of the POST on the user that follows.  
  `follow user silent error-handling`  
  also: 043_attention (finding)
- **`POST /entity/human_users/<user_id>/follow`** — Subscribes one HumanUser to a list of records at 204. `entity` must be the CamelCase schema name: the snake_case plural every path uses answers 500, and a bad id in the list 404s after applying the good ones.  
  `follow user header error-handling silent trap`  
  also: 043_attention (finding)
- **`GET /entity/human_users/<user_id>/following`** — Everything one HumanUser follows, unpaged in a single body, filterable only by `entity` and `project_id`. An ApiUser id is a 404, so a script has no follow list of its own.  
  `follow user paging project cost`  
  also: 043_attention (finding)
- **`GET /entity/notes/<id>/thread_contents`** — A Note, its Attachments and its Replies as one flat list in time order. The Note and the Attachments name their author under `created_by`, a Reply names it under `user`.  
  `note reply attachment user`  
  also: 043_attention (finding)

### Webhooks

- **`GET /webhook/deliveries/<record_uuid>`** **[partial]** — Returns one delivery record with ten keys. `status` is `delivered` even when nothing answered, so read `response_code`, which is 0 when no response was received.  
  `webhook delivery error-handling`  
  not measured: Measured against a Webhook_Status_Change delivery to a dead host. request_headers, response_headers, body and a non-zero response_code are unmeasured.  
  also: 045_webhooks (finding)
- **`PUT /webhook/deliveries/<record_uuid>`** **[partial]** — Answers 200 for an empty body, for a key it does not take, and for a valid acknowledgement that then reads back null. Only the 4096-byte cap is enforced.  
  `webhook delivery silent trap`  
  not measured: The acknowledgement never persisted on the probed site, where the webhook subsystem is degraded. Whether that is the API or the site is unresolved.  
  also: 045_webhooks (finding)
- **`POST /webhook/deliveries/<record_uuid>/redeliver`** **[partial]** — Answers 204 with no body. On the probed site no second delivery record followed, so 204 reports that the request was accepted and nothing more.  
  `webhook delivery silent`  
  not measured: Answers 204 and produced no second delivery on the probed site. Whether it redelivers anywhere is unmeasured.  
  also: 045_webhooks (finding)
- **`GET /webhook/hooks`** — Lists every hook on the site, not only this script's. `status` takes active or disabled and a value no hook has answers 200 with zero rows rather than 400.  
  `webhook paging silent`  
  also: 045_webhooks (finding), 011_audit_webhook_subscriptions (recipe)
- **`POST /webhook/hooks`** — `url` and `entity_types` are required and the entity type and action are checked. A field name, a project id and a second entity type are all accepted without being checked.  
  `webhook create silent trap token`  
  also: 045_webhooks (finding), 050_webhook_subscriptions (finding)
- **`GET /webhook/hooks/<hook_id>/deliveries`** **[partial]** — Takes status, entity_type, entity_id, from and acknowledgement as query params and answers 200 with zero rows for any of them. No delivery was observed, so the record shape is unprobed.  
  `webhook delivery paging filter`  
  not measured: Only Webhook_Status_Change deliveries were observed. The record for an entity event, and every field that only an answering consumer fills, are unmeasured.  
  also: 045_webhooks (finding), 011_audit_webhook_subscriptions (recipe)
- **`GET /webhook/hooks/<record_uuid>`** — Returns the hook without its token. A well-formed uuid naming nothing answers 404 code 104, a segment that is not a uuid answers 404 code 103 with `detail` null.  
  `webhook error-handling`  
  also: 045_webhooks (finding), 050_webhook_subscriptions (finding), 011_audit_webhook_subscriptions (recipe)
- **`PUT /webhook/hooks/<record_uuid>`** — A partial body edits only the keys it names. An empty body is 400, and `status` takes active or disabled and names both in the error.  
  `webhook write status`  
  also: 045_webhooks (finding)
- **`DELETE /webhook/hooks/<record_uuid>`** — 204 and the hook is gone at once: the hook, its deliveries listing and a second delete all answer 404 immediately after.  
  `webhook destructive`  
  also: 045_webhooks (finding), 050_webhook_subscriptions (finding)
- **`POST /webhook/hooks/<record_uuid>/test_connection`** **[partial]** — Answers 204 for any uuid, a hook that does not exist included, and confirms nothing about the hook, the endpoint or whether anything was sent.  
  `webhook silent trap`  
  not measured: Answers 204 for any uuid and produced no delivery record on the probed site. What it does on a working site is unmeasured.  
  also: 045_webhooks (finding)

### Exports

- **`GET /exports/page/<page_id>.<format>`** — Exports a page's default view. Off unless a site admin marked the view exportable: on the probed site all 52 pages sampled answered 422, and no field says which pages will work.  
  `page error-handling`  
  also: 048_one_record_beyond_crud (finding)
- **`GET /exports/page/<page_id>/<layout_name>.<format>`** — The same export addressed at one named view, needed when a page has several. A layout name that does not exist is indistinguishable from one that does, because both answer the page-level 422.  
  `page`  
  also: 048_one_record_beyond_crud (finding)


## By tag

- **async** — 013_upload_media (finding), 024_read_after_write (finding), 043_attention (finding), 006_media_round_trip (recipe), image (field type), get_entity_type_id_field_upload (endpoint), post_transcode_attachment_metadata_id (endpoint), post_links_complete_upload (endpoint), get_entity_type_id_activity_stream (endpoint)
- **attachment** — 013_upload_media (finding), 014_attach_file (finding), 022_sequence_on_version (finding), 039_upload_silent_failures (finding), 048_one_record_beyond_crud (finding), 001_publish_version_with_media (recipe), 006_media_round_trip (recipe), 008_delivery_progress (recipe), url (field type), Attachment (entity type), Delivery (entity type), Note (entity type), get_entity_type_id_field (endpoint), post_entity_type_id_field_upload (endpoint), get_entity_type_id_upload (endpoint), post_entity_type_id_upload (endpoint), put_entity_type_id_upload (endpoint), get_entity_type_id_upload_multipart (endpoint), post_links_complete_upload (endpoint), put_links_upload (endpoint), get_entity_notes_id_thread_contents (endpoint)
- **auth** — 001_auth (finding), 027_auth_permissions (finding), 049_script_events (finding), get_root (endpoint), post_auth_access_token (endpoint)
- **batch** — 024_read_after_write (finding), 002_batch (recipe), 005_propagate_status (recipe), 007_build_and_reconcile_a_cut (recipe), post_entity_batch (endpoint)
- **cache** — 010_status_icons (finding), 010_status_picker (recipe)
- **client** — 001_auth (finding), 027_auth_permissions (finding), 051_api_version (finding), post_auth_access_token (endpoint)
- **colour** — 010_status_icons (finding), 010_status_picker (recipe), color (field type)
- **cost** — 002_schema (finding), 020_summarize (finding), 042_spec_coverage (finding), 048_one_record_beyond_crud (finding), get_spec_format (endpoint), get_schema (endpoint), get_schema_type_fields (endpoint), get_entity_type_id_relationships_field (endpoint), post_entity_type_summarize (endpoint), get_entity_human_users_id_following (endpoint)
- **create** — 011_create_project (finding), 012_create_version (finding), 024_read_after_write (finding), 025_event_log (finding), 040_field_revive (finding), 045_webhooks (finding), 050_webhook_subscriptions (finding), 002_batch (recipe), 004_register_published_file (recipe), post_schema_type_fields (endpoint), post_entity_type (endpoint), post_entity_batch (endpoint), post_webhook_hooks (endpoint)
- **custom-entity** — 008_custom_entities (finding), entity_type (field type), put_preferences_update (endpoint), get_schema (endpoint), get_schema_type (endpoint)
- **custom-field** — 019_create_fields (finding), 040_field_revive (finding), post_schema_type_fields (endpoint), post_schema_type_fields_field (endpoint), put_schema_type_fields_field (endpoint), delete_schema_type_fields_field (endpoint)
- **cut** — 007_build_and_reconcile_a_cut (recipe), Cut (entity type), CutItem (entity type)
- **date** — 047_site_facts_and_the_working_week (finding), date (field type), date_time (field type), get_schedule_work_day_rules (endpoint), put_schedule_work_day_rules (endpoint)
- **delivery** — 045_webhooks (finding), 008_delivery_progress (recipe), Delivery (entity type), get_webhook_deliveries_record_uuid (endpoint), put_webhook_deliveries_record_uuid (endpoint), post_webhook_deliveries_record_uuid_redeliver (endpoint), get_webhook_hooks_hook_id_deliveries (endpoint)
- **dependency** — PublishedFile (entity type), Task (entity type)
- **destructive** — 009_multi_entity_safely (recipe), image (field type), multi_entity (field type), Note (entity type), Reply (entity type), post_schema_type_fields (endpoint), delete_schema_type_fields_field (endpoint), delete_entity_type_id (endpoint), delete_webhook_hooks_record_uuid (endpoint)
- **discovery** — 002_schema (finding), 008_custom_entities (finding), 040_field_revive (finding), 042_spec_coverage (finding), 047_site_facts_and_the_working_week (finding), 048_one_record_beyond_crud (finding), 051_api_version (finding), get_root (endpoint), get_license_info (endpoint), get_preferences (endpoint), get_schedule_work_day_rules (endpoint), get_spec_format (endpoint), get_subscription_seat_user_subscriptions (endpoint), post_subscription_seat_user_subscriptions (endpoint), get_schema (endpoint), get_schema_type (endpoint), get_schema_type_fields (endpoint), post_schema_type_fields_field (endpoint)
- **dotted-field** — 003_query (finding), 016_dotted_multi_entity (finding), 017_filter_operators (finding), 026_result_order (finding), 003_query_fields_and_pages (recipe), 010_status_picker (recipe), entity (field type), multi_entity (field type), password (field type), CutItem (entity type), Sequence (entity type)
- **duration** — duration (field type), Task (entity type), TimeLog (entity type), get_preferences (endpoint)
- **entity-field** — 004_array_vs_hash (finding), 005_link_usage (finding), 010_status_icons (finding), 012_create_version (finding), 017_filter_operators (finding), 019_create_fields (finding), 024_read_after_write (finding), 048_one_record_beyond_crud (finding), 004_register_published_file (recipe), 007_build_and_reconcile_a_cut (recipe), 009_multi_entity_safely (recipe), 010_status_picker (recipe), entity (field type), entity_type (field type), multi_entity (field type), get_entity_type (endpoint), post_entity_type (endpoint), get_entity_type_id (endpoint), get_entity_type_id_relationships_field (endpoint)
- **enumeration** — 006_pagination (finding), 050_webhook_subscriptions (finding), PublishedFileType (entity type)
- **error-handling** — 004_array_vs_hash (finding), 017_filter_operators (finding), 028_loud_and_silent (finding), 030_complex_filters (finding), 039_upload_silent_failures (finding), 040_field_revive (finding), 045_webhooks (finding), 047_site_facts_and_the_working_week (finding), 050_webhook_subscriptions (finding), 002_batch (recipe), 008_delivery_progress (recipe), float (field type), jsonb (field type), serializable (field type), put_preferences_update (endpoint), put_schedule_work_day_rules (endpoint), post_subscription_seat_user_subscriptions (endpoint), put_entity_type_id_unfollow (endpoint), post_entity_human_users_id_follow (endpoint), get_webhook_deliveries_record_uuid (endpoint), get_webhook_hooks_record_uuid (endpoint), get_exports_page_id_format (endpoint)
- **etag** — 044_multipart_upload (finding), post_entity_type_id_field_upload (endpoint), get_entity_type_id_field_upload_multipart (endpoint)
- **event-log** — 025_event_log (finding), 049_script_events (finding)
- **fill-rate** — 007_fill_rates (finding), 020_summarize (finding), checkbox (field type), number (field type), percent (field type), summary (field type), get_schema_type_fields (endpoint), post_entity_type_summarize (endpoint)
- **filter** — 003_query (finding), 014_attach_file (finding), 016_dotted_multi_entity (finding), 017_filter_operators (finding), 018_project_listing (finding), 023_pages (finding), 025_event_log (finding), 026_result_order (finding), 028_loud_and_silent (finding), 030_complex_filters (finding), 046_search_without_a_path (finding), 003_query_fields_and_pages (recipe), 005_propagate_status (recipe), 007_build_and_reconcile_a_cut (recipe), 009_multi_entity_safely (recipe), CutItem (entity type), Delivery (entity type), Project (entity type), PublishedFileType (entity type), Reply (entity type), Step (entity type), get_entity_type (endpoint), post_entity_type_search (endpoint), post_entity_text_search (endpoint), get_webhook_hooks_hook_id_deliveries (endpoint)
- **follow** — 043_attention (finding), get_entity_type_id_activity_stream (endpoint), get_entity_type_id_followers (endpoint), put_entity_type_id_unfollow (endpoint), post_entity_human_users_id_follow (endpoint), get_entity_human_users_id_following (endpoint)
- **header** — 004_array_vs_hash (finding), 014_attach_file (finding), 030_complex_filters (finding), 043_attention (finding), 046_search_without_a_path (finding), post_entity_type_search (endpoint), post_entity_text_search (endpoint), post_hierarchy_expand (endpoint), post_hierarchy_search (endpoint), post_entity_human_users_id_follow (endpoint)
- **icon** — 010_status_icons (finding), 010_status_picker (recipe)
- **image** — 006_media_round_trip (recipe), image (field type), get_entity_type_id_field (endpoint), get_entity_type_id_field_upload (endpoint)
- **inspector** — 005_link_usage (finding), 007_fill_rates (finding), 009_status_lists (finding), 018_project_listing (finding), 020_summarize (finding), 021_media_resolution (finding), 023_pages (finding), calculated (field type), checkbox (field type), password (field type), pivot_column (field type), summary (field type)
- **jsonb** — jsonb (field type), Note (entity type)
- **link** — 005_link_usage (finding), Version (entity type)
- **list-field** — 009_status_lists (finding), 018_project_listing (finding), 020_summarize (finding), 008_delivery_progress (recipe), 010_status_picker (recipe), list (field type), status_list (field type), Asset (entity type), Cut (entity type), Delivery (entity type), get_schema_type_fields_field (endpoint), post_entity_type_summarize (endpoint)
- **media** — 013_upload_media (finding), 021_media_resolution (finding), 022_sequence_on_version (finding), 039_upload_silent_failures (finding), 006_media_round_trip (recipe), image (field type), timecode (field type), url (field type), Attachment (entity type), Version (entity type), get_entity_type_id_field (endpoint), get_entity_type_id_field_upload (endpoint), put_entity_type_id_field_upload (endpoint), post_transcode_attachment_metadata_id (endpoint), put_links_upload (endpoint)
- **multi-entity** — 014_attach_file (finding), 016_dotted_multi_entity (finding), 048_one_record_beyond_crud (finding), 007_build_and_reconcile_a_cut (recipe), 009_multi_entity_safely (recipe), multi_entity (field type), get_entity_type_id_relationships_field (endpoint)
- **multipart** — 044_multipart_upload (finding), post_entity_type_id_field_upload (endpoint), get_entity_type_id_field_upload_multipart (endpoint), post_entity_type_id_field_upload_multipart_abort (endpoint), post_entity_type_id_upload (endpoint), get_entity_type_id_upload_multipart (endpoint), post_entity_type_id_upload_multipart_abort (endpoint)
- **note** — 039_upload_silent_failures (finding), 043_attention (finding), 009_multi_entity_safely (recipe), Note (entity type), Reply (entity type), post_entity_type_id_upload (endpoint), post_entity_type_id_upload_multipart_abort (endpoint), get_entity_type_id_followers (endpoint), get_entity_notes_id_thread_contents (endpoint)
- **number** — duration (field type), number (field type), percent (field type), timecode (field type)
- **observe** — 049_script_events (finding)
- **operator** — 017_filter_operators (finding), 025_event_log (finding), 028_loud_and_silent (finding), 030_complex_filters (finding), 003_query_fields_and_pages (recipe), CutItem (entity type), post_entity_type_search (endpoint)
- **page** — 023_pages (finding), 030_complex_filters (finding), 048_one_record_beyond_crud (finding), 003_query_fields_and_pages (recipe), get_exports_page_id_format (endpoint), get_exports_page_id_layout_format (endpoint)
- **paging** — 003_query (finding), 005_link_usage (finding), 006_pagination (finding), 016_dotted_multi_entity (finding), 025_event_log (finding), 026_result_order (finding), 043_attention (finding), 051_api_version (finding), get_entity_type (endpoint), post_entity_type_search (endpoint), get_entity_type_id_activity_stream (endpoint), get_entity_type_id_followers (endpoint), get_entity_human_users_id_following (endpoint), get_webhook_hooks (endpoint), get_webhook_hooks_hook_id_deliveries (endpoint)
- **path** — 021_media_resolution (finding), 022_sequence_on_version (finding), 004_register_published_file (recipe), PublishedFile (entity type)
- **permission** — 027_auth_permissions (finding), 049_script_events (finding), 011_audit_webhook_subscriptions (recipe), put_preferences_update (endpoint)
- **pivot-column** — pivot_column (field type), Shot (entity type)
- **playlist** — 009_multi_entity_safely (recipe), Playlist (entity type)
- **project** — 011_create_project (finding), 018_project_listing (finding), 023_pages (finding), 046_search_without_a_path (finding), 010_status_picker (recipe), Project (entity type), put_schedule_work_day_rules (endpoint), put_entity_projects_id_update_last_accessed (endpoint), post_hierarchy_expand (endpoint), post_hierarchy_search (endpoint), get_entity_human_users_id_following (endpoint)
- **protocol** — 051_api_version (finding)
- **provenance** — 014_attach_file (finding), 019_create_fields (finding), 001_publish_version_with_media (recipe), get_entity_type_id_upload (endpoint)
- **published-file** — 021_media_resolution (finding), 004_register_published_file (recipe), Delivery (entity type), PublishedFile (entity type), PublishedFileType (entity type)
- **query** — 003_query (finding), 004_array_vs_hash (finding), 006_pagination (finding), 016_dotted_multi_entity (finding), 017_filter_operators (finding), 018_project_listing (finding), 020_summarize (finding), 021_media_resolution (finding), 023_pages (finding), 025_event_log (finding), 026_result_order (finding), 028_loud_and_silent (finding), 030_complex_filters (finding), 046_search_without_a_path (finding), 003_query_fields_and_pages (recipe), Reply (entity type), Step (entity type), get_entity_type (endpoint), get_entity_type_id (endpoint), post_entity_type_search (endpoint), post_entity_type_summarize (endpoint), post_entity_text_search (endpoint), post_hierarchy_expand (endpoint), post_hierarchy_search (endpoint)
- **read-only** — 011_audit_webhook_subscriptions (recipe), calculated (field type), password (field type), pivot_column (field type), serializable (field type), summary (field type), uuid (field type), get_license_info (endpoint), get_schedule_work_day_rules (endpoint), get_subscription_seat_user_subscriptions (endpoint)
- **reply** — 043_attention (finding), 008_delivery_progress (recipe), Delivery (entity type), Reply (entity type), get_entity_notes_id_thread_contents (endpoint)
- **schema** — 002_schema (finding), 007_fill_rates (finding), 008_custom_entities (finding), 009_status_lists (finding), 011_create_project (finding), 019_create_fields (finding), 020_summarize (finding), 023_pages (finding), 040_field_revive (finding), 042_spec_coverage (finding), 003_query_fields_and_pages (recipe), 005_propagate_status (recipe), 010_status_picker (recipe), get_preferences (endpoint), get_spec_format (endpoint), get_schema (endpoint), get_schema_type (endpoint), get_schema_type_fields (endpoint), post_schema_type_fields (endpoint), get_schema_type_fields_field (endpoint), post_schema_type_fields_field (endpoint), put_schema_type_fields_field (endpoint), delete_schema_type_fields_field (endpoint)
- **sequence** — 022_sequence_on_version (finding), Sequence (entity type)
- **serializable** — 025_event_log (finding), jsonb (field type), serializable (field type)
- **shot** — 002_batch (recipe), 005_propagate_status (recipe), 007_build_and_reconcile_a_cut (recipe), Sequence (entity type), Shot (entity type)
- **silent** — 016_dotted_multi_entity (finding), 017_filter_operators (finding), 019_create_fields (finding), 023_pages (finding), 024_read_after_write (finding), 025_event_log (finding), 026_result_order (finding), 028_loud_and_silent (finding), 030_complex_filters (finding), 039_upload_silent_failures (finding), 040_field_revive (finding), 043_attention (finding), 045_webhooks (finding), 047_site_facts_and_the_working_week (finding), 048_one_record_beyond_crud (finding), 049_script_events (finding), 050_webhook_subscriptions (finding), 002_batch (recipe), 005_propagate_status (recipe), 009_multi_entity_safely (recipe), 011_audit_webhook_subscriptions (recipe), float (field type), multi_entity (field type), password (field type), serializable (field type), url (field type), Playlist (entity type), PublishedFileType (entity type), Reply (entity type), Sequence (entity type), Step (entity type), get_schedule_work_day_rules (endpoint), post_schema_type_fields (endpoint), put_schema_type_fields_field (endpoint), get_entity_type (endpoint), post_entity_type (endpoint), put_entity_type_id (endpoint), post_entity_batch (endpoint), put_entity_projects_id_update_last_accessed (endpoint), post_entity_type_search (endpoint), post_entity_text_search (endpoint), post_transcode_attachment_metadata_id (endpoint), post_links_complete_upload (endpoint), put_links_upload (endpoint), put_entity_type_id_unfollow (endpoint), post_entity_human_users_id_follow (endpoint), put_webhook_deliveries_record_uuid (endpoint), post_webhook_deliveries_record_uuid_redeliver (endpoint), get_webhook_hooks (endpoint), post_webhook_hooks (endpoint), post_webhook_hooks_record_uuid_test_connection (endpoint)
- **sort** — 026_result_order (finding), 028_loud_and_silent (finding)
- **status** — 009_status_lists (finding), 010_status_icons (finding), 025_event_log (finding), 005_propagate_status (recipe), 008_delivery_progress (recipe), 010_status_picker (recipe), status_list (field type), get_schema_type_fields_field (endpoint), put_webhook_hooks_record_uuid (endpoint)
- **step** — pivot_column (field type), Step (entity type)
- **storage** — 021_media_resolution (finding), 044_multipart_upload (finding), 004_register_published_file (recipe), PublishedFile (entity type), put_entity_type_id_field_upload (endpoint), post_entity_type_id_field_upload_multipart_abort (endpoint), put_entity_type_id_upload (endpoint)
- **summary** — 003_query_fields_and_pages (recipe), summary (field type), timecode (field type), post_entity_type_summarize (endpoint)
- **task** — 005_propagate_status (recipe), Step (entity type), Task (entity type), TimeLog (entity type)
- **timecode** — 007_build_and_reconcile_a_cut (recipe), timecode (field type), Cut (entity type), CutItem (entity type)
- **token** — 001_auth (finding), 027_auth_permissions (finding), 045_webhooks (finding), post_auth_access_token (endpoint), post_webhook_hooks (endpoint)
- **transcode** — post_transcode_attachment_metadata_id (endpoint)
- **trap** — 004_array_vs_hash (finding), 016_dotted_multi_entity (finding), 018_project_listing (finding), 019_create_fields (finding), 023_pages (finding), 024_read_after_write (finding), 025_event_log (finding), 026_result_order (finding), 028_loud_and_silent (finding), 030_complex_filters (finding), 039_upload_silent_failures (finding), 040_field_revive (finding), 043_attention (finding), 045_webhooks (finding), 046_search_without_a_path (finding), 049_script_events (finding), 050_webhook_subscriptions (finding), post_entity_type_id (endpoint), get_entity_type_id_field (endpoint), post_hierarchy_expand (endpoint), post_hierarchy_search (endpoint), get_entity_type_id_activity_stream (endpoint), post_entity_human_users_id_follow (endpoint), put_webhook_deliveries_record_uuid (endpoint), post_webhook_hooks (endpoint), post_webhook_hooks_record_uuid_test_connection (endpoint)
- **upload** — 013_upload_media (finding), 014_attach_file (finding), 022_sequence_on_version (finding), 024_read_after_write (finding), 039_upload_silent_failures (finding), 044_multipart_upload (finding), 001_publish_version_with_media (recipe), 006_media_round_trip (recipe), 008_delivery_progress (recipe), image (field type), url (field type), Attachment (entity type), get_entity_type_id_field_upload (endpoint), get_entity_type_id_upload (endpoint), post_links_complete_upload (endpoint), put_links_upload (endpoint)
- **url** — 006_media_round_trip (recipe), url (field type), Attachment (entity type)
- **user** — 027_auth_permissions (finding), 043_attention (finding), 047_site_facts_and_the_working_week (finding), get_license_info (endpoint), put_schedule_work_day_rules (endpoint), get_subscription_seat_user_subscriptions (endpoint), post_subscription_seat_user_subscriptions (endpoint), put_entity_projects_id_update_last_accessed (endpoint), get_entity_type_id_activity_stream (endpoint), get_entity_type_id_followers (endpoint), put_entity_type_id_unfollow (endpoint), post_entity_human_users_id_follow (endpoint), get_entity_human_users_id_following (endpoint), get_entity_notes_id_thread_contents (endpoint)
- **version** — 003_query (finding), 005_link_usage (finding), 007_fill_rates (finding), 012_create_version (finding), 013_upload_media (finding), 014_attach_file (finding), 021_media_resolution (finding), 022_sequence_on_version (finding), 001_publish_version_with_media (recipe), 002_batch (recipe), 004_register_published_file (recipe), 005_propagate_status (recipe), 006_media_round_trip (recipe), 007_build_and_reconcile_a_cut (recipe), 008_delivery_progress (recipe), 009_multi_entity_safely (recipe), url (field type), Delivery (entity type), Playlist (entity type), Version (entity type)
- **webhook** — 045_webhooks (finding), 050_webhook_subscriptions (finding), 011_audit_webhook_subscriptions (recipe), get_webhook_deliveries_record_uuid (endpoint), put_webhook_deliveries_record_uuid (endpoint), post_webhook_deliveries_record_uuid_redeliver (endpoint), get_webhook_hooks (endpoint), post_webhook_hooks (endpoint), get_webhook_hooks_hook_id_deliveries (endpoint), get_webhook_hooks_record_uuid (endpoint), put_webhook_hooks_record_uuid (endpoint), delete_webhook_hooks_record_uuid (endpoint), post_webhook_hooks_record_uuid_test_connection (endpoint)
- **write** — 011_create_project (finding), 012_create_version (finding), 013_upload_media (finding), 014_attach_file (finding), 019_create_fields (finding), 022_sequence_on_version (finding), 024_read_after_write (finding), 025_event_log (finding), 028_loud_and_silent (finding), 045_webhooks (finding), 049_script_events (finding), 001_publish_version_with_media (recipe), 002_batch (recipe), 004_register_published_file (recipe), 005_propagate_status (recipe), 006_media_round_trip (recipe), 007_build_and_reconcile_a_cut (recipe), 008_delivery_progress (recipe), 009_multi_entity_safely (recipe), Sequence (entity type), put_preferences_update (endpoint), put_schedule_work_day_rules (endpoint), post_subscription_seat_user_subscriptions (endpoint), post_entity_type (endpoint), post_entity_type_id (endpoint), put_entity_type_id (endpoint), delete_entity_type_id (endpoint), post_entity_batch (endpoint), put_webhook_hooks_record_uuid (endpoint)
