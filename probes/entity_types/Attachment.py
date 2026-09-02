"""Q: how is an Attachment addressed, can one be created directly, and what does it link to?

The caller's question is whether `POST /entity/attachments` exists at all or whether the only door is the
three-call upload dance (probe 013, probe 014). Probe 014 also left an open question: it read Attachment
rows whose `file_extension` and `file_size` were null, and never established whether those fill in.

Read-only by default. `--write` adds the direct-create attempts and one complete upload dance in the
sandbox, polled to see which fields the server fills, every row deleted on the way out.
"""
import json
import base64
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _lib  # noqa: E402

env = _lib.load_env()
c = _lib.client()
PROJECT = _lib.sample_projects(c, env)[0]
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
JSN = {"Content-Type": "application/json"}
rows = []

# 16x16 red PNG, so the probe needs no image library
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAJ0lEQVR42mP8z8BQz0AEYBxVSF+F"
    "jIyM/xnpoxCfwlGFoy4cVUgPhQCq0Ags7T6l4wAAAABJRU5ErkJggg==")


def err(r):
    """Whole errors[] object, source included; the 400 is where the API documents itself (probe 017)."""
    try:
        return json.dumps(r.json().get("errors", r.json()), indent=1)
    except ValueError:
        return r.text


def search(entity, filt, fields=("id",), size=500, project=None, sort=None):
    body = {"filters": ([["project", "is", {"type": "Project", "id": project}]] if project else []) + filt,
            "fields": list(fields), "page": {"size": size}}
    if sort:
        body["sort"] = sort
    r = c.post(f"/entity/{entity}/_search", headers=ARR, json=body)
    if not r.ok:
        return f"ERR {r.status_code}", err(r)
    return len(r.json()["data"]), r.json()["data"]


def props(entity, field, project=None):
    p = {"project_id": project} if project else None
    r = c.get(f"/schema/{entity}/fields/{field}", params=p)
    if not r.ok:
        return {}, {"ERR": err(r)}
    d = r.json()["data"]
    flat = {k: (v.get("value") if isinstance(v, dict) else v) for k, v in d.items() if k != "properties"}
    return flat, {k: v.get("value") for k, v in (d.get("properties") or {}).items()}


rows.append("=== the REST path slug, called rather than guessed")
for slug in ("attachments", "attachment", "Attachment", "attachmentss"):
    r = c.get(f"/entity/{slug}", params={"page[size]": 1})
    tail = "" if r.ok else json.dumps(r.json()["errors"][0].get("detail") or r.json()["errors"][0].get("title"))
    rows.append(f"  GET /entity/{slug:13s} -> {r.status_code} {tail}")
r = c.get("/entity/attachments", params={"page[size]": 1})
if r.ok and r.json()["data"]:
    rows.append(f"  links.self normalises to {r.json()['data'][0]['links']['self']}")

rows.append("\n=== project-scoped or site-wide")
schema = c.get("/schema/Attachment/fields").json()["data"]
rows.append(f"  Attachment fields ({len(schema)}): {sorted(schema)}")
pf, pp = props("Attachment", "project")
rows.append(f"  Attachment.project data_type={pf.get('data_type')} mandatory={pf.get('mandatory')} "
            f"editable={pf.get('editable')} valid_types={pp.get('valid_types')}")
site_n, site_rows = search("attachments", [], fields=("project",), size=500)
proj_n, _ = search("attachments", [], size=500, project=PROJECT)
pids = {(d.get("relationships", {}).get("project", {}).get("data") or {}).get("id") for d in site_rows} \
    if isinstance(site_n, int) else set()
rows.append(f"  _search with no project filter -> {site_n} rows (page size 500) spanning {len(pids)} projects")
rows.append(f"  _search filtered to the sample project -> {proj_n} rows")

rows.append("\n=== identity: which field a human reads")
for f in ("filename", "display_name", "cached_display_name", "description", "original_fname",
          "file_extension", "file_size", "processing_status", "name"):
    ff, _ = props("Attachment", f)
    if not ff:
        rows.append(f"  Attachment.{f:20s} ABSENT from /schema/Attachment/fields")
        continue
    rows.append(f"  Attachment.{f:20s} name={ff.get('name')!r} data_type={ff.get('data_type')} "
                f"mandatory={ff.get('mandatory')} unique={ff.get('unique')} editable={ff.get('editable')}")
rows.append(f"  flagged mandatory: {sorted(k for k, v in schema.items() if (v.get('mandatory') or {}).get('value'))}")
rows.append(f"  flagged unique:    {sorted(k for k, v in schema.items() if (v.get('unique') or {}).get('value'))}")

rows.append("\n=== do file_extension and file_size fill in, or stay null? (probe 014 left this open)")
CENSUS = ("filename", "display_name", "cached_display_name", "file_extension", "file_size",
          "original_fname", "processing_status", "created_at", "this_file")
n, data = search("attachments", [], fields=CENSUS, size=500)
if isinstance(n, int):
    filled = {k: 0 for k in CENSUS}
    by_link_type = {}
    oldest_null = None
    for d in data:
        a = d["attributes"]
        tf = a.get("this_file")
        lt = tf.get("link_type") if isinstance(tf, dict) else ("bare-string" if tf else None)
        b = by_link_type.setdefault(repr(lt), {"rows": 0, "file_size": 0, "file_extension": 0})
        b["rows"] += 1
        for k in CENSUS:
            if a.get(k) not in (None, ""):
                filled[k] += 1
        for k in ("file_size", "file_extension"):
            if a.get(k) not in (None, ""):
                b[k] += 1
        if a.get("file_size") is None and a.get("created_at"):
            oldest_null = min(oldest_null or a["created_at"], a["created_at"])
    rows.append(f"  over {n} attachments site-wide, non-null count per field:")
    for k in CENSUS:
        rows.append(f"    {k:22s} {filled[k]}/{n}")
    rows.append("  split by this_file.link_type:")
    for k, v in sorted(by_link_type.items()):
        rows.append(f"    link_type={k:12s} rows={v['rows']:4d} file_size set={v['file_size']:4d} "
                    f"file_extension set={v['file_extension']:4d}")
    ages = {"file_size set": [], "file_size null": []}
    for d in data:
        a = d["attributes"]
        ages["file_size set" if a.get("file_size") is not None else "file_size null"].append(a.get("created_at"))
    for k, v in ages.items():
        v = sorted(x for x in v if x)
        rows.append(f"  {k:16s} created_at oldest={v[0] if v else None} newest={v[-1] if v else None}")
    for d in data[:2]:
        a = d["attributes"]
        _lib.note_names(*[str(a.get(k)) for k in ("filename", "display_name", "original_fname") if a.get(k)])
        rows.append(f"  sample row id={d['id']} " + json.dumps(
            {k: a.get(k) for k in ("filename", "display_name", "file_extension", "file_size",
                                   "processing_status")}))

rows.append("\n=== this_file, the url field that is the payload (field_types/url)")
tf, tp = props("Attachment", "this_file")
rows.append(f"  data_type={tf.get('data_type')} editable={tf.get('editable')} mandatory={tf.get('mandatory')}")
rows.append(f"  property keys: {sorted(tp)}")
r = c.post("/entity/attachments/_search", headers=ARR,
           json={"filters": [["this_file", "is_not", None]], "fields": ["this_file"], "page": {"size": 1}})
rows.append(f"  filter this_file is_not null -> {r.status_code}")
if not r.ok:
    rows.append("   " + err(r).replace("\n", "\n   "))
n, data = search("attachments", [], fields=("this_file",), size=500)
if isinstance(n, int):
    shapes = {}
    for d in data:
        v = d["attributes"].get("this_file")
        if isinstance(v, dict):
            shapes.setdefault(v.get("link_type"), []).append(v)
    for lt, vs in sorted(shapes.items(), key=lambda kv: str(kv[0])):
        rows.append(f"  link_type={lt!r}: {len(vs)} rows, keys={sorted(vs[0])}")
        rows.append(f"    {json.dumps({k: vs[0][k] for k in sorted(vs[0])})}")
        _lib.note_from(vs[0])
        _lib.note_path(vs[0].get("relative_path"))
else:
    rows.append(f"  {n} {data}")

rows.append("\n=== attachment_links and the other links (field_types/entity, field_types/multi_entity)")
links = {k: v for k, v in schema.items()
         if (v.get("data_type") or {}).get("value") in ("entity", "multi_entity")}
link_fields = sorted(links)
n, data = search("attachments", [], fields=("id", *link_fields), size=500)
filled = {}
for d in data if isinstance(n, int) else []:
    for k, v in (d.get("relationships") or {}).items():
        if v.get("data"):
            filled[k] = filled.get(k, 0) + 1
for k in link_fields:
    v = links[k]
    p = {kk: vv.get("value") for kk, vv in (v.get("properties") or {}).items()}
    vt = p.get("valid_types")
    vt = f"{len(vt)} types (every type on the site)" if vt and len(vt) > 12 else vt
    rows.append(f"  {k:28s} {(v['data_type']['value']):12s} editable={str((v.get('editable') or {}).get('value')):5s} "
                f"filled on {filled.get(k, 0):3d}/{n}  valid_types={vt}")
al = links.get("attachment_links", {}).get("properties", {}).get("valid_types", {}).get("value") or []
rows.append(f"  attachment_links valid_types, in full ({len(al)}): {al}")

rows.append("\n=== reading the attachments of one entity (probe 014: flat filter[] cannot express a hash)")
vn, vdata = search("versions", [["image", "is_not", None]], fields=("id",), size=1, project=PROJECT)
if isinstance(vn, int) and vn:
    vid = vdata[0]["id"]
    n, data = search("attachments", [["attachment_links", "is", {"type": "Version", "id": vid}]],
                     fields=("filename", "file_size", "file_extension"), size=50)
    rows.append(f"  attachment_links is {{Version, <id>}} -> {n} row(s)")
    r = c.get("/entity/attachments", params={"filter[attachment_links]": f"Version,{vid}", "page[size]": 1})
    rows.append(f"  flat filter[attachment_links]=Version,<id> -> {r.status_code}")
    if not r.ok:
        rows.append("   " + err(r).replace("\n", "\n   "))

rows.append("\n=== status")
sf, sp = props("Attachment", "sg_status_list")
_, spj = props("Attachment", "sg_status_list", PROJECT)
rows.append(f"  Attachment.sg_status_list data_type={sf.get('data_type')} editable={sf.get('editable')} "
            f"default_value={sp.get('default_value')!r}")
rows.append(f"    valid_values={sp.get('valid_values')} hidden_values site={sp.get('hidden_values')!r} "
            f"project {PROJECT}={spj.get('hidden_values')!r}")
n, data = search("attachments", [], fields=("sg_status_list",), size=500)
seen = {}
for d in data if isinstance(n, int) else []:
    v = d["attributes"].get("sg_status_list")
    seen[repr(v)] = seen.get(repr(v), 0) + 1
rows.append(f"    distinct sg_status_list over {n} attachments site-wide: {seen}")
ps, pps = props("Attachment", "processing_status")
rows.append(f"  Attachment.processing_status data_type={ps.get('data_type')} editable={ps.get('editable')} "
            f"valid_values={pps.get('valid_values')}")
n, data = search("attachments", [], fields=("processing_status",), size=500)
seen = {}
for d in data if isinstance(n, int) else []:
    v = d["attributes"].get("processing_status")
    seen[repr(v)] = seen.get(repr(v), 0) + 1
rows.append(f"  distinct processing_status over {n} attachments site-wide: {seen}")

if not _lib.writes_allowed():
    rows.append("\n(read-only run; pass --write for the direct-create attempts and the upload dance)")
else:
    SANDBOX = _lib.sandbox_id(c, env)
    with _lib.Created(c) as made:
        rows.append("\n=== can an Attachment be created directly? POST /entity/attachments")
        r = c.post("/entity/versions", headers=JSN,
                   json={"project": {"type": "Project", "id": SANDBOX}, "code": "zzprobe_attachment_host"})
        HOST = made.add("versions", r.json()["data"]["id"]) if r.ok else None
        rows.append(f"  (host Version for the link attempts: POST /entity/versions -> {r.status_code})")
        attempts = [
            ("empty body", {}),
            ("project alone", {"project": {"type": "Project", "id": SANDBOX}}),
            ("filename alone", {"filename": "probe.png"}),
            ("project + filename", {"project": {"type": "Project", "id": SANDBOX}, "filename": "probe.png"}),
            ("project + attachment_links",
             {"project": {"type": "Project", "id": SANDBOX},
              "attachment_links": [{"type": "Version", "id": HOST}]}),
            ("project + this_file url object",
             {"project": {"type": "Project", "id": SANDBOX},
              "this_file": {"url": "https://example.com/probe.png", "name": "probe.png"}}),
        ]
        DIRECT = {}
        for label, body in attempts:
            r = c.post("/entity/attachments", headers=JSN, json=body)
            if r.ok:
                d = r.json()["data"]
                DIRECT[label] = made.add("attachments", d["id"])
                rows.append(f"  {r.status_code} {label}: id={d['id']} attributes={json.dumps(d['attributes'])}")
                _lib.note_from(d)
            else:
                rows.append(f"  {r.status_code} {label}:")
                rows.append("   " + err(r).replace("\n", "\n   "))

        rows.append("\n=== what a directly created Attachment actually holds")
        for label, i in (("empty body", DIRECT.get("empty body")),
                         ("project + this_file url object", DIRECT.get("project + this_file url object"))):
            if not i:
                continue
            d = c.get(f"/entity/attachments/{i}").json()["data"]
            a = d["attributes"]
            rows.append(f"  {label} id={i}: this_file={json.dumps(a.get('this_file'))}")
            rows.append(f"    filename={a.get('filename')!r} display_name={a.get('display_name')!r} "
                        f"file_size={a.get('file_size')!r} file_extension={a.get('file_extension')!r}")
            _lib.note_from(d)

        rows.append("\n=== the upload dance instead (probe 014), then what the server fills in")
        r = c.post("/entity/versions", headers=JSN,
                   json={"project": {"type": "Project", "id": SANDBOX}, "code": "zzprobe_attachment_upload"})
        UP = made.add("versions", r.json()["data"]["id"]) if r.ok else None
        if UP:
            r = c.get(f"/entity/versions/{UP}/_upload", params={"filename": "probe.png"})
            rows.append(f"  1. GET /entity/versions/<id>/_upload (no field) -> {r.status_code} "
                        f"upload_type={r.json()['data'].get('upload_type') if r.ok else ''}")
            if r.ok:
                body = r.json()
                put = requests.put(body["links"]["upload"], data=PNG, timeout=60)
                rows.append(f"  2. PUT {len(PNG)} bytes to the presigned link -> {put.status_code}")
                cr = c.post(body["links"]["complete_upload"], headers=JSN,
                            json={"upload_info": body["data"], "upload_data": {}})
                rows.append(f"  3. POST complete_upload -> {cr.status_code}")
                if not cr.ok:
                    rows.append("   " + err(cr).replace("\n", "\n   "))
                FIELDS = ("filename", "display_name", "cached_display_name", "file_extension", "file_size",
                          "original_fname", "processing_status", "description")
                aid = None
                for label, wait in (("immediately after the 201", 0), ("after 10s", 10), ("after 30s more", 30)):
                    if wait:
                        time.sleep(wait)
                    n, data = search("attachments",
                                     [["attachment_links", "is", {"type": "Version", "id": UP}]],
                                     fields=FIELDS, size=10)
                    if isinstance(n, int) and n:
                        a = data[0]["attributes"]
                        aid = data[0]["id"]
                        rows.append(f"  {label}: {n} attachment(s), id={aid} " +
                                    json.dumps({k: a.get(k) for k in FIELDS}))
                        _lib.note_from(data[0])
                    else:
                        rows.append(f"  {label}: {n} {data}")
                if aid:
                    made.add("attachments", aid)
                    full = c.get(f"/entity/attachments/{aid}").json()["data"]
                    rows.append(f"  full read of that Attachment: attributes={sorted(full['attributes'])}")
                    rows.append(f"    relationships with data: "
                                f"{sorted(k for k, v in (full.get('relationships') or {}).items() if v.get('data'))}")
                    tfv = full["attributes"].get("this_file")
                    if isinstance(tfv, dict):
                        rows.append(f"    this_file keys={sorted(tfv)} link_type={tfv.get('link_type')!r} "
                                    f"content_type={tfv.get('content_type')!r} name={tfv.get('name')!r}")
                    _lib.note_from(full)

                    rows.append("\n=== is the Attachment writable after the fact?")
                    for field, value in (("description", "zzprobe attachment description"),
                                         ("filename", "zzprobe_renamed.png"),
                                         ("file_size", 1),
                                         ("this_file", None)):
                        r = c.put(f"/entity/attachments/{aid}", headers=JSN, json={field: value})
                        if r.ok:
                            rows.append(f"  PUT {field}={value!r} -> 200, reads back "
                                        f"{json.dumps(r.json()['data']['attributes'].get(field))}")
                        else:
                            rows.append(f"  PUT {field}={value!r} -> {r.status_code}")
                            rows.append("   " + err(r).replace("\n", "\n   "))

actual = "\n".join(rows)
_lib.emit("entity_types/Attachment", actual, env)
