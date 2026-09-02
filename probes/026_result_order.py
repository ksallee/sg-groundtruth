"""Q: in what order does a read return rows, and can a caller rely on it?

Production code that filters on ["id", "in", [...]] re-sorts client-side against the id list it sent,
to keep the order the user selected on screen. This asks whether that re-sort is necessary, what the
order is when no sort is asked for, whether a sort survives paging, and whether an unsortable field
says so. Read-only.
"""
import json

import _lib

env = _lib.load_env()
c = _lib.client()
PROJECT = _lib.sample_projects(c, env)[0]
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
PROJ = ["project", "is", {"type": "Project", "id": PROJECT}]
BASE = {"filter[project.Project.id]": PROJECT, "fields": "code"}
rows = []


def get_ids(sort=None, size=20, number=None, extra=None):
    p = dict(BASE, **{"page[size]": size})
    if sort is not None:
        p["sort"] = sort
    if number is not None:
        p["page[number]"] = number
    p.update(extra or {})
    r = c.get("/entity/versions", params=p)
    return r, [row["id"] for row in r.json().get("data", [])]


def search_ids(body):
    r = c.post("/entity/versions/_search", headers=ARR, json=body)
    return r, [row["id"] for row in r.json().get("data", [])]


def err(r):
    return json.dumps(r.json().get("errors", r.json()))


_, ALL = get_ids(sort="id", size=500)
rows.append(f"=== reference set: {len(ALL)} Versions in one project, sort=id")

# Eight ids spread across the set, then a fixed permutation of them. Fixed, not random, so two
# runs of this probe compare.
step = max(1, len(ALL) // 8)
SAMPLE = ALL[::step][:8]
SHUFFLED = [SAMPLE[i] for i in (5, 0, 7, 2, 6, 1, 4, 3)]

rows.append("\n=== 1. ['id', 'in', [...]]: is the order of the list honoured?")
rows.append(f"  sent shuffled     {SHUFFLED}")
for label, sent in (("shuffled", SHUFFLED), ("ascending", sorted(SAMPLE)),
                    ("descending", sorted(SAMPLE, reverse=True))):
    r, got = search_ids({"filters": [["id", "in", sent]], "fields": ["code"]})
    verdict = "as sent" if got == sent else ("id asc" if got == sorted(sent) else "neither")
    rows.append(f"  POST _search  in {label:<10} -> {r.status_code} {got}  {verdict}")
r, got = get_ids(sort=None, extra={"filter[id]": ",".join(str(i) for i in SHUFFLED)})
rows.append(f"  GET filter[id]=comma list  -> {r.status_code} {got}  "
            f"{'as sent' if got == SHUFFLED else 'id asc' if got == sorted(SHUFFLED) else 'neither'}")
r, got = search_ids({"filters": [["id", "in", SHUFFLED]], "fields": ["code"], "sort": "-id"})
rows.append(f"  POST _search  in shuffled + sort=-id -> {r.status_code} {got}")

rows.append("\n=== 2. no sort at all: what order, and is it stable across identical calls?")
runs = [get_ids(sort=None, size=25)[1] for _ in range(5)]
rows.append(f"  5 identical GETs, page[size]=25: {len(set(map(tuple, runs)))} distinct orderings")
rows.append(f"  run 1 first 8     {runs[0][:8]}")
rows.append(f"  == id ascending   {runs[0] == sorted(runs[0])}")
rows.append(f"  == sort=id page 1 {runs[0] == get_ids(sort='id', size=25)[1]}")
r, desc = get_ids(sort="-id", size=25)
rows.append(f"  == sort=-id       {runs[0] == desc}")

rows.append("\n=== 3. paging: does a sorted walk visit every row exactly once? (page[size]=10)")


def walk(sort, size=10, cap=40):
    seen, n = [], 1
    while n <= cap:
        r, page = get_ids(sort=sort, size=size, number=n)
        if r.status_code != 200:
            return seen, f"{r.status_code} {err(r)}"
        if not page:                                   # empty data is the stop signal (probe 006)
            return seen, None
        seen.extend(page)
        n += 1
    return seen, f"hit the {cap}-page cap"


for sort in ("id", None, "-created_at", "sg_status_list", "code"):
    got, note = walk(sort)
    dup = len(got) - len(set(got))
    missing = len(set(ALL) - set(got))
    extra = len(set(got) - set(ALL))
    whole = get_ids(sort=sort, size=500)[1]             # the same query in one unpaged read
    rows.append(f"  sort={str(sort):<14} {len(got):>4} rows  {len(set(got)):>4} distinct  "
                f"{dup} duplicated  {missing} missed  {extra} foreign  "
                f"{'same order as one unpaged read' if got == whole else 'order differs from one unpaged read'}"
                f"  {note or ''}")

rows.append("\n=== 4. sort on a field that cannot be sorted: 400 or silent no-op?")
_, DEFAULT = get_ids(sort=None, size=20)
rows.append(f"  {'sort=':<26}{'asc':>5} {'desc':>5}  effect")
for f in ("id", "code", "created_at", "sg_status_list", "open_notes_count", "sg_uploaded_movie",
          "sg_not_a_field_at_all", "entity", "entity.Shot.code",
          "", "id desc", "+id"):
    ra, asc = get_ids(sort=f, size=20)
    rd, desc = get_ids(sort=f"-{f}" if f else "-", size=20)
    if ra.status_code != 200 or rd.status_code != 200:
        effect = f"{err(ra if not ra.ok else rd)}"
    elif asc != desc:
        effect = "sorted"
    elif asc == DEFAULT:
        effect = "accepted, ignored: same rows as no sort"
    else:
        effect = "asc == desc, differs from no sort"
    rows.append(f"  {repr(f):<26}{ra.status_code:>5} {rd.status_code:>5}  {effect}")

# All 100 rows share one project, so a project.Project.name sort is a no-op here whether or not it
# is honoured. Ask the same question site-wide, where the values differ.
sa = c.get("/entity/versions", params={"fields": "code", "page[size]": 20,
                                       "sort": "project.Project.name"})
sd = c.get("/entity/versions", params={"fields": "code", "page[size]": 20,
                                       "sort": "-project.Project.name"})
sn = c.get("/entity/versions", params={"fields": "code", "page[size]": 20})
ia, idd, inn = ([r["id"] for r in x.json().get("data", [])] for x in (sa, sd, sn))
rows.append(f"  site-wide sort=project.Project.name  {sa.status_code}/{sd.status_code}  "
            f"asc != desc {ia != idd}, asc == no sort {ia == inn}")

rows.append("\n  the same names in a filter, for contrast (probe 017):")
for f in ("sg_not_a_field_at_all", "open_notes_count", "sg_uploaded_movie"):
    r, _ = search_ids({"filters": [PROJ, [f, "is", None]], "fields": ["code"]})
    rows.append(f"  filter [{f!r}, 'is', None] -> {r.status_code} {err(r) if not r.ok else 'ok'}")

rows.append("\n=== 5. multi-key sort, and the POST _search spellings")
combos = ("sg_status_list", "sg_status_list,id", "sg_status_list,-id", "-sg_status_list,id")
seen = {}
for f in combos:
    r, got = get_ids(sort=f, size=20)
    same = [k for k, v in seen.items() if v == got]
    seen[f] = got
    rows.append(f"  sort={f:<22} {r.status_code} first 6 {got[:6]}"
                f"{'  identical to sort=' + same[0] if same else ''}")
for body in ({"sort": "-id"}, {"sort": "id"},
             {"sort": [{"field_name": "id", "direction": "desc"}]},
             {"sort": "sg_not_a_field_at_all"},
             {"sort": "open_notes_count"}):
    r, got = search_ids(dict({"filters": [PROJ], "fields": ["code"], "page": {"size": 6}}, **body))
    rows.append(f"  POST sort={json.dumps(body['sort']):<45} -> {r.status_code} "
                f"{got if r.ok else err(r)}")

_lib.emit("026_result_order", "\n".join(rows), env)
