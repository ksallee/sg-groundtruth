"""Q: with roots on every platform and roots that nest, which one does a path write resolve against?

Recipe 004 measured one LocalStorage row defining one platform, so two things stayed unproven: whether
a single create fills all three `local_path_*` when the row defines all three, and which row the server
picks when a path sits under more than one. The third question is recipe 004's open race: whether any
conditional-write header closes it.

Rows are named zzprobe_058_* and deleted on exit. The site's own storage row is never touched.
"""
import json

import _lib

env = _lib.load_env()
c = _lib.client()
JSON = {"Content-Type": "application/json"}
rows = []

if not _lib.writes_allowed():
    raise SystemExit("058_local_storage_roots writes to the site; re-run with --write")


def err(r):
    try:
        return json.dumps(r.json().get("errors", r.json()))
    except ValueError:
        return repr(r.text)


SANDBOX = _lib.sandbox_id(c, env)

with _lib.Created(c) as made:

    def keep_attachment(p):
        row = ("attachments", (p or {}).get("id"))
        if isinstance(p, dict) and row[1] and row not in made.rows:
            made.rows.insert(0, row)

    def storage(code, **paths):
        r = c.post("/entity/local_storages", headers=JSON, json=dict(code=code, **paths))
        if not r.ok:
            rows.append(f"  storage {code} -> {r.status_code} {err(r)}")
            return None
        return made.add("local_storages", r.json()["data"]["id"])

    def publish(label, pathval):
        """One create, then the resolved path off the 201 itself."""
        r = c.post("/entity/published_files", headers=JSON, json={
            "project": {"type": "Project", "id": SANDBOX},
            "code": f"zzprobe_058_{label}", "path": pathval})
        if not r.ok:
            rows.append(f"  {label:<28} -> {r.status_code} {err(r)}")
            return None
        d = r.json()["data"]
        made.add("published_files", d["id"])
        p = d["attributes"].get("path") or {}
        keep_attachment(p)
        rows.append(f"  {label:<28} -> 201  storage={(p.get('local_storage') or {}).get('id')} "
                    f"link_type={p.get('link_type')!r}")
        rows.append(f"    relative_path={p.get('relative_path')!r}")
        rows.append(f"    mac={p.get('local_path_mac')!r}")
        rows.append(f"    win={p.get('local_path_windows')!r}")
        rows.append(f"    lnx={p.get('local_path_linux')!r}")
        return p

    # --- 1. one row, all three platforms ---------------------------------------------------
    MAC, WIN, LNX = "/zzprobe_058_a", "Z:\\zzprobe_058_a", "/mnt/zzprobe_058_a"
    three = storage("zzprobe_058_three", mac_path=MAC, windows_path=WIN, linux_path=LNX)
    rows.append(f"=== 1. one LocalStorage defining mac, windows and linux (id {three})")
    rows.append(f"  mac_path={MAC!r} windows_path={WIN!r} linux_path={LNX!r}")
    publish("local_path under mac", {"local_path": f"{MAC}/seq/plate.v001.exr"})
    publish("local_path under linux", {"local_path": f"{LNX}/seq/plate.v001.exr"})
    publish("local_path under windows", {"local_path": "Z:/zzprobe_058_a/seq/plate.v001.exr"})
    publish("relative_path + storage", {"relative_path": "seq/plate.v001.exr",
                                        "local_storage": {"type": "LocalStorage", "id": three}})

    # --- 2. roots that nest -----------------------------------------------------------------
    rows.append("\n=== 2. two rows whose roots nest, and a path under both")
    parent = storage("zzprobe_058_parent", mac_path="/zzprobe_058_n")
    child = storage("zzprobe_058_child", mac_path="/zzprobe_058_n/sub")
    rows.append(f"  parent /zzprobe_058_n id={parent} created first, "
                f"child /zzprobe_058_n/sub id={child} second")
    publish("under both, parent first", {"local_path": "/zzprobe_058_n/sub/deep/plate.v001.exr"})
    publish("under the parent only", {"local_path": "/zzprobe_058_n/other/plate.v001.exr"})

    # The reverse creation order, so id and prefix length disagree.
    child2 = storage("zzprobe_058_child2", mac_path="/zzprobe_058_m/sub")
    parent2 = storage("zzprobe_058_parent2", mac_path="/zzprobe_058_m")
    rows.append(f"  child /zzprobe_058_m/sub id={child2} created first, "
                f"parent /zzprobe_058_m id={parent2} second")
    publish("under both, child first", {"local_path": "/zzprobe_058_m/sub/deep/plate.v001.exr"})

    # Two rows with the identical root, so prefix length cannot decide.
    dupe_a = storage("zzprobe_058_dupe_a", mac_path="/zzprobe_058_d")
    dupe_b = storage("zzprobe_058_dupe_b", mac_path="/zzprobe_058_d")
    rows.append(f"  two rows on the identical root /zzprobe_058_d: ids {dupe_a} and {dupe_b}")
    publish("identical roots", {"local_path": "/zzprobe_058_d/plate.v001.exr"})

    # What the response says about the choice, beyond the id.
    r = c.get("/entity/published_files", params={
        "filter[project.Project.id]": SANDBOX, "fields": "path,path_cache,path_cache_storage",
        "page[size]": 1, "sort": "-id"})
    d = r.json()["data"][0]
    rows.append("  everything the response says about the row, beyond path.local_storage:")
    rows.append("    attributes:    " + json.dumps({k: v for k, v in d["attributes"].items()
                                                    if k != "path"}))
    rows.append("    relationships: " + json.dumps({k: v.get("data")
                                                    for k, v in d.get("relationships", {}).items()}))
    rows.append("    links:         " + json.dumps(d.get("links")))

    # --- 3. conditional writes ---------------------------------------------------------------
    rows.append("\n=== 3. conditional writes on one row")
    r = c.post("/entity/published_files", headers=JSON, json={
        "project": {"type": "Project", "id": SANDBOX}, "code": "zzprobe_058_cond",
        "version_number": 1})
    pf = made.add("published_files", r.json()["data"]["id"])
    g = c.get(f"/entity/published_files/{pf}", params={"fields": "code,updated_at"})
    rows.append("  response headers on a GET: " + json.dumps(
        {k: v for k, v in g.headers.items()
         if k.lower() in ("etag", "last-modified", "cache-control", "vary")}))
    updated = g.json()["data"]["attributes"]["updated_at"]
    rows.append(f"  updated_at={updated!r}")

    for label, extra in (
        ("no header, the control", {}),
        ('If-Match: "definitely-not-an-etag"', {"If-Match": '"definitely-not-an-etag"'}),
        ("If-Match: *", {"If-Match": "*"}),
        ("If-None-Match: *", {"If-None-Match": "*"}),
        ("If-Unmodified-Since: 1994", {"If-Unmodified-Since": "Sun, 06 Nov 1994 08:49:37 GMT"}),
        ("If-Modified-Since: 1994", {"If-Modified-Since": "Sun, 06 Nov 1994 08:49:37 GMT"}),
    ):
        h = dict(JSON)
        h.update(extra)
        rr = c.put(f"/entity/published_files/{pf}", headers=h,
                   json={"version_number": 2})
        rows.append(f"  PUT {label:<36} -> {rr.status_code} "
                    + ("" if rr.ok else err(rr)))
    back = c.get(f"/entity/published_files/{pf}", params={"fields": "code,updated_at"})
    rows.append(f"  Etag before the writes {g.headers.get('Etag')} after {back.headers.get('Etag')} "
                f"changed={g.headers.get('Etag') != back.headers.get('Etag')}")
    again = c.get(f"/entity/published_files/{pf}", params={"fields": "code,updated_at"})
    rows.append(f"  two reads of the unchanged row: same Etag="
                f"{back.headers.get('Etag') == again.headers.get('Etag')}")
    v = c.get(f"/entity/published_files/{pf}", params={"fields": "version_number"})
    rows.append(f"  version_number after the six writes: "
                f"{v.json()['data']['attributes']['version_number']}")

    rows.append("\n=== cleanup")

_lib.emit("058_local_storage_roots", "\n".join(rows), env)
