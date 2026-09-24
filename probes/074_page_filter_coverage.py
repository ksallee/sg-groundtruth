"""Q: does recipe 003's convert() translate every filter tree stored on a page, and does the server accept
what it produces?

Every query widget on every listed page's shared tree is converted and run once as a `_summarize`
record_count. Identical (entity type, filters) pairs run once. Tallied by relation, path shape and
token, then 200 against 400 with the error verbatim. Site-wide trees, read only.
"""
import collections
import json
import re

import _lib
import _pages as P

env = _lib.load_env()
c = _lib.client()
SAMPLE = _lib.sample_projects(c, env)[0]
rows = []

# ---- recipe 003's converter, verbatim --------------------------------------------------------
LIST_RELATIONS = {"in", "not_in", "between", "in_last", "not_in_last", "in_next", "not_in_next"}


def convert(node, tokens):
    if "conditions" in node:
        return {"logical_operator": node.get("logical_operator", "and"),
                "conditions": [convert(child, tokens) for child in node["conditions"]]}
    values = [substitute(v, tokens) for v in (node.get("values") or [])]
    relation = node["relation"]
    return [node["path"], relation,
            values if relation in LIST_RELATIONS else (values[0] if values else None)]


def substitute(value, tokens):
    if not isinstance(value, dict):
        return value
    token = value.get("valid")
    if token in tokens:
        return tokens[token]
    if token and token != "valid":
        raise KeyError(f"no substitution for token {token!r}")
    return {"type": value["type"], "id": value["id"]}


def slug(entity_type):
    s = re.sub(r"(?<!^)(?=[A-Z])", "_", entity_type).lower().replace("__", "_")
    return s + ("es" if s.endswith(("s", "x", "ch", "sh")) else "s")


def inactive(node):
    return str(node.get("active", "true")).lower() == "false"


def prune(node):
    """The tree without its unticked leaves, and without any group that pruning left empty."""
    if "conditions" not in node:
        return None if inactive(node) else node
    kept = [p for p in (prune(x) for x in node["conditions"]) if p is not None]
    had = bool(node["conditions"])
    if had and not kept:
        return None
    return dict(node, conditions=kept)


_counts = {}


def count(entity_type, filters):
    key = (entity_type, json.dumps(filters, sort_keys=True))
    if key not in _counts:
        _counts[key] = _count(entity_type, filters)
    return _counts[key]


def _count(entity_type, filters):
    r = c.post(f"/entity/{slug(entity_type)}/_summarize", headers=P.HASH,
               json={"filters": filters, "summary_fields": [{"field": "id", "type": "record_count"}]})
    return r.status_code, (r.json()["data"]["summaries"]["id"] if r.ok else r.json()["errors"][0])


# ---- what to substitute ----------------------------------------------------------------------
me = (env.get("FPT_USER_LOGIN") or "").strip()
me_row = c.get("/entity/human_users", params={"filter[login]": me, "fields": "id"}).json()["data"] if me else []
ME = {"type": "HumanUser", "id": me_row[0]["id"]} if me_row else None
_one = {}


def one_row(entity_type):
    """A live row of the type, so a parent_entity_token run measures a real parent, not id 0."""
    if entity_type not in _one:
        r = c.get(f"/entity/{slug(entity_type)}", params={"fields": "id", "page[size]": 1})
        d = r.json().get("data") if r.ok else None
        _one[entity_type] = {"type": entity_type, "id": d[0]["id"]} if d else None
    return _one[entity_type]


def tokens_for(page, tree):
    proj = P.rel(page, "project") or {"type": "Project", "id": SAMPLE}
    t = {"project_token": {"type": "Project", "id": proj["id"]}}
    for leaf in P.leaves(tree):
        for v in leaf.get("values") or []:
            if isinstance(v, dict) and v.get("valid") == "parent_entity_token":
                # The stored type is a label: "Entity" and the string "None" both appear. The row the
                # query hangs off is of the page's own type.
                typ = v.get("type") if v.get("type") not in (None, "Entity", "None") else page["attributes"]["entity_type"]
                if typ and one_row(typ):
                    t["parent_entity_token"] = one_row(typ)
    if ME:
        t["logged_in_user_token"] = ME
    return t


# ---- schema, for the path shape --------------------------------------------------------------
_schema = {}


def dtype(entity_type, field):
    if entity_type not in _schema:
        r = c.get(f"/schema/{entity_type}/fields")
        _schema[entity_type] = ({k: v["data_type"]["value"] for k, v in r.json()["data"].items()}
                                if r.ok else {})
    return _schema[entity_type].get(field, "absent")


def path_shape(entity_type, path):
    seg = path.split(".")
    hops = (len(seg) - 1) // 2
    last_type, last_field = (seg[-2], seg[-1]) if hops else (entity_type, seg[0])
    first = dtype(entity_type, seg[0])
    shape = {0: "plain", 1: "one hop"}.get(hops, f"{hops} hops")
    if first == "pivot_column":
        shape += ", pivot column"
    if dtype(last_type, last_field) == "summary":
        shape += ", summary field"
    if dtype(last_type, last_field) == "absent":
        shape += ", field absent"
    return shape


# ---- run ------------------------------------------------------------------------------------
pages = P.pages(c)
by_id = {p["id"]: p for p in pages}
trees = P.shared(P.settings(c, by_id))

widgets = []
for pid, t in trees.items():
    for path, w in P.walk(t):
        if w["type"] == P.QUERY:
            widgets.append((pid, path, w["settings"]))
no_tree = [w for w in widgets if not isinstance(w[2].get("filters"), dict)]
with_tree = [w for w in widgets if isinstance(w[2].get("filters"), dict)]
rows.append(f"=== {len(widgets)} query widgets; filters absent or null on {len(no_tree)}, a tree on {len(with_tree)}")

by_rel, by_shape, by_tok = collections.Counter(), collections.Counter(), collections.Counter()
for pid, _, s in with_tree:
    for leaf in P.leaves(s["filters"]):
        by_rel[(leaf["relation"], len(leaf.get("values") or []))] += 1
        by_shape[path_shape(s["entity_type"], leaf["path"])] += 1
        for v in leaf.get("values") or []:
            if isinstance(v, dict):
                by_tok[v.get("valid", "<absent>")] += 1
rows.append(f"  leaves by (relation, number of values): {dict(by_rel.most_common())}")
rows.append(f"  leaves by path shape: {dict(by_shape.most_common())}")
absent = collections.Counter((s["entity_type"], l_["path"]) for _, _, s in with_tree for l_ in P.leaves(s["filters"])
                             if "field absent" in path_shape(s["entity_type"], l_["path"]))
rows.append(f"  field absent, top (type, path): {absent.most_common(6)}")
rows.append(f"  field absent, types whose /schema/<Type>/fields is not 200: "
            f"{sorted({t for t, _ in absent if not _schema.get(t)})}")
rows.append(f"  entity values by `valid`: {dict(by_tok.most_common())}")
cal = sum(1 for r_, _ in by_rel if r_.startswith("in_calendar"))
rows.append(f"  in_calendar_* leaves: {cal}")

rows.append("\n=== recipe 003 convert(), as published")
outcome, errors, examples = collections.Counter(), collections.Counter(), {}
err_types = collections.defaultdict(set)
done = {}
# A page can query a type the site has since disabled; its 400 says nothing about the filter.
enabled = set(c.get("/schema").json()["data"])
off = [s["entity_type"] for _, _, s in with_tree if s["entity_type"] not in enabled]
rows.append(f"  trees on a type absent from GET /schema, not sent: {len(off)} over {sorted(set(off))}")
for pid, path, s in with_tree:
    if s["entity_type"] not in enabled:
        continue
    page = by_id[pid]
    try:
        f = convert(s["filters"], tokens_for(page, s["filters"]))
    except (KeyError, TypeError) as e:
        outcome["convert raised"] += 1
        msg = f"convert raised {type(e).__name__}: {e}"
        errors[msg] += 1
        err_types[msg].add(s["entity_type"])
        bad = next((l_ for l_ in P.leaves(s["filters"]) for v in l_.get("values") or []
                    if isinstance(v, dict) and v.get("valid") not in (None, "valid", *tokens_for(page, s["filters"]))), None)
        examples.setdefault(msg, (s["entity_type"], json.dumps(bad)))
        continue
    key = (s["entity_type"], json.dumps(f, sort_keys=True))
    done[key] = status, body = count(s["entity_type"], f)
    outcome[status] += 1
    if status != 200:
        msg = f"{status} {body.get('title')} source {json.dumps(body.get('source'))} detail {json.dumps(body.get('detail'))}"
        errors[msg] += 1
        err_types[msg].add(s["entity_type"])
        examples.setdefault(msg, (s["entity_type"], json.dumps(f)[:300]))
rows.append(f"  widgets by outcome: {dict(outcome)}; distinct (type, filters) sent: {len(done)}")
for e, n in errors.most_common(8):
    rows.append(f"    {n:>4}x {e[:300]}")
    rows.append(f"          on types {sorted(err_types[e])[:6]}; e.g. {examples[e][0]} {examples[e][1][:200]}")

rows.append("\n=== unticked leaves: `active` false")
act = collections.Counter(repr(l_.get("active", "<absent>")) for _, _, s in with_tree for l_ in P.leaves(s["filters"]))
rows.append(f"  leaf `active` values: {dict(act)}")
diff = collections.Counter()
shown = 0
for pid, path, s in with_tree:
    if s["entity_type"] not in enabled or not any(inactive(l_) for l_ in P.leaves(s["filters"])):
        continue
    page = by_id[pid]
    try:
        tok = tokens_for(page, s["filters"])
        kept = convert(s["filters"], tok)
        pr = prune(s["filters"]) or {"logical_operator": "and", "conditions": []}
        dropped = convert(pr, tok)
    except KeyError:
        diff["convert raised"] += 1
        continue
    a, b = count(s["entity_type"], kept), count(s["entity_type"], dropped)
    same = a == b
    diff["same count" if same else "count differs"] += 1
    if not same and shown < 3:
        shown += 1
        un = [l_ for l_ in P.leaves(s["filters"]) if inactive(l_)]
        rows.append(f"  {s['entity_type']:<10} kept {a}  dropped {b}  unticked {json.dumps(un)[:220]}")
rows.append(f"  trees holding an unticked leaf, counted with it and without it: {dict(diff)}")

rows.append("\n=== the tokens convert() cannot fill")
auto = collections.Counter()
for pid, path, s in with_tree:
    for l_ in P.leaves(s["filters"]):
        for v in l_.get("values") or []:
            if isinstance(v, dict) and v.get("valid") == "autocomplete":
                auto[(s["entity_type"], l_["path"], json.dumps(v))] += 1
for (t, p_, v), n in auto.items():
    rows.append(f"  {n}x autocomplete on {t}.{p_}: {v}")
ptypes = collections.Counter(v.get("type") for _, _, s in with_tree for l_ in P.leaves(s["filters"])
                             for v in l_.get("values") or [] if isinstance(v, dict) and v.get("valid") == "parent_entity_token")
rows.append(f"  parent_entity_token stored `type`: {dict(ptypes)}")
empty_root = count("Shot", {"logical_operator": "and", "conditions": []})
rows.append(f"  an empty root group, Shot: {empty_root}")
_lib.note_from([p["attributes"] for p in pages])

_lib.emit("074_page_filter_coverage", "\n".join(rows), env)
