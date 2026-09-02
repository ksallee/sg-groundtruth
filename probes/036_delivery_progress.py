"""Q: what can a Delivery say about a long transfer while it runs, and what can it say when it fails?

A survey of production code found this re-implemented in three consumer applications of one delivery
framework: a short status code plus a separate free-text progress line, both written from a finally
block; user cancellation modelled as distinct from error; and a failure reported by creating a Reply on
the Delivery.

Read-only half: the Delivery field census, both vocabularies at site and project scope, and how many
Delivery rows the site holds.
--write half: create a Delivery in the sandbox, walk a progress loop reading back each step, refuse the
codes it refuses, report a failure as a Reply, attach a manifest, and delete all of it.
"""
import base64
import json

import requests

import _lib

env = _lib.load_env()
c = _lib.client()
rows = []

JSON = {"Content-Type": "application/json"}
ARRAY = {"Content-Type": "application/vnd+shotgun.api3_array+json"}   # probe 004

STATUS = "sg_status_list"
PROGRESS = "sg_delivery_progress"
FREETEXT = ["description", "sg_contents", "title"]
READ = [STATUS, PROGRESS, "description", "sg_contents", "title", "delivery_number"]

MANIFEST = json.dumps({"files": 1, "bytes": 68}).encode()
# 16x16 red PNG, so the probe needs no image library and no file on disk (probe 013).
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAJ0lEQVR42mP8z8BQz0AEYBxVSF+F"
    "jIyM/xnpoxCfwlGFoy4cVUgPhQCq0Ass7T6l4wAAAABJRU5ErkJggg==")


def props(field, params=None):
    r = c.get(f"/schema/Delivery/fields/{field}", params=params)
    p = r.json()["data"]["properties"]
    return {k: p.get(k, {}).get("value") for k in ("valid_values", "hidden_values", "default_value")}


def read(did, fields=READ):
    r = c.get(f"/entity/deliveries/{did}", params={"fields": ",".join(fields)})
    return r.json()["data"]["attributes"]


def err(r):
    """Never truncate an error body: the API documents itself in its rejections."""
    return json.dumps(r.json().get("errors", r.json()))


# ---------------------------------------------------------------- read-only
rows.append("=== GET /schema/Delivery/fields — 32 fields; the ones a transfer writes")
schema = c.get("/schema/Delivery/fields").json()["data"]
for name in sorted(schema):
    f = schema[name]
    dt, ed = f["data_type"]["value"], f.get("editable", {}).get("value")
    if dt in ("status_list", "list", "url", "date") or (dt == "text" and ed) \
            or (dt in ("entity", "multi_entity") and name != "image_source_entity"):
        p = f.get("properties", {})
        extra = ""
        if dt in ("status_list", "list"):
            extra = f"  valid={json.dumps(p.get('valid_values', {}).get('value'))}"
        if dt in ("entity", "multi_entity"):
            extra = f"  valid_types={json.dumps(p.get('valid_types', {}).get('value'))}"
        rows.append(f"  {name:<32}{dt:<14}editable={str(ed):<6}{f['name']['value']!r}{extra}")

rows.append("\n=== the two vocabularies, site scope then sandbox project scope (probe 009)")
sandbox = _lib.sandbox_id(c, env)
PROJ = {"type": "Project", "id": sandbox}
for field in (STATUS, PROGRESS):
    site_p = props(field)
    proj_p = props(field, {"project_id": sandbox})
    rows.append(f"  {field}")
    rows.append(f"    site    valid={json.dumps(site_p['valid_values'])}")
    rows.append(f"            hidden={json.dumps(site_p['hidden_values'])} default={json.dumps(site_p['default_value'])}")
    rows.append(f"    project valid={json.dumps(proj_p['valid_values'])}")
    rows.append(f"            hidden={json.dumps(proj_p['hidden_values'])} default={json.dumps(proj_p['default_value'])}")
    rows.append(f"    identical at both scopes: {site_p == proj_p}")

rows.append("\n=== how many Delivery rows exist")
for label, filters in (("site-wide", []), ("sandbox project", [["project", "is", PROJ]])):
    r = c.post("/entity/deliveries/_summarize", headers=ARRAY,
               json={"filters": filters, "summary_fields": [{"field": "id", "type": "record_count"}]})
    rows.append(f"  {label:<16}{r.status_code} {json.dumps(r.json()['data']['summaries'])}")

rows.append("\n=== path slug: the router matches loosely on word boundaries (entity_types/PublishedFile)")
for slug in ("deliveries", "delivery", "Delivery", "Deliveries", "deliverys", "deliveriess", "deliver"):
    r = c.get(f"/entity/{slug}", params={"page[size]": 1})
    detail = "" if r.ok else f"  {r.json()['errors'][0]['detail']}"
    self_link = r.json().get("links", {}).get("self") if r.ok else None
    rows.append(f"  GET /entity/{slug:<14}{r.status_code}{detail}  links.self={self_link}")

rows.append("\n=== read-only fields, and how the refusal reads")
ro = sorted(n for n, f in schema.items() if not f.get("editable", {}).get("value"))
rows.append(f"  {json.dumps(ro)}")

rows.append("\n=== filters: the API enumerates its own operators (probe 017)")
for field in (STATUS, PROGRESS, "title", "sg_versions", "project", "delivery_number"):
    r = c.post("/entity/deliveries/_search", headers=ARRAY,
               json={"filters": [[field, "definitely_not_an_operator", "x"]], "fields": ["id"]})
    rows.append(f"  {field:<22}{r.status_code}  {json.dumps(r.json().get('errors', [{}])[0].get('source'))}")
for label, filters in (("project is sandbox", [["project", "is", PROJ]]),
                       ("sg_status_list is opn", [[STATUS, "is", "opn"]]),
                       ("no filter", [])):
    r = c.post("/entity/deliveries/_search", headers=ARRAY, json={"filters": filters, "fields": ["id"]})
    rows.append(f"  {label:<22}{r.status_code}  {len(r.json()['data'])} row(s)")

rows.append("\n=== the other end of the two Version links")
vfields = c.get("/schema/Version/fields").json()["data"]
for name, f in sorted(vfields.items()):
    vt = (f.get("properties", {}).get("valid_types") or {}).get("value") or []
    if vt == ["Delivery"] or (len(vt) < 5 and "Delivery" in vt):
        rows.append(f"  Version.{name:<26}{f['data_type']['value']:<14}"
                    f"editable={str(f.get('editable', {}).get('value')):<6}valid_types={json.dumps(vt)}")

rows.append("\n=== Reply on a Delivery is ordinary (entity_types/Reply)")
reply_types = c.get("/schema/Reply/fields/entity").json()["data"]["properties"]["valid_types"]["value"]
rows.append(f"  Reply.entity valid_types: {len(reply_types)} types, 'Delivery' in it: {'Delivery' in reply_types}")
rows.append(f"  Delivery.replies valid_types: {json.dumps(schema['replies']['properties']['valid_types']['value'])}")

if not _lib.writes_allowed():
    rows.append("\n(read-only; pass --write for the create, the progress loop and the Reply)")
    _lib.emit("036_delivery_progress", "\n".join(rows), env)
    raise SystemExit

# ---------------------------------------------------------------- writes
with _lib.Created(c) as made:
    rows.append("\n=== create contract")
    for label, body in (("{}", {}),
                        ("{project}", {"project": PROJ}),
                        ("{project, title}", {"project": PROJ, "title": "zzprobe_036_delivery"})):
        r = c.post("/entity/deliveries", headers=JSON, json=body)
        if r.status_code == 201:
            d = r.json()["data"]
            made.add("deliveries", d["id"])
            a = d["attributes"]
            rows.append(f"  {label:<18}201  id={d['id']} title={a.get('title')!r} "
                        f"delivery_number={a.get('delivery_number')!r} "
                        f"{STATUS}={a.get(STATUS)!r} {PROGRESS}={a.get(PROGRESS)!r}")
            did = d["id"]
        else:
            rows.append(f"  {label:<18}{r.status_code}  {err(r)}")

    rows.append("\n=== identity: nothing is flagged mandatory or unique, and title is not unique")
    flagged = {n: {k: (f.get("properties", {}).get(k) or {}).get("value") for k in ("mandatory", "unique")}
               for n, f in schema.items()
               if (f.get("properties", {}).get("mandatory") or {}).get("value")
               or (f.get("properties", {}).get("unique") or {}).get("value")}
    rows.append(f"  fields flagged mandatory or unique: {json.dumps(flagged)}")
    dup = c.post("/entity/deliveries", headers=JSON,
                 json={"project": PROJ, "title": "zzprobe_036_delivery"}).json()["data"]
    made.add("deliveries", dup["id"])
    rows.append(f"  a second Delivery with the same title -> 201 id={dup['id']}")
    rows.append(f"  201 echoes {json.dumps(sorted(dup['attributes']))}")
    rows.append(f"  cached_display_name at the 201: {dup['attributes']['cached_display_name']!r} "
                f"(delivery_number={dup['attributes']['delivery_number']!r})")
    c.put(f"/entity/deliveries/{dup['id']}", headers=JSON, json={"title": "zzprobe_036_renamed"})
    a = c.get(f"/entity/deliveries/{dup['id']}",
              params={"fields": "title,cached_display_name"}).json()["data"]["attributes"]
    rows.append(f"  after a PUT of title:            {a['cached_display_name']!r}")

    rows.append("\n=== what the transfer is transferring")
    v = c.post("/entity/versions", headers=JSON,
               json={"project": PROJ, "code": "zzprobe_036_v001"}).json()["data"]
    made.add("versions", v["id"])
    LINKS = ["sg_versions", "version_sg_deliveries_versions", "sg_published_files"]

    def links(did):
        rel = c.get(f"/entity/deliveries/{did}",
                    params={"fields": ",".join(LINKS)}).json()["data"]["relationships"]
        return {f: [x["id"] for x in (rel.get(f, {}).get("data") or [])] for f in LINKS}

    for field in ("sg_versions", "version_sg_deliveries_versions"):
        r = c.put(f"/entity/deliveries/{did}", headers=JSON,
                  json={field: [{"type": "Version", "id": v["id"]}]})
        rows.append(f"  PUT {field:<32}{r.status_code}  all three read back {json.dumps(links(did))}")
    r = c.put(f"/entity/deliveries/{did}", headers=JSON, json={"sg_versions": []})
    rows.append(f"  PUT sg_versions=[]                   {r.status_code}  "
                f"all three read back {json.dumps(links(did))}")
    r = c.put(f"/entity/deliveries/{did}", headers=JSON,
              json={"sg_versions": [{"type": "Version", "id": v["id"]}]})
    rows.append(f"  PUT sg_versions restored             {r.status_code}  "
                f"all three read back {json.dumps(links(did))}")

    r = c.put(f"/entity/versions/{v['id']}", headers=JSON,
              json={"sg_deliveries": [{"type": "Delivery", "id": did}]})
    rows.append(f"  PUT Version.sg_deliveries            {r.status_code}  "
                f"all three read back {json.dumps(links(did))}")
    r = c.put(f"/entity/versions/{v['id']}", headers=JSON, json={"sg_deliveries": []})
    rows.append(f"  PUT Version.sg_deliveries=[]         {r.status_code}  "
                f"all three read back {json.dumps(links(did))}")

    rows.append("\n=== progress loop: the code and the free-text line, re-read after every write")
    loop = [("opn", "queued: 1 file, 68 bytes"),
            ("ip", "in transit: 0/1 files, 0% "),
            ("ip", "in transit: 1/1 files, 100%"),
            ("dlvr", "delivered: 1 file, 68 bytes, 0 errors")]
    for code, line in loop:
        r = c.put(f"/entity/deliveries/{did}", headers=JSON,
                  json={STATUS: code, "description": line})
        a = read(did)
        rows.append(f"  PUT {code:<5} {r.status_code}  reader sees: "
                    f"{STATUS}={a[STATUS]!r} description={a['description']!r}")

    rows.append("\n=== the other free-text fields hold the same line")
    for field in FREETEXT:
        r = c.put(f"/entity/deliveries/{did}", headers=JSON, json={field: f"zzprobe_036 via {field}"})
        rows.append(f"  {field:<14}{r.status_code}  reads back {read(did)[field]!r}")
    r = c.put(f"/entity/deliveries/{did}", headers=JSON, json={"description": ""})
    rows.append(f"  description=\"\"  {r.status_code}  reads back {read(did)['description']!r}  (field_types/text)")

    rows.append("\n=== cancellation and failure against each vocabulary")
    for field, value in ((STATUS, "cancelled"), (STATUS, "failed"), (STATUS, "recd"),
                         ("sg_delivery_type", "Final"),
                         (PROGRESS, "Delivery cancelled"), (PROGRESS, "Delivery failed"),
                         (PROGRESS, "delivery cancelled"), (PROGRESS, "Cancelled")):
        r = c.put(f"/entity/deliveries/{did}", headers=JSON, json={field: value})
        got = read(did, READ + ["sg_delivery_type"])[field]
        rows.append(f"  {field}={value!r:<22}{r.status_code}  reads back {got!r}")
        if r.status_code != 200:
            rows.append(f"      {err(r)}")

    rows.append("\n=== writing a read-only field")
    for field, value in (("delivery_number", "9999"), ("created_at", "2026-01-01T00:00:00Z")):
        r = c.put(f"/entity/deliveries/{did}", headers=JSON, json={field: value})
        rows.append(f"  {field:<18}{r.status_code}  {err(r)}")

    rows.append("\n=== failure reported as a Reply on the Delivery")
    trace = ("Traceback (most recent call last):\n"
             '  File "deliver.py", line 88, in _push\n'
             "    raise TransferError(\"connection reset after 42 of 68 bytes\")\n"
             "TransferError: connection reset after 42 of 68 bytes")
    r = c.post("/entity/replies", headers=JSON,
               json={"entity": {"type": "Delivery", "id": did}, "content": trace})
    rows.append(f"  POST /entity/replies -> {r.status_code}")
    if r.status_code == 201:
        rid = made.add("replies", r.json()["data"]["id"])
        rows.append(f"  reply attributes: {json.dumps(r.json()['data']['attributes'])[:300]}")
        back = c.get(f"/entity/deliveries/{did}",
                     params={"fields": "replies,reply_content"}).json()["data"]
        rows.append(f"  Delivery.replies -> {json.dumps(back['relationships'].get('replies', {}).get('data'))}")
        rows.append(f"  Delivery.reply_content -> {back['attributes'].get('reply_content')!r}")
        s = c.post("/entity/replies/_search", headers=ARRAY,
                   json={"filters": [["entity", "is", {"type": "Delivery", "id": did}]],
                         "fields": ["content", "created_at"], "sort": ["id"]})
        rows.append(f"  _search entity is Delivery -> {s.status_code}, {len(s.json()['data'])} row(s)")

    rows.append("\n=== the paperwork: a manifest onto the Delivery (probes 013, 014)")
    for filename, payload in (("zzprobe_036_manifest.json", MANIFEST), ("zzprobe_036_frame.png", PNG)):
        b = c.get(f"/entity/deliveries/{did}/_upload", params={"filename": filename})
        rows.append(f"  init {filename:<26}{b.status_code} upload_type={b.json()['data']['upload_type']}")
        if b.status_code != 200:
            rows.append(f"      {err(b)}")
            continue
        info = b.json()
        put = requests.put(info["links"]["upload"], data=payload)
        done = c.post(info["links"]["complete_upload"], headers=JSON,
                      json={"upload_info": info["data"], "upload_data": {}})
        rows.append(f"  PUT S3 -> {put.status_code} ; complete_upload -> {done.status_code}")
    s = c.post("/entity/attachments/_search", headers=ARRAY,
               json={"filters": [["attachment_links", "is", {"type": "Delivery", "id": did}]],
                     "fields": ["display_name", "this_file"], "sort": ["id"]})
    for a in s.json()["data"]:
        made.add("attachments", a["id"])
        rows.append(f"  attachment {a['id']} display_name={a['attributes'].get('display_name')!r}")
    rows.append(f"  Delivery.attachments -> {json.dumps(c.get(f'/entity/deliveries/{did}', params={'fields': 'attachments'}).json()['data']['relationships'].get('attachments', {}).get('data'))}")

    rows.append("\n=== final state a reader is left with")
    rows.append(f"  {json.dumps(read(did))}")
    _lib.note_from(read(did))

    rows.append("\n=== cleanup")

_lib.emit("036_delivery_progress", "\n".join(rows), env)
