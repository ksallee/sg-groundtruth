---
endpoint: PUT <links.upload>
coverage: measured
tags: [upload, media, attachment, silent]
scope: api
measured: sandbox project written
verdict: Step two, to storage rather than to Flow PT, with no Authorization header. It is the only step that moves bytes, and skipping it still lets step three answer 201.
---

# PUT <links.upload>

**Params**

| part | value |
|---|---|
| URL | `links.upload` from step one, verbatim. Presigned, and it expires |
| method | `PUT` |
| body | the raw bytes |
| `Authorization` | **do not send one.** The signature covers the request; a bearer token is not part of it |

**Sample requests**

```python
import requests
put = requests.put(links["upload"], data=open("clip.mov", "rb"))
print(put.status_code, put.headers.get("ETag"))
```

Empty body. The headers are the receipt:

```
200   Content-Length: 0   ETag: "9ef430cc6d563983f362487a051169cd"
```

The `ETag` is the md5 of what was sent, so it verifies the transfer without a second call:

```python
import hashlib
assert put.headers["ETag"].strip('"') == hashlib.md5(open("clip.mov", "rb").read()).hexdigest()
```

**Response codes**

| status | when |
|---|---|
| 200 | stored |
| 403 | the signature has expired |

**Edge cases**

- **Skipping this step is not detected.** Going straight from step one to step three answers 201 and
  creates a real Attachment row over an object that was never written. `file_size` reads `null` for that
  row and for a good one, so it cannot tell them apart: only fetching the stored file proves it exists.
- The URL is presigned and short-lived. Mint it, use it, and never persist it.
- This is the only step that does not go to Flow PT at all.

**Links**

- `endpoints/get_entity_type_id_field_upload`
- `endpoints/post_links_complete_upload`
- `findings/039_upload_silent_failures`
- `field_types/url`