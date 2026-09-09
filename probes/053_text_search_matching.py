"""Q: what does `_text_search` match, and how many rows will it hand back?

The card records the request shape and the row shape. It does not record the page cap, what a word
is matched against, or what a second word costs. This probe measures the `page.size` boundary and
the default, then the matching rules against rows whose names it made itself, then the latency of
one multi-type call against the same question asked as one `contains` `_search` per type.

Read-only by default: the cap, the default page size, `sort` and the latency comparison need no
rows. `--write` adds twelve rows in the sandbox project, named `zzprobe_053_*`, and deletes them.
"""
import json
import random
import string
import time

import _lib

env = _lib.load_env()
c = _lib.client()
SANDBOX = _lib.sandbox_id(c, env)
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
PROJECT_IS = ["project", "is", {"type": "Project", "id": SANDBOX}]
MINE = ["code", "contains", "zzprobe_053"]
rows = []


def out(s=""):
    rows.append(s)


def head(s):
    out(f"\n\n===== {s}")


def search(text, entity_types, page=None):
    body = {"text": text, "entity_types": entity_types}
    if page is not None:
        body["page"] = page
    t = time.perf_counter()
    r = c.post("/entity/_text_search", headers=ARR, json=body)
    return r, round((time.perf_counter() - t) * 1000)


def err(r):
    try:
        return json.dumps(r.json().get("errors", r.json()))
    except ValueError:
        return repr(r.text[:200])


# ------------------------------------------------------------------ the page cap

head("page.size, text matching more rows than any cap")

VERSIONS = {"Version": [PROJECT_IS]}
for page in ({"size": 1}, {"size": 24}, {"size": 25}, {"size": 26}, {"size": 100},
             {"size": 0}, {"size": -1}, {"size": "25"}, {"size": 25, "number": 2},
             {"size": 25, "number": 0}, {"number": 2}, {}):
    r, ms = search("v", VERSIONS, page)
    n = len(r.json().get("data", [])) if r.ok else None
    out(f"\n-- page={json.dumps(page)} -> {r.status_code}" + (f", {n} rows" if r.ok else ""))
    if not r.ok:
        out("   " + err(r))
    elif page.get("number") == 2:
        out(f"   links: {json.dumps(r.json().get('links'))}")

r, _ = search("v", VERSIONS)
out(f"\n-- page key absent -> {r.status_code}, {len(r.json().get('data', []))} rows  "
    f"links: {json.dumps(r.json().get('links'))}")

# Two pages of 25 at size 25 and number 1/2: are the ids disjoint, so is the cap pageable?
ids = []
for number in (1, 2, 3):
    r, _ = search("v", VERSIONS, {"size": 25, "number": number})
    got = [x["id"] for x in r.json().get("data", [])]
    ids.append(got)
    out(f"   number={number}: {len(got)} rows, first {got[:1]}")
out(f"   page 1 and 2 disjoint: {not (set(ids[0]) & set(ids[1]))}; "
    f"page 3 repeats page 1: {ids[2] == ids[0]}")

# The site's own spec gives `sort` on this body and `page.size` a default of 500, both shared with
# the paginated reads.
head("sort, which the site's spec.json advertises on this body")
base = None
for sort in (None, "-id", "id", "code", "-not_a_field"):
    body = {"text": "v", "entity_types": VERSIONS, "page": {"size": 5}}
    if sort:
        body["sort"] = sort
    r = c.post("/entity/_text_search", headers=ARR, json=body)
    got = [x["id"] for x in r.json().get("data", [])] if r.ok else None
    base = base or got
    out(f"-- sort={sort!r} -> {r.status_code}, {got}" + ("  same order" if got == base else ""))

# ------------------------------------------------------------------ latency

head("one _text_search against one contains _search per type")

IDENTITY = {"Shot": "code", "Asset": "code", "Version": "code", "Task": "content",
            "Note": "subject", "Playlist": "code", "Sequence": "code", "PublishedFile": "code",
            "Cut": "code", "CutItem": "code", "Delivery": "sg_title", "Episode": "code",
            "Camera": "code", "Element": "code", "Level": "code", "Scene": "code"}
SLUG = {"Shot": "shots", "Asset": "assets", "Version": "versions", "Task": "tasks",
        "Note": "notes", "Playlist": "playlists", "Sequence": "sequences",
        "PublishedFile": "published_files", "Cut": "cuts", "CutItem": "cut_items",
        "Delivery": "deliveries", "Episode": "episodes", "Camera": "cameras",
        "Element": "elements", "Level": "levels", "Scene": "scenes"}
present = set(c.get("/schema").json()["data"])
TYPES = [t for t in IDENTITY if t in present][:14]
out(f"\n{len(TYPES)} types: {', '.join(TYPES)}")

WORDS = ["".join(random.choice(string.ascii_lowercase) for _ in range(7)) for _ in range(4)]
one, many = [], []
for word in WORDS:
    r, ms = search(word, {t: [PROJECT_IS] for t in TYPES}, {"size": 25})
    one.append(ms)
    t0 = time.perf_counter()
    hits = 0
    for t in TYPES:
        s = c.post(f"/entity/{SLUG[t]}/_search", headers=ARR,
                   json={"filters": [PROJECT_IS, [IDENTITY[t], "contains", word]],
                         "fields": IDENTITY[t], "page": {"size": 25}})
        hits += len(s.json().get("data", [])) if s.ok else 0
    many.append(round((time.perf_counter() - t0) * 1000))
    out(f"   fresh word: _text_search {one[-1]} ms ({len(r.json().get('data', []))} rows), "
        f"{len(TYPES)} x _search {many[-1]} ms ({hits} rows)")
out(f"\n   _text_search {min(one)}-{max(one)} ms, {len(TYPES)} x _search {min(many)}-{max(many)} ms "
    f"over {len(WORDS)} runs")

_lib.emit("053_text_search_matching", "\n".join(rows), env)
READ_ONLY = len(rows)

# ------------------------------------------------------------------ matching

if not _lib.writes_allowed():
    raise SystemExit("\n--write to measure the matching rules against rows named by this probe")

SHOTS = ["zzprobe_053_qat_0020", "zzprobe_053_qat_sh010", "zzprobe_053_kif_hello",
         "zzprobe_053_kif_only"]
ASSETS = ["zzprobe_053_qat_charA", "zzprobe_053_kif_skyline"]
TOKEN = "wubblefish"

with _lib.Created(c) as made:
    name = {}
    for code in SHOTS:
        body = {"project": {"type": "Project", "id": SANDBOX}, "code": code}
        if code.endswith("_only"):
            body["description"] = f"{TOKEN} glorp, a word this row's code does not hold"
        name[made.add("shots", c.post("/entity/shots", json=body).json()["data"]["id"])] = code
    for code in ASSETS:
        name[made.add("assets", c.post("/entity/assets", json={
            "project": {"type": "Project", "id": SANDBOX}, "code": code}).json()["data"]["id"])] = code
    VERSION = made.add("versions", c.post("/entity/versions", json={
        "project": {"type": "Project", "id": SANDBOX},
        "code": "zzprobe_053_qat_v001"}).json()["data"]["id"])
    name[VERSION] = "zzprobe_053_qat_v001"

    # Every matching call carries the probe's own rows as a second filter, so a row another probe
    # is making in the same sandbox at the same time cannot join the answer.
    OWN = {"Shot": [PROJECT_IS, MINE], "Asset": [PROJECT_IS, MINE]}

    head("what a word is matched against")
    out(f"\nrows: {', '.join(SHOTS)} (Shot), {', '.join(ASSETS)} (Asset)")
    out(f"      zzprobe_053_kif_only.description holds {TOKEN!r}, its code does not")

    for text in ("qat", "QAT", "Qat", "qAt", "0020", "020", "h01", "kif", "q", "k",
                 "qat 0020", "0020 qat", "qat kif", "qat nomatch", "zzprobe_053",
                 "qat_0020", "053_qat", "_qat_", "at", "zzprobe 053 qat"):
        r, ms = search(text, OWN, {"size": 25})
        got = sorted(name.get(x["id"], f"?{x['type']}/{x['id']}") for x in r.json().get("data", []))
        out(f"\n-- {text!r} -> {r.status_code}, {len(got)} rows  {ms} ms")
        out("   " + (", ".join(got) if got else "(none)"))

    head("a token that is only in description")
    for text in (TOKEN, "glorp", "wubble", "this row's"):
        r, _ = search(text, OWN, {"size": 25})
        got = [name.get(x["id"], x["id"]) for x in r.json().get("data", [])]
        out(f"\n-- {text!r} filtered to this probe's rows -> {r.status_code}, {got}")
    for text in (TOKEN, "glorp"):
        r, _ = search(text, {"Shot": [PROJECT_IS]}, {"size": 25})
        got = [x["attributes"]["name"] for x in r.json().get("data", [])]
        out(f"-- {text!r} over every Shot in the sandbox -> {r.status_code}, {len(got)} rows")
    SHOT_ONLY = [k for k, v in name.items() if v.endswith("_only")][0]
    dsc = c.get(f"/entity/shots/{SHOT_ONLY}",
                params={"fields": "description"}).json()["data"]["attributes"]["description"]
    out(f"   the description reads: {dsc!r}")

    # An Asset's description, to say whether the miss is Shot.description or every description.
    ASSET_DSC = made.add("assets", c.post("/entity/assets", json={
        "project": {"type": "Project", "id": SANDBOX}, "code": "zzprobe_053_kif_asset",
        "description": f"{TOKEN} on an Asset"}).json()["data"]["id"])
    name[ASSET_DSC] = "zzprobe_053_kif_asset"
    r, _ = search(TOKEN, OWN, {"size": 25})
    out(f"-- {TOKEN!r} with an Asset.description holding it too -> {r.status_code}, "
        f"{[name.get(x['id'], x['id']) for x in r.json().get('data', [])]}")

    # A Version whose own code holds none of the word, linked to the Shot whose code does.
    LINKED = made.add("versions", c.post("/entity/versions", json={
        "project": {"type": "Project", "id": SANDBOX}, "code": "zzprobe_053_zzz_v001",
        "entity": {"type": "Shot", "id": [k for k, v in name.items()
                                          if v == "zzprobe_053_qat_0020"][0]}}).json()["data"]["id"])
    name[LINKED] = "zzprobe_053_zzz_v001"
    r, _ = search("qat", {"Version": [PROJECT_IS, MINE]}, {"size": 25})
    got = r.json().get("data", [])
    out(f"-- 'qat' over Versions, one of them linked to the Shot named zzprobe_053_qat_0020 -> "
        f"{[name.get(x['id'], x['id']) for x in got]}")
    out(f"   the linked Version reads back: "
        f"{json.dumps([x['attributes'] for x in c.post('/entity/_text_search', headers=ARR, json={'text': 'zzz', 'entity_types': {'Version': [PROJECT_IS, MINE]}}).json()['data']])}")

    head("result order across types")
    keysets = [("Shot", "Asset", "Version"), ("Version", "Asset", "Shot"),
               ("Asset", "Shot", "Version")]
    for keys in keysets:
        r, _ = search("qat", {k: [PROJECT_IS, MINE] for k in keys}, {"size": 25})
        got = [(x["type"], x["id"]) for x in r.json().get("data", [])]
        out(f"\n-- keys {list(keys)} -> "
            f"{[f'{t}/{i} {name.get(i, i)}' for t, i in got]}")
    r, _ = search("zzprobe_053", {k: [PROJECT_IS, MINE] for k in ("Shot", "Asset", "Version")},
                  {"size": 25})
    got = [(x["type"], x["id"]) for x in r.json().get("data", [])]
    out(f"\n-- every row this probe made, keys Shot, Asset, Version -> "
        f"{[f'{t}/{i} {name.get(i, i)}' for t, i in got]}")
    out(f"   id ascending: {[i for _, i in got] == sorted(i for _, i in got)}")
    out(f"   grouped by type: {[t for t, _ in got]}")
    out(f"   name length ascending: "
        f"{[len(name[i]) for _, i in got] == sorted(len(name[i]) for _, i in got)}")

    # Three names sharing a token, created longest first, so creation order and id both run
    # against name length.
    for code in ("zzprobe_053_zed_the_longest_of_the_three", "zzprobe_053_zed",
                 "zzprobe_053_zed_middling"):
        name[made.add("shots", c.post("/entity/shots", json={
            "project": {"type": "Project", "id": SANDBOX}, "code": code}).json()["data"]["id"])] = code
    r, _ = search("zed", {"Shot": [PROJECT_IS, MINE]}, {"size": 25})
    got = [x["id"] for x in r.json().get("data", [])]
    out(f"\n-- 'zed', three Shots created longest name first -> "
        f"{[f'{i} {name[i]} ({len(name[i])})' for i in got]}")

_lib.emit("053_text_search_matching writes", "\n".join(rows[READ_ONLY:]), env)
