---
tags: [version, silent, playlist]
scope: api
measured: first sample project read, sandbox project written
summary: An ordered set of Versions to review together.
verdict: Playlist.versions reads back sorted by the Version's code, never in the order written; the human order is sg_sort_order on PlaylistVersionConnection, which a write through the field leaves null.
---

# Playlist

**Type** Schema name `Playlist`, addressed at `/api/v1/entity/playlists`. The slug is neither case nor
plural sensitive, and only an unknown name is refused.

```
GET /entity/playlists  -> 200      GET /entity/Playlist   -> 200
GET /entity/playlist   -> 200      GET /entity/playlistss -> 404 "Entity type 'playlistss' does not exist."
```

Project-scoped. `Playlist.project` is an editable `entity` field, `valid_types: ["Project"]`, and it stays
editable after create: a `PUT` moving a playlist to another project returned 200. An unfiltered `_search`
returns playlists from every project on the site, so send the project filter on every read:

```
{"filters": [["project", "is", {"type": "Project", "id": <pid>}]], "fields": ["code"]}
```

**Identity** `code`, display name `Playlist Name`, `data_type: text`. It is the only field flagged
`mandatory`, and no Playlist field is flagged `unique`. Two playlists created in one project with the same
`code` both returned 201. `cached_display_name` mirrors `code`.

**Create** `POST /entity/playlists`, `Content-Type: application/json`. The schema's `mandatory` flags are
not the create contract (probe 012), and Playlist inverts them exactly as Asset, Shot and Version do: the
flagged field is optional, the unflagged `project` is required.

| body sent | result |
|---|---|
| `{}` | 400 `API create() missing 'project' attribute: {}` |
| `{"code": "review_a"}` | 400 `API create() missing 'project' attribute: {"code" => "review_a"}` |
| `{"project": {"type": "Project", "id": N}}` | 201, `code` auto-filled `"New Playlist 16"` |
| `{"project": {...}, "code": "review_a"}` | 201, `code` as sent |
| the same `{project, code}` a second time | 201, a second playlist with the same `code` |
| `{"project": {...}, "code": ..., "versions": [{type,id}, ...]}` | 201, linked, read back re-sorted |

The 201 echoes `code`, `cached_display_name`, `created_at`, `updated_at`, `external_share_count: 0`,
`open_notes_count: 0` and `media_center_viewed_by_current_user: "unread"`.

**Order** A playlist is an ordered thing to a human and `Playlist.versions` is not ordered at all. Three
versions coded so that `code` order reverses `id` order, written three ways:

```
A id 26443 code zzprobe_pl_v_ccc   B id 26444 ..._bbb   C id 26445 ..._aaa
PUT versions [A, B, C] -> 200  reads back C B A        POST with versions [C, B, A] -> 201, reads C B A
PUT versions [C, B, A] -> 200  reads back C B A        add [A] to [C, B]           -> 200, reads C B A
PUT versions [B, A, C] -> 200  reads back C B A
```

Every read is ascending by the target Version's `code`, from `GET /entity/playlists/{id}?fields=versions`
and from `_search` alike. The order sent is not stored and not readable.

The order a review tool shows is `sg_sort_order`, a `number` on the join row
`PlaylistVersionConnection`, addressed by schema name or by snake-case plural.

```
GET /entity/PlaylistVersionConnection    -> 200    fields: cached_display_name, id, playlist,
GET /entity/playlist_version_connections -> 200            sg_sort_order, version, version_review_message
GET /entity/playlistversionconnections   -> 404 "Entity type 'playlistversionconnections' does not exist."
```

| action | join row | `sg_sort_order` |
|---|---|---|
| link through `Playlist.versions` | created | `null` |
| `PUT sg_sort_order` on the join row | unchanged | as sent |
| bare-list `PUT versions` over the same members | unchanged | unchanged |
| `remove` then `add` the same Version | replaced, new id | back to `null` |
| `POST` `{playlist, version, sg_sort_order}` | 201 | as sent |
| `POST` a second row for the same pair | 400 `Create failed for [PlaylistVersionConnection]: Validation failed: There is already a connection between the entities.` | |

Order a playlist by writing `sg_sort_order` on each join row; read it back with `_search` on
`PlaylistVersionConnection`, filtered `[["playlist", "is", {...}]]`, `"sort": ["sg_sort_order"]`.

**Links** Written and read as `field_types/entity` and `field_types/multi_entity` describe. `versions` is
the type: a bare list replaces the whole review, and only the body form of
`{"multi_entity_update_mode": "add", "value": [...]}` appends. Verified on this field, from `[A]`:

| sent as `versions` | result |
|---|---|
| bare `[B]` | 200, `[B]`. `A` is gone |
| `{"multi_entity_update_mode": "add", "value": [C]}` | 200, both |
| the same `add [C]` again | 200, deduped |
| `{"multi_entity_update_mode": "remove", "value": [C]}` | 200, `C` unlinked |
| `?multi_entity_update_mode=add` in the query string | 200, list replaced |

| field | type | valid_types | editable |
|---|---|---|---|
| `project` | entity | `['Project']` | yes |
| `versions` | multi_entity | `['Version']` | yes |
| `notes` | multi_entity | `['Note']` | yes |
| `open_notes` | multi_entity | `['Note']` | no |
| `tags` | multi_entity | `['Tag']` | yes |
| `created_by`, `updated_by`, `locked_by` | entity | `['HumanUser', 'ApiUser']` | no |
| `image_source_entity` | entity | every entity type on the site | no |

`Version.playlists` is the same relation from the other end, `multi_entity`, `valid_types: ['Playlist']`,
editable. An `add` written there was returned by `Playlist.versions` immediately. Write either side.

A playlist is not confined to its project: adding a Version belonging to another project returned 200 and
the Version was returned in `versions`. `project` places the playlist, not its contents.

**Status** None. `GET /schema/Playlist/fields/sg_status_list` returns 404 `Field
'Playlist.sg_status_list' does not exist.` The one `list` field is
`media_center_viewed_by_current_user`, `valid_values: ['read', 'unread']`,
`default_value: None`, per-viewer state rather than a workflow status.

**Traps**
- A playlist read back is not the playlist a reviewer sees. Sorting by `code` puts `sh010_v10` ahead of
  `sh010_v9` and interleaves shots; take the order from `PlaylistVersionConnection.sg_sort_order`.
- Appending with a bare list drops every other Version at 200. The query-string spellings of the update
  mode do the same (`field_types/multi_entity`). Send the mode in the body.
- Unlinking a Version destroys its `sg_sort_order`: re-adding it makes a new join row with `null`. Reorder
  by writing `sg_sort_order`, never by rewriting the member list.
- The stock read-only fields are `created_at`, `created_by`, `external_share_count`, `id`,
  `image_blur_hash`, `image_source_entity`, `locked_at`, `locked_by`,
  `media_center_viewed_by_current_user_at`, `open_notes`, `open_notes_count`, `updated_at`, `updated_by`.
  They 400 with two different messages: `API update() Playlist.id is read only.` and
  `API update() Playlist.created_at is editable on create only.`
