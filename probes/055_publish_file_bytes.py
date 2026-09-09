"""Q: can a PublishedFile carry its own bytes, with no LocalStorage row anywhere?

Recipe 004 only ever wrote `path` as {local_path} or {relative_path, local_storage}, both of which
need a storage root the caller can reach. `path` is data_type url, and probe 013's three-call upload
flow is addressed by field, so the question is whether `path` answers it and what the row reads back
as afterwards. The second half is the third shape: {"url": "file:///…", "name": …}, which the site
returns on rows it already holds and which nothing has written over REST.
"""
import hashlib
import io
import json
import urllib.parse
import zipfile

import requests

import _lib

env = _lib.load_env()
c = _lib.client()
JSON = {"Content-Type": "application/json"}
rows = []

if not _lib.writes_allowed():
    raise SystemExit("055_publish_file_bytes writes to the site; re-run with --write")


def err(r):
    """The error body, whole."""
    try:
        return json.dumps(r.json().get("errors", r.json()))
    except ValueError:
        return repr(r.text)


def expiry(url):
    """The signed lifetime, off the query string, without printing the signature."""
    q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    return {k: q[k][0] for k in ("X-Amz-Expires", "X-Amz-Date") if k in q}


# An image sequence, zipped, so the round trip carries structure and not just bytes.
buf = io.BytesIO()
with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
    for i in range(1, 4):
        z.writestr(f"zzprobe_055.{i:04d}.exr", b"not-an-exr-" + str(i).encode() * 64)
PAYLOAD = buf.getvalue()
SENT_SHA1 = hashlib.sha1(PAYLOAD).hexdigest()
FILENAME = "zzprobe_055_seq.zip"

SANDBOX = _lib.sandbox_id(c, env)

with _lib.Created(c) as made:

    def keep_attachment(path_value):
        """Every accepted path write mints an Attachment that outlives the row pointing at it.
        Deleted last: Created unwinds in reverse, so index 0 goes after the PublishedFiles."""
        row = ("attachments", (path_value or {}).get("id"))
        if isinstance(path_value, dict) and row[1] and row not in made.rows:
            made.rows.insert(0, row)

    def path_of(pf_id, fields="path,path_cache,path_cache_storage"):
        r = c.get(f"/entity/published_files/{pf_id}", params={"fields": fields})
        _lib.note_from(r.json())
        return r.json()["data"]["attributes"]

    # --- 1. a PublishedFile with no path at all -------------------------------------------
    r = c.post("/entity/published_files", headers=JSON, json={
        "project": {"type": "Project", "id": SANDBOX},
        "code": "zzprobe_055_seq.v001.zip", "name": "zzprobe_055_seq.zip", "version_number": 1})
    rows.append(f"=== 1. create with no path -> {r.status_code}"
                + ("" if r.ok else f" {err(r)}"))
    pf = made.add("published_files", r.json()["data"]["id"])
    rows.append(f"  path on the 201: {json.dumps(r.json()['data']['attributes'].get('path'))}")

    # --- 2. the three-call upload, addressed at `path` -----------------------------------
    r = c.get(f"/entity/published_files/{pf}/path/_upload", params={"filename": FILENAME})
    rows.append(f"\n=== 2. GET /entity/published_files/<id>/path/_upload -> {r.status_code}"
                + ("" if r.ok else f" {err(r)}"))
    info, links = r.json()["data"], r.json()["links"]
    rows.append(f"  data:  {json.dumps(info)}")
    rows.append(f"  links: {sorted(links)}  complete_upload={links.get('complete_upload')!r}")
    rows.append(f"  upload url signed for: {expiry(links['upload'])}")

    put = requests.put(links["upload"], data=PAYLOAD, timeout=120)
    etag = put.headers.get("ETag", "").strip('"')
    rows.append(f"  PUT the bytes ({len(PAYLOAD)} b) -> {put.status_code} etag={etag!r} "
                f"md5-matches={etag == hashlib.md5(PAYLOAD).hexdigest()}")

    cr = c.post(links["complete_upload"], headers=JSON,
                json={"upload_info": info, "upload_data": {}})
    rows.append(f"  POST complete_upload -> {cr.status_code} body={cr.text!r}")

    # --- 3. what the row reads back as ---------------------------------------------------
    attrs = path_of(pf)
    p = attrs.get("path") or {}
    keep_attachment(p)
    rows.append("\n=== 3. read back")
    rows.append("  path keys: " + json.dumps(sorted(p)))
    rows.append("  path: " + json.dumps({k: v for k, v in p.items() if k != "url"}))
    rows.append(f"  url present={'url' in p} signed for: {expiry(p.get('url') or '')}")
    for k in ("local_path_mac", "local_path_windows", "local_path_linux", "relative_path",
              "local_storage"):
        rows.append(f"  {k}: {'ABSENT' if k not in p else json.dumps(p[k])}")
    rows.append(f"  path_cache={attrs.get('path_cache')!r} "
                f"path_cache_storage={attrs.get('path_cache_storage')!r}")

    a = c.get(f"/entity/attachments/{p['id']}",
              params={"fields": "filename,file_size,attachment_links,this_file"})
    _lib.note_from(a.json())
    ad = a.json()["data"]["attributes"]
    rows.append(f"  GET /entity/attachments/{p['id']} -> {a.status_code} "
                f"filename={ad.get('filename')!r} file_size={ad.get('file_size')!r}")

    # --- 4. the bytes back ----------------------------------------------------------------
    g = requests.get(p["url"], timeout=120)
    got = hashlib.sha1(g.content).hexdigest()
    rows.append("\n=== 4. GET the url (no Authorization header)")
    rows.append(f"  {g.status_code} {len(g.content)} b  content-type={g.headers.get('Content-Type')!r}")
    rows.append(f"  sha1 sent={SENT_SHA1} back={got} identical={got == SENT_SHA1}")
    try:
        with zipfile.ZipFile(io.BytesIO(g.content)) as z:
            rows.append(f"  zip intact, members: {z.namelist()}")
    except Exception as e:  # noqa: BLE001
        rows.append(f"  zip unreadable: {e}")

    # two reads of the same row, to show the url is re-minted
    p2 = (path_of(pf, "path").get("path") or {})
    rows.append(f"  a second read returns a different url string: {p2.get('url') != p.get('url')}")

    # --- 5. does the Attachment outlive the PublishedFile? ---------------------------------
    d = c.delete(f"/entity/published_files/{pf}")
    made.rows = [row for row in made.rows if row != ("published_files", pf)]
    rows.append(f"\n=== 5. DELETE /entity/published_files/{pf} -> {d.status_code}")
    ga = c.get(f"/entity/attachments/{p['id']}", params={"fields": "filename"})
    rows.append(f"  GET the Attachment afterwards -> {ga.status_code} "
                + (json.dumps(ga.json()["data"]["attributes"]) if ga.ok else err(ga)))

    # --- 6. the file:/// shape on the same field -------------------------------------------
    rows.append("\n=== 6. {\"url\": \"file:///...\", \"name\": ...} on PublishedFile.path")
    ROOT = "file:///zzprobe_055_root"
    # A create, then one PUT per url. The two characters the site's own rows carry encoded are a
    # space and a narrow no-break space, so each goes in raw and percent-encoded.
    r = c.post("/entity/published_files", headers=JSON, json={
        "project": {"type": "Project", "id": SANDBOX}, "code": "zzprobe_055_file_url.v001.exr",
        "path": {"url": ROOT + "/plate.exr", "name": "zzprobe_055_plate.exr"}})
    rows.append(f"  POST create {{url, name}} -> {r.status_code}" + ("" if r.ok else f" {err(r)}"))
    pf2 = made.add("published_files", r.json()["data"]["id"])
    pp = r.json()["data"]["attributes"].get("path") or {}
    keep_attachment(pp)
    rows.append(f"    keys={sorted(pp)} link_type={pp.get('link_type')!r} "
                f"content_type={pp.get('content_type')!r} name={pp.get('name')!r}")
    rows.append(f"    url read back: {pp.get('url')!r}")

    NNBSP = "\u202f"
    for label, pathval in (
        ("{url} alone", {"url": ROOT + "/plain.exr"}),
        ("space, raw", {"url": ROOT + "/a folder/plate.exr"}),
        ("space, %20", {"url": ROOT + "/a%20folder/plate.exr"}),
        ("U+202F, raw", {"url": ROOT + "/nar" + NNBSP + "row.exr"}),
        ("U+202F, encoded", {"url": ROOT + "/nar%E2%80%AFrow.exr"}),
        ("https, space raw", {"url": "https://example.com/a folder/plate.exr"}),
        ("a bare string", ROOT + "/plate.exr"),
    ):
        rr = c.put(f"/entity/published_files/{pf2}", headers=JSON, json={"path": pathval})
        rows.append(f"  PUT {label:<18} -> {rr.status_code}" + ("" if rr.ok else f" {err(rr)}"))
        if not rr.ok:
            continue
        pp = path_of(pf2, "path").get("path") or {}
        keep_attachment(pp)
        rows.append(f"    link_type={pp.get('link_type')!r} name={pp.get('name')!r} "
                    f"url={pp.get('url')!r}")

        rows.append(f"    url read back: {pp.get('url')!r}")

    rows.append("\n=== cleanup")

_lib.emit("055_publish_file_bytes", "\n".join(rows), env)
