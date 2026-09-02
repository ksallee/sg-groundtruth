---
tags: [field-type, url, media, upload, attachment, version, filter, operator, write, trap]
scope: api
summary: A link to a file or a web address, returned as an object rather than a string.
verdict: A url field supports no filter relation at all and sort on it is accepted and ignored, so "which Versions have media" can only be answered by paging rows and testing the value.
---

# url

**Data type** `url`, probed on `Version.sg_uploaded_movie` and its three derived fields
`sg_uploaded_movie_mp4`, `_webm`, `_image` (stock, all four editable). Schema properties are
`default_value`, `open_in_new_window`, `summary_default`; no `valid_values`, no format hint.
`Version.image` is data_type `image`, not `url`. The plain string probe 021 read back is that field;
the object is this type.

**Read** A JSON object under `attributes` whose keys depend on `link_type`. `relationships` stays empty.
On the probed site there are 20 `url` fields on 9 of 114 entity types. Reading all 20 returned three
shapes and no fourth, from the 10 that held a value on any row:

| shape | keys | seen on |
|---|---|---|
| `link_type` `upload` or `web` | `url`, `name`, `content_type`, `link_type`, `type`, `id` | `Attachment.this_file`, `PipelineConfiguration.uploaded_config`, `Project.billboard`, `PublishedFile.path` and `.sg_uploaded_file`, `Version.sg_uploaded_movie` and its derived fields |
| `link_type` `local` | `content_type`, `link_type`, `name`, `local_storage`, `relative_path`, `local_path_linux`, `local_path_mac`, `local_path_windows`, `type`, `id`, and no `url` | `Attachment.this_file`, `FilesystemLocation.path`, `PublishedFile.path` |
| a bare string, not an object | n/a | `Project.landing_page_url`, 22 of 22 rows, a site-relative path |

One field mixes them: `Attachment.this_file` returned `upload` on 148 rows, `web` on 19 and `local` on 33.
The six keys of the `upload` shape, on the probed Version:

| key | value | |
|---|---|---|
| `url` | `<media-url>` | presigned on `s3-accelerate.amazonaws.com`, re-minted on every read |
| `name` | `bunny.jpg` | |
| `content_type` | `image/jpeg` | `null` when the object was assigned directly |
| `link_type` | `upload` | `upload` from the three-call upload flow (probe 013), `web` from an assigned object |
| `type` | `Attachment` | |
| `id` | `1430` | the Attachment id; persist this, not the url |

The signed query holds `X-Amz-Expires`, `X-Amz-Signature` and `X-Amz-Security-Token`, and two reads of
the same row return two different strings. Re-read for a fresh link; `GET /entity/attachments/{id}`
gives `filename`, `file_size` and `this_file`.

A dotted read, `?fields=sg_uploaded_movie.Attachment.url`, answers 200 with the key silently absent,
the same hole as a multi_entity dotted read (probe 016). Ask for the field, not a path through it.

**Write** The only accepted input is an object holding `url`.

| sent to `sg_uploaded_movie` | result |
| --- | --- |
| `"https://example.com/plate.mov"` | 400 `API update() Version.sg_uploaded_movie expected [Hash, ActiveSupport::HashWithIndifferentAccess, ActionDispatch::Http::Parameters, ActionDispatch::Http::ParamsHashWithIndifferentAccess, NilClass] data type(s) but got String:` and the value echoed |
| `"/mnt/projects/demo_show/plate.mov"` | 400, same message, the path echoed |
| `"plate.mov"` | 400, same message, the filename echoed |
| the same string in a `POST /entity/versions` body | 400, the same list under `API create()` |
| `{"type": "Attachment", "id": 1}` | 400 `API update() invalid/missing url hash string 'url': {"type" => "Attachment", "id" => 1}` |
| `{}` | 400 `API update() invalid/missing url hash string 'url': {}` |
| `{"url": …, "name": "plate.mov"}` | 200, `link_type` `web`, `content_type` null, a new Attachment id |
| the same object plus `type` and `id` | 200, both ignored, a new Attachment id |
| the same object into `sg_uploaded_movie_mp4` | 200 |

The url is read back exactly as sent and each accepted write mints an Attachment row, so a direct
object publishes a link the review player will open without putting bytes on the site, with no
transcode and no thumbnail. The derived fields take the same object, so a client can assert a
transcode that was never made.

**Clear**

| `PUT {"sg_uploaded_movie": …}` | result |
| --- | --- |
| `null` | 200, field reads null |
| `""` | 400 `API update() Version.sg_uploaded_movie expected [Hash, … NilClass] data type(s) but got String: …` |
| `{}` | 400 `API update() invalid/missing url hash string 'url': {}` |

Read immediately after the field went null, on two Versions whose uploads had finished transcoding:

| field | after the clear |
| --- | --- |
| `sg_uploaded_movie` | null |
| `sg_uploaded_movie_mp4`, `sg_uploaded_movie_image` | still set |
| `image`, `filmstrip_image` | still set |
| `sg_uploaded_movie_frame_rate` | `25.0` |
| `sg_uploaded_movie_transcoding_status` | `1` |
| Attachments still linked to the Version | 7 |

Each derived field is its own `url` field and has to be nulled by name. `_transcoding_status` is a
number and stays at 1, the same stale reading a replacement leaves behind (probe 022).

**Filter** No relation exists, on the field or on any derived field.

| filter | result |
| --- | --- |
| `is`, `is_not`, `contains`, `not_contains`, `starts_with`, `ends_with`, `in`, `not_in`, with `null`, `""` or a url string | 400 `… 'url' data type cannot be used in a filter.` |
| `definitely_not_an_operator` | 400, the same message, and no `Valid relations:` list |
| `sg_uploaded_movie.Attachment.url is_not null` | 400 `API read() Version.sg_uploaded_movie.Attachment.url doesn't exist.` |

```
["sg_uploaded_movie", "definitely_not_an_operator", null] -> 400
 title:  "API read() Version.sg_uploaded_movie's 'url' data type cannot be used in a filter."
 source: {"Version.sg_uploaded_movie": " data type cannot be used in a filter. Value:
          {"path" => "sg_uploaded_movie", "relation" => "definitely_not_an_operator",
           "values" => [nil]}"}
```

There is no legal relation to list, so this is the one type where the bogus-operator trick (probe 017)
returns nothing to build a filter editor from. `sort` answers 200 and is ignored, so the field is
invisible to the query API in both directions:

| sort | result |
| --- | --- |
| `["sg_uploaded_movie"]` | 200, 100 rows, same order as unsorted |
| `["-sg_uploaded_movie"]` | 200, 100 rows, identical to asc |
| `["code"]`, the control | reorders the same rows |
| `[{"field": "sg_uploaded_movie", "direction": "asc"}]` | 400 `{"sort": ["sort array is not valid"]}` |

**Traps**
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
