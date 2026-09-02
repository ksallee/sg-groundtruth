"""Q: what is the full media upload round trip, start to finish?"""
import base64
import json

import requests

import _lib

env = _lib.load_env()
c = _lib.client()
VERSION_ID = 26263
rows = []

# 16x16 red PNG, so the probe needs no image library
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAJ0lEQVR42mP8z8BQz0AEYBxVSF+F"
    "jIyM/xnpoxCfwlGFoy4cVUgPhQCq0Ags7T6l4wAAAABJRU5ErkJggg==")


def step(label, fn):
    try:
        out = fn()
        rows.append(f"  {label}: {out}")
        return out
    except Exception as e:
        rows.append(f"  {label}: EXCEPTION {e}")
        return None


for field, desc in [("image", "thumbnail"), ("sg_uploaded_movie", "media field")]:
    rows.append(f"\n=== {desc} via /{field}/_upload")
    r = c.get(f"/entity/versions/{VERSION_ID}/{field}/_upload", params={"filename": "probe.png"})
    if not r.ok:
        rows.append(f"  init failed {r.status_code}: {r.text[:200]}")
        continue
    body = r.json()
    rows.append(f"  1. init 200 — data keys: {sorted(body['data'])}")
    rows.append(f"     link keys: {sorted(body['links'])}")
    rows.append(f"     upload_type={body['data'].get('upload_type')} storage={body['data'].get('storage_service')} "
                f"multipart={body['data'].get('multipart_upload')}")

    put = requests.put(body["links"]["upload"], data=PNG, timeout=60)
    rows.append(f"  2. PUT to presigned S3 -> {put.status_code} (etag {put.headers.get('ETag')})")

    complete = body["links"].get("complete_upload")
    if not complete:
        rows.append("  3. no complete_upload link — upload may be final after PUT")
    else:
        cr = c.post(complete, json={"upload_info": body["data"], "upload_data": {}},
                    headers={"Content-Type": "application/json"})
        detail = "" if cr.ok else json.dumps(cr.json())[:250]
        rows.append(f"  3. POST {complete} -> {cr.status_code} {detail}")

# read back
v = c.get(f"/entity/versions/{VERSION_ID}",
          params={"fields": "code,image,sg_uploaded_movie,sg_uploaded_movie_type"}).json()["data"]
_lib.register_from(v)
rows.append("\n=== read back")
rows.append(f"  attributes: {json.dumps(v.get('attributes'))[:300]}")
rows.append(f"  relationships: {sorted(v.get('relationships', {}))}")

actual = "\n".join(rows)
_lib.record("013_upload_media", "GET /entity/versions/{id}/{field}/_upload -> PUT S3 -> POST complete_upload",
            "Media upload is a multi-step presigned flow.",
            actual,
            "Three steps, no shortcuts. 1) GET /entity/versions/{id}/{field}/_upload?filename=X returns "
            "links.upload (presigned S3) and links.complete_upload. 2) PUT the raw bytes to links.upload. "
            "3) POST links.complete_upload with {'upload_info': <the data block from step 1 verbatim>, "
            "'upload_data': {}} -> 201. Omitting upload_data 400s with 'upload_data is missing' even though it "
            "is empty. Field choice sets upload_type: /image/ is a Thumbnail, any other field is an Attachment. "
            "Transcoding is ASYNC - reading the field straight back returns a placeholder under "
            "/images/status/transient/, so detect that path prefix rather than treating it as the real media.",
            env, tags=("write", "upload", "media", "attachment", "version", "async"))
print(actual)
