"""Q: what changes in the upload handshake when one PUT is not enough?

Findings 013 and 039 cover the three-call handshake: GET `_upload`, PUT the presigned URL, POST
`links.complete_upload`. That path returns `multipart_upload: false` and one `links.upload`. This
probe asks what turns it true, what the extra calls take, and what has to be cleaned up when a
transfer is abandoned halfway.

Read-only by default: the OpenAPI document the site publishes is the authority for parameter names,
so the ungated half prints the contract it declares for each of these paths.

`--write` runs the real handshakes in the sandbox project. Every multipart init opens an S3 upload
that outlives the request, so every init here is either completed or aborted, including the ones
whose completion the probe expects to fail. Test bytes are `os.urandom`, in memory, never written to
the repo.
"""
import json
import os

import requests

import _lib

env = _lib.load_env()
c = _lib.client()
MiB = 1024 * 1024
UPLOAD_PATHS = ("/entity/{entity}/{record_id}/_upload",
                "/entity/{entity}/{record_id}/_upload/multipart",
                "/entity/{entity}/{record_id}/_upload/multipart_abort",
                "/entity/{entity}/{record_id}/{field_name}/_upload",
                "/entity/{entity}/{record_id}/{field_name}/_upload/multipart",
                "/entity/{entity}/{record_id}/{field_name}/_upload/multipart_abort",
                "/transcode/attachment_metadata/{record_id}")
rows = []
secrets = []


def out(s=""):
    """One line of the report, with every opaque upload id masked.

    An S3 upload id is 150-odd characters of noise that also appears inside `get_next_part`, so a
    reader learns its shape from its length and nothing from its value.
    """
    s = str(s)
    for i, v in enumerate(secrets):
        s = s.replace(v, f"<upload_id {len(v)} chars>")
    rows.append(s)


def head(t):
    out(f"\n\n===== {t} =====")


def mask(upload_id):
    if upload_id and upload_id not in secrets:
        secrets.append(upload_id)
    return upload_id


# ---------------------------------------------------------------- read-only

head("what the site's own spec declares")
spec = c.get("/spec.json").json()
for p in UPLOAD_PATHS:
    ops = spec["paths"].get(p)
    if not ops:
        out(f"\n-- {p}: absent from the spec")
        continue
    for method, op in ops.items():
        args = ", ".join(
            f"{a['name']} ({a['in']}{'' if a.get('required') else ', optional'})"
            for a in op.get("parameters", []))
        out(f"\n-- {method.upper()} {p}\n   {op['summary']}\n   {args or 'no parameters'}")
        body = op.get("requestBody", {}).get("content", {}).get("application/json", {})
        req = body.get("schema", {}).get("required")
        if req:
            out(f"   body requires: {req}")

info_props = (spec["paths"]["/entity/{entity}/{record_id}/{field_name}/_upload"]["post"]
              ["requestBody"]["content"]["application/json"]["schema"]
              ["properties"]["upload_info"])
out(f"\n-- upload_info on the complete call\n   required: {info_props['required']}"
    f"\n   properties: {sorted(info_props['properties'])}")
out(f"   etags: {info_props['properties']['etags']['description']}")

_lib.emit("044_multipart_upload", "\n".join(rows), env)
READ_ONLY = len(rows)

# ---------------------------------------------------------------- writes

if _lib.writes_allowed():
    SANDBOX = _lib.sandbox_id(c, env)
    with _lib.Created(c) as made:
        v = c.post("/entity/versions", json={"project": {"type": "Project", "id": SANDBOX},
                                             "code": "zzprobe_044"}).json()["data"]
        VERSION = made.add("versions", v["id"])
        FIELD = f"/entity/versions/{VERSION}/sg_uploaded_movie/_upload"

        def init(path=FIELD, filename="zzprobe_044.bin", **extra):
            b = c.get(path, params={"filename": filename, **extra}).json()
            mask(b.get("data", {}).get("upload_id"))
            return b.get("data", {}), b.get("links", {})

        def abort(info, path=FIELD):
            return c.post(f"{path}/multipart_abort", json=info)

        def transfer(sizes, path=FIELD, filename="zzprobe_044.bin", upload_data=None):
            """One multipart transfer end to end. Returns the completion response."""
            info, links = init(path, filename, multipart_upload="true")
            etags, up, nxt = [], links["upload"], links["get_next_part"]
            for i, size in enumerate(sizes):
                part = requests.put(up, data=os.urandom(size), timeout=300)
                etags.append(part.headers["ETag"].strip('"'))
                if i + 1 < len(sizes):
                    l2 = c.get(nxt).json()["links"]
                    up, nxt = l2["upload"], l2["get_next_part"]
            r = c.post(links["complete_upload"],
                       json={"upload_info": dict(info, etags=etags),
                             "upload_data": upload_data or {}})
            out(f"\n-- parts {sizes}, {sum(sizes)} bytes"
                f"\n   POST <links.complete_upload>  etags={len(etags)}"
                f"\n   -> {r.status_code}  {r.text[:200]!r}")
            if not r.ok:
                out(f"   aborted: {abort(info).status_code}")
            return r, info

        head("GET /entity/<type>/<id>/<field>/_upload  ?multipart_upload=true")
        single, single_links = init()
        out(f"\n-- without the parameter\n   data: {json.dumps(single)}"
            f"\n   links: {sorted(single_links)}")
        multi, multi_links = init(multipart_upload="true")
        out(f"\n-- multipart_upload=true\n   data: {json.dumps(multi)}"
            f"\n   links: {sorted(multi_links)}")
        out(f"   get_next_part: {multi_links['get_next_part']}")
        out(f"   abort it unused -> {abort(multi).status_code}")

        head("the same switch on the other two forms")
        thumb, thumb_links = init(f"/entity/versions/{VERSION}/image/_upload",
                                  "zzprobe_044.png", multipart_upload="true")
        out(f"\n-- image, a Thumbnail\n   upload_type={thumb['upload_type']} "
            f"multipart_upload={thumb['multipart_upload']}  links: {sorted(thumb_links)}")
        out(f"   abort -> {abort(thumb, f'/entity/versions/{VERSION}/image/_upload').status_code}")
        note = c.post("/entity/notes", json={"project": {"type": "Project", "id": SANDBOX},
                                             "subject": "zzprobe_044"}).json()["data"]
        NOTE = made.add("notes", note["id"])
        NOTE_PATH = f"/entity/notes/{NOTE}/attachments/_upload"
        field_less, fl_links = init(NOTE_PATH, multipart_upload="true")
        out(f"\n-- no field in the path\n   upload_type={field_less['upload_type']} "
            f"multipart_upload={field_less['multipart_upload']}  links: {sorted(fl_links)}")
        out(f"   abort -> {abort(field_less, NOTE_PATH).status_code}")

        head("GET /entity/<type>/<id>/<field>/_upload/multipart")
        for label, params in (
            ("nothing at all", {}),
            ("filename alone", {"filename": "zzprobe_044.bin"}),
            ("everything but upload_id", {"filename": "zzprobe_044.bin", "part_number": 2,
                                          "upload_type": "Attachment",
                                          "timestamp": "2026-09-04T04:35:50Z"}),
            ("an upload_id that was never minted",
             {"filename": "zzprobe_044.bin", "part_number": 2, "upload_type": "Attachment",
              "timestamp": "2026-09-04T04:35:50Z", "upload_id": "nope"}),
        ):
            r = c.get(f"{FIELD}/multipart", params=params)
            out(f"\n-- {label}\n   -> {r.status_code}  {r.text[:300]}")

        head("one part is a legal multipart upload")
        r, _ = transfer([10])
        val = c.get(f"/entity/versions/{VERSION}",
                    params={"fields": "sg_uploaded_movie"}).json()["data"]["attributes"]
        att = val["sg_uploaded_movie"]
        made.add("attachments", att["id"])
        got = requests.get(att["url"], timeout=120)
        out(f"   Attachment {att['id']}, GET this_file -> {got.status_code}, "
            f"{len(got.content)} bytes")

        head("the floor on every part but the last")
        transfer([1024, 1024])
        transfer([5 * MiB - 1, 17])
        r, _ = transfer([5 * MiB, 17], upload_data={"display_name": "zzprobe_044 display"})
        att2 = c.get(f"/entity/versions/{VERSION}",
                     params={"fields": "sg_uploaded_movie"}).json()["data"]["attributes"][
                         "sg_uploaded_movie"]
        ATTACHMENT = made.add("attachments", att2["id"])
        got = requests.get(att2["url"], timeout=300)
        out(f"   GET this_file -> {got.status_code}, {len(got.content)} bytes")
        full = c.get(f"/entity/attachments/{ATTACHMENT}").json()["data"]["attributes"]
        out("   attachment: " + json.dumps({k: full.get(k) for k in
                                            ("filename", "original_fname", "display_name",
                                             "file_size", "file_extension")}))

        head("completing a multipart without etags")
        info, links = init(multipart_upload="true")
        requests.put(links["upload"], data=os.urandom(1024), timeout=60)
        r = c.post(links["complete_upload"], json={"upload_info": info, "upload_data": {}})
        out(f"\n-- upload_info as returned, etags left out\n   -> {r.status_code}  {r.text[:300]}")
        out(f"   aborted: {abort(info).status_code}")

        head("POST /entity/<type>/<id>/<field>/_upload/multipart_abort")
        info, _ = init(multipart_upload="true")
        r = c.post(f"{FIELD}/multipart_abort", json={"upload_info": info, "upload_data": {}})
        out(f"\n-- the body shape the spec declares\n   "
            f"{{\"upload_info\": ..., \"upload_data\": {{}}}}\n   -> {r.status_code}  {r.text[:300]}")
        r = c.post(f"{FIELD}/multipart_abort", params=info)
        out(f"\n-- the same six keys as query parameters, no body\n   -> {r.status_code}  "
            f"{r.text[:200]}")
        r = abort(info)
        out(f"\n-- upload_info flat at the top level\n   -> {r.status_code}  {r.text[:120]!r}")
        r = abort(info)
        out(f"\n-- the same abort a second time\n   -> {r.status_code}  {r.text[:200]}")
        single2, _ = init()
        r = abort(single2)
        out(f"\n-- an init that was never multipart\n   -> {r.status_code}  {r.text[:200]}")

        head("PUT /entity/<type>/<id>/<field>/_upload")
        r = c.put(FIELD, params={"filename": "zzprobe_044.bin"}, data=b"zzprobe_044")
        out(f"\n-- the Flow PT path, not the presigned link\n   -> {r.status_code}  {r.text[:300]}")
        r = c.put(NOTE_PATH, params={"filename": "zzprobe_044.bin"}, data=b"zzprobe_044")
        out(f"\n-- the same, no field in the path\n   -> {r.status_code}  {r.text[:300]}")
        out(f"\n-- storage_service on this site: {single['storage_service']!r}, so links.upload "
            f"points at S3 and this route is never the one a client calls")

        head("POST /transcode/attachment_metadata/<id>")
        before = c.get(f"/entity/attachments/{ATTACHMENT}").json()["data"]["attributes"]
        meta = {"width": 1920, "height": 1080, "display_aspect_ratio": 1.7778,
                "frame_rate": 24.0, "nb_frames": 1440, "start_frame": 7}
        r = c.post(f"/transcode/attachment_metadata/{ATTACHMENT}", json=meta)
        out(f"\n-- every documented key\n   body={json.dumps(meta)}"
            f"\n   -> {r.status_code} {r.headers.get('Content-Type', '')}  {r.text[:80]!r}")
        after = c.get(f"/entity/attachments/{ATTACHMENT}").json()["data"]["attributes"]
        changed = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
        out(f"   attachment fields that changed: {changed}")
        out(f"   metadata field: {after.get('metadata')!r}")
        for label, aid, body in (
            ("a width that is not an integer", ATTACHMENT, {"width": "wide"}),
            ("a key the schema does not name", ATTACHMENT, {"nope": 1}),
            ("an empty body", ATTACHMENT, {}),
            ("an id no Attachment has", 999999999, meta),
            ("the Version id, not the Attachment id", VERSION, meta),
        ):
            r = c.post(f"/transcode/attachment_metadata/{aid}", json=body)
            out(f"\n-- {label}\n   -> {r.status_code}  {r.text[:200]!r}")

    _lib.emit("044_multipart_upload writes", "\n".join(rows[READ_ONLY:]), env)
