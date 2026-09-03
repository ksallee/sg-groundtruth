#!/usr/bin/env python3
"""Weekly client status report for one Flow Production Tracking project.

    python weekly_report.py <project id>

Writes report.csv, one row per Version, oldest first, then attaches it to the
project's most recent Note.
"""

import csv
import json
import os
import sys

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
ENV = os.path.join(HERE, ".env")
OUT = os.path.join(HERE, "report.csv")

COLUMNS = ["version", "status", "shot", "created_by", "created_at", "movie"]

# Entity fields are returned under relationships, never attributes (finding 003).
# entity.Shot.code is null on a row whose entity is an Asset (field_types/entity).
VERSION_FIELDS = "code,sg_status_list,created_at,entity,entity.Shot.code,created_by,sg_uploaded_movie"

JSON = {"Content-Type": "application/json"}
# _search and _summarize refuse application/json (finding 004).
SEARCH = {"Content-Type": "application/vnd+shotgun.api3_array+json"}


def load_env(path):
    cfg = {}
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                cfg[k.strip()] = v.strip().strip('"').strip("'")
    return cfg


class FPT:
    """Thin client. Re-auths rather than storing refresh state (finding 001)."""

    def __init__(self, cfg):
        self.base = cfg["FPT_API_SITE_URL"].rstrip("/") + "/api/v1"
        self.creds = {
            "grant_type": "client_credentials",
            "client_id": cfg["FPT_API_SCRIPT_NAME"],
            "client_secret": cfg["FPT_API_API_KEY"],
        }
        self.s = requests.Session()
        self.s.headers["Accept"] = "application/json"
        self.calls = 0
        self._auth()

    def _auth(self):
        self.calls += 1
        r = self.s.post(self.base + "/auth/access_token", data=self.creds)
        r.raise_for_status()
        # expires_in is 600s exactly, so a long run must re-auth (finding 001).
        self.s.headers["Authorization"] = "Bearer " + r.json()["access_token"]

    def call(self, method, path, **kw):
        # links.complete_upload is returned already carrying the /api/v1 prefix,
        # while every path this script writes by hand is relative to it. Prefix
        # twice and the API answers 404 "Not Found" with a null source, which
        # reads as "wrong entity", not "wrong URL".
        if path.startswith("/api/v1/"):
            path = path[len("/api/v1"):]
        url = path if path.startswith("http") else self.base + path
        self.calls += 1
        r = self.s.request(method, url, **kw)
        if r.status_code == 401:
            self._auth()
            self.calls += 1
            r = self.s.request(method, url, **kw)
        if r.status_code >= 400:
            raise SystemExit(f"{method} {path} -> {r.status_code} {r.text[:600]}")
        return r

    def get(self, path, **kw):
        return self.call("GET", path, **kw)

    def post(self, path, **kw):
        return self.call("POST", path, **kw)


def page_all(fpt, path, params):
    """Stop on an empty data array. links.next is present forever, empty pages
    included, so following it until absent never terminates (finding 006)."""
    rows = []
    number = 1
    while True:
        p = dict(params, **{"page[size]": 200, "page[number]": number})
        data = fpt.get(path, params=p).json()["data"]
        if not data:
            return rows
        rows.extend(data)
        number += 1


def link(row, field):
    return ((row.get("relationships") or {}).get(field) or {}).get("data")


def movie_url(value):
    """sg_uploaded_movie is a url field: an object, not a string. A link_type of
    'local' has no url key at all (field_types/url). The url is presigned and
    re-minted per read, so it expires."""
    if not isinstance(value, dict):
        return ""
    return value.get("url") or ""


def version_rows(fpt, project_id):
    # id is the tiebreak for rows written in the same second. A sort on an
    # unsortable field is a silent 200 no-op, and finding 026 records both of
    # these as sorts that do reorder.
    raw = page_all(fpt, "/entity/versions", {
        "filter[project.Project.id]": project_id,
        "fields": VERSION_FIELDS,
        "sort": "created_at,id",
    })
    out = []
    for row in raw:
        a = row["attributes"]
        entity = link(row, "entity")
        # entity is polymorphic: Shot, Asset, Sequence and more (finding 005).
        shot = a.get("entity.Shot.code") or "" if (entity or {}).get("type") == "Shot" else ""
        created_by = link(row, "created_by") or {}
        out.append({
            "version": a.get("code") or "",
            "status": a.get("sg_status_list") or "",
            "shot": shot,
            "created_by": created_by.get("name") or "",
            "created_at": a.get("created_at") or "",
            "movie": movie_url(a.get("sg_uploaded_movie")),
        })
    return out


def latest_note(fpt, project_id):
    r = fpt.get("/entity/notes", params={
        "filter[project.Project.id]": project_id,
        "fields": "subject,created_at",
        "sort": "-created_at,-id",
        "page[size]": 1,
    })
    data = r.json()["data"]
    if not data:
        raise SystemExit(f"project {project_id} has no Note to attach to")
    return data[0]


def note_attachments(fpt, note_id):
    """A multi_entity field cannot be filtered by flat filter[]; only a _search
    body can hold the {type, id} hash (finding 014)."""
    return fpt.post("/entity/attachments/_search", headers=SEARCH, data=json.dumps({
        "filters": [["attachment_links", "is", {"type": "Note", "id": note_id}]],
        "fields": "filename",
    })).json()["data"]


def attach(fpt, note_id, path):
    """Three calls (findings 013, 014). No field in the _upload path stores the
    file as an Attachment on attachment_links, which is the same relation the
    Note reads back as `attachments`. Nothing writes Note.attachments directly:
    a bare multi_entity write would replace the set (entity_types/Note)."""
    name = os.path.basename(path)
    before = {r["id"] for r in note_attachments(fpt, note_id)}

    init = fpt.get(f"/entity/notes/{note_id}/_upload", params={"filename": name}).json()

    with open(path, "rb") as fh:
        payload = fh.read()
    fpt.calls += 1
    put = requests.put(init["links"]["upload"], data=payload)  # presigned S3, no auth header
    if put.status_code >= 400:
        raise SystemExit(f"PUT upload -> {put.status_code} {put.text[:600]}")

    # complete_upload takes application/json; the vendor type 415s here (014).
    # upload_data must be present even though it is empty (013).
    done = fpt.post(init["links"]["complete_upload"], headers=JSON,
                    json={"upload_info": init["data"], "upload_data": {}})

    # The completion answers 201 with a body that is not JSON, so it never names
    # the row it made. Parse defensively, then read the Attachment back.
    try:
        got = ((done.json() or {}).get("data") or {}).get("id")
    except ValueError:
        got = None
        print(f"complete_upload -> {done.status_code}, body {done.text!r}, no id in it; "
              f"reading the Attachment back", file=sys.stderr)
    if got:
        return got

    # Name the row by what appeared, not by "the newest report.csv": this Note
    # can be written by anything else at the same time, and a filename is not
    # unique on it. Nothing about an Attachment is (entity_types/Attachment).
    fresh = [r["id"] for r in note_attachments(fpt, note_id)
             if r["id"] not in before and r["attributes"].get("filename") == name]
    if not fresh:
        raise SystemExit(f"upload completed but no new {name} is linked to Note {note_id}")
    return max(fresh)


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: weekly_report.py <project id>")
    project_id = int(sys.argv[1])

    fpt = FPT(load_env(ENV))
    rows = version_rows(fpt, project_id)

    with open(OUT, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)

    print(f"total: {len(rows)}")

    note = latest_note(fpt, project_id)
    attachment_id = attach(fpt, note["id"], OUT)
    print(f"attached Attachment {attachment_id} to Note {note['id']} "
          f"({note['attributes']['subject']!r}, {note['attributes']['created_at']})")
    print(f"api calls: {fpt.calls}")


if __name__ == "__main__":
    main()
