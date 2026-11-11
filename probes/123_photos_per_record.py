"""Q: where can several full-resolution photos per record live, on the on-set types and on a custom
entity, and which of the places keeps the original?

sg-onset uploads full-resolution photos, several per take. Five candidate places, each measured with
the same three JPEGs (6000x4000, made with ImageMagick into a temp dir, never into the repo):

  a. the record's `image` thumbnail field
  b. a `url` (File/Link) field, and a multi_entity field to Attachment, both custom, created here
  c. Attachments on a Note whose `note_links` names the record
  d. one Version per photo, `entity` the record, the file on `sg_uploaded_movie`
  e. one PublishedFile per photo, `entity` the record, the file on `path`

For each: does it hold several files, is the original byte-identical when read back, and how a
client reads it back. It also settles item 9 of issue 100: whether Version has `attachments`, and
which types answer the field-less `_upload`.

Read-only by default: the schema half. `--write` makes rows named `zzprobe_123_*` in the sandbox and
deletes them, and every Attachment the run made (found by id above the run's starting maximum and
`created_by` the probe's own user). It creates two schema fields on Slate, `sg_zzprobe_123_photo`
and `sg_zzprobe_123_photos`, and retires both before it exits. A retired name stays spent until the
Trash page is emptied in the web interface (probe 019).

    python probes/123_photos_per_record.py [--write]
"""
import hashlib
import json
import subprocess
import tempfile
import time
import urllib.parse
from pathlib import Path

import requests

import _lib

env = _lib.load_env()
c = _lib.client()
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
TYPES = ("Slate", "Camera", "MocapTake", "ShootDay", "Scene", "CustomEntity19", "Version", "Shot",
         "Note", "PublishedFile")
SLUG = {"Slate": "slates", "Camera": "cameras", "MocapTake": "mocap_takes", "ShootDay": "shoot_days",
        "Scene": "scenes", "CustomEntity19": "custom_entity19s", "Version": "versions", "Shot": "shots",
        "Note": "notes", "PublishedFile": "published_files"}
rows = []


def out(s=""):
    rows.append(str(s))


def head(t):
    out(f"\n===== {t}")


def errs(r):
    try:
        j = r.json()
    except ValueError:
        return repr(r.text[:300])
    return json.dumps(j.get("errors", j))[:600]


# ---------------------------------------------------------------- read-only
head("which types carry attachments, image, url fields; what Attachment and PublishedFile link to")
schema = c.get("/schema").json()["data"]
custom = sorted(t for t in schema if t.startswith("CustomEntity") and t[12:].isdigit())
CE = custom[0] if custom else None
if CE:
    SLUG[CE] = f"custom_entity{CE[12:]}s"
for t in TYPES:
    if t == "CustomEntity19":
        t = CE
    if not t:
        continue
    d = c.get(f"/schema/{t}/fields").json()["data"]
    att = d.get("attachments")
    imgs = sorted(f for f, v in d.items() if v["data_type"]["value"] == "image")
    urls = sorted(f for f, v in d.items() if v["data_type"]["value"] == "url")
    label = "<custom slot>" if t == CE else t
    out(f"  {label:<14} attachments: "
        + ("absent" if not att else f"{att['data_type']['value']} {att['properties'].get('valid_types', {}).get('value')}")
        + f"; image fields {imgs}; url fields {len(urls)}")
for t, f in (("Attachment", "attachment_links"), ("PublishedFile", "entity"), ("Version", "entity")):
    v = c.get(f"/schema/{t}/fields/{f}").json()["data"]
    vt = v["properties"]["valid_types"]["value"]
    out(f"  {t}.{f} valid_types names: {[x for x in vt if x in TYPES or x == CE]}")
r = c.get("/schema/Version/fields/attachments")
out(f"  GET /schema/Version/fields/attachments -> {r.status_code} {'' if r.ok else errs(r)}")

_lib.emit("123_photos_per_record", "\n".join(rows), env)
if not _lib.writes_allowed():
    raise SystemExit("\nread-only half done; --write runs the uploads in the sandbox")

# ---------------------------------------------------------------- photos
rows.clear()
tmp = Path(tempfile.mkdtemp(prefix="zzprobe_123_"))
PHOTOS = []
for i in range(3):
    p = tmp / f"zzprobe_123_photo{i + 1}.jpg"
    subprocess.run(["magick", "-size", "6000x4000", f"plasma:fractal", "-seed", str(i + 1),
                    "-quality", "92", str(p)], check=True)
    PHOTOS.append(p)
SHA = {p.name: hashlib.sha1(p.read_bytes()).hexdigest() for p in PHOTOS}
sizes = {p.name: p.stat().st_size for p in PHOTOS}


def dims(blob):
    f = tmp / "probe_read.bin"
    f.write_bytes(blob)
    r = subprocess.run(["magick", "identify", "-format", "%m %wx%h", str(f)], capture_output=True,
                       text=True)
    return r.stdout.strip() or "not an image"


def fetch(url):
    """Bytes behind a presigned URL, no Authorization header (field_types/url)."""
    g = requests.get(url, timeout=300)
    return g.status_code, g.content, g.headers.get("Content-Type")


def expiry(url):
    q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    return q.get("X-Amz-Expires", ["?"])[0]


def describe(url):
    if not url:
        return "no url"
    if "/images/status/transient/" in url:
        return "transient placeholder"
    st, blob, ct = fetch(url)
    sha = hashlib.sha1(blob).hexdigest()
    same = [n for n, s in SHA.items() if s == sha]
    return (f"GET {st} {len(blob)} b {ct} {dims(blob)}, "
            f"{'byte-identical to ' + same[0] if same else 'not any original'}")


def upload(path, photo, params=None):
    """The three calls of probe 013. Returns (init status, put status, complete status, body)."""
    i = c.get(f"{path}/_upload", params={"filename": photo.name, **(params or {})})
    if not i.ok:
        return i.status_code, None, None, errs(i)
    b = i.json()
    put = requests.put(b["links"]["upload"], data=photo.read_bytes(), timeout=600)
    cr = c.post(b["links"]["complete_upload"], json={"upload_info": b["data"], "upload_data": {}})
    return i.status_code, put.status_code, cr.status_code, b["links"]["complete_upload"]


def settle(slug, rid, field, tries=30):
    """Poll an image field until it stops reading the transient placeholder (probe 013)."""
    for _ in range(tries):
        v = c.get(f"/entity/{slug}/{rid}", params={"fields": field}).json()["data"]["attributes"][field]
        if v and "/images/status/transient/" not in v:
            return v
        time.sleep(5)
    return v


SB = _lib.sandbox_id(c, env)
PROJ = {"type": "Project", "id": SB}
ME = c.get("/entity/api_users", params={"filter[firstname]": env["FPT_API_SCRIPT_NAME"],
                                        "fields": "id"}).json()["data"]
ME_ID = ME[0]["id"] if ME else None
start_att = c.post("/entity/attachments/_search", headers=ARR, json={
    "filters": [], "fields": ["id"], "sort": "-id", "page": {"size": 1}}).json()["data"]
START_ATT = start_att[0]["id"] if start_att else 0
fields_made = []

with _lib.Created(c) as made:
    def new(t, **body):
        r = c.post(f"/entity/{SLUG[t]}", json={"project": PROJ, **body})
        assert r.status_code == 201, errs(r)
        return made.add(SLUG[t], r.json()["data"]["id"])

    slate = new("Slate", code="zzprobe_123_slate")
    out(f"photos: 3 JPEGs 6000x4000, {sorted(sizes.values())} bytes")

    # ------------------------------------------------ item 9 and the field-less upload
    head("field-less upload: GET /entity/<type>/<id>/_upload on each type")
    probe_rows = {"Slate": slate}
    for t in ("Camera", "MocapTake", "ShootDay", "Scene", CE, "Shot", "Version", "Note"):
        if not t:
            continue
        body = {"code": f"zzprobe_123_{t}"} if t != "Note" else {"subject": "zzprobe_123"}
        probe_rows[t] = new(t, **body)
    for t, rid in probe_rows.items():
        r = c.get(f"/entity/{SLUG[t]}/{rid}/_upload", params={"filename": "zzprobe_123.jpg"})
        label = "<custom slot>" if t == CE else t
        out(f"  {label:<14} -> {r.status_code} "
            + (f"complete_upload ends {r.json()['links']['complete_upload'].rsplit('/', 2)[-2]!r}"
               if r.ok else errs(r)))
    v = probe_rows["Version"]
    st = upload(f"/entity/versions/{v}", PHOTOS[0])
    q = c.post("/entity/attachments/_search", headers=ARR, json={
        "filters": [["attachment_links", "is", {"type": "Version", "id": v}]],
        "fields": ["id", "attachment_links"], "page": {"size": 10}}).json()["data"]
    vb = c.get(f"/entity/versions/{v}", params={"fields": "attachments"})
    out(f"  Version field-less upload {st[:3]}; Attachments with attachment_links=Version: {len(q)}; "
        f"GET ?fields=attachments -> {vb.status_code} keys "
        f"{sorted(vb.json()['data'].get('attributes', {}))}{sorted(vb.json()['data'].get('relationships', {}))}")

    # ------------------------------------------------ a. image
    head("a. the image field, twice on one Slate")
    for p in PHOTOS[:2]:
        st = upload(f"/entity/slates/{slate}/image", p)
        val = settle("slates", slate, "image")
        out(f"  upload {p.name} {st[:3]} -> image: {describe(val)}")
    fi = c.get(f"/entity/slates/{slate}", params={"fields": "filmstrip_image,image_source_entity"}).json()["data"]
    out(f"  filmstrip_image: {describe(fi['attributes'].get('filmstrip_image'))}")
    r = c.get(f"/entity/slates/{slate}/image")
    out(f"  GET /entity/slates/<id>/image -> {r.status_code} {json.dumps(r.json().get('data'))[:200] if r.ok else errs(r)}")
    q = c.post("/entity/attachments/_search", headers=ARR, json={
        "filters": [["id", "greater_than", START_ATT]], "fields": ["id", "filename", "attachment_links"],
        "page": {"size": 50}}).json()["data"]
    out(f"  Attachments made so far in this run: {len(q)} "
        f"{[(a['attributes'].get('filename')) for a in q]}")

    # ------------------------------------------------ b. custom url and multi_entity fields
    head("b. a custom url field and a multi_entity-to-Attachment field on Slate")

    def make_field(name, display, body):
        r = c.post("/schema/Slate/fields", json=body)
        if r.status_code == 400 and "retired" in r.text:
            r = c.post(f"/schema/Slate/fields/{name}", params={"revive": "true"})
            out(f"  {name} retired by an earlier run; revive -> {r.status_code}")
        else:
            out(f"  POST /schema/Slate/fields {body['data_type']} {display!r} -> {r.status_code} "
                + (r.json()["links"]["self"].rsplit("/", 1)[-1] if r.status_code == 201 else errs(r)))
        if r.status_code in (201, 204):
            fields_made.append(name)
            return True
        return False

    def prop(**kv):
        return [{"property_name": k, "value": vv} for k, vv in kv.items()]

    try:
        if make_field("sg_zzprobe_123_photo", "zzprobe 123 photo",
                      {"data_type": "url", "properties": prop(name="zzprobe 123 photo")}):
            for p in PHOTOS[:2]:
                st = upload(f"/entity/slates/{slate}/sg_zzprobe_123_photo", p)
                val = c.get(f"/entity/slates/{slate}",
                            params={"fields": "sg_zzprobe_123_photo"}).json()["data"]["attributes"]["sg_zzprobe_123_photo"]
                shown = {k: val[k] for k in val if k != "url"} if isinstance(val, dict) else val
                out(f"  upload {p.name} {st[:3]} -> {json.dumps(shown)}")
                out(f"    url: {describe(val.get('url') if isinstance(val, dict) else None)}")
        if make_field("sg_zzprobe_123_photos", "zzprobe 123 photos",
                      {"data_type": "multi_entity",
                       "properties": prop(name="zzprobe 123 photos", valid_types=["Attachment"])}):
            st = upload(f"/entity/slates/{slate}/sg_zzprobe_123_photos", PHOTOS[0])
            out(f"  upload straight to the multi_entity field -> {st}")
            held = c.get(f"/entity/slates/{slate}", params={"fields": "sg_zzprobe_123_photos"}).json()
            out(f"    field reads {json.dumps(held['data']['relationships'].get('sg_zzprobe_123_photos'))}")
    finally:
        pass

    # ------------------------------------------------ c. Note attachments
    head("c. one Note, note_links the Slate, three photos uploaded to it")
    note = new("Note", subject="zzprobe_123_photos", content="zzprobe_123",
               note_links=[{"type": "Slate", "id": slate}])
    for p in PHOTOS:
        out(f"  upload {p.name} -> {upload(f'/entity/notes/{note}', p)[:3]}")
    nb = c.get(f"/entity/notes/{note}", params={"fields": "attachments"}).json()["data"]
    atts = nb["relationships"]["attachments"]["data"] or []
    out(f"  Note.attachments: {len(atts)} rows")
    for a in atts:
        ar = c.get(f"/entity/attachments/{a['id']}",
                   params={"fields": "this_file,file_size,image,attachment_links"}).json()["data"]
        tf = ar["attributes"].get("this_file") or {}
        out(f"    {a['name']}: this_file {describe(tf.get('url'))}; url expires {expiry(tf.get('url') or '')}s")
        out(f"      attachment_links {[(x['type']) for x in ar['relationships']['attachment_links']['data']]}"
            f", image {describe(settle('attachments', a['id'], 'image', tries=12))}")
    q = c.post("/entity/notes/_search", headers=ARR, json={
        "filters": [["note_links", "is", {"type": "Slate", "id": slate}]],
        "fields": ["attachments"], "page": {"size": 10}}).json()["data"]
    out(f"  from the Slate: Notes with note_links=Slate {len(q)}, their attachments "
        f"{sum(len(n['relationships']['attachments']['data'] or []) for n in q)}")
    if "sg_zzprobe_123_photos" in fields_made:
        r = c.put(f"/entity/slates/{slate}", json={"sg_zzprobe_123_photos": [
            {"type": "Attachment", "id": a["id"]} for a in atts]})
        held = c.get(f"/entity/slates/{slate}", params={"fields": "sg_zzprobe_123_photos"}).json()
        out(f"  PUT those Attachments on Slate.sg_zzprobe_123_photos -> {r.status_code}; reads "
            f"{len(held['data']['relationships']['sg_zzprobe_123_photos']['data'] or [])} rows")
    r = c.put(f"/entity/attachments/{atts[0]['id']}", json={
        "attachment_links": [{"type": "Note", "id": note}, {"type": "Slate", "id": slate}]})
    out(f"  PUT Attachment.attachment_links += the Slate (not in valid_types) -> {r.status_code} "
        + ("" if r.ok else errs(r)))

    # ------------------------------------------------ d. one Version per photo
    head("d. one Version per photo, entity the Slate, file on sg_uploaded_movie")
    for p in PHOTOS[:2]:
        vv = new("Version", code=f"zzprobe_123_{p.stem}", entity={"type": "Slate", "id": slate})
        st = upload(f"/entity/versions/{vv}/sg_uploaded_movie", p)
        row = c.get(f"/entity/versions/{vv}", params={"fields": "sg_uploaded_movie"}).json()["data"]["attributes"]
        um = row["sg_uploaded_movie"] or {}
        out(f"  {p.name} {st[:3]} sg_uploaded_movie: {describe(um.get('url'))}")
        out(f"    image after transcode: {describe(settle('versions', vv, 'image'))}")
        a = c.get(f"/entity/attachments/{um.get('id')}", params={"fields": "attachment_links"})
        if a.ok:
            out(f"    the Attachment behind it: attachment_links "
                f"{[x['type'] for x in a.json()['data']['relationships']['attachment_links']['data']]}")
    q = c.post("/entity/versions/_search", headers=ARR, json={
        "filters": [["entity", "is", {"type": "Slate", "id": slate}]], "fields": ["code"],
        "page": {"size": 10}}).json()["data"]
    out(f"  from the Slate: Versions with entity=Slate {len(q)}")

    # ------------------------------------------------ e. one PublishedFile per photo
    head("e. one PublishedFile per photo, entity the Slate, file on path")
    for p in PHOTOS[:2]:
        r = c.post("/entity/published_files", json={"project": PROJ, "code": p.name,
                                                    "entity": {"type": "Slate", "id": slate}})
        out(f"  create {{project, code, entity: Slate}} -> {r.status_code} {'' if r.ok else errs(r)}")
        if r.status_code != 201:
            continue
        pf = made.add("published_files", r.json()["data"]["id"])
        st = upload(f"/entity/published_files/{pf}/path", p)
        row = c.get(f"/entity/published_files/{pf}", params={"fields": "path,entity"}).json()["data"]
        pv = row["attributes"]["path"] or {}
        out(f"  {p.name} {st[:3]} path keys {sorted(pv)}: {describe(pv.get('url'))}")
        out(f"    entity reads {(row['relationships']['entity']['data'] or {}).get('type')}; "
            f"image: {describe(settle('published_files', pf, 'image', tries=12))}")

    # ------------------------------------------------ cleanup of Attachments
    head("Attachments this run made, deleted after the rows")
    q = c.post("/entity/attachments/_search", headers=ARR, json={
        "filters": [["id", "greater_than", START_ATT]] +
                   ([["created_by", "is", {"type": "ApiUser", "id": ME_ID}]] if ME_ID else []),
        "fields": ["id", "filename"], "page": {"size": 100}}).json()["data"]
    out(f"  {len(q)} Attachments, filenames {sorted({a['attributes'].get('filename') for a in q})}")
    # the transcodes behind sg_uploaded_movie are Attachments too, named <hash>_zzprobe_123_*
    mine = [a["id"] for a in q if "zzprobe_123" in str(a["attributes"].get("filename") or "")]
    for aid in mine:
        made.rows.insert(0, ("attachments", aid))
    out(f"  {len(mine)} naming zzprobe_123 queued for deletion, server transcodes included; others left alone: "
        f"{[a['id'] for a in q if a['id'] not in mine]}")

    _lib.emit("123_photos_per_record (write)", "\n".join(rows), env)

for name in fields_made:
    r = c.delete(f"/schema/Slate/fields/{name}")
    print(f"  retired /schema/Slate/fields/{name} -> {r.status_code}")
