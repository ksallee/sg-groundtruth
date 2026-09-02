---
intent: Register the next PublishedFile without overwriting the last one, and write a path the server resolves for every platform
tags: [write, published-file, path, storage, version, create, entity-field, trap, recipe]
scope: api
---

# 004_register_published_file

## Call

```python
import json
import sys

sys.path.insert(0, "src")                       # or PYTHONPATH=src
from sg_groundtruth.client import FPT           # adds the bearer token and the /api/v1 prefix
from sg_groundtruth.env import load

c = FPT.from_env(load("."))                     # FPT_API_SITE_URL, FPT_API_SCRIPT_NAME, FPT_API_API_KEY
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}   # _search only
JSON = {"Content-Type": "application/json"}

PROJECT_ID = 1234                               # the caller supplies these five
SHOT_ID = 7514
TYPE_CODE = "<type>"                            # a code from GET /entity/published_file_types
STORAGE_CODE = "<storage>"                      # a code from GET /entity/local_storages
NAME = "charA.ma"                               # the publish stream; `code` is one version of it

# 1. The storage roots, read once per session. A local path must sit under one of them.
storages = c.get("/entity/local_storages",
                 params={"fields": "code,mac_path,windows_path,linux_path"}).json()["data"]
storage = next(s for s in storages if s["attributes"]["code"] == STORAGE_CODE)  # by code, not position
root = storage["attributes"]["mac_path"]        # the root for the platform this client runs on


# 2. The next version number. Descending sort, one row. Nothing on the server enforces the answer.
def next_version(name):
    r = c.post("/entity/published_files/_search", headers=ARR, json={
        "filters": [["project", "is", {"type": "Project", "id": PROJECT_ID}],
                    ["name", "is", name]],
        "fields": ["code", "name", "version_number"],
        "sort": ["-version_number"], "page": {"size": 1}})
    rows = r.json()["data"]
    return (rows[0]["attributes"]["version_number"] or 0) + 1 if rows else 1


n = next_version(NAME)

# 3. Resolve the type by code. Matching is case-insensitive, so normalise before deciding it is absent.
types = c.get("/entity/published_file_types", params={"fields": "code"}).json()["data"]
match = [t for t in types if t["attributes"]["code"].strip().lower() == TYPE_CODE.strip().lower()]
# On a miss, creating the type adds it to every project on the site. Gate it behind an allowlist:
#   c.post("/entity/published_file_types", headers=JSON, json={"code": TYPE_CODE})   # not run here
pft = {"type": "PublishedFileType", "id": match[0]["id"]} if match else None

# 4. One create. Forward slashes only, and the server splits the root off {local_path}.
local_path = f"{root}/assets/charA/publish/maya/charA.v{n:03d}.ma".replace("\\", "/")
body = {
    "project": {"type": "Project", "id": PROJECT_ID},
    "name": NAME,                                       # the stream
    "code": f"charA.v{n:03d}.ma",                       # this version of it
    "version_number": n,
    "path": {"local_path": local_path},
    "entity": {"type": "Shot", "id": SHOT_ID},          # links are {type, id}; a bare id 400s
    "sg_status_list": "cmpt",
    # "task":    {"type": "Task",    "id": TASK_ID},
    # "version": {"type": "Version", "id": VERSION_ID},
}
if pft:
    body["published_file_type"] = pft
r = c.post("/entity/published_files", headers=JSON, json=body)
if not r.ok:
    raise SystemExit(json.dumps(r.json()["errors"], indent=2))
pf = r.json()["data"]
path = pf["attributes"]["path"]                 # resolved in the 201 already; no read-back needed

# 5. Defensive: the storage the server chose against the one this client meant.
got = (path.get("local_storage") or {}).get("id")
if got != storage["id"]:
    c.put(f"/entity/published_files/{pf['id']}", headers=JSON, json={
        "path": {"relative_path": local_path[len(root):].lstrip("/"),
                 "local_storage": {"type": "LocalStorage", "id": storage["id"]}}})
    # The corrective write mints a second Attachment and leaves the first unreferenced.
```

## Response

The version query on a `name` nothing has published, then the same sort over rows that exist:

```
POST /entity/published_files/_search  sort=["-version_number"] page.size=1
  new name        -> 200, 0 rows              -> next = 1
  after v001      -> 200, 1 row,  9 rows/site -> version_number descending [9, 9, 8, 8, 8]
```

`POST /entity/published_files` -> 201, and `attributes.path` in that 201 body is the resolved object,
not the `{"local_path": ...}` that was sent:

```json
{ "link_type": "local",
  "name": "charA.v001.ma",
  "content_type": "application/mathematica",
  "local_storage": {"type": "LocalStorage", "id": 3, "name": "primary"},
  "relative_path": "assets/charA/publish/maya/charA.v001.ma",
  "local_path_mac": "<storage-root>/assets/charA/publish/maya/charA.v001.ma",
  "local_path_windows": null,
  "local_path_linux": null,
  "type": "Attachment", "id": 2133 }
```

One write filled `local_storage`, `relative_path`, `content_type` and every `local_path_*` whose root the
LocalStorage row defines. On the probed site that row sets `mac_path` and leaves `windows_path` and
`linux_path` null, so two of the three platform paths read back null: the cross-platform payoff is the
server doing the join, and how many platforms it covers is the storage row's configuration, not the write.
`path_cache` stays null (`entity_types/PublishedFile`).

What the four path shapes do, all sent to `POST /entity/published_files`:

| `path` sent | result |
|---|---|
| `{"local_path": "<storage-root>/assets/charA/publish/maya/charA.v001.ma"}` | 201, `local_storage` id 3 |
| `{"relative_path": "assets/charA/publish/maya/charA.v001.ma", "local_storage": {"type": "LocalStorage", "id": 3}}` | 201, `local_storage` id 3, same read shape |
| `{"relative_path": "assets/charA/publish/maya/charA.v001.ma"}`, no storage | 400 code 103 |
| `{"local_path": "/no_such_root/assets/charA/publish/maya/charA.v001.ma"}` | 400 code 104 |

```
{"relative_path": …} alone
  400 code 103  API create() invalid/missing url hash string 'url': {"relative_path" =>
                "assets/charA/publish/maya/charA.v001.ma"}

{"local_path": …} outside every root
  400 code 104  Create failed for [Attachment]: Path
                /no_such_root/assets/charA/publish/maya/charA.v001.ma doesn't match any defined
                Local Storage.
```

**Storage correction, not reproduced here.** The operator claim is that the server sometimes attaches the
wrong LocalStorage to a relative-path publish, most often on Windows where the roots are bare drive letters
and two rows match the same path. On the probed site there is one LocalStorage row, so no path is ambiguous
and no shape returned anything but id 3. Step 5 is written as a check rather than a fix for that reason, and
is **unverified against a multi-storage site**. The corrective write itself does work:

```
PUT /entity/published_files/<id>  {"path": {"relative_path": …, "local_storage": {…}}}
  -> 200, local_storage id 3, Attachment id 2136 before -> 2138 after
```

**Backslashes are rejected**, and by two different errors depending on which key holds them. A single
backslash is enough: the third case below is an otherwise valid forward-slash path with one separator
before the filename.

| `path` sent | result |
|---|---|
| `{"relative_path": "assets\\charA\\publish\\maya\\charA.v001.ma", "local_storage": {…}}` | 400 code 103 |
| `{"local_path": "\\Volumes\\<root>\\assets\\charA\\publish\\maya\\charA.v001.ma"}` | 400 code 104 |
| `{"relative_path": "assets/charA/publish/maya\\charA.v001.ma", "local_storage": {…}}` | 400 code 103 |

```
relative_path with backslashes
  400 code 103  API create() invalid/missing relative_path hash string 'relative_path':
                {"relative_path" => "assets\\charA\\publish\\maya\\charA.v001.ma",
                 "local_storage" => {"type" => "LocalStorage", "id" => 3}}

local_path with backslashes
  400 code 104  Create failed for [Attachment]: Path
                \Volumes\<root>\assets\charA\publish\maya\charA.v001.ma doesn't match any defined
                Local Storage.
```

A `local_path` written with backslashes never matches a root, so it fails as an unknown storage rather than
as a malformed path. Replace the separators before the call, as `.replace("\\", "/")` does in step 4.

The links, read back from the create in one call:

```
attributes    {"code": "charA.v003.ma", "name": "charA.ma", "version_number": 3,
               "sg_status_list": "cmpt"}
relationships {"entity":              {"type": "Shot",              "id": 7514,  "name": "sh010"},
               "task":                {"type": "Task",              "id": 46691, "name": "rig"},
               "version":             {"type": "Version",           "id": 31648, "name": "charA.v001"},
               "published_file_type": {"type": "PublishedFileType",  "id": 1,     "name": "<type>"}}

published_file_type as a bare id ->
  400 code 103  API create() PublishedFile.published_file_type expected [Hash,
                ActiveSupport::HashWithIndifferentAccess, ActionDispatch::Http::Parameters,
                ActionDispatch::Http::ParamsHashWithIndifferentAccess, NilClass] data type(s)
                but got Integer: 1
```

## Notes

- **The version query is the whole guard, and it is a read-then-write race.** No field on PublishedFile is
  unique and no combination is enforced, so the identical body posted twice returns two 201s and there is no
  conflict error to catch (`entity_types/PublishedFile`). Two clients that read `next_version` at the same
  moment both publish version 4. The API offers nothing to close this: no unique constraint to create, no
  conditional write, no returned row to lose the race against. What a client can do is narrow the query to
  the same context it publishes into (`name` plus `project`, plus `entity` or `task` if the stream is scoped
  to one), re-run it immediately before the create, and treat the answer as advisory. Production code pairs
  it with a filesystem probe of the publish directory and a retry cap because either source alone goes stale;
  that belongs in the client, and the API cannot confirm or deny what the retry found.
- **Each accepted path write mints an Attachment**, on the create and again on every corrective `PUT`. The
  id is inside the `path` object. Nothing removes the previous one, so a publish loop that rewrites paths
  accumulates Attachment rows silently. Delete by `DELETE /entity/attachments/<id>`, which answered 204.
- **Creating a PublishedFileType for an unknown extension adds it to every project on the site.**
  PublishedFileType has no `project` field and no filter narrows it (`entity_types/PublishedFileType`).
  Resolve against the full listing with a case-normalised compare, and create only from an allowlist. The
  create call is shown in step 3 and was not run for this reason.
- The 201 body already holds the resolved `path`, so a publish needs no read-back to log the paths it wrote.
  This is the one place a create returns more than it was sent; `?fields` on a write is still ignored
  (probe 024).
- `path_cache` is null after a REST create even though the path resolved. A filter on `path_cache` misses
  every row published this way (`entity_types/PublishedFile`).
- `sg_status_list` takes a raw code from the field's `valid_values` minus the project's `hidden_values`
  (probe 009, `field_types/status_list`). On the probed site the set is `['wtg', 'ip', 'cmpt']`.
- Reading the path back later: `GET /entity/published_files/<id>?fields=path` returns the `local` shape,
  which has no `url` key, so `value["url"]` raises on exactly the shape a publish writes. Test `link_type`
  first (`field_types/url`, probe 021).
