# NOTES

## Output

Final run, 2026-09-03T02:41:45Z to 02:41:49Z, verbatim:

```
$ python weekly_report.py 1180
complete_upload -> 201, body ' ', no id in it; reading the Attachment back
total: 23
attached Attachment 2213 to Note 10943 ('Client review round 3', 2026-09-03T02:31:04Z)
api calls: 9
```

The first line is on stderr. `report.csv` is 24 lines: a header and 23 rows.

Nine calls: auth, two Version pages (the second empty), the Note read, the Attachment `_search` taken
before the upload, `_upload` init, the presigned `PUT`, `complete_upload`, and the `_search` taken after.

## What I got wrong

**1. I prefixed `/api/v1` twice and read the 404 as the wrong thing.**

`links.complete_upload` comes back as `/api/v1/entity/notes/10943/_upload`, already carrying the prefix.
My client added `self.base` to every path, so the request went to `<site>/api/v1/api/v1/entity/notes/...`.

```
POST /api/v1/entity/notes/10943/_upload -> 404
{"errors":[{"id":"4e55e2a24d3384d63725bd2258ae56aa","status":404,"code":103,
  "title":"Not Found","source":null,"detail":null,"meta":null}]}
```

That body says nothing. `source` is null and `detail` is null, and my first reading of it was that a Note
is not a valid upload target. What settled it was posting an empty body to the same path with a single
prefix:

| POST with `{}` | result |
|---|---|
| `/entity/notes/10943/_upload` | 400 `upload_info is missing`, `upload_data is missing` |
| `/entity/notes/10943/attachments/_upload` | 400, the same |
| `/entity/notes/10943/this_file/_upload` | 400, the same |

The route was alive under every field name, so the 404 was the URL and not the entity. The corpus records
the three-call dance (findings 013, 014, recipe 001) but never that the returned link is absolute against
the site rather than against the API root.

**2. I assumed the completion names the row it made. It returns 201 with a one-byte body.**

```
requests.exceptions.JSONDecodeError: Expecting value: line 1 column 2 (char 1)
```

The body is `' '`, a single space. The write had already succeeded, so the crash left Attachment 2210
linked to Note 10943 with nothing reporting it. Findings 013 and 014 both record the 201 and neither
records what is in it; recipe 001 ignores the response entirely, which is why the recipe works and my
copy of it did not.

The fix is to read the Attachment back. `attachment_links` is a `multi_entity` field, so a flat
`filter[]` 400s and only a `_search` body can hold the `{type, id}` hash (finding 014).

**3. My first read-back picked a row I did not create.**

I added a guard that reused an existing `report.csv` on the Note instead of uploading a second one, and
took `max(id)` of the matches. It printed Attachment **2211**, which is not mine:

```
2210 report.csv 2026-09-03T02:36:24Z by <fpt_api_script_name> 1.0 298   <- my crashed run
2211 report.csv 2026-09-03T02:39:05Z by <fpt_api_script_name> 1.0 298   <- not mine
2212 report.csv 2026-09-03T02:40:57Z by <fpt_api_script_name> 1.0 298   <- not mine
2213 report.csv 2026-09-03T02:41:48Z by <fpt_api_script_name> 1.0 298   <- mine
```

Something else is writing `report.csv` to the same Note with the same credentials. `created_by` is the
same `ApiUser` on all four rows, and nothing on an Attachment is unique (`entity_types/Attachment`), so
no field distinguishes them. What told me was arithmetic: my run made 5 API calls, none of them an
upload, and 2211 predated it.

`attach()` now snapshots the Note's attachment ids before the upload and names the id that appeared. It
is still racy inside that window, and I have no way to close it: the API offers no handle on the row
between `_upload` and the read-back.

## Litter

Attachment **2210** is mine, orphaned by the crash in item 2. `DELETE /entity/attachments/2210` was
refused by the sandbox, and the brief says to delete nothing, so it stands. Two rows on that Note are
mine rather than one. The id the script reports, and the answer to the brief, is **2213**.

## What the corpus caught before I could get it wrong

| | |
|---|---|
| `links.next` is present on empty pages forever (006) | paging stops on an empty `data`, not a missing `next` |
| entity fields are returned under `relationships` (003, 004) | `created_by` and `entity` read as absent from `attributes` alone |
| `Version.entity` is polymorphic (005) | 19 of 23 link a Shot, 1 links an Asset, 3 link nothing |
| `_search` and `_summarize` need the vendor Content-Type (004) | `application/json` 415s there |
| `sg_uploaded_movie` is a `url` field (`field_types/url`) | an object, not a string, and a `local` value has no `url` key |
| `Note.attachments` is `multi_entity`, `Note.replies` destroys rows (`entity_types/Note`) | the script never `PUT`s the Note |
| `upload_data` must be sent even though it is empty (013) | |
| a sort on an unsortable field is a silent 200 (026) | I checked `created_at,id` reverses under `-` before trusting it |

The polymorphism one is the difference between a correct report and a plausible one. The `entity` link
returns `name` for free, and for a Shot that name is the code, so reading `relationships.entity.data.name`
looks right on 19 rows and quietly writes the Asset code `sbx_charA` into the shot column on the twentieth.
The script asks for `entity.Shot.code`, which is null on a row linking an Asset (`field_types/entity`), and
gates it on `entity.data.type == "Shot"`.

## Unsure

- **The movie column is a link that dies.** `sg_uploaded_movie.url` is presigned with `X-Amz-Expires=900`
  and re-minted on every read (`field_types/url`). The client has 15 minutes from the run. Two runs of
  this script also produce byte-different CSVs for identical data, which I confirmed by hashing: 31909
  bytes on one run and 31953 on the next. The field returns nothing more durable, so that is what I
  shipped. A permanent link would need the site's own Attachment URL, which the REST API does not return.
- **"Most recent Note" is `created_at` descending, `-id` as tiebreak.** Note 10943 is newest on both keys
  here, so nothing rides on the choice, but a Note edited after a newer one was created would sort
  differently under `updated_at`. The brief does not say which.
- **The shot column is empty on 4 of 23 rows.** Three Versions link nothing and one links the Asset
  `sbx_charA`. The brief asks for the code of the Shot, so I did not put an Asset code there. A client
  wanting "whatever it hangs off" would want a different column.
- **23 is the whole set.** `POST /entity/versions/_summarize` with `{"field": "id", "type": "count"}`
  returned `{"summaries": {"id": 23}}`, which agrees with the paged walk, so nothing was lost to paging.
- **The no-field `_upload` path is the one finding 014 verified.** On this Note,
  `/entity/notes/10943/attachments/_upload` returns an identical init block with `upload_type` `Attachment`,
  so the two are probably the same thing. I did not complete an upload through the second one, because that
  would have created a row I have no way to remove.
