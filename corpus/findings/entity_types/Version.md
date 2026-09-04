---
tags: [media, link, version]
scope: api
measured: first sample project read, sandbox project written
summary: A reviewable piece of media, usually hanging off a Shot or an Asset.
verdict: The schema inverts the create contract: `project` is required and `code` is not, generated as "New Version <id>" when omitted. `code` is not unique, so key on `id`.
---

# Version

**Type** Schema name `Version`, REST slug `versions`, project-scoped: every row holds a `project`
entity link and a create without one is refused.

The slug is matched case- and plural-insensitively. `/entity/versions`, `/entity/version`,
`/entity/Version` and `/entity/Versions` each answered 200 with the same row, `data[0].type` `Version`
in all four. An unknown type 404s:

```
GET /entity/vershion -> 404
 title:  "Not Found"
 detail: "Entity type 'vershion' does not exist."
```

Project scoping is a filter, not a path segment. `POST /entity/versions/_search` with `filters: []`
returns rows from every project at once (500 rows spanning 3 projects on the probed site). Narrow with
`filter[project.Project.id]=<id>` on a `GET`, or `["project", "is", {"type": "Project", "id": N}]`.

**Identity** `code`, data_type `text`, `unique: false`. There is no `name`, `content` or `title` field.
`cached_display_name` is the server's copy of `code`, not a second name, and is discarded on write
(probe 004). Two Versions in one project with the same `code` both create at 201, so `id` is the only
identifier a client may key on.

**Create**

| body | result |
|---|---|
| `{"code": "sh010_v001"}` | 400 `API create() missing 'project' attribute: {"code" => "sh010_v001"}` |
| `{"project": {"type": "Project", "id": N}}` | 201, `code` generated as `"New Version <id>"` |
| both | 201 |
| the same `code` a second time in the same project | 201, a second row |
| `"entity": <bare id>` instead of `{type, id}` | 400 (probe 012) |

`/schema/Version/fields` marks `code` mandatory and `project` not, and the server does the opposite of
both. The 201 also fills `created_at`, `updated_at`, `cached_display_name`, `open_notes_count` 0, four
checkboxes at `false`, and `sg_status_list` at the field's `default_value`.

**Links**

| field | data_type | `valid_types` |
|---|---|---|
| `project` | entity | `Project`. Required on create |
| `entity` | entity | `Asset`, `Level`, `MocapTake`, `Reel`, `ShootDay`, `Shot`, `Sequence`, `Delivery`, `Launch`, `Camera`, `Slate`, `SourceClip`, plus the site's enabled CustomEntity slots (probe 008) |
| `sg_task` | entity | `Task` |
| `user` | entity | `HumanUser`, `ApiUser`, `Group` |
| `client_approved_by` | entity | `HumanUser`, `ClientUser` |
| `source_clip` | entity | `SourceClip` |
| `task_template` | entity | `TaskTemplate` |
| `created_by`, `updated_by` | entity | `HumanUser`, `ApiUser`. Not editable |
| `image_source_entity` | entity | every entity type the site exposes. Not editable |
| `tasks` | multi_entity | `Task` |
| `notes`, `open_notes` | multi_entity | `Note`. `open_notes` is not editable |
| `playlists` | multi_entity | `Playlist` |
| `published_files` | multi_entity | `PublishedFile` |
| `cuts` | multi_entity | `Cut` |
| `tags` | multi_entity | `Tag` |

Which of `entity` and `sg_task` a site populates is a measurement, not API behaviour: on the probed
site probe 005 found `entity` set on 100 of 100 Versions and `sg_task` on 1. Run that measurement
before coding against either. An `sg_` prefix does not mark a field as custom, so read
`/schema/Version/fields` on the target site rather than sorting by name: the probed site adds three
further multi_entity link fields that are its own configuration. Write shapes and dotted reads:
`field_types/entity`, `field_types/multi_entity`.

**Status** `sg_status_list`, data_type `status_list`, with a `default_value` applied on create. A
project's usable set is `valid_values` minus `hidden_values`, read with `project_id` (probe 009); both
lists are site configuration. Write and filter: `field_types/status_list`.

**Media** Four tiers, one per row. Probe 021 covers which resolves and in what order.

| field | data_type | holds | go to |
|---|---|---|---|
| `image`, `filmstrip_image` | image | a plain presigned URL string, or a `/images/status/transient/` placeholder while transcoding | `field_types/image`, probe 013 |
| `sg_uploaded_movie` | url | an object: `url`, `name`, `content_type`, `link_type`, `type`, `id`. Single-valued | `field_types/url`, probe 022 |
| `sg_uploaded_movie_mp4`, `_webm`, `_image` | url | server transcodes of whatever was uploaded last | probe 022 |
| `sg_uploaded_movie_frame_rate`, `_transcoding_status` | float, number | the last transcode, not the current media | probe 022 |
| `sg_path_to_movie`, `sg_path_to_frames` | text | one absolute path, free text, no padding convention | probe 021 |
| `published_files` | multi_entity | `PublishedFile`, whose `path` returns mac, windows and linux paths already joined | probe 021 |
| `image_blur_hash` | text, not editable | never filled by a REST upload | `field_types/image` |

**Traps**
- The schema's `mandatory` and `editable` flags are not the contract. `project` is required and unflagged,
  `code` is flagged and generated, and `image` reads `editable: true` while refusing every write
  (`field_types/image`).
- The 201 `relationships` block lists all 20 link slots, including ones never set, so its keys are not a
  record of the input (probe 012). Read the row back to confirm a link.
- Not editable on the probed site: `id`, `created_at`, `created_by`, `updated_at`, `updated_by`,
  `image_blur_hash`, `image_source_entity`, `open_notes`, `open_notes_count`, `otio_playable`,
  `viewed_by_current_user_at`, and one `pivot_column` (`field_types/pivot_column`).
- There is no `attachments` field. A file uploaded with no field in the path is found through
  `Attachment.attachment_links`, never from the Version (probe 014).
