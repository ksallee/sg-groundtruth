# NOTES

This arm has no credentials and no site. `NO-ENV.txt` says so. Nothing here has been run against
Flow Production Tracking, so the brief's "it has to run, and you show the output" rule is not met and
cannot be. Everything below is recall or guess, labelled as one or the other.

The only thing I actually executed: `write_csv` and the record-shaping helpers, against a synthetic
payload I made up, plus the two argument/`.env` error paths. That proves the CSV columns and the
`Asset`-not-`Shot` and missing-`created_by` cases, and proves nothing about the API.

## Disclosure

I was told to read nothing under `sg-groundtruth/` except this directory, and I did not. But the
harness injected the repo's `CLAUDE.md` into my context before I started, and one line of it is an
API fact: `links.next` never absent. That is not my own knowledge and I should not launder it as
such. I did not use it as a terminator anyway (see pagination below), so it changed one comment, not
the logic. Flagging it because a cold-recall measurement is worthless if I quietly keep a leaked fact.

## What I know

Confident, recalled rather than reconstructed:

| | |
|---|---|
| REST v1 lives at `<site>/api/v1` | |
| `POST /api/v1/auth/access_token`, form-encoded, `grant_type=client_credentials`, `client_id` = script name, `client_secret` = API key | response carries `access_token`, `token_type`, `expires_in`, `refresh_token`; `Authorization: Bearer <token>` afterwards |
| The envelope is JSON:API-shaped | top-level `data`, each record `{type, id, attributes, relationships, links}`, and a top-level `links` |
| Scalar fields are returned under `attributes`, entity links under `relationships` | |
| `page[size]` and `page[number]` are the pagination parameters | |
| `sort=created_at` ascending, `sort=-created_at` descending | |
| The Version fields are `code`, `sg_status_list`, `entity`, `created_by`, `created_at`, `sg_uploaded_movie` | these are the stock schema names, not guesses; a site can hide or rename the display name but the API name stands |
| `entity` on a Version can point at an Asset, not only a Shot | so the `shot` column is left empty for those rather than filled with an asset code |

## What I am guessing

Ordered by how much damage the guess does.

### 1. The upload handshake — low confidence, the whole three-step shape

What I wrote: `GET /api/v1/entity/notes/{id}/attachments/_upload?filename=report.csv` returns
`links.upload` (a presigned storage URL) and `links.complete_upload` (a site-absolute path), plus a
`data` object; PUT the bytes to `links.upload` with no `Authorization` and no `Content-Type`; then
POST `{"upload_info": <the data object>, "upload_data": {}}` to `links.complete_upload`.

I am moderately confident there are three steps and that a presigned PUT is in the middle. I am
guessing:

| guess | confidence |
|---|---|
| the path segment is `attachments` for a file linked to the record rather than to a named field | medium |
| the query parameter is `filename` | medium |
| the link keys are `upload` and `complete_upload` | low |
| the completion body keys are `upload_info` and `upload_data` | low |
| the PUT must carry no `Content-Type` (a signed content type that does not match gets a 403 from storage) | low, and it may be the opposite: the signature may *require* one |

First thing I would check: do the handshake by hand with curl against a scratch Note and print the
raw JSON of step 1. That one response settles every row above at once.

### 2. Getting the new Attachment's id back — low confidence

I do not believe `complete_upload` reliably returns the created Attachment, so the script reads it
back: search Attachments filtered on `attachment_links is {Note, id}` and `filename is report.csv`,
newest first. Guesses stacked in there: that `attachment_links` is the field name (medium), that
`filename` holds the basename rather than a path (medium), and that Attachment is queryable through
`_search` at all rather than being a special-cased type (low). If the readback fails the script
raises instead of printing a wrong id, which is the behaviour I want, but it means the last line of
the brief is the least likely line to print.

### 3. Filter syntax on GET — medium confidence

`filter[project.Project.id]=1180`. I recall the dotted `field.EntityType.field` form for reaching
through a link, and I recall simple `filter[code]=x`. I am much less sure the two compose that way
on a GET. The script falls back to `POST /entity/versions/_search` on a 400 or 404, which I trust
more, so this guess degrades rather than fails. First check: `GET /api/v1/entity/versions?filter[project.Project.id]=1180&page[size]=1`.

### 4. `_search` content type — medium confidence

`application/vnd+shotgun.api3_array+json` for array-style filters, with a hash-style sibling for the
`{logical_operator, conditions}` form. I am fairly sure a custom content type is required and that
plain `application/json` is rejected, because the server cannot otherwise tell the two filter
grammars apart. I am less sure of the exact vendor string, and the product rename makes `shotgun` in
that literal look wrong even though I think it is still correct. Guessing outright that `page` and
`sort` go in the `_search` body rather than the query string.

### 5. Entity type in the path — medium confidence, and it is a single point of failure

I used lowercase plural throughout: `entity/versions`, `entity/shots`, `entity/notes`,
`entity/attachments`. My memory of the docs' example URLs is plural lowercase, and I half-remember
the server normalising `Version`, `version` and `versions` to the same thing. If that normalisation
is not real and the correct form is CamelCase singular, every request in the script 404s. I chose
one form deliberately instead of mixing, so a fix is one constant, not a scatter.

### 6. Whether a relationship carries `name` — medium confidence

I read `relationships.entity.data.name` for the Shot code and `relationships.created_by.data.name`
for the user. Strict JSON:API would give only `type` and `id`. I think Flow PT adds the display name,
but the script does not bet on it for the Shot: if `name` is absent it batch-fetches `code` for those
ids. It does bet on it for `created_by`, and if that is wrong the column comes out empty rather than
wrong, which I judged acceptable. Note also that a Shot's display name is its `code`, so `name` and
`code` should agree; if a site has changed which field is the display name for Shot, the two paths
disagree silently.

### 7. Where `sg_uploaded_movie` is returned — genuine coin flip

It is a file/url field holding an Attachment. It could be an `attributes` hash or a `relationships`
entry. The script reads both, so this one is covered rather than guessed away.

### 8. The movie link itself — a judgment call, not a recall

The `url` the API returns for an upload is, I believe, a short-lived presigned storage URL. Putting
that in a CSV a client opens on Tuesday gives them a dead link. So the script builds
`<site>/file_serve/attachment/<id>` instead, which I am fairly confident is the durable form and
which requires the reader to be logged in. If `/file_serve/attachment/` is wrong the column is
uniformly broken and obviously so. If the brief wanted the raw returned URL, this is a wrong reading
of "a link to the Version's uploaded movie" rather than a wrong API call.

### 9. Smaller guesses

| guess | confidence |
|---|---|
| `page[size]` max is 500 | low; if it is lower the server may 400 rather than clamp |
| 429 with `Retry-After` is how throttling is expressed | low; I have no specific memory of rate limiting here |
| the token is good for ~600s and `expires_in` is seconds | medium; the script refreshes a minute early and also retries once on a 401 |
| retired entities are excluded by default | medium; if not, deleted Versions inflate `total:` |
| `subject` is a Note field | medium, and it does not matter, only `id` is used |

## What I expect to break first

The upload. Step 1 of the handshake is where I have the least real memory and the most invented key
names, and it is also the step that has to succeed before the last two lines of the brief can happen.
Second most likely: `filter[project.Project.id]` on the GET, which has a fallback. Third: the
lowercase-plural path segment, which does not, and which fails loudly on the very first call.

The report half of the job I would expect to survive with small corrections. The attach half I would
expect to need a real handshake response in front of me before it works.

## What told me

Nothing told me. There was no site, no docs, no search, and no corpus. The only feedback in this run
came from Python itself: a syntax check, the two `.env` and argument error paths, and one synthetic
payload through `write_csv`. Every API-shaped statement in `weekly_report.py` is unverified.
