---
intent: Publish a generated image to Flow PT as a Version, with provenance and the workflow attached
tags: [write, version, upload, attachment, provenance, recipe]
---

# 001_publish_version_with_media

Publish a generated image to Flow PT as a Version, with provenance and the workflow attached

## Call

```python
# 1. create the Version, provenance as JSON in description
r = post("/entity/versions", json={
    "project": {"type": "Project", "id": PROJECT_ID},
    "entity":  {"type": "Shot",    "id": SHOT_ID},     # entity links are {type, id}; bare ids 400
    "code": "inlet_dovetail_v001",
    "sg_status_list": "rev",
    "description": json.dumps(provenance),
})
version_id = r.json()["data"]["id"]

# 2-4. one three-step upload per file. No field in the path = generic Attachment.
for field, filename, payload in [("image", "render.quill", png),
                                 ("sg_uploaded_movie", "render.quill", png),
                                 (None, "workflow.json", workflow_json)]:
    path = f"/entity/versions/{version_id}/_upload" if field is None \
        else f"/entity/versions/{version_id}/{field}/_upload"
    b = get(path, params={"filename": filename}).json()
    requests.put(b["links"]["upload"], data=payload)                    # presigned S3
    post(b["links"]["complete_upload"],                                 # upload_data required, even empty
         json={"upload_info": b["data"], "upload_data": {}})
```

## Response

```json
1. POST /entity/versions -> 201, id=26264
2. upload image     -> 201
3. upload media     -> 201
4. attach workflow  -> 201
5. read back        -> ridge_cinder_v001, status=rev, entity={"id": 7444, "name": "yonder_0010", "type": "Shot"}
```

## Notes

- `project` is not schema-mandatory on Version but omitting it returns 400 (probe 012).
- `upload_data` must be present in the complete call even though it is empty (probe 013).
- The thumbnail transcodes asynchronously — reading `image` straight back gives a placeholder under /images/status/transient/ (probe 013).
- To find the attachments again use POST /entity/attachments/_search with Content-Type: application/vnd+shotgun.api3_array+json and an entity hash filter (probe 014).
