"""Q: how does an `image` field read, write, clear and filter?

Probe 013 established the three-call upload and saw a placeholder under `/images/status/transient/`.
Probe 021 saw the settled value as a plain presigned URL string. Neither asked whether the field is
writable by assignment — the schema flags it `editable: true` — nor whether it can be filtered,
nor how long the transient state lasts. Those are the three a client actually needs.

Read-only half runs ungated. Writes need --write and go only into the sandbox project.
"""
import base64
import json
import sys
import time
from pathlib import Path
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _lib  # noqa: E402

env = _lib.load_env()
c = _lib.client()
PROJECT = _lib.sample_projects(c, env)[0]
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
JSN = {"Content-Type": "application/json"}
PROJ = ["project", "is", {"type": "Project", "id": PROJECT}]
TRANSIENT = "/images/status/transient/"
FIELDS = "code,image,filmstrip_image,image_blur_hash"
rows = []

# 16x16 red PNG, so the probe needs no image library and no file on disk (probe 013)
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAJ0lEQVR42mP8z8BQz0AEYBxVSF+F"
    "jIyM/xnpoxCfwlGFoy4cVUgPhQCq0Ags7T6l4wAAAABJRU5ErkJggg==")


def classify(v):
    """What a client can conclude from the field value alone."""
    if v is None:
        return "null (no thumbnail)"
    if not isinstance(v, str):
        return f"{type(v).__name__}: {v!r}"
    if TRANSIENT in v:
        return f"transient placeholder ({v.rsplit('/', 1)[-1]})"
    return f"url str len={len(v)}"


def search(filt, entity="versions", size=200, fields=None):
    """Row count, or the whole errors[] object — never a slice; the 400 is the teaching content."""
    r = c.post(f"/entity/{entity}/_search", headers=ARR,
               json={"filters": filt, "fields": fields or ["code"], "page": {"size": size}})
    if not r.ok:
        return None, json.dumps(r.json().get("errors"), indent=1)
    return len(r.json()["data"]), None


def snap(vid, fields=FIELDS):
    r = c.get(f"/entity/versions/{vid}", params={"fields": fields})
    return r.json()["data"]["attributes"] if r.ok else {}


# --------------------------------------------------------------- schema
# A field census is site configuration, so sweep every type the site exposes rather than generalising
# from the handful a Version-shaped job happens to touch.
rows.append("=== schema census: every `image` field on every entity type this site exposes")
CORE = ("Version", "Shot", "Asset", "Project", "HumanUser")
types = sorted(c.get("/schema").json()["data"])
census, flags, counts = {}, set(), {}
for etype in types:
    sch = c.get(f"/schema/{etype}/fields")
    if not sch.ok:
        rows.append(f"  {etype}: schema {sch.status_code}")
        continue
    d = sch.json()["data"]
    imgs = tuple(sorted(f for f, m in d.items() if m["data_type"]["value"] == "image"))
    census.setdefault(imgs, []).append(etype)
    flags.update((f, d[f]["editable"]["value"]) for f in imgs)
    if etype in CORE:
        counts[etype] = (len(d), list(imgs))
    if etype == "Version":
        rows.append(f"  properties exposed for Version.image: {sorted(d['image'])}")
        rows.append(f"  image_blur_hash data_type = "
                    f"{d.get('image_blur_hash', {}).get('data_type', {}).get('value')}")
rows.append(f"  {len(types)} entity types swept; distinct image field sets: {len(census)}")
for imgs, ts in sorted(census.items(), key=lambda kv: -len(kv[1])):
    rows.append(f"  {len(ts):>3} types  {list(imgs) or 'no image field at all'}")
    if len(ts) <= 12:
        rows.append(f"           {ts}")
rows.append(f"  every (field, editable) pair seen: {sorted(flags)}")
for etype in CORE:
    n, imgs = counts.get(etype, (0, []))
    rows.append(f"  {etype:<10} {len(imgs)} of {n} fields: {imgs}")

# --------------------------------------------------- operators, from the API
rows.append("\n=== the API enumerates its own operators (probe 017)")
for field in ("image", "filmstrip_image"):
    _, err = search([PROJ, [field, "definitely_not_an_operator", None]])
    rows.append(f"  Version.{field}:")
    rows.append(err or "  (no error — the bogus operator was accepted)")

rows.append("\n=== so can a client filter on a thumbnail at all?")
for label, filt in [("image is_not None", ["image", "is_not", None]),
                    ("image is None", ["image", "is", None]),
                    ("filmstrip_image is_not None", ["filmstrip_image", "is_not", None]),
                    ("image is ''", ["image", "is", ""]),
                    ("image is 'https://x/y.png'", ["image", "is", "https://x/y.png"]),
                    ("image contains 'thumb'", ["image", "contains", "thumb"]),
                    ("image in [None]", ["image", "in", [None]])]:
    n, err = search([PROJ, filt])
    rows.append(f"  {label:<26} -> {n if err is None else 'ERR'}")
    if err:
        rows.append(err)

s = c.post("/entity/versions/_summarize", headers=ARR,
           json={"filters": [PROJ], "summary_fields": [{"field": "id", "type": "count"}],
                 "grouping": [{"field": "image", "type": "exact", "direction": "asc"}]})
rows.append(f"  _summarize grouping on image -> {s.status_code}")
if not s.ok:
    rows.append(json.dumps(s.json().get("errors"), indent=1))

# ------------------------------------------------------------------- read
rows.append("\n=== read: shape and fill on the sample project")
r = c.get("/entity/versions", params={"filter[project.Project.id]": PROJECT, "page[size]": 200,
                                      "fields": FIELDS, "sort": "-created_at"})
data = r.json()["data"]
_lib.note_from(data)
for f in ("image", "filmstrip_image"):
    kinds = {}
    for row in data:
        k = classify(row["attributes"].get(f)).split(" len=")[0]
        kinds[k] = kinds.get(k, 0) + 1
    rows.append(f"  {f:<18} {len(data)} rows: {kinds} — under attributes: "
                f"{f in data[0]['attributes'] if data else '?'}")
hashes = [row["attributes"].get("image_blur_hash") for row in data]
rows.append(f"  image_blur_hash    {sum(h is not None for h in hashes)} of {len(hashes)} non-null, "
            f"data_type text, e.g. {next((h for h in hashes if h), None)!r}")

withimg = [row for row in data if isinstance(row["attributes"].get("image"), str)
           and TRANSIENT not in row["attributes"]["image"]]
rows.append(f"  Versions with a settled thumbnail: {len(withimg)} of {len(data)}")

if withimg:
    vid = withimg[0]["id"]
    rows.append("\n=== read: is the presigned URL stable across two reads?")
    a = snap(vid)["image"]
    time.sleep(1)
    b = snap(vid)["image"]
    third = c.post("/entity/versions/_search", headers=ARR,
                   json={"filters": [["id", "is", vid]], "fields": ["image"]}
                   ).json()["data"][0]["attributes"]["image"]
    rows.append(f"  GET #1 == GET #2 : {a == b}")
    rows.append(f"  GET    == _search: {a == third}")
    q = parse_qs(urlparse(a).query)
    stem = urlparse(a).path.split("/")[1] if urlparse(a).path else "?"
    rows.append(f"  URL path shape   : {stem}/... ({len(a)} chars total)")
    rows.append(f"  query parameters : {sorted(q)}")
    for k in ("X-Amz-Expires", "Expires", "X-Amz-Date", "X-Amz-Algorithm"):
        if k in q:
            rows.append(f"    {k} = {q[k][0]}")
    diff = [i for i in range(min(len(a), len(b))) if a[i] != b[i]]
    rows.append(f"  first differing character index between the two reads: "
                f"{diff[0] if diff else 'none'} of {len(a)}")
    hd = requests.head(a, timeout=30)
    rows.append(f"  HEAD the URL     : {hd.status_code} {hd.headers.get('Content-Type')}")
    g = requests.get(a, timeout=30)
    rows.append(f"  GET  the URL     : {g.status_code} {g.headers.get('Content-Type')} "
                f"{g.headers.get('Content-Length')} bytes")
    rows.append("\n=== read: is the expiry per-read, or a fixed instant the reads share?")
    rows.append(f"  {'read at':<22}{'X-Amz-Date':<18}{'X-Amz-Expires':<15}expires at")
    for i in range(6):
        u = snap(vid)["image"]
        p_ = parse_qs(urlparse(u).query)
        signed = p_["X-Amz-Date"][0]
        secs = int(p_["X-Amz-Expires"][0])
        at = datetime.strptime(signed, "%Y%m%dT%H%M%SZ") + timedelta(seconds=secs)
        rows.append(f"  {datetime.utcnow():%Y-%m-%dT%H:%M:%SZ}  {signed:<18}{secs:<15}"
                    f"{at:%Y-%m-%dT%H:%M:%SZ}")
        if i < 5:
            time.sleep(20)

    if "--expiry" in sys.argv:
        wait = int(q.get("X-Amz-Expires", ["900"])[0]) + 60
        rows.append(f"  sleeping {wait}s to outlive X-Amz-Expires, then re-fetching the string")
        time.sleep(wait)
        g2 = requests.get(a, timeout=30)
        why = "still 200" if g2.ok else g2.text[g2.text.find("<Code>"):g2.text.find("</Code>") + 7]
        rows.append(f"  GET the cached URL after {wait}s: {g2.status_code} {why}")
    else:
        rows.append("  (pass --expiry to sleep past X-Amz-Expires and re-fetch the cached string)")

# ------------------------------------------------------------------ write
if not _lib.writes_allowed():
    rows.append("\n(read-only run; pass --write for assignment, upload, timing and clear)")
else:
    SANDBOX = _lib.sandbox_id(c, env)
    tag = f"zzprobe_image_{int(time.time())}"
    made = _lib.Created(c)
    r = c.post("/entity/versions", json={"project": {"type": "Project", "id": SANDBOX},
                                         "code": tag})
    rows.append(f"\n=== write: throwaway Version in the sandbox -> {r.status_code}")
    vid = made.add("versions", r.json()["data"]["id"]) if r.ok else None
    if not r.ok:
        rows.append(json.dumps(r.json().get("errors"), indent=1))

    with made:
        if not vid:
            raise SystemExit("no sandbox Version to probe")
        fresh = snap(vid)
        rows.append("  a Version that has never had a thumbnail: "
                    + ", ".join(f"{k}={classify(fresh.get(k))}"
                                for k in ("image", "filmstrip_image", "image_blur_hash")))
        rows.append(f"  201 response echoes image: "
                    f"{r.json()['data']['attributes'].get('image', '<absent>')!r}")

        rows.append("\n=== write: assignment, on a Version with no thumbnail")
        rows.append(f"  {'sent':<44}{'code':<6}read back")
        DATA_URI = "data:image/png;base64," + base64.b64encode(PNG).decode()
        for label, val in [
            ("'https://example.com/thumb.png'", "https://example.com/thumb.png"),
            (f"'{DATA_URI[:28]}...' ({len(DATA_URI)} chars)", DATA_URI),
            ("'/images/status/transient/x.png'", "/images/status/transient/x.png"),
            ("{'url': 'https://example.com/t.png'}", {"url": "https://example.com/thumb.png"}),
            ("''", ""),
            ("None", None),
        ]:
            u = c.request("PUT", f"/entity/versions/{vid}", json={"image": val}, headers=JSN)
            if u.ok:
                got = snap(vid).get("image")
                rows.append(f"  {label:<44}{u.status_code:<6}{classify(got)}")
            else:
                rows.append(f"  {label:<44}{u.status_code:<6}")
                rows.append(json.dumps(u.json().get("errors"), indent=1))

        rows.append("\n=== write: the upload dance instead (probe 013)")
        init = c.get(f"/entity/versions/{vid}/image/_upload", params={"filename": "zzprobe.png"})
        rows.append(f"  1. GET /image/_upload -> {init.status_code} "
                    f"upload_type={init.json()['data'].get('upload_type') if init.ok else '?'}")
        if init.ok:
            body = init.json()
            put = requests.put(body["links"]["upload"], data=PNG, timeout=60)
            rows.append(f"  2. PUT {len(PNG)} bytes to presigned S3 -> {put.status_code}")
            done = c.post(body["links"]["complete_upload"],
                          json={"upload_info": body["data"], "upload_data": {}}, headers=JSN)
            t0 = time.monotonic()
            rows.append(f"  3. POST complete_upload -> {done.status_code}")

            rows.append("\n=== the transient placeholder: how long, and what changes")
            settled_at = None
            asked_transient = False
            for _ in range(40):
                a = snap(vid)
                dt = time.monotonic() - t0
                v = a.get("image")
                rows.append(f"  t+{dt:5.0f}s image={classify(v)} "
                            f"filmstrip={classify(a.get('filmstrip_image'))} "
                            f"blur_hash={a.get('image_blur_hash')!r}")
                if isinstance(v, str) and TRANSIENT in v and not asked_transient:
                    asked_transient = True
                    n, _ = search([["id", "is", vid], ["image", "is_not", None]])
                    rows.append(f"         `image is_not None` matches the transient row: {n} row")
                if isinstance(v, str) and TRANSIENT not in v:
                    settled_at = dt
                    break
                time.sleep(5)
            rows.append(f"  settled after ~{settled_at:.0f}s" if settled_at is not None
                        else "  still transient after the poll window")
            n, _ = search([["id", "is", vid], ["image", "is_not", None]])
            rows.append(f"  `image is_not None` matches the settled row: {n} row")
            for _ in range(12):
                a = snap(vid)
                if a.get("image_blur_hash") or a.get("filmstrip_image"):
                    break
                time.sleep(5)
            rows.append(f"  t+{time.monotonic() - t0:.0f}s image_blur_hash="
                        f"{snap(vid).get('image_blur_hash')!r} "
                        f"filmstrip_image={classify(snap(vid).get('filmstrip_image'))}")

        after = snap(vid)
        if isinstance(after.get("image"), str) and TRANSIENT not in after["image"]:
            h = requests.head(after["image"], timeout=30)
            rows.append(f"  HEAD the settled URL -> {h.status_code} "
                        f"{h.headers.get('Content-Type')} {h.headers.get('Content-Length')} bytes")
            rows.append(f"  the value is a {type(after['image']).__name__}, "
                        f"query parameters {sorted(parse_qs(urlparse(after['image']).query))}")

        rows.append("\n=== write: assignment again, now that the field holds a real thumbnail")
        before = snap(vid).get("image")
        u = c.request("PUT", f"/entity/versions/{vid}", json={"image": "https://example.com/x.png"},
                      headers=JSN)
        got = snap(vid).get("image")
        rows.append(f"  PUT image='https://example.com/x.png' -> {u.status_code}")
        if not u.ok:
            rows.append(json.dumps(u.json().get("errors"), indent=1))
        rows.append("  the signature is regenerated per read, so compare the stable path, not the "
                    f"string: unchanged={urlparse(got).path == urlparse(before).path}")

        rows.append("\n=== write: the 400 demands a Hash — is it an entity hash?")
        att = c.post("/entity/attachments/_search", headers=ARR,
                     json={"filters": [["attachment_links", "is", {"type": "Version", "id": vid}]],
                           "fields": ["this_file"], "page": {"size": 5}})
        linked = [a["id"] for a in att.json()["data"]] if att.ok else []
        # id 0 names no row, so on its own it cannot separate "the type refuses writes" from
        # "no such Attachment". Get an id that does resolve and send that too.
        anyatt = c.post("/entity/attachments/_search", headers=ARR,
                        json={"filters": [], "fields": ["this_file"], "page": {"size": 1}})
        real = anyatt.json()["data"][0]["id"] if anyatt.ok and anyatt.json()["data"] else None
        rows.append(f"  Attachments linked to the throwaway Version: {len(linked)}; "
                    f"site-wide search for a real Attachment id: {'found one' if real else 'none'}")
        for label, val in [("{'type': 'Attachment', 'id': <a real Attachment>}",
                            {"type": "Attachment", "id": real} if real else None),
                           ("{'type': 'Attachment', 'id': <linked to this Version>}",
                            {"type": "Attachment", "id": linked[0]} if linked else None),
                           ("{'type': 'Attachment', 'id': 0}", {"type": "Attachment", "id": 0}),
                           ("{}", {})]:
            if val is None:
                continue
            u = c.request("PUT", f"/entity/versions/{vid}", json={"image": val}, headers=JSN)
            rows.append(f"  PUT image={label} -> {u.status_code} "
                        f"{classify(snap(vid).get('image')) if u.ok else ''}")
            if not u.ok:
                rows.append(json.dumps(u.json().get("errors"), indent=1))

        rows.append("\n=== write: image in the POST body at create time")
        cr = c.post("/entity/versions", json={"project": {"type": "Project", "id": SANDBOX},
                                              "code": tag + "_create",
                                              "image": "https://example.com/thumb.png"})
        rows.append(f"  POST with image='https://example.com/thumb.png' -> {cr.status_code}")
        if not cr.ok:
            rows.append(json.dumps(cr.json().get("errors"), indent=1))
        elif cr.ok:
            made.add("versions", cr.json()["data"]["id"])

        rows.append("\n=== a second upload, to filmstrip_image, so clearing has something to take")
        fi = c.get(f"/entity/versions/{vid}/filmstrip_image/_upload",
                   params={"filename": "zzprobe_filmstrip.png"})
        rows.append(f"  GET /filmstrip_image/_upload -> {fi.status_code} "
                    f"upload_type={fi.json()['data'].get('upload_type') if fi.ok else '?'}")
        if fi.ok:
            fb = fi.json()
            requests.put(fb["links"]["upload"], data=PNG, timeout=60)
            fd = c.post(fb["links"]["complete_upload"],
                        json={"upload_info": fb["data"], "upload_data": {}}, headers=JSN)
            rows.append(f"  POST complete_upload -> {fd.status_code}")
            for _ in range(24):
                a = snap(vid)
                fv = a.get("filmstrip_image")
                if isinstance(fv, str) and TRANSIENT not in fv:
                    break
                time.sleep(5)
            rows.append("  after settling: " + ", ".join(
                f"{k}={classify(snap(vid).get(k))}"
                for k in ("image", "filmstrip_image", "image_blur_hash")))

        rows.append("\n=== clear: does null remove the thumbnail, and what else goes with it?")
        pre = snap(vid)
        rows.append("  before: " + ", ".join(f"{k}={classify(pre.get(k))}"
                                             for k in ("image", "filmstrip_image",
                                                       "image_blur_hash")))
        for label, body_ in [("PUT {image: null}", {"image": None}),
                             ("PUT {image: ''}", {"image": ""})]:
            u = c.request("PUT", f"/entity/versions/{vid}", json=body_, headers=JSN)
            post = snap(vid)
            rows.append(f"  {label:<20} {u.status_code} -> "
                        + ", ".join(f"{k}={classify(post.get(k))}"
                                    for k in ("image", "filmstrip_image", "image_blur_hash")))
            if not u.ok:
                rows.append(json.dumps(u.json().get("errors"), indent=1))

        rows.append("\n=== clear: reverse — does clearing filmstrip_image keep image?")
        for field in ("image", "filmstrip_image"):
            up = c.get(f"/entity/versions/{vid}/{field}/_upload", params={"filename": "zz.png"})
            b = up.json()
            requests.put(b["links"]["upload"], data=PNG, timeout=60)
            c.post(b["links"]["complete_upload"],
                   json={"upload_info": b["data"], "upload_data": {}}, headers=JSN)
        for _ in range(24):
            a = snap(vid)
            if all(isinstance(a.get(k), str) and TRANSIENT not in a[k]
                   for k in ("image", "filmstrip_image")):
                break
            time.sleep(5)
        rows.append("  both uploaded: " + ", ".join(f"{k}={classify(snap(vid).get(k))}"
                                                    for k in ("image", "filmstrip_image")))
        u = c.request("PUT", f"/entity/versions/{vid}", json={"filmstrip_image": None}, headers=JSN)
        rows.append(f"  PUT {{filmstrip_image: null}} {u.status_code} -> "
                    + ", ".join(f"{k}={classify(snap(vid).get(k))}"
                                for k in ("image", "filmstrip_image")))

        rows.append("\n=== clear: the obvious alternative — DELETE the field endpoint")
        d = c.request("DELETE", f"/entity/versions/{vid}/image")
        rows.append(f"  DELETE /entity/versions/{{id}}/image -> {d.status_code}")
        if not d.ok:
            rows.append(json.dumps(d.json().get("errors"), indent=1)
                        if d.headers.get("Content-Type", "").startswith("application/json")
                        else f"  body: {d.text[:200]}")
        end = snap(vid)
        rows.append("  after:  " + ", ".join(f"{k}={classify(end.get(k))}"
                                             for k in ("image", "filmstrip_image",
                                                       "image_blur_hash")))

actual = "\n".join(rows)
_lib.emit("field_types/image", actual, env)
