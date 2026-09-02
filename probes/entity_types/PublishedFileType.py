"""Q: is a PublishedFileType site-wide or project-scoped, and what identifies one?

A publish tool that creates the type when it meets an unrecognised extension is writing into whatever
scope this entity has. If that scope is the site, one project's stray `.abc` becomes a row every other
project sees, and the row cannot be un-made: DELETE retires it.

Read-only, always. No create is attempted, for the reason above; the finding records what the schema
declares and says the contract is unverified. Uses sample_projects to show that two projects resolve
their published file types out of the same site-wide listing.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _lib  # noqa: E402

env = _lib.load_env()
c = _lib.client()
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
SAMPLES = _lib.sample_projects(c, env)
SLUG = "published_file_types"
rows = []


def errs(r):
    """The whole errors[] object, `source` included. The 400 is the documentation (probe 017)."""
    try:
        return json.dumps(r.json().get("errors", r.json()))
    except ValueError:
        return r.text


def search(slug, filters, fields, size=500, extra=None):
    body = {"filters": [list(f) for f in filters], "fields": list(fields), "page": {"size": size}}
    body.update(extra or {})
    r = c.post(f"/entity/{slug}/_search", headers=ARR, json=body)
    return (r.json()["data"], None) if r.ok else (None, r)


def count(slug, filters):
    """Exact totals; a _search page caps at its page size and reads as a ceiling (probe 020)."""
    r = c.post(f"/entity/{slug}/_summarize", headers=ARR,
               json={"filters": [list(f) for f in filters],
                     "summary_fields": [{"field": "id", "type": "record_count"}]})
    return r.json()["data"]["summaries"]["id"] if r.ok else f"ERR {r.status_code} {errs(r)}"


rows.append("=== the REST path slug: which spellings of /entity/<slug> resolve")
for variant in (SLUG, "published_file_type", "PublishedFileType", "publishedfiletypes",
                "publish_file_types", "published_files_types"):
    r = c.get(f"/entity/{variant}", params={"page[size]": 1, "fields": "code"})
    d = r.json().get("data") if r.ok else None
    rows.append(f"  GET /entity/{variant:<22} -> {r.status_code}"
                + (f"  links.self={d[0]['links']['self']}  type={d[0]['type']}" if d
                   else f"  {errs(r)}" if not r.ok else "  0 rows"))

rows.append("\n=== site-wide or project-scoped")
fields = c.get("/schema/PublishedFileType/fields").json()["data"]
rows.append(f"  fields: {len(fields)}    'project' present: {'project' in fields}")
got, r = search(SLUG, [["project", "is", {"type": "Project", "id": SAMPLES[0]}]], ["code"])
rows.append(f"  _search filter project is <sample project> -> "
            + (f"{len(got)} rows" if got is not None else f"{r.status_code} {errs(r)}"))
r = c.get(f"/entity/{SLUG}", params={"filter[project]": SAMPLES[0], "page[size]": 1})
rows.append(f"  GET ?filter[project]=<id> -> {r.status_code} " + ("" if r.ok else errs(r)))
base = count(SLUG, [])
r = c.get(f"/entity/{SLUG}", params={"project_id": SAMPLES[0], "page[size]": 500, "fields": "code"})
rows.append(f"  GET ?project_id=<id> -> {r.status_code}, {len(r.json()['data']) if r.ok else '-'} rows"
            f"      unscoped record_count: {base}")

rows.append("\n=== do two projects draw their types from the same rows?")
for p in SAMPLES[:3]:
    pf, r = search("published_files", [["project", "is", {"type": "Project", "id": p}],
                                       ["published_file_type", "is_not", None]],
                   ["published_file_type"], size=500)
    if pf is None:
        rows.append(f"  project <sample>: {r.status_code} {errs(r)}")
        continue
    ids = {(row["relationships"]["published_file_type"]["data"] or {}).get("id") for row in pf}
    rows.append(f"  a project's published files use {len(ids)} distinct type id(s) out of {base} "
                f"site-wide: {sorted(i for i in ids if i)}")

rows.append("\n=== identity: which field names a type, and is it unique")
for name in ("code", "name", "content", "short_name", "cached_display_name"):
    v = fields.get(name)
    rows.append(f"  {name:<20} " + ("absent from /schema/PublishedFileType/fields" if v is None else
                f"data_type={v['data_type']['value']:<10} display_name={v['name']['value']!r:<26} "
                f"editable={v['editable']['value']!s:<5} mandatory={v['mandatory']['value']!s:<5} "
                f"unique={v['unique']['value']}"))
allrows, r = search(SLUG, [], ["code", "short_name", "description", "sg_status_list"], size=500)
for f in ("code", "short_name", "cached_display_name"):
    vals = [row["attributes"].get(f) for row in allrows]
    dupes = sorted({v for v in vals if vals.count(v) > 1}, key=lambda x: (x is None, x))
    rows.append(f"  {f:<20} {len(set(vals)):>3} distinct of {len(vals)}   repeated: {len(dupes)}")
_lib.note_from(allrows)
rows.append(f"  filled: short_name {sum(1 for x in allrows if x['attributes'].get('short_name'))}, "
            f"description {sum(1 for x in allrows if x['attributes'].get('description'))} of {len(allrows)}")
one = allrows[0]
rows.append(f"  a row: {json.dumps(one)}")

rows.append("\n=== looking a type up by name, the way a create-if-missing publish would")
probe_code = one["attributes"]["code"]
for filt, label in (([["code", "is", probe_code]], "code is <an existing code>"),
                    ([["code", "is", (probe_code or "").upper()]], "code is <the same, upper-cased>"),
                    ([["code", "is", "zzznope"]], "code is 'zzznope'")):
    got, r = search(SLUG, filt, ["code"], size=10)
    rows.append(f"  {label:<38} -> " + (f"{len(got)} row(s)" if got is not None
                                        else f"{r.status_code} {errs(r)}"))
got, r = search(SLUG, [["code", "in", ["zzznope", probe_code]]], ["code"], size=10)
rows.append(f"  {'code in [absent, present]':<38} -> "
            + (f"{len(got)} row(s)" if got is not None else f"{r.status_code} {errs(r)}"))

rows.append("\n=== relationship to PublishedFile")
pf_fields = c.get("/schema/PublishedFile/fields").json()["data"]
for f, v in sorted(pf_fields.items()):
    vt = v["properties"].get("valid_types", {}).get("value") or []
    if "PublishedFileType" in vt and len(vt) <= 20:
        rows.append(f"  PublishedFile.{f:<24} {v['data_type']['value']:<12} "
                    f"editable={v['editable']['value']!s:<5} mandatory={v['mandatory']['value']!s:<5} "
                    f"valid_types={vt}")
back = [f for f, v in fields.items()
        if "PublishedFile" in (v["properties"].get("valid_types", {}).get("value") or [])
        and len(v["properties"].get("valid_types", {}).get("value") or []) <= 20]
rows.append(f"  reverse fields on PublishedFileType naming PublishedFile: {back}")

TYPES = sorted(c.get("/schema").json()["data"].keys())
pointers, catch_all = [], 0
for t in TYPES:
    r = c.get(f"/schema/{t}/fields")
    if not r.ok:
        continue
    for f, v in r.json()["data"].items():
        vt = v["properties"].get("valid_types", {}).get("value") or []
        if "PublishedFileType" not in vt:
            continue
        if len(vt) > 20:
            catch_all += 1
        else:
            pointers.append(f"{t}.{f} {v['data_type']['value']} {vt}")
rows.append(f"  fields naming PublishedFileType specifically, across {len(TYPES)} types: {pointers}")
rows.append(f"  plus {catch_all} generic any-entity fields that list it among 100+ valid_types")

rows.append("\n=== reading and filtering a PublishedFile by its type")
pf, r = search("published_files", [["published_file_type", "is_not", None]],
               ["code", "published_file_type.PublishedFileType.code",
                "published_file_type.PublishedFileType.short_name",
                "published_file_type.PublishedFileType.id"], size=3)
if pf:
    _lib.note_from(pf)
    for row in pf:
        rows.append(f"  {json.dumps(row['attributes'])}")
else:
    rows.append(f"  {r.status_code if r else 'none'} {errs(r) if r else ''}")
tid, tcode = one["id"], one["attributes"]["code"]
rows.append(f"  published_file_type is {{type, id}}          -> "
            f"{count('published_files', [['published_file_type', 'is', {'type': 'PublishedFileType', 'id': tid}]])}")
rows.append(f"  published_file_type is <bare id>            -> "
            f"{count('published_files', [['published_file_type', 'is', tid]])}")
rows.append(f"  published_file_type.PublishedFileType.code  -> "
            f"{count('published_files', [['published_file_type.PublishedFileType.code', 'is', tcode]])}")
rows.append(f"  published_file_type is None                 -> "
            f"{count('published_files', [['published_file_type', 'is', None]])} of "
            f"{count('published_files', [])} published files site-wide")

rows.append("\n=== status and read-only fields")
st = c.get("/schema/PublishedFileType/fields/sg_status_list").json()["data"]["properties"]
rows.append(f"  sg_status_list default={st['default_value']['value']!r} "
            f"valid_values={st['valid_values']['value']} hidden_values={st['hidden_values']['value']}")
stp = c.get("/schema/PublishedFileType/fields/sg_status_list",
            params={"project_id": SAMPLES[0]}).json()["data"]["properties"]
rows.append(f"  with project_id=<sample>: valid={stp['valid_values']['value']} "
            f"hidden={stp['hidden_values']['value']} (probe 009)")
used = {}
for row in allrows:
    v = row["attributes"].get("sg_status_list")
    used[v] = used.get(v, 0) + 1
rows.append(f"  in use across the site-wide listing: {used}")
rows.append(f"  read-only: {sorted(f for f, v in fields.items() if not v['editable']['value'])}")
rows.append(f"  schema-mandatory: {sorted(f for f, v in fields.items() if v['mandatory']['value'])}")
rows.append(f"  schema-unique:    {sorted(f for f, v in fields.items() if v['unique']['value'])}")

rows.append("\n=== create: not attempted")
rows.append("  PublishedFileType has no project field, so a row made here would appear in every")
rows.append("  project on the site and DELETE only retires it. The create contract stays unverified;")
rows.append("  the schema declaration above is what a caller has, and probe 012 shows that flag is")
rows.append("  not the server's contract.")

_lib.emit("entity_types/PublishedFileType", "\n".join(rows), env)
