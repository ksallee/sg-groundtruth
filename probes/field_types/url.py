"""Q: how does a `url` field read, write, clear and filter, and can a client ever ask "which Versions have media"?

Probed on stock editable fields — Version.sg_uploaded_movie and its derived sg_uploaded_movie_mp4 /
_webm / _image. Never creates a schema field: a name is burned permanently (probe 019).

Probe 021 hit a 400 filtering this type and stopped there. The question that matters to a client is
narrower: is *every* relation refused, does `sort` share the refusal, and if both are gone, what is left
to answer "has media" with. The write half asks whether the upload flow (probe 013) is the only way in.
"""
import json
import os
import re
import sys
import time
import urllib.parse
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _lib  # noqa: E402

env = _lib.load_env()
c = _lib.client()
PROJECT = _lib.sample_projects(c, env)[0]
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
FIELD = "sg_uploaded_movie"
DERIVED = ["sg_uploaded_movie_mp4", "sg_uploaded_movie_webm", "sg_uploaded_movie_image",
           "sg_uploaded_movie_transcoding_status", "sg_uploaded_movie_frame_rate"]
rows = []


def err(r):
    """Whole errors[] object, source included. Truncating it throws away the operator vocabulary."""
    try:
        return json.dumps(r.json().get("errors", r.json()), indent=1)
    except ValueError:
        return r.text


def props(entity, field):
    d = c.get(f"/schema/{entity}/fields/{field}").json()["data"]
    flat = {k: (v.get("value") if isinstance(v, dict) else v) for k, v in d.items()}
    return flat, d


def search(filt, fields=None, size=200, sort=None, project=True):
    body = {"filters": ([["project", "is", {"type": "Project", "id": PROJECT}]] if project else []) + filt,
            "fields": fields or ["code"], "page": {"size": size}}
    if sort:
        body["sort"] = sort
    r = c.post("/entity/versions/_search", headers=ARR, json=body)
    return (len(r.json()["data"]), r.json()["data"]) if r.ok else (f"ERR {r.status_code}", err(r))


rows.append("=== schema: the url fields on Version, against the `image` field probe 021 read as a string")
for entity, field in (("Version", FIELD), ("Version", "sg_uploaded_movie_mp4"),
                      ("Version", "sg_uploaded_movie_image"), ("Version", "image")):
    flat, raw = props(entity, field)
    rows.append(f"  {entity}.{field:<26} data_type={flat.get('data_type'):<9} "
                f"editable={flat.get('editable')} mandatory={flat.get('mandatory')} "
                f"properties={sorted(raw.get('properties', {}))}")

rows.append("\n=== the API enumerates its own operators (probe 017) — ask it for this type's list")
n, e = search([[FIELD, "definitely_not_an_operator", None]])
rows.append(f"  {FIELD} definitely_not_an_operator null -> {n}")
rows.append(e if isinstance(e, str) else "")

rows.append("\n=== does ANY relation work? the whole text vocabulary, plus null")
base, _ = search([])
rows.append(f"  baseline (project filter only) -> {base} versions")
for label, filt in [
    ("is null",                 [[FIELD, "is", None]]),
    ("is_not null",             [[FIELD, "is_not", None]]),
    ('is ""',                   [[FIELD, "is", ""]]),
    ("is a url string",         [[FIELD, "is", "https://example.com/a.mov"]]),
    ("contains '.mov'",         [[FIELD, "contains", ".mov"]]),
    ("not_contains '.mov'",     [[FIELD, "not_contains", ".mov"]]),
    ("starts_with 'https'",     [[FIELD, "starts_with", "https"]]),
    ("ends_with '.mov'",        [[FIELD, "ends_with", ".mov"]]),
    ("in ['a.mov']",            [[FIELD, "in", ["a.mov"]]]),
    ("not_in ['a.mov']",        [[FIELD, "not_in", ["a.mov"]]]),
]:
    n, e = search(filt)
    rows.append(f"  {label:<24} -> {n}")
    if isinstance(n, str):
        rows.append(f"      {' '.join(e.split())[:300]}")

rows.append("\n=== the derived fields and the neighbouring types, same filter")
for field, op, val in [("sg_uploaded_movie_mp4", "is_not", None), ("sg_uploaded_movie_webm", "is", None),
                       ("image", "is_not", None), ("sg_path_to_movie", "is_not", None),
                       ("sg_uploaded_movie_transcoding_status", "is_not", None)]:
    n, e = search([[field, op, val]])
    rows.append(f"  {field}.{op} {val!r} -> {n}")
    if isinstance(n, str):
        rows.append(f"      {' '.join(e.split())[:220]}")

rows.append("\n=== dotted read and dotted filter through the field (probe 016)")
r = c.get("/entity/versions", params={"filter[project.Project.id]": PROJECT,
                                      "fields": f"code,{FIELD}.Attachment.url", "page[size]": 1})
rows.append(f"  GET fields={FIELD}.Attachment.url -> {r.status_code} "
            f"{json.dumps(r.json()['data'][0]['attributes']) if r.ok and r.json()['data'] else err(r)}")
n, e = search([[f"{FIELD}.Attachment.url", "is_not", None]])
rows.append(f"  filter on {FIELD}.Attachment.url is_not null -> {n}")
if isinstance(n, str):
    rows.append(f"      {' '.join(e.split())[:220]}")

rows.append("\n=== sort: does it share the filter's refusal, and does it actually order?")
orders = {}
ASC, DESC, CTRL, NONE = "sort [FIELD] asc", "sort [-FIELD] desc", "sort [code] control", "no sort"
for label, sort in [(ASC, [FIELD]), (DESC, ["-" + FIELD]), (CTRL, ["code"]), (NONE, None),
                    ("sort [{field,direction}]", [{"field": FIELD, "direction": "asc"}])]:
    n, e = search([], fields=["code", FIELD], sort=sort)
    rows.append(f"  {label:<26} -> {n}")
    if isinstance(n, str):
        rows.append(f"      {' '.join(e.split())[:200]}")
    else:
        orders[label] = [(d["id"], bool(d["attributes"].get(FIELD))) for d in e]
if ASC in orders:
    ids = {k: [i for i, _m in orders.get(k, [])] for k in (ASC, DESC, CTRL, NONE)}
    rows.append(f"      asc  has-media first 5 {[m for _i, m in orders[ASC][:5]]} "
                f"last 3 {[m for _i, m in orders[ASC][-3:]]}")
    rows.append(f"      asc == desc: {ids[ASC] == ids[DESC]}   "
                f"asc == unsorted: {ids[ASC] == ids[NONE]}   "
                f"asc == reversed(desc): {ids[ASC] == ids[DESC][::-1]}   "
                f"code-sort == unsorted: {ids[CTRL] == ids[NONE]}")

rows.append("\n=== read: shape, and where the value lands")
r = c.get("/entity/versions", params={"filter[project.Project.id]": PROJECT,
                                      "fields": ",".join(["code", FIELD, "image"] + DERIVED),
                                      "page[size]": 200})
data = r.json()["data"]
_lib.note_from(data)
withmedia = [d for d in data if d["attributes"].get(FIELD)]
rows.append(f"  {len(data)} rows scanned; {len(withmedia)} carry {FIELD}, "
            f"{sum(1 for d in data if d['attributes'].get('image'))} carry image")
rows.append(f"  relationships keys on such a row: {sorted(data[0].get('relationships', {}))}")
for f in [FIELD, "image"] + DERIVED:
    vals = [d["attributes"].get(f) for d in data if d["attributes"].get(f) is not None]
    kinds = sorted({type(v).__name__ for v in vals})
    keys = sorted({k for v in vals if isinstance(v, dict) for k in v})
    rows.append(f"  {f:<38} {len(vals):>3} non-null  type={kinds}  dict keys={keys or '-'}")
if withmedia:
    ex = dict(withmedia[0]["attributes"][FIELD])
    rows.append(f"  one whole value: {json.dumps(ex, indent=1)}")
    rows.append(f"  the same row's image: {json.dumps(withmedia[0]['attributes'].get('image'))}")
    a = c.get(f"/entity/attachments/{ex['id']}",
              params={"fields": "this_file,filename,file_size,attachment_links"})
    rows.append(f"  GET /entity/attachments/{{that id}} -> {a.status_code}"
                + (f" attributes keys={sorted(a.json()['data']['attributes'])}" if a.ok else ""))
    q = urllib.parse.urlsplit(ex["url"])
    rows.append(f"  the url itself: host suffix {'.'.join(q.netloc.split('.')[-3:])} "
                f"query params {sorted(urllib.parse.parse_qs(q.query))}")
    again = c.get(f"/entity/versions/{withmedia[0]['id']}",
                  params={"fields": FIELD}).json()["data"]["attributes"][FIELD]["url"]
    rows.append(f"  same url on a second read: {again == ex['url']}")

# One Version teaches one shape. A url field is stock on nine types here, so ask them all before
# claiming the object always has the same keys.
rows.append("\n=== is the read shape the same everywhere? every url field the site exposes")
TYPES = sorted(c.get("/schema").json()["data"])
uflds = {}
for t in TYPES:
    us = sorted(f for f, m in c.get(f"/schema/{t}/fields").json()["data"].items()
                if (m.get("data_type") or {}).get("value") == "url")
    if us:
        uflds[t] = us
rows.append(f"  {sum(len(v) for v in uflds.values())} url fields on {len(uflds)} of {len(TYPES)} "
            f"entity types: {json.dumps(uflds)}")


def slug(t):
    s = re.sub(r"(?<!^)(?=[A-Z])", "_", t).lower()
    return s[:-1] + "ies" if s.endswith("y") and s[-2] not in "aeiou" else s + "s"


rows.append(f"  {'field':<38}{'non-null':<10}{'value type':<12}keys, and link_type")
for t, fs in uflds.items():
    for f in fs:
        r = c.post(f"/entity/{slug(t)}/_search", headers=ARR,
                   json={"filters": [], "fields": [f], "page": {"size": 200}})
        if not r.ok:
            rows.append(f"  {t + '.' + f:<38}{r.status_code} {' '.join(err(r).split())[:160]}")
            continue
        d = r.json()["data"]
        vals = [x["attributes"].get(f) for x in d if x["attributes"].get(f) is not None]
        shapes = {}
        for v in vals:
            k = (tuple(sorted(v)), v.get("link_type")) if isinstance(v, dict) else (type(v).__name__, None)
            shapes[k] = shapes.get(k, 0) + 1
        rows.append(f"  {t + '.' + f:<38}{f'{len(vals)}/{len(d)}':<10}"
                    f"{'dict' if vals and isinstance(vals[0], dict) else type(vals[0]).__name__ if vals else '-':<12}"
                    + " | ".join(f"link_type={lt} x{n} {list(ks) if isinstance(ks, tuple) else ks}"
                                 for (ks, lt), n in shapes.items()))
        _lib.note_from(d)

if not _lib.writes_allowed():
    rows.append("\n(read-only run; pass --write for the write / clear half)")
else:
    SANDBOX = _lib.sandbox_id(c, env)
    WEB = "https://example.com/zzprobe_url/plate.mov"

    rows.append("\n=== write, into the sandbox project only")
    rc = c.post("/entity/versions", json={"project": {"type": "Project", "id": SANDBOX},
                                          "code": "zzprobe_url_create", FIELD: WEB})
    rows.append(f"  POST create with {FIELD}=<a plain https string> -> {rc.status_code}")
    rows.append(f"      {' '.join(err(rc).split())[:400] if not rc.ok else 'ACCEPTED'}")
    if rc.ok:
        c.request("DELETE", f"/entity/versions/{rc.json()['data']['id']}")

    v = c.post("/entity/versions", json={"project": {"type": "Project", "id": SANDBOX},
                                         "code": "zzprobe_url"})
    vid = v.json()["data"]["id"]
    rows.append(f"  POST create with the field omitted -> {v.status_code} id={vid}")

    def read(fields=None):
        rr = c.get(f"/entity/versions/{vid}", params={"fields": ",".join(fields or [FIELD] + DERIVED)})
        return rr.json()["data"]["attributes"]

    def put(value, field=FIELD):
        rr = c.request("PUT", f"/entity/versions/{vid}", json={field: value},
                       headers={"Content-Type": "application/json"})
        if not rr.ok:
            return rr.status_code, " ".join(err(rr).split())[:400]
        return rr.status_code, f"read back {json.dumps(read([field]))}"

    for label, field, value in [
        ("a plain https string",       FIELD, WEB),
        ("the read shape, url+name",   FIELD, {"url": WEB, "name": "plate.mov"}),
        ("the read shape, all 6 keys", FIELD, {"url": WEB, "name": "plate.mov", "id": 1,
                                               "content_type": "video/quicktime",
                                               "link_type": "web", "type": "Attachment"}),
        ("link_type web, no type/id",  FIELD, {"url": WEB, "name": "plate.mov",
                                               "content_type": "video/quicktime",
                                               "link_type": "web"}),
        ("a local file path",          FIELD, "/mnt/projects/demo_show/plate.mov"),
        ("a bare filename",            FIELD, "plate.mov"),
        ("an Attachment hash",         FIELD, {"type": "Attachment", "id": 1}),
        ("a string into _mp4",         "sg_uploaded_movie_mp4", WEB),
        ("a hash into _mp4",           "sg_uploaded_movie_mp4", {"url": WEB, "name": "plate.mp4"}),
    ]:
        code, info = put(value, field)
        rows.append(f"  PUT {label:<28} -> {code} {info}")

    D = env.get("FPT_PROBE_FRAMES_DIR") or ""
    src = next((f"{D}/{f}" for f in sorted(os.listdir(D)) if f.endswith(".png")), None) if D else None
    if not src:
        rows.append("\n(no FPT_PROBE_FRAMES_DIR; clear tested without real media behind the field)")
    else:
        rows.append("\n=== put real media behind the field (probe 013), then clear it")
        b = c.get(f"/entity/versions/{vid}/{FIELD}/_upload",
                  params={"filename": os.path.basename(src)}).json()
        requests.put(b["links"]["upload"], data=open(src, "rb").read(), timeout=300)
        up = c.post(b["links"]["complete_upload"], json={"upload_info": b["data"], "upload_data": {}})
        rows.append(f"  upload {os.path.basename(src)} -> {up.status_code}")
        _lib.note_path(src)
        for waited in (10, 30, 60, 60):
            time.sleep(waited)
            a = read()
            if a.get("sg_uploaded_movie_transcoding_status") == 1 and a.get("sg_uploaded_movie_mp4"):
                break
        a = read()
        rows.append(f"  after transcode: {FIELD}.name={(a.get(FIELD) or {}).get('name')!r} "
                    f"status={a.get('sg_uploaded_movie_transcoding_status')}")
        for f in DERIVED[:3]:
            v_ = a.get(f)
            rows.append(f"    {f:<30} {json.dumps(v_)[:100] if v_ else None}")

    rows.append("\n=== clear — each attempt against a field that holds media, so 'did it clear' means something")
    for label, value in [("null", None), ('empty string ""', ""), ("empty dict {}", {})]:
        if (read([FIELD]).get(FIELD)) is None:
            put({"url": WEB, "name": "plate.mov"})  # restore, so the next clear has something to remove
        code, info = put(value)
        a = read()
        rows.append(f"  PUT {label:<16} -> {code}  {FIELD} now {json.dumps(a.get(FIELD))[:60]}")
        if code != 200:
            rows.append(f"      {info[:260]}")
        rows.append(f"      mp4={bool(a.get('sg_uploaded_movie_mp4'))} "
                    f"image={bool(a.get('sg_uploaded_movie_image'))} "
                    f"webm={bool(a.get('sg_uploaded_movie_webm'))} "
                    f"fps={a.get('sg_uploaded_movie_frame_rate')} "
                    f"status={a.get('sg_uploaded_movie_transcoding_status')}")

    rows.append("\n=== after the field is null: what still points at the media?")
    put(None)
    a = read(["image", "filmstrip_image", FIELD] + DERIVED)
    rows.append("  " + json.dumps({k: (bool(v) if k != "sg_uploaded_movie_transcoding_status" else v)
                                   for k, v in a.items()}))
    at = c.post("/entity/attachments/_search", headers=ARR,
                json={"filters": [["attachment_links", "is", {"type": "Version", "id": vid}]],
                      "fields": ["filename"], "page": {"size": 20}})
    rows.append(f"  attachments still linked to the Version: "
                f"{len(at.json()['data']) if at.ok else err(at)}")

    # The neighbours are the only filterable proxies for "has media", and one cleared row cannot
    # show whether they keep matching. Clear a second row the same way and filter for both.
    def neighbours(target):
        out = []
        for f in ("image", "sg_uploaded_movie_transcoding_status"):
            n, _ = search([["id", "is", target], [f, "is_not", None]], project=False)
            out.append(f"{f} is_not None -> {n}")
        return ";  ".join(out)

    def state(target):
        a_ = c.get(f"/entity/versions/{target}",
                   params={"fields": ",".join([FIELD, "image", "filmstrip_image"] + DERIVED)}
                   ).json()["data"]["attributes"]
        return json.dumps({k: (v if k.startswith("sg_uploaded_movie_transcoding") or
                               k.endswith("frame_rate") else bool(v)) for k, v in a_.items()})

    rows.append("\n=== a SECOND row, uploaded and cleared the same way")
    if not src:
        rows.append("  (needs FPT_PROBE_FRAMES_DIR; without real media a second row proves nothing)")
    else:
        v2 = c.post("/entity/versions", json={"project": {"type": "Project", "id": SANDBOX},
                                              "code": "zzprobe_url_row2"})
        vid2 = v2.json()["data"]["id"]
        b = c.get(f"/entity/versions/{vid2}/{FIELD}/_upload",
                  params={"filename": os.path.basename(src)}).json()
        requests.put(b["links"]["upload"], data=open(src, "rb").read(), timeout=300)
        up2 = c.post(b["links"]["complete_upload"], json={"upload_info": b["data"], "upload_data": {}})
        rows.append(f"  row 2 upload -> {up2.status_code}")
        for waited in (10, 30, 60, 60):
            time.sleep(waited)
            a2 = c.get(f"/entity/versions/{vid2}", params={"fields": ",".join(DERIVED)}
                       ).json()["data"]["attributes"]
            if a2.get("sg_uploaded_movie_transcoding_status") == 1 and a2.get("sg_uploaded_movie_mp4"):
                break
        rows.append(f"  row 2 before clear: {state(vid2)}")
        rows.append(f"  row 2 before clear: {neighbours(vid2)}")
        cl = c.request("PUT", f"/entity/versions/{vid2}", json={FIELD: None},
                       headers={"Content-Type": "application/json"})
        rows.append(f"  row 2 PUT {FIELD}=null -> {cl.status_code}")
        rows.append(f"  row 2 after  clear: {state(vid2)}")
        rows.append(f"  row 2 after  clear: {neighbours(vid2)}")
        rows.append(f"  row 1 after  clear: {state(vid)}")
        rows.append(f"  row 1 after  clear: {neighbours(vid)}")
        rows.append(f"  cleanup: DELETE version {vid2} -> "
                    f"{c.request('DELETE', f'/entity/versions/{vid2}').status_code}")

    d = c.request("DELETE", f"/entity/versions/{vid}")
    rows.append(f"\ncleanup: DELETE version {vid} -> {d.status_code}")

report = "\n".join(rows)
D = env.get("FPT_PROBE_FRAMES_DIR")
if D:
    report = report.replace(D, "<storage>/<sequence>")
_lib.emit("field_types/url", report, env)
