"""Q: what is a Version, how is it addressed, identified, created and linked?

The map for the type, not a re-run of the media probes. Probe 012 established the create contract,
005 measured link usage, 013/021/022 and field_types/url and /image cover media. What is missing is
the one page that says which slug answers, whether `code` is unique, which fields are server managed,
and where to go next.

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
for slug in ("versions", "version", "Version", "Versions", "vershion"):
    r = c.get(f"/entity/{slug}", params={"fields": "code", "page[size]": 1})
    if not r.ok:
        rows.append(f"  GET /entity/{slug:9} -> {r.status_code}\n{errors(r)}")
        continue
    d = r.json()["data"]
    rows.append(f"  GET /entity/{slug:9} -> 200  rows={len(d)} "
                f"data[0].type={d[0]['type'] if d else None!r} id={d[0]['id'] if d else None}")
r = c.post("/entity/versions/_search", headers=ARR,
           json={"filters": [], "fields": ["code"], "page": {"size": 1}})
rows.append(f"  POST /entity/versions/_search -> {r.status_code}")

# --------------------------------------------------------------- scope
rows.append("\n=== project-scoped or site-wide")
schema = c.get("/schema/Version/fields").json()["data"]
p = schema.get("project", {})
rows.append(f"  project field: data_type={(p.get('data_type') or {}).get('value')} "
            f"valid_types={prop(p, 'valid_types')} "
            f"mandatory={(p.get('mandatory') or {}).get('value')} "
            f"editable={(p.get('editable') or {}).get('value')}")
r = c.post("/entity/versions/_search", headers=ARR,
           json={"filters": [], "fields": ["code", "project"], "page": {"size": 500}})
seen = {((row.get("relationships") or {}).get("project") or {}).get("data", {}).get("id")
        for row in r.json()["data"]}
rows.append(f"  unfiltered _search returned {len(r.json()['data'])} rows across "
            f"{len(seen)} distinct project ids")
r = c.get("/entity/versions", params={"filter[project.Project.id]": PROJECT,
                                      "fields": "code", "page[size]": 200})
rows.append(f"  filter[project.Project.id]={PROJECT} -> {r.status_code} {len(r.json()['data'])} rows")

# --------------------------------------------------------------- identity
rows.append("\n=== identity: the name-ish fields the schema offers")
for f in ("code", "name", "content", "title", "cached_display_name", "description", "id"):
    m = schema.get(f)
    if not m:
        rows.append(f"  {f:20} absent from /schema/Version/fields")
        continue
    rows.append(f"  {f:20} data_type={(m.get('data_type') or {}).get('value'):12} "
                f"mandatory={str((m.get('mandatory') or {}).get('value')):5} "
                f"editable={str((m.get('editable') or {}).get('value')):5} "
                f"unique={(m.get('unique') or {}).get('value')}")

# --------------------------------------------------------------- links
rows.append("\n=== link fields and their valid_types")
for f, m in sorted(schema.items()):
    dt = (m.get("data_type") or {}).get("value")
    if dt not in ("entity", "multi_entity"):
        continue
    vt = prop(m, "valid_types") or []
    shown = ", ".join(vt[:6]) + (f", +{len(vt) - 6} more" if len(vt) > 6 else "")
    rows.append(f"  {f:20} {dt:12} [{shown}]")

# --------------------------------------------------------------- status
rows.append("\n=== status field")
site = c.get("/schema/Version/fields/sg_status_list").json()["data"]
scoped = c.get("/schema/Version/fields/sg_status_list",
               params={"project_id": PROJECT}).json()["data"]
valid = prop(site, "valid_values")
hidden = prop(scoped, "hidden_values")
rows.append(f"  data_type={(site.get('data_type') or {}).get('value')} "
            f"default_value={prop(site, 'default_value')!r}")
rows.append(f"  valid_values ({len(valid)}): {valid}")
rows.append(f"  display_values: {json.dumps(prop(site, 'display_values'))}")
rows.append(f"  hidden_values on the sample project: {hidden}")
rows.append(f"  usable there: {[v for v in valid if v not in (hidden or [])]}")

# --------------------------------------------------------------- media fields
rows.append("\n=== media fields, by data_type")
for f in ("image", "filmstrip_image", "image_blur_hash", "sg_uploaded_movie",
          "sg_uploaded_movie_mp4", "sg_uploaded_movie_webm", "sg_uploaded_movie_image",
          "sg_uploaded_movie_frame_rate", "sg_uploaded_movie_transcoding_status",
          "sg_path_to_movie", "sg_path_to_frames", "sg_first_frame", "sg_last_frame",
          "frame_count", "frame_range", "published_files", "attachments"):
    m = schema.get(f)
    rows.append(f"  {f:36} " + ("absent" if not m else
                f"{(m.get('data_type') or {}).get('value'):12} "
                f"editable={(m.get('editable') or {}).get('value')}"))

# --------------------------------------------------------------- server managed
rows.append("\n=== not editable in the schema")
ro = sorted(f for f, m in schema.items() if (m.get("editable") or {}).get("value") is False)
rows.append(f"  {len(ro)} of {len(schema)} fields: {ro}")
rows.append(f"  mandatory in the schema: "
            f"{sorted(f for f, m in schema.items() if (m.get('mandatory') or {}).get('value'))}")

# --------------------------------------------------------------- create contract
rows.append("\n=== create contract (probe 012, re-verified)")
if not _lib.writes_allowed():
    rows.append("  (read-only run; pass --write)")
else:
    SANDBOX = _lib.sandbox_id(c, env)
    ref = {"type": "Project", "id": SANDBOX}
    with _lib.Created(c) as made:
        attempts = [
            ("code alone, no project", {"code": "zzprobe_ver_a"}),
            ("project alone, no code", {"project": ref}),
            ("both", {"project": ref, "code": "zzprobe_ver_a"}),
            ("both, same code again", {"project": ref, "code": "zzprobe_ver_a"}),
        ]
        for label, body in attempts:
            r = c.post("/entity/versions", json=body, headers=JSN)
            if r.ok:
                d = r.json()["data"]
                made.add("versions", d["id"])
                rows.append(f"  {r.status_code} {label:26} id={d['id']} "
                            f"code={d['attributes'].get('code')!r}")
            else:
                rows.append(f"  {r.status_code} {label:26}\n{errors(r)}")

        # what the server filled in on the row created with project + code only
        vid = made.rows[-1][1] if made.rows else None
        if vid:
            got = c.get(f"/entity/versions/{vid}").json()["data"]
            filled = {k: v for k, v in got["attributes"].items() if v not in (None, "", [], {})}
            rows.append(f"  server-filled attributes on the minimal row ({len(filled)}): "
                        f"{json.dumps(filled, default=str)}")
            rows.append(f"  relationships returned: {sorted(got.get('relationships', {}))}")
            _lib.note_from(got)

actual = "\n".join(rows)
_lib.emit("entity_types/Version", actual, env)
