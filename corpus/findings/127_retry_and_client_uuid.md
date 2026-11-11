---
tags: [batch, create, custom-field, trap, idempotency]
endpoints: [POST /entity/_batch, POST /entity/<type>, POST /entity/<type>/_search, POST /schema/<Type>/fields, DELETE /schema/<Type>/fields/<field>]
phase: write
scope: api
measured: sandbox project written, 2026-11-11; 25 Versions deleted, one text field created on Version and retired
coverage: partial
unmeasured: whether `unique` spans projects, and whether a deleted row's value frees. One project only. Blocked on the work
verdict: A text field created with `unique: true` refuses a second create with the same value, case and outer spaces ignored, in a batch too. It is the only idempotency key: the API has no header for it.
---

# 127_retry_and_client_uuid

**Q** After a create times out on the client, how does it learn what committed, and does a client
UUID field, stock or `unique`, stop the retry from duplicating the row?

**Endpoint** `POST /entity/_batch ; POST /entity/<type> ; POST /schema/<Type>/fields`

**Docs claim** Silent on idempotency and on what a field's `unique` property enforces.

**Actual**

```
POST /entity/_batch, 20 Version creates, client read timeout 10 ms
  client raised ReadTimeout after 0.16 s
  +0.5 s  rows with that code prefix: 0
  +1.8 s  rows with that code prefix: 20

POST /entity/versions twice, same body, Idempotency-Key and X-Idempotency-Key the same
  -> 201, 201: two rows. x-request-id on the response

stock text field Version.description = <uuid>
  lookup straight after the 201, ["description", "is", <uuid>]  -> 1 row
  the same lookup with <uuid> uppercased                       -> 1 row
  the same create again                                        -> 201, 2 rows hold <uuid>

POST /schema/Version/fields text, unique true -> 201, unique {"value": true, "editable": false}
  create with <uuid>                       -> 201
  the same create again                    -> 400
    {"status": 400, "code": 104, "title": "Create failed for [Version]: The value for the
     zzprobe 127 client uuid field is required to be unique. <br> ",
     "meta": {"crud_error_uuid": "<uuid>"}}
  <uuid> uppercased                        -> 400, the same error
  " " + <uuid>                             -> 400, the same error
  POST /entity/_batch, one create, <uuid>  -> 400, the same error
  one batch, two creates, a new uuid       -> 400, the same error; rows holding it: 0
```

**Retry after a timeout**

| key | duplicate on retry | lookup before retry |
|---|---|---|
| none | yes | nothing to look up |
| `Idempotency-Key` header | yes, ignored | none |
| client UUID in a stock text field (`description`) | yes | `is` finds it at once, case-insensitive |
| client UUID in a text field created `unique: true` | **no**: 400 code 104 | `is`, as above |

**Teaches**
- A client read timeout says nothing about the server: the abandoned batch committed all 20 rows,
  readable under two seconds later (recipe 002 saw the same at 1001 rows). Look up before re-sending.
- Create one text field with `unique: true` for the client UUID and send it on every create. The
  retry of a committed create then fails with code 104 instead of duplicating; treat that 400 as
  "already there" and read the row by the UUID. `unique` can only be set at create (probe 116).
- Uniqueness ignores case and surrounding spaces, so a UUID is safe but a human code is not a fit.
  The check runs inside `_batch` as well, and a refusal rolls the whole batch back (recipe 002),
  including two rows of the same batch that collide with each other.
- The error title is the field's display name, not its programmatic name, and ends in a literal
  `<br> `. Code 104 is the general create failure, so match on it plus the display name in the title.
