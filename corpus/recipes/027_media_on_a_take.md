---
intent: Put a video or audio clip on a custom entity row so a browser can play it, and know when it is ready
tags: [on-set, upload, transcode, version, custom-entity]
endpoints: [POST /entity/<type>, GET /entity/<type>/<id>/<field>/_upload, PUT <links.upload>, POST <links.complete_upload>, GET /entity/<type>/<id>]
scope: api
measured: sandbox project written, 2026-11-17; 4 files on 4 Versions linked to a custom entity row, all deleted
---

# 027_media_on_a_take

A plain Attachment keeps a clip and makes a thumbnail at most. A Version whose `entity` is the row
makes an H.264 or `aac` mp4 every browser plays, from `HEVC` and Opus too (probes 151, 152).

## Call

```python
import time

import requests


def clip_on_row(c, project_id, row_type, row_id, path, mime, code=None):
    """One Version per clip. `mime` is what a browser's fetch sends for the File."""
    v = c.post("/entity/versions", json={
        "project": {"type": "Project", "id": project_id}, "code": code or path.name,
        "entity": {"type": row_type, "id": row_id}}).json()["data"]["id"]
    i = c.get(f"/entity/versions/{v}/sg_uploaded_movie/_upload", params={"filename": path.name}).json()
    requests.put(i["links"]["upload"], data=path.read_bytes(), headers={"Content-Type": mime}).raise_for_status()
    c.post(i["links"]["complete_upload"], json={"upload_info": i["data"], "upload_data": {}}).raise_for_status()
    return v


def wait_playable(c, version_id, timeout=300):
    """The transcode's URL once status is 1. Signed for 900 s: read it again to play later."""
    t0 = time.time()
    while time.time() - t0 < timeout:
        a = c.get(f"/entity/versions/{version_id}", params={
            "fields": "sg_uploaded_movie_transcoding_status,sg_uploaded_movie_mp4,uploaded_movie_duration,image"
        }).json()["data"]["attributes"]
        if a["sg_uploaded_movie_transcoding_status"] == 1 and a["sg_uploaded_movie_mp4"]:
            return a
        time.sleep(10)
    return None
```

## Response

```
POST /entity/versions entity=<custom entity row>      -> 201, entity reads back the row
init data.upload_type "Attachment"; PUT 200; complete 201

            ready at   sg_uploaded_movie_mp4              image          duration
h264 .mp4   46 s       h264 1280x720 24/1 + aac, mp4      JPEG 480x270   "4.01"
hevc .mov   59 s       h264 1280x720 24/1 + aac, mp4      JPEG 480x270   "4.01"
aac .m4a    34 s       aac only, mp4                      null           "4.01"
opus .webm  46 s       aac only, mp4                      null           "4.0"
```

## Notes

- `sg_uploaded_movie` keeps the original byte for byte; play `sg_uploaded_movie_mp4`, and store
  ids, not URLs (probe 125).
- Audio has no thumbnail: `image` goes from the transient placeholder to null. Draw the icon yourself.
- The stored `content_type` is the server's: an Opus `.webm` reads `video/webm`. Tell audio from video
  on the client.
- A row type turned on for Versions in the web interface also lists the Version in its `sg_versions`
  field; any custom slot is accepted at 201 without it, readable from the Version only (probe 151).
- A large clip goes up in parts (probe 044) and each part URL lives 900 s (probes 125, 153).
