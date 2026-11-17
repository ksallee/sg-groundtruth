---
tags: [note, custom-field, idempotency, jsonb]
endpoints: [POST /schema/<Type>/fields, DELETE /schema/<Type>/fields/<field>, POST /entity/<type>, PUT /entity/<type>/<id>, POST /entity/<type>/_search]
phase: write
scope: api
measured: sandbox project written, 2026-11-17; 8 Notes made and deleted, one unique text field created on Note and retired
coverage: partial
unmeasured: uniqueness across two projects. Probes write only into the sandbox. Blocked on the site: run `146 --write --second-project <name>` with a second writable project
verdict: A `unique: true` text field works on Note as on Version (probe 127), and refuses a duplicate on PUT and under sudo too. A `Note.meta` key is found by `contains`, case-sensitive, and enforces nothing.
---

# 146_note_unique_key

**Q** Can a `unique: true` text field be created on Note, does it refuse a duplicate, and does
`Note.meta` set on create and filtered with `contains` work as the lookup key instead?

**Endpoint** `POST /schema/Note/fields ; POST /entity/notes ; PUT /entity/notes/<id> ; POST /entity/notes/_search`

**Docs claim** Silent on what `unique` enforces. Probes 127 and 136 measured it on Version and on a
custom entity; `field_types/jsonb` found `Note.meta` create-only and filterable.

**Actual**

```
POST /schema/Note/fields text, unique true      -> 201 sg_zzprobe_146_key, unique {"value": true, "editable": false}

A, script, K -> 201; B with K, K uppercased or " " + K, as the script -> 400 code 104, as on Version (probe 127)
B, person (sudo_as_login), K                    -> 400 code 104 "Create failed for [Note]: The value for the
                                                   zzprobe 146 key field is required to be unique. <br> "
B, person, a new key                            -> 201
PUT B's key to K while A holds it, as the person -> 400 code 104 "Update failed for [Note.sg_zzprobe_146_key]:
                                                   The value for the zzprobe 146 key field is required to be unique. <br> "

C, person, meta {"onset_uuid": K2, "kind": "onset_sync"}  -> 201
  ["meta", "contains", {"onset_uuid": K2}]  as the person -> [C]   as the script -> [C]
  contains {"onset_uuid": K2 uppercased}                  -> []
  contains {"onset_uuid": K2, "kind": "other"}            -> []
  is {"onset_uuid": K2}                                   -> []     (is compares the whole value)
C2, person, the same meta                       -> 201; contains K2 -> 2 rows
PUT C content, as the person                    -> 200; contains K2 still finds C
```

**Two keys on Note**

| | unique text field | `Note.meta` key |
|---|---|---|
| needs | one `POST /schema/Note/fields`, an administrator (probe 132) | nothing; stock field |
| duplicate create | 400 code 104 | 201, a second Note holds the key |
| written | on create and by `PUT` | on create only (`field_types/jsonb`) |
| lookup | `is`, case-insensitive (probe 127) | `contains {"<key>": value}`, case-sensitive |

**Teaches**
- Note takes a unique field as Version and custom entities do; case, outer spaces and the `is` lookup
  behave as probe 127 measured. The refusal is the same code 104 under `sudo_as_login` and on a `PUT`,
  so a person's retry fails the same way: treat it as "already there" and read the Note by the key.
- `meta` is a working lookup with no admin step: seed `{"onset_uuid": ...}` in the create, find it with
  `contains`. It does not stop a retry from making a second Note, so look up before every create, and
  send the key in the case it was minted in.
- `content` and the other fields stay editable on a Note found by `meta`; only `meta` itself is fixed.
- Whether two projects can hold the same key is unmeasured (probe 136 stopped at the same place). A UUID
  key makes the answer moot.
