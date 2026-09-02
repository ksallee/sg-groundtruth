"""Q: can _summarize answer the inspector's questions more cheaply than fetching rows?

The inspector needs two things per field: how often it is filled, and how many distinct values it
carries. Fill rate alone is misleading (probe 007) — a field can be 100% filled with one repeated
value and carry no information at all. Cardinality is the better discriminator; this asks what it costs.
"""
import json
import time

import _lib

env = _lib.load_env()
c = _lib.client()
BBB = 70
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
PROJ = ["project", "is", {"type": "Project", "id": BBB}]
rows = []


def summarize(body, entity="versions"):
    t = time.time()
    r = c.post(f"/entity/{entity}/_summarize", headers=ARR, json=body)
    return r, round((time.time() - t) * 1000)


rows.append("=== content type: same vendor requirement as _search (probe 004)")
r, _ = summarize({"filters": [PROJ], "summary_fields": [{"field": "id", "type": "count"}]})
rows.append(f"  vendor array Content-Type -> {r.status_code} {json.dumps(r.json()['data'])}")
plain = c.post("/entity/versions/_summarize", json={"filters": [PROJ],
               "summary_fields": [{"field": "id", "type": "count"}]})
rows.append(f"  application/json          -> {plain.status_code} "
            f"{plain.json()['errors'][0]['title'][:60]}")

rows.append("\n=== grouping: one group per distinct value, and '' for empty")
rows.append(f"  {'field':<18}{'groups':>7}{'ms':>7}  interpretation")
for f in ("sg_status_list", "entity", "code", "sg_task", "flagged", "description", "sg_version_type"):
    r, ms = summarize({"filters": [PROJ], "summary_fields": [{"field": "id", "type": "count"}],
                       "grouping": [{"field": f, "type": "exact", "direction": "asc"}]})
    if r.status_code != 200:
        rows.append(f"  {f:<18}{r.status_code:>7}  {r.text[:70]}")
        continue
    g = r.json()["data"]["groups"]
    _lib.register_names(*[str(x["group_name"]) for x in g])   # group names are real values
    empty = sum(x["summaries"]["id"] for x in g if str(x["group_name"]).strip() == "")
    total = r.json()["data"]["summaries"]["id"]
    note = ("identifier - every row distinct" if len(g) == total else
            "no information - one value" if len(g) == 1 else
            f"{len(g)} values, {empty} empty")
    rows.append(f"  {f:<18}{len(g):>7}{ms:>7}  {note}")

rows.append("\n=== fill rate without fetching rows")
tot = summarize({"filters": [PROJ], "summary_fields": [{"field": "id", "type": "count"}]})[0] \
    .json()["data"]["summaries"]["id"]
for f in ("sg_task", "image", "description", "sg_path_to_movie", "flagged"):
    r, ms = summarize({"filters": [PROJ, [f, "is_not", None]],
                       "summary_fields": [{"field": "id", "type": "count"}]})
    got = r.json()["data"]["summaries"]["id"] if r.ok else r.json()["errors"][0]["title"][:70]
    rows.append(f"  {f:<18} {r.status_code} {got}/{tot}")

rows.append("\n=== summary types")
for t in ("count", "sum", "average", "maximum", "minimum"):
    r, _ = summarize({"filters": [PROJ], "summary_fields": [{"field": "frame_count", "type": t}]})
    rows.append(f"  frame_count {t:<8} -> {r.status_code} {json.dumps(r.json().get('data', {}))[:70]}")

rows.append("\n=== cardinality cap? 300 shots, all distinct codes")
r, ms = summarize({"filters": [PROJ], "summary_fields": [{"field": "id", "type": "count"}],
                   "grouping": [{"field": "code", "type": "exact", "direction": "asc"}]}, "shots")
n = len(r.json()["data"]["groups"])
_lib.register_names(*[str(x["group_name"]) for x in r.json()["data"]["groups"]])
rows.append(f"  Shot.code -> {n} groups of {r.json()['data']['summaries']['id']} shots, {ms}ms")

rows.append("\n=== cost against the alternative")
t = time.time()
c.get("/entity/versions", params={"filter[project.Project.id]": BBB, "page[size]": 100,
                                  "fields": "code,sg_status_list,description,sg_task,image"})
one_fetch = round((time.time() - t) * 1000)
rows.append(f"  one paged fetch of 100 rows          {one_fetch}ms")
rows.append(f"  ~300ms x 61 fields of _summarize     ~{300 * 61}ms")

actual = "\n".join(rows)
_lib.record("020_summarize", "POST /entity/<type>/_summarize",
            "Summarize is a cheap aggregate call.",
            actual,
            "_summarize takes the SAME vendor Content-Type as _search (application/json is 415, probe "
            "004) and answers the inspector's second question directly: `grouping` by a field returns "
            "one group per distinct value with a count, so ONE call yields both cardinality and the "
            "empty count - empty values come back as a '' group. That is the metric fill rate cannot "
            "give: Version.code returns one group per row (an identifier, useless to expose) and "
            "flagged returns exactly one group (no information at all), while both look identical to a "
            "fill-rate scan. Grouping is NOT capped - 300 distinct Shot codes return 300 groups. "
            "Checkbox fields cannot be filtered `is_not None` at all (400), which is the same trap as "
            "probe 007 from the other side. BUT it is not free: ~300ms typical and up to 1.5s when the "
            "grouped field is an entity, so scanning all 61 Version fields costs far more than a single "
            "paged fetch of 100 rows. Use one fetch for the broad fill-rate pass, then _summarize per "
            "candidate field to rank the shortlist by cardinality.",
            env, tags=("query", "inspector", "fill-rate", "schema", "cost", "list-field"))
print(actual)
