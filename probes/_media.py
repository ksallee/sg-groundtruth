"""Shared by probes 151 and 152: build a known file with ffmpeg, put it on a take as an Attachment and
as `Version.sg_uploaded_movie`, and watch what the server makes of each.

The take is a row on the first custom entity that has a multi_entity field to Attachment, which is how
sg-onset holds photos today (probe 134); no slot or field name is hardcoded. The Version's `entity` is
that row (probe 122 found `valid_types` unenforced on `Version.entity`).

Each PUT sends the `Content-Type` a browser's `fetch` sends for a `File` of that extension, because that
is what sg-onset will send.
"""
import json
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

import requests

import _lib

ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
VIDEO = ["-f", "lavfi", "-i", "testsrc2=size=1280x720:rate=24"]
TONE = ["-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000"]
FILES = {
    "h264.mp4": (VIDEO + TONE + ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
                                 "-movflags", "+faststart"], "video/mp4"),
    "hevc.mov": (VIDEO + TONE + ["-c:v", "libx265", "-tag:v", "hvc1", "-pix_fmt", "yuv420p",
                                 "-x265-params", "log-level=error", "-c:a", "aac"], "video/quicktime"),
    "aac.m4a": (TONE + ["-c:a", "aac"], "audio/mp4"),
    "opus.webm": (TONE + ["-c:a", "libopus"], "audio/webm"),
}
VERSION_MEDIA = ["sg_uploaded_movie", "sg_uploaded_movie_transcoding_status", "sg_uploaded_movie_mp4",
                 "sg_uploaded_movie_webm", "sg_uploaded_movie_frame_rate", "sg_uploaded_movie_image",
                 "uploaded_movie_duration", "frame_count", "uploaded_movie_audio_offset_mp4", "image",
                 "filmstrip_image"]
ATT_MEDIA = ["this_file", "processing_status", "image", "filmstrip_image", "file_size", "file_extension",
             "metadata", "sg_type"]


def need_ffmpeg():
    for b in ("ffmpeg", "ffprobe"):
        if not shutil.which(b):
            raise SystemExit(f"this probe builds its media with {b}; put it on PATH")


MIME = {}


def build(names, tag):
    """Four seconds of colour bars and a 440 Hz tone, or the tone alone, per name."""
    d = Path(tempfile.mkdtemp(prefix=f"{tag}_"))
    paths = []
    for n in names:
        args, mime = FILES[n]
        p = d / f"{tag}_{n.replace('.', '_')}.{n.split('.')[-1]}"
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args, "-t", "4", str(p)],
                       check=True)
        MIME[p.name] = mime
        paths.append(p)
    return paths


def streams(blob_or_path):
    """`h264 1280x720 24/1 + aac` from ffprobe, for a path or bytes."""
    if isinstance(blob_or_path, (bytes, bytearray)):
        f = tempfile.NamedTemporaryFile(delete=False)
        f.write(blob_or_path)
        f.close()
        path = f.name
    else:
        path = str(blob_or_path)
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "stream=codec_type,codec_name,width,height,r_frame_rate:format=duration",
                        "-of", "json", path], capture_output=True, text=True)
    try:
        j = json.loads(r.stdout)
    except ValueError:
        return f"ffprobe could not read it ({r.stderr.strip()[:120]})"
    parts = []
    for s in j.get("streams", []):
        if s.get("codec_type") == "video":
            parts.append(f"{s.get('codec_name')} {s.get('width')}x{s.get('height')} {s.get('r_frame_rate')}")
        else:
            parts.append(str(s.get("codec_name")))
    dur = (j.get("format") or {}).get("duration")
    return " + ".join(parts) + (f", {float(dur):.2f} s" if dur else "")


def take_target(c):
    """(Type, slug, field) of the first custom entity with a multi_entity field to Attachment."""
    for t in sorted(c.get("/schema").json()["data"]):
        if not (t.startswith("CustomEntity") and t[12:].isdigit()):
            continue
        for name, f in c.get(f"/schema/{t}/fields").json()["data"].items():
            vt = ((f.get("properties") or {}).get("valid_types") or {}).get("value") or []
            if f["data_type"]["value"] == "multi_entity" and vt == ["Attachment"]:
                return t, f"custom_entity{t[12:]}s", name
    raise SystemExit("no custom entity has a multi_entity field to Attachment on this site")


def upload(c, path, f):
    """The three calls of probe 013, the PUT carrying the browser's Content-Type for the extension."""
    i = c.get(f"{path}/_upload", params={"filename": f.name})
    if not i.ok:
        return {"init": i.status_code, "error": i.text}
    b = i.json()
    mime = MIME[f.name]
    put = requests.put(b["links"]["upload"], data=f.read_bytes(), headers={"Content-Type": mime}, timeout=300)
    cr = c.post(b["links"]["complete_upload"], json={"upload_info": b["data"], "upload_data": {}})
    return {"init": i.status_code, "upload_type": b["data"].get("upload_type"), "put": put.status_code,
            "put_content_type": mime, "complete": cr.status_code,
            "complete_body": "" if cr.ok else cr.text}


def image_state(v):
    """What an image field holds: null, the transient placeholder, or a decoded image."""
    if not v:
        return "null"
    url = v if isinstance(v, str) else (v.get("url") if isinstance(v, dict) else None)
    if not url:
        return repr(v)[:80]
    if "/images/status/transient/" in url:
        return "transient placeholder"
    g = requests.get(url, timeout=60)
    return f"{g.status_code} {g.headers.get('Content-Type')} {streams(g.content) if g.ok else ''}".strip()


def media_state(v):
    """A url/media field: its name and content_type, and what ffprobe reads in the stored bytes."""
    if not v:
        return "null"
    if isinstance(v, str):
        return v[:80]
    url = v.get("url")
    desc = f"name {v.get('name')!r} content_type {v.get('content_type')!r}"
    if url:
        g = requests.get(url, timeout=120)
        desc += f"; GET {g.status_code} {g.headers.get('Content-Type')} {len(g.content)} bytes; {streams(g.content)}"
    return desc


def snapshot(c, slug, rid, fields):
    a = c.get(f"/entity/{slug}/{rid}", params={"fields": ",".join(fields)}).json()["data"]
    vals = dict(a.get("attributes") or {})
    for k, rel in (a.get("relationships") or {}).items():
        vals[k] = rel.get("data")
    return vals


def cheap(v):
    """A value with its signature stripped, so a re-signed URL does not read as a change."""
    if isinstance(v, dict) and "url" in v:
        v = {**v, "url": (v["url"] or "").split("?")[0]}
    if isinstance(v, str) and v.startswith("http"):
        v = v.split("?")[0]
    return json.dumps(v, sort_keys=True, default=str)


def watch(c, items, out, limit=420, every=10):
    """Poll every (label, slug, id, fields) until nothing has changed for 90 s, after at least 180 s,
    or `limit` seconds pass. Print each field the first time and whenever it changes."""
    t0, last, quiet_since = time.time(), {}, None
    while True:
        changed = False
        for label, slug, rid, fields in items:
            s = snapshot(c, slug, rid, fields)
            for k in fields:
                key = (label, k)
                if key not in last or cheap(s.get(k)) != last[key]:
                    last[key] = cheap(s.get(k))
                    changed = True
                    v = s.get(k)
                    shown = (image_state(v) if k in ("image", "filmstrip_image", "sg_uploaded_movie_image")
                             else json.dumps(v, default=str)[:160] if not isinstance(v, dict) else
                             json.dumps({x: v[x] for x in v if x != "url"}, default=str)[:200])
                    out(f"  t+{time.time() - t0:4.0f}s {label} {k}: {shown}")
        el = time.time() - t0
        quiet_since = None if changed else (quiet_since or el)
        if el > limit or (quiet_since and el - quiet_since >= 90 and el > 180):
            out(f"  stopped polling at t+{el:.0f}s")
            return
        time.sleep(every)


def entity_on_every_slot(c, proj, tag, vt, made, out):
    """`Version.entity` = a new row on each enabled custom slot, whether or not the slot is in
    `valid_types`, and whether the slot's own fields then list the Version."""
    out("\nVersion.entity on every enabled custom slot")
    for t in sorted(c.get("/schema").json()["data"]):
        if not (t.startswith("CustomEntity") and t[12:].isdigit()):
            continue
        s = f"custom_entity{t[12:]}s"
        back = [k for k, f in c.get(f"/schema/{t}/fields").json()["data"].items()
                if f["data_type"]["value"] == "multi_entity"
                and ((f.get("properties") or {}).get("valid_types") or {}).get("value") == ["Version"]]
        row = made.add(s, c.post(f"/entity/{s}", json={"project": proj, "code": f"{tag}_slot"}).json()["data"]["id"])
        r = c.post("/entity/versions", json={"project": proj, "code": f"{tag}_slot", "entity": {"type": t, "id": row}})
        if not r.ok:
            out(f"  <slot {t[12:]}> in valid_types {t in vt}: POST /entity/versions -> {r.status_code} {r.text}")
            continue
        vid = made.add("versions", r.json()["data"]["id"])
        ent = r.json()["data"]["relationships"]["entity"]["data"] or {}
        listed = {k: [x["id"] for x in (snapshot(c, s, row, [k]).get(k) or [])] for k in back}
        out(f"  <slot {t[12:]}> in valid_types {t in vt}: POST /entity/versions -> {r.status_code}, "
            f"entity reads back {'the row' if (ent.get('type'), ent.get('id')) == (t, row) else ent}; "
            f"multi_entity fields to Version on the slot {back or 'none'}"
            + (f", listing the Version: {[k for k, ids in listed.items() if vid in ids]}" if back else ""))


def run(c, env, tag, names, out, every_slot=False, hold=0):
    """The whole of probes 151 and 152 but the question: one take, one Version per file."""
    need_ffmpeg()
    sb = _lib.sandbox_id(c, env)
    proj = {"type": "Project", "id": sb}
    t, slug, field = take_target(c)
    out(f"take type <slot {t[12:]}>, its multi_entity to Attachment <{'photos' if 'photo' in field else 'files'} field>")
    start = c.post("/entity/attachments/_search", headers=ARR, json={
        "filters": [], "fields": ["id"], "sort": "-id", "page": {"size": 1}}).json()["data"]
    start = start[0]["id"] if start else 0
    files = build(names, tag)
    for f in files:
        out(f"built {f.name}: {f.stat().st_size} bytes, {streams(f)}")

    with _lib.Created(c) as made:
        take = made.add(slug, c.post(f"/entity/{slug}", json={"project": proj, "code": f"{tag}_take"}).json()["data"]["id"])
        vt = c.get("/schema/Version/fields/entity").json()["data"]["properties"]["valid_types"]["value"]
        r = c.post("/entity/versions", json={"project": proj, "code": f"{tag}_entity_check",
                                              "entity": {"type": t, "id": take}})
        ent = (r.json()["data"]["relationships"]["entity"]["data"] or {}) if r.ok else {}
        out(f"Version.entity = the take (<slot> in Version.entity valid_types: {t in vt}) -> {r.status_code}, "
            f"reads back type {'<the slot>' if ent.get('type') == t else ent.get('type')}, id match {ent.get('id') == take}")
        if r.ok:
            made.add("versions", r.json()["data"]["id"])
        if every_slot:
            entity_on_every_slot(c, proj, tag, vt, made, out)

        items = []
        for f in files:
            out(f"\n===== {f.name}")
            u = upload(c, f"/entity/{slug}/{take}/{field}", f)
            out(f"  as an Attachment on the take's field: {u}")
            atts = c.get(f"/entity/{slug}/{take}", params={"fields": field}).json()["data"]["relationships"][field]["data"]
            att = next((a["id"] for a in atts if a.get("name") == f.name), None)
            if att is None:
                for a in atts:
                    if snapshot(c, "attachments", a["id"], ["filename"]).get("filename") == f.name:
                        att = a["id"]
            if att:
                items.append((f"{f.suffix[1:]} Attachment", "attachments", att, ATT_MEDIA))
            v = c.post("/entity/versions", json={"project": proj, "code": f"{tag}_{f.stem}",
                                                  "entity": {"type": t, "id": take}})
            vid = made.add("versions", v.json()["data"]["id"])
            u = upload(c, f"/entity/versions/{vid}/sg_uploaded_movie", f)
            out(f"  as Version.sg_uploaded_movie: {u}")
            items.append((f"{f.suffix[1:]} Version", "versions", vid, VERSION_MEDIA))

        out("\n===== polling")
        watch(c, items, out)

        out("\n===== the stored files at the end")
        for label, s, rid, _ in items:
            snap = snapshot(c, s, rid, ["this_file"] if s == "attachments" else
                            ["sg_uploaded_movie", "sg_uploaded_movie_mp4", "sg_uploaded_movie_webm"])
            for k, v in snap.items():
                if k in ("this_file", "sg_uploaded_movie", "sg_uploaded_movie_mp4", "sg_uploaded_movie_webm"):
                    out(f"  {label} {k}: {media_state(v)}")
        ti = snapshot(c, slug, take, ["image", "filmstrip_image"])
        out(f"  the take's own image: {image_state(ti.get('image'))}; filmstrip_image {image_state(ti.get('filmstrip_image'))}")

        out("\n===== Attachments made since the run began")
        q = c.post("/entity/attachments/_search", headers=ARR, json={
            "filters": [["id", "greater_than", start]],
            "fields": ["filename", "this_file", "attachment_links", "processing_status"],
            "page": {"size": 100}}).json()["data"]
        for a in q:
            fn = a["attributes"].get("filename") or ""
            if tag not in fn:
                continue
            links = [x["type"] if x["type"] != t else "<take>" for x in a["relationships"]["attachment_links"]["data"] or []]
            ct = (a["attributes"].get("this_file") or {}).get("content_type")
            out(f"  {fn.split(tag)[0] and '<hash>_'}{tag}{fn.split(tag, 1)[1]}  content_type {ct!r}  links {links}")
            if ("attachments", a["id"]) not in made.rows:
                made.rows.insert(0, ("attachments", a["id"]))
        if hold:
            print(f"holding {hold} s before cleanup: open the take and its Versions in the web interface", flush=True)
            time.sleep(hold)
    shutil.rmtree(files[0].parent, ignore_errors=True)
