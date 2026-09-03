# Scorecard

Written before any arm ran. The brief mentions none of this: it asks for a CSV, a total and an
attachment, in the words a producer would use.

Eight traps, all documented in the corpus, all reachable from that one paragraph. Seven of the eight
return HTTP 200 when you get them wrong.

| # | asked for | trap | wrong answer looks like | corpus |
|---|---|---|---|---|
| 1 | "one row per Version" | `links.next` is emitted on every page forever, zero-row pages included | the loop never ends, or it stops at page 1 and the CSV is short | `findings/006_pagination` |
| 2 | "sort oldest first" | an unknown or unsortable sort key is a silent 200 no-op, where the same name in a filter is a 400 | rows come back id-ascending and look sorted | `findings/026_result_order` |
| 3 | "the Shot the Version is linked to" | an entity field is returned under `relationships`, not `attributes`. A row read from `attributes` alone has no link | the `shot` column is empty on every row | `findings/003_query` |
| 4 | same, if solved with a dotted `?fields` path | a dotted path comes back flat under the literal key `"entity.Shot.code"`, not nested | `KeyError`, or an empty column | `findings/003_query` |
| 5 | "a link to the uploaded movie" | `sg_uploaded_movie` is a `url` field; the URL it returns is presigned and expires | the CSV ships dead links, and they work when you test them | `field_types/url`, `findings/013_upload_media` |
| 6 | "print the total" | `_search` and `_summarize` count different populations: `include_archived_projects` defaults false on one, true on the other | a total that disagrees with the row count in the file it just wrote | not in the corpus, found twice by agents |
| 7 | "attach report.csv to the Note" | leave the field out of the `_upload` path and the file is stored as an Attachment on `attachment_links` rather than on the field | 200, an id comes back, the file is not where you think | `findings/014_attach_file` |
| 8 | "print the id of what you attached" | reading that attachment back needs `POST /entity/attachments/_search`; a flat `filter[]` on it is ignored | 200 with every attachment on the site, or zero | `findings/014_attach_file` |

Only trap 1 announces itself, by hanging. The other seven produce a file that looks correct.

## The three arms

| arm | has |
|---|---|
| `corpus` | the corpus, and a live Flow PT site |
| `live` | a live Flow PT site, the public REST documentation, and the web. No corpus |
| `cold` | its own knowledge. No corpus, no site, no web. It writes the script and cannot run it |

`cold` is the control for the other two: it separates what a model already knows about this API from what
either source taught it. It cannot satisfy "it has to run", and is graded on the code alone against the
same eight rows.

## Grading

Each trap is pass or fail, judged from the artifact and from an independent re-run, never from the
agent's own report. Run 1 of the filter-editor experiment was scored from self-reports and the score was
wrong.

Two checks are done by the grader, not the agent:

| check | how |
|---|---|
| Is the CSV complete and correct | count the project's Versions independently, and spot-check three rows for `shot` and `movie` against the API |
| Did the attachment land where the brief implies | read the Note back and see whether the file is on the field or on `attachment_links` |

Record for each arm: wall clock, API calls, which traps were hit, and for each one whether anything told
the agent it was wrong.

## Why this task rather than the filter editor

Two runs on a filter editor tied. Filters are the loud half of this API: a bad operator is a 400 that
prints the legal set, so a wrong belief costs one request and corrects itself. Nothing was being
measured.

Seven of the eight rows above return 200. That is the claim the corpus actually makes, and this is the
smallest task that reaches it. One script, one afternoon's work, not an application.

## The outcome that says the corpus is not worth it

If `live` hits all eight, the corpus saves API calls and nothing else on this task, and the landing page
should say so. If `cold` hits all eight, the corpus is documenting what models already know, and the
whole repository needs rethinking. Both are real possibilities and both get published.
