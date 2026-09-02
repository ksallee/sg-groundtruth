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
- **004_array_vs_hash** — REST has NO array/hash negotiation - api3_array+json and api3_hash+json both 406; entity and multi-entity fields always come back under relationships as {data, links}. TRAP: a bogus name in ?fields is silently dropped (HTTP 200, field simply absent), while the same name in filter[] errors 400 - so a typo reads as 'no data' instead of 'wrong field'.  
  `query header entity-field error-handling`
- **005_link_usage** — On BBB, Versions link via `entity` 100% (Shot 99%, Asset 1%) and via `sg_task` only 1% - hardcoding Task-linking would be wrong almost always here, which is the whole case for the site profile. Also: page[size]=500 returned 100 rows, so page size is capped at 100.  
  `version link inspector entity-field paging`
- **006_pagination** — CONFIRMED and worse than reported: links.next is emitted on EVERY page forever, including pages that return zero rows - following it until absent is an infinite loop. Paging itself is correct (size=30 page=3 returns 30 rows). No total count exists anywhere: meta is null and options[return_paging_info] is ignored. Stop on an empty data array; never on a missing next.  
  `paging query enumeration`
- **007_fill_rates** — Of 61 Version fields in the schema, 30 carry data on BBB and 31 are never populated - rank by fill rate, never expose the schema wholesale. CAVEAT: booleans read as 100% filled because False is not null, so the inspector must exclude checkbox fields from fill ranking or use the schema data_type to weight them.  
  `version inspector schema fill-rate`
- **008_custom_entities** — /schema returns ONLY enabled custom entities (11 slots, all visible) - a disabled slot is simply absent, so presence in /schema is the enablement test. Slot numbers are non-contiguous and site-specific (01-07, 19, 29, 66 here); resolve display names from name.value and never hardcode a number. Connection entities appear as their own type.  
  `schema custom-entity discovery`
- **009_status_lists** — A project's usable statuses are valid_values MINUS hidden_values, read with project_id. valid_values is identical at every scope and is NOT the answer on its own; hidden_values is what varies (site-wide hides 0, one project hides 2, another hides 6). Status lists are also per entity type - Version and Task share no vocabulary. Always read display_values: raw codes like 'pndvs' mean nothing to a user.  
  `schema status list-field inspector`
- **010_status_icons** — Status is a real queryable entity (32 rows, 11 fields) holding bg_color, name, code and a `system` flag separating built-in from custom statuses. bg_color is comma-separated RGB ('25,118,27'), NOT hex. GAP: `icon` is null on all 32 statuses on this site, so the standard/custom-icon branches are unverified - set a custom icon on one status to close it.  
  `status icon cache schema colour`

## Recipes

- none yet

## By tag

- **auth** — 001_auth (finding)
- **cache** — 010_status_icons (finding)
- **client** — 001_auth (finding)
- **colour** — 010_status_icons (finding)
- **cost** — 002_schema (finding)
- **custom-entity** — 008_custom_entities (finding)
- **discovery** — 002_schema (finding), 008_custom_entities (finding)
- **dotted-field** — 003_query (finding)
- **entity-field** — 004_array_vs_hash (finding), 005_link_usage (finding)
- **enumeration** — 006_pagination (finding)
- **error-handling** — 004_array_vs_hash (finding)
- **fill-rate** — 007_fill_rates (finding)
- **filter** — 003_query (finding)
- **header** — 004_array_vs_hash (finding)
- **icon** — 010_status_icons (finding)
- **inspector** — 005_link_usage (finding), 007_fill_rates (finding), 009_status_lists (finding)
- **link** — 005_link_usage (finding)
- **list-field** — 009_status_lists (finding)
- **paging** — 003_query (finding), 005_link_usage (finding), 006_pagination (finding)
- **query** — 003_query (finding), 004_array_vs_hash (finding), 006_pagination (finding)
- **schema** — 002_schema (finding), 007_fill_rates (finding), 008_custom_entities (finding), 009_status_lists (finding), 010_status_icons (finding)
- **status** — 009_status_lists (finding), 010_status_icons (finding)
- **token** — 001_auth (finding)
- **version** — 003_query (finding), 005_link_usage (finding), 007_fill_rates (finding)
