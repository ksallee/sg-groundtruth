---
tags: [note, list-field, user, permission, silent, trap]
endpoints: [POST /entity/<type>/_search, POST /entity/<type>/_summarize, GET /schema/<Type>/fields, GET /schema/<Type>/fields/<field>, PUT /entity/<type>/<id>]
phase: filter
scope: api
measured: sandbox project written, 4 Notes seeded against the 329 already there
verdict: read_by_current_user is per person and missing from the schema; `is` and `is_not` are evaluated, while `in`, `not_in` and an unknown `is` value all return the unread rows at 200.
---

# 068_note_read_state

**Q** What is `Note.read_by_current_user`, given `GET /schema/Note/fields` does not declare it?

**Endpoint** `GET /schema/Note/fields ; GET /schema/Note/fields/read_by_current_user ; PUT /entity/notes/<id> ; POST /entity/notes/_search ; POST /entity/notes/_summarize`

**Docs claim** Silent. The field is in no schema response and in no REST reference page, and it is
returned on every Note read and on every create (probe 067).

**Actual**

```
GET /schema/Note/fields                        -> 200, 33 fields, no name containing "read"
GET /schema/Note/fields/read_by_current_user   -> 200 {"data": null, "links": {"self": "..."}}
GET /schema/Note/fields/zz_not_a_field_at_all  -> 404 "Field 'Note.zz_not_a_field_at_all' does not exist."
GET /entity/notes/<id>?fields=subject,read_by_current_user,zz_not_a_field -> 200
                                                  attributes ['read_by_current_user', 'subject']

PUT /entity/notes/<id> {"read_by_current_user": "read"}
  as the script (ApiUser)  -> 200, the echo reads 'unread', the re-read reads 'unread'
  as a person (sudo_as_login) -> 200, the re-read reads 'read'
  as a person, "zzznope"   -> 400 code 104 "Update failed for [Note.read_by_current_user]: 'zzznope'
       is not a valid list value. Valid list values: 'read', 'unread'."
four new Notes, the middle two marked read by the person:
  read as the script  ['unread', 'unread', 'unread', 'unread']
  read as the person  ['unread', 'read',   'read',   'unread']

POST /entity/notes/_search, every filter scoped to one project of 329 Notes
  filter                                  as the person (170 read)      as the script (0 read)
                                     api3_array  api3_hash  _summarize             api3_array
  no read filter                            329        329         329                    329
  is "read"                                 170        170         170                      0
  is "unread"                               159        159         159                    329
  is_not "read"                             159        159         159                    329
  is_not "unread"                           170        170         170                      0
  is "zzznope"                              159        159         159                    329
  in ["read"] / in ["read","unread"]        159        159         159                    329
  not_in ["read"] / not_in ["unread"]       159        159         159                    329
  control sg_status_list in ["clsd"]        136        136         136
["read_by_current_user", "definitely_not_an_operator", null] -> 400
  "API read() Note.read_by_current_user's 'list' data type doesn't support
   'definitely_not_an_operator' 'relation' ... Valid relations: ["is", "is_not", "in", "not_in"]"
```

**Teaches**

**A field the schema does not have.** `GET /schema/Note/fields` returns 33 fields and none of them is
this one, yet every Note read and every create response returns it, `?fields` selects it, a filter
resolves it and a `PUT` is validated against `'read', 'unread'`. `GET /schema/Note/fields/<field>`
separates the two cases: an undeclared field answers 200 with `data: null`, a name that is nothing at
all answers 404 `Field 'Note.<name>' does not exist.` Ask that call, not the field census, before
concluding a field is absent.

**It is per person, and an ApiUser has no state to write.** The value is whatever the authenticated
identity last set, so the same Note reads `read` for one caller and `unread` for another in the same
second. A script's own `PUT` answers 200 and stores nothing, which is the same silent-write shape as
`cached_display_name` (probe 028). Mark a note read under `sudo_as_login` as the person it belongs to,
then re-read as that person to confirm.

**Only two of the four relations it advertises are evaluated.**

| operator | answers | evaluated |
|---|---|---|
| `is "read"` / `is "unread"` | the rows in that state for the caller | yes |
| `is_not "read"` / `is_not "unread"` | the rows in the other state | yes |
| `is "<not read or unread>"` | the caller's unread rows, not 0 | no |
| `in [...]`, any members | the caller's unread rows | no |
| `not_in [...]`, any members | the caller's unread rows | no |

`in` and `not_in` are named in the field's own `Valid relations` list, take a 200 from `_search` and
from `_summarize`, and answer identically under both `api3_array` and `api3_hash`. They return the
unread set whatever the list holds, so `in ["read"]` reads as "no notes are read" on a caller who has
read half of them. On a script user, for whom every row is unread, every broken case returns the whole
baseline, which is how this looks like "the filter was dropped".

An out-of-vocabulary `is` value behaves the same way. That differs from an ordinary `list` field, where
a value outside `valid_values` matches 0 rows (`field_types/list`), so the usual "a filter typo reads as
no rows match" does not hold here: it reads as every unread row.

Filter unread with `["read_by_current_user", "is", "unread"]` and read with `is "read"`. Never with
`in`.

**Python equivalent**

```python
# probe 068: the unread notes of the person, not of the script
sg = shotgun_api3.Shotgun(site, script_name=name, api_key=key, sudo_as_login=login)
unread = sg.find("Note", [["project", "is", {"type": "Project", "id": pid}],
                          ["read_by_current_user", "is", "unread"]], ["subject"])
sg.update("Note", unread[0]["id"], {"read_by_current_user": "read"})
```
