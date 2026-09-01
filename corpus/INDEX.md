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
- **009_status_lists** — Status lists are per entity type, not global - Version and Task share no vocabulary. valid_values, display_values, hidden_values and default_value are ALL readable over REST, so hidden values are visible even if not settable. On this site project_id changed nothing, which does not disprove project scoping - it means no per-project override exists here. Always read display_values: raw codes like 'pndvs' are meaningless to a user.  
  `schema status list-field inspector`

## Recipes

- none yet

## By tag

- **auth** — 001_auth (finding)
- **client** — 001_auth (finding)
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
- **inspector** — 005_link_usage (finding), 007_fill_rates (finding), 009_status_lists (finding)
- **link** — 005_link_usage (finding)
- **list-field** — 009_status_lists (finding)
- **paging** — 003_query (finding), 005_link_usage (finding), 006_pagination (finding)
- **query** — 003_query (finding), 004_array_vs_hash (finding), 006_pagination (finding)
- **schema** — 002_schema (finding), 007_fill_rates (finding), 008_custom_entities (finding), 009_status_lists (finding)
- **status** — 009_status_lists (finding)
- **token** — 001_auth (finding)
- **version** — 003_query (finding), 005_link_usage (finding), 007_fill_rates (finding)
