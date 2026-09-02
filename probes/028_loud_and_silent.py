"""Q: which failures does this API announce, and which does it swallow?

Twenty-odd cases sit one per finding across the corpus. This re-runs the cheap read-only half of
them side by side, so the split between a 400 that enumerates the legal set and a 200 that drops the
request is measured in one pass rather than inferred across eleven files. The destructive writes
(field_types/text, field_types/serializable, field_types/multi_entity, entity_types/Sequence,
entity_types/Note, probe 020) are cited, never re-run: proving them again costs data.

Read-only. No --write path.
"""
import json

import _lib

env = _lib.load_env()
c = _lib.client()
PROJECT = _lib.sample_projects(c, env)[0]
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
PROJ = ["project", "is", {"type": "Project", "id": PROJECT}]
BOGUS_OP = "definitely_not_an_operator"
rows = []


def search(entity, body, headers=ARR):
    return c.post(f"/entity/{entity}/_search", headers=headers, json=body)


def ids(r):
    return [row["id"] for row in r.json().get("data", [])]


def err(r):
    """The whole errors object. Never truncated: the enumeration is the teaching content."""
    return json.dumps(r.json().get("errors", r.json()))


def one_err(r):
    e = r.json().get("errors") or [{}]
    return e[0].get("title") or json.dumps(e[0])


rows.append(f"baseline: project {PROJECT}")
r = search("versions", {"filters": [PROJ], "fields": ["code"], "page": {"size": 500}})
ALL = ids(r)
rows.append(f"  {len(ALL)} Versions, sort default")

# ---------------------------------------------------------------- loud
rows.append("\n===== loud: the rejection names the legal set")

r = search("versions", {"filters": [PROJ, ["code", BOGUS_OP, "x"]], "fields": ["code"]})
rows.append(f"\n-- 1. unknown filter operator on a text field -> {r.status_code}")
rows.append(f"   {err(r)}")

r = c.post("/entity/versions/_summarize", headers=ARR,
           json={"filters": [PROJ],
                 "summary_fields": [{"field": "id", "type": "definitely_not_a_summary_type"}]})
rows.append(f"\n-- 2. unknown _summarize type -> {r.status_code}")
rows.append(f"   {err(r)}")

for path in ("/entity/zzz_not_an_entity_type", "/schema/DisplayColumn"):
    r = c.get(path)
    rows.append(f"\n-- 3. unknown entity type {path} -> {r.status_code}")
    rows.append(f"   {err(r)}")

r = search("versions", {"filters": [PROJ, ["sg_not_a_field_at_all", "is", "x"]], "fields": ["code"]})
rows.append(f"\n-- 4. unknown field name in a filter -> {r.status_code}")
rows.append(f"   {one_err(r)}")

r = search("versions", {"filters": [PROJ, ["frame_count", "is", 2.5]], "fields": ["code"]})
rows.append(f"\n-- 5. wrong Python type as a filter value -> {r.status_code}")
rows.append(f"   {one_err(r)}")

for sort in ("", "id desc", "+id"):
    r = c.get("/entity/versions", params={"filter[project.Project.id]": PROJECT,
                                          "fields": "code", "page[size]": 5, "sort": sort})
    rows.append(f"\n-- 6. sort syntax {sort!r} -> {r.status_code}  {err(r) if not r.ok else ''}")

# ---------------------------------------------------------------- silent
rows.append("\n\n===== silent: 200, and the request is dropped")

p = {"filter[project.Project.id]": PROJECT, "fields": "code,zzz_not_a_field", "page[size]": 3}
r = c.get("/entity/versions", params=p)
got = sorted(r.json()["data"][0]["attributes"]) if r.ok and r.json().get("data") else None
rows.append(f"\n-- 7. bogus name in ?fields -> {r.status_code}  attributes {got}")

_, DEFAULT = None, ids(c.get("/entity/versions", params={
    "filter[project.Project.id]": PROJECT, "fields": "code", "page[size]": 20}))
rows.append(f"\n-- 8. sort on a field that cannot sort (first 20 ids, against no sort at all)")
for f in ("code", "open_notes_count", "sg_uploaded_movie", "sg_not_a_field_at_all"):
    a = c.get("/entity/versions", params={"filter[project.Project.id]": PROJECT, "fields": "code",
                                          "page[size]": 20, "sort": f})
    d = c.get("/entity/versions", params={"filter[project.Project.id]": PROJECT, "fields": "code",
                                          "page[size]": 20, "sort": f"-{f}"})
    asc, desc = ids(a), ids(d)
    effect = ("sorted" if asc != desc else
              "accepted and ignored: identical to no sort" if asc == DEFAULT else
              "asc == desc, and differs from no sort")
    rows.append(f"   sort={f:<22} {a.status_code} {d.status_code}  {effect}")

step = max(1, len(ALL) // 8)
SAMPLE = ALL[::step][:8]
SHUFFLED = [SAMPLE[i] for i in (5, 0, 7, 2, 6, 1, 4, 3)]
r = search("versions", {"filters": [["id", "in", SHUFFLED]], "fields": ["code"]})
got = ids(r)
rows.append(f"\n-- 9. ['id','in',[...]] -> {r.status_code}  "
            f"{'as sent' if got == SHUFFLED else 'id ascending' if got == sorted(SHUFFLED) else 'neither'}")
rows.append(f"   sent     {SHUFFLED}")
rows.append(f"   returned {got}")

LIST_FIELD = "sg_version_type"
sch = c.get(f"/schema/Version/fields/{LIST_FIELD}")
valid = (sch.json().get("data", {}).get("properties", {}).get("valid_values", {}).get("value")
         if sch.ok else None)
rows.append(f"\n-- 10. an invalid value in a `list` filter (Version.{LIST_FIELD}, "
            f"valid_values {valid})")
for label, flt in (("is <valid[0]>", ["is", (valid or [None])[0]]),
                   ("is 'zzz_not_a_valid_value'", ["is", "zzz_not_a_valid_value"]),
                   ("in [valid[0]]", ["in", [(valid or [None])[0]]]),
                   ("in [valid[0], 'zzz_not_a_valid_value']",
                    ["in", [(valid or [None])[0], "zzz_not_a_valid_value"]]),
                   ("in ['zzz_not_a_valid_value']", ["in", ["zzz_not_a_valid_value"]])):
    r = search("versions", {"filters": [PROJ, [LIST_FIELD, flt[0], flt[1]]], "fields": ["code"],
                            "page": {"size": 500}})
    rows.append(f"   {label:<42} {r.status_code}  {len(ids(r))} rows"
                f"{'  ' + one_err(r) if not r.ok else ''}")

def count(entity, filters):
    """record_count over the whole type: a page cap cannot hide a filter that did nothing."""
    r = c.post(f"/entity/{entity}/_summarize", headers=ARR,
               json={"filters": filters,
                     "summary_fields": [{"field": "id", "type": "record_count"}]})
    return r, (r.json()["data"]["summaries"].get("id") if r.ok else one_err(r))


rows.append("\n-- 11. every filter on PageSetting.settings_json, counted with record_count")
for label, filters in (("no filter", []),
                       ("contains 'ZZZNOPE'", [["settings_json", "contains", "ZZZNOPE"]]),
                       ("is null", [["settings_json", "is", None]]),
                       ("is_not null", [["settings_json", "is_not", None]]),
                       ("control: page is null", [["page", "is", None]])):
    r, n = count("page_settings", filters)
    rows.append(f"   {label:<42} {r.status_code}  {n}")

rows.append("\n-- 12. every filter on EventLogEntry.audit_trail, one project, record_count")
EL = ["project", "is", {"type": "Project", "id": PROJECT}]
for label, filters in (("project only", [EL]),
                       ("+ audit_trail is null", [EL, ["audit_trail", "is", None]]),
                       ("+ audit_trail is_not null", [EL, ["audit_trail", "is_not", None]]),
                       ("+ audit_trail contains {'x': 1}",
                        [EL, ["audit_trail", "contains", {"x": 1}]]),
                       ("control: + event_type is 'ZZZNOPE'",
                        [EL, ["event_type", "is", "ZZZNOPE"]])):
    r, n = count("event_log_entries", filters)
    rows.append(f"   {label:<42} {r.status_code}  {n}")

_lib.emit("028_loud_and_silent", "\n".join(rows), env)
