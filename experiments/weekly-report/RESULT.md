# Result

Graded against `SCORECARD.md`, written before any arm ran. Every row below was measured by the grader
against the live site, not taken from an agent's report.

## The three artifacts

| | `cold` | `live` | `corpus` |
|---|---|---|---|
| Had | its own knowledge | site plus public docs | site plus the corpus |
| Ran the script | grader ran it afterwards | yes | yes |
| Wall clock | about 4 min, writing only | about 30 min | about 15 min, most of it reading |
| API calls, whole session | 0 | about 55 | not separately counted |
| API calls, final script run | 10 | 11 | 9 |
| `report.csv` rows | 23 | 23 | 23 |
| Rows disagreeing with the API | **0** | **0** | **0** |
| Sorted oldest first | yes | yes | yes |
| `total:` printed | 23, correct | 23, correct | 23, correct |
| Attachment has real bytes | yes, md5 verified | yes | yes |

All three produced a correct CSV and a real attachment on the right Note.

## The traps

| # | trap | `cold` | `live` | `corpus` |
|---|---|---|---|---|
| 1 | `links.next` never absent | pass, short-page stop | pass, does not trust it | pass, stops on empty |
| 2 | silent no-op sort | pass | pass | pass |
| 3 | entity link under `relationships` | pass | pass | pass |
| 4 | dotted path returned flat | avoided, no dotted path | avoided | pass, uses `entity.Shot.code` |
| 5 | presigned URL expires | **pass**, `/file_serve/` | **pass**, `/file_serve/` | **FAIL**, 22 rows carry `X-Amz-Expires=900` |
| 6 | `_search` vs `_summarize` | inert on this project | inert | inert |
| 7 | upload lands on the wrong field | pass | pass | pass |
| 8 | reading the attachment back | pass | pass | pass |

Trap 5 is the only one that separated the arms, and it separated them against the corpus.

`field_types/url` records that the value is "presigned on `s3-accelerate.amazonaws.com`, re-minted on
every read". The `corpus` arm read that, wrote it into its own notes as "the client has 15 minutes", and
shipped the expiring link anyway. Having the fact is not using it. Both other arms reasoned their way to
the stable `/file_serve/attachment/<id>` route unaided, `cold` with no source at all.

## What the task actually turned up

Three silent failures, none of them in the corpus, all found by the arms that were experimenting rather
than reading:

| found by | |
|---|---|
| `live` | `complete_upload` with valid `upload_info` and empty `upload_data`, and no S3 PUT at all, returns **201** and creates a real Attachment row over an S3 key that was never written. `file_size` reads `None` for an empty attachment and for a good one, so it cannot be used to tell them apart |
| `corpus` | `complete_upload` returns 201 with a body of a single space. Not JSON, and it never names the row it created. Parsing it crashes *after* the write has landed |
| `corpus` | `links.complete_upload` comes back already prefixed with `/api/v1`. A client that prefixes again gets `404` with `source: null`, which reads as "a Note is not a valid upload target" rather than "your URL is wrong" |
| `live` | `options[retired_only]=true` is accepted at 200 and silently ignored. The real spelling is `options[return_only]=retired` |

The first is the sharpest thing this experiment produced. It is an empty file that looks in every way
like a delivered one, on a client's note, with a 201 behind it.

## Two wrong beliefs nothing corrected

| arm | |
|---|---|
| `live` | wrote `PAGE = 500` with a comment asserting the API caps a page at 500. It believed that from nothing. `page[size]=1000` returns 1000 |
| `cold` | its whole three-call upload handshake was recalled, not checked. It happened to be right, which is luck it could not have known it had |

## Method faults, all mine

**`CLAUDE.md` was auto-injected into all three agents**, because the session spawning them had this
repository as its working directory. That file states one real API fact, that `links.next` is never
absent, which is trap 1. All three disclosed the injection unprompted. **Trap 1 is void for every arm**
and should not be counted. A clean run must be launched from a different directory.

**The three arms shared one project and ran concurrently.** Four `report.csv` attachments landed on Note
10943 seconds apart under the same script user. The `corpus` arm's own guard, which reused "the newest
`report.csv`", picked up **2211**, a row belonging to `live`. It caught this and switched to snapshotting
the Note's attachment ids before uploading. Nothing on an Attachment distinguishes one writer from
another. Serial runs, or a project each.

**Version rows changed under the runs.** An early ground-truth read counted 20 entity links and 22
movies; a later one counted fewer. Row counts in this file are the ones measured at grading time.

## Litter

Attachment **2210** is the `corpus` arm's, orphaned when its first run crashed on the single-space
`complete_upload` body after the write had landed. `DELETE /entity/attachments/2210` was refused by
sandbox policy.

## Conclusion

On this task the corpus bought fewer API calls and nothing else. It did not buy correctness: it was the
only arm to ship a defective column, and the defect was one it had the fact to prevent.

The stronger result is `cold`. A model with no site, no documentation and no corpus wrote a 465-line
script that ran first time and produced a byte-correct CSV and a valid upload. Whatever this corpus is
for, it is not for teaching a model the shape of this API.

What it plausibly remains for is the four silent failures above, none of which any arm knew in advance
and three of which are still unrecorded. That is a claim about a corpus that has been fed by
experiments like this one, and it is not the claim the landing page currently makes.
