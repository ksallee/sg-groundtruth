#!/usr/bin/env python3.11
"""Weekly client status report for one Flow Production Tracking project.

    python weekly_report.py <project id>

Writes report.csv (one row per Version, oldest first), prints the total, then
attaches the CSV to the project's most recent Note and prints the Attachment id.
"""

import csv
import os
import sys

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(HERE, "report.csv")
COLUMNS = ["version", "status", "shot", "created_by", "created_at", "movie"]

# Just a batch size. There is no cap here worth working around: page[size]=1000
# really does return 1000 records.
PAGE = 500


def load_env(path):
    env = {}
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                env[key.strip()] = value.strip().strip('"').strip("'")
    return env


class Site:
    def __init__(self, env):
        self.url = env["FPT_API_SITE_URL"].rstrip("/")
        self.session = requests.Session()
        r = self.session.post(
            self.url + "/api/v1/auth/access_token",
            data={
                "grant_type": "client_credentials",
                "client_id": env["FPT_API_SCRIPT_NAME"],
                "client_secret": env["FPT_API_API_KEY"],
            },
            headers={"Accept": "application/json"},
        )
        r.raise_for_status()
        self.session.headers.update(
            {
                "Authorization": "Bearer " + r.json()["access_token"],
                "Accept": "application/json",
            }
        )

    def request(self, method, path, **kw):
        url = path if path.startswith("http") else self.url + path
        r = self.session.request(method, url, **kw)
        if r.status_code >= 400:
            raise SystemExit("%s %s -> %s\n%s" % (method, path, r.status_code, r.text))
        return r

    def get(self, path, **kw):
        return self.request("GET", path, **kw).json()

    def page_all(self, path, params):
        """Walk every page.

        `links.next` is present on every response, including the last one and
        including an empty page past the end, so it cannot be used as the stop
        condition. A short page is the only reliable signal.
        """
        out = []
        number = 1
        while True:
            p = dict(params, **{"page[size]": PAGE, "page[number]": number})
            batch = self.get(path, params=p)["data"]
            out.extend(batch)
            if len(batch) < PAGE:
                return out
            number += 1


def status_labels(site, project_id):
    """Map sg_status_list codes to the labels the site shows, e.g. rev -> Pending Review."""
    props = site.get(
        "/api/v1/schema/Version/fields/sg_status_list",
        params={"project_id": project_id},
    )["data"]["properties"]
    return props["display_values"]["value"]


def versions(site, project_id):
    return site.page_all(
        "/api/v1/entity/versions",
        {
            # A plain filter[project]=<id> is rejected: the field wants a hash,
            # so reach through the link to the id instead.
            "filter[project.Project.id]": project_id,
            "fields": "code,sg_status_list,entity,created_by,created_at,sg_uploaded_movie",
            "sort": "created_at,id",
        },
    )


def shot_codes(site, ids):
    """Resolve Shot codes rather than trusting the name on the link stub."""
    if not ids:
        return {}
    codes = {}
    ids = sorted(ids)
    for i in range(0, len(ids), 100):
        chunk = ids[i : i + 100]
        for shot in site.page_all(
            "/api/v1/entity/shots",
            {"filter[id]": ",".join(str(s) for s in chunk), "fields": "code"},
        ):
            codes[shot["id"]] = shot["attributes"]["code"]
    return codes


def rows(site, project_id):
    records = versions(site, project_id)
    linked = {
        r["relationships"]["entity"]["data"]["id"]
        for r in records
        if (r["relationships"]["entity"]["data"] or {}).get("type") == "Shot"
    }
    codes = shot_codes(site, linked)

    out = []
    for r in records:
        attrs = r["attributes"]
        entity = r["relationships"]["entity"]["data"] or {}
        author = r["relationships"]["created_by"]["data"] or {}
        movie = attrs.get("sg_uploaded_movie") or {}
        out.append(
            {
                "version": attrs.get("code") or "",
                "status": attrs.get("sg_status_list") or "",
                # Only a Shot goes in the shot column. Versions here also link
                # to Assets, and one links to nothing.
                "shot": codes.get(entity["id"], "") if entity.get("type") == "Shot" else "",
                "created_by": author.get("name", ""),
                "created_at": attrs.get("created_at") or "",
                # sg_uploaded_movie.url is a presigned S3 link that expires in
                # 900 seconds, which is useless in a report a client reads on
                # Monday. file_serve is the stable, permission-checked route.
                "movie": "%s/file_serve/attachment/%s" % (site.url, movie["id"]) if movie else "",
            }
        )
    return out


def latest_note(site, project_id):
    notes = site.get(
        "/api/v1/entity/notes",
        params={
            "filter[project.Project.id]": project_id,
            "fields": "subject,created_at",
            "sort": "-created_at,-id",
            "page[size]": 1,
        },
    )["data"]
    if not notes:
        raise SystemExit("project %s has no Note to attach to" % project_id)
    return notes[0]


def attach(site, note_id, path):
    """Three legs: ask for a signed URL, PUT the bytes, then confirm.

    The confirm step returns 201 and creates an Attachment whether or not the
    PUT happened, so the PUT must be checked on its own.
    """
    name = os.path.basename(path)
    before = {
        a["id"] for a in site.get("/api/v1/entity/notes/%s" % note_id, params={"fields": "attachments"})
        ["data"]["relationships"]["attachments"]["data"]
    }

    ticket = site.get(
        "/api/v1/entity/notes/%s/attachments/_upload" % note_id, params={"filename": name}
    )
    with open(path, "rb") as fh:
        body = fh.read()
    put = requests.put(ticket["links"]["upload"], data=body, headers={"Content-Type": "text/csv"})
    if put.status_code >= 400:
        raise SystemExit("upload PUT -> %s\n%s" % (put.status_code, put.text))

    site.request(
        "POST",
        ticket["links"]["complete_upload"],
        json={"upload_info": ticket["data"], "upload_data": {}},
        headers={"Content-Type": "application/json"},
    )

    after = site.get("/api/v1/entity/notes/%s" % note_id, params={"fields": "attachments"})
    fresh = [a for a in after["data"]["relationships"]["attachments"]["data"] if a["id"] not in before]
    if not fresh:
        raise SystemExit("complete_upload reported success but the Note gained no attachment")
    return max(a["id"] for a in fresh)


def main(argv):
    if len(argv) != 2:
        raise SystemExit("usage: weekly_report.py <project id>")
    project_id = argv[1]

    site = Site(load_env(os.path.join(HERE, ".env")))
    labels = status_labels(site, project_id)

    data = rows(site, project_id)
    with open(CSV_PATH, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        for row in data:
            row = dict(row, status=labels.get(row["status"], row["status"]))
            w.writerow(row)

    print("wrote %s" % CSV_PATH)
    print("total: %d" % len(data))

    note = latest_note(site, project_id)
    attachment_id = attach(site, note["id"], CSV_PATH)
    print(
        "attached Attachment %s to Note %s (%r)"
        % (attachment_id, note["id"], note["attributes"]["subject"])
    )


if __name__ == "__main__":
    main(sys.argv)
