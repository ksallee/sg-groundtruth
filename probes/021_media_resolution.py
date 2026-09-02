"""Q: given a Version, what media can actually be resolved, and in what order?

A Fetch node has three tiers to choose from, best quality first: the PublishedFiles hanging off the
Version, then sg_path_to_movie / sg_path_to_frames, then the uploaded media. This asks which of them
this site can actually deliver — metadata that resolves to nothing is not a tier.
"""
import json
import os

import _lib

env = _lib.load_env()
c = _lib.client()
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
PROJECT = next(  # the sample project that actually has publish history; ids are site data
    (pid for pid in _lib.sample_projects(c, env)
     if c.get("/entity/published_files",
              params={"filter[project.Project.id]": pid, "page[size]": 1}).json()["data"]),
    _lib.sample_projects(c, env)[0])
HOME = os.path.expanduser("~")
rows = []


def summarize(entity, filters, grouping=None):
    body = {"filters": filters, "summary_fields": [{"field": "id", "type": "count"}]}
    if grouping:
        body["grouping"] = [{"field": grouping, "type": "exact", "direction": "asc"}]
    return c.post(f"/entity/{entity}/_summarize", headers=ARR, json=body)


def search(entity, filters, fields, size=3):
    return c.post(f"/entity/{entity}/_search", headers=ARR,
                  json={"filters": filters, "fields": fields, "page": {"size": size}})


rows.append("=== tier 1: PublishedFiles")
r = summarize("published_files", [], "project")
_lib.note_from(r.json())
rows.append(f"  {r.json()['data']['summaries']['id']} on the whole site:")
for g in r.json()["data"]["groups"]:
    rows.append(f"    {str(g['group_name'])!r:<34} {g['summaries']['id']}")

PROJ = ["project", "is", {"type": "Project", "id": PROJECT}]
rows.append("\n  by type, and whether `path` resolves to a file that exists.")
rows.append("  NOTE: a missing file is NOT evidence about the API — the operator deleted most of these")
rows.append("  from disk. Only the `carries a path` column says anything about Flow PT.")
types = summarize("published_files", [PROJ], "published_file_type").json()["data"]["groups"]
for g in types:
    t = str(g["group_name"])
    if not t:
        continue
    r = search("published_files", [PROJ, ["published_file_type.PublishedFileType.code", "is", t]],
               ["code", "path"], 5)
    paths = [(d["attributes"].get("path") or {}) for d in r.json()["data"]]
    for pp in paths:
        _lib.note_path(pp.get("local_path_mac") or pp.get("relative_path"))
    withpath = [p for p in paths if p.get("local_path_mac")]
    exists = sum(1 for p in withpath if os.path.exists(p["local_path_mac"]))
    rows.append(f"    {t:<18} {g['summaries']['id']:>4} PFs   "
                f"{len(withpath)}/{len(paths)} sampled carry a path, {exists} of those exist on disk")

rows.append("\n  the Version -> PublishedFile link, which is what a Fetch node would traverse:")
tot = summarize("versions", [PROJ]).json()["data"]["summaries"]["id"]
linked = summarize("versions", [PROJ, ["published_files", "is_not", None]]).json()["data"]["summaries"]["id"]
withver = summarize("published_files", [PROJ, ["version", "is_not", None]]).json()["data"]["summaries"]["id"]
rows.append(f"    Versions carrying published_files      {linked}/{tot}")
rows.append(f"    PublishedFiles carrying a version link {withver}/{sum(g['summaries']['id'] for g in types)}")

rows.append("\n=== the `path` field: the server has already done the LocalStorage join")
r = search("published_files", [PROJ, ["path_cache", "is_not", None]], ["code", "path", "path_cache"], 1)
d = r.json()["data"][0]
_lib.note_from(r.json())
p = d["attributes"]["path"]
_lib.note_path(p.get("local_path_mac"))
_lib.note_path(p.get("relative_path"))
rows.append("  " + json.dumps({k: p.get(k) for k in
            ("link_type", "relative_path", "local_path_mac", "local_path_windows",
             "local_path_linux", "local_storage")}, indent=2).replace("\n", "\n  "))
store = c.get("/entity/local_storages", params={"fields": "code,mac_path,windows_path,linux_path"})
_lib.note_from(store.json())
rows.append("  LocalStorage entities on this site:")
for s in store.json()["data"]:
    _lib.note_path(s["attributes"].get("mac_path"))
    rows.append(f"    {s['id']} {json.dumps(s['attributes'])}")

rows.append("\n=== tier 2: the path fields on the Version itself")
for f in ("sg_path_to_movie", "sg_path_to_frames"):
    r = summarize("versions", [PROJ, [f, "is_not", None]])
    n = r.json()["data"]["summaries"]["id"] if r.ok else r.text[:60]
    rows.append(f"  {f:<20} {n}/{tot}")
r = search("versions", [PROJ, ["sg_path_to_movie", "is_not", None]],
           ["code", "sg_path_to_movie"], 4)
_lib.note_from(r.json())
for d in r.json()["data"]:
    path = d["attributes"]["sg_path_to_movie"]
    _lib.note_path(path)
    rows.append(f"    exists={os.path.exists(path)}  {path}")

rows.append("\n=== tier 3: uploaded media")
r = search("versions", [PROJ], ["code", "image", "sg_uploaded_movie"], 1)
_lib.note_from(r.json())
a = r.json()["data"][0]["attributes"]
rows.append(f"  image             {type(a.get('image')).__name__} -> "
            f"{'presigned S3 URL in the field itself' if isinstance(a.get('image'), str) else a.get('image')}")
mv = a.get("sg_uploaded_movie")
rows.append(f"  sg_uploaded_movie {type(mv).__name__} keys={list(mv) if isinstance(mv, dict) else mv}")
bad = summarize("versions", [PROJ, ["sg_uploaded_movie", "is_not", None]])
rows.append(f"  filtering sg_uploaded_movie is_not None -> {bad.status_code} "
            f"{'' if bad.ok else bad.json()['errors'][0]['title']}")

# "tier 3 resolves" is a proportion, not a shape: count the Versions that actually hold an image.
img = summarize("versions", [PROJ, ["image", "is_not", None]]).json()["data"]["summaries"]["id"]
site = summarize("versions", []).json()["data"]["summaries"]["id"]
site_img = summarize("versions", [["image", "is_not", None]]).json()["data"]["summaries"]["id"]
rows.append(f"  image is_not None      {img}/{tot} on this project, {site_img}/{site} site-wide")

actual = "\n".join(rows).replace(HOME, "<home>")
_lib.emit("021_media_resolution", actual, env)
