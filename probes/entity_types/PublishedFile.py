"""Q: what is a PublishedFile, how is it addressed, identified, created, versioned and linked?

The map for the type. Probe 021 established that `path` is returned with the LocalStorage join
already done and field_types/url the three shapes a url field returns; neither says what the server
requires on create, whether `name` + `version_number` is enforced anywhere, or how a client puts a
local path on a row in the first place. This asks that.

Read-only half runs ungated. Writes need --write and go only into the sandbox project.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _lib  # noqa: E402

env = _lib.load_env()
c = _lib.client()
PROJECT = _lib.sample_projects(c, env)[0]
JSN = {"Content-Type": "application/json"}
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
rows = []


def prop(meta, key):
    return (meta.get("properties", {}).get(key) or {}).get("value")


def errors(r):
    """Whole errors[] object. A sliced 400 loses the half worth having."""
    try:
        return json.dumps(r.json().get("errors"), indent=1)
    except ValueError:
        return r.text


# --------------------------------------------------------------- slug
rows.append("=== REST path slug: which spelling answers")
for slug in ("published_files", "published_file", "PublishedFile", "PublishedFiles",
             "publishedfiles", "publishedFile", "Published_File", "publish_files"):
    r = c.get(f"/entity/{slug}", params={"fields": "code", "page[size]": 1})
    if not r.ok:
        rows.append(f"  GET /entity/{slug:16} -> {r.status_code}\n{errors(r)}")
        continue
    d = r.json()["data"]
    rows.append(f"  GET /entity/{slug:16} -> 200  rows={len(d)} "
                f"data[0].type={d[0]['type'] if d else None!r}")
r = c.post("/entity/published_files/_search", headers=ARR,
           json={"filters": [], "fields": ["code"], "page": {"size": 1}})
rows.append(f"  POST /entity/published_files/_search -> {r.status_code}")

# --------------------------------------------------------------- scope
rows.append("\n=== project-scoped or site-wide")
schema = c.get("/schema/PublishedFile/fields").json()["data"]
p = schema.get("project", {})
rows.append(f"  project field: data_type={(p.get('data_type') or {}).get('value')} "
            f"valid_types={prop(p, 'valid_types')} "
            f"mandatory={(p.get('mandatory') or {}).get('value')} "
            f"editable={(p.get('editable') or {}).get('value')}")
r = c.post("/entity/published_files/_search", headers=ARR,
           json={"filters": [], "fields": ["code", "project"], "page": {"size": 500}})
allrows = r.json()["data"]
seen = {((row.get("relationships") or {}).get("project") or {}).get("data", {}).get("id")
        for row in allrows}
rows.append(f"  unfiltered _search returned {len(allrows)} rows across "
            f"{len(seen)} distinct project ids")
r = c.get("/entity/published_files", params={"filter[project.Project.id]": PROJECT,
                                             "fields": "code", "page[size]": 200})
rows.append(f"  filter[project.Project.id]={PROJECT} -> {r.status_code} "
            f"{len(r.json()['data'])} rows")

# --------------------------------------------------------------- identity
rows.append("\n=== identity: the name-ish fields the schema offers")
for f in ("code", "name", "content", "title", "cached_display_name", "description",
          "version_number", "path_cache", "id"):
    m = schema.get(f)
    if not m:
        rows.append(f"  {f:20} absent from /schema/PublishedFile/fields")
        continue
    rows.append(f"  {f:20} data_type={(m.get('data_type') or {}).get('value'):12} "
                f"name={prop(m, 'name') or (m.get('name') or {}).get('value')!r:24} "
                f"mandatory={str((m.get('mandatory') or {}).get('value')):5} "
                f"editable={str((m.get('editable') or {}).get('value')):5} "
                f"unique={(m.get('unique') or {}).get('value')}")

FIELDS = ["code", "name", "version_number", "cached_display_name"]
r = c.post("/entity/published_files/_search", headers=ARR,
           json={"filters": [["project", "is", {"type": "Project", "id": PROJECT}]],
                 "fields": FIELDS, "page": {"size": 200}})
sample = r.json()["data"]
where = "sample project"
if not sample:  # the type is publish history; a project can hold none of it
    r = c.post("/entity/published_files/_search", headers=ARR,
               json={"filters": [], "fields": FIELDS, "page": {"size": 200}})
    sample = r.json()["data"]
    where = "site-wide, the sample project holding none"
rows.append(f"  how code and name compare on real rows ({where}):")
same = sum(1 for x in sample if x["attributes"].get("code") == x["attributes"].get("name"))
nver = sum(1 for x in sample if x["attributes"].get("version_number") is not None)
rows.append(f"    {len(sample)} rows; code == name on {same}; version_number set on {nver}")
for x in sample[:3]:
    a = x["attributes"]
    _lib.note_from(x)
    rows.append(f"    id={x['id']} code={a.get('code')!r} name={a.get('name')!r} "
                f"version_number={a.get('version_number')!r}")
# does a (name, version_number) pair repeat inside one project?
pairs = {}
for x in sample:
    a = x["attributes"]
    pairs.setdefault((a.get("name"), a.get("version_number")), []).append(x["id"])
dupes = {k: v for k, v in pairs.items() if len(v) > 1}
rows.append(f"    distinct (name, version_number) pairs: {len(pairs)}; "
            f"pairs held by more than one row: {len(dupes)}")

# --------------------------------------------------------------- links
rows.append("\n=== link fields and their valid_types")
for f, m in sorted(schema.items()):
    dt = (m.get("data_type") or {}).get("value")
    if dt not in ("entity", "multi_entity"):
        continue
    vt = prop(m, "valid_types") or []
    shown = ", ".join(vt[:8]) + (f", +{len(vt) - 8} more" if len(vt) > 8 else "")
    rows.append(f"  {f:28} {dt:12} editable={str((m.get('editable') or {}).get('value')):5} "
                f"[{shown}]")

rows.append("\n=== published_file_type: how to read the vocabulary")
r = c.get("/entity/published_file_types", params={"fields": "code", "page[size]": 200})
pft = r.json()["data"] if r.ok else []
rows.append(f"  GET /entity/published_file_types -> {r.status_code}, {len(pft)} rows on this site")
pfts = c.get("/schema/PublishedFileType/fields").json()["data"]
rows.append(f"  /schema/PublishedFileType/fields -> {sorted(pfts)}")
rows.append(f"  has a project field: {'project' in pfts}")
for x in pft[:3]:
    _lib.note_from(x)
    rows.append(f"    id={x['id']} code={x['attributes'].get('code')!r}")

# --------------------------------------------------------------- path
rows.append("\n=== path: the read shape (probe 021, re-read for the key set)")
r = c.post("/entity/published_files/_search", headers=ARR,
           json={"filters": [["path_cache", "is_not", None]],
                 "fields": ["path", "path_cache", "path_cache_storage", "name"],
                 "page": {"size": 5}})
got = r.json()["data"] if r.ok else []
rows.append(f"  path_cache is_not None -> {r.status_code}, {len(got)} rows")
for x in got[:2]:
    a = x["attributes"]
    _lib.note_from(x)
    _lib.note_path(a.get("path_cache"))
    pth = a.get("path") or {}
    if isinstance(pth, dict):
        _lib.note_path(pth.get("relative_path"))
        for k in ("local_path_mac", "local_path_windows", "local_path_linux", "name"):
            _lib.note_path(pth.get(k))
        rows.append(f"    id={x['id']} path.link_type={pth.get('link_type')!r} "
                    f"keys={sorted(pth)}")
        rows.append(f"      {json.dumps(pth, default=str)}")
    rows.append(f"      path_cache={a.get('path_cache')!r} "
                f"path_cache_storage="
                f"{((x.get('relationships') or {}).get('path_cache_storage') or {}).get('data')}")
r = c.get("/entity/local_storages", params={"fields": "code,mac_path,windows_path,linux_path",
                                            "page[size]": 20})
ls = r.json()["data"] if r.ok else []
for x in ls:
    _lib.note_from(x)
    for k in ("mac_path", "windows_path", "linux_path"):
        _lib.note_path(x["attributes"].get(k))
rows.append(f"  GET /entity/local_storages -> {r.status_code}, {len(ls)} rows: "
            f"{json.dumps([{'id': x['id'], **x['attributes']} for x in ls], default=str)}")

# --------------------------------------------------------------- status
rows.append("\n=== status field")
site = c.get("/schema/PublishedFile/fields/sg_status_list").json()["data"]
scoped = c.get("/schema/PublishedFile/fields/sg_status_list",
               params={"project_id": PROJECT}).json()["data"]
rows.append(f"  data_type={(site.get('data_type') or {}).get('value')} "
            f"default_value={prop(site, 'default_value')!r}")
rows.append(f"  valid_values: {prop(site, 'valid_values')}")
rows.append(f"  hidden_values on the sample project: {prop(scoped, 'hidden_values')}")

# --------------------------------------------------------------- server managed
rows.append("\n=== not editable in the schema")
ro = sorted(f for f, m in schema.items() if (m.get("editable") or {}).get("value") is False)
rows.append(f"  {len(ro)} of {len(schema)} fields: {ro}")
rows.append(f"  mandatory in the schema: "
            f"{sorted(f for f, m in schema.items() if (m.get('mandatory') or {}).get('value'))}")

# --------------------------------------------------------------- create contract
rows.append("\n=== create contract, and whether anything is unique")
if not _lib.writes_allowed():
    rows.append("  (read-only run; pass --write)")
else:
    SANDBOX = _lib.sandbox_id(c, env)
    ref = {"type": "Project", "id": SANDBOX}
    storage = ls[0] if ls else None
    with _lib.Created(c) as made:
        def attempt(label, body):
            r = c.post("/entity/published_files", json=body, headers=JSN)
            if r.ok:
                d = r.json()["data"]
                made.add("published_files", d["id"])
                a = d["attributes"]
                # A path write mints an Attachment row that outlives the PublishedFile.
                att = a.get("path") if isinstance(a.get("path"), dict) else {}
                if att.get("type") == "Attachment" and att.get("id"):
                    made.add("attachments", att["id"])
                rows.append(f"  {r.status_code} {label:34} id={d['id']} code={a.get('code')!r} "
                            f"name={a.get('name')!r} version_number={a.get('version_number')!r}")
                return d
            rows.append(f"  {r.status_code} {label:34}\n{errors(r)}")
            return None

        attempt("{}", {})
        attempt("code alone, no project", {"code": "zzprobe_pf"})
        attempt("name alone, no project", {"name": "zzprobe_pf"})
        first = attempt("project alone", {"project": ref})
        base = {"project": ref, "code": "zzprobe_pf.v001.ma", "name": "zzprobe_pf",
                "version_number": 1}
        attempt("project + code + name + version", base)
        attempt("the identical body a second time", base)
        attempt("same name, version_number 2", {**base, "version_number": 2})

        def readback(pf, dump=False):
            if not pf:
                return
            got = c.get(f"/entity/published_files/{pf['id']}",
                        params={"fields": "path,path_cache,path_cache_storage"}).json()["data"]
            v = got["attributes"].get("path") or {}
            _lib.note_from(got)
            _lib.note_path(v.get("relative_path"))
            rows.append(f"      read back: link_type={v.get('link_type')!r} keys={sorted(v)}")
            if dump:
                rows.append(f"      {json.dumps(v, default=str)}")
            rows.append(f"      path_cache={got['attributes'].get('path_cache')!r} "
                        f"path_cache_storage="
                        f"{((got.get('relationships') or {}).get('path_cache_storage') or {}).get('data')}")

        # path: the reason the type exists. Which write shape puts a local path on a row?
        rows.append("  path write shapes:")
        attempt("path as a bare string",
                {**base, "path": "/mnt/projects/demo_show/publish/zzprobe.v001.ma"})
        readback(attempt("path as {url}",
                         {**base, "path": {"url": "file:///mnt/projects/zzprobe.v001.ma",
                                           "name": "zzprobe.v001.ma"}}))
        if storage:
            root = storage["attributes"].get("mac_path") or "/mnt/projects"
            local = {"local_path": root + "/zzprobe/zzprobe.v001.ma"}
            readback(attempt("path as {local_path}", {**base, "path": local}), dump=True)
            readback(attempt("path as {relative_path, local_storage}",
                             {**base, "path": {"relative_path": "zzprobe/zzprobe.v001.ma",
                                               "local_storage": {"type": "LocalStorage",
                                                                 "id": storage["id"]}}}))
            attempt("the identical local_path a second time", {**base, "path": local})

        # what the server filled in on the row created with project alone
        if first:
            got = c.get(f"/entity/published_files/{first['id']}").json()["data"]
            filled = {k: v for k, v in got["attributes"].items() if v not in (None, "", [], {})}
            _lib.note_from(got)
            rows.append(f"  server-filled attributes on the minimal row ({len(filled)}): "
                        f"{json.dumps(filled, default=str)}")
            rows.append(f"  relationships returned: {sorted(got.get('relationships', {}))}")

actual = "\n".join(rows)
_lib.emit("entity_types/PublishedFile", actual, env)
