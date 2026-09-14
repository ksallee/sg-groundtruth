# Field types

One per `data_type`: how it reads, writes, clears and filters. Each rule is the card's own **Traps**, copied whole. The matrices behind them are in the cards.

## calculated

A calculated field refuses every write with "is read only" and every filter with "cannot be used in a filter", yet it sorts and summarizes fine, and the formula is exposed as calculated_function.

- **Filter it by rewriting the formula.** `["workload", "is", 600]` 400s; `["duration", "is", 600]` gets the
  same rows for `{duration}`. There is no equivalent for `CONCAT({code}, {id})`: page and match client-side.

- Sort is the one query verb that survives: top-N by a computed column is one call, on all four fields.

- A `float` renderer returns a string, so `sorted(rows, key=...)` on the raw value sorts
  lexicographically and puts `"0.9"` after `"0.625"`. Cast before comparing (field_types/float).

- A `text` renderer formats numeric operands for display: `CONCAT({code}, {id})` on id 1226 gives
  `"charA1,226"`, a thousands separator inside a string a client might parse back.

- Division by null yields null, not an error: `workload_per_day_per_assignee` is null on 21 of 40 rows where
  `{workload_assignee_count}` is 0. Fill rate measures the operands, so drop the type from fill ranking (probe 007).

- `default_value` is present in `properties` and always null. Nothing sets it; do not read it as the
  value of an unpopulated row.

`corpus/findings/field_types/calculated.md`

## checkbox

A checkbox is two-state, never null - an untouched row already reads false, null is unwritable and unfilterable, and the only relations are is/is_not, so fill rate reads 100% on every checkbox.

- **Fill rate is meaningless on this type.** Every checkbox on every row is non-null, so a fill-rate scan
  reports 100% for all four Version checkboxes while every row holds the same value (probe 007). Drop
  `data_type == "checkbox"` from fill ranking before scoring; no threshold separates an informative
  checkbox from a dead one.

- The `is_not None` fill-rate filter that works on every other type 400s here, in both `_search` and
  `_summarize` (probe 020). Special-case the type; do not catch the 400 and score 0.

- `_summarize` returns the UI glyph, not the value, so the empty-group trick that yields an empty count
  on a list field (`[('<value>', 99), ('', 1)]`) never sees `''` here and reports the field fully
  populated.

- Strings coerce on read and write (`"true"` -> `True`), so a checkbox set from a CSV or a form post
  works until someone sends `"1"`. That 400s with a different error shape (`Invalid data for 'checkbox'
  data type`, under `source`) than a bare `1` (`expected [String, FalseClass, TrueClass] ... got
  Integer`). Match on the status, not the title.

`corpus/findings/field_types/checkbox.md`

## color

`Task.color` holds the token `pipeline_step` rather than a colour: read `step.Step.color` in the same dotted call and keep a client default. A real value is decimal r,g,b, never hex.

- Never treat `Task.color` as a colour. A swatch renderer parsing it as `r,g,b` gets `pipeline_step` on
  every row this site has and must follow `step.Step.color` instead.

- Decimal `r,g,b`, no spaces and no `#`, matching `Status.bg_color` (probe 010). Hex is rejected on write
  and on filter. Build it with `"%d,%d,%d" % rgb`, split on `,` to read.

- No `Task.color` row on this site is empty and a written null is refused, so a fill-rate count over it
  reads 100% and measures nothing (probe 007).

- A bad filter value is a 400 on `Step` and `Project` but a silent 0 rows on `Task`.

- Writing a legacy name is lossy: `"Red"` stores `253,1,0` and never reads back as `"Red"`, so filtering
  on the name it was written with returns 0.

`corpus/findings/field_types/color.md`

## date

A date is the string "YYYY-MM-DD" and nothing else: any timestamp 400s on write and as a filter value. Every negating operator (is_not, not_in, not_in_last) also matches rows that are null.

- **Every negating operator also returns null rows.** `is_not "2026-09-02"`, `not_in [...]` and
  `not_in_last [1,"MONTH"]` each matched the row with no date. Use `is_not null` for "has a value"; it is
  the only filter that means that.

- A `date` never accepts a timestamp, on write or as a filter value; `date_time` accepts both
  `"2026-09-02"` and `"2026-09-02T00:00:00Z"`. That and the read shape are the only differences: the
  operator list and the relative-value shapes are identical between the two types.

- `between` with a `null` endpoint returns 0 rows and no error. Use `greater_than` / `less_than` for an
  open-ended range; they are strict, not inclusive.

- `HOUR` is a legal unit but the value has no time part, so anything under 24h collapses to today: a date
  5 days back missed `in_last [1,"HOUR"]` and matched `in_last [200,"HOUR"]`.

- `""` is not a distinct empty state: it is written, filtered and read back as `null`.

`corpus/findings/field_types/date.md`

## date_time

Stored and read as UTC `YYYY-MM-DDTHH:MM:SSZ`: a written offset is silently normalised, a zoneless string is taken as UTC, and a date-only filter value means midnight UTC, not the whole day.

- A written offset is not preserved: `05:06:07+05:00` reads back as `00:06:07Z`. Convert to UTC yourself
  and keep the original zone in your own field if a client must redisplay local wall-clock time.

- A zoneless string is **assumed UTC**, not site-local: `"2026-03-04T05:06:07"` is not "5am here".

- `is` is exact-second equality, so `is "2026-03-04"` finds only rows at `00:00:00Z`. Match a day with
  `between ["2026-03-04", "2026-03-05"]` or `in_calendar_day`.

- `""` 400s where a `text` field accepts it; only `null` clears. There is no numeric form: epoch integers
  400 with the `[String, NilClass]` type error, epoch strings with the format error.

- `created_at`/`updated_at` 400 with "is editable on create only"; check the schema's `editable` flag
  before writing any timestamp.

`corpus/findings/field_types/date_time.md`

## duration

A duration is a bare integer of minutes and the unit is on the site: `GET /preferences` gives `hours_per_day` and `duration_units`. A Float truncates toward zero at 200, so round before writing.

- **The unit is on the site, not on the field.** No `/schema` route names it. Read `hours_per_day` and
  `duration_units` once from `GET /preferences`, then render.

- **A Float truncates instead of failing.** `number` 400s on `3.7` (`field_types/number`); `duration`
  takes `90.9` and stores `90`. Round before writing an average, a ratio or `total/2`.

- **`"2:30"` is not a duration.** The only string the API accepts is one that parses as a number.

- **Negation includes nulls; comparison excludes them.** `is_not 480` and `not_in [999999]` return the
  null rows too (3 and 4 of 4); `greater_than -1` returns only the 2 rows holding a value. A row holding
  `0` is `is_not None`, so a field full of zeroes scans as fully populated (`probe 007`); rank by
  `greater_than 0`.

`corpus/findings/field_types/duration.md`

## entity

An entity link is a {type,id} hash under `relationships`, cleared only by null. Enforce `valid_types` yourself: it binds on a few fields, is ignored on most, and nothing in the schema marks which.

- Validate the type against `valid_types` client-side, on every field. A client cannot predict which
  field will protect it, and an unenforced write stores nonsense at 200: `sg_task` (`['Task']`) took a
  Shot and read it back as a Shot.

- No project-consistency check. Pointing a sandbox Version at a Shot in another project returned 200 and
  read back linked, with nothing in the response flagging it. Compare projects before writing.

- A wrong `type` for a real id 400s here only because ids come from one site-wide sequence (250 shots
  862..1111 vs 250 assets 1226..3588, zero overlap), so the wrong table holds no such row. That is a lookup
  miss, not type validation.

- Reading `attributes` alone makes every entity link look absent, and `filter[]` needs the full
  `{type, id}`: `[{"id": N}]` and bare ints both 400 (probe 017), while a bad `?fields` name is silently
  dropped at 200 (probe 004).

`corpus/findings/field_types/entity.md`

## entity_type

An entity_type field is a bare schema-name string in attributes, validated on write against 290 built-in type names but not against the site's enabled ones, and filtered only by is/is_not/in/not_in.

- Not an `entity` field. `entity` stores a `{type, id}` link under `relationships` and takes the entity
  vocabulary (`type_is`, `name_contains`, nine operators); `entity_type` stores the type name alone under
  `attributes` and takes four. An `{type, id}` hash 400s on both read and write here.

- Filters are case-sensitive, unlike a `list`, where `'type a'` matches `'Type A'`. `"shot"` returns 0 rows
  with no error, so a lowercased value reads as "nothing matches".

- The 290-name legal set is the built-in type table, not the site's schema. Validate against
  `/schema` before writing, or store a type name that has no endpoint.

- Existing rows hold values the validator rejects: `PermissionRuleSet.entity_type` reads
  `PermissionRuleSet.HumanUser`, and writing that back 400s. Never round-trip a read value into an update.

- Four of the five are read-only, and a write to one 400s with `is editable on create only.`

`corpus/findings/field_types/entity_type.md`

## float

A float reads back as a JSON string rounded to 6 decimals and rejects Integer on both write and filter: send 1.0 or "1.0", never 1; 0.0 and null stay distinct, and 1e-9 silently becomes 0.0.

- Integer is rejected on both halves: `PUT {"field": 1}` and `["field", "is", 1]`. A client that computed
  an aspect ratio as exactly `2` must send `2.0` or `"2.0"`. `number` is the mirror image; it rejects Float.

- The value is a string, so `row["attributes"][f] > 1.0` raises and `== 1.0` is False. Cast on read.

- Precision is 6 decimal places, applied on write, at 200 and without warning. `1e-9` stores as `0.0` and
  then matches `is 0.0`, not `is None`.

- `not_in` returns rows whose value is null, so it is not the complement of `in`. Intersect it with
  `is_not None` for "has a value, but not that one".

`corpus/findings/field_types/float.md`

## image

Only the upload dance sets an image: every value but null 400s, and clearing it also clears `filmstrip_image`. The value is a presigned URL re-signed per read, so store the row id, never the string.

- `is_not None` matches a row that is still transcoding, so a job that filters and then downloads
  fetches `thumbnail_pending.png`. Filter, then check the prefix on each row.

- Transcoding took ~38 seconds for a 16x16 97-byte PNG. Poll the field every 5 seconds.

- The REST upload never fills `image_blur_hash`: still `null` 102 seconds after the thumbnail settled
  and after a second upload to `filmstrip_image`. The one sample-project row holding one
  (`'YXFZJ]4U-=ISt8oh…'`, 68 chars) was made outside REST. Do not wait on it.

`corpus/findings/field_types/image.md`

## jsonb

jsonb filters, where serializable cannot: is, is_not, contains, not_contains, values always hashes. Note.meta stores what you send but is create-only, so nothing written there is ever editable.

- **The filter on `EventLogEntry.audit_trail` is a silent no-op.** `is null` and `is_not null` each return
  the full unfiltered page, so the two together over-count every row. The field is filterable per the
  schema, absent from every response, and ignored in every `WHERE`.

- **`Note.meta` is a one-shot slot.** A client can seed it at create and never revise it, and there is no
  update or clear. `editable: false` in the schema does not predict the create path; a create-time write
  succeeds where every later one 400s.

- **A one-element filter array is unwrapped.** `is [[]]` reaches the field as `[]`, which matches `null`
  rows, so a stored empty array cannot be selected. `contains [{"x": 1}]` is unwrapped to the hash and then
  fails to match an array-valued row.

- **`contains` reaches into objects only.** A stored array is unmatchable by any containment value: a hash
  finds nothing and an array is unwrapped first.

- **Distinct from `serializable` on every axis but read.** `serializable` has no `Valid relations` list and
  cannot be filtered; `Task.splits` accepts a write at 200 and stores `null`. `jsonb` filters with four
  operators and stores exactly what it is given. Both return a decoded value under `attributes`.

`corpus/findings/field_types/jsonb.md`

## list

A list is one bare string in attributes; a write outside valid_values 400s and is case-sensitive, while filters are case-insensitive and only is/is_not/in/not_in exist.

- Never round-trip a filter value into an update.

- An invalid operator 400s (probe 017); an invalid value does not, so a dropdown typo reads as "no rows match".

- "list" names the schema, not the value: it holds one string, and an array 400s with `expected [String, NilClass]`.

- `viewed_by_current_user` is flagged `editable: true` and takes a 200, but writing `'read'` reads back
  `'unread'`: computed per API user, not storage (probe 007).

- `default_value` is applied on create when the field is omitted, so a fill-rate count over a `list` measures
  the default, not intent (probe 007).

`corpus/findings/field_types/list.md`

## multi_entity

A bare list replaces the whole link set, but {"multi_entity_update_mode": "add"|"remove"|"set", "value": [...]} adds and removes in place; the field never reads null and null 400s.

- Both incremental spellings that live in the query string return 200 having **silently replaced** the
  list. The loss is a success response, not an error; send the mode in the body.

- A bare list replaces, so an append coded as read-then-PUT loses any link a concurrent writer added
  between the two calls. Use the `multi_entity_update_mode` wrapper, not read-modify-write.

- `in [X]` means "links any of X" and `not_in [X]` means "links none of X", so it matches empty rows, as
  does `is_not`. "Links all of X" has no operator: repeat `is` once per entity, as separate filter rows.

- `in` with only unresolvable ids is field-dependent, so a negative control built that way must be checked
  per field. On `Version.sg_ai_generated_from` it returns the rows linking nothing rather than zero rows;
  on `Note.note_links` it returns zero rows though rows with an empty list exist (`recipes/009`). Mixed,
  `in [A, 99999999]` returns A's rows. Which side varies, and why, is unprobed.

- A dotted path through this field reads back nothing: 200, key absent from `attributes`, in `GET ?fields`
  and in `_search` alike, while the identical path filters correctly (probe 016). To read the far side,
  query the child entity filtered by the parent.

- Read order is not insertion order (adding B then A read back A then B), so never treat it as a sequence.

`corpus/findings/field_types/multi_entity.md`

## number

A number is a signed 32-bit integer: floats 400, 2**31 is "integer out of range", and 0 is not null, yet is_not and not_in match null rows while greater_than and less_than do not.

- **Signed 32-bit, not 64.** A 64-bit id or seed reaches `2**64-1` and must be stored in a `text` field
  (`probe 019` saw the same ceiling on a created field). The create path names the cause,
  `PG::NumericValueOutOfRange`; the update path says only `Invalid statement.`

- **A float is rejected, not coerced.** `int()` anything computed (a mean, a ratio, `n/2` in Python 3)
  before writing it. A numeric string coerces, so `"42"` works and `42.0` does not.

- **`0` is a value, `''` is not a clear.** `null` is the only clear. Following `probe 007`: a row holding
  `0` is `is_not None`, so a number field full of zeroes scans as 100% filled, exactly like a checkbox
  full of `False`. Rank a number field by `greater_than 0`, or by `_summarize` grouping (`probe 020`),
  never by fill rate.

- **Negation includes nulls; comparison excludes them.** `is_not 1001` and `not_in [999999]` return the
  null rows too (3 and 4 of 4), while `greater_than -1` returns only the 2 rows that hold a value. Any
  "everything except X" filter over a sparse number field silently sweeps in every unset row.

`corpus/findings/field_types/number.md`

## password

A password field reads as a constant seven-asterisk mask on every row, including through a dotted path; it cannot be filtered, sort is accepted and ignored, and it must never be written.

- The field passes every generic inspector test (`visible: true`, `ui_value_displayable: true`, present in
  `/schema/<Type>/fields`) and returns a value, so exclude `data_type == "password"` by name from field
  pickers, from row exports and from anything that echoes a read back into a write.

- Fill-rate scanning reads 100%, and the `is_not None` correction 400s. Drop the type before ranking,
  the way probe 007 drops `checkbox`.

- A sort on a `password` field is a silent no-op. Validate a user-supplied sort key against the schema
  rather than trusting a 200 to mean the rows came back ordered.

- `ClientUser.password_proxy` reports `editable: true`. Treat that as a schema claim only: no probe writes
  a `password` field, and neither should a client.

`corpus/findings/field_types/password.md`

## percent

A percent is a bare integer on a 0-100 scale (50% is 50, and 0.5 is rejected as Float), but nothing is clamped, so -1, 1000 and 2**31-1 all store at HTTP 200.

- **Integer or nothing, on both halves.** `PUT {"field": "50"}` and `["field", "is", "50"]` each 400
  with `expected [Integer, NilClass] ... but got String`. `int()` a value out of a CSV or a form field
  before sending it.

- **The 0-100 range is a convention, not a constraint.** `-1`, `101` and `1000000` all store at 200 and
  read back unchanged, and no `properties` key declares a bound. Validate before writing, and clamp on
  read; a percent field is not evidence that its value is a fraction of a whole.

- **`0` is a value and `""` is not a clear.** Following `probe 007`, a row holding `0` is `is_not None`,
  so a percent field full of zeroes scans as 100% filled. Rank by `greater_than 0`, never by fill rate.

- **Negation includes nulls; comparison excludes them.** `is_not 50` and `not_in [50]` return the null
  rows too, 3 of 5; `greater_than -1` returns only the 3 rows holding a value. A "not yet at 100%"
  filter written as `is_not 100` sweeps in every unset row.

`corpus/findings/field_types/percent.md`

## pivot_column

A pivot_column is a web-UI task rollup with no REST implementation - it reads null on every row, and write, filter, sort and _summarize each fail with a different error.

- These pass every generic test an inspector applies (`visible: true`, `ui_value_displayable: true`,
  present in `/schema/<Type>/fields`) and then return null for every row.

- Fill-rate scanning breaks twice: the `is_not None` probe 400s like a `checkbox`, and the
  `_summarize` fallback 500s rather than 400s. A scanner that retries on 5xx retries a permanent
  failure 45 times per site.

- Only the write error names the field. A request that 400s with `Read failed for entity type [Shot]`
  gives no clue which sort key caused it; match on code 104 plus the sort you sent.

- `step_0` exists on types that have no Steps at all, so its presence says nothing about whether the
  type is task-tracked. Read `Step.entity_type` for that.

Exclude `data_type == "pivot_column"` from field pickers and from any payload built by iterating the
schema. For the same information, query `Task` filtered on `entity` and `step`, and aggregate
`sg_status_list` yourself.

`corpus/findings/field_types/pivot_column.md`

## serializable

No operator works on a serializable field: every filter 400s as unfilterable. Task.splits answers a well-formed array of hashes with 200 while storing null, so REST cannot write it.

- **A client cannot query into a blob.** No operator means no `is None` to rank fill rate by (`probe 007`)
  and no way to find the rows holding a marker; `_summarize` (`probe 020`) has nothing to group on. Fetch
  rows on some other filter and inspect the decoded value client-side.

- **`Task.splits` answers 200 and stores nothing.** A client that writes state there and re-reads it cannot
  tell a discarded write from an empty field. Read back every serializable write.

- **Two failure layers, two error shapes.** A wrong Ruby class gives code 103 with the accepted-class list
  and an empty `source`; a right class the setter chokes on gives code 104 with a raw Ruby message and
  `source: null`. Neither names the key at fault.

- **The column takes arbitrary JSON; the field refuses it.** `EventLogEntry.meta` holds nested objects,
  lists, booleans and nulls, so the storage is a blob. Of the four editable fields three are outside a
  project: `Project.tracking_settings` is site configuration, `SavedFilter.filters` and `RvLicense.meta`
  have no `project` field. A project-scoped blob to write does not exist here.

`corpus/findings/field_types/serializable.md`

## status_list

REST does not enforce hidden_values: a project-hidden status writes and reads back fine, so every client must subtract it itself. Only valid_values is enforced.

- `hidden_values` is not a subset of `valid_values`. On the probed sandbox project Task hides `blk` and
  `rdy`, neither of which `valid_values` contains, so writing one is 400 while the hidden-but-valid `hld`
  writes at 200 and reads back. Subtracting one set from the other is right for offering a choice and wrong
  for testing a row: a row may hold a code outside the usable set (`recipes/005`).

- `hidden_values` is not enforced by the API. REST 201s and 200s on a status the project's UI refuses to
  offer, so **every client must subtract `hidden_values` itself** (probe 009). The API will not do it.
  Conversely, do not treat a hidden code read back off an entity as corrupt: it is a legal stored value.

- **Permitted is not safe.** An operator reports that a hidden status set this way can break the web UI for
  that entity. Unverified: it is not observable through the API (see `docs/quirks.md`). Until someone
  checks it in a browser, treat writing a hidden status as something to avoid, not merely as something the
  server allows.

- A wrong code in a filter is a silent 0 rows, indistinguishable from a status nothing holds.

- Display labels are accepted nowhere. Round-trip through `display_values` in both directions, and fall
  back to the raw code when a key is missing.

- No substring operator, so there is no server-side type-ahead over statuses. Fetch `valid_values` once
  and filter the list client-side. Sorting and filtering is on the code, which is not alphabetical by label.

- Codes are per entity type: `Version` has 16, `Shot` 10, `Shot.sg_latest_vendor_status` 6. Never reuse a
  code across types, and read the schema per field, not per entity.

`corpus/findings/field_types/status_list.md`

## summary

A summary field is a live rollup: refused on write even where editable=true, unfilterable, unsortable, and null on every custom one here, so re-run the query /schema exposes to select on it.

- **Fill rate is meaningless on this type.** `open_notes_count` is never null, so it scans as 100% filled
  while holding one value: 100 Versions all read `0` (probe 007). The other four read `null` on every row
  and scan as 0% filled while their queries match rows. Exclude `data_type == "summary"` from fill
  ranking; the `is_not None` probe 400s, as does `_summarize` grouping.

- Sort fails silently. `?sort=code` and `?sort=-code` return different orders, `?sort=open_notes_count`
  returns the unsorted order, and so does `?sort=definitely_not_a_field`: an unsortable field and a
  typo are indistinguishable at 200.

- `editable: true` describes the field-configuration form in the web interface, not the REST value, and
  the refusal cites the data type rather than the field. Three of the 42 summary fields on this site
  claim it, so a client building an update form from `editable` offers three that can never be saved.

- 38 of the 42 are `open_notes_count`, one per entity type, all counting Notes whose status is `opn`,
  `ip` or `rdy`. That set is the site's definition of "open", readable from `properties.query` and site
  configuration rather than an API constant: read it instead of hardcoding the three codes.

`corpus/findings/field_types/summary.md`

## text

A text field has no empty string: writing "" stores null, so `is ""` and `is None` are one filter; matching is case-insensitive, whitespace is stripped, and a non-string 400s.

- Writing `""` returns 200 and stores `null`. A client round-tripping a form field cannot distinguish
  "user cleared it" from "never set"; encode that distinction in a sentinel string.

- Every operator is case-insensitive, including `is`. There is no case-sensitive text match. Filter
  broadly and re-check the case client-side.

- `is_not` and `not_contains` return the null rows, so `is_not X` is not the complement of `is X`.
  `is ''` matches exactly the rows `contains ''` skips.

- Leading and trailing whitespace is stripped on write, silently, so `'   '` is stored as `null`.

- `cached_display_name` reports `editable: True` and accepts a write at 200, then discards it. It
  mirrors `code`, and re-reads as the new `code` after a rename. Never write it.

- `in [None]` teaches nothing: code 104, `source: null`, `detail: null`. Use `is None`.

`corpus/findings/field_types/text.md`

## timecode

A timecode stores milliseconds as a signed 32-bit integer. No schema or preference names its frame rate, but a _summarize group_name renders `HH:MM:SS:FF` and the rate solves out of that.

- **The rate is real but hidden.** Solve it once per site from two `_summarize` writes and store it;
  a client that guesses 24 or 25 is wrong by a frame inside the first second.

- **A timecode field rejects timecode strings.** `"01:00:00:00"` and the drop-frame `"01:00:00;00"`
  both 400 on write and again inside a filter, and a numeric string does not coerce the way it does for
  `number` and `duration`. Send `int` milliseconds.

- **Nothing is validated as a time.** `-3600000`, `86400001` and `2147483647` all store, and render
  as `-1:59:59:00`, `24:00:00:00` and `596:31:23:16`; `-1` renders as `-1:59:60:00`, a 60th second.
  Range-check before writing. The API only enforces the 32-bit column.

- **Negation includes nulls; comparison excludes them.** `is_not 3600000` and `not_in [999999999]`
  return the null rows too (3 and 4 of 4), while `greater_than -1` returns only the 2 rows holding a
  value. A row holding `0` is `is_not None`, so a field full of zeroes scans as fully populated
  (`probe 007`); rank by `greater_than 0`.

- **A new field belongs in `text`, not here.** Every stock field a cut or a source clip uses for
  timecode is `text` plus a `number` rate, which round-trips `HH:MM:SS:FF` and survives drop frame.

`corpus/findings/field_types/timecode.md`

## url

The value is a presigned link re-minted on every read and expiring on `X-Amz-Expires`, so persist the Attachment id and re-read. No filter relation exists at all, and sort is a 200 no-op.

- **"Has media" is not a query.** Page the rows with `fields=sg_uploaded_movie` and test the value
  client-side. `_summarize` refuses with the same message under `API summarize()` (probe 021), so a
  fill-rate scan must special-case `data_type == "url"`.

- The filterable neighbours are proxies, not answers. `image is_not None` and
  `sg_uploaded_movie_transcoding_status is_not None` both matched exactly the media-holding rows on
  the sample project, and on two Versions uploaded and then cleared both still matched the row after
  `sg_uploaded_movie` had gone null. A picker built on either offers Versions with no media.

- The url is regenerated per read and signed with an expiry. Anything that caches it (a database
  column, a rendered page, a message to a chat client) serves a dead link once it lapses.

- Read `link_type` before anything else. `upload` and `web` are indistinguishable by keys, and a `local`
  value has no `url` key at all, so indexing `value["url"]` raises on the shape a published file uses.

`corpus/findings/field_types/url.md`

## uuid

A uuid field is server-generated and rejects every write with "is read only", so it cannot hold your key; it filters on is/is_not/in/not_in only, and a malformed value 400s.

- **`is null` is a 400, not a filter.** Use `is ""` for "unset" and `is_not ""` for "set". The empty
  string is legal only with `is` and `is_not`: `in [""]` fails as a malformed uuid.

- **A malformed filter value 400s the whole read.** Code 104 `invalid input syntax for type uuid`
  surfaces the database. A prefix, a `urn:uuid:` form, surrounding whitespace and any non-uuid string all
  fail. Validate client-side; there is no partial match to fall back on, since `contains` is unsupported.

- **`is_not` and `not_in` return the rows where the field is `null`**, so `is_not X` is not the
  complement of `is X`. Add `is_not ""` to exclude them.

- **Sorting on a uuid field fails**, on both spellings: `GET /entity/icons?sort=uuid` and `_search` with
  `"sort": "uuid"` return 400 code 104 `Read failed for entity type [Icon]`, with `source` and `detail`
  null. `sort=id` on the same endpoint returns 200. Page by `id` and sort client-side.

- **It cannot be your correlation key.** A uuid field is generated by the server, is not unique, and
  refuses every write. To tie a Flow PT row to a record in another system, put your identifier in a
  `text` field, which is writable and supports `is`, `in` and `contains`.

`corpus/findings/field_types/uuid.md`
