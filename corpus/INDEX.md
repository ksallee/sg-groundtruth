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
- **010_status_icons** — Status.icon is an ENTITY link, so it arrives under relationships, not attributes - reading attributes alone makes every icon look null. Icons resolve three ways by display_type: 'image_map' (94 standard, url empty, addressed by image_map_key like 'icon_apr' - a sprite, and its location is NOT guessable at /images/*, still unresolved); 'image' (custom upload - url is a self-contained data:image/png;base64 URI, with newlines that must be stripped, and image_data holds the same bytes); 'html' (custom text badge - html holds the label, no image at all). bg_color is comma-separated RGB, not hex, and is enough to render a badge without any icon.  
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
- **017_filter_operators** — is/is_not/contains/not_contains/starts_with/ends_with/in/not_in all work on text fields AND through dotted paths (entity.Shot.code contains <substr> returns partial counts), and every negative control returns 0 - so these operators are real, not ignored. Crucially an UNKNOWN operator returns 400, never a silent pass, so a typo cannot masquerade as 'no filter' the way a bogus ?fields name does (probe 004). `in` takes a plain list for scalars, but on an entity field it needs FULL {type, id} hashes: [{id: N}] and bare ints both 400 with 'invalid/missing entity hash'. `contains` on a dotted path is what makes server-side type-ahead over names possible.  
  `query filter operator dotted-field entity-field error-handling`
- **018_project_listing** — DO NOT filter a project picker on sg_status. Its valid values are Bidding/Active/Lost/Hold with NO display_values, and it is null on most real projects - on this site 10 of 22, including freshly created ones, so 'sg_status is Active' hides working projects. The reliable discriminators are the checkboxes: is_template is True for exactly the stock templates, is_demo for the shipped demo show, archived for retired ones. Filter is_template/is_demo/archived is False and leave sg_status alone; a new project has no status until someone sets one.  
  `project query filter inspector list-field trap`
- **019_create_fields** — Almost every useful type IS creatable - the 400s are missing properties, not refusals. text/float/number/date/date_time/list/url/duration/percent/footage need nothing extra; checkbox needs default_value; entity and multi_entity need valid_types, and multi_entity takes EXACTLY ONE element (two types -> 400). Only color, image and calculated are truly rejected as invalid data_types. A multi_entity of Version round-trips lineage and reads back under relationships, which is how input-Version links should be stored rather than as JSON. Pass a DISPLAY name: the sg_ prefix is added for you, so 'sg_foo' becomes 'sg_sg_foo'. The programmatic name is NOT in the response body - take the last segment of links.self. TWO TRAPS. (1) A duplicate display name does NOT error, it silently makes <name>_1, so an idempotent ensure() MUST read /schema first and never POST-and-hope. (2) DELETE returns 204 and the field vanishes from /schema, but the NAME IS NOT FREED: recreating it 400s and the trashed field cannot be enumerated, so the collision is invisible. Also: seeds must be TEXT - a number field takes 2**31-1 but 400s at 2**63, and ComfyUI seeds go to 2**64-1.  
  `schema write custom-field provenance entity-field trap`
- **020_summarize** — _summarize takes the SAME vendor Content-Type as _search (application/json is 415, probe 004) and answers the inspector's second question directly: `grouping` by a field returns one group per distinct value with a count, so ONE call yields both cardinality and the empty count - empty values come back as a '' group. That is the metric fill rate cannot give: Version.code returns one group per row (an identifier, useless to expose) and flagged returns exactly one group (no information at all), while both look identical to a fill-rate scan. Grouping is NOT capped - 300 distinct Shot codes return 300 groups. Checkbox fields cannot be filtered `is_not None` at all (400), which is the same trap as probe 007 from the other side. BUT it is not free: ~300ms typical and up to 1.5s when the grouped field is an entity, so scanning all 61 Version fields costs far more than a single paged fetch of 100 rows. Use one fetch for the broad fill-rate pass, then _summarize per candidate field to rank the shortlist by cardinality.  
  `query inspector fill-rate schema cost list-field`
- **021_media_resolution** — All three tiers exist; only the LAST is reliable, and the first is not testable here. THE REUSABLE TRUTH: `path` on a PublishedFile arrives with the LocalStorage join ALREADY DONE - local_path_mac / local_path_windows / local_path_linux are filled by the server alongside relative_path and the local_storage hash, so a client NEVER reads LocalStorage or reassembles a root. But which types carry a path is not uniform: Maya Scene (5/5) and Alembic Cache (2/2) carry one and the files exist on the mount, Movie (4/4) carries one and NONE of the files exist, and Image, Rendered Image, Texture and USD carry NO path at all - so precisely the types a Fetch node wants are the ones with nothing to load. Traversal is worse: published_files is filled on 2 of 53 Versions and `version` is null on 180 of 182 PFs, so walking Version -> PublishedFile finds nothing on this site. Tier 2 sg_path_to_movie is filled 28/53 and the sampled paths DO exist, but they are ad-hoc user paths under Zenith and Thicket rather than a shared root - readable, not portable - and sg_path_to_frames is 0/53, so the %04d sequence form is untested. Tier 3 always resolves and needs no second call: `image` IS a presigned S3 URL as a plain string and sg_uploaded_movie is a dict carrying the same under `url`. Note sg_uploaded_movie cannot be filtered or summarized `is_not None` at all - 400, "'url' escarp type cannot be" - the same shape of trap as a checkbox (probe 020). Build the Fetch node on tier 3, keep tier 2 as an opt-in, and treat the PublishedFile tier as UNPROVEN until a site with a real cinder history exists to probe.  
  `version media published-file path storage inspector query`

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
- **cost** — 002_schema (finding), 020_summarize (finding)
- **create** — 011_create_project (finding), 012_create_version (finding)
- **custom-entity** — 008_custom_entities (finding)
- **custom-field** — 019_create_fields (finding)
- **discovery** — 002_schema (finding), 008_custom_entities (finding)
- **dotted-field** — 003_query (finding), 016_dotted_multi_entity (finding), 017_filter_operators (finding)
- **entity-field** — 004_array_vs_hash (finding), 005_link_usage (finding), 010_status_icons (finding), 012_create_version (finding), 017_filter_operators (finding), 019_create_fields (finding)
- **enumeration** — 006_pagination (finding)
- **error-handling** — 004_array_vs_hash (finding), 017_filter_operators (finding)
- **fill-rate** — 007_fill_rates (finding), 020_summarize (finding)
- **filter** — 003_query (finding), 014_attach_file (finding), 016_dotted_multi_entity (finding), 017_filter_operators (finding), 018_project_listing (finding)
- **header** — 004_array_vs_hash (finding)
- **icon** — 010_status_icons (finding)
- **inspector** — 005_link_usage (finding), 007_fill_rates (finding), 009_status_lists (finding), 018_project_listing (finding), 020_summarize (finding), 021_media_resolution (finding)
- **link** — 005_link_usage (finding)
- **list-field** — 009_status_lists (finding), 018_project_listing (finding), 020_summarize (finding)
- **media** — 013_upload_media (finding), 021_media_resolution (finding)
- **multi-entity** — 014_attach_file (finding), 016_dotted_multi_entity (finding)
- **operator** — 017_filter_operators (finding)
- **paging** — 003_query (finding), 005_link_usage (finding), 006_pagination (finding), 016_dotted_multi_entity (finding)
- **path** — 021_media_resolution (finding)
- **project** — 011_create_project (finding), 018_project_listing (finding)
- **provenance** — 014_attach_file (finding), 019_create_fields (finding), 001_publish_version_with_media (recipe)
- **published-file** — 021_media_resolution (finding)
- **query** — 003_query (finding), 004_array_vs_hash (finding), 006_pagination (finding), 016_dotted_multi_entity (finding), 017_filter_operators (finding), 018_project_listing (finding), 020_summarize (finding), 021_media_resolution (finding)
- **recipe** — 001_publish_version_with_media (recipe)
- **sandbox** — 011_create_project (finding)
- **schema** — 002_schema (finding), 007_fill_rates (finding), 008_custom_entities (finding), 009_status_lists (finding), 019_create_fields (finding), 020_summarize (finding)
- **status** — 009_status_lists (finding), 010_status_icons (finding)
- **storage** — 021_media_resolution (finding)
- **token** — 001_auth (finding)
- **trap** — 016_dotted_multi_entity (finding), 018_project_listing (finding), 019_create_fields (finding)
- **upload** — 013_upload_media (finding), 014_attach_file (finding), 001_publish_version_with_media (recipe)
- **version** — 003_query (finding), 005_link_usage (finding), 007_fill_rates (finding), 012_create_version (finding), 013_upload_media (finding), 014_attach_file (finding), 021_media_resolution (finding), 001_publish_version_with_media (recipe)
- **write** — 011_create_project (finding), 012_create_version (finding), 013_upload_media (finding), 014_attach_file (finding), 019_create_fields (finding), 001_publish_version_with_media (recipe)
