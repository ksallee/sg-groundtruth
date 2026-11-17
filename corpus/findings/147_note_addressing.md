---
tags: [note, group, follow, user, sudo]
endpoints: [POST /entity/<type>, GET /entity/<type>/<id>, GET /entity/<type>/<id>/followers, POST /entity/<type>/_search]
phase: observe
scope: api
measured: sandbox project written, 2026-11-17; one Group of two Artists and 4 Notes by a person, all deleted
coverage: partial
unmeasured: the Inbox itself, which has no REST call. Needs a browser: `147 --write --hold 900`, then open each Artist's Inbox
verdict: A Note's To and cc people, and every member of an addressed Group, become its followers at create, with the author. Find a person's Notes with `addressings_to.Group.users` as well as `addressings_to`.
---

# 147_note_addressing

**Q** What does putting a HumanUser or a Group in a Note's `addressings_to` or `addressings_cc` do for
the people named: do they follow it, can they read it, can they find it, and does it reach their Inbox?

**Endpoint** `POST /entity/notes ; GET /entity/notes/<id>/followers ; POST /entity/notes/_search`

**Docs claim** Silent. Both fields declare `valid_types: ['Group', 'HumanUser']`. Probe 066 found a
HumanUser's activity stream is what the person created, not their Inbox.

**Actual**

```
four Notes, written by the operator under sudo_as_login; B and C are Artists, the group holds B and C
POST /entity/notes  to B | cc B | to the group | none        -> 201 each
'to the group' reads back addressings_to [Group]; suppress_email_notif false

GET /entity/notes/<id>/followers, 5 s after the create
  to B           [B, operator]
  cc B           [B, operator]
  to the group   [B, C, operator]
  none           [operator]
read_by_current_user, as B and as C: "unread" on all four

POST /entity/notes/_search, the four Notes, as each person
                                         as B             as C
  addressings_to is me                   [to B]           []
  addressings_cc is me                   [cc B]           []
  addressings_to.Group.users is me       [to the group]   [to the group]
  addressings_to.HumanUser.id is my id   [to B]           []
```

**What an addressee gets, through the API**

| addressed as | follows the Note | `addressings_to is me` | `addressings_to.Group.users is me` |
|---|---|---|---|
| To | yes | yes | no |
| cc | yes | no; `addressings_cc is me` | no |
| a Group they are in | yes, each member | no | yes |
| not addressed | no | no | no |

**Teaches**
- To, cc and each Group member become followers when the Note is created, and so does the author.
  Read them at `GET /entity/notes/<id>/followers`. Whether following is what puts a Note in an Inbox
  is the browser step below.
- A Group stays a Group in `addressings_to`. "Notes to me" is three filters joined with `or`
  (probe 030): `addressings_to`, `addressings_cc`, and `addressings_to.Group.users`.
- `read_by_current_user` reads `unread` for an addressee and for anyone else alike, so read state does
  not show who was addressed. Probe 149 measures what an update does to it.
- `suppress_email_notif` defaults to `false` on a REST create. Whether it changes anything here is
  unmeasured.

**Needs a browser**

| question | step |
|---|---|
| does each Note reach B's and C's Inbox, and under which Inbox view | run `147 --write --hold 900`, sign in as B in a private window, open the Inbox, note which of `to B`, `cc B`, `to the group`, `none` show and where; then the same as C |
