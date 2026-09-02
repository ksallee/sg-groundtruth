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
PROJECT = _lib.sample_projects(c, env)[0]
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
PROJ = ["project", "is", {"type": "Project", "id": PROJECT}]
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
    _lib.note_names(*[str(x["group_name"]) for x in g])   # group names are real values
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
r, _ = summarize({"filters": [PROJ], "summary_fields": [{"field": "id", "type": "definitely_not_a_type"}]})
rows.append(f"  bogus type -> {r.status_code} {json.dumps(r.json()['errors'])}")

rows.append("\n=== two types on one field: `summaries` is keyed by field, so only one survives")
for sf in ([{"field": "id", "type": "count"}],
           [{"field": "id", "type": "maximum"}],
           [{"field": "id", "type": "count"}, {"field": "id", "type": "maximum"}],
           [{"field": "id", "type": "maximum"}, {"field": "id", "type": "count"}],
           [{"field": "id", "type": "count"}, {"field": "id", "type": "count"}],
           [{"field": "id", "type": "count"}, {"field": "id", "type": "minimum"},
            {"field": "id", "type": "maximum"}],
           [{"field": "id", "type": "count"}, {"field": "frame_count", "type": "sum"}]):
    r, _ = summarize({"filters": [PROJ], "summary_fields": sf})
    sent = " + ".join(f"{x['field']} {x['type']}" for x in sf)
    rows.append(f"  {sent:<46} -> {r.status_code} {json.dumps(r.json()['data']['summaries'])}")

rows.append("\n=== grouping on an entity field: what group_name and group_value each hold")
for f in ("user", "sg_task", "sg_status_list"):
    r, _ = summarize({"filters": [PROJ], "summary_fields": [{"field": "id", "type": "count"}],
                      "grouping": [{"field": f, "type": "exact", "direction": "asc"}]})
    g = r.json()["data"]["groups"]
    _lib.note_from(g)
    _lib.note_names(*[str(x["group_name"]) for x in g])
    labels = [str(x["group_name"]) for x in g]
    dupes = {n for n in labels if labels.count(n) > 1 and n}
    rows.append(f"  {f}: {len(g)} groups, {len(set(labels))} distinct group_name, "
                f"duplicate labels {sorted(dupes)}")
    for x in g[:3]:
        rows.append(f"    {json.dumps(x)}")

rows.append("\n=== cardinality cap? 300 shots, all distinct codes")
r, ms = summarize({"filters": [PROJ], "summary_fields": [{"field": "id", "type": "count"}],
                   "grouping": [{"field": "code", "type": "exact", "direction": "asc"}]}, "shots")
n = len(r.json()["data"]["groups"])
_lib.note_names(*[str(x["group_name"]) for x in r.json()["data"]["groups"]])
rows.append(f"  Shot.code -> {n} groups of {r.json()['data']['summaries']['id']} shots, {ms}ms")

rows.append("\n=== above 300: the widest code field reachable read-only, and the whole site")


def group_code(slug, filters):
    r, ms = summarize({"filters": filters, "summary_fields": [{"field": "id", "type": "count"}],
                       "grouping": [{"field": "code", "type": "exact", "direction": "asc"}]}, slug)
    if not r.ok:
        return None, r.json()["errors"][0], ms
    g = r.json()["data"]["groups"]
    _lib.note_names(*[str(x["group_name"]) for x in g])
    return len(g), r.json()["data"]["summaries"]["id"], ms


for slug in ("versions", "shots"):
    best, best_n = None, -1
    for pid in _lib.sample_projects(c, env):
        n = summarize({"filters": [["project", "is", {"type": "Project", "id": pid}]],
                       "summary_fields": [{"field": "id", "type": "count"}]}, slug)[0] \
            .json()["data"]["summaries"]["id"]
        if n > best_n:
            best, best_n = pid, n
    g, tot_rows, ms = group_code(slug, [["project", "is", {"type": "Project", "id": best}]])
    rows.append(f"  {slug}.code, widest sample project  -> {g} groups of {tot_rows} rows, {ms}ms")
    g, tot_rows, ms = group_code(slug, [])
    rows.append(f"  {slug}.code, whole site             -> {g} groups of {tot_rows} rows, {ms}ms")

rows.append("\n=== cost against the alternative")
t = time.time()
c.get("/entity/versions", params={"filter[project.Project.id]": PROJECT, "page[size]": 100,
                                  "fields": "code,sg_status_list,description,sg_task,image"})
one_fetch = round((time.time() - t) * 1000)
rows.append(f"  one paged fetch of 100 rows          {one_fetch}ms")
rows.append("  one _summarize per field             ~300ms each, up to 1.5s")

actual = "\n".join(rows)
_lib.emit("020_summarize", actual, env)
