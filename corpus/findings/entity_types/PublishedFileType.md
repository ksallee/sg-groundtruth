---
tags: [entity-type, published-file, enumeration, schema, filter, create, trap]
scope: api
measured: site-wide plus the first sample project; read only
summary: The kind of a published file, named once for the whole site.
verdict: PublishedFileType is site-wide with no project field, so a publish that creates one on an unknown extension adds it to every project; `code` is the identity and the only unique field.
---

# PublishedFileType

**Type** Schema name `PublishedFileType`, REST path slug `published_file_types`. Site-wide: 14 fields,
none of them `project`, and no project scope on the endpoint. Every project on the site reads the same
rows, and one project's publish of an unrecognised extension is visible in all of them.

| path | result |
|---|---|
| `GET /entity/published_file_types` | 200 |
| `GET /entity/published_file_type`, `GET /entity/PublishedFileType` | 200, the same rows; `links.self` normalises to `/api/v1/entity/published_file_types/<id>` |
| `GET /entity/publishedfiletypes`, `GET /entity/publish_file_types` | 404 `Entity type 'publishedfiletypes' does not exist.` |

| project scope attempted | result |
|---|---|
| `_search` `[["project", "is", {"type": "Project", "id": N}]]` | 400 code 103 `API read() PublishedFileType.project doesn't exist.` |
| `GET ?filter[project]=N` | 400, same title, `source` `{"PublishedFileType.project": " does not exist. ..."}` |
| `GET ?project_id=N` | 200, accepted and ignored: the same row count as the unscoped call |

Which types one project actually uses is a question about its PublishedFiles, not about this endpoint:

```
POST /entity/published_files/_search   Content-Type: application/vnd+shotgun.api3_array+json
{"filters": [["project", "is", {"type": "Project", "id": N}]],
 "fields": ["code", "published_file_type.PublishedFileType.code"]}
 -> {"code": "charA.v003.ma", "published_file_type.PublishedFileType.code": "<type>"}
```

**Identity** `code`, display name `Published File Type Name`. It is the only field the schema marks
`unique: true`, and the only one it marks `mandatory`. `short_name` and `description` are free text and
optional; on the probed site both are `null` on every row, and `cached_display_name` is `null` too, so
display `code`. PublishedFileType has no `name` and no `content` field.

| field | data type | editable | mandatory | unique |
|---|---|---|---|---|
| `code` | text | yes | yes | yes |
| `short_name`, `description`, `cached_display_name` | text | yes | no | no |
| `sg_status_list` | status_list | yes | no | no |
| `tags` | multi_entity `['Tag']` | yes | no | no |
| `created_at`, `created_by`, `id`, `image_blur_hash`, `image_source_entity`, `updated_at`, `updated_by` | | no | no | no |

A create-if-missing publish looks the type up by `code`, and `text` matching is case-insensitive
(`field_types/text`): a filter for a code in upper case returned the row stored in mixed case. Compare the
case yourself before deciding a type is absent, or the same type is created twice under two spellings.

**Create** Not attempted. A row made here appears in every project on the site, and `DELETE` retires
rather than removes it. What the schema declares, unverified against the server, which requires a
different set on every type measured so far (probe 012):

| field | schema |
|---|---|
| `code` | `mandatory: true`, `unique: true` |
| every other editable field | `mandatory: false` |

Whether the uniqueness constraint is case-sensitive is unmeasured for the same reason. A publish tool
should read the full listing once, match on a normalised `code`, and create only on a miss.

**Links** One field in the 114 types of `/schema` names `PublishedFileType` specifically. There is no
reverse field on PublishedFileType, so the direction is PublishedFile to type, one type per file. 51
further fields (`image_source_entity` and the like) list it among 100+ `valid_types`; those are generic
any-entity links, not type links (`field_types/entity`).

| field | data type | editable | `valid_types` |
|---|---|---|---|
| `PublishedFile.published_file_type` | entity | yes | `['PublishedFileType']` |

`published_file_type` is optional on a PublishedFile: on the probed site 6 of 183 published files have
none.

| filter on `/entity/published_files` | result |
|---|---|
| `["published_file_type", "is", {"type": "PublishedFileType", "id": N}]` | the files of that type |
| `["published_file_type.PublishedFileType.code", "is", "<type>"]` | the same rows, without the id lookup |
| `["published_file_type", "is", N]` | 400 `API summarize() PublishedFile.published_file_type expected [Hash, ... NilClass] data type(s) but got Integer: 1` |
| `["published_file_type", "is", null]` | the files with no type |

**Status** `sg_status_list`, a `status_list`, `default_value` `"wtg"`. On the probed site `valid_values` is
`['wtg', 'ip', 'cmpt']` and `hidden_values` is empty at both site and project scope, and every row is
`wtg`. The codes are site configuration, not part of the type: read them from
`GET /schema/PublishedFileType/fields/sg_status_list` and subtract `hidden_values` yourself (probe 009,
`field_types/status_list`).

**Traps**
- The scope is the site. A publish that creates the type on an unknown extension pollutes every project,
  and no filter narrows this endpoint. Gate creation behind an allowlist, or resolve to an existing row.
- `?project_id=N` returns 200 and changes nothing. A client that reads it as scoping will report every
  type on the site as belonging to whichever project it asked about.
- Matching by `code` is case-insensitive on read. Two rows differing only in case are two types to the
  API and one to a filter.
- `PublishedFile.published_file_type` takes a `{type, id}` hash; a bare id is 400. Filter by the dotted
  path `published_file_type.PublishedFileType.code` when the id is not already in hand.
