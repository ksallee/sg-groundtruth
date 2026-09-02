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
KIDS = 91          # the only project on this site with a real publish history
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
_lib.register_from(r.json())
rows.append(f"  {r.json()['data']['summaries']['id']} on the whole site:")
for g in r.json()["data"]["groups"]:
    rows.append(f"    {str(g['group_name'])!r:<34} {g['summaries']['id']}")

PROJ = ["project", "is", {"type": "Project", "id": KIDS}]
rows.append("\n  by type, and whether `path` resolves to a file that exists:")
types = summarize("published_files", [PROJ], "published_file_type").json()["data"]["groups"]
for g in types:
    t = str(g["group_name"])
    if not t:
        continue
    r = search("published_files", [PROJ, ["published_file_type.PublishedFileType.code", "is", t]],
               ["code", "path"], 5)
    paths = [(d["attributes"].get("path") or {}) for d in r.json()["data"]]
    for pp in paths:
        _lib.register_path(pp.get("local_path_mac") or pp.get("relative_path"))
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
_lib.register_from(r.json())
p = d["attributes"]["path"]
_lib.register_path(p.get("local_path_mac"))
_lib.register_path(p.get("relative_path"))
rows.append("  " + json.dumps({k: p.get(k) for k in
            ("link_type", "relative_path", "local_path_mac", "local_path_windows",
             "local_path_linux", "local_storage")}, indent=2).replace("\n", "\n  "))
store = c.get("/entity/local_storages", params={"fields": "code,mac_path,windows_path,linux_path"})
_lib.register_from(store.json())
rows.append("  LocalStorage entities on this site:")
for s in store.json()["data"]:
    _lib.register_path(s["attributes"].get("mac_path"))
    rows.append(f"    {s['id']} {json.dumps(s['attributes'])}")

rows.append("\n=== tier 2: the path fields on the Version itself")
for f in ("sg_path_to_movie", "sg_path_to_frames"):
    r = summarize("versions", [PROJ, [f, "is_not", None]])
    n = r.json()["data"]["summaries"]["id"] if r.ok else r.text[:60]
    rows.append(f"  {f:<20} {n}/{tot}")
r = search("versions", [PROJ, ["sg_path_to_movie", "is_not", None]],
           ["code", "sg_path_to_movie"], 4)
_lib.register_from(r.json())
for d in r.json()["data"]:
    path = d["attributes"]["sg_path_to_movie"]
    _lib.register_path(path)
    rows.append(f"    exists={os.path.exists(path)}  {path}")

rows.append("\n=== tier 3: uploaded media")
r = search("versions", [PROJ], ["code", "image", "sg_uploaded_movie"], 1)
_lib.register_from(r.json())
a = r.json()["data"][0]["attributes"]
rows.append(f"  image             {type(a.get('image')).__name__} -> "
            f"{'presigned S3 URL in the field itself' if isinstance(a.get('image'), str) else a.get('image')}")
mv = a.get("sg_uploaded_movie")
rows.append(f"  sg_uploaded_movie {type(mv).__name__} keys={list(mv) if isinstance(mv, dict) else mv}")
bad = summarize("versions", [PROJ, ["sg_uploaded_movie", "is_not", None]])
rows.append(f"  filtering sg_uploaded_movie is_not None -> {bad.status_code} "
            f"{'' if bad.ok else bad.json()['errors'][0]['title'][:70]}")

actual = "\n".join(rows).replace(HOME, "<home>")
_lib.record("021_media_resolution",
            "POST /entity/published_files/_search + GET /entity/versions",
            "A Version's media resolves through its PublishedFiles, then its path fields, then the upload.",
            actual,
            "All three tiers exist; only the LAST is reliable, and the first is not testable here. "
            "THE REUSABLE TRUTH: `path` on a PublishedFile arrives with the LocalStorage join ALREADY "
            "DONE - local_path_mac / local_path_windows / local_path_linux are filled by the server "
            "alongside relative_path and the local_storage hash, so a client NEVER reads LocalStorage "
            "or reassembles a root. But which types carry a path is not uniform: Maya Scene (5/5) and "
            "Alembic Cache (2/2) carry one and the files exist on the mount, Movie (4/4) carries one "
            "and NONE of the files exist, and Image, Rendered Image, Texture and USD carry NO path at "
            "all - so precisely the types a Fetch node wants are the ones with nothing to load. "
            "Traversal is worse: published_files is filled on 2 of 53 Versions and `version` is null on "
            "180 of 182 PFs, so walking Version -> PublishedFile finds nothing on this site. Tier 2 "
            "sg_path_to_movie is filled 28/53 and the sampled paths DO exist, but they are ad-hoc user "
            "paths under Downloads and Documents rather than a shared root - readable, not portable - "
            "and sg_path_to_frames is 0/53, so the %04d sequence form is untested. Tier 3 always "
            "resolves and needs no second call: `image` IS a presigned S3 URL as a plain string and "
            "sg_uploaded_movie is a dict carrying the same under `url`. Note sg_uploaded_movie cannot "
            "be filtered or summarized `is_not None` at all - 400, \"\'url\' data type cannot be\" - "
            "the same shape of trap as a checkbox (probe 020). Build the Fetch node on tier 3, keep "
            "tier 2 as an opt-in, and treat the PublishedFile tier as UNPROVEN until a site with a real "
            "publish history exists to probe.",
            env, tags=("version", "media", "published-file", "path", "storage", "inspector", "query"))
print(actual)
