"""Q: how is a Note addressed, what does creating one really require, and how do links, replies and
attachments attach to it?

Note is the type a review client writes into, and it is the one standard type whose identity field is
`subject` while its body is `content`, the same field name Task uses for its identity. The create
contract, the `note_links` valid_types, whether a Reply is reachable from the Note side, and whether
`attachments` can be set in the same POST are the four things a client gets wrong.

Read-only by default. `--write` adds the create attempts, the note_links replace demonstration, the
Reply direction test and the attachment-at-create test, sandbox only, every row deleted on the way out.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _lib  # noqa: E402

env = _lib.load_env()
c = _lib.client()
PROJECT = _lib.sample_projects(c, env)[0]
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
JSN = {"Content-Type": "application/json"}
rows = []


def err(r):
    """Whole errors[] object, source included; the 400 is where the API documents itself (probe 017)."""
    try:
        return json.dumps(r.json().get("errors", r.json()), indent=1)
    except ValueError:
        return r.text


def show(r, label):
    rows.append(f"  {r.status_code} {label}:")
    rows.append("   " + err(r).replace("\n", "\n   "))


def search(entity, filt, fields=("id",), size=500, project=None):
    body = {"filters": ([["project", "is", {"type": "Project", "id": project}]] if project else []) + filt,
            "fields": list(fields), "page": {"size": size}}
    r = c.post(f"/entity/{entity}/_search", headers=ARR, json=body)
    if not r.ok:
        return f"ERR {r.status_code}", err(r)
    return len(r.json()["data"]), r.json()["data"]


def props(entity, field, project=None):
    p = {"project_id": project} if project else None
    r = c.get(f"/schema/{entity}/fields/{field}", params=p)
    if not r.ok:
        return {"absent": r.status_code}, {}
    d = r.json()["data"]
    flat = {k: (v.get("value") if isinstance(v, dict) else v) for k, v in d.items() if k != "properties"}
    return flat, {k: v.get("value") for k, v in (d.get("properties") or {}).items()}


def rel(d, field):
    return json.dumps((d.get("relationships") or {}).get(field, {}).get("data"))


rows.append("=== the REST path slug, called rather than guessed")
for slug in ("notes", "note", "Note", "notess"):
    r = c.get(f"/entity/{slug}", params={"page[size]": 1})
    tail = "" if r.ok else json.dumps(r.json()["errors"][0].get("detail") or r.json()["errors"][0].get("title"))
    rows.append(f"  GET /entity/{slug:7s} -> {r.status_code} {tail}")
r = c.get("/entity/notes", params={"page[size]": 1, "fields": "subject"})
one = r.json()["data"][0]
rows.append(f"  one row: type={one['type']!r} links.self={one['links']['self']!r}")

rows.append("\n=== project-scoped or site-wide")
schema = c.get("/schema/Note/fields").json()["data"]
rows.append(f"  Note has {len(schema)} fields in /schema/Note/fields")
pf, pp = props("Note", "project")
rows.append(f"  Note.project data_type={pf.get('data_type')} mandatory={pf.get('mandatory')} "
            f"editable={pf.get('editable')} valid_types={pp.get('valid_types')}")
site_n, sdata = search("notes", [], fields=("subject", "project"), size=500)
proj_n, _ = search("notes", [], size=500, project=PROJECT)
projects_seen = {(d.get("relationships", {}).get("project", {}).get("data") or {}).get("id")
                 for d in sdata} if isinstance(site_n, int) else set()
rows.append(f"  _search with no project filter -> {site_n} rows at page size 500, "
            f"spanning {len(projects_seen)} distinct project(s)")
rows.append(f"  _search filtered to the sample project -> {proj_n} rows")

rows.append("\n=== identity: subject, and the body field content")
for field in ("subject", "content", "cached_display_name", "code", "name", "description"):
    f, p = props("Note", field)
    if f.get("absent"):
        rows.append(f"  Note.{field:20s} absent from /schema/Note/fields ({f['absent']})")
    else:
        rows.append(f"  Note.{field:20s} name={f.get('name')!r} data_type={f.get('data_type')} "
                    f"mandatory={f.get('mandatory')} unique={f.get('unique')} editable={f.get('editable')}")
rows.append(f"  Note fields flagged mandatory: {sorted(k for k, v in schema.items() if (v.get('mandatory') or {}).get('value'))}")
rows.append(f"  Note fields flagged unique:    {sorted(k for k, v in schema.items() if (v.get('unique') or {}).get('value'))}")
tf, _ = props("Task", "content")
rows.append(f"  Task.content for comparison: name={tf.get('name')!r} data_type={tf.get('data_type')} "
            f"mandatory={tf.get('mandatory')}")

n, data = search("notes", [], fields=("subject", "content", "cached_display_name"), size=500, project=PROJECT)
if isinstance(n, int) and n:
    same_subject = sum(1 for d in data if d["attributes"].get("cached_display_name") == d["attributes"].get("subject"))
    same_content = sum(1 for d in data if d["attributes"].get("cached_display_name") == d["attributes"].get("content"))
    null_subj = sum(1 for d in data if d["attributes"].get("subject") in (None, ""))
    null_body = sum(1 for d in data if d["attributes"].get("content") in (None, ""))
    lens = sorted(len(d["attributes"].get("content") or "") for d in data)
    subj_lens = sorted(len(d["attributes"].get("subject") or "") for d in data)
    rows.append(f"  over {n} notes in the sample project: cached_display_name == subject on {same_subject}, "
                f"== content on {same_content}")
    rows.append(f"  subject null or empty on {null_subj}; content null or empty on {null_body}")
    rows.append(f"  length of subject: min {subj_lens[0]} median {subj_lens[n // 2]} max {subj_lens[-1]}")
    rows.append(f"  length of content: min {lens[0]} median {lens[n // 2]} max {lens[-1]}")
    shapes = {}
    for d in data:
        a = d["attributes"]
        s, cdn = a.get("subject") or "", a.get("cached_display_name") or ""
        shape = cdn.replace(s, "<subject>") if s and s in cdn else "<neither>"
        shapes[shape[:60]] = shapes.get(shape[:60], 0) + 1
    rows.append(f"  cached_display_name with the subject masked out: {sorted(shapes.items(), key=lambda x: -x[1])[:3]}")
for field in ("subject", "content", "cached_display_name", "code", "name"):
    k, detail = search("notes", [[field, "is_not", None]], size=1, project=PROJECT)
    rows.append(f"  filter [{field!r}, 'is_not', None] -> {k}"
                + ("" if isinstance(k, int) else " " + json.dumps(json.loads(detail)[0].get("title"))))

rows.append("\n=== note_links and the other links (field_types/entity, field_types/multi_entity)")
links = {k: v for k, v in schema.items()
         if (v.get("data_type") or {}).get("value") in ("entity", "multi_entity")}
link_fields = sorted(links)
n, data = search("notes", [], fields=("subject", *link_fields), size=500, project=PROJECT)
filled, seen_types = {}, {}
for d in data if isinstance(n, int) else []:
    for k, v in (d.get("relationships") or {}).items():
        payload = v.get("data")
        if payload:
            filled[k] = filled.get(k, 0) + 1
        if k == "note_links":
            for e in payload or []:
                seen_types[e["type"]] = seen_types.get(e["type"], 0) + 1
for k in link_fields:
    v = links[k]
    p = {kk: vv.get("value") for kk, vv in (v.get("properties") or {}).items()}
    vt = p.get("valid_types")
    vt = f"{len(vt)} types" if vt and len(vt) > 8 else vt
    rows.append(f"  {k:26s} {(v['data_type']['value']):12s} editable={str((v.get('editable') or {}).get('value')):5s} "
                f"valid_types={vt}  filled on {filled.get(k, 0)}/{n}")
rows.append(f"  types actually seen inside note_links over those {n} notes: {seen_types}")
nl_types = {kk: vv.get("value") for kk, vv in (schema["note_links"].get("properties") or {}).items()}.get("valid_types")
rows.append(f"  note_links valid_types ({len(nl_types)}): {nl_types}")

rows.append("\n=== threading: which side carries the link")
for entity, field in (("Note", "replies"), ("Reply", "entity"), ("Reply", "content")):
    f, p = props(entity, field)
    if f.get("absent"):
        rows.append(f"  {entity}.{field}: absent from the schema ({f['absent']})")
    else:
        rows.append(f"  {entity}.{field}: data_type={f.get('data_type')} editable={f.get('editable')} "
                    f"mandatory={f.get('mandatory')} valid_types={p.get('valid_types')}")
rsch = c.get("/schema/Reply/fields")
if rsch.ok:
    rows.append(f"  Reply fields: {sorted(rsch.json()['data'])}")
n, data = search("notes", [], fields=("subject", "replies"), size=500, project=PROJECT)
with_replies = sum(1 for d in data if isinstance(n, int) and (d.get("relationships", {}).get("replies", {}).get("data")))
rows.append(f"  notes in the sample project with a non-empty replies list: {with_replies}/{n}")
k, rdata = search("replies", [], fields=("content",), size=5)
rows.append(f"  GET-side /entity/replies/_search unfiltered -> {k} row(s) at page size 5")
if isinstance(k, int) and k:
    r = c.get(f"/entity/replies/{rdata[0]['id']}")
    if r.ok:
        rows.append(f"  one Reply's relationship keys: {sorted((r.json()['data'].get('relationships') or {}))}")
        rows.append(f"  its entity link: {rel(r.json()['data'], 'entity')[:120]}")

rows.append("\n=== status (field_types/status_list)")
sf, sp = props("Note", "sg_status_list")
_, spj = props("Note", "sg_status_list", PROJECT)
if sf.get("absent"):
    rows.append("  Note.sg_status_list absent")
else:
    rows.append(f"  data_type={sf.get('data_type')} editable={sf.get('editable')} default_value={sp.get('default_value')!r}")
    rows.append(f"  valid_values={sp.get('valid_values')}")
    rows.append(f"  display_values={json.dumps(sp.get('display_values'))}")
    rows.append(f"  hidden_values site-wide={sp.get('hidden_values')!r}  project {PROJECT}={spj.get('hidden_values')!r}")
n, data = search("notes", [], fields=("sg_status_list",), size=500, project=PROJECT)
seen = {}
for d in data if isinstance(n, int) else []:
    v = d["attributes"].get("sg_status_list")
    seen[repr(v)] = seen.get(repr(v), 0) + 1
rows.append(f"  distinct sg_status_list over {n} notes in the sample project: {seen}")

rows.append("\n=== the other single-valued fields a client sets")
for field in ("sg_note_type", "meta", "client_note", "client_approved", "reply_content",
              "publish_status", "suppress_email_notif", "addressings_to", "addressings_cc", "user"):
    f, p = props("Note", field)
    if f.get("absent"):
        rows.append(f"  Note.{field}: absent")
        continue
    extra = f" valid_values={p.get('valid_values')}" if p.get("valid_values") is not None else ""
    extra += f" valid_types={p.get('valid_types')}" if p.get("valid_types") is not None else ""
    rows.append(f"  Note.{field:16s} data_type={f.get('data_type'):13s} editable={str(f.get('editable')):5s} "
                f"mandatory={f.get('mandatory')}{extra}")

if not _lib.writes_allowed():
    rows.append("\n(read-only run; pass --write for the create contract, replies, and attachments at create)")
else:
    SANDBOX = _lib.sandbox_id(c, env)
    P = {"type": "Project", "id": SANDBOX}
    targets = {}
    for slug, typ in (("shots", "Shot"), ("assets", "Asset"), ("versions", "Version"), ("tasks", "Task")):
        k, d = search(slug, [], size=2, project=SANDBOX)
        if isinstance(k, int) and k:
            targets[typ] = [x["id"] for x in d]
    rows.append(f"\n=== create contract, sandbox project (probe 012: mandatory is not the contract)")
    rows.append(f"  link targets found in the sandbox: { {t: len(v) for t, v in targets.items()} }")
    with _lib.Created(c) as made:
        first = next(iter(targets.items()), None)
        link = {"type": first[0], "id": first[1][0]} if first else None
        attempts = [
            ("neither", {}),
            ("subject alone", {"subject": "zzprobe_note_subject_only"}),
            ("content alone", {"content": "zzprobe_note_body_only"}),
            ("note_links alone", {"note_links": [link]} if link else None),
            ("project alone", {"project": P}),
            ("project + subject", {"project": P, "subject": "zzprobe_note_a"}),
            ("project + subject + content", {"project": P, "subject": "zzprobe_note_b",
                                             "content": "zzprobe_note_b body"}),
            ("project + subject + note_links", {"project": P, "subject": "zzprobe_note_c",
                                                "note_links": [link]} if link else None),
        ]
        for label, body in attempts:
            if body is None:
                rows.append(f"  {label}: skipped, no link target in the sandbox")
                continue
            r = c.post("/entity/notes", headers=JSN, json=body)
            if r.ok:
                d = r.json()["data"]
                made.add("notes", d["id"])
                rows.append(f"  {r.status_code} {label}: id={d['id']} attributes={json.dumps(d['attributes'])}")
                rows.append(f"      note_links={rel(d, 'note_links')} user={rel(d, 'user')} "
                            f"created_by={rel(d, 'created_by')} replies={rel(d, 'replies')} "
                            f"attachments={rel(d, 'attachments')}")
            else:
                show(r, label)

        rows.append("\n=== note_links valid_types, one create per target type")
        for typ, ids in targets.items():
            r = c.post("/entity/notes", headers=JSN,
                       json={"project": P, "subject": f"zzprobe_note_link_{typ}",
                             "note_links": [{"type": typ, "id": ids[0]}]})
            if r.ok:
                made.add("notes", r.json()["data"]["id"])
                rows.append(f"  201 note_links [{typ}] -> {rel(r.json()['data'], 'note_links')}")
            else:
                show(r, f"note_links [{typ}]")
        rows.append("  types absent from note_links valid_types, tried anyway:")
        outside = [("Project", SANDBOX)]
        k, tdata = search("tasks", [], size=1, project=SANDBOX)
        if isinstance(k, int) and k:
            outside.append(("Task", tdata[0]["id"]))
        k, udata = search("human_users", [], fields=("id",), size=1)
        if isinstance(k, int) and k:
            outside.append(("HumanUser", udata[0]["id"]))
        for typ, tid in outside:
            r = c.post("/entity/notes", headers=JSN,
                       json={"project": P, "subject": f"zzprobe_note_link_{typ}",
                             "note_links": [{"type": typ, "id": tid}]})
            if r.ok:
                nid = made.add("notes", r.json()["data"]["id"])
                back = c.get(f"/entity/notes/{nid}", params={"fields": "subject,note_links"})
                rows.append(f"  201 note_links [{typ}] -> {rel(r.json()['data'], 'note_links')}, "
                            f"re-read {rel(back.json()['data'], 'note_links')}")
            else:
                show(r, f"note_links [{typ}]")

        rows.append("\n=== a bare list replaces the whole note_links set (field_types/multi_entity)")
        multi = [{"type": t, "id": v[0]} for t, v in list(targets.items())[:2]]
        if len(multi) == 2:
            r = c.post("/entity/notes", headers=JSN,
                       json={"project": P, "subject": "zzprobe_note_replace", "note_links": multi})
            nid = made.add("notes", r.json()["data"]["id"]) if r.ok else None
            rows.append(f"  created with two links -> {rel(r.json()['data'], 'note_links')}")
            r = c.put(f"/entity/notes/{nid}", headers=JSN, json={"note_links": [multi[0]]})
            rows.append(f"  PUT note_links [one of them] -> {r.status_code} {rel(r.json()['data'], 'note_links')}")
            r = c.put(f"/entity/notes/{nid}", headers=JSN,
                      json={"note_links": {"multi_entity_update_mode": "add", "value": [multi[1]]}})
            rows.append(f"  PUT note_links add mode -> {r.status_code} {rel(r.json()['data'], 'note_links')}")
        else:
            rows.append("  fewer than two link target types in the sandbox; skipped")

        rows.append("\n=== threading, measured: does a Reply attach from the Reply side?")
        r = c.post("/entity/notes", headers=JSN, json={"project": P, "subject": "zzprobe_note_thread"})
        tid = made.add("notes", r.json()["data"]["id"]) if r.ok else None
        if tid:
            replies = {}
            for label, body in (("entity + content", {"entity": {"type": "Note", "id": tid},
                                                      "content": "zzprobe_reply_body"}),
                                ("content alone", {"content": "zzprobe_reply_orphan"})):
                r = c.post("/entity/replies", headers=JSN, json=body)
                if r.ok:
                    d = r.json()["data"]
                    replies[label] = d["id"]
                    rows.append(f"  201 POST /entity/replies {label}: id={d['id']} "
                                f"attributes={json.dumps(d['attributes'])} entity={rel(d, 'entity')}")
                else:
                    show(r, f"POST /entity/replies {label}")
            r = c.get(f"/entity/notes/{tid}", params={"fields": "subject,replies"})
            rows.append(f"  the Note read back after the Reply: replies={rel(r.json()['data'], 'replies')}")
            r = c.put(f"/entity/notes/{tid}", headers=JSN, json={"replies": []})
            rows.append(f"  PUT Note.replies [] -> {r.status_code} "
                        + (rel(r.json()["data"], "replies") if r.ok else ""))
            if not r.ok:
                rows.append("   " + err(r).replace("\n", "\n   "))
            back = c.get(f"/entity/notes/{tid}", params={"fields": "subject,replies"})
            rows.append(f"  re-read after that PUT: replies={rel(back.json()['data'], 'replies')}")

            # Deleting a Reply is its own problem, and an orphan one outlives the run unless adopted.
            for label, rid in replies.items():
                d = c.delete(f"/entity/replies/{rid}")
                rows.append(f"  DELETE /entity/replies/{rid} ({label}) -> {d.status_code}")
                if not d.ok:
                    rows.append("   " + err(d).replace("\n", "\n   "))
                    a = c.put(f"/entity/replies/{rid}", headers=JSN,
                              json={"entity": {"type": "Note", "id": tid}})
                    d2 = c.delete(f"/entity/replies/{rid}")
                    rows.append(f"  PUT entity onto it -> {a.status_code}, DELETE again -> {d2.status_code}")
                k, _ = search("replies", [["id", "is", rid]], size=1)
                rows.append(f"  _search for reply {rid} afterwards -> {k} row(s)")

        rows.append("\n=== attachments: can they be set in the same POST as the Note?")
        af, ap = props("Note", "attachments")
        rows.append(f"  Note.attachments data_type={af.get('data_type')} editable={af.get('editable')} "
                    f"valid_types={ap.get('valid_types')}")
        k, adata = search("attachments", [], fields=("id",), size=2, project=SANDBOX)
        rows.append(f"  attachments already in the sandbox project: {k}")
        att = None
        r = c.post("/entity/attachments", headers=JSN, json={"project": P})
        if r.ok:
            att = made.add("attachments", r.json()["data"]["id"])
            rows.append(f"  201 POST /entity/attachments {{project}} -> id={att}")
        else:
            show(r, "POST /entity/attachments {project}")
            if isinstance(k, int) and k:
                att = adata[0]["id"]
                rows.append(f"  falling back to an existing sandbox attachment id={att}")
        if att:
            body = {"project": P, "subject": "zzprobe_note_attach_at_create",
                    "attachments": [{"type": "Attachment", "id": att}]}
            r = c.post("/entity/notes", headers=JSN, json=body)
            if r.ok:
                d = r.json()["data"]
                made.add("notes", d["id"])
                rows.append(f"  201 create with attachments in the same call -> {rel(d, 'attachments')}")
                back = c.get(f"/entity/notes/{d['id']}", params={"fields": "subject,attachments"})
                rows.append(f"  re-read -> {rel(back.json()['data'], 'attachments')}")
                r = c.put(f"/entity/notes/{d['id']}", headers=JSN, json={"attachments": []})
                rows.append(f"  PUT attachments [] on the same note -> {r.status_code} "
                            + (rel(r.json()['data'], 'attachments') if r.ok else ""))
                if not r.ok:
                    rows.append("   " + err(r).replace("\n", "\n   "))
            else:
                show(r, "create with attachments in the same call")
            plain = c.post("/entity/notes", headers=JSN, json={"project": P, "subject": "zzprobe_note_attach_after"})
            if plain.ok:
                pid = made.add("notes", plain.json()["data"]["id"])
                r = c.put(f"/entity/notes/{pid}", headers=JSN,
                          json={"attachments": [{"type": "Attachment", "id": att}]})
                rows.append(f"  second pass: PUT attachments on an existing note -> {r.status_code} "
                            + (rel(r.json()['data'], 'attachments') if r.ok else ""))
                if not r.ok:
                    rows.append("   " + err(r).replace("\n", "\n   "))
                r = c.put(f"/entity/attachments/{att}", headers=JSN,
                          json={"attachment_links": [{"type": "Note", "id": pid}]})
                rows.append(f"  the other direction: PUT Attachment.attachment_links [Note] -> {r.status_code} "
                            + (rel(r.json()['data'], 'attachment_links') if r.ok else ""))
                if not r.ok:
                    rows.append("   " + err(r).replace("\n", "\n   "))
        else:
            rows.append("  no attachment available to link; attachments-at-create untested")

        rows.append("\n=== what a fresh Note reads back, and what is refused on update")
        r = c.post("/entity/notes", headers=JSN, json={"project": P, "subject": "zzprobe_note_defaults"})
        if r.ok:
            d = r.json()["data"]
            made.add("notes", d["id"])
            rows.append(f"  201 attributes: {json.dumps(d['attributes'])}")
            rows.append(f"  201 relationship keys: {sorted(d.get('relationships') or {})}")
            for field, value in (("cached_display_name", "zzprobe_note_display"),
                                 ("meta", {"zzprobe": 1})):
                rr = c.put(f"/entity/notes/{d['id']}", headers=JSN, json={field: value})
                tail = json.dumps(rr.json()["data"]["attributes"].get(field)) if rr.ok else ""
                rows.append(f"  PUT {field} -> {rr.status_code} {tail}")
                if not rr.ok:
                    rows.append("   " + err(rr).replace("\n", "\n   "))

actual = "\n".join(rows)
_lib.emit("entity_types/Note", actual, env)
