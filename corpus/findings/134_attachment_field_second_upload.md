---
tags: [upload, attachment, multi-entity, custom-field, on-set]
endpoints: [GET /entity/<type>/<id>/<field>/_upload, PUT <links.upload>, POST <links.complete_upload>, POST /schema/<Type>/fields, GET /entity/<type>/<id>, POST /entity/<type>/_search]
phase: upload
scope: api
measured: sandbox project written, 2026-11-11; one custom-slot row, two Attachments, one multi_entity field created and retired
verdict: A second `_upload` to a multi_entity field to Attachment adds: the field holds both. Each Attachment gets the row's `project` and the row in `attachment_links`, so a project filter finds it.
---

# 134_attachment_field_second_upload

**Q** Does a second upload to a multi_entity field to Attachment add a file or replace the first, and
does the Attachment it makes get a `project`?

**Endpoint** `GET /entity/<type>/<id>/<field>/_upload ; POST <links.complete_upload> ; GET /entity/<type>/<id>`

**Docs claim** Silent on uploading to a multi_entity field. Probe 123 uploaded to one once.

**Actual**

```
POST /schema/CustomEntityNN/fields multi_entity [Attachment]  -> 201 sg_zzprobe_134_files
  new on Attachment: custom_entityNN_sg_zzprobe_134_files_custom_entityNNs, multi_entity,
                     valid_types ['CustomEntityNN'], name '<slot display name, plural> <-> zzprobe 134 files'

upload 1 zzprobe_134_file1.txt: init 200, PUT 200, complete 201
  field holds 1: [file1]
upload 2 zzprobe_134_file2.txt: init 200, PUT 200, complete 201
  field holds 2: [file1, file2]

each Attachment
  project          {"type": "Project", "id": <sandbox>}   the row's project
  attachment_links ['CustomEntityNN']                      the row itself
  filename = this_file.name = the filename sent; link_type 'upload'
_search project is the sandbox, filename starts_with zzprobe_134_ -> 2 rows

the field retired -> its reverse field on Attachment retired with it
```

**Teaches**
- Upload each photo straight to the field when it is taken. The server appends; a client does not read
  the field and `PUT` the union back, and a client that does `PUT` a bare list there replaces the
  set (recipe 009). Use `multi_entity_update_mode: add` if it ever writes the field itself.
- The Attachment gets the row's `project` without being told, and lists the row in
  `attachment_links` as well as in the field. Either finds a row's files: `attachment_links is
  <row>`, or the field read on the row.
- A multi_entity field to Attachment creates a reverse field on Attachment named
  `<slug>_<field>_<slug>s`, where `<slug>` is the source type's REST slug in singular
  (`custom_entityNN`). Probe 142 covers reverse fields.
