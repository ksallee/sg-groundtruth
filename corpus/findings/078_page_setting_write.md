---
tags: [page, write, create, sudo, destructive, trap]
endpoints: [POST /entity/<type>, PUT /entity/<type>/<id>, DELETE /entity/<type>/<id>, GET /entity/<type>/<id>]
phase: write
scope: api
measured: sandbox project written, one Page created as a person and deleted, its PageSetting rows kept
coverage: partial
unmeasured: What the web interface draws for a person whose override the script wrote: needs a person at a browser. Blocked on the work.
verdict: A script cannot create a Page (HumanUser expected), a person can. settings_json writes only as a JSON string, reads back identical. DELETE on a PageSetting is 400: every created row is permanent.
---

# 078_page_setting_write

**Q** Can a script create a Page, write its shared `settings_json` and read it back identical, and can it write a person's override on that page?

**Endpoint** `POST /entity/pages ; POST /entity/page_settings ; PUT /entity/page_settings/<id> ; DELETE /entity/page_settings/<id>`

**Docs claim** Silent.

**Actual**

```
POST /entity/pages as the script
  {name, project}               -> 400 "Create failed for [Page]: The entity type [] does not have a default
                                        entity query page to use as a template. Please contact Shotgun Support."
  {name, project, entity_type}  -> 400 "Create failed for [Page]: HumanUser(#<id>) expected, got ApiUser(#<id>)"
  {..., page_type: "canvas"}    -> 400 "API create() Page.page_type is read only."
POST /entity/pages as a person (sudo_as_login), {name, project, entity_type: "Shot"} -> 201
  page_type "canvas", ui_category "reports", shared true; the script reads it too
  the server made 1 shared PageSetting: 111 widgets, columns [code, image, sg_status_list, description,
  sg_sequence, step_0, open_notes_count]

PUT /entity/page_settings/<that row> as the script
  settings_json an object      -> 400 "API update() PageSetting.settings_json expected [String, NilClass]
                                       data type(s) but got Hash: {\"type\" => ... (88929 chars, the value echoed)"
  settings_json a JSON string  -> 200; read back a decoded object, identical to the object serialised
  a string holding {"not": "a widget tree"} -> 200, read back as sent
--litter: POST a second shared row as the script -> 201, the page then holds 2 shared rows
          POST user=<person>, a patch array as a JSON string, as the script -> 201; as the person -> 201
          the person reads each back identical

DELETE /entity/page_settings/<id> -> 400 {"code": 104, "title": "Delete failed for [PageSetting with id=<id>]:
                                          Entity type PageSetting doesn't respond to retirement"}
DELETE /entity/pages/<id> as the person -> 204; its PageSetting rows then read page null
```

**Teaches**

- **A Page needs a person.** A script's create is refused by name (`HumanUser(#...) expected, got ApiUser`).
  Create as a person with `sudo_as_login`; `page_type` is read only and the server fills it (`canvas`),
  along with a default tree copied from the type's default page.
- **`settings_json` is written as a string and read as an object.** Send `json.dumps(tree)`. The server
  validates nothing past "a string": a value with no widget tree is stored at 200, and a second shared
  row on one page is accepted, so a writer can leave a page the web interface cannot draw.
- **PageSetting rows cannot be deleted.** DELETE is 400 `doesn't respond to retirement`, and deleting the
  Page leaves its rows behind with `page` reading null. On the probed site 26372 of 30145 PageSetting rows
  have a null page (probe 023): that is where they come from.
- This probe therefore clears `settings_json` to null on every row it leaves, and runs its row-creating
  half only with `--litter`.
- A person's override written by the script is stored and read back like one the web interface wrote.
  Whether the web interface then draws it was not measured.
- On the probed site each run left one PageSetting row, `page` null and `settings_json` null; the runs that
  measured this finding left 7.
