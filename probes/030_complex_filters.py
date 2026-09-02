"""Q: how are boolean and nested filters expressed, and what are their limits?

Probe 004 proved api3_hash takes one `and` group and nothing else was tried. Nesting has only ever
worked incidentally, inside the summary rollup translator. Probe 023 found the web stores a page's
filters as {path, relation, values} trees that 004 says _search rejects, and a converter from a saved
page to a runnable query turns on whether that is a translation or a pass-through.

Read-only. Every positive here has a control that must return 0 or a named row: this API accepts and
ignores (probe 028), so a 200 with rows proves nothing on its own.
"""
import json

import _lib

env = _lib.load_env()
c = _lib.client()
PROJECTS = _lib.sample_projects(c, env)
PROJECT = PROJECTS[0]
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
HSH = {"Content-Type": "application/vnd+shotgun.api3_hash+json"}
rows = []


def post(filters, headers=HSH, params=None, size=500, endpoint="_search", entity="shots", extra=None):
    body = {"filters": filters, "fields": ["code"], "page": {"size": size}}
    if extra:
        body.update(extra)
    return c.post(f"/entity/{entity}/{endpoint}", headers=headers, params=params, json=body)


def err(r):
    """Whole errors[0], source included. Slicing it cuts the part worth having (probe 017)."""
    try:
        e = r.json()["errors"][0]
    except Exception:
        return r.text
    return json.dumps({"title": e.get("title"), "source": e.get("source")})


def run(filters, **kw):
    """-> (count or 'ERR nnn', [ids] or the error body)."""
    r = post(filters, **kw)
    if not r.ok:
        return f"ERR {r.status_code}", err(r)
    d = r.json()["data"]
    return len(d), sorted(x["id"] for x in d)[:4]


def line(label, filters, expect="", **kw):
    n, detail = run(filters, **kw)
    tail = detail if isinstance(n, str) else (f"ids {detail}" if 0 < n <= 4 else "")
    rows.append(f"  {label:<46} -> {str(n):<9} {expect:<22} {tail}")
    return n


# --- fixtures -------------------------------------------------------------------------------------
shots = c.get("/entity/shots", params={"filter[project.Project.id]": PROJECT, "fields": "code",
                                       "page[size]": 5}).json()["data"]
_lib.note_from(shots)
A, B = shots[0]["id"], shots[1]["id"]
CODE_A = shots[0]["attributes"]["code"]
MID = CODE_A[2:-2]

OTHER = next((p for p in PROJECTS[1:]
              if c.get("/entity/shots", params={"filter[project.Project.id]": p, "fields": "code",
                                                "page[size]": 1}).json()["data"]), None)
other_shot = None
if OTHER:
    d = c.get("/entity/shots", params={"filter[project.Project.id]": OTHER, "fields": "code",
                                       "page[size]": 1}).json()["data"]
    _lib.note_from(d)
    other_shot = d[0]["id"]

base_all = len(post([], headers=ARR).json()["data"])
base_proj = len(post([["project", "is", {"type": "Project", "id": PROJECT}]], headers=ARR).json()["data"])
IS_A = ["id", "is", A]
IS_B = ["id", "is", B]
OR2 = {"logical_operator": "or", "conditions": [IS_A, IS_B]}
AND2 = {"logical_operator": "and", "conditions": [IS_A, IS_B]}
rows.append(f"baseline shots: no filter {base_all} (page size 500), in project {base_proj}; "
            f"control rows {A} and {B}")
rows.append("two conditions on id that share no row: `or` must be 2, `and` must be 0, "
            f"an ignored group is {base_all}")

# --- 1. or at the top level -----------------------------------------------------------------------
rows.append("\n=== 1. logical_operator at the top level, api3_hash")
line("or  [id is A, id is B]", OR2, "expect 2")
line("and [id is A, id is B]", AND2, "expect 0")
line("or  [id is A, id is 99999999]", {"logical_operator": "or",
                                       "conditions": [IS_A, ["id", "is", 99999999]]}, "expect 1")
line("or  [id is 99999999] only", {"logical_operator": "or",
                                   "conditions": [["id", "is", 99999999]]}, "expect 0")
for op in ("AND", "OR", "Or", "not", "xor", "nand", ""):
    line(f"logical_operator {op!r}, disjoint pair", {"logical_operator": op, "conditions": [IS_A, IS_B]},
         "0=and 2=or")
line("conditions [] with and", {"logical_operator": "and", "conditions": []}, f"{base_all}=no filter")
line("conditions [] with or", {"logical_operator": "or", "conditions": []}, f"{base_all}=no filter")
line("logical_operator key absent", {"conditions": [IS_A, IS_B]}, "expect 400")
line("conditions key absent", {"logical_operator": "or"}, "?")

# --- 2. depth -------------------------------------------------------------------------------------
rows.append("\n=== 2. depth: N `and` groups wrapping one leaf group")
rows.append("     positive must stay 2, control must stay 0; either at "
            f"{base_all} means the inner group was dropped")


def nested_body(leaf, depth):
    """Built as text: json.dumps recurses, and CPython hits its own limit long before the server does."""
    wrap = '{"logical_operator":"and","conditions":['
    return ('{"fields":["code"],"page":{"size":500},"filters":'
            + wrap * (depth - 1) + json.dumps(leaf) + "]}" * (depth - 1) + "}")


def run_raw(body):
    r = c.post("/entity/shots/_search", headers=HSH, data=body.encode())
    if not r.ok:
        return f"ERR {r.status_code}", err(r)
    return len(r.json()["data"]), ""


rows.append(f"  {'groups deep':<14}{'bytes':>9}  {'or leaf (2)':<38}{'and leaf (0)':<38}")
for depth in (1, 2, 3, 5, 10, 20, 50, 100, 200, 250, 256, 257, 300, 400, 500, 1000, 5000):
    pb, nb = nested_body(OR2, depth), nested_body(AND2, depth)
    p, pd = run_raw(pb)
    n, nd = run_raw(nb)
    flag = ""
    if p == base_all or n == base_all:
        flag = "  <- INNER GROUP IGNORED"
    elif isinstance(p, str) or isinstance(n, str):
        flag = "  <- REJECTED"
    rows.append(f"  {depth:<14}{len(pb):>9}  {(str(p) + ' ' + str(pd)).strip():<38}"
                f"{(str(n) + ' ' + str(nd)).strip():<38}{flag}")

rows.append("  exact boundary, bisected on depth:")
lo, hi = 1, 5000
while lo + 1 < hi:
    mid = (lo + hi) // 2
    ok, _ = run_raw(nested_body(OR2, mid))
    lo, hi = (mid, hi) if ok == 2 else (lo, mid)
rows.append(f"  deepest accepted {lo}, shallowest rejected {hi}")
rows.append(f"  same boundary 3 runs: {lo} -> {[run_raw(nested_body(OR2, lo))[0] for _ in range(3)]}, "
            f"{hi} -> {[run_raw(nested_body(OR2, hi))[0] for _ in range(3)]}")

rows.append("  is it depth or payload size? one flat group, N sibling leaf conditions:")
for width in (200, 500, 1000, 5000):
    body = ('{"fields":["code"],"page":{"size":500},"filters":'
            '{"logical_operator":"or","conditions":['
            + ",".join([json.dumps(IS_A)] * (width - 1) + [json.dumps(IS_B)]) + "]}}")
    w, wd = run_raw(body)
    rows.append(f"  or-group, {width:<6} conditions, {len(body):>7} bytes -> {w} {wd}")

rows.append("\n  siblings at depth: one group holding 20 sub-groups")
line("and [ or-leaf x20 ]", {"logical_operator": "and", "conditions": [OR2] * 20}, "expect 2")
line("and [ and-leaf x20 ]", {"logical_operator": "and", "conditions": [AND2] * 20}, "expect 0")
line("or  [ and-leaf x19, or-leaf ]",
     {"logical_operator": "or", "conditions": [AND2] * 19 + [OR2]}, "expect 2")

# --- 3. can api3_array express boolean logic at all? ----------------------------------------------
rows.append("\n=== 3. api3_array and boolean logic")
line("flat [[id is A],[id is B]] (implicit and?)", [IS_A, IS_B], "expect 0", headers=ARR)
line("flat [[id is A]]", [IS_A], "expect 1", headers=ARR)
line("nested list [[[id is A],[id is B]]]", [[IS_A, IS_B]], "?", headers=ARR)
line("array holding a hash group", [OR2], "?", headers=ARR)
line("array: leaf then hash group", [IS_A, OR2], "?", headers=ARR)
line("the hash form sent as api3_array", OR2, "?", headers=ARR)
line("['or', [id is A], [id is B]]", ["or", IS_A, IS_B], "?", headers=ARR)
line("[[id, is, A, 'or']]", [["id", "is", A, "or"]], "?", headers=ARR)
line("the array form sent as api3_hash", [IS_A, IS_B], "expect 400", headers=HSH)
line("default Content-Type, hash body", OR2, "expect 415", headers={})

# --- 4. query params alongside a body filter ------------------------------------------------------
rows.append("\n=== 4. query-string filter[] on a _search that also carries a body filter")
rows.append(f"  project {PROJECT} holds {base_proj} shots; row {A} is in it"
            + (f"; row {other_shot} is in another project" if other_shot else "; no second project"))
line("body [id is A], no params", {"logical_operator": "and", "conditions": [IS_A]}, "expect 1")
line("params filter[id]=B only, body no-filter",
     {"logical_operator": "and", "conditions": []}, "B wins? A wins?",
     params={"filter[id]": B})
line("params filter[id]=B + body [id is A]",
     {"logical_operator": "and", "conditions": [IS_A]}, "0=and 1=one wins",
     params={"filter[id]": B})
line("params filter[id]=A + body [id is A]",
     {"logical_operator": "and", "conditions": [IS_A]}, "expect 1",
     params={"filter[id]": A})
if other_shot:
    line(f"params filter[project.Project.id]={PROJECT} + body [id is other]",
         {"logical_operator": "and", "conditions": [["id", "is", other_shot]]},
         f"0=and {base_proj}=param 1=body", params={"filter[project.Project.id]": PROJECT})
    line("params filter[id]=other + body [project is P0]",
         {"logical_operator": "and",
          "conditions": [["project", "is", {"type": "Project", "id": PROJECT}]]},
         f"0=and {base_proj}=body ignored param", params={"filter[id]": other_shot})
g = c.get("/entity/shots", params={"filter[id]": B, "fields": "code", "page[size]": 500}).json()
rows.append(f"  GET /entity/shots?filter[id]={B} (same param, listing endpoint)  -> "
            f"{len(g['data'])} ids {[x['id'] for x in g['data']]}")
line("params filter[zzz_not_a_field]=1 + body [id is A]",
     {"logical_operator": "and", "conditions": [IS_A]}, "400? 1? 0?",
     params={"filter[zzz_not_a_field]": 1})

# --- 5. the {path, relation, values} object form --------------------------------------------------
rows.append("\n=== 5. the page-storage object form (probe 023) against every filter endpoint")
OBJ = {"path": "id", "relation": "is", "values": [A]}
OBJ_ACTIVE = dict(OBJ, active="true")
STORED = {"logical_operator": "and", "conditions": [OBJ_ACTIVE],
          "filter_name": "<saved filter>", "filter_id": 2}
line("hash, conditions [object]", {"logical_operator": "and", "conditions": [OBJ]}, "expect 400")
line("hash, conditions [object+active] + filter_name/id", STORED, "expect 400")
line("hash, filters = a bare object", OBJ, "?")
line("hash, filters = {path,relation,values} + logical_operator",
     dict(OBJ, logical_operator="and"), "?")
line("array, filters = [object]", [OBJ], "?", headers=ARR)
line("array, filters = object", OBJ, "?", headers=ARR)
rows.append("  _summarize takes the same filters key (probe 020):")
for label, filt, hdr in [("array [[id is A]]", [IS_A], ARR),
                         ("hash and-group of triples",
                          {"logical_operator": "and", "conditions": [IS_A]}, HSH),
                         ("hash or-group of triples", OR2, HSH),
                         ("hash and-group of objects",
                          {"logical_operator": "and", "conditions": [OBJ]}, HSH),
                         ("array [object]", [OBJ], ARR)]:
    r = c.post("/entity/shots/_summarize", headers=hdr,
               json={"filters": filt, "summary_fields": [{"field": "id", "type": "count"}]})
    got = r.json()["data"]["summaries"]["id"] if r.ok else err(r)
    rows.append(f"  _summarize {label:<34} -> {r.status_code} {got}")
rows.append("  extra keys on a triple leaf, which the stored tree also carries:")
line("hash, conditions [[id, is, A, 'true']]",
     {"logical_operator": "and", "conditions": [["id", "is", A, "true"]]}, "expect 1 or 400")
line("hash, group with filter_name/filter_id, triple leaf",
     {"logical_operator": "and", "conditions": [IS_A], "filter_name": "x", "filter_id": 2},
     "expect 1")
line("hash, group with an unknown key",
     {"logical_operator": "and", "conditions": [IS_A], "zzz_not_a_key": 1}, "expect 1")

# --- 6. mixed operators, and leaves beside sub-groups ---------------------------------------------
rows.append("\n=== 6. mixed operators in one group, and leaf + sub-group siblings")
PROJ = ["project", "is", {"type": "Project", "id": PROJECT}]
line("or [id is A, code contains MID, id in [B]]",
     {"logical_operator": "or",
      "conditions": [IS_A, ["code", "contains", MID], ["id", "in", [B]]]}, ">=2")
line("or [id is 9e7, code contains ZZZNOPE, id in [9e7]]",
     {"logical_operator": "or",
      "conditions": [["id", "is", 99999999], ["code", "contains", "ZZZNOPE"],
                     ["id", "in", [99999999]]]}, "expect 0")
line("and [project is P, or-leaf]  (leaf beside a group)",
     {"logical_operator": "and", "conditions": [PROJ, OR2]}, "expect 2")
line("and [project is P, and-leaf] (leaf beside a group)",
     {"logical_operator": "and", "conditions": [PROJ, AND2]}, "expect 0")
line("and [or-leaf, project is <no such project>]",
     {"logical_operator": "and",
      "conditions": [OR2, ["project", "is", {"type": "Project", "id": 99999999}]]}, "expect 0")
line("or [project is <no such>, or-leaf]",
     {"logical_operator": "or",
      "conditions": [["project", "is", {"type": "Project", "id": 99999999}], OR2]}, "expect 2")
line("and [code contains MID, or [id is A, id is 9e7]] scoped",
     {"logical_operator": "and",
      "conditions": [PROJ, ["code", "starts_with", CODE_A[:4]],
                     {"logical_operator": "or",
                      "conditions": [IS_A, ["id", "is", 99999999]]}]}, "expect 1")
line("dotted path inside a nested or",
     {"logical_operator": "and",
      "conditions": [{"logical_operator": "or",
                      "conditions": [["project.Project.id", "is", 99999999],
                                     ["project.Project.id", "is", PROJECT]]}]},
     f"expect {base_proj}")
line("bogus operator inside a nested group",
     {"logical_operator": "and",
      "conditions": [{"logical_operator": "or",
                      "conditions": [["code", "definitely_not_an_operator", "x"]]}]}, "expect 400")
line("bogus field inside a nested group",
     {"logical_operator": "and",
      "conditions": [{"logical_operator": "or",
                      "conditions": [["sg_not_a_field", "is", "x"]]}]}, "expect 400")

actual = "\n".join(rows)
_lib.emit("030_complex_filters", actual, env)
