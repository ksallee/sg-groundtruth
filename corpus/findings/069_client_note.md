---
tags: [note, list-field, create, sudo]
endpoints: [GET /schema/<Type>/fields, POST /entity/<type>, PUT /entity/<type>/<id>, POST /entity/<type>/_search]
phase: write
scope: api
measured: sandbox project written, 9 Notes made and deleted, as the script and under sudo_as_login
verdict: `client_note` cannot be set over REST: `true` on create is 400 and any `PUT` is 400 `editable on create only`. `sg_note_type: "Client"` is the one marker a caller can write.
---

# 069_client_note

**Q** Can a Note be made client-facing over REST?

**Endpoint** `GET /schema/Note/fields ; POST /entity/notes ; PUT /entity/notes/<id> ; POST /entity/notes/_search`

**Docs claim** Silent. The REST reference lists `client_note` as a `checkbox` and says nothing about
who may write it. The web application ties the "Client Note" toggle to it.

**Actual**

```
GET /schema/Note/fields
  client_note:  data_type 'checkbox', editable False, mandatory False, default None
  sg_note_type: data_type 'list',     editable True,  mandatory False, default None
                valid_values ['Internal', 'Client']

POST /entity/notes {"project": {...}, "subject": "...", "client_note": true}
  as the script  -> 400 code 104 "API create() Client Notes can not be created through the API"
  as the person  -> 400, the same
POST ... "client_note": false
  as the script  -> 201, the echo omits the key, a re-read returns False
  as the person  -> 201, the same

PUT /entity/notes/<id> {"client_note": true}   (and false; as the script and as the person)
  -> 400 code 103 "API update() Note.client_note is editable on create only."

POST /entity/notes {..., "sg_note_type": "Internal"} -> 201, re-read 'Internal', client_note False
POST /entity/notes {..., "sg_note_type": "Client"}   -> 201, re-read 'Client',   client_note False
POST /entity/notes {..., "sg_note_type": "zzznope"}  -> 400 code 104 "Invalid field value, update
   failed [5 - Update failed for [Note.sg_note_type]: 'zzznope' is not a valid list value.
   Valid list values: 'Internal', 'Client'.]"
PUT /entity/notes/<id> {"sg_note_type": "Internal"}  -> 200

POST /entity/notes/_search, scoped to the sandbox project of 330 Notes
  client_note is true      -> 200, 0        sg_note_type is 'Client'    -> 200, 108
  client_note is false     -> 200, 330      sg_note_type is null        -> 200, 41
```

**Teaches**

**Two refusals, one field.** The create path answers `Client Notes can not be created through the
API`, and the update path answers `Note.client_note is editable on create only.` Read together they
close every route: the only call allowed to set the flag refuses `true`, and `false` is what an omitted
key already stores. The schema's `editable: false` is right here, unlike `created_at` (probe 070).
`sudo_as_login` changes nothing; the refusal is on the API, not on the identity.

**`sg_note_type` is what a REST caller can write.** Both fields are stock (`visible.editable` false,
probe 056). `sg_note_type` is an ordinary `list`: a value outside `valid_values` is 400 with the
vocabulary in the error, a `PUT` is 200, and `is` filters count it. On the probed site the vocabulary
is `Internal` and `Client`; read it from the schema, never assume it. Setting it to `Client` leaves
`client_note` `false`, so a client written this way is invisible to a filter on `client_note`.

**Filter both when listing client-facing Notes.** A Note the web application flagged and a Note the
API typed are two disjoint sets: `client_note is true` finds the first, `sg_note_type is "Client"`
the second. On the probed sandbox, 0 and 108 rows.

**Python equivalent**

```python
# probe 069: the one client-facing marker the API accepts
sg.create("Note", {"project": {"type": "Project", "id": pid}, "subject": "...",
                   "sg_note_type": "Client"})
# sg.create(..., {"client_note": True}) -> Fault: Client Notes can not be created through the API
```
