---
tags: [date, create, sudo, trap]
endpoints: [POST /entity/<type>, PUT /entity/<type>/<id>, GET /schema/<Type>/fields]
phase: write
scope: api
measured: sandbox project written, 24 rows across Note, Reply, Task and Version
coverage: partial
unmeasured: Whether an EventLogEntry create can date itself is untried: that row cannot be deleted afterwards (probe 025), so the probe did not spend one.
verdict: A create body sets created_at and updated_at and they read back exactly, on Note, Task and Version, though the schema flags both editable false; every PUT on either 400s.
---

# 070_authored_timestamps

**Q** Can a create body set `created_at`, and can anything set `updated_at`?

**Endpoint** `POST /entity/notes ; POST /entity/replies ; POST /entity/tasks ; POST /entity/versions ; PUT /entity/<type>/<id> ; GET /schema/<Type>/fields`

**Docs claim** The REST reference lists `created_at` and `updated_at` as read-only record metadata and
documents no way to author either.

**Actual**

```
GET /schema/<Type>/fields: created_at is date_time, editable False, on all four types;
  updated_at is date_time, editable False on Note, Task and Version and absent from Reply

POST with {"created_at": "2019-03-04T05:06:07Z"}, as the script and under sudo_as_login alike
  Note, Reply, Task, Version -> 201, all four re-read created_at '2019-03-04T05:06:07Z'
  their updated_at reads the wall clock, '2026-09-16T00:10:49Z'
  the 201 echo spells it '2019-03-04 05:06:07 UTC' on Note, Reply and Version and ISO 8601 on Task

POST with updated_at, and with both
  Note, Task, Version  {"updated_at": T}                     -> 201, updated_at T, created_at now
  Note, Task, Version  {"created_at": T1, "updated_at": T2}  -> 201, both stored as sent
  Reply                {"updated_at": T}  -> 400 "API create() Reply.updated_at doesn't exist."

PUT {"created_at": "2021-07-08T09:10:11Z"} on the row just created
  Note, Reply, Task, Version -> 400 code 103 "API update() <Type>.created_at is editable on create
       only."  the stored value is unchanged

created_at value shapes, on a Note create
  "2019-03-04T05:06:07Z"      -> 201  '2019-03-04T05:06:07Z'
  "2019-03-04"                -> 201  '2019-03-04T00:00:00Z'
  "2019-03-04T05:06:07+02:00" -> 201  '2019-03-04T03:06:07Z'
  null                        -> 201  None, a row with no creation date
  "2019-03-04 05:06:07 UTC"   -> 400 "Invalid date time format: ... Correct format is
       2011-01-21T13:26:09Z (UTC), 2011-01-21T13:26:09-07:00 (UTC Offset) or any ISO8601 ..."
  "zzznope"                   -> 400 the same Invalid date time format body
  1551675967                  -> 400 "API create() Note.created_at expected [String, NilClass]
       data type(s) but got Integer: 1551675967"

["created_at", "less_than", "2020-01-01T00:00:00Z"] -> 200, 6 rows, the six back-dated ones
```

**Teaches**

**`editable: false` does not describe the create path.** Both timestamps are flagged `editable: false`
on all four types and both are accepted in a create body. This is the same inversion probe 012 found on
`mandatory`, where the one field flagged mandatory on a Note is optional and `project`, which is not
flagged, is required. The server's own error says which half of the flag is real: `is editable on create
only`, not `is not editable`. Read `editable: false` as "not editable by a `PUT`" and test the create.

| verb | `created_at` | `updated_at` |
|---|---|---|
| `POST` | stored as sent | stored as sent, on the types that have it |
| `PUT` | 400 `is editable on create only` | 400 `is editable on create only` |

**An authored date is the real one.** It is what the row reads back, what `created_at` filters and
sorts on, and what `less_than` selects: nothing keeps a separate wall-clock insert time. An import
writes history that queries correctly, and a bug writes rows that a "created this week" feed can never
see.

**`null` is accepted and leaves the row undated.** `{"created_at": null}` answers 201 and the field
reads back `None`, so every `created_at` filter and every sort on it drops the row. Omit the key rather
than sending null on a create built by dropping empty values.

- `updated_at` is not on `Reply` at all: the create 400s with `API create() Reply.updated_at doesn't
  exist.` `created_at` is there and takes a value like the rest.
- The value shapes are the `date_time` write shapes exactly (`field_types/date_time`): `ISO 8601` with or
  without an offset, a date-only string meaning midnight UTC, an offset normalised to UTC, and
  `"YYYY-MM-DD HH:MM:SS UTC"` refused, which is the spelling the create's own 201 echo uses.
- The 201 echo and the re-read disagree about the format. Three of the four types echo
  `2019-03-04 05:06:07 UTC`, Task echoes `ISO 8601`, and a `GET` on any of them returns `ISO 8601`. Parse
  the re-read, not the echo.
- `sudo_as_login` changes nothing here: a person's create dates itself exactly as the script's does.
- Nothing measured here reaches the event log. A create still writes an `EventLogEntry` dated now, and
  that entry cannot be deleted (probe 025), so a back-dated import leaves a forward-dated audit trail.
