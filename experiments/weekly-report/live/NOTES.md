# NOTES

Starting knowledge: none of this site, and only the public REST API docs at
developers.shotgridsoftware.com. Everything below was found by calling the live site.

## Run output

    $ python weekly_report.py 1180
    wrote ~/dev/sg-groundtruth/experiments/weekly-report/live/report.csv
    total: 23
    attached Attachment 2211 to Note 10943 ('Client review round 3')

23 data rows plus a header. Attachment **2211** on **Note 10943**. Verified by downloading it
back: 3394 bytes, byte-identical to the local `report.csv`.

## Things that were wrong and nothing told me

These are the dangerous ones. Every one of them returns a success status.

**`complete_upload` creates an Attachment even when nothing was uploaded.**
While probing the request shape I sent the completion POST with a valid `upload_info` and an
empty `upload_data`, having never PUT a single byte to the signed S3 URL. Response:

    201

Attachment **2209** now existed on Note 10943, named `probe.csv`, linked to the note, pointing
at an S3 key that had never been written. Nothing in the response said the file was empty. A
client opening the note would see an attachment and get nothing. I deleted 2209; it was mine
and seconds old. The script now checks the PUT's own status code, because the confirm step
will not do it for you.

**`file_size` does not distinguish the two cases.** My first instinct was to use it as the
check. It reads `None` on attachment 2211, which uploaded correctly and downloads 3394 bytes,
exactly as it read `None` on the empty 2209. It is not a signal.

**`links.next` is present on every page, including pages past the end.** Asking for
`page[number]=2` of a 23-record result returns `data: []` and a `links.next` pointing at page 3.
`while response["links"]["next"]` is an infinite loop that no error will interrupt. The only
stop condition is a short page.

**Unknown `options[...]` keys are accepted and ignored.** I guessed `options[retired_only]=true`
and got `200` with the same 23 rows as no option at all. I read that as "there are no retired
Versions". There are: `options[return_only]=retired` returns at least 1000 in project 1180.
`options[nonsense]=zzz` also returns 200. A typo in an option name is silent.

Nothing about the default query announces that 1000+ retired Versions are being hidden. The
default is right for a client report, and `total: 23` is the right number, but I only know that
because I went looking. Had the brief wanted every Version ever made, I would have shipped 23
and never known.

**`fields=` silently drops names it does not recognise.** `fields=code,name` on a Shot returns
only `code`, with a 200 and no warning. A misspelled field just is not in the response.

**I invented a 500-record page cap.** I wrote `PAGE = 500` with a comment asserting the API caps
a page at 500 "regardless of what page[size] asks for". I believed that from nothing. Testing
it: `page[size]=1000` returns 1000 records. I corrected the comment after the run; the change is
comment text only, and I re-ran the read path afterwards and confirmed it reproduces `report.csv`
exactly.

**`sg_uploaded_movie.url` expires in 900 seconds.** The API hands you a working, correct-looking
presigned S3 URL. `X-Amz-Expires=900` is buried in the query string. Put it in a CSV a client
opens on Monday and every link is dead; the failure surfaces days later, as AWS XML, to the
client. I used `https://<site>/file_serve/attachment/<id>` instead, which is stable and
permission-checked (it 302s to the login page when unauthenticated, so the route is real).

## Things the API did tell me

**`filter[project]=1180` → 400.** Clear message:

    API read() Version.project expected [Hash, ...] data type(s) but got String: "1180"

`filter[project.Project.id]=1180` works.

**The documented upload path is wrong.** The docs describe
`/entity/{entity}/{id}/fields/{field}/_upload`. That is a 404 here. The working paths are
`/api/v1/entity/notes/{id}/attachments/_upload` (field-scoped) and
`/api/v1/entity/notes/{id}/_upload` (record-scoped). Both 200.

**`complete_upload` enumerates its own contract.** POSTing `{}` returns 400 naming
`upload_info` and `upload_data`; POSTing `{"upload_info": {}}` returns 400 naming every key
inside `upload_info`. `upload_info` is the step-1 `data` object verbatim; `upload_data` can be
`{}`.

## Judgment calls, any of which could be wrong

**`status` holds the display label, not the code.** The field value is `rev`; the site's schema
calls that "Pending Review". This is a report a client reads, so I resolved the codes through
`/api/v1/schema/Version/fields/sg_status_list?project_id=1180`. If the column was meant to carry
the raw stored value, this is wrong. Both are one line apart in the code.

**Every Version, not just the last week.** The brief says "one row per Version in that project"
and also calls the thing a weekly report. I took the sentence over the title. There is no date
filter in the script.

**One Version links to an Asset, not a Shot.** `sbx_charA_turntable_v001` links to Asset 10033.
The column is named `shot`, so I left it empty rather than putting an Asset code in it. Three
more Versions link to nothing and are also empty. Twelve values would change if this call is
wrong.

**Shot codes are dereferenced, not read off the link stub.** The `entity` relationship returns
`{"id": 7514, "name": "sbx_0020", "type": "Shot"}` and that `name` happens to equal the Shot's
`code`. I did not want to rely on the stub's `name` being the `code` field, so the script fetches
the Shots. One extra call for the whole report.

**"Most recent Note" is unambiguous here, and might not be elsewhere.** Project 1180 has exactly
three Notes, created one second apart, and 10943 is newest by both `created_at` and `updated_at`.
I sorted on `created_at` descending with `id` as the tiebreak. If a project's newest note by
creation is not its newest by activity, this picks the former.

**I attached to the Note's `attachments` field.** `/api/v1/entity/notes/{id}/_upload` also
returns 200 and would presumably produce a record-level attachment. I did not test which one the
Flow Production Tracking web UI shows in the note body, because testing it means creating a
second attachment I would then have to delete.

## Other observations

**A concurrent run touched the same note.** Attachment **2210**, `report.csv`, appeared on Note
10943 at `02:36:24`, two seconds after my accidental 2209 and under the same API script user. It
is not mine. I left it alone. Note 10943 now carries 2210 and 2211.

**Boundary.** I was told to read nothing under `~/dev/sg-groundtruth/` outside this
directory. I did not. However, before my first action, the session prompt already contained the
full text of `~/dev/fpt-llm-api/CLAUDE.md`, auto-injected. That file describes this
same corpus project and states among other things that `links.next` is never absent. I did not
open it and could not decline it. I rediscovered the `links.next` behaviour by paging past the
end of a real result, and every other finding above came from a request I made, but the prior
exposure is real and I am recording it rather than pretending it did not happen.

**Cost.** About 55 API calls across the whole session; the script itself makes 10 calls to Flow
Production Tracking plus one PUT to S3, and runs in 3.0 seconds. Roughly 30 minutes of work,
most of it spent on the upload handshake.
