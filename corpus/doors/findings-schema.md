# Findings — schema: what the site has, and adding to it

How the API behaves in this part of a session. Each rule is the entry's own **Teaches**, copied whole.

## 002_schema

Fetch /schema once for the type list, then /schema/<Type>/fields only for types you actually need: it is the expensive call (48KB, ~330ms each) and must never be looped over all types.

- A connection type's REST slug collapses the doubled underscore. `Asset_linked_projects_Connection` is
  addressable as itself or as `asset_linked_projects_connections`, while the naive snake_case rule gives
  `asset_linked_projects__connections`, which 404s. Ten types on the probed site are affected
  (`recipes/003`).

Sizes below are from the probed site.

| call | size | what it gives |
|---|---|---|
| `/schema` | 13KB | the type list, nothing per type |
| `/schema/<Type>` | 138b | `name` and `visible` |
| `/schema/<Type>/fields` | 48KB | every field on the type |
| `/schema/<Type>/fields/<field>` | 1.2KB | one field, when you know its name |
| `/schema/entity_types` | 404 `"Not Found"` | no lighter enumeration exists |
| `/entity_types`, `/entity`, `/api/v1/entity` | 404, `detail: null` | not routes |

- `/schema/<x>` addresses one entity type, so an enumeration path under it is read as a type name and 404s
  saying so: `entity_types`, `entity_type`, `entities`, `types` and `_types` each return
  `Entity type '<x>' does not exist.` Off that prefix, `/entity_types`, `/entity` and `/api/v1/entity` 404
  with `detail: null`. `/schema` is the type list; there is nothing lighter.

- There is no cheap middle tier: anything about a type costs the `/fields` call, so drill straight to one field with `/fields/<field>` when you know the name.

- `project_id` is accepted on both `/schema` and `/fields` and does change the body (13368 → 13395b, 48111 → 48139b), so a project-scoped schema is not the site schema. Cache the two under separate keys (see the `.schema-cache/<site>/<site|pNNN>/` split).

- Site settings are not under `/schema`. `GET /preferences` returns 200 with 17 keys, `hours_per_day` and `duration_units` among them (`field_types/duration`).

- Nothing in a field's block names where the field came from. `visible.editable` is the closest
  reading and the `sg_` prefix is not one at all (probe 056).

- Counts are site state, not API constants. On the probed site, `/schema` returned 114 types and `Version` 71 fields, against 113 and 61 on an earlier run. Measure and cache; never hardcode a count or a field list.

`corpus/findings/002_schema.md`

## 008_custom_entities

Presence in /schema is the enablement test for a custom entity: a slot absent from the listing 404s. Slot numbers are non-contiguous and site-specific, so read name.value and never hardcode one.

- Presence in /schema is the enablement test, in both directions. A slot in the listing is enabled, and
  a slot absent from it is unaddressable: `GET /schema/CustomEntity08` and
  `GET /schema/CustomEntity08/fields` both return 404 `Entity type 'CustomEntity08' does not exist.`
  Enumerate `/schema` rather than probing slot numbers.

- On the probed site every slot in `/schema` read `visible: true`, so `visible: false` was never observed.
  Treat absence, not `visible`, as the disabled signal. A site with a slot enabled and then disabled would
  settle whether `visible` can read False.

- Never hardcode a slot number: they are non-contiguous and site-specific. On the probed site the enabled slots are 01-07, 19, 29 and 66. Look a slot up by its `name.value` display name.

- A connection entity is its own type, `CustomEntity29_sg_scene_Connection`, and its display name is machine-derived from the type name rather than studio-chosen.

- Display names are free text and may include a trailing space (`CustomEntity66` above), so match them trimmed.

`corpus/findings/008_custom_entities.md`

## 009_status_lists

A project's usable statuses are valid_values minus hidden_values, read with project_id: valid_values is identical at every scope, hidden_values is the only thing that varies.

- Usable statuses are `valid_values` minus `hidden_values`, read with `project_id`. REST does not enforce
  `hidden_values` on write, so do the subtraction yourself. See `field_types/status_list.md`.

- `valid_values` is the site's whole vocabulary and is byte-identical at every scope, so reading it alone
  tells you nothing about a project. On the probed site, 21 scopes returned 1 distinct value.

- `hidden_values` is the only thing `project_id` changes. Omit `project_id` and you get the site-wide
  answer, which hides nothing and will offer statuses the project's UI refuses.

- Status lists are per entity type. On the probed site, Version and Task overlap only on
  `ip`/`fin`/`apr`/`na`/`rev`, and Task's `wtg`/`hld`/`omt`/`ready` do not exist on Version. Never reuse
  one type's codes for another.

- On the probed site, Version's 16 `valid_values` leave 10 usable in one project, 14 in another and 15 in
  a third, and 15 of the 21 projects hide the same 6 codes. Which codes a project hides is site
  configuration, not API behaviour: read it per project rather than reusing a list between sites.

- Always render `display_values`: `pndvs` means "Pending VFX Supervisor" to nobody, and a missing key
  there is possible, so fall back to the raw code rather than dropping the option.

`corpus/findings/009_status_lists.md`

## 019_create_fields

Custom fields are creatable over REST, but you pass a display name and a duplicate silently becomes <name>_1: an idempotent ensure() must read /schema first, never POST-and-hope.

- **Trap.** A duplicate display name does not error: it creates `<name>_1`, and it keeps going. Three creates of one display name gave `sg_zzprobe_041_dup`, `sg_zzprobe_041_dup_1` and `sg_zzprobe_041_dup_2`, all at 201, all three live at once and all three reading back the identical display name.

- **A display name identifies nothing**, so a client that looks a field up by the name a person typed can match several fields or the wrong one. Match on the programmatic name. An idempotent `ensure()` must GET `/schema/Version/fields` and match first, never POST-and-hope.

- **Trap.** `DELETE` returns 204 and the field vanishes from `/schema`, but the name is not freed: re-creating it 400s, and the trashed field cannot be enumerated, so the collision is invisible.

- That is one delete-and-recreate cycle on one field name, observed once; settling whether every deleted name behaves this way costs another name, which this repo does not spend. Treat a name you have created as spent.

- On the probed site Version has 71 fields against the 61 of `probe 002`, and the nine `sg_ai_*` fields are the difference; none follow the `sg_zzprobe_<nnn>_*` convention `docs/quirks.md` mandates. Attribution of those nine to this probe is `<unverified>`: the committed code creates `zzprobe 019 *` names, and no creator is recorded anywhere.

- You pass a display name and the `sg_` prefix is added for you, so `sg_foo` becomes `sg_sg_foo`. The programmatic name is absent from the response body; take the last segment of `links.self`.

- Most creation 400s are a missing `properties`, not a refusal. Only `color`, `image` and `calculated` are rejected outright; `entity` and `multi_entity` need `valid_types` holding exactly one type, and `checkbox` needs `default_value`. `multi_entity` round-trips lineage under `relationships` (field_types/multi_entity).

- A seed must be a text field: `number` is signed 32-bit, and 64-bit ids and seeds reach 2**64-1 (field_types/number).

`corpus/findings/019_create_fields.md`

## 040_field_revive

A trashed field is revived by POST /schema/<Type>/fields/<name> with {"revive": true} at 204, but it returns at its original data_type, and a PUT changing data_type is a 200 that does nothing.

| do | why |
|---|---|
| Read the schema and match before creating | a trashed name is unlistable, so the collision is unpredictable otherwise |
| Revive with `POST <field path>` and `{"revive": true}` | it is a 204 and it is in no documentation |
| Read `data_type` back after reviving | it returns at its original type, whatever you asked for |
| Never trust a `PUT` that changes `data_type` | the top-level form is a 200 that does nothing |
| Give up on the name when the type is wrong | nothing converts a trashed field to another type |
| Never create a field to test with | the name is spent whether you trash it, revive it or re-trash it |

The quiet neighbour is worse still. A duplicate of a **live** field does not error: it silently becomes
`<name>_1` (probe 019). A create returns 201 both when it did what you meant and when your code now
writes to a field that is not the one you asked for.

`corpus/findings/040_field_revive.md`

## 042_spec_coverage

`GET /spec.json` returns the deployment's own OpenAPI v3 document. It advertises 62 operations against the 23 this corpus covers, and it disagrees with the published documentation.

- The deployment answering your calls will hand you its own endpoint list. Reconstructing one from
  documentation is unnecessary and, here, wrong.

- **The spec and the published reference disagree.** The reference documents
  `PUT /entity/{entity}/{record_id}/_revive`, `POST .../_upload_complete`,
  `PATCH /schema/{entity}/fields/{field}` and `PATCH /preferences`.

- This site's spec has none of those spellings, and has `PUT /schema/<type>/fields/<field>` and `PUT /preferences/update` instead. Probe
  041 measured the `PUT` on a schema field working. Read the spec, not the reference.

- `servers[0].url` ends in `/api/v1.1`. Every recorded call in this corpus was made against `/api/v1`.
  Probe 051 swept 20 read-only calls under both prefixes: the two are the same API, differing only in
  `api_version` in the root document and the prefix each echoes in its own `links`.

- The two upload steps with no operation in the spec are correct as they stand: `links.upload` is a
  presigned storage URL and is not a route on this API at all.

- 191KB is too large to hand an agent. `probes/042_spec_coverage.py` prints the difference between the
  spec and `corpus/endpoints/`, which is the only part that changes.

`corpus/findings/042_spec_coverage.md`

## 047_site_facts_and_the_working_week

Three site-fact calls, three different envelopes: `{data, status}`, a bare hash, and JSON:API. Only `/schedule/work_day_rules` reports a bad scope id, and it reports it as a 200.

- **Every site-fact call has its own envelope.** `/license_info` returns `{data, status}` with no
  `links`, the subscription hash returns neither, and only `/schedule/work_day_rules` is JSON:API.
  One decoder does not read all three.

- **A `project_id` or `user_id` that does not exist is a 200, not a 404.** The studio default answers
  instead, and `reason` reads `STUDIO_WORK_WEEK` for both the fallback and a real studio-wide answer.
  A client asking "is this a working day for project X" gets a plausible answer for a project that
  is not there. Check the id first.

- One endpoint, two error shapes. A missing or out-of-order parameter is a JSON:API `errors` array;
  an unparseable date is `{"status": "error", "error": "invalid date"}` with no `errors` key.
  `r.json()["errors"][0]` raises on the second.

- No paging on `work_day_rules`: a 730-day window returned 730 rows in one 61631-byte response, with
  no `page` envelope and no `links.next`. Bound the range in the request.

- `PUT /preferences/update` refused every body identically on the probed site, `{}` and a complete one
  alike, so the 400 tells a client nothing about its own payload and the parameter names in
  `/spec.json` stay unverified. The code is 111 and `source` is `null`, not the 103 with a populated
  `source` that parameter errors use elsewhere.

- The three ways to count users disagree. On the probed site `license_info.assigned` was 4, the
  subscription hash held 14 keys and there were 24 HumanUser rows, and `sg_status_list` did not
  predict which users the hash held. Do not derive a seat count from a user query.

- `POST /subscription_seat/user_subscriptions` with `{}` answers 200 with `{}`: a 200 that assigned
  nothing looks exactly like one that assigned something. Its per-user failures are a 207 whose
  messages are strings inside the hash, which `r.ok` passes over.

- The write paths for the working week, subscriptions and custom entity slots were exercised only
  with bodies that must fail. Each of the three changes configuration for every user of the site, and
  none has a dry run.

`corpus/findings/047_site_facts_and_the_working_week.md`

## 056_stock_vs_custom_field

A field with `visible.editable` false is stock and safe to depend on; true means the site can hide it, which is every custom field and a few stock ones. The `sg_` prefix decides nothing.

- **`visible.editable` is the flag, and it reads one way round.** `false` means the site cannot hide
  the field, and no custom field on the probed site read `false`. `true` is "the site may hide this",
  which every custom field is and a few stock fields are as well, so it is a strong hint and not a
  proof.

- **The `sg_` prefix decides nothing in either direction.** On the probed site 126 of 439 fields are named
  with it and 33 of those are stock, `sg_status_list` and the whole `sg_uploaded_movie` family among them.
  Probe 019 explains the other half: a field created over REST is named `sg_<display name>` whatever
  the caller passes, so the prefix marks how a field was named, not who added it.

- On the probed site 4 of 97 `visible.editable` fields are not prefixed.
  `version_sg_ai_generated_from_versions` is the reverse side of a custom `multi_entity` field, so it
  is custom under a generated name. `Project.code` and `platform_status` on Version and Shot are stock.
  Reading `visible.editable` as "custom" would have called all four wrong.

- Nothing in the schema names the origin of a field. `custom_metadata` is `""` on all 439, and
  `visible.value` is `true` on all 439, so neither separates anything. A client that needs certainty
  reads `/schema/<Type>/fields` on the site it is about to write to and matches on the programmatic
  name (probe 002), rather than deciding from a name it learned somewhere else.

`corpus/findings/056_stock_vs_custom_field.md`

## 061_shipped_statuses

Nothing in the schema marks a shipped Status. `system` is true on a minority of them; the stock set is `created_by is null`, plus `options[return_only]=retired` for the rows a site retired.

- `created_by is null` selects the shipped rows and is the only mark that does. It is one filter at
  200, so the split costs no extra call. A row an operator added names them in `created_by`, and
  `created_by` is `editable: false`, so nobody can blank it afterwards.

- `system` is a checkbox whose display name is `Locked by System`, and it does not mean "shipped":

  | selection | on the probed site |
  |---|---|
  | `created_by is null` | 19 rows |
  | `system is true` | 6 rows, `act` `dis` `ip` `na` `cfrm` `pndng` |
  | `system is true` and `created_by` set | 0 rows |
  | an `or` of the two | 19 rows, the same set as `created_by is null` alone |

  `system` is a subset, so an `or` adds nothing and `system` alone drops 13 shipped codes.

- `created_at` is not a mark either. On the probed site it is null on 17 of the 19 shipped rows and
  `2014-08-06` on `cfrm` and `pndng`, which no creator names, while every operator-added row from
  id 32 up has both a date and a person.

- The live listing is what the site kept, not what it started with. On the probed site 9 further
  rows are retired, 8 of them with no `created_by` (`cbb`, `rdy`, `blk`, `plsh`, `late`, `rsk`,
  `rrq`, `out`), and only `options[return_only]=retired` returns them. A low id proves nothing on
  its own: retired id 20, `tkt`, names a person.

- The 19 shipped codes on the probed site, with the stock `image_map_key` each points at. Resolve a
  key against the site's own stylesheet and the `/images/sg_icon_image_map.png` sprite, both of
  which answer an unauthenticated GET at 200; probe 010 and `recipes/010_status_picker` record that
  rediscovery and the offsets.

  | code | name | `image_map_key` |
  |---|---|---|
  | `act` | Active | none. On the probed site it points at a `custom_status`/`html` icon |
  | `apr` | Approved | `icon_apr` |
  | `clsd` | Closed | `icon_fin` |
  | `cmpt` | Complete | `icon_cmpt` |
  | `dis` | Disabled | `icon_na` |
  | `fin` | Final | `icon_fin` |
  | `hld` | On Hold | `icon_hld` |
  | `ip` | In Progress | `icon_ip` |
  | `na` | N/A | `icon_na` |
  | `omt` | Omit | `icon_omt` |
  | `opn` | Open | `icon_rdy` |
  | `res` | Resolved | `icon_fin` |
  | `rev` | Pending Review | `icon_rev` |
  | `wtg` | Waiting to Start | `icon_wtg` |
  | `vwd` | Viewed | `icon_fin` |
  | `recd` | Received | `icon_recd` |
  | `dlvr` | Delivered | `icon_dlvr` |
  | `cfrm` | Confirmed | `icon_thumb_up` |
  | `pndng` | Pending | `icon_voice_command` |

  15 distinct keys over 19 codes: `icon_fin` draws `clsd`, `fin`, `res` and `vwd`, and `icon_na`
  draws `dis` and `na`. The icon does not identify the status, and `icon` is the one editable field
  on the row, so a stock code can point at a custom icon.

- Which codes a site holds is site configuration, and only the shape transfers. Read the split per
  site rather than hardcoding the 19: this site retired 8 shipped rows and added 13 of its own, and
  a shipped code is still only offered where a type's `valid_values` lists it (probe 009).

`corpus/findings/061_shipped_statuses.md`

## 091_status_summary_exclusions

Excluded statuses are invisible to REST: not in /schema at any scope, not writable by PUT. status_list honours them: fin plus an excluded omt rolls up to fin, omt alone to na. **[partial]**

not measured: status_list with the exclusion removed on the same rows: the setting is not API-writable, so the before state rests on probe 079's rule, not on a toggle. Blocked on the API.

- **The setting is stored where REST cannot read it.** It is `status_list_summary_exclude` inside the
  field's `DisplayColumn` `data_type_properties`, and DisplayColumn is not a REST type. It is site-wide:
  the change event names no project, and the schema reads the same with and without `project_id`.

- The one REST trace is `Shotgun_DisplayColumn_Change` in the event log, whose `meta.new_value` holds the
  list. A client can learn the current list only from the newest such event, if the log still has it.

- **Not writable.** `PUT /schema` rejects the name and enumerates the seven writable properties, so the
  exclusion is set in the web interface only (Fields, the status field, Summary = Status, Excluded statuses).

- **`status_list` applies it.** Without an exclusion a mix rolls up to `ip` (probe 079: `[fin, wtg]` gives
  `ip`); with `omt` excluded, `[fin, omt]` gives `fin`, and `omt` alone gives `na`, not `omt`. A client
  computing its own roll-up from grouped counts must drop the excluded statuses itself, and has to be told
  which they are.

- `status_percentage` returned 0 on every set here and is not a share of anything (probe 079).

`corpus/findings/091_status_summary_exclusions.md`
