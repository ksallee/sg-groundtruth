"""Q: does a second upload to a multi_entity field to Attachment add a file or replace the first, and
does the Attachment it makes get a `project`?

Probe 123 uploaded once to such a field and then PUT three Attachments on it. sg-onset uploads photos
one at a time as each arrives, so the second `_upload` decides whether it must read the field and PUT
the union back. Measured: two uploads in a row, the field read after each; each Attachment's
`project`, `attachment_links` and `this_file.name`; whether the first Attachment survives; and the
reverse field the create made on Attachment (probe 142 measures reverse fields in full).

Writes in the sandbox, behind `--write`: one row on the first enabled custom slot, two Attachments,
one schema field `sg_zzprobe_134_files` on that slot, retired before exit.

    python probes/134_attachment_field_second_upload.py --write
"""
import json
import os

import requests

import _lib

ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
env = _lib.load_env()
c = _lib.client()
if not _lib.writes_allowed():
    raise SystemExit("probe 134 writes; run with --write")
SB = _lib.sandbox_id(c, env)
P = {"type": "Project", "id": SB}
schema = c.get("/schema").json()["data"]
CE = sorted(t for t in schema if t.startswith("CustomEntity") and t[12:].isdigit())[0]
SLUG = f"custom_entity{CE[12:]}s"
FIELD = "sg_zzprobe_134_files"
rows = []


def out(s=""):
    rows.append(str(s))


def errs(r):
    try:
        return json.dumps(r.json().get("errors", r.json()))[:600]
    except ValueError:
        return repr(r.text[:300])


def upload(path, name, data):
    i = c.get(f"{path}/_upload", params={"filename": name})
    if not i.ok:
        return f"init {i.status_code} {errs(i)}"
    b = i.json()
    put = requests.put(b["links"]["upload"], data=data, timeout=120)
    cr = c.post(b["links"]["complete_upload"], json={"upload_info": b["data"], "upload_data": {}})
    return f"init {i.status_code}, PUT {put.status_code}, complete {cr.status_code}" + ("" if cr.ok else errs(cr))


att_before = set(c.get("/schema/Attachment/fields").json()["data"])
field_made = False
with _lib.Created(c) as made:
    row = made.add(SLUG, c.post(f"/entity/{SLUG}", json={"project": P, "code": "zzprobe_134"}).json()["data"]["id"])
    try:
        r = c.post(f"/schema/{CE}/fields", json={"data_type": "multi_entity", "properties": [
            {"property_name": "name", "value": "zzprobe 134 files"},
            {"property_name": "valid_types", "value": ["Attachment"]}]})
        out(f"POST /schema/<custom slot>/fields multi_entity [Attachment] -> {r.status_code} "
            + (r.json()["links"]["self"].rsplit("/", 1)[-1] if r.ok else errs(r)))
        field_made = r.status_code == 201
        new_att = sorted(set(c.get("/schema/Attachment/fields").json()["data"]) - att_before)
        out(f"fields new on Attachment after the create: {new_att}")
        for nf in new_att:
            d = c.get(f"/schema/Attachment/fields/{nf}").json()["data"]
            out(f"  {nf}: data_type {d['data_type']['value']}, name {d['name']['value']!r}, "
                f"valid_types {d['properties'].get('valid_types', {}).get('value')}, editable {d['editable']['value']}")

        seen = []
        for n in (1, 2):
            name = f"zzprobe_134_file{n}.txt"
            out(f"\n===== upload {n}: {name}")
            out("  " + upload(f"/entity/{SLUG}/{row}/{FIELD}", name, os.urandom(512)))
            held = c.get(f"/entity/{SLUG}/{row}", params={"fields": FIELD}).json()["data"]["relationships"][FIELD]["data"]
            out(f"  field holds {len(held)}: {[(h['type'], h.get('name')) for h in held]}")
            for h in held:
                if h["id"] not in seen:
                    seen.append(h["id"])
                    made.rows.insert(0, ("attachments", h["id"]))
        out("\n===== each Attachment the uploads made")
        for aid in seen:
            a = c.get(f"/entity/attachments/{aid}", params={
                "fields": "project,attachment_links,this_file,filename,file_size,created_by"}).json()["data"]
            rel, at = a["relationships"], a["attributes"]
            tf = at.get("this_file") or {}
            out(f"  Attachment {seen.index(aid) + 1}: project {(rel.get('project') or {}).get('data')}; "
                f"attachment_links {[x['type'] for x in rel['attachment_links']['data']]}; "
                f"filename {at.get('filename')!r}; this_file name {tf.get('name')!r} link_type {tf.get('link_type')!r}")
        q = c.post("/entity/attachments/_search", headers=ARR, json={
            "filters": [["project", "is", P], ["filename", "starts_with", "zzprobe_134_"]],
            "fields": ["id"]}).json()["data"]
        out(f"  _search project is the sandbox and filename starts_with zzprobe_134_: {len(q)} rows")
        out("\n===== the remedy: PUT both back with multi_entity_update_mode add (recipe 009)")
        if len(seen) == 2:
            r = c.put(f"/entity/{SLUG}/{row}", json={FIELD: {"multi_entity_update_mode": "add", "value": [
                {"type": "Attachment", "id": i} for i in seen]}})
            held = c.get(f"/entity/{SLUG}/{row}", params={"fields": FIELD}).json()["data"]["relationships"][FIELD]["data"]
            out(f"  PUT add both -> {r.status_code}; field holds {len(held)}")
    finally:
        _lib.emit("134_attachment_field_second_upload", "\n".join(rows), env)

if field_made:
    r = c.delete(f"/schema/{CE}/fields/{FIELD}")
    print(f"  retired /schema/<custom slot>/fields/{FIELD} -> {r.status_code}")
    print(f"  fields still new on Attachment: {sorted(set(c.get('/schema/Attachment/fields').json()['data']) - att_before)}")
