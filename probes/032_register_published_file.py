"""Q: how does a publish register the next PublishedFile without stomping the last, and make its path resolve everywhere?

Reimplemented more than twenty times across four production repositories, one publish plugin per
application. The corpus has the pieces (entity_types/PublishedFile, entity_types/PublishedFileType,
021_media_resolution, field_types/url) and no worked sequence. Three operator claims to test:
the version query is the only guard, the server sometimes attaches the wrong LocalStorage to a
relative-path write, and a relative path needs its backslashes replaced first.
"""
import json

import _lib

env = _lib.load_env()
c = _lib.client()
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
JSON = {"Content-Type": "application/json"}
rows = []


def err(r):
    """The error body, whole. A truncated API error teaches nothing."""
    try:
        return json.dumps(r.json().get("errors", r.json()))
    except ValueError:
        return r.text


def path_of(pf_id):
    r = c.get(f"/entity/published_files/{pf_id}", params={"fields": "path,path_cache"})
    d = r.json()["data"]["attributes"]
    _lib.note_from(r.json())
    return d.get("path") or {}, d.get("path_cache")


# --- read-only: the two lookups every publish needs before it writes anything ----------------
storages = c.get("/entity/local_storages",
                 params={"fields": "code,mac_path,windows_path,linux_path"}).json()["data"]
_lib.note_from({"data": storages})
for s in storages:
    _lib.note_path(s["attributes"].get("mac_path"))
rows.append(f"=== LocalStorage rows on this site: {len(storages)}")
for s in storages:
    a = s["attributes"]
    rows.append(f"  id={s['id']} code={a['code']!r} mac={a['mac_path']!r} "
                f"windows={a['windows_path']!r} linux={a['linux_path']!r}")

types = c.get("/entity/published_file_types", params={"fields": "code,short_name"}).json()["data"]
_lib.note_from({"data": types})
rows.append(f"\n=== PublishedFileType rows (site-wide, no project scope): {len(types)}")
rows.append("  codes: " + ", ".join(sorted(t["attributes"]["code"] for t in types)))

PROJECT = _lib.sample_projects(c, env)[0]
NAME = "zzprobe_032_charA.ma"


def next_version(project_id, name, extra=None):
    """The descending read that decides the next number. There is no server-side guard behind it."""
    filters = [["project", "is", {"type": "Project", "id": project_id}], ["name", "is", name]]
    filters += extra or []
    r = c.post("/entity/published_files/_search", headers=ARR, json={
        "filters": filters, "fields": ["code", "name", "version_number"],
        "sort": ["-version_number"], "page": {"size": 1}})
    d = r.json()["data"]
    _lib.note_from(r.json())
    return (d[0]["attributes"]["version_number"] or 0) + 1 if d else 1, r.status_code, len(d)


nxt, sc, n = next_version(PROJECT, NAME)
rows.append(f"\n=== the version query, on a read-only project and a name nothing published")
rows.append(f"  POST /entity/published_files/_search sort=['-version_number'] -> {sc}, {n} rows, next={nxt}")

r = c.post("/entity/published_files/_search", headers=ARR, json={
    "filters": [["version_number", "is_not", None]],
    "fields": ["code", "name", "version_number"], "sort": ["-version_number"], "page": {"size": 5}})
_lib.note_from(r.json())
rows.append(f"  the same sort over the site's real rows -> {r.status_code}, "
            f"version_number descending: {[x['attributes']['version_number'] for x in r.json()['data']]}")

if not _lib.writes_allowed():
    rows.append("\n(read-only run; the write half needs --write)")
    _lib.emit("032_register_published_file", "\n".join(rows), env)
    raise SystemExit(0)

SANDBOX = _lib.sandbox_id(c, env)
STORAGE = storages[0]
ROOT = STORAGE["attributes"]["mac_path"]
REL = "zzprobe_032/assets/charA/publish/maya"

with _lib.Created(c) as made:

    def keep_attachment(path_value):
        """Each accepted path write mints an Attachment that outlives the PublishedFile. Deleted last:
        Created unwinds in reverse, so an id at index 0 goes after the rows pointing at it."""
        if isinstance(path_value, dict) and path_value.get("id"):
            made.rows.insert(0, ("attachments", path_value["id"]))

    echoed = []

    def publish(label, body):
        r = c.post("/entity/published_files", headers=JSON, json=body)
        if not r.ok:
            rows.append(f"  {label:<26} {r.status_code} {err(r)}")
            return None
        pid = made.add("published_files", r.json()["data"]["id"])
        rows.append(f"  {label:<26} {r.status_code} id={pid}")
        echoed.append(r.json()["data"]["attributes"].get("path"))
        return pid

    # 1. choose the next number, then write it. Read and write are two calls with no lock between.
    rows.append("\n=== 1. next version number, then the create")
    for i in (1, 2):
        nxt, sc, n = next_version(SANDBOX, NAME)
        rows.append(f"  query -> {n} row(s), next={nxt}")
        pid = publish(f"create v{nxt:03d}", {
            "project": {"type": "Project", "id": SANDBOX},
            "name": NAME,
            "code": f"zzprobe_032_charA.v{nxt:03d}.ma",
            "version_number": nxt,
            "path": {"local_path": f"{ROOT}/{REL}/zzprobe_032_charA.v{nxt:03d}.ma"},
        })
        p, cache = path_of(pid)
        keep_attachment(p)
        if i == 1:
            rows.append("\n=== 2. what the server filled in from {local_path} alone")
            rows.append("  the 201 echoes path as: " + json.dumps(echoed[0]))
            rows.append("  GET .../published_files/<id>?fields=path :")
            rows.append("  " + json.dumps(p, indent=2).replace("\n", "\n  "))
            rows.append(f"  path_cache after a REST create: {cache!r}")
            rows.append("\n  (back to the sequence)")

    nxt, sc, n = next_version(SANDBOX, NAME)
    rows.append(f"  query again -> {n} row(s), next={nxt}")

    # 2. the storage the server picked, against the one the client intended.
    rows.append("\n=== 3. storage correction: intended id vs the one returned")
    intended = STORAGE["id"]
    cases = [
        ("{relative_path, local_storage}", {"relative_path": f"{REL}/zzprobe_032_rel.v001.ma",
                                            "local_storage": {"type": "LocalStorage", "id": intended}}),
        ("{local_path} under the root", {"local_path": f"{ROOT}/{REL}/zzprobe_032_abs.v001.ma"}),
        ("{relative_path} alone", {"relative_path": f"{REL}/zzprobe_032_norel.v001.ma"}),
        ("{local_path} under no root", {"local_path": f"/zzprobe_032_no_such_root/{REL}/x.v001.ma"}),
    ]
    for label, pathval in cases:
        pid = publish(label, {"project": {"type": "Project", "id": SANDBOX},
                              "code": f"zzprobe_032_{label}", "path": pathval})
        if pid is None:
            continue
        p, _ = path_of(pid)
        keep_attachment(p)
        got = (p.get("local_storage") or {}).get("id")
        rows.append(f"    intended={intended} returned={got} "
                    f"{'match' if got == intended else 'MISMATCH'}  link_type={p.get('link_type')!r} "
                    f"relative_path={p.get('relative_path')!r}")
        rows.append(f"    local_path_mac={p.get('local_path_mac')!r} "
                    f"windows={p.get('local_path_windows')!r} linux={p.get('local_path_linux')!r}")
        if got != intended:
            rows.append("    ^ a mismatch reproduced; the corrective PUT below is the fix")

    # The corrective write itself, run on a matching row so the recipe's defensive step is verified.
    fix_id = made.rows[-1][1] if made.rows and made.rows[-1][0] == "published_files" else None
    if fix_id:
        before, _ = path_of(fix_id)
        rf = c.put(f"/entity/published_files/{fix_id}", headers=JSON, json={
            "path": {"relative_path": f"{REL}/zzprobe_032_abs.v001.ma",
                     "local_storage": {"type": "LocalStorage", "id": intended}}})
        after, _ = path_of(fix_id)
        keep_attachment(after)
        rows.append(f"  PUT path (the corrective update) -> {rf.status_code}"
                    + ("" if rf.ok else f" {err(rf)}"))
        rows.append(f"    Attachment id before={before.get('id')} after={after.get('id')} "
                    f"storage={(after.get('local_storage') or {}).get('id')}")

    # 3. backslashes.
    rows.append("\n=== 4. backslashes in a path")
    bs = [
        ("relative_path with \\", {"relative_path": REL.replace("/", "\\") + "\\zzprobe_032_bs.v001.ma",
                                   "local_storage": {"type": "LocalStorage", "id": intended}}),
        ("local_path with \\", {"local_path": f"{ROOT}/{REL}".replace("/", "\\")
                                              + "\\zzprobe_032_bs2.v001.ma"}),
        ("mixed separators", {"relative_path": f"{REL}\\zzprobe_032_bs3.v001.ma",
                              "local_storage": {"type": "LocalStorage", "id": intended}}),
    ]
    for label, pathval in bs:
        rows.append(f"  sent {json.dumps(pathval)}")
        pid = publish(label, {"project": {"type": "Project", "id": SANDBOX},
                              "code": f"zzprobe_032_{label}", "path": pathval})
        if pid is None:
            continue
        p, _ = path_of(pid)
        keep_attachment(p)
        rows.append(f"    read back relative_path={p.get('relative_path')!r}")
        rows.append(f"    local_path_mac={p.get('local_path_mac')!r} "
                    f"storage={(p.get('local_storage') or {}).get('id')}")

    # 4. the links a publish sets, in one create.
    rows.append("\n=== 5. linking it up")
    shots = c.get("/entity/shots", params={"filter[project.Project.id]": SANDBOX,
                                           "fields": "code", "page[size]": 1}).json()
    _lib.note_from(shots)
    if shots["data"]:
        shot_id = shots["data"][0]["id"]
        rows.append(f"  reused an existing Shot in the sandbox")
    else:
        shot_id = made.add("shots", c.post("/entity/shots", headers=JSON, json={
            "project": {"type": "Project", "id": SANDBOX},
            "code": "zzprobe_032_sh010"}).json()["data"]["id"])
        rows.append(f"  created Shot zzprobe_032_sh010")

    rt = c.post("/entity/tasks", headers=JSON, json={
        "project": {"type": "Project", "id": SANDBOX}, "content": "zzprobe_032_task",
        "entity": {"type": "Shot", "id": shot_id}})
    rows.append(f"  POST /entity/tasks -> {rt.status_code}"
                + ("" if rt.ok else f" {err(rt)}"))
    task_id = made.add("tasks", rt.json()["data"]["id"]) if rt.ok else None

    rv = c.post("/entity/versions", headers=JSON, json={
        "project": {"type": "Project", "id": SANDBOX}, "code": "zzprobe_032_charA.v001",
        "entity": {"type": "Shot", "id": shot_id}})
    rows.append(f"  POST /entity/versions -> {rv.status_code}"
                + ("" if rv.ok else f" {err(rv)}"))
    version_id = made.add("versions", rv.json()["data"]["id"]) if rv.ok else None

    # PublishedFileType is site-wide: resolve by code, never create for an unknown extension here.
    WANT = "Maya Scene"
    match = [t for t in types if t["attributes"]["code"].strip().lower() == WANT.lower()]
    rows.append(f"  resolve type {WANT!r} by code (case-insensitive) -> "
                + (f"id={match[0]['id']}" if match else "absent"))
    pft = {"type": "PublishedFileType", "id": match[0]["id"]} if match else None

    body = {"project": {"type": "Project", "id": SANDBOX},
            "name": NAME, "code": "zzprobe_032_charA.v003.ma", "version_number": 3,
            "path": {"local_path": f"{ROOT}/{REL}/zzprobe_032_charA.v003.ma"},
            "entity": {"type": "Shot", "id": shot_id},
            "sg_status_list": "cmpt"}
    if task_id:
        body["task"] = {"type": "Task", "id": task_id}
    if version_id:
        body["version"] = {"type": "Version", "id": version_id}
    if pft:
        body["published_file_type"] = pft
    pid = publish("linked publish", body)
    p, _ = path_of(pid)
    keep_attachment(p)
    back = c.get(f"/entity/published_files/{pid}", params={
        "fields": "code,name,version_number,sg_status_list,entity,task,version,published_file_type"}).json()
    _lib.note_from(back)
    rows.append("    attributes:    " + json.dumps(back["data"]["attributes"]))
    rows.append("    relationships: " + json.dumps(
        {k: v.get("data") for k, v in back["data"]["relationships"].items()}))

    # A bare id where a hash belongs, so the recipe can name the error rather than warn about it.
    rb = c.post("/entity/published_files", headers=JSON, json={
        "project": {"type": "Project", "id": SANDBOX}, "code": "zzprobe_032_bare",
        "published_file_type": match[0]["id"] if match else 1})
    rows.append(f"  published_file_type as a bare id -> {rb.status_code} {err(rb)}")
    if rb.ok:
        made.add("published_files", rb.json()["data"]["id"])

    rows.append("\n=== 6. creating a missing type: not run, the row would be site-wide")
    rows.append('  POST /entity/published_file_types {"code": "<ext>"}')

    rows.append("\n=== cleanup")

_lib.emit("032_register_published_file", "\n".join(rows), env)
