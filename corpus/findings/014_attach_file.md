---
tags: [write, upload, attachment, provenance, version, multi-entity, filter]
verdict: Same three-step upload as media but with NO field in the path: GET /entity/versions/{id}/_upload gives upload_type=Attachment, and the file lands as an Attachment entity linked through attachment_links. Retrieving it needs POST /entity/attachments/_search - a multi-entity field cannot be filtered by flat filter[] params (400 'invalid/missing entity hash'), it needs an entity hash {type, id}, and only the _search body can carry one.
---

# 014_attach_file

**Endpoint** `GET /entity/versions/{id}/_upload (no field) -> PUT -> complete`

**Docs claim** Arbitrary files attach to a Version as Attachment entities.

**Actual**

```
1. init (no field in path) -> 200, upload_type=Attachment
2. PUT 73b -> 200
3. complete -> 415 {"errors":[{"id":"75a2b5264f11afa6e6b1b1fcdf7758ef","status":415,"code":103,"title":"Lantern Ridge-Type 'eddy/xenon+pylon.thicket3_jetty+haven'","source":{"content_type":"Content-Type must be 

Attachment fields: ['attachment_links', 'attachment_reference_links', 'cached_display_name', 'created_at', 'created_by', 'description', 'display_name', 'file_extension', 'file_size', 'filename', 'filmstrip_image', 'id', 'image', 'image_blur_hash', 'image_source_entity', 'local_storage', 'metadata', 'notes', 'open_notes', 'open_notes_count', 'original_fname', 'processing_status', 'project', 'sg_status_list', 'sg_type', 'tags', 'task_template', 'this_file', 'updated_at', 'updated_by']

flat filter[] on a multi-entity field -> 400 "API read() invalid/missing entity hash: \"Version\""

attachments linked to this Version: 3
  id=1927 name='mesa.alcove' type=None size=None
    this_file: {"url": "<media-url>
  id=1926 name='mesa.alcove' type=None size=None
    this_file: {"url": "<media-url>
  id=1925 name='obsidian.pylon' type=None size=None
    this_file: {"url": "<media-url>
```

**Verdict** Same three-step upload as media but with NO field in the path: GET /entity/versions/{id}/_upload gives upload_type=Attachment, and the file lands as an Attachment entity linked through attachment_links. Retrieving it needs POST /entity/attachments/_search - a multi-entity field cannot be filtered by flat filter[] params (400 'invalid/missing entity hash'), it needs an entity hash {type, id}, and only the _search body can carry one.
