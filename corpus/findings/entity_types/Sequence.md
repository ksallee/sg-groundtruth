---
tags: [entity-type, sequence, shot, write, create, entity-field, multi-entity, status, dotted-field, trap]
scope: api
verdict: A Sequence needs `project`, not `code`, and project alone names it `New Sequence <id>`; `shots` is the reverse of `Shot.sg_sequence`, one link, so a Shot sits in exactly one Sequence.
---

# Sequence

**Type** `Sequence`, addressed as `/entity/sequences`. Project-scoped: every row holds a `project` link,
and an unfiltered listing spans projects, so filter by `project` before counting anything.

| path | result |
|---|---|
| `GET /entity/sequences` | 200 |
| `GET /entity/sequence` | 200, the same rows |
| `GET /entity/Sequence`, `GET /entity/Sequences` | 200, the same rows |
| `GET /entity/sequencies` | 404 `Entity type 'sequencies' does not exist.` |
| `GET /entity/seqs` | 404 `Entity type 'seqs' does not exist.` |

Naive and English pluralisation agree here, case is ignored, and a wrong stem 404s quoting it back.

**Identity** `code`, display name `Sequence Name`. There is no `name`, `content` or `title` field.
`unique` is `false` in the schema and nothing enforces it: two Sequences with the same `code` in the same
project both created at 201, and `["code", "is", <that value>]` then returned both. Only `id` identifies
a row. `cached_display_name` holds a copy of `code` and follows a rename.

**Create** `POST /entity/sequences`, `Content-Type: application/json`. The requirement is `project`;
`code` is the field the schema flags `mandatory: true`, and it is optional (probe 012).

| body sent | result |
|---|---|
| `{}` | 400 `API create() missing 'project' attribute: {}` |
| `{"code": "seq01"}` | 400 `API create() missing 'project' attribute: {"code" => "seq01"}` |
| `{"project": {"type": "Project", "id": N}}` | 201, `code` set by the server to `New Sequence <id>` |
| `{"code": "seq01", "project": {"type": "Project", "id": N}}` | 201 |
| `{"code": null, "project": {…}}` | 400 `Create failed for [Sequence]: Cannot set identifier field to empty. (Sequence)` |
| `{"code": "", "project": {…}}` | 400, the same message |
| `{"code": "seq01", "project": N}` bare int | 400 `API create() Sequence.project expected [Hash,\n ActiveSupport::HashWithIndifferentAccess,\n ActionDispatch::Http::Parameters,\n ActionDispatch::Http::ParamsHashWithIndifferentAccess,\n NilClass] data type(s) but got Integer: N` |

The 201 echoes 6 attributes and 17 relationships against the 16 and 21 a read-back returns, so re-read
the row. Server-set on create: `code` when omitted, `sg_status_list` `"ip"`, `cached_display_name`,
`created_at`, `updated_at`, `open_notes_count` `0`. On the probed site 10 of the 38 fields are not
editable, and sent anyway they split into two messages; the other three are `image_source_entity`,
`open_notes` and `updated_by`.

| field | `PUT` |
|---|---|
| `id`, `open_notes_count`, `image_blur_hash`, `step_0` | 400 `API update() Sequence.<field> is read only.` |
| `created_at`, `updated_at`, `created_by` | 400 `API update() Sequence.<field> is editable on create only.` |

**Links** On the probed site 21 of Sequence's 38 fields are `entity` or `multi_entity`. The hierarchy
ones, with the field on the other type that answers them:

| on Sequence | data_type | valid_types | the other end |
|---|---|---|---|
| `shots` | multi_entity | `['Shot']` | `Shot.sg_sequence`, entity, `['Sequence']` |
| `episode` | entity | `['Episode']` | `Episode.sequences`, multi_entity, `['Sequence']` |
| `sg_scenes`, `sg_sequence_scenes` | multi_entity | `['Scene']` | `Scene.sg_sequence`, entity; `Scene.sequence_sg_sequence_scenes_sequences`, multi_entity |
| `assets` | multi_entity | `['Asset']` | `Asset.sequences`, multi_entity |
| `cuts` | multi_entity | `['Cut']` | `Cut.entity`, entity, `['Sequence','Scene','Episode','Reel']` |
| `tasks` | multi_entity | `['Task']` | `Task.entity`, entity, 8 types |
| `sg_versions` | multi_entity | `['Version']` | `Version.entity`, entity, 15 types |
| `sg_published_files` | multi_entity | `['PublishedFile']` | `PublishedFile.entity`, entity, 8 types |

The other twelve: `project`, `task_template`, `sg_sequence_vendor` (`['Group']`), `notes`,
`addressings_cc`, `sg_slates`, `sg_vendor_groups`, `tags`, and the four not editable.

Each pair is one link, not two. Writing either end updates the other:

| write | read back |
|---|---|
| `PUT Shot.sg_sequence = {"type": "Sequence", "id": S}` | `Sequence.shots` holds that Shot |
| `PUT Shot.sg_sequence = null` | `Sequence.shots` is `[]` |
| `PUT Sequence.shots` `add [{"type": "Shot", "id": H}]` | `Shot.sg_sequence` holds that Sequence |
| add the same Shot to a second Sequence | 200; `Shot.sg_sequence` is the second, the first's `shots` is `[]` |
| `PUT Sequence.episode = {"type": "Episode", "id": E}` | `Episode.sequences` holds that Sequence |
| `PUT Episode.sequences` `add [{"type": "Sequence", "id": S}]` | `Sequence.episode` holds that Episode |
| `PUT Sequence.episode = {"type": "Sequence", "id": X}` | 400 `Update failed for [Sequence.episode]: Episode expected, got Sequence` |

Read the hierarchy from the Shot. `?fields=code,shots.Shot.code` returns 200 with the dotted key absent,
while `sg_sequence.Sequence.code` on a Shot reads back `"seq01"` (`field_types/multi_entity`, probe 016).
Both paths filter: `shots.Shot.code is 'sh010'` matched 1 Sequence, `sg_sequence is {Sequence, S}` matched
its 3 Shots. `valid_types` binds on `episode`, which is not the rule for entity fields
(`field_types/entity`). `sg_timecode` is the only `timecode` field on the site (`field_types/timecode`).

On the probed site all 15 Sequences of the sample project link `shots` and `assets`, all 300 of its Shots
set `sg_sequence`, and `episode`, `sg_scenes`, `cuts`, `sg_versions` and `tasks` are empty on all 15. The
site holds 0 Episodes and 1 Scene, so Sequence is the top of the hierarchy there.

**Status** `sg_status_list`, a `status_list` (`field_types/status_list`). `default_value` `"ip"`,
`valid_values` `['wtg', 'ip', 'fin']`, `hidden_values` `[]` both site-wide and with `project_id`
(probe 009). `display_values` `{"wtg": "Waiting to Start", "ip": "In Progress", "fin": "Final"}`. `null`
writes at 200 and reads back `null`; an unknown code 400s and names the vocabulary:
`Update failed for [Sequence.sg_status_list]: 'ZZZ' is not a valid status. Valid statuses: 'wtg', 'ip', 'fin'.`
On the probed site the sample project's 15 Sequences hold `fin` 6, `ip` 6, `wtg` 3.

**Traps**
- `code` looks mandatory and is not, and `project` looks optional and is not. `{"project": …}` alone
  returns 201 with `code` set to `New Sequence <id>`, so a client that omits `code` on a retry does not
  fail, it litters. `{"code": …}` alone 400s with `missing 'project' attribute`.
- A Shot belongs to exactly one Sequence. Adding a Shot already linked elsewhere to `Sequence.shots`
  returns 200 and silently empties the first Sequence's `shots`; there is no reparenting error.
- `code` is not unique and no filter makes it so. Two rows in one project answered to the same `code`.
  `cached_display_name` accepts a `PUT` at 200 and stores nothing: it re-reads as `code`.
- `DELETE /entity/sequences/<id>` returns 204 and the row leaves both `GET` and `_search`, but it is a
  retire: `POST /entity/sequences/<id>?revive=true` returns 200 and the id is live again. Without the
  query parameter that same `POST` is 400 `Request Parameters invalid.` with `source: {"revive": ["revive is missing"]}`.
