#!/usr/bin/env python3
"""Weekly client status report for one Flow Production Tracking project.

    python weekly_report.py <project id>

Writes report.csv (one row per Version), prints `total: <n>`, then attaches the
CSV to the project's most recent Note and prints the attachment id.

Credentials come from .env beside this script:
    FPT_API_SITE_URL, FPT_API_SCRIPT_NAME, FPT_API_API_KEY
"""

from __future__ import annotations

import csv
import json
import sys
import time
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
OUT_CSV = HERE / "report.csv"

PAGE_SIZE = 500
TIMEOUT = 60

VERSION_FIELDS = [
    "code",
    "sg_status_list",
    "entity",
    "created_by",
    "created_at",
    "sg_uploaded_movie",
]


# --------------------------------------------------------------------------- env


def load_env(path: Path) -> dict[str, str]:
    """Minimal .env reader: KEY=VALUE, # comments, optional quotes, optional `export`."""
    env: dict[str, str] = {}
    if not path.exists():
        return env
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        env[key] = value
    return env


# --------------------------------------------------------------------------- client


class FPTError(RuntimeError):
    pass


class FPT:
    """Thin Flow Production Tracking REST v1 client: script auth, retry, pagination."""

    def __init__(self, site_url: str, script_name: str, api_key: str) -> None:
        self.origin = site_url.rstrip("/")
        self.base = self.origin + "/api/v1"
        self.script_name = script_name
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})
        self.token: str | None = None
        self.token_expires_at = 0.0

    # -- auth ---------------------------------------------------------------

    def authenticate(self) -> None:
        resp = self.session.post(
            f"{self.base}/auth/access_token",
            data={
                "grant_type": "client_credentials",
                "client_id": self.script_name,
                "client_secret": self.api_key,
            },
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
            timeout=TIMEOUT,
        )
        if resp.status_code != 200:
            raise FPTError(
                f"auth failed: HTTP {resp.status_code} {resp.text[:500]}\n"
                "Check FPT_API_SITE_URL, FPT_API_SCRIPT_NAME and FPT_API_API_KEY, "
                "and that the script is not disabled on the site."
            )
        payload = resp.json()
        self.token = payload["access_token"]
        # expires_in is seconds; refresh a minute early rather than on the 401.
        self.token_expires_at = time.time() + float(payload.get("expires_in", 600)) - 60

    def _auth_header(self) -> dict[str, str]:
        if self.token is None or time.time() >= self.token_expires_at:
            self.authenticate()
        return {"Authorization": f"Bearer {self.token}"}

    # -- request ------------------------------------------------------------

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict | None = None,
        json_body: object | None = None,
        content_type: str | None = None,
        allow_status: tuple[int, ...] = (),
    ) -> requests.Response:
        # `links.complete_upload` comes back as a site-absolute path, not a
        # bare endpoint name, so it must not be joined onto /api/v1 again.
        if path.startswith("http"):
            url = path
        elif path.startswith("/"):
            url = self.origin + path
        else:
            url = f"{self.base}/{path}"

        for attempt in range(4):
            headers = dict(self._auth_header())
            if json_body is not None:
                headers["Content-Type"] = content_type or "application/json"
            body = None if json_body is None else json.dumps(json_body).encode("utf-8")

            resp = self.session.request(
                method, url, params=params, data=body, headers=headers, timeout=TIMEOUT
            )

            if resp.status_code == 401 and attempt < 3:
                self.token = None  # token expired mid-run; re-auth once and retry
                continue
            if resp.status_code == 429 and attempt < 3:
                time.sleep(float(resp.headers.get("Retry-After", 2 ** attempt)))
                continue
            if resp.status_code >= 500 and attempt < 3:
                time.sleep(2 ** attempt)
                continue

            if resp.status_code >= 400 and resp.status_code not in allow_status:
                raise FPTError(
                    f"{method} {url} -> HTTP {resp.status_code}\n{resp.text[:1000]}"
                )
            return resp

        raise FPTError(f"{method} {url} failed after retries")

    # -- reads --------------------------------------------------------------

    def paginate(self, path: str, params: dict) -> list[dict]:
        """Walk page[number] until a short page comes back.

        `links.next` is not trusted as the terminator: a short page is an
        unambiguous end regardless of whether the link is emitted on the last page.
        """
        records: list[dict] = []
        page = 1
        while True:
            page_params = dict(params)
            page_params["page[size]"] = PAGE_SIZE
            page_params["page[number]"] = page
            payload = self.request("GET", path, params=page_params).json()
            batch = payload.get("data") or []
            records.extend(batch)
            if len(batch) < PAGE_SIZE:
                return records
            page += 1
            if page > 1000:
                raise FPTError(f"pagination did not terminate for {path}")

    def search(
        self,
        entity_type: str,
        filters: list,
        fields: list[str],
        sort: str | None = None,
    ) -> list[dict]:
        """POST /_search with array-style filters.

        The array form needs its own content type; plain application/json is
        rejected because the server cannot tell array filters from hash filters.
        """
        records: list[dict] = []
        page = 1
        while True:
            body: dict = {
                "filters": filters,
                "fields": fields,
                "page": {"size": PAGE_SIZE, "number": page},
            }
            if sort:
                body["sort"] = sort
            payload = self.request(
                "POST",
                f"entity/{entity_type}/_search",
                json_body=body,
                content_type="application/vnd+shotgun.api3_array+json",
            ).json()
            batch = payload.get("data") or []
            records.extend(batch)
            if len(batch) < PAGE_SIZE:
                return records
            page += 1
            if page > 1000:
                raise FPTError(f"pagination did not terminate for {entity_type}/_search")


# --------------------------------------------------------------------------- shaping


def attr(record: dict, name: str, default=None):
    return (record.get("attributes") or {}).get(name, default)


def rel(record: dict, name: str) -> dict | None:
    """An entity link is returned under `relationships`, but a record fetched
    through some paths carries it under `attributes` instead. Read both."""
    relationships = record.get("relationships") or {}
    if name in relationships:
        data = relationships[name]
        if isinstance(data, dict):
            data = data.get("data")
        if isinstance(data, dict):
            return data
        return None
    value = (record.get("attributes") or {}).get(name)
    return value if isinstance(value, dict) else None


def movie_link(record: dict, site_url: str) -> str:
    """Stable link to the uploaded movie.

    The `url` the API returns for an upload is a presigned URL that expires in
    minutes, which is useless in a report a client opens later. `/file_serve/`
    is the durable form, so prefer the attachment id when there is one.
    """
    movie = attr(record, "sg_uploaded_movie") or rel(record, "sg_uploaded_movie")
    if not isinstance(movie, dict):
        return ""
    attachment_id = movie.get("id")
    if attachment_id and movie.get("link_type", "upload") == "upload":
        return f"{site_url.rstrip('/')}/file_serve/attachment/{attachment_id}"
    return movie.get("url") or ""


def resolve_shot_codes(client: FPT, versions: list[dict]) -> dict[int, str]:
    """Fill in Shot codes for links whose `name` was not returned."""
    needed = set()
    for version in versions:
        link = rel(version, "entity")
        if link and link.get("type") == "Shot" and not link.get("name"):
            needed.add(int(link["id"]))
    if not needed:
        return {}
    codes: dict[int, str] = {}
    ids = sorted(needed)
    for start in range(0, len(ids), 200):
        chunk = ids[start:start + 200]
        for shot in client.search("shots", [["id", "in", chunk]], ["code"]):
            codes[int(shot["id"])] = attr(shot, "code") or ""
    return codes


# --------------------------------------------------------------------------- steps


def fetch_versions(client: FPT, project_id: int) -> list[dict]:
    params = {
        "filter[project.Project.id]": project_id,
        "fields": ",".join(VERSION_FIELDS),
        "sort": "created_at",  # oldest first; `-created_at` would be newest first
    }
    try:
        return client.paginate("entity/versions", params)
    except FPTError as exc:
        # Some sites reject the dotted filter key on GET. The search endpoint
        # takes the same condition as a real entity filter.
        if "400" not in str(exc) and "404" not in str(exc):
            raise
        print("note: GET filter rejected, falling back to _search", file=sys.stderr)
        return client.search(
            "versions",
            [["project", "is", {"type": "Project", "id": project_id}]],
            VERSION_FIELDS,
            sort="created_at",
        )


def write_csv(versions: list[dict], shot_codes: dict[int, str], site_url: str) -> None:
    with OUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            ["version", "status", "shot", "created_by", "created_at", "movie"]
        )
        for version in versions:
            link = rel(version, "entity")
            shot = ""
            if link and link.get("type") == "Shot":
                shot = link.get("name") or shot_codes.get(int(link["id"]), "")
            creator = rel(version, "created_by") or {}
            writer.writerow(
                [
                    attr(version, "code") or "",
                    attr(version, "sg_status_list") or "",
                    shot,
                    creator.get("name") or "",
                    attr(version, "created_at") or "",
                    movie_link(version, site_url),
                ]
            )


def latest_note_id(client: FPT, project_id: int) -> int:
    params = {
        "filter[project.Project.id]": project_id,
        "fields": "subject,created_at",
        "sort": "-created_at",
        "page[size]": 1,
        "page[number]": 1,
    }
    try:
        payload = client.request("GET", "entity/notes", params=params).json()
        notes = payload.get("data") or []
    except FPTError:
        notes = client.search(
            "notes",
            [["project", "is", {"type": "Project", "id": project_id}]],
            ["subject", "created_at"],
            sort="-created_at",
        )[:1]
    if not notes:
        raise FPTError(f"project {project_id} has no Note to attach to")
    return int(notes[0]["id"])


def attach_csv_to_note(client: FPT, note_id: int, path: Path) -> int:
    """Three-step upload: ask for a slot, PUT the bytes, tell the site it landed."""
    filename = path.name

    start = client.request(
        "GET",
        f"entity/notes/{note_id}/attachments/_upload",
        params={"filename": filename},
    ).json()
    upload_url = (start.get("links") or {}).get("upload")
    complete_url = (start.get("links") or {}).get("complete_upload")
    upload_info = start.get("data") or {}
    if not upload_url or not complete_url:
        raise FPTError(f"upload handshake returned no links: {json.dumps(start)[:500]}")

    # The presigned URL carries its own signature. Sending the site's
    # Authorization header, or a Content-Type the signature did not include,
    # gets a 403 from the storage service.
    put = requests.put(upload_url, data=path.read_bytes(), timeout=TIMEOUT)
    if put.status_code not in (200, 201, 204):
        raise FPTError(f"storage PUT -> HTTP {put.status_code}\n{put.text[:500]}")

    done = client.request(
        "POST",
        complete_url,
        json_body={"upload_info": upload_info, "upload_data": {}},
    )

    attachment_id = None
    if done.content:
        try:
            body = done.json()
            data = body.get("data") if isinstance(body, dict) else None
            if isinstance(data, dict):
                attachment_id = data.get("id")
        except ValueError:
            pass
    if attachment_id is None:
        attachment_id = newest_attachment_id(client, note_id, filename)
    return int(attachment_id)


def newest_attachment_id(client: FPT, note_id: int, filename: str) -> int:
    """complete_upload does not reliably return the new Attachment, so read it back."""
    attachments = client.search(
        "attachments",
        [
            ["attachment_links", "is", {"type": "Note", "id": note_id}],
            ["filename", "is", filename],
        ],
        ["filename", "created_at"],
        sort="-created_at",
    )
    if not attachments:
        attachments = client.search(
            "attachments",
            [["attachment_links", "is", {"type": "Note", "id": note_id}]],
            ["filename", "created_at"],
            sort="-created_at",
        )
    if not attachments:
        raise FPTError(
            f"upload completed but no Attachment is linked to Note {note_id}"
        )
    return int(attachments[0]["id"])


# --------------------------------------------------------------------------- main


def main(argv: list[str]) -> int:
    if len(argv) != 2 or not argv[1].isdigit():
        print("usage: python weekly_report.py <project id>", file=sys.stderr)
        return 2
    project_id = int(argv[1])

    env = load_env(HERE / ".env")
    missing = [
        key
        for key in ("FPT_API_SITE_URL", "FPT_API_SCRIPT_NAME", "FPT_API_API_KEY")
        if not env.get(key)
    ]
    if missing:
        print(f"missing in .env: {', '.join(missing)}", file=sys.stderr)
        return 2

    site_url = env["FPT_API_SITE_URL"]
    if not site_url.startswith("http"):
        site_url = "https://" + site_url

    client = FPT(site_url, env["FPT_API_SCRIPT_NAME"], env["FPT_API_API_KEY"])

    try:
        client.authenticate()
        versions = fetch_versions(client, project_id)
        shot_codes = resolve_shot_codes(client, versions)
        write_csv(versions, shot_codes, site_url)
        print(f"total: {len(versions)}")

        note_id = latest_note_id(client, project_id)
        attachment_id = attach_csv_to_note(client, note_id, OUT_CSV)
        print(attachment_id)
    except FPTError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except requests.RequestException as exc:
        print(f"network error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
