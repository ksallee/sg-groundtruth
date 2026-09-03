"""Q: which steps of the three-call upload can fail without saying so?

013 records the sequence and 014 records where the file lands when the field is left out. Both describe
the path where every call is made. This probe asks what happens when one of them is skipped or gets its
URL wrong, because three agents building the same reporting script hit three different silent failures
between them and none is recorded.

Four questions:

  1. Does `complete_upload` succeed when the bytes were never PUT?
  2. Is there any field on the resulting Attachment that tells the two apart?
  3. What does `complete_upload` return, and can it be parsed?
  4. Is `links.complete_upload` relative to the site or to the API root?

Writes. Sandbox only, and every row it makes is deleted on the way out.
"""
import json

import requests

import _lib

if not _lib.writes_allowed():
    raise SystemExit("039 writes. Run it with --write; it only ever touches the sandbox project.")

env = _lib.load_env()
c = _lib.client()
SANDBOX = _lib.sandbox_id(c, env)
CSV = b"version,status\nprobe_v001,rev\n"
out = []


def upload_start(note_id):
    """Step one of the three. `filename` is required: without it the call is a 400 naming it."""
    return c.get(f"/entity/notes/{note_id}/attachments/_upload", params={"filename": "report.csv"})


with _lib.Created(c) as made:
    note = c.post("/entity/notes", json={"project": {"type": "Project", "id": SANDBOX},
                                         "subject": "probe 039",
                                         "content": "upload failure modes"}).json()["data"]
    made.add("notes", note["id"])

    # --- 0. the one loud step, recorded so the quiet ones below read against it ----------------
    bare = c.get(f"/entity/notes/{note['id']}/attachments/_upload")
    out.append("**Step one without `filename`**\n")
    out.append("```")
    out.append(f"GET /entity/notes/<id>/attachments/_upload -> {bare.status_code}")
    out.append(_lib.dump((bare.json().get("errors") or [{}])[0].get("source"), 200))
    out.append("```\n")

    # --- 3. what step one hands back, and what the link is relative to -------------------------
    r = upload_start(note["id"])
    body = r.json()
    links = body.get("links") or {}
    out.append("**Step one**\n")
    out.append(f"`GET /entity/notes/<id>/attachments/_upload` -> {r.status_code}")
    out.append(f"links.upload starts: {str(links.get('upload'))[:40]}...")
    out.append(f"links.complete_upload: {links.get('complete_upload')}\n")

    complete = links.get("complete_upload", "")
    out.append("| the link | value |")
    out.append("|---|---|")
    out.append(f"| already carries `/api/v1` | {'yes' if complete.startswith('/api/v1') else 'no'} |")
    out.append(f"| is absolute against the site | {'yes' if complete.startswith('/') else 'no'} |\n")

    # Prefixing an already-prefixed link, which is what a client with a base URL does by default.
    double = c.post(f"/api/v1{complete}" if complete.startswith("/api/v1") else complete,
                    json={"upload_info": body.get("data") or {}, "upload_data": {}})
    out.append("**Prefixing the link a second time**\n")
    out.append("```")
    out.append(f"POST /api/v1{complete} -> {double.status_code}")
    out.append(_lib.dump(double.json() if double.text.strip() else double.text, 300))
    out.append("```\n")

    # --- 1 and 3. complete without ever PUTting the bytes -----------------------------------
    empty = c.post(complete, json={"upload_info": body.get("data") or {}, "upload_data": {}})
    out.append("**`complete_upload` with no PUT to the presigned link**\n")
    out.append("```")
    out.append(f"POST {complete} -> {empty.status_code}")
    out.append(f"content-type: {empty.headers.get('Content-Type')}")
    out.append(f"body: {empty.text[:120]!r}  ({len(empty.text)} chars)")
    out.append("```\n")

    # --- 2. is the empty one distinguishable from a real one? -------------------------------
    def note_attachments(nid):
        rr = c.get(f"/entity/notes/{nid}", params={"fields": "attachments"})
        d = ((rr.json()["data"].get("relationships") or {}).get("attachments") or {}).get("data") or []
        return [x["id"] for x in d]

    after_empty = note_attachments(note["id"])
    for aid in after_empty:
        made.add("attachments", aid)

    # Now the honest path: start again, PUT the bytes, then complete.
    r2 = upload_start(note["id"])
    b2 = r2.json()
    if "links" not in b2:
        out.append("**Starting a second upload on the same Note**\n")
        out.append("```")
        out.append(f"GET /entity/notes/<id>/attachments/_upload -> {r2.status_code}")
        out.append(_lib.dump(b2, 400))
        out.append("```\n")
        _lib.emit("039_upload_silent_failures", "\n".join(out), env)
        raise SystemExit(0)
    put = requests.put((b2["links"]["upload"]), data=CSV, timeout=60)
    good = c.post(b2["links"]["complete_upload"],
                  json={"upload_info": b2.get("data") or {}, "upload_data": {}})
    after_good = [i for i in note_attachments(note["id"]) if i not in after_empty]
    for aid in after_good:
        made.add("attachments", aid)

    out.append("**The two rows side by side**\n")
    out.append(f"PUT to the presigned link -> {put.status_code}\n")
    out.append("| | no PUT | bytes PUT |")
    out.append("|---|---|---|")
    out.append(f"| `complete_upload` status | {empty.status_code} | {good.status_code} |")
    out.append(f"| Attachment row created | {'yes' if after_empty else 'no'} | "
               f"{'yes' if after_good else 'no'} |")

    fields = "filename,file_size,this_file,attachment_links,created_at"
    rows = {}
    for label, ids in (("no PUT", after_empty), ("bytes PUT", after_good)):
        if not ids:
            continue
        d = c.get(f"/entity/attachments/{ids[0]}", params={"fields": fields}).json()["data"]
        url = (d["attributes"].get("this_file") or {}).get("url")
        got = requests.get(url, timeout=60) if url else None
        rows[label] = {
            "filename": d["attributes"].get("filename"),
            "file_size": d["attributes"].get("file_size"),
            "GET the stored file": f"{got.status_code}" if got is not None else "no url",
            "bytes downloaded": (len(got.content) if got is not None and got.ok else None),
        }
    for key in ("filename", "file_size", "GET the stored file", "bytes downloaded"):
        a = rows.get("no PUT", {}).get(key)
        b = rows.get("bytes PUT", {}).get(key)
        out.append(f"| `{key}` | {a!r} | {b!r} |")
    out.append("")
    same = [k for k in ("filename", "file_size")
            if rows.get("no PUT", {}).get(k) == rows.get("bytes PUT", {}).get(k)]
    out.append(f"Identical on both rows: {', '.join(f'`{k}`' for k in same) or 'nothing'}. "
               f"Only fetching the stored file separates them.")

_lib.emit("039_upload_silent_failures", "\n".join(out), env)
