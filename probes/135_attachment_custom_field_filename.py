"""Q: can a custom field be created on Attachment over REST, is `Attachment.filename` kept verbatim at
about 90 characters, and do `is` and `starts_with` filters match on it?

sg-onset names each photo for its take and capture time, and finds it again by that name. Measured:
`POST /schema/Attachment/fields` for a text field; three uploads to one Note (field-less `_upload`,
probe 123) under long names, 90 characters and past it, with spaces, dots and a non-ASCII letter;
what `filename` and `this_file.name` read back; and `is`, `starts_with`, `contains` and `ends_with`
on `filename`.

Writes in the sandbox, behind `--write`: one Note `zzprobe_135`, three Attachments, and if the
schema create lands, `sg_zzprobe_135_note` on Attachment, retired before exit.

    python probes/135_attachment_custom_field_filename.py --write
"""
import json
import os

import requests

import _lib

ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
env = _lib.load_env()
c = _lib.client()
if not _lib.writes_allowed():
    raise SystemExit("probe 135 writes; run with --write")
SB = _lib.sandbox_id(c, env)
P = {"type": "Project", "id": SB}
rows = []


def out(s=""):
    rows.append(str(s))


def errs(r):
    try:
        return json.dumps(r.json().get("errors", r.json()))[:700]
    except ValueError:
        return repr(r.text[:300])


def pad(stem, n, ext=".jpg"):
    return (stem + "_" + "x" * n)[: n - len(ext)] + ext


NAMES = [
    pad("zzprobe_135_A001C002_take03_2026-11-11T14-22-05.123", 90),
    pad("zzprobe_135 B cam take 3 é.ü", 90, ".jpeg"),
    pad("zzprobe_135_long", 200),
]

field_made = None
with _lib.Created(c) as made:
    out("===== POST /schema/Attachment/fields, a text field")
    r = c.post("/schema/Attachment/fields", json={"data_type": "text", "properties": [
        {"property_name": "name", "value": "zzprobe 135 note"}]})
    out(f"  -> {r.status_code} {r.json()['links']['self'].rsplit('/', 1)[-1] if r.status_code == 201 else errs(r)}")
    if r.status_code == 201:
        field_made = r.json()["links"]["self"].rsplit("/", 1)[-1]

    note = made.add("notes", c.post("/entity/notes", json={
        "project": P, "subject": "zzprobe_135", "content": "zzprobe_135"}).json()["data"]["id"])
    out("\n===== three uploads to one Note")
    ids = {}
    for n in NAMES:
        i = c.get(f"/entity/notes/{note}/_upload", params={"filename": n})
        if not i.ok:
            out(f"  init {len(n)} chars -> {i.status_code} {errs(i)}")
            continue
        b = i.json()
        requests.put(b["links"]["upload"], data=os.urandom(256), timeout=60)
        cr = c.post(b["links"]["complete_upload"], json={"upload_info": b["data"], "upload_data": {}})
        out(f"  sent {len(n)} chars {n!r}: init original_filename {b['data'].get('original_filename') == n}, complete {cr.status_code}")
    atts = c.get(f"/entity/notes/{note}", params={"fields": "attachments"}).json()["data"]["relationships"]["attachments"]["data"]
    for a in atts:
        made.rows.insert(0, ("attachments", a["id"]))
        d = c.get(f"/entity/attachments/{a['id']}", params={"fields": "filename,this_file,display_name"}).json()["data"]["attributes"]
        fn = d.get("filename")
        sent = next((n for n in NAMES if n == fn or (fn and n.startswith(fn[:20]))), None)
        ids[sent] = a["id"]
        out(f"  read back {len(fn or '')} chars: filename {fn!r}\n      verbatim {fn == sent}; this_file.name equal {(d.get('this_file') or {}).get('name') == fn}; "
            f"display_name equal {d.get('display_name') == fn}")

    if field_made and atts:
        r = c.put(f"/entity/attachments/{atts[0]['id']}", json={field_made: "zzprobe 135 value"})
        out(f"\n  PUT the new field on an Attachment -> {r.status_code} {'' if r.ok else errs(r)}")

    out("\n===== filters on filename, project the sandbox")
    first = NAMES[0]
    for op, val in (("is", first), ("is", first.upper()), ("is", first[:-4]),
                    ("starts_with", first[:40]), ("starts_with", "ZZPROBE_135_A001"), ("starts_with", "zzprobe_135"),
                    ("contains", "take03_2026"), ("ends_with", first[-20:]), ("is", NAMES[1]),
                    ("starts_with", "zzprobe_135 B cam take 3 é")):
        r = c.post("/entity/attachments/_search", headers=ARR, json={
            "filters": [["project", "is", P], ["filename", op, val]], "fields": ["filename"]})
        out(f"  {op:<12} {val[:48]!r:<52} -> {r.status_code} "
            + (f"{len(r.json()['data'])} rows" if r.ok else errs(r)))
    r = c.post("/entity/attachments/_search", headers=ARR, json={
        "filters": [["filename", "definitely_not_an_operator", "x"]], "fields": ["id"]})
    out(f"  bogus operator -> {r.status_code} {errs(r)}")
    _lib.emit("135_attachment_custom_field_filename", "\n".join(rows), env)

if field_made:
    r = c.delete(f"/schema/Attachment/fields/{field_made}")
    print(f"  retired /schema/Attachment/fields/{field_made} -> {r.status_code}")
