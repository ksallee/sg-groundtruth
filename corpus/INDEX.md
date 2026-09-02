# Corpus index

Read this first. Open an entry only when its one-liner does not already answer the question.

**Findings** — how the API behaves. **Recipes** — a verified call and its real response.

## Findings

- **001_auth** — client_credentials works; token lives 600s; refresh_token returned but the client re-auths instead.  
  `auth client token`
- **002_schema** — /schema lists 113 entity types (13KB); /schema/<Type>/fields is the expensive call (Version = 61 fields, 42KB, ~350ms) — never fetch it for all types; /schema/<Type> returns only name+visible; /schema/entity_types is 404; project_id is accepted on both and does change the response.  
  `schema cost discovery`
- **003_query** — see below  
  `query filter dotted-field paging version`
- **004_array_vs_hash** — The array/hash choice is a REQUEST Content-Type on POST _search, NOT an Accept header on GET - sending those vendor types as Accept on a GET returns 406 (see below), but POST /entity/<type>/_search REJECTS application/json with 415 and demands application/vnd+shotgun.api3_array+json or ...api3_hash+json (probe 014). Array form takes filters as [[field, op, value]]. Responses are unaffected: entity and multi-entity fields always arrive under relationships as {data, links}. TRAP: a bogus name in ?fields is silently dropped (HTTP 200, field simply absent), while the same name in filter[] errors 400 - so a typo reads as 'no data' rather than 'wrong field'.  
  `query header entity-field error-handling`
- **005_link_usage** — On BBB, Versions link via `entity` 100% (Shot 99%, Asset 1%) and via `sg_task` only 1% - hardcoding Task-linking would be wrong almost always here, which is the whole case for the site profile. (An earlier version of this finding claimed page[size] is capped at 100. It is not - probe 016 shows 150 returns 150. BBB simply has exactly 100 Versions.)  
  `version link inspector entity-field paging`
- **006_pagination** — CONFIRMED and worse than reported: links.next is emitted on EVERY page forever, including pages that return zero rows - following it until absent is an infinite loop. Paging itself is correct (size=30 page=3 returns 30 rows). No total count exists anywhere: meta is null and options[return_paging_info] is ignored. Stop on an empty data array; never on a missing next.  
  `paging query enumeration`
- **007_fill_rates** — Of 61 Version fields in the schema, 30 carry data on BBB and 31 are never populated - rank by fill rate, never expose the schema wholesale. CAVEAT: booleans read as 100% filled because False is not null, so the inspector must exclude checkbox fields from fill ranking or use the schema data_type to weight them.  
  `version inspector schema fill-rate`
- **008_custom_entities** — /schema returns ONLY enabled custom entities (11 slots, all visible) - a disabled slot is simply absent, so presence in /schema is the enablement test. Slot numbers are non-contiguous and site-specific (01-07, 19, 29, 66 here); resolve display names from name.value and never hardcode a number. Connection entities appear as their own type.  
  `schema custom-entity discovery`
- **009_status_lists** — A project's usable statuses are valid_values MINUS hidden_values, read with project_id. valid_values is identical at every scope and is NOT the answer on its own; hidden_values is what varies (site-wide hides 0, one project hides 2, another hides 6). Status lists are also per entity type - Version and Task share no vocabulary. Always read display_values: raw codes like 'pndvs' mean nothing to a user.  
  `schema status list-field inspector`
- **010_status_icons** — Status.icon is an ENTITY link, so it arrives under relationships, not attributes - reading attributes alone makes every icon look null. Icons basaltolve three ways by display_type: 'image_map' (94 standard, url empty, addbasaltsed by image_map_key like 'icon_apr' - a sprite, and its location is NOT guessable at /images/*, still unbasaltolved); 'image' (custom upload - url is a self-contained data:image/png;base64 URI, with newlines that must be stripped, and image_data holds the same bytes); 'html' (custom text badge - html holds the label, no image at all). bg_color is comma-separated RGB, not hex, and is enough to render a badge without any icon.  
  `status icon cache colour entity-field`
- **011_create_project** — see below  
  `write project create sandbox`
- **012_create_version** — see below  
  `write version create entity-field`
- **013_upload_media** — Three steps, no shortcuts. 1) GET /entity/versions/{id}/{field}/_upload?filename=X returns links.upload (presigned S3) and links.complete_upload. 2) PUT the raw bytes to links.upload. 3) POST links.complete_upload with {'upload_info': <the data block from step 1 verbatim>, 'upload_data': {}} -> 201. Omitting upload_data 400s with 'upload_data is missing' even though it is empty. Field choice sets upload_type: /image/ is a Thumbnail, any other field is an Attachment. Transcoding is ASYNC - reading the field straight back returns a placeholder under /images/status/transient/, so detect that path prefix rather than treating it as the real media.  
  `write upload media attachment version async`
- **014_attach_file** — Same three-step upload as media but with NO field in the path: GET /entity/versions/{id}/_upload gives upload_type=Attachment, and the file lands as an Attachment entity linked through attachment_links. Retrieving it needs POST /entity/attachments/_search - a multi-entity field cannot be filtered by flat filter[] params (400 'invalid/missing entity hash'), it needs an entity hash {type, id}, and only the _search body can carry one.  
  `write upload attachment provenance version multi-entity filter`
- **016_dotted_multi_entity** — READS and FILTERS differ. Reading a dotted path through a multi_entity field silently omits the key - HTTP 200, no error (single-entity 'entity' fields read fine). But FILTERING on the same path WORKS, including two hops, verified by negative controls returning 0 while positives return partial counts. So: filter through multi-entity freely; to READ those values you must query the child entity separately. Also corrects probe 005: page[size] is NOT capped at 100 - 150 returns 150 and 500 returns everything.  
  `query dotted-field multi-entity filter paging trap`

## Recipes

- **001_publish_version_with_media** — Publish a generated image to Flow PT as a Version, with provenance and the workflow attached  
  `write version upload attachment provenance recipe`

## By tag

- **async** — 013_upload_media (finding)
- **attachment** — 013_upload_media (finding), 014_attach_file (finding), 001_publish_version_with_media (recipe)
- **auth** — 001_auth (finding)
- **cache** — 010_status_icons (finding)
- **client** — 001_auth (finding)
- **colour** — 010_status_icons (finding)
- **cost** — 002_schema (finding)
- **create** — 011_create_project (finding), 012_create_version (finding)
- **custom-entity** — 008_custom_entities (finding)
- **discovery** — 002_schema (finding), 008_custom_entities (finding)
- **dotted-field** — 003_query (finding), 016_dotted_multi_entity (finding)
- **entity-field** — 004_array_vs_hash (finding), 005_link_usage (finding), 010_status_icons (finding), 012_create_version (finding)
- **enumeration** — 006_pagination (finding)
- **error-handling** — 004_array_vs_hash (finding)
- **fill-rate** — 007_fill_rates (finding)
- **filter** — 003_query (finding), 014_attach_file (finding), 016_dotted_multi_entity (finding)
- **header** — 004_array_vs_hash (finding)
- **icon** — 010_status_icons (finding)
- **inspector** — 005_link_usage (finding), 007_fill_rates (finding), 009_status_lists (finding)
- **link** — 005_link_usage (finding)
- **list-field** — 009_status_lists (finding)
- **media** — 013_upload_media (finding)
- **multi-entity** — 014_attach_file (finding), 016_dotted_multi_entity (finding)
- **paging** — 003_query (finding), 005_link_usage (finding), 006_pagination (finding), 016_dotted_multi_entity (finding)
- **project** — 011_create_project (finding)
- **provenance** — 014_attach_file (finding), 001_publish_version_with_media (recipe)
- **query** — 003_query (finding), 004_array_vs_hash (finding), 006_pagination (finding), 016_dotted_multi_entity (finding)
- **recipe** — 001_publish_version_with_media (recipe)
- **sandbox** — 011_create_project (finding)
- **schema** — 002_schema (finding), 007_fill_rates (finding), 008_custom_entities (finding), 009_status_lists (finding)
- **status** — 009_status_lists (finding), 010_status_icons (finding)
- **token** — 001_auth (finding)
- **trap** — 016_dotted_multi_entity (finding)
- **upload** — 013_upload_media (finding), 014_attach_file (finding), 001_publish_version_with_media (recipe)
- **version** — 003_query (finding), 005_link_usage (finding), 007_fill_rates (finding), 012_create_version (finding), 013_upload_media (finding), 014_attach_file (finding), 001_publish_version_with_media (recipe)
- **write** — 011_create_project (finding), 012_create_version (finding), 013_upload_media (finding), 014_attach_file (finding), 001_publish_version_with_media (recipe)
