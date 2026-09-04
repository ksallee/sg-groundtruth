---
intent: Take media off one Version and put the same bytes on another, which is what every sync, transfer and hand-off does
tags: [write, version, media, upload, attachment, url, image, async]
endpoints: [GET /entity/<type>/<id>, PUT /entity/<type>/<id>, GET /entity/<type>/<id>/<field>/_upload, PUT <links.upload>, POST <links.complete_upload>]
scope: api
measured: the first sample project holding media, copied onto a sandbox project Version
---

# 006_media_round_trip

There is no server-side copy. Nothing moves an upload between two Versions, so a transfer is a
download and a fresh three-call upload (probe 013), with the bytes passing through the client.

## The renditions

One upload produces up to five assets on five fields, each its own Attachment. On the probed site, a
Version whose master was a `.jpg`:

| field | data type | read as | holds | `name` key | filename in the signed query |
|---|---|---|---|---|---|
| `sg_uploaded_movie` | `url` | object, 6 keys | the master, `image/jpeg` | `bunny.jpg` | `bunny.jpg` |
| `sg_uploaded_movie_mp4` | `url` | object, 6 keys | the transcode the review player streams, `video/mp4` | `<hash>_bunny.mp4` | `<hash>_bunny.mp4` |
| `sg_uploaded_movie_webm` | `url` | `null` | never populated on the probed site (probe 022) | | |
| `sg_uploaded_movie_image` | `url` | object, 6 keys | a poster frame, `image/jpg` | `<hash>_bunny_2Dlod.jpeg` | `<hash>_bunny_2Dlod.jpeg` |
| `image` | `image` | bare string | the thumbnail | absent | `<hash>_bunny_t.jpg` |
| `filmstrip_image` | `image` | bare string | the scrub strip | absent | `<hash>_bunny_filmstrip.jpg` |

`sg_uploaded_movie_frame_rate` and `sg_uploaded_movie_transcoding_status` describe the transcode, not
the media, and both survive every clear. Read `link_type` before `url`: a `local` object has no `url`
key at all (`field_types/url`).

**Take the transcode, not the master.** `sg_uploaded_movie_mp4` is what the review player already
streams and the one format the far end opens without a codec question. The master is whatever the
artist uploaded: on the probed Version it is a `.jpg`, so a job that syncs "the movie" from
`sg_uploaded_movie` moves a still image.

## Call

```python
import os
import tempfile
from urllib.parse import parse_qs, unquote, urlparse

import requests

# get/put/post are FPT.get/.put/.post from src/sg_groundtruth/client.py; they add auth and the /api/v1 prefix.
# The caller supplies SOURCE_ID and TARGET_ID.
JSON = {"Content-Type": "application/json"}
RENDITIONS = ["sg_uploaded_movie", "sg_uploaded_movie_mp4", "sg_uploaded_movie_webm",
              "sg_uploaded_movie_image", "image", "filmstrip_image"]
PREFER = ["sg_uploaded_movie_mp4", "sg_uploaded_movie_webm", "sg_uploaded_movie_image",
          "sg_uploaded_movie", "image"]


def read(version_id, fields):
    r = get(f"/entity/versions/{version_id}", params={"fields": ",".join(fields)})
    return r.json()["data"]["attributes"]


def rendition_url(value):
    """image is a bare string, a url field is an object, and a link_type local object has no url."""
    if isinstance(value, str):
        return None if "/images/status/transient/" in value else value      # still transcoding
    if isinstance(value, dict) and value.get("link_type") != "local":
        return value.get("url")
    return None


def filename_of(url, value):
    """The signature signs response-content-disposition, so the filename is in the query string.
    An image field has no name key, so that query parameter is the only place its extension exists."""
    cd = (parse_qs(urlparse(url).query).get("response-content-disposition") or [""])[0]
    for part in cd.split(";"):
        part = part.strip()
        for key in ("filename*=UTF-8''", "filename="):
            if part.startswith(key):
                return unquote(part[len(key):].strip('"'))
    return value.get("name") if isinstance(value, dict) else None


# 1. read the source and pick the transcode over the master
a = read(SOURCE_ID, RENDITIONS)
field = next(f for f in PREFER if rendition_url(a.get(f)))
url = rendition_url(a[field])
filename = filename_of(url, a[field])

# 2. download. The url is signed for X-Amz-Expires seconds from X-Amz-Date; re-read the field for a
#    fresh one instead of caching the string. GET only: the signature covers no other method.
fd, tmp = tempfile.mkstemp(prefix="fpt_media_")
os.close(fd)
try:
    r = requests.get(url, timeout=300)
    r.raise_for_status()
    with open(tmp, "wb") as fh:
        fh.write(r.content)

    # 3. clear all six renditions on the target by name. Clearing sg_uploaded_movie alone leaves the
    #    other five serving the file you replaced.
    put(f"/entity/versions/{TARGET_ID}", headers=JSON, json={f: None for f in RENDITIONS})

    # 4. upload: init, PUT the bytes to the presigned link, complete (probe 013)
    b = get(f"/entity/versions/{TARGET_ID}/sg_uploaded_movie/_upload",
            params={"filename": filename}).json()
    with open(tmp, "rb") as fh:
        requests.put(b["links"]["upload"], data=fh.read(), timeout=300)      # presigned S3
    post(b["links"]["complete_upload"], headers=JSON,                        # upload_data required, empty
         json={"upload_info": b["data"], "upload_data": {}})
finally:
    os.unlink(tmp)          # the temp file goes even when the upload raises
```

Poll `sg_uploaded_movie_transcoding_status` until it leaves 0 if the far end needs the mp4.

## Response

```
1. source Version, 5 of 6 renditions filled, transcoding_status 1
   chosen sg_uploaded_movie_mp4, Attachment 1431, video/mp4

2. the signed url, query parameters:
     X-Amz-Algorithm X-Amz-Credential X-Amz-Date X-Amz-Expires X-Amz-Security-Token
     X-Amz-Signature X-Amz-SignedHeaders response-content-disposition
     x-amz-meta-user-id x-amz-meta-user-type
   read 1  X-Amz-Date=20260902T192216Z  X-Amz-Expires=847
   read 2  X-Amz-Date=20260902T192216Z  X-Amz-Expires=900   different string, one second later
   HEAD -> 403 application/xml          GET -> 200 video/mp4 158170 bytes

3. target Version, seeded with a 16x16 png so a re-sync has stale state to fix
     after ~40s  transcoding_status=2, every derived field null: the png was refused
   first sync, the 158170-byte mp4:
     after ~40s  transcoding_status=1, _mp4 <hash2>_<hash>_bunny.mp4, image and filmstrip_image set

4. PUT {"sg_uploaded_movie": null}                    -> 200
     sg_uploaded_movie null; _mp4, image, filmstrip_image still serving the old file
     frame_rate '25.0'   transcoding_status 1
   PUT all six null                                   -> 200
     all six null; frame_rate '25.0'   transcoding_status 1   still stale

5. upload the same bytes back                         -> PUT 200, complete 201
   immediately: sg_uploaded_movie set, _mp4 null, image /images/status/transient/,
                transcoding_status 0, frame_rate still '25.0' from the previous file
   after ~40s:  transcoding_status 1, _mp4 <hash3>_<hash>_bunny.mp4 (a second transcode of a transcode),
                sg_uploaded_movie_image still null
   GET what came back -> 200 binary/octet-stream 158170 bytes, byte-identical to what was sent

6. Attachments linked to the target: 5, for one file synced twice
```

## Notes

- **No server-side copy, and no reference to reuse.** The only value `sg_uploaded_movie` accepts is an
  object holding a `url` (`field_types/url`). Wrapping the source's presigned url in
  `{"url": …, "name": …}` answers 200 and stores a `link_type: web` link that dies with the signature,
  with no transcode and no thumbnail. Moving the bytes is the only transfer that survives.
- **The signature expires, and re-reading the field is the fix.** The window is `X-Amz-Expires`
  seconds from `X-Amz-Date`, and the number is not a constant: two reads one second apart returned
  847 and 900. Both reads returned different strings for the same Attachment, so a client that
  outlives its url re-reads the field and starts the transfer again rather than retrying the string.
  A string held 706 seconds past expiry 403s `AccessDenied` (`field_types/image`). Persist the
  Attachment id or the Version id; never the url.
- **`HEAD` 403s** with an `application/xml` body. The signature covers `GET` alone, so size and type
  come from the `GET` response or from `GET /entity/attachments/{id}`.
- **Where the extension lives depends on the field.**

  | field | source of the filename |
  |---|---|
  | `sg_uploaded_movie` and the three derived `url` fields | `name`, and `response-content-disposition` agrees with it |
  | `image`, `filmstrip_image` | `response-content-disposition` only: an `image` field is a bare string with no `name` |

  Parse the query parameter in both cases and the same code handles all six. Uploading with the wrong
  extension is accepted, so nothing downstream corrects it.
- **Clearing is per field, and two readings never clear.**

  | after | `sg_uploaded_movie` | `_mp4` | `image`, `filmstrip_image` | `_frame_rate` | `_transcoding_status` |
  |---|---|---|---|---|---|
  | `PUT {"sg_uploaded_movie": null}` | null | old file | old file | `'25.0'` | 1 |
  | `PUT` all six null | null | null | null | `'25.0'` | 1 |
  | the new upload, before the transcode | new file | null | `/images/status/transient/` | `'25.0'` | 0 |
  | the new upload, after the transcode | new file | new file | new file | `'25.0'` | 1 |

  `_frame_rate` and `_transcoding_status` are a `float` and a `number`, not `url` fields, and neither
  `null` nor the upload resets them. Between the clear and the transcode landing they describe a file
  the Version no longer holds, exactly as a replacement does (probe 022). `_frame_rate` reads back as
  a JSON string (`field_types/float`).
- **`sg_uploaded_movie_transcoding_status`** was 0 in flight, 1 after the transcode landed, and 2 for
  a 16x16 png the transcoder refused, which left every derived field null. Treat 1 as "a transcode
  finished", never as "this media is transcoded": 1 was the reading throughout the clear, when the
  Version held no media at all.
- **The target does not end up with the source's rendition set.** Uploading the source's mp4 produced
  a second transcode of an already transcoded file (`<hash3>_<hash>_bunny.mp4`), a thumbnail and a
  filmstrip, and left `sg_uploaded_movie_image` null, which the source had. Compare Versions on the
  file you sent, not on which fields are filled.
- **Attachments accumulate and the clear does not touch them.** One file synced twice left 5
  Attachments on the target: the seed, both uploads and both transcodes. `PUT … null` unlinks nothing;
  `DELETE /entity/attachments/{id}` does, and only the rows you made.
- **The download's `Content-Type` is not the media's.** Reading the round-tripped file back served
  `binary/octet-stream` while the field reads `video/mp4`. Trust the field's `content_type`.
- Wrap the download so the temp file is removed even when the upload raises. A failed sync that keeps
  its scratch file fills the disk of whatever runs the job.
