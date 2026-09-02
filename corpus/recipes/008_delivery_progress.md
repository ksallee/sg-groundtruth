---
intent: Keep a Delivery honest about what a long transfer is doing, including when it is cancelled and when it crashes
tags: [write, delivery, status, list-field, reply, upload, attachment, version, error-handling, trap, recipe]
scope: api
measured: sandbox project; Delivery holds 0 rows site-wide, so every row was created here
---

# 008_delivery_progress

A transfer runs for minutes or hours with nobody watching it. The Delivery row is the only thing a
producer can read while it runs, so a client writes to it as it goes, and writes to it again on the way
out of a crash.

On the probed site `Delivery` holds zero rows site-wide, so everything below was measured against rows
this recipe created in the sandbox and deleted. There is no `entity_types/Delivery`
card yet; what the type does is recorded here.

## The fields a transfer writes

`Delivery` has 32 fields. These are the ones a progress reporter touches.

| field | display name | data type | editable | holds |
|---|---|---|---|---|
| `sg_status_list` | `Status` | status_list | yes | the short code |
| `sg_delivery_progress` | `Delivery Progress` | list | yes | the stage, with cancelled and failed distinct |
| `description` | `Description` | text | yes | the free-text progress line |
| `sg_contents` | `Contents` | text | yes | what is being sent, not how far it got |
| `title` | `Title` | text | yes | server-generated `New Delivery <id>` when omitted |
| `delivery_number` | `Delivery #` | text | no | server-assigned, the id as a string, and not reused after a delete |
| `sg_versions` | `Version <-> Link` | multi_entity | yes | `valid_types: ['Version']` |
| `version_sg_deliveries_versions` | `Versions` | multi_entity | yes | `valid_types: ['Version']`, a second, independent link |
| `sg_published_files` | `Published File <-> Link` | multi_entity | yes | `valid_types: ['PublishedFile']` |
| `attachments` | `Attachments` | multi_entity | yes | `valid_types: ['Attachment']`, filled by the upload dance |
| `replies` | `Replies` | multi_entity | yes | `valid_types: ['Reply']` |
| `sg_delivery_method` | `Delivery Method` | list | yes | site configuration; on the probed site `['FTP', 'Aspera', 'FedEx', 'Sneaker Net']` |
| `sg_upload_url` | `Upload URL` | url | yes | where the far end fetches from |

**Two Version links, not one.** `sg_versions` and `version_sg_deliveries_versions` both take Versions and
neither mirrors the other. Writing one leaves the other empty:

```
PUT sg_versions                     200  {"sg_versions": [<vid>], "version_sg_deliveries_versions": [], "sg_published_files": []}
PUT version_sg_deliveries_versions  200  {"sg_versions": [<vid>], "version_sg_deliveries_versions": [<vid>], "sg_published_files": []}
PUT sg_versions=[]                  200  {"sg_versions": [],      "version_sg_deliveries_versions": [<vid>], "sg_published_files": []}
```

Pick one and write both if the site's pages read both. A bare list replaces the whole set;
`{"multi_entity_update_mode": "add", "value": [...]}` appends (`field_types/multi_entity`).

## The two vocabularies

Read them; the codes below are one site's. `valid_values` was byte-identical at site scope and at
sandbox-project scope for both fields, and `hidden_values` was `[]` on `sg_status_list` and `null` on
`sg_delivery_progress` (probe 009). `hidden_values` is not a subset of `valid_values`, so subtract, never
assume (`field_types/status_list`).

| field | `valid_values` on the probed site | `default_value` |
|---|---|---|
| `sg_status_list` | `['opn', 'ip', 'dlvr', 'recd']` | `opn` |
| `sg_delivery_progress` | `['In transit', 'Delivery cancelled', 'Delivery failed', 'Delivered', 'Ingesting', 'Ingest cancelled', 'Ingest failed', 'Ingest suspended', 'Received', 'Received with warnings', 'Transcode cancelled']` | `null` |

```python
p = get("/schema/Delivery/fields/sg_status_list",
        params={"project_id": PROJECT_ID}).json()["data"]["properties"]
valid  = (p.get("valid_values")  or {}).get("value") or []
hidden = (p.get("hidden_values") or {}).get("value") or []
usable = [v for v in valid if v not in hidden]
```

## Create

`project` is the only required attribute. Everything else the server invents or leaves null.

| body sent | result |
|---|---|
| `{}` | 400 code 103 `API create() missing 'project' attribute: {}` |
| `{"project": {"type": "Project", "id": N}}` | 201, id 21, `title` `"New Delivery 21"`, `delivery_number` `"21"`, `sg_status_list` `"opn"`, `sg_delivery_progress` `null` |
| `{"project": …, "title": "…"}` | 201, the title as sent |

## Call

```python
import traceback

import requests

# get/post/put are FPT.get/.post/.put from src/sg_groundtruth/client.py; they add auth and the /api/v1 prefix.
# The caller supplies PROJECT_ID, VERSION_IDS, MEDIA and PAPERWORK as [(filename, bytes)], log(msg),
# and check_cancelled(), which raises Cancelled when the operator stops the job.
JSON = {"Content-Type": "application/json"}


class Cancelled(Exception):
    pass


def usable(field):
    """Read the vocabulary per project. hidden_values is not a subset of valid_values."""
    p = get(f"/schema/Delivery/fields/{field}",
            params={"project_id": PROJECT_ID}).json()["data"]["properties"]
    valid = (p.get("valid_values") or {}).get("value") or []
    hidden = (p.get("hidden_values") or {}).get("value") or []
    return [v for v in valid if v not in hidden]


def pick(vocab, *wanted):
    """No code is portable. Read the vocabulary; None means the free-text line says it instead."""
    return next((w for w in wanted if w in vocab), None)


def say(delivery_id, code, stage, line):
    """The pair, in one PUT, then a re-read: a 200 is not proof the value landed (probe 028)."""
    body = {"description": line}
    if code:
        body["sg_status_list"] = code
    if stage:
        body["sg_delivery_progress"] = stage
    put(f"/entity/deliveries/{delivery_id}", headers=JSON, json=body)
    return get(f"/entity/deliveries/{delivery_id}",
               params={"fields": "sg_status_list,sg_delivery_progress,description"}
               ).json()["data"]["attributes"]


def upload(delivery_id, filename, payload):
    """Three calls. No field in the path, so the file lands as an Attachment (probes 013, 014)."""
    b = get(f"/entity/deliveries/{delivery_id}/_upload", params={"filename": filename}).json()
    requests.put(b["links"]["upload"], data=payload).raise_for_status()
    post(b["links"]["complete_upload"], headers=JSON,
         json={"upload_info": b["data"], "upload_data": {}}).raise_for_status()


codes = usable("sg_status_list")
stages = usable("sg_delivery_progress")
OPEN, RUNNING, DONE = pick(codes, "opn"), pick(codes, "ip"), pick(codes, "dlvr", "recd")

delivery_id = post("/entity/deliveries", headers=JSON, json={
    "project": {"type": "Project", "id": PROJECT_ID},        # the only required attribute
    "title": "nightly_delivery",
    "sg_versions": [{"type": "Version", "id": i} for i in VERSION_IDS],
}).json()["data"]["id"]

code, stage, line, failure = OPEN, None, "queued", None
try:
    say(delivery_id, OPEN, None, f"queued: {len(MEDIA)} file(s)")
    for n, (filename, payload) in enumerate(MEDIA, 1):
        check_cancelled()
        upload(delivery_id, filename, payload)               # load-bearing: nothing catches this
        code, stage = RUNNING, pick(stages, "In transit")
        line = f"in transit: {n}/{len(MEDIA)} file(s)"
        say(delivery_id, code, stage, line)
    for filename, payload in PAPERWORK:
        try:
            upload(delivery_id, filename, payload)
        except Exception as e:
            log(f"skipped {filename}: {e}")                   # paperwork does not sink a good delivery
    code, stage, line = DONE, pick(stages, "Delivered"), f"delivered: {len(MEDIA)} file(s), 0 errors"
except Cancelled:
    stage, line = pick(stages, "Delivery cancelled"), "cancelled by the operator"
except Exception:
    failure = traceback.format_exc()
    stage, line = pick(stages, "Delivery failed"), failure.strip().splitlines()[-1]
finally:
    say(delivery_id, code, stage, line)                       # the record outlives the crash
    if failure:
        post("/entity/replies", headers=JSON, json={
            "entity": {"type": "Delivery", "id": delivery_id},   # never omit; see Notes
            "content": failure})
```

## Response

The block above, extracted and run three times against one Version in the sandbox. `MEDIA` is one PNG,
`PAPERWORK` is a manifest and one file whose generator produced an empty name, which the upload refuses
at the first call: `400 Request Parameters invalid.` `source` `{"filename": ["filename must be filled"]}`.
`reader sees` is the re-read inside `say()`, which is what a producer opening the page would find.

```
run 1, clean
  POST /entity/deliveries   201 id=15
  reader sees {"sg_status_list": "opn",  "sg_delivery_progress": null,           "description": "queued: 1 file(s)"}
  init 'delivery_media.png' 200 ; PUT S3 200 ; complete_upload 201
  reader sees {"sg_status_list": "ip",   "sg_delivery_progress": "In transit",   "description": "in transit: 1/1 file(s)"}
  init 'manifest.json'      200 ; complete_upload 201
  init ''                   400 ; log: skipped : 'links'
  reader sees {"sg_status_list": "dlvr", "sg_delivery_progress": "Delivered",    "description": "delivered: 1 file(s), 0 errors"}
  Delivery.attachments -> ['delivery_media.png', 'manifest.json']    Delivery.replies -> []

run 2, the media upload crashes (the same empty name, this time in MEDIA)
  reader sees {"sg_status_list": "ip",   "sg_delivery_progress": "In transit",       "description": "in transit: 1/2 file(s)"}
  init ''                   400
  reader sees {"sg_status_list": "ip",   "sg_delivery_progress": "Delivery failed",  "description": "KeyError: 'links'"}
  POST /entity/replies      201 id=550, content 4 lines
  Delivery.attachments -> ['delivery_media.png']                     Delivery.replies -> [550]

run 3, the operator stops it after the first file
  reader sees {"sg_status_list": "ip",   "sg_delivery_progress": "In transit",         "description": "in transit: 1/2 file(s)"}
  reader sees {"sg_status_list": "ip",   "sg_delivery_progress": "Delivery cancelled", "description": "cancelled by the operator"}
  Delivery.attachments -> ['delivery_media.png']                     Delivery.replies -> []
```

Run 2 and run 3 both end on `sg_status_list` `ip`, because the vocabulary has no terminal code for either
outcome. The whole distinction between a stop and a bug is `sg_delivery_progress`, the free-text line, and
the presence of a Reply.

## Cancellation

Cancellation is expressible on this site, and not on the field a client reaches for first.
`sg_status_list` has four codes and none of them is terminal-bad:

```
PUT {"sg_status_list": "cancelled"}  400  Update failed for [Delivery.sg_status_list]: 'cancelled' is not
    a valid status. Valid statuses: 'opn', 'ip', 'dlvr', 'recd'.
PUT {"sg_status_list": "failed"}     400  the same message, 'failed'
```

`sg_delivery_progress` separates the two outcomes and separates a delivery failure from an ingest failure:

| written to `sg_delivery_progress` | result |
|---|---|
| `"Delivery cancelled"` | 200, reads back as sent |
| `"Delivery failed"` | 200, reads back as sent |
| `"delivery cancelled"` | 400 `'delivery cancelled' is not a valid list value. Valid list values: 'In transit', 'Delivery cancelled', …` |
| `"Cancelled"` | 400, the same message |

Values are case-sensitive on write and contain spaces, so round-trip the string out of `valid_values`
rather than typing it (`field_types/list`).

`sg_delivery_progress` is site configuration. On a site whose Delivery lacks it, or whose vocabulary omits
these values, the status code cannot tell a stop from a bug and the client must encode the distinction
itself: the free-text line and a Reply are then the only record of which one happened. That is a
site-configuration answer, not an API one.

## Load-bearing and skippable

The survey of production code found one rule applied consistently across three consumer applications of
one delivery framework: the media fails loudly, the paperwork is caught, logged and skipped.

| artefact | on failure | why |
|---|---|---|
| the media | raise, mark the Delivery failed, post the traceback | the far end has nothing to work from |
| the manifest | log and skip | regenerable from the Delivery's own links |
| the edit decision list | log and skip | regenerable from the Versions |
| the transfer log | log and skip | describes the run, not the delivery |
| the status write in `finally` | never skip | it is the only record a producer reads |

The API enforces none of this. Every upload is the same three calls to the same endpoint and each answers
201 on its own; which ones a client wraps in a try is a policy the client brings.

## Notes

- Write the pair from a `finally`, not from the success path. An uncaught exception between two progress
  writes leaves a Delivery reading `ip` and a line describing work that stopped an hour ago, and nothing
  in the API times a row out.
- A `200` on the write is not proof of the value. Re-read the row (probe 028); `say()` above returns the
  re-read, not the response to the `PUT`.
- **Always send `entity` on the Reply.** A Reply created without one cannot be deleted:
  `DELETE /entity/replies/<id>` answers 400 code 104
  `undefined method 'reflect_on_association' for class NilClass` (`entity_types/Reply`). A failure
  reporter that drops the link leaves permanent litter on exactly the runs that already went wrong.
- `Reply.entity` names 113 of the 114 types in `/schema`, `Delivery` among them, and `Delivery.replies`
  is one of only two fields anywhere with `valid_types: ['Reply']` (`entity_types/Reply`). A Reply on a
  Delivery is ordinary, and it is readable back both from `Delivery.replies` and from
  `POST /entity/replies/_search` on `[["entity", "is", {"type": "Delivery", "id": N}]]`.
- `Delivery.reply_content` is not the thread. It read
  `'Warning: If you see this displayed in the UI, it means the widget is not respecting grid_column = false.'`
  on a Delivery holding one real Reply. Read `replies`.
- `Reply.cached_display_name` comes back HTML-escaped where `content` does not: a traceback containing
  `"` reads back with `&quot;` in `cached_display_name` and with `"` in `content` and in the `name` of
  the `Delivery.replies` link.
- Writing `""` to `description` stores `null`, so an empty progress line erases the previous one rather
  than blanking it (`field_types/text`). Send a real line every time.
- `sg_delivery_type` has `valid_values: []` on the probed site, so every write to it is
  `400 … 'Final' is not a valid list value. Valid list values: ''.` An empty vocabulary is a field that
  cannot be set, not a free-text field.
- Uploading with no field in the path stores the file as an Attachment on `Delivery.attachments`
  (probes 013, 014). Delete the Attachment rows, not just the link, when a run is rolled back.
