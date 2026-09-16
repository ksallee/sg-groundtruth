# Recipes

A verified call and its real response, addressed by the task. The heading is the intent and the rules are the recipe's own **Notes**. The code is in the entry.

## 001_publish_version_with_media

Publish a generated image to Flow PT as a Version, with provenance and the workflow attached

- `project` is not schema-mandatory on Version but omitting it returns 400 (probe 012).

- `entity` must be a `{type, id}` hash; a bare shot id 400s (probe 012, `field_types/entity`).

- `sg_status_list` accepts only a code in the field's `valid_values`, and `hidden_values` is not enforced, so subtract it per project yourself (`field_types/status_list`).

- `upload_data` must be present in the complete call even though it is empty (probe 013).

- The complete call takes `Content-Type: application/json`; the vendor type 415s there (probe 014).

- The field in the path picks the upload type: `/image/` a Thumbnail, any other field an Attachment, no field at all a generic Attachment on `attachment_links` (probes 013, 014).

- Reading `image` straight back gives a placeholder under `/images/status/transient/` until the transcode lands, so test that prefix rather than truthiness (probe 013, `field_types/image`).

- To find the attachments again use `POST /entity/attachments/_search` with `Content-Type: application/vnd+shotgun.api3_array+json` and an entity hash filter (probe 014).

`corpus/recipes/001_publish_version_with_media.md`

## 002_batch

Apply many creates, updates and deletes in one atomic call, and match the results back to the requests

- **A batch cannot use an id it creates.** Every way of pointing request 1 at request 0's row was
  rejected, and the failure is the whole batch, so nothing at all lands.

  | `entity` value sent | result |
  |---|---|
  | `{"type": "Shot", "id": "$0"}` | 400 `Invalid field value, update failed [5 - Update failed for [Version.entity]: Value is not legal.]` |
  | `{"type": "Shot", "id": -1}` | 400, the same |
  | `{"type": "Shot", "id": "0"}` | 400, the same |
  | `{"type": "Shot", "id": "u1"}`, request 0 sent with `"uuid": "u1"` | 400, the same |
  | `{"type": "Shot", "uuid": "u1"}`, request 0 sent with `"uuid": "u1"` | 400 `Invalid field value, update failed [5 - Update failed for [Version.entity]: Invalid statement.]` |

  The `uuid` a delete row returns is generated per request and is not an input. Build a dependent
  graph as one batch per level: create the parents, read their ids out of the response, substitute,
  then send the children. Steps 1 and 2 above are that sequence.

- **Results are in request order**, one row per request, interleaved by neither id nor type. A batch of
  `[update 29926, create, update 29927, create, update Shot 7557]` answered in exactly that order, so
  `zip(requests, response["data"])` is correct and no key matching is needed.

- Two creates sending the same `code` came back as two rows distinguished only by position and by the new ids, 29930 and 29931.

- **One failing request rolls back every other one.** Each round below sent a good create, one bad
  request, and an update of an existing row whose `description` read `before`:

  | the bad request | status | after it |
  |---|---|---|
  | `update` `record_id` 999999999 | 404 `Entity of type [Version] with id=999999999 does not exist.` | 0 rows created, `description` still `before` |
  | `delete` `record_id` 999999999 | 404, the same | 0 rows created, `description` still `before` |
  | `create` with `sg_not_a_field` | 400 `Invalid field value, update failed [2 - Invalid field name: field [Version.sg_not_a_field] does not exist or user does not have access permission.]` | 0 rows created, `description` still `before` |
  | `create` with `sg_status_list: not_a_status` | 400 `Invalid field value, update failed [5 - Update failed for [Version.sg_status_list]: 'not_a_status' is not a valid status. Valid statuses: 'na', 'rev', 'vwd', 'apr', 'custom', 'fin', 'ip', 'clsd', 'cmpt', 'cfrm', 'pndad', 'pndl', 'pndvs', 'part', 'pass', 'pndng'.]` | 0 rows created, `description` still `before` |

  The rollback is the reason to use the endpoint. A timeout is not covered by it: see the size note.

- **A batch create skips the validation a single create applies, and the row it makes is unreadable.**
  `POST /entity/versions` with no `project` is 400 `API create() missing 'project' attribute: {"code" => "v001"}`.
  The same create inside a batch answered 200 with `id` 29932 and a create row holding no `project`
  relationship.

- `GET /entity/versions/29932` then answered 404 `Version: 29932 not found`, and a site-wide
  `POST /entity/versions/_search` on its `code` returned 0 rows. `DELETE /entity/versions/29932` answered
  204, so the row exists and only the id from the create response can reach it.

- Validate a batch payload yourself; a 200 is not proof the row is addressable. A link to an id that does not exist is rejected on
  both paths, 400 `Update failed for [Version.entity]: Value is not legal.`

- **Size.** No cap was found. A `requests` array of 5001 was validated in full, answering one
  `data hash containing field/value pairs is required for the given request` per element.

- On the probed site a committing batch of 200 answered in 11.7s, 500 in 31.0s and 1001 in 47.7s on one run and not at
  all on another, where the client gave up at its own 60s read timeout. **All 1001 rows had committed
  anyway.**

- A read timeout tells you nothing about what landed, and there is no request id to ask about,
  so keep a batch inside the response window, around 200 requests, and make each chunk re-runnable by
  reading back on `code` before resending.

- **The contract, one 400 at a time.** Every rejection below names what it wanted.

  | sent | result |
  |---|---|
  | `Content-Type: application/vnd+shotgun.api3_array+json` | 415 `Unsupported Content-Type 'application/vnd+shotgun.api3_array+json'`, `{"content_type": "Content-Type must be one of: 'application/json'."}` |
  | a top-level array | 400 `Invalid JSON body. Expected Hash but received Array.` |
  | `{"entity": "Version"}` | 400 `Request Parameters invalid.` `{"requests": ["requests is missing"]}` |
  | `{"requests": []}` | 200 `{"data": []}` |
  | a request with no `entity` | 400 `{"requests": {"0": {"entity": ["entity is missing"]}}}` |
  | a `create` with no `data` | 400 `{"data": ["data hash containing field/value pairs is required for the given request"]}` |
  | `"request_type": "read"` | 400 `{"requests": {"0": {"request_type": ["request_type must be one of: create, update, delete"]}}}` |
  | `"entity": "versions"`, the URL slug | 400 `Invalid entity type: entity type [] does not exist.` |
  | `delete` with no `record_id`, or with `entity_id` | 404 `Entity of type [Version] with id=0 does not exist.` |

- **`delete` in a batch and the `DELETE` verb do the same thing and report it differently.**

  | | body | after it |
  |---|---|---|
  | batch `delete` | 200 `{"request_type": "delete", "type": "Version", "id": N, "uuid": "...", "did_delete": true}` | `GET` that id 404s |
  | `DELETE /entity/versions/N` | 204, 0 bytes | `GET` that id 404s |

  Deleting an already deleted id inside a batch is 404 `Entity of type [Version] with id=N does not exist.`
  and takes the rest of the batch down with it, so a delete pass is not idempotent.

- Response shape differs by `request_type`: a create row is the thin create subset, an update row is the
  whole record wrapped with `links` and `status`, a delete row is flat (probe 024 for the field-level
  table). `?fields` on `/entity/_batch` is accepted and ignored, as on every other write (probe 024), and
  no row resolves a dotted path, so re-read for those.

`corpus/recipes/002_batch.md`

## 003_query_fields_and_pages

Resolve a query field's value, and run the rows a saved Page shows

### The field is not a shortcut

### The four flavours

### The tree runs nowhere as stored

### Tokens

### Relations whose value is a list

### Reading the page

- `columns` are schema field names in display order and go straight into `?fields`. All six on the
  page above were returned. On the probed site another Shot page lists the pivot columns `step_35` and
  `step_106`, which are real fields in `/schema/Shot/fields` and were returned like any other.

- `id` is a legal column and is not a field. On an EventLogEntry page listing it, `?fields=id,user`
  answered 200 with `attributes: {}` and the id under the row's own `id` key. Drop `id` from the list
  and read `row["id"]`.

- A column absent from `/schema/<Type>/fields` is dropped at 200 with no error (probe 004), so check
  the list against the schema to know which columns you lost (probe 023).

- `sorts` and `grouping` are lists of `{column, direction}`. `?sort` takes one field, so the second
  and later sort keys and the grouping have to be applied client-side.

### The stored project can be a project that is gone

### Once translated, the field is still unusable as a field

### The URL slug

`corpus/recipes/003_query_fields_and_pages.md`

## 004_register_published_file

Register the next PublishedFile without overwriting the last one, and write a path the server resolves for every platform

- **The version query is the whole guard, and it is a read-then-write race.** No field on PublishedFile is
  unique and no combination is enforced, so the identical body posted twice returns two 201s and there is no
  conflict error to catch (`entity_types/PublishedFile`). Two clients that read `next_version` at the same
  moment both publish version 4.

- The API offers nothing to close this: no unique constraint to create, no conditional write, no returned
  row to lose the race against.

- What a client can do is narrow the query to the same context it publishes into (`name` plus `project`, plus `entity` or `task` if the stream is scoped
  to one), re-run it immediately before the create, and treat the answer as advisory.

- Production code pairs it with a filesystem probe of the publish directory and a retry cap because either source alone goes stale;
  that belongs in the client, and the API cannot confirm or deny what the retry found.

- **A caller with no storage root has a second route.** The same field takes the three-call upload,
  which puts the bytes on the site and names no LocalStorage at all
  (`recipes/013_publish_file_bytes`). Everything below still applies to the `local` shape.

- **Each accepted path write mints an Attachment**, on the create and again on every corrective `PUT`. The
  id is inside the `path` object. Nothing removes the previous one, so a publish loop that rewrites paths
  accumulates Attachment rows silently. Delete by `DELETE /entity/attachments/<id>`, which answered 204.

- **Creating a PublishedFileType for an unknown extension adds it to every project on the site.**
  PublishedFileType has no `project` field and no filter narrows it (`entity_types/PublishedFileType`).
  Resolve against the full listing with a case-normalised compare, and create only from an allowlist. The
  create call is shown in step 3 and was not run for this reason.

- The 201 body already holds the resolved `path`, so a publish needs no read-back to log the paths it wrote.
  This is the one place a create returns more than it was sent; `?fields` on a write is still ignored
  (probe 024).

- `path_cache` is null after a REST create even though the path resolved. A filter on `path_cache` misses
  every row published this way (`entity_types/PublishedFile`).

- `sg_status_list` takes a raw code from the field's `valid_values` minus the project's `hidden_values`
  (probe 009, `field_types/status_list`). On the probed site the set is `['wtg', 'ip', 'cmpt']`.

- Reading the path back later: `GET /entity/published_files/<id>?fields=path` returns the `local` shape,
  which has no `url` key, so `value["url"]` raises on exactly the shape a publish writes. Test `link_type`
  first (`field_types/url`, probe 021).

`corpus/recipes/004_register_published_file.md`

## 005_propagate_status

Roll a status up from a parent's Tasks and Versions onto the parent, without racing a concurrent write

- **The trigger is not the rule.** A run started by one Task changing answers "do all siblings satisfy
  the condition now", so the sibling set is re-queried in full and the triggering row's own status is
  used for nothing but the guard in step 4.

- **Two child types are two calls.** `_search` is per entity type, so a rule over Tasks and Versions
  queries `/entity/tasks/_search` and `/entity/versions/_search` with the same `entity` filter. One
  call per child type per parent, not one per row.

- **Many parents in one call.** `["entity", "in", [{"type": "Shot", "id": a}, {"type": "Shot", "id": b}]]`
  is accepted at 200, as is `["entity.Shot.id", "in", [a, b]]`. Ask for `entity` in `fields` and group
  the rows by `relationships.entity.data.id` yourself, then pair that with the batch write in step 5.

- **A sibling can hold a status outside `usable`.** REST does not enforce `hidden_values`
  (`field_types/status_list`), so a code the project hides writes and reads back fine. On the probed
  site `hld` is hidden on Task in this project and `PUT {"sg_status_list": "hld"}` answered 200 and
  read back `hld`.

- The two spellings of the rule then disagree over the same siblings
  `['fin', 'fin', 'hld']`:

  | rule | result | parent |
  |---|---|---|
  | `all(s in done)` | `False` | `ip`, correct |
  | `not any(s in blocking)` | `True` | `fin`, wrong: `blocking` was built from `usable`, which excludes `hld` |

  Build the "every status except these" set from the schema for the operator-facing list, and decide
  with `in done` so an unknown or hidden code blocks instead of passing.

- **`hidden_values` can name codes that are not in `valid_values`.** On the probed site the project
  hides `['blk', 'hld', 'na', 'rdy', 'rev']` on Task while `valid_values` holds no `blk` and no `rdy`;
  `PUT {"sg_status_list": "blk"}` is 400. Subtracting one list from the other is still correct, and
  the difference is not the set of writable codes.

- **Display labels fail two different ways.** `PUT {"sg_status_list": "Final"}` is a 400 that names the
  legal set, and the same string in a filter is a silent 0 rows:

      400 {"status": 400, "code": 104, "source": null, "detail": null, "meta": null,
           "title": "Update failed for [Task.sg_status_list]: 'Final' is not a valid status.
                     Valid statuses: 'wtg', 'ip', 'fin', 'apr', 'dis', 'na', 'hld', 'rev', 'omt', 'ready'."}

  The 400 enumerates site-wide `valid_values`, hidden codes included. Round-trip through
  `display_values` for anything an operator reads and send the code everywhere else.

- **The read-then-write race has no server-side guard.** The step 4 comparison narrows the window; it
  does not close it, and there is no conditional write to close it with:

  | sent on `PUT /entity/tasks/{id}` | result |
  |---|---|
  | `If-Match: "zzstale"` | 200, applied |
  | `If-Unmodified-Since: Mon, 01 Jan 1990 00:00:00 GMT` | 200, applied |
  | `If-None-Match: *` | 200, applied |
  | `updated_at` echoed back in the body | 400 `API update() Task.updated_at is editable on create only.` |

  A `GET` does return a weak `ETag` (`W/"6829a03d..."`), and no verb honours it. Two propagations
  racing over one parent both write; the last one wins, and the loser leaves no trace. Serialise the
  runs per parent on your side if the answer has to be exact.

- **Batch is worth it for the write half only.** The decision is reads, which `_batch` does not do.
  On the probed site two parent updates answered in 474ms as one batch against 857ms as two `PUT`s,
  one failing row rolls the whole call back, and the rows come back in request order. Recipe 002 has
  the contract, the size limits and the rollback matrix.

- A batch update row returns the whole record including the new `sg_status_list`, and it is still not
  the confirmation: `?fields` is ignored on every write (probe 024) and a write can be a 200 no-op
  (probe 028). Step 6 is the confirmation.

`corpus/recipes/005_propagate_status.md`

## 006_media_round_trip

Take media off one Version and put the same bytes on another, which is what every sync, transfer and hand-off does

- **No server-side copy, and no reference to reuse.** The only value `sg_uploaded_movie` accepts is an
  object holding a `url` (`field_types/url`). Wrapping the source's presigned url in
  `{"url": …, "name": …}` answers 200 and stores a `link_type: web` link that dies with the signature,
  with no transcode and no thumbnail. Moving the bytes is the only transfer that survives.

- **The signature expires, and re-reading the field is the fix.** The window is `X-Amz-Expires`
  seconds from `X-Amz-Date`, and the number is not a constant: two reads one second apart returned
  847 and 900.

- Both reads returned different strings for the same Attachment, so a client that
  outlives its url re-reads the field and starts the transfer again rather than retrying the string.
  A string held 706 seconds past expiry 403s `AccessDenied` (`field_types/image`). Persist the
  Attachment id or the Version id; never the url.

- **`HEAD` 403s** with an `application/xml` body. The signature covers `GET` alone, so size and type
  come from the `GET` response or from `GET /entity/attachments/{id}`.

- **Where the extension lives depends on the field.**

  | field | source of the filename |
  |---|---|
  | `sg_uploaded_movie` and the three derived `url` fields | `name`, and `response-content-disposition` agrees with it |
  | `image`, `filmstrip_image` | `response-content-disposition` only: an `image` field is a bare string with no `name` |

  Parse the query parameter in both cases and the same code handles all six. Uploading with the wrong
  extension is accepted, so nothing downstream corrects it.

- **Clearing is per field, and two readings never clear.**

  | after | `sg_uploaded_movie` | `_mp4` | `image`, `filmstrip_image` | `_frame_rate` | `_transcoding_status` |
  |---|---|---|---|---|---|
  | `PUT {"sg_uploaded_movie": null}` | null | old file | old file | `'25.0'` | 1 |
  | `PUT` all six null | null | null | null | `'25.0'` | 1 |
  | the new upload, before the transcode | new file | null | `/images/status/transient/` | `'25.0'` | 0 |
  | the new upload, after the transcode | new file | new file | new file | `'25.0'` | 1 |

  `_frame_rate` and `_transcoding_status` are a `float` and a `number`, not `url` fields, and neither
  `null` nor the upload resets them. Between the clear and the transcode landing they describe a file
  the Version no longer holds, exactly as a replacement does (probe 022). `_frame_rate` reads back as
  a JSON string (`field_types/float`).

- **`sg_uploaded_movie_transcoding_status`** was 0 in flight, 1 after the transcode landed, and 2 for
  a 16x16 png the transcoder refused, which left every derived field null. Treat 1 as "a transcode
  finished", never as "this media is transcoded": 1 was the reading throughout the clear, when the
  Version held no media at all.

- **The target does not end up with the source's rendition set.** Uploading the source's mp4 produced
  a second transcode of an already transcoded file (`<hash3>_<hash>_bunny.mp4`), a thumbnail and a
  filmstrip, and left `sg_uploaded_movie_image` null, which the source had. Compare Versions on the
  file you sent, not on which fields are filled.

- **Attachments accumulate and the clear does not touch them.** One file synced twice left 5
  Attachments on the target: the seed, both uploads and both transcodes. `PUT … null` unlinks nothing;
  `DELETE /entity/attachments/{id}` does, and only the rows you made.

- **The download's `Content-Type` is not the media's.** Reading the round-tripped file back served
  `binary/octet-stream` while the field reads `video/mp4`. Trust the field's `content_type`.

- Wrap the download so the temp file is removed even when the upload raises. A failed sync that keeps
  its scratch file fills the disk of whatever runs the job.

`corpus/recipes/006_media_round_trip.md`

## 007_build_and_reconcile_a_cut

Write a Cut and its CutItems from an edit, read the timeline back, and reconcile a second edit against the Cut already there

- **The four stages exist because a batch cannot use an id it creates** (`recipes/002`). A CutItem
  needs a Cut id, a Shot id and a Version id at once, and a Version needs a Shot id, so the graph is
  four levels deep and each level is its own call. Within a level, batch, and chunk at around 200
  requests.

- **An id alone does not say which Cut a row is on.** `code` repeats across Cuts:
  `[["code", "is", "reel1_sh010"]]` returned items `(46, cut 19)` and `(53, cut 20)`. A blind
  `PUT /entity/cut_items/53` with no `cut` key answered 200, left `cut` at 20, and overwrote that Cut's
  metadata.

- Before updating, confirm the row's Cut: filter on `cut` when reading, or ask for
  `cut.Cut.id` in `fields` and drop every id that does not match. A dotted read through this single
  `entity` field works, unlike one through a multi_entity field (probe 016).

- **Sending `cut` in an update moves the item.** `PUT` with `{"cut": {"type": "Cut", "id": other}}`
  answers 200 and the item leaves its old Cut. So does the other side:
  `PUT /entity/cuts/<a>` with `{"cut_items": {"multi_entity_update_mode": "add", "value": [...]}}`
  answered 200 and left the item's former Cut holding `[]`.

- `CutItem.cut` is single-valued, so an `add` on the parent is a re-parent, not an addition.

- **`Cut.cut_items` is not the running order.** It is returned sorted by the item's display name:
  `['aaa_last', 'sh010', 'sh020', 'sh030', 'sh030_gap', 'sh030_overlap']` against `cut_order`
  `1, 2, 3, 4, 5, 6` on the same six rows.

- Read the items with `POST /entity/cut_items/_search`, `[["cut", "is", {"type": "Cut", "id": N}]]`, `sort: "cut_order"`.
  A `null` `cut_order` sorts last in both directions.

- **No frame rate is reachable from a CutItem.** `Cut.fps` is the only rate on either type, it is
  `null` until someone writes it, and no CutItem field points at the Cut's value. Read `Cut.fps` once
  and pass it down; `float` reads back as a string, so `float()` it (`field_types/float`).

- Drop frame is expressible only inside the `text` fields, which validate nothing, so the client owns
  that flag too.

- **Deleting a Cut does not delete its CutItems.** `DELETE /entity/cuts/<id>` answered 204 and the
  item survived with `cut` `null`, reachable only through
  `[["project", "is", ...], ["cut", "is", None]]`. Delete the items first. A delete inside a batch is
  not idempotent: a second delete of the same id 404s and takes the whole batch with it
  (`recipes/002`).

- **Nothing about a Cut is unique either.** Three Cuts created with the same `code` all answered 201.
  `revision_number` is a plain number the client maintains, and the display name the server builds
  from it is `code` plus ` v%03d`: `reel1 v001`, `reel1 v002`, and bare `reel1` when
  `revision_number` is `null`. "The current cut" is `sort: "-revision_number"` over a `code` filter.

- `Cut.entity` accepts `['Sequence', 'Scene', 'Episode', 'Reel']` and `Cut.version` a `Version`, whose
  reverse `Version.cuts` fills in on the same write.

`corpus/recipes/007_build_and_reconcile_a_cut.md`

## 008_delivery_progress

Keep a Delivery honest about what a long transfer is doing, including when it is cancelled and when it crashes

- Write the pair from a `finally`, not from the success path. An uncaught exception between two progress
  writes leaves a Delivery reading `ip` and a line describing work that stopped an hour ago, and nothing
  in the API times a row out.

- A `200` on the write is not proof of the value. Re-read the row (probe 028); `say()` above returns the
  re-read, not the response to the `PUT`.

- **Always send `entity` on the Reply.** A Reply created without one cannot be deleted:
  `DELETE /entity/replies/<id>` answers 400 code 104
  `undefined method 'reflect_on_association' for class NilClass` (`entity_types/Reply`). A failure
  reporter that drops the link leaves permanent litter on exactly the runs that already went wrong.

- `Reply.entity` names 113 of the 114 types in `/schema`, `Delivery` among them, and `Delivery.replies`
  is one of only two fields anywhere with `valid_types: ['Reply']` (`entity_types/Reply`). A Reply on a
  Delivery is ordinary, and it is readable back both from `Delivery.replies` and from
  `POST /entity/replies/_search` on `[["entity", "is", {"type": "Delivery", "id": N}]]`.

- `Delivery.reply_content` is not the thread. It read
  `'Warning: If you see this displayed in the UI, it means the widget is not respecting grid_column = false.'`
  on a Delivery holding one real Reply. Read `replies`.

- `Reply.cached_display_name` comes back HTML-escaped where `content` does not: a traceback containing
  `"` reads back with `&quot;` in `cached_display_name` and with `"` in `content` and in the `name` of
  the `Delivery.replies` link.

- Writing `""` to `description` stores `null`, so an empty progress line erases the previous one rather
  than blanking it (`field_types/text`). Send a real line every time.

- `sg_delivery_type` has `valid_values: []` on the probed site, so every write to it is
  `400 … 'Final' is not a valid list value. Valid list values: ''.` An empty vocabulary is a field that
  cannot be set, not a free-text field.

- Uploading with no field in the path stores the file as an Attachment on `Delivery.attachments`
  (probes 013, 014). Delete the Attachment rows, not just the link, when a run is rolled back.

`corpus/recipes/008_delivery_progress.md`

## 009_multi_entity_safely

Add to and remove from a multi_entity field without destroying the links you did not mean to touch

- **The removal direction is the dangerous one.** An append that goes wrong loses one link; a removal
  that skips the other-parents check breaks a relationship something else still needs, and a child
  that left one parent is not a child nothing claims.

- Remove from the parent, then ask
  `[[<field>, "is", <child hash>], ["id", "is_not", <parent id>]]` on the parent type, and strip the
  child only on an empty answer.

- On the probed site the same query over an existing project answered
  `200, [332, 4473, ... 4491]` for one Shot, 20 Notes claiming it, 19 once the one it left is
  excluded.

- **Use `is` with one entity hash for that query.** A bare id is
  `400 API read() invalid/missing entity hash: 954`, `is` with a list is `400 'is' 'relation' expects
  a 1-element array`, and `in` means "links any of", which on some fields returns the rows that link
  nothing when a member is unresolvable (`field_types/multi_entity`).

- One `_search` answers for one child; batch it by asking `in [child, child, ...]` and grouping the returned parents yourself.

- **The query-string trap.** `?multi_entity_update_mode=add` and
  `?options[multi_entity_update_modes][<field>]=add` both answer 200 having replaced the whole list.
  The loss is a success response, so the mode is only ever correct in the body
  (`field_types/multi_entity`, probe 028).

- **The lost-update race.** Read-then-PUT is not an append. A bare list replaces, the window between
  the read and the write is open, and no conditional write closes it: `If-Match`,
  `If-Unmodified-Since` and `If-None-Match` are ignored at 200 and `updated_at` echoed back is
  `400 editable on create only` (probe 024). The wrapper is not a narrower window, it is no window.

- **Verify by re-reading.** `?fields` is ignored on every write (probe 024) and a 200 proves nothing
  about a `multi_entity` field, since the query-string form returns one after replacing (probe 028).

- Compare the set you wanted against a fresh `GET /entity/<slug>/<id>?fields=<field>`. A dotted path
  is not a shortcut: `?fields=versions.Version.code` answered 200 with `attributes` and
  `relationships` both empty (probe 016).

- **Order is not stored.** `Playlist.versions` reads back sorted by the target's `code`, whatever
  order was written, and the human order is `sg_sort_order` on the `PlaylistVersionConnection` join
  row, which a write through the field leaves null.

- `remove` then `add` the same member replaces the join row and the order with it, so reorder by writing `sg_sort_order`, never by rewriting the
  member list (`entity_types/Playlist`).

- **Know the field before sending a bare list.** `PUT {"replies": []}` on a Note deletes the Reply
  rows outright, and the ids answer 404 afterwards (`entity_types/Note`). A bare list is a replace on
  most fields and a delete on some, and nothing in the response distinguishes them.

- **A multi_entity field reads back as a list.** Unset is `[]`, never null and never an absent key.

- `relationships.<field>.data` was a list on every read taken here: 100 rows of `Note.note_links` and
  100 of `Version.playlists` and `Version.tasks` from `_search`, 20 of those re-read singly by `GET`,
  and 72 sandbox reads split across 0, 1 and 2 members over `GET`, `_search` under both filter
  Content-Types, and `GET .../relationships/<field>`.

- One implementation reported by the survey defends against the field coming back as a single mapping
  instead; that did not reproduce, so the defensive read below is recorded unverified, on the
  survey's word rather than on a measurement here.

- The one field that does return a mapping is a single `entity` field,
  `{"data": {"id", "name", "type"}}`, which is what a caller reading the wrong field name gets.

      d = row["relationships"][field]["data"] or []
      d = [d] if isinstance(d, dict) else d

`corpus/recipes/009_multi_entity_safely.md`

## 010_status_picker

List the statuses a project actually offers, each with the label, colour and icon needed to draw it

### Two calls, not one per status

### `Icon.url` is empty unless `image_data` is asked for beside it

### The three renderings

### Rediscover the sprite; never hardcode it

### Fall back to `bg_color`

### The picker is not a validator

### The other pieces

- Read the schema per entity type. Codes do not transfer: on the probed site Version has 16 and Task
  10, overlapping on five, and `HumanUser` has `act` and `dis`, which no other type offers.

- `display_values` is a map from code to label and a key can be missing, so fall back to the code
  rather than dropping the option.

- `valid_values` order is the order to show. It is not alphabetical by label, and there is no
  substring operator on a `status_list` field, so a type-ahead filters the list client-side
  (`field_types/status_list`).

- `icon_type` has two values and no more. Over all 98 `Icon` rows on the probed site:
  `permanent_status`/`image_map` 94, `custom_status`/`html` 3, `custom_status`/`image` 1. Page 2 of
  the same listing returned 0 rows, so that census covers the whole table (probe 006).

- Probe 010 left the question open; the answer is site configuration, and a site with more custom statuses will hold
  more `custom_status` rows, not a third `icon_type`.

`corpus/recipes/010_status_picker.md`

## 011_audit_webhook_subscriptions

Inventory every webhook subscription on a site, and see which have ever delivered

- **The listing is the whole site.** A script with API access reads every other integration's consumer
  url, its `entity_types` and its project scoping. Treat the output as sensitive.

- The secret token is never returned. `is_token_set` is the only readable fact about it.

- `num_deliveries: 0` on an `active` hook means it has never delivered in its lifetime, not that it is
  idle. That is the one field that separates a working subscription from a subscription that was
  accepted and never fired, which the create contract cannot tell you (`045_webhooks`).

- A hook may name `entity_types` or `event_type`, never both, so read whichever is populated
  (`050_webhook_subscriptions`).

- `status` is one of `active`, `unstable`, `failed` or `disabled`. Only `disabled` is set by a caller;
  the other three are the site's own assessment of the endpoint's health.

`corpus/recipes/011_audit_webhook_subscriptions.md`

## 012_sign_in_as_a_person

Reach the REST API as a person, with no script key and no password, by having them approve a login in their browser

- `user` is a `HumanUser`, so every row this bearer writes has the person as `created_by` and, on a
  Version, as `user`, which the web UI shows as Artist. A script key gets the same result only through
  `sudo_as_login`, and that needs an administrator to grant `can_impersonate_this_user` per person
  (`027_auth_permissions`). This needs nobody.

- The person's permission level applies, not a script's. Rows collapse to what they may see
  (`027_auth_permissions`); on the probed site the approver was in the `Admin` set and saw everything.

- `expires_in` is 600, the same as a script token, and `grant_type=refresh_token` on the returned
  `refresh_token` answers 200 with another 600. Re-minting from the session token costs the same one
  call and needs no refresh bookkeeping.

- The session token is the credential to keep, not the bearer. How long the site keeps it alive is the
  site's `User Session Expiry` preference (`052_app_session_launcher`), and is not returned anywhere.

- `machineId` is not checked when polling, so it is a label for the person, not a binding.

`corpus/recipes/012_sign_in_as_a_person.md`

## 013_publish_file_bytes

Publish a file's bytes onto a PublishedFile when the caller has no LocalStorage root to write under

- **The url is not the file.** It is minted per read and signed for 900 seconds, so persist
  `path["id"]`, the Attachment, and re-read the field when the bytes are wanted
  (`field_types/url`). Two reads of the same unchanged row return two different strings.

- **`local_path_mac` is absent, not null.** A reader doing `(path or {}).get("local_path_mac")`
  returns `None` for every row published this way and reports it as a row with no path. Branch on
  `link_type` first: an `upload` or `web` value has `url`, a `local` value has the three platform
  paths and no `url` (`field_types/url`).

- **Deleting the PublishedFile leaves the Attachment.** `DELETE /entity/published_files/<id>` answered
  204 and `GET /entity/attachments/<id>` still answered 200 with the filename. The bytes stay on the
  site until the Attachment is deleted by id, which is the same accumulation a `local` path write
  causes on every rewrite (`recipes/004_register_published_file`).

- `file_size` on that Attachment reads `null` even after the bytes landed, so it distinguishes nothing
  (`endpoints/put_links_upload`).

- Step three answers 201 whether or not step two ever ran, and its body is a single space rather than
  JSON (`endpoints/post_links_complete_upload`). Fetch the url to prove the bytes exist.

- **A `file://` url is a third shape, and it moves nothing.** `{"url": "file:///…", "name": …}` on the
  same field answers 201 on create and 200 on a `PUT`, at `link_type` `web`, and stores the string
  only: no bytes reach the site and any reader without that mount sees a dead link. A space in the url
  is refused, so percent-encode before sending (`field_types/url`).

- The three-call flow needs no LocalStorage row to exist on the site at all, and no
  `published_file_type`. What it costs is that the file is one object: a sequence has to be archived
  first, and the archive is what a consumer downloads.

`corpus/recipes/013_publish_file_bytes.md`

## 014_notes_about

Find the Notes about a Shot, Asset or Version by the name of the thing, and read what each Note is linked to

- `cached_display_name` resolves for every one of the 28 `valid_types`. `code` is 400 on `Booking`
  and `name` on every type but `Department`, with the same `doesn't exist.` string for a wrong type
  and a wrong field.

- `?fields=note_links.Shot.code` answers 200 with the key absent from `attributes` (probe 016). The
  links are readable only through `note_links` itself, as `{id, name, type}` triples.

- `["note_links", "contains", NAME]` without a type is 400 `'multi_entity' data type doesn't support
  'contains' 'relation'`. There is no search across all types in one filter by name; resolve ids first
  and use `["note_links", "in", [{"type": ..., "id": ...}, ...]]`.

- A Note about a Task is in `tasks`, not `note_links`. Search it on `tasks.Task.content`.

- Two hops resolve: `note_links.Shot.sg_sequence.Sequence.code` narrows to a sequence.

`corpus/recipes/014_notes_about.md`
