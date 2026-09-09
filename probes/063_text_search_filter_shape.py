"""Q: what shape does the per-type filter in `entity_types` take, and what enforces it?

`_text_search` keys a filter by the type it applies to, and the card records only the array form
under `api3_array`. The `filters` of `POST /entity/<type>/_search` follow the vendor content type
(probe 004); this asks whether the value of an `entity_types` key follows it too, whether a nested
group filters or is accepted and ignored, what a field the type lacks answers, and whether the
`text` rule of probe 053 still holds once a filter is present.

Read-only. Every call is a search over one sample project's own rows.

    python probes/063_text_search_filter_shape.py
"""
import json

import _lib

env = _lib.load_env()
c = _lib.client()
P = _lib.sample_projects(c, env)[0]

ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
HSH = {"Content-Type": "application/vnd+shotgun.api3_hash+json"}
TYPES = [("api3_array", ARR), ("api3_hash", HSH)]
PROJECT_IS = ["project", "is", {"type": "Project", "id": P}]
rows = []


def out(s=""):
    rows.append(s)


def head(s):
    out(f"\n\n===== {s}")


def search(text, entity_types, headers, page=None):
    body = {"text": text, "entity_types": entity_types, "page": page or {"size": 25}}
    return c.post("/entity/_text_search", headers=headers, json=body)


def err(r):
    """The whole errors[] object. Trimming at capture cuts the part worth having."""
    try:
        return json.dumps(r.json().get("errors", r.json()))
    except ValueError:
        return repr(r.text[:300])


def names(r):
    return sorted(x["attributes"]["name"] for x in r.json().get("data", []))


def report(label, r, width=58, show=0):
    if r.ok:
        got = names(r)
        _lib.note_names(*got)
        out(f"  {label:<{width}} {r.status_code}, {len(got)} rows"
            + (f"  {got[:show]}" if show else ""))
    else:
        out(f"  {label:<{width}} {r.status_code} {err(r)}")
    return r


# The rows this probe measures against, read off the sample project rather than made.
shots = c.post("/entity/shots/_search", headers=ARR,
               json={"filters": [PROJECT_IS], "fields": "code", "page": {"size": 25}})
codes = [x["attributes"]["code"] for x in shots.json()["data"] if x["attributes"]["code"]]
_lib.note_names(*codes)
STEM = codes[0][:5]                       # a fragment every Shot code in the project shares
TAIL = codes[0][-4:]                      # a second fragment of the same code, for a two-word text
C0, C1 = codes[0], codes[1]               # two whole codes, one row each, so a count is readable
out(f"sample project {P}: {len(codes)} Shots read for fixtures, "
    f"text stem {STEM!r}, whole codes {C0!r} and {C1!r}")

GROUP = {"logical_operator": "and", "conditions": [PROJECT_IS]}
IS_C0, IS_C1 = ["code", "is", C0], ["code", "is", C1]
NESTED = {"logical_operator": "and",
          "conditions": [PROJECT_IS,
                         {"logical_operator": "or", "conditions": [IS_C0, IS_C1]}]}
DEEP = {"logical_operator": "and",
        "conditions": [{"logical_operator": "or",
                        "conditions": [{"logical_operator": "and",
                                        "conditions": [PROJECT_IS, IS_C0]},
                                       IS_C1]}]}

SHAPES = [
    ("[]", []),
    ("[[project, is, {Project, id}]]", [PROJECT_IS]),
    ("two triples in one array", [PROJECT_IS, ["code", "contains", STEM]]),
    ('{"logical_operator": "and", "conditions": [triple]}', GROUP),
    ('{"logical_operator": "and", "conditions": []}', {"logical_operator": "and",
                                                       "conditions": []}),
    ('{"logical_operator": "or", "conditions": [triple]}', {"logical_operator": "or",
                                                            "conditions": [PROJECT_IS]}),
    ("a group nested in a group (or inside and)", NESTED),
    ("three levels of group", DEEP),
    ('{"conditions": [triple]}, no logical_operator', {"conditions": [PROJECT_IS]}),
    ("conditions as {path, relation, values} objects",
     {"logical_operator": "and",
      "conditions": [{"path": "project", "relation": "is",
                      "values": [{"type": "Project", "id": P}]}]}),
    ("a group as one element of an array", [PROJECT_IS, GROUP]),
    ("{}", {}),
    ("null", None),
    ('"project"', "project"),
]

# ------------------------------------------------------------------ 1. the shape

head("1. one filter shape at a time on {\"Shot\": <filter>}, under each Content-Type")
for name, ct in TYPES:
    out(f"\n-- Content-Type: application/vnd+shotgun.{name}+json")
    for label, shape in SHAPES:
        report(label, search(STEM, {"Shot": shape}, ct))

head("2. the same shapes with no Content-Type, and with application/json")
for label, hdr in (("no Content-Type", {}), ("application/json", {"Content-Type":
                                                                 "application/json"})):
    for shape_label, shape in (("[]", []), ("group", GROUP)):
        report(f"{label}, {shape_label}", search(STEM, {"Shot": shape}, hdr))

head("3. one map, two types, the two shapes mixed")
for name, ct in TYPES:
    out(f"\n-- Content-Type: application/vnd+shotgun.{name}+json")
    report("Shot: array, Asset: group", search(STEM, {"Shot": [PROJECT_IS], "Asset": GROUP}, ct))
    report("Shot: group, Asset: array", search(STEM, {"Shot": GROUP, "Asset": [PROJECT_IS]}, ct))

# ------------------------------------------------------------------ 4. does it filter

head("4. does the group filter, or is it accepted and ignored?")
out(f"  every call below is Content-Type api3_hash, text {STEM!r}, which alone matches "
    f"{len(names(search(STEM, {'Shot': GROUP}, HSH)))} rows at the 25 cap")
a = report(f"and[project, code is {C0!r}]",
           search(STEM, {"Shot": {"logical_operator": "and",
                                  "conditions": [PROJECT_IS, IS_C0]}}, HSH), show=3)
b = report(f"and[project, code is {C1!r}]",
           search(STEM, {"Shot": {"logical_operator": "and",
                                  "conditions": [PROJECT_IS, IS_C1]}}, HSH), show=3)
both = report("and[project, or[the two codes]]", search(STEM, {"Shot": NESTED}, HSH), show=3)
deep = report("and[or[and[project, code is a], code is b]]", search(STEM, {"Shot": DEEP}, HSH),
              show=3)
if both.ok and a.ok and b.ok:
    out(f"  or[a, b] == a + b: {sorted(names(a) + names(b)) == names(both)}")
if deep.ok and both.ok:
    out(f"  three levels == or[a, b]: {names(deep) == names(both)}")

# The array form has no operator of its own. Two triples are the `and` of both, or they are not.
out("\n  the same question under api3_array, which has no logical_operator")
arr_two = report(f"[project is {P}, code is {C0!r}]",
                 search(STEM, {"Shot": [PROJECT_IS, IS_C0]}, ARR), show=3)
if arr_two.ok and a.ok:
    out(f"  two triples == and[the same two]: {names(arr_two) == names(a)}")

# One filter per key, or one filter for the call?
out("\n  a narrow filter on one key and a wide one on the other, same call")
mixed = report("Shot: and[project, code is a], Asset: and[project]",
               search(STEM, {"Shot": {"logical_operator": "and",
                                      "conditions": [PROJECT_IS, IS_C0]},
                             "Asset": GROUP}, HSH), show=4)
if mixed.ok:
    kinds = sorted({x["type"] for x in mixed.json()["data"]})
    shots_back = [x["attributes"]["name"] for x in mixed.json()["data"] if x["type"] == "Shot"]
    out(f"  types returned: {kinds}; Shots returned: {shots_back}")

# ------------------------------------------------------------------ 5. a field the type lacks

head("5. a filter naming a field the type does not have")
present = set(c.get("/schema/Shot/fields").json()["data"])
MISSING = [f for f in ("content", "subject", "sg_status_list", "sg_not_a_field")
           if f not in present]
out(f"  not on Shot: {MISSING}")
for name, ct in TYPES:
    out(f"\n-- Content-Type: application/vnd+shotgun.{name}+json")
    for f in MISSING:
        triple = [f, "is", "x"]
        shape = [triple] if ct is ARR else {"logical_operator": "and", "conditions": [triple]}
        report(f"Shot filtered on {f!r}", search(STEM, {"Shot": shape}, ct))
    bogus = ["code", "definitely_not_an_operator", "x"]
    shape = [bogus] if ct is ARR else {"logical_operator": "and", "conditions": [bogus]}
    report("an operator that does not exist", search(STEM, {"Shot": shape}, ct))

out("\n  the same name, two levels down inside an or group")
report(f"and[project, or[code is a, {MISSING[0]!r} is x]]",
       search(STEM, {"Shot": {"logical_operator": "and",
                              "conditions": [PROJECT_IS,
                                             {"logical_operator": "or",
                                              "conditions": [IS_C0,
                                                             [MISSING[0], "is", "x"]]}]}}, HSH))

out("\n  a bad filter on one type of a map whose other types are fine")
bad = MISSING[0] if MISSING else "sg_not_a_field"
report(f"Shot on {bad!r}, Asset on project",
       search(STEM, {"Shot": {"logical_operator": "and",
                              "conditions": [[bad, "is", "x"]]},
                     "Asset": GROUP}, HSH))
report("Shot on project, Asset on project",
       search(STEM, {"Shot": GROUP, "Asset": GROUP}, HSH))
report("a type that does not exist, with a filter",
       search(STEM, {"NotAType": GROUP}, HSH))

# ------------------------------------------------------------------ 6. text, with a filter

head("6. does `text` still need every word once a per-type filter is present?")
out(f"  Content-Type api3_hash, {{\"Shot\": and[project is {P}]}} on every row")
for text in (STEM, TAIL, f"{STEM} {TAIL}", f"{TAIL} {STEM}", f"{STEM} zzznotaword",
             "zzznotaword", f"{STEM}  {TAIL}", STEM.upper()):
    report(repr(text), search(text, {"Shot": GROUP}, HSH), show=2)
out("\n  and with no filter at all, the same texts")
for text in (f"{STEM} {TAIL}", f"{STEM} zzznotaword"):
    report(repr(text), search(text, {"Shot": []}, ARR), show=2)
out("\n  a filter that matches nothing, and a text that matches everything")
report("code contains a string no row holds",
       search(STEM, {"Shot": {"logical_operator": "and",
                              "conditions": [PROJECT_IS,
                                             ["code", "contains", "zzznotaword"]]}}, HSH))
report("text one letter, filtered to the project", search(STEM[0], {"Shot": GROUP}, HSH))

_lib.emit("063_text_search_filter_shape", "\n".join(rows), env)
