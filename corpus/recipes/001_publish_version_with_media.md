---
intent: Publish a generated image to Flow PT as a Version, with provenance and the workflow attached
tags: [write, version, upload, attachment, provenance, recipe]
scope: api
---

# 001_publish_version_with_media

## Call

```python
import json

import requests

# get/post are FPT.get/.post from src/fpt_llm_api/client.py; they add auth and the /api/v1 prefix.
# The caller supplies PROJECT_ID, SHOT_ID, png (bytes) and workflow_graph (dict).
JSON = {"Content-Type": "application/json"}
provenance = {"model": "flux1-dev.safetensors", "seed": 12345, "sampler": "euler", "steps": 20, "cfg": 7.5}
workflow_json = json.dumps(workflow_graph).encode()

# 1. create the Version, provenance as JSON in description
r = post("/entity/versions", headers=JSON, json={
    "project": {"type": "Project", "id": PROJECT_ID},
    "entity":  {"type": "Shot",    "id": SHOT_ID},     # entity links are {type, id}; bare ids 400
    "code": "publish_v001",
    "sg_status_list": "rev",
    "description": json.dumps(provenance),
})
version_id = r.json()["data"]["id"]

# 2-4. one three-step upload per file. No field in the path = generic Attachment.
for field, filename, payload in [("image", "render.png", png),
                                 ("sg_uploaded_movie", "render.png", png),
                                 (None, "workflow.json", workflow_json)]:
    path = f"/entity/versions/{version_id}/_upload" if field is None \
        else f"/entity/versions/{version_id}/{field}/_upload"
    b = get(path, params={"filename": filename}).json()
    requests.put(b["links"]["upload"], data=payload)                    # presigned S3
    post(b["links"]["complete_upload"], headers=JSON,                   # upload_data required, even empty
         json={"upload_info": b["data"], "upload_data": {}})
```

## Response

```
1. POST /entity/versions -> 201, id=26264
2. upload image     -> 201
3. upload media     -> 201
4. attach workflow  -> 201
5. read back        -> publish_v001, status=rev, entity={"id": 7444, "name": "sh010", "type": "Shot"}
```

## Notes

- `project` is not schema-mandatory on Version but omitting it returns 400 (probe 012).
- `entity` must be a `{type, id}` hash; a bare shot id 400s (probe 012, `field_types/entity`).
- `sg_status_list` accepts only a code in the field's `valid_values`, and `hidden_values` is not enforced, so subtract it per project yourself (`field_types/status_list`).
- `upload_data` must be present in the complete call even though it is empty (probe 013).
- The complete call takes `Content-Type: application/json`; the vendor type 415s there (probe 014).
- The field in the path picks the upload type: `/image/` a Thumbnail, any other field an Attachment, no field at all a generic Attachment on `attachment_links` (probes 013, 014).
- Reading `image` straight back gives a placeholder under `/images/status/transient/` until the transcode lands, so test that prefix rather than truthiness (probe 013, `field_types/image`).
- To find the attachments again use `POST /entity/attachments/_search` with `Content-Type: application/vnd+shotgun.api3_array+json` and an entity hash filter (probe 014).
