# Endpoints — Site

Every call in this family: what the card records, the edge cases that live on the call, and the verdict of every entry that measured it. Each of those lines names the door holding that entry's rules. The map is `corpus/INDEX.md`.

## `GET /license_info`

Seat counts in a `{data, status}` envelope, not the JSON:API one. `rule` decides whether `free` is a number or `-1` for unlimited, and none of the three counts equals the HumanUser row count.

- The envelope is `{"data": ..., "status": "success"}`. There is no `links` and no `links.self`, so
  a client that reads every response through a JSON:API decoder fails on this one.

- The site's own `/spec.json` example gives the five values as strings (`"assigned": "56"`). The site
  returns integers. Type-check rather than trusting the example.

- `free` is `-1`, not `0` or `null`, when `rule` is `unlimited`. Subtracting it from `total` gives a
  number larger than the licence.

- `assigned` is not the HumanUser row count and not the size of the
  `GET /subscription_seat/user_subscriptions` hash. On the probed site the three were 4, 24 and 14.
  Do not derive one from another.

- `/spec.json` marks this call with the `sudo_as_login` security scope. A script token reads it
  without one, and so does a token acting as an `Admin`. Acting as an `Artist` it is
  `401` code 110 `Must sudo as Administrator to query license information`, the API naming the
  scope in its own refusal (probe 027).

**Measured by**

- `047_site_facts_and_the_working_week` (findings) — Three site-fact calls, three different envelopes: `{data, status}`, a bare hash, and JSON:API. Only `/schedule/work_day_rules` reports a bad scope id, and it reports it as a 200.  
  rules: `doors/findings-schema`

**Silent on this call**

- `047_site_facts_and_the_working_week` — Three site-fact calls, three different envelopes: `{data, status}`, a bare hash, and JSON:API. Only `/schedule/work_day_rules` reports a bad scope id, and it reports it as a 200.

`corpus/endpoints/get_license_info.md`

## `GET /preferences`

The only place the unit behind a `duration` field is named. `prefs` narrows it to one key, and `hours_per_day` and `duration_units` are the pair a renderer needs.

- `view_master_settings` and `creative_review_settings` are JSON encoded inside a string, not nested
  objects. Decode them a second time.

- `hours_per_day` is a float, `8.0`, not an integer.

- An unknown `prefs` name is not an error. The key is absent from `data` and the status is 200, so test
  for the key rather than the status.

**Measured by**

- `002_schema` (findings) — Fetch /schema once for the type list, then /schema/<Type>/fields only for types you actually need: it is the expensive call (48KB, ~330ms each) and must never be looped over all types.  
  rules: `doors/findings-schema`
- `088_project_template_defaults` (findings) — The per-entity-type default is readable at `Project.tracking_settings.default_task_template.<Type>`, a `{type, id, name, valid}` dict. `Project.task_templates` is a separate list, not the default.  
  rules: `doors/findings-read`

`corpus/endpoints/get_preferences.md`

## `PUT /preferences/update`

Enables a custom entity slot and nothing else. On the probed site every body, valid or not, answered 400 code 111 `Updating the preferences is not available`, so the shape stays unverified.

- **The success path is deliberately unexercised.** Enabling a custom entity slot changes the schema
  of the whole site for every user and cannot be undone by this endpoint: `/spec.json` names no
  `disable_entity`. Only rejections were sent.

- The 400 precedes validation. An empty body and a complete one get the same status, the same
  code and the same string, so the error says nothing about whether the body was right. A client
  cannot use it to test its own payload.

- `code` is 111 and `source` is `null`, where the parameter errors elsewhere in the API report 103
  with a populated `source`. Read `code`, not the status.

- The refusal is a 400, not a 403. Whatever gates this call, it is not reported as an authorisation
  failure, so retrying with different credentials is not indicated by the response.

- Enabling a slot is site configuration. Read which slots are already enabled with
  `PYTHONPATH=src python -m sg_groundtruth.schema entities --custom` rather than probing for them.

**Measured by**

- `047_site_facts_and_the_working_week` (findings) — Three site-fact calls, three different envelopes: `{data, status}`, a bare hash, and JSON:API. Only `/schedule/work_day_rules` reports a bad scope id, and it reports it as a 200.  
  rules: `doors/findings-schema`

**Silent on this call**

- `047_site_facts_and_the_working_week` — Three site-fact calls, three different envelopes: `{data, status}`, a bare hash, and JSON:API. Only `/schedule/work_day_rules` reports a bad scope id, and it reports it as a 200.

`corpus/endpoints/put_preferences_update.md`

## `GET /schedule/work_day_rules`

One row per calendar day, both ends inclusive, no paging at 730 rows. A `project_id` or `user_id` that does not exist answers 200 with the studio default instead of an error.

- **Two error shapes on one endpoint.** A missing or out-of-order parameter is a JSON:API `errors`
  array; an unparseable date is a bare `{"status": "error", "error": "invalid date"}` with no `errors`
  key at all. A client reading `r.json()["errors"][0]["title"]` raises `KeyError` on the second.

- A `project_id` or `user_id` that is not on the site answers 200 with the studio rule. Nothing in the
  body says which scope answered, other than `reason`, and `reason` reads `STUDIO_WORK_WEEK` for both
  the fallback and a genuine studio-wide answer. Check the id exists before trusting the schedule.

- Both ends are inclusive. `start_date` equal to `end_date` returns one row.

- No paging. A 730-day window returned 730 rows in 61631 bytes, with no `page` envelope and no
  `links.next`. Bound the range yourself.

- `links.self` echoes the parameters back, so two responses that differ only in `project_id` differ in
  byte length while their `data` is identical.

- The dates must be `YYYY-MM-DD`. `03/02/2026` is refused, whatever `date_component_order` in
  `GET /preferences` says the site displays.

**Measured by**

- `047_site_facts_and_the_working_week` (findings) — Three site-fact calls, three different envelopes: `{data, status}`, a bare hash, and JSON:API. Only `/schedule/work_day_rules` reports a bad scope id, and it reports it as a 200.  
  rules: `doors/findings-schema`

**Silent on this call**

- `get_schedule_work_day_rules` — One row per calendar day, both ends inclusive, no paging at 730 rows. A `project_id` or `user_id` that does not exist answers 200 with the studio default instead of an error.
- `047_site_facts_and_the_working_week` — Three site-fact calls, three different envelopes: `{data, status}`, a bare hash, and JSON:API. Only `/schedule/work_day_rules` reports a bad scope id, and it reports it as a 200.

`corpus/endpoints/get_schedule_work_day_rules.md`

## `PUT /schedule/work_day_rules`

One day per call, keyed by `date` in the body rather than by a path id, and `user_id` or `project_id` absent means the change applies to the studio default for everyone.

- **The success path is deliberately unexercised.** A call with neither `user_id` nor `project_id`
  rewrites the studio calendar for every user of the site, and there is no dry run and no undo. The
  400 rows above are what pins the parameter names; the 200 shape comes from the site's own
  `/spec.json`.

- Scope is decided by omission. No `user_id` and no `project_id` means studio-wide, which is the
  widest possible effect and also the shortest body. Send the scope explicitly.

- Every parameter is validated in one pass: a body wrong in two places lists both keys under `source`.

- `recalculate_field` is what moves existing Task rows. Omitting it changes the calendar and leaves
  `duration` and `due_date` where they were, so the two can be made to disagree.

- Only `date` addresses the row. There is no id, no `DELETE`, and no documented way to remove an
  exception other than writing the day back to what the work week says.

- The 200 response shape adds `project` and `user` references that the `GET` rows do not have.

**Measured by**

- `047_site_facts_and_the_working_week` (findings) — Three site-fact calls, three different envelopes: `{data, status}`, a bare hash, and JSON:API. Only `/schedule/work_day_rules` reports a bad scope id, and it reports it as a 200.  
  rules: `doors/findings-schema`

**Silent on this call**

- `047_site_facts_and_the_working_week` — Three site-fact calls, three different envelopes: `{data, status}`, a bare hash, and JSON:API. Only `/schedule/work_day_rules` reports a bad scope id, and it reports it as a 200.

`corpus/endpoints/put_schedule_work_day_rules.md`

## `GET /spec.<format>`

The site publishes its own OpenAPI v3 document, `json` or `yaml`, and it lists 62 operations where this corpus covers 23. The suffix is required and any other 406s.

- `servers[0].url` ends in **`/api/v1.1`**, not `/api/v1`. The path this client uses is not the one the
  site advertises, and nothing in the corpus has yet measured whether the two differ.

- `info.version` reads `1.x`, and the title has a trailing space. Neither is a useful version check;
  `endpoints/get_root` returns the real build.

- The spec is the authority for one deployment. The published documentation lists operations under
  different names, `PUT /entity/{entity}/{record_id}/_revive` and `POST .../_upload_complete` among
  them, that this site's spec does not have.

- 191KB is too large to hand an agent whole. Diff it against the corpus and read the difference, which
  is what `probes/042_spec_coverage.py` prints.

**Measured by**

- `051_api_version` (findings) — /api/v1 and /api/v1.1 are the same API. Across 20 read-only calls the only difference is api_version in the root document and the prefix each echoes in its own links. Any other segment is 404.  
  rules: `doors/findings-protocol`
- `042_spec_coverage` (findings) — `GET /spec.json` returns the deployment's own OpenAPI v3 document. It advertises 62 operations against the 23 this corpus covers, and it disagrees with the published documentation.  
  rules: `doors/findings-schema`
- `084_task_template_reapply` (findings) — Changing `task_template` on a Shot only adds: one Task per template task not yet linked by `template_task`. Nothing is removed or merged; a hand-made Task of the same content and step is duplicated.  
  rules: `doors/findings-write`
- `007_reference_disagrees_with_spec` (reports) — Four calls in the published REST reference exist under no spelling in the deployment's own OpenAPI document, which names two of them differently.  
  rules: `doors/reports`

`corpus/endpoints/get_spec_format.md`

## `GET /subscription_seat/user_subscriptions`

Returns a bare hash of user id to subscription string with no `data` and no `links`, holding only some HumanUser rows, and a `null` value means the user has no subscription rather than no such user.

- The hash holds a subset of HumanUser rows and the endpoint gives no rule for which. On the probed
  site it held 14 of 24 HumanUser rows, and `sg_status_list` did not predict membership: 5 of 6 `act`
  users were present and 9 of 18 `dis` users were too. Treat a missing key as unknown, not as
  "no subscription".

- `null` is a value in the hash, not an absence. A user present with `null` and a user absent are two
  different states and only the first one is stated.

- Keys are strings. Comparing them against an integer id from `/entity/human_users` matches nothing.

- On the probed site the only non-`null` value was `not_for_resale`. The vocabulary of subscription
  names is site data; read it off the hash rather than hardcoding a list.

- The size of this hash is not `assigned` from `GET /license_info`. On the probed site they were 14
  and 4.

**Measured by**

- `047_site_facts_and_the_working_week` (findings) — Three site-fact calls, three different envelopes: `{data, status}`, a bare hash, and JSON:API. Only `/schedule/work_day_rules` reports a bad scope id, and it reports it as a 200.  
  rules: `doors/findings-schema`

**Silent on this call**

- `047_site_facts_and_the_working_week` — Three site-fact calls, three different envelopes: `{data, status}`, a bare hash, and JSON:API. Only `/schedule/work_day_rules` reports a bad scope id, and it reports it as a 200.

`corpus/endpoints/get_subscription_seat_user_subscriptions.md`

## `POST /subscription_seat/user_subscriptions`

Body is a bare hash of user id to subscription string, not a JSON:API document. An unknown id is a whole-request 400, and a hash naming no user is a 200 returning `{}`.

- **The success path is deliberately unexercised.** Every call that could succeed changes the
  subscription of a real user of a real site, and there is no dry-run parameter and no undo. The
  rejections above are what pins the body shape; the 200 and 207 rows come from the site's own
  `/spec.json`.

- `{}` answers 200 with `{}`. A caller that treats a 200 as "the assignment happened" cannot tell an
  applied change from a body that named nobody.

- The whole request fails on the first unknown id: the 400 replaces the per-user hash, so nothing is
  reported about the ids that were valid. Validate ids against `/entity/human_users` first.

- A per-user failure is a **207**, not a 400, and its message is a string inside the hash rather than
  in an `errors` array. A client checking `r.ok` passes straight over it.

- The error message is in `title`. `detail` is `null`, `source` is `{}`.

**Measured by**

- `047_site_facts_and_the_working_week` (findings) — Three site-fact calls, three different envelopes: `{data, status}`, a bare hash, and JSON:API. Only `/schedule/work_day_rules` reports a bad scope id, and it reports it as a 200.  
  rules: `doors/findings-schema`

**Silent on this call**

- `047_site_facts_and_the_working_week` — Three site-fact calls, three different envelopes: `{data, status}`, a bare hash, and JSON:API. Only `/schedule/work_day_rules` reports a bad scope id, and it reports it as a 200.

`corpus/endpoints/post_subscription_seat_user_subscriptions.md`
