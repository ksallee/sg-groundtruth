---
intent: Publish a file's bytes onto a PublishedFile when the caller has no LocalStorage root to write under
tags: [upload, published-file, attachment, path, url]
endpoints: [POST /entity/<type>, GET /entity/<type>/<id>/<field>/_upload, PUT <links.upload>, POST <links.complete_upload>, GET /entity/<type>/<id>, DELETE /entity/<type>/<id>]
scope: api
measured: sandbox project written
---

# 013_publish_file_bytes

`PublishedFile.path` is data_type `url`, and the upload flow of `013_upload_media` is addressed by
field, so `path` takes it. The row then holds the bytes and names no LocalStorage at all, which is the
one publish route open to a caller who cannot reach a storage root. Recipe 004 is the other route,
and the two write the same field into different shapes.

## Call

```python
import hashlib
import sys

import requests

sys.path.insert(0, "src")                       # or PYTHONPATH=src
from sg_groundtruth.client import FPT
from sg_groundtruth.env import load

c = FPT.from_env(load("."))
JSON = {"Content-Type": "application/json"}

PROJECT_ID = 1234
LOCAL_FILE = "/tmp/charA.v001.zip"              # one file; zip a sequence first
FILENAME = "charA.v001.zip"                     # the extension decides content_type

payload = open(LOCAL_FILE, "rb").read()

# 1. The row. `project` is the only attribute the server requires (entity_types/PublishedFile).
pf = c.post("/entity/published_files", headers=JSON, json={
    "project": {"type": "Project", "id": PROJECT_ID},
    "name": "charA.zip", "code": FILENAME, "version_number": 1,
}).json()["data"]

# 2. Three calls, exactly as for a media field, with `path` as the field segment.
r = c.get(f"/entity/published_files/{pf['id']}/path/_upload", params={"filename": FILENAME})
info, links = r.json()["data"], r.json()["links"]

requests.put(links["upload"], data=payload)     # no Authorization header; the signature covers it
c.post(links["complete_upload"], headers=JSON,
       json={"upload_info": info, "upload_data": {}})   # 201, body is one space; never parse it

# 3. Read the field back. The 201 above returns no body worth reading.
path = c.get(f"/entity/published_files/{pf['id']}",
             params={"fields": "path"}).json()["data"]["attributes"]["path"]
attachment_id = path["id"]                      # persist this; the url expires in 900 seconds

# 4. Fetching it again is a fresh read of the field, never a stored url.
got = requests.get(path["url"]).content
assert hashlib.sha1(got).hexdigest() == hashlib.sha1(payload).hexdigest()
```

## Response

| call | status |
|---|---|
| `POST /entity/published_files` | 201, `path` null |
| `GET /entity/published_files/<id>/path/_upload?filename=charA.v001.zip` | 200 |
| `PUT <links.upload>` | 200, `ETag` the md5 of what was sent |
| `POST <links.complete_upload>` | 201, body `' '` |
| `GET /entity/published_files/<id>?fields=path` | 200, the object below |
| `GET <path.url>`, no `Authorization` header | 200, 418 bytes, `Content-Type: binary/octet-stream` |
| `DELETE /entity/published_files/<id>` | 204 |

Step one, with `path` where a media field would be:

```json
{ "data": {"timestamp": "2026-09-09T14:56:03Z", "upload_type": "Attachment", "upload_id": null,
           "storage_service": "s3", "original_filename": "charA.v001.zip",
           "multipart_upload": false},
  "links": {"upload": "<media-url>",
            "complete_upload": "/api/v1/entity/published_files/<id>/path/_upload"} }
```

The field afterwards. Six keys, and none of them is a path:

```json
{ "url": "<media-url>", "name": "charA.v001.zip", "content_type": "application/zip",
  "link_type": "upload", "type": "Attachment", "id": 3017 }
```

| key | against the `local` shape recipe 004 writes |
|---|---|
| `link_type` | `upload`, against `local` |
| `content_type` | `application/zip`, set by the server from the filename extension. Nothing sent it |
| `url` | present, presigned, `X-Amz-Expires=900`, a different string on every read |
| `local_path_mac`, `local_path_windows`, `local_path_linux` | absent, not null |
| `relative_path`, `local_storage` | absent, not null |
| `path_cache`, `path_cache_storage` | both null. A `local` write fills `path_cache_storage` |

A 418-byte zip of three files went up and came back byte-identical, `sha1`
`3a7d0d1d348b9886c75f1f9849edf8f557e1b8d1` both ways, with all three members readable.

## Notes

- **The url is not the file.** It is minted per read and signed for 900 seconds, so persist
  `path["id"]`, the Attachment, and re-read the field when the bytes are wanted
  (`field_types/url`). Two reads of the same unchanged row return two different strings.
- **`local_path_mac` is absent, not null.** A reader doing `(path or {}).get("local_path_mac")`
  returns `None` for every row published this way and reports it as a row with no path. Branch on
  `link_type` first: an `upload` or `web` value has `url`, a `local` value has the three platform
  paths and no `url` (`field_types/url`).
- **Deleting the PublishedFile leaves the Attachment.** `DELETE /entity/published_files/<id>` answered
  204 and `GET /entity/attachments/<id>` still answered 200 with the filename. The bytes stay on the
  site until the Attachment is deleted by id, which is the same accumulation a `local` path write
  causes on every rewrite (`recipes/004_register_published_file`).
- `file_size` on that Attachment reads `null` even after the bytes landed, so it distinguishes nothing
  (`endpoints/put_links_upload`).
- Step three answers 201 whether or not step two ever ran, and its body is a single space rather than
  JSON (`endpoints/post_links_complete_upload`). Fetch the url to prove the bytes exist.
- **A `file://` url is a third shape, and it moves nothing.** `{"url": "file:///…", "name": …}` on the
  same field answers 201 on create and 200 on a `PUT`, at `link_type` `web`, and stores the string
  only: no bytes reach the site and any reader without that mount sees a dead link. A space in the url
  is refused, so percent-encode before sending (`field_types/url`).
- The three-call flow needs no LocalStorage row to exist on the site at all, and no
  `published_file_type`. What it costs is that the file is one object: a sequence has to be archived
  first, and the archive is what a consumer downloads.
