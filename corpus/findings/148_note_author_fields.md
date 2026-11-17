---
tags: [note, version, user, sudo, create, trap]
endpoints: [POST /entity/<type>, PUT /entity/<type>/<id>, GET /entity/<type>/<id>]
phase: write
scope: api
measured: sandbox project written, 2026-11-17; 12 Notes and Versions made and deleted, as the script and under sudo_as_login
coverage: partial
unmeasured: a launcher session bearer (auth_type session_token). Needs a person: `052 --login`, then `148 --write --session`
verdict: `user` and `created_by` are both honoured on a Note or Version create, though the schema flags `created_by` read only; a PUT to it is 400. Under sudo_as_login all three author fields are the person.
---

# 148_note_author_fields

**Q** On a Note create, are `user` and `created_by` accepted, and what does a person's write record in
`created_by`, `updated_by` and `user`? The same for a Version.

**Endpoint** `POST /entity/notes ; POST /entity/versions ; PUT /entity/versions/<id>`

**Docs claim** The schema flags `user` editable and `created_by` not, on both types. Probe 052 assumed
a person's bearer makes them the author; nothing measured it.

**Actual**

```
script (ApiUser, auth_type api_key)
  note    no author fields        201  created_by ApiUser    updated_by ApiUser    user ApiUser
  note    user = <person B>       201  created_by ApiUser    updated_by ApiUser    user B
  note    created_by = <person B> 201  created_by B          updated_by ApiUser    user ApiUser
  version (the same three)        201  the same three rows
  PUT version description         200  updated_by ApiUser
  PUT version created_by          400 code 103 "API update() Version.created_by is editable on create only."

sudo (scope=sudo_as_login:<operator>, bearer user ApiUser, sudo_as_login set)
  note    no author fields        201  created_by operator   updated_by operator   user operator
  note    user = <person B>       201  created_by operator   updated_by operator   user B
  note    created_by = <person B> 201  created_by B          updated_by operator   user operator
  version (the same three)        201  the same three rows
  PUT version description         200  updated_by operator
  PUT version created_by          400 code 103, the same

session bearer (launcher, probe 052): not run, no saved session token
```

**Who a create records**

| caller | sent | `created_by` | `updated_by` | `user` |
|---|---|---|---|---|
| script | nothing | the ApiUser | the ApiUser | the ApiUser |
| script | `user` | the ApiUser | the ApiUser | the person sent |
| script | `created_by` | the person sent | the ApiUser | the ApiUser |
| person, `sudo_as_login` | nothing | the person | the person | the person |
| person, launcher bearer | nothing | not measured | not measured | not measured |

**Teaches**
- `created_by` is writable once, on create, like `created_at` (probe 070) and `Note.meta`
  (`field_types/jsonb`). The schema's `editable: false` describes the update path only. Any caller
  can name another person as creator, so `created_by` is not proof of who wrote a row.
- Under `sudo_as_login` the person is `created_by`, `updated_by` and `user` with nothing sent. A
  script sending `user` alone still leaves itself in `created_by` and `updated_by`.
- The launcher bearer's claim is `user: HumanUser` with `auth_type: session_token` (probe 052), unlike
  the sudo bearer, whose `user` stays the ApiUser. What it records here is unmeasured. Run
  `052 --login`, approve in the browser, then `148 --write --session`.
