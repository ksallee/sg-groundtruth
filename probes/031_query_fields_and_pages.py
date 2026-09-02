"""Q: how does a client resolve a query field's value, and run a saved Page's filters?

Two halves of one problem. A query field stores a query rather than a value, so a normal read answers
null or a stale number and never an error. A saved Page stores its filters in the web interface's
representation. Both are a tree of {path, relation, values} with tokens standing for the current row,
and both have to be rewritten as _search conditions before anything can run them.

Read-only throughout: everything here is a query.
"""
import collections
import json
import re
import sys

import _lib

env = _lib.load_env()
c = _lib.client()
PROJECT = _lib.sample_projects(c, env)[0]
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
HASH = {"Content-Type": "application/vnd+shotgun.api3_hash+json"}
rows = []

# ---------------------------------------------------------------- the translator

# A relation whose value is a list rather than a scalar. `in_last` names the unit as a second element,
# so v[0] alone is 400 "expects a 2-element array".
LIST_RELATIONS = {"in", "not_in", "between", "in_last", "not_in_last", "in_next", "not_in_next"}


def convert(node, tokens):
    """The web condition tree -> the api3_hash `filters` value. Groups survive, leaves become triples."""
    if "conditions" in node:
        return {"logical_operator": node.get("logical_operator", "and"),
                "conditions": [convert(ch, tokens) for ch in node["conditions"]]}
    values = [resolve(v, tokens) for v in (node.get("values") or [])]
    relation = node["relation"]
    # Everything but path/relation/values is dropped: a leaf's extra key is 400 (probe 030).
    return [node["path"], relation,
            values if relation in LIST_RELATIONS else (values[0] if values else None)]


def resolve(value, tokens):
    """An entity value is a hash with a `valid` key. "valid" means a real row; anything else is a token."""
    if not isinstance(value, dict):
        return value
    token = value.get("valid")
    if token in tokens:
        return tokens[token]
    if token and token != "valid":
        raise KeyError(token)
    return {"type": value["type"], "id": value["id"]}          # name/uuid/subtype are labels, dropped


def slug(entity_type):
    """Schema name -> URL slug. The Connection types already hold an underscore, so collapse the pair."""
    s = re.sub(r"(?<!^)(?=[A-Z])", "_", entity_type).lower().replace("__", "_")
    return s + ("es" if s.endswith(("s", "x", "ch", "sh")) else "s")


def search(entity_type, filters, fields, size=500, sort=None):
    out, n = [], 1
    while True:
        body = {"filters": filters, "fields": fields, "page": {"size": size, "number": n}}
        if sort:
            body["sort"] = sort
        r = c.post(f"/entity/{slug(entity_type)}/_search", headers=HASH, json=body)
        if not r.ok:
            return f"ERR {r.status_code} {r.text}"
        d = r.json()["data"]
        out += d
        if not d or sort:
            return out
        n += 1


def count(entity_type, filters, headers=HASH):
    r = c.post(f"/entity/{slug(entity_type)}/_summarize", headers=headers,
               json={"filters": filters, "summary_fields": [{"field": "id", "type": "record_count"}]})
    return r.json()["data"]["summaries"]["id"] if r.ok else f"ERR {r.status_code} {r.text}"


def rel(row, name):
    return (row["relationships"].get(name) or {}).get("data")


def flat(entity_type, filters, fields, size=500):
    """The api3_array form, for the independent controls."""
    out, n = [], 1
    while True:
        r = c.post(f"/entity/{slug(entity_type)}/_search", headers=ARR,
                   json={"filters": filters, "fields": fields, "page": {"size": size, "number": n}})
        if not r.ok:
            return f"ERR {r.status_code} {r.text}"
        d = r.json()["data"]
        out += d
        if not d:
            return out
        n += 1


# ---------------------------------------------------------------- the census of query fields

rows.append("=== every summary field on the site, and its aggregate")
types = c.get("/schema").json()["data"]
fields = {}
for t in types:
    r = c.get(f"/schema/{t}/fields")
    if not r.ok:
        continue
    for name, spec in r.json()["data"].items():
        if spec["data_type"]["value"] == "summary":
            fields[f"{t}.{name}"] = spec
by_flavour = collections.Counter(s["properties"]["summary_default"]["value"] for s in fields.values())
rows.append(f"  {len(types)} types scanned, {len(fields)} summary fields")
rows.append(f"  summary_default: {json.dumps(by_flavour)}")
for k, spec in sorted(fields.items()):
    p = spec["properties"]
    if k.endswith(".open_notes_count") and k != "Shot.open_notes_count":
        continue
    rows.append(f"    {k:<34} {p['summary_default']['value']:<14} summary_field={p['summary_field']['value']!r} "
                f"summary_value={json.dumps(p['summary_value']['value'])} "
                f"query.entity_type={p['query']['value']['entity_type']!r}")
rows.append(f"    (+{sum(1 for k in fields if k.endswith('.open_notes_count')) - 1} more open_notes_count, "
            f"one per entity type, identical)")

rows.append("\n=== the aggregate vocabulary, from the endpoint that computes it")
r = c.post(f"/entity/{slug('Shot')}/_summarize", headers=ARR,
           json={"filters": [], "summary_fields": [{"field": "id", "type": "definitely_not_an_aggregate"}]})
rows.append(f"  _summarize type definitely_not_an_aggregate -> {r.status_code} "
            f"{json.dumps(r.json()['errors'][0]['source'])}")
r = c.post(f"/entity/{slug('Shot')}/_summarize", headers=ARR,
           json={"filters": [], "summary_fields": [{"field": "id", "type": "single_record"}]})
rows.append(f"  _summarize type single_record               -> {r.status_code}, absent from that list")
rows.append("  the same call shape under the aggregates no field on this site declares:")
for agg in ("sum", "average", "minimum", "maximum", "count", "percentage", "status_percentage"):
    r = c.post(f"/entity/{slug('Shot')}/_summarize", headers=ARR,
               json={"filters": [["project", "is", {"type": "Project", "id": PROJECT}]],
                     "summary_fields": [{"field": "sg_cut_duration", "type": agg}]})
    rows.append(f"    Shot.sg_cut_duration {agg:<18} -> {r.status_code} "
                f"{json.dumps(r.json()['data']['summaries'] if r.ok else r.json()['errors'][0]['title'])}")

# ---------------------------------------------------------------- record_count, end to end

rows.append("\n=== record_count resolved end to end: Shot.open_notes_count")
q = fields["Shot.open_notes_count"]["properties"]["query"]["value"]
rows.append("  properties.query.filters as stored:")
rows.append("  " + json.dumps(q["filters"], indent=1)[:700].replace("\n", "\n  "))
shots = flat("Shot", [["project", "is", {"type": "Project", "id": PROJECT}]],
             ["code", "open_notes_count"], 200)
_lib.note_from(shots[:5])
sample = [s for s in shots if (s["attributes"].get("open_notes_count") or 0) > 0][:3]
for s in sample:
    filters = convert(q["filters"], {"parent_entity_token": {"type": "Shot", "id": s["id"]}})
    n = count(q["entity_type"], filters)
    rows.append(f"  shot {s['id']}: field reads {s['attributes']['open_notes_count']}, "
                f"its own query counts {n}, equal={s['attributes']['open_notes_count'] == n}")
rows.append("  the filters actually sent, for the last of them:")
rows.append("  " + json.dumps(convert(q["filters"], {"parent_entity_token": {"type": "Shot", "id": sample[-1]['id']}})))

rows.append("\n=== the same tree sent without translating it")
r = c.post(f"/entity/{slug('Note')}/_search", headers=HASH,
           json={"filters": q["filters"], "fields": ["id"]})
rows.append(f"  api3_hash, verbatim -> {r.status_code} {json.dumps(r.json()['errors'][0]['title'])}")
r = c.post(f"/entity/{slug('Note')}/_search", headers=ARR,
           json={"filters": q["filters"]["conditions"], "fields": ["id"]})
rows.append(f"  api3_array, conditions -> {r.status_code} {json.dumps(r.json()['errors'][0]['title'])[:200]}")

# ---------------------------------------------------------------- the field that disagrees

rows.append("\n=== a record_count field whose value disagrees with its own query")
custom = [k for k, s in fields.items()
          if s["properties"]["summary_default"]["value"] == "record_count" and not k.endswith(".open_notes_count")]
for key in custom:
    owner, fname = key.split(".")
    q2 = fields[key]["properties"]["query"]["value"]
    child_link = q2["filters"]["conditions"][0]["conditions"][0]["path"]
    kids = flat(q2["entity_type"], [], [child_link], 500)
    busiest = collections.Counter(
        (rel(k, child_link) or {}).get("id") for k in kids if rel(k, child_link)).most_common(3)
    rows.append(f"  {key}: query over {q2['entity_type']} on path {child_link!r}, "
                f"{len(kids)} rows of {q2['entity_type']} on the site")
    for owner_id, _ in busiest:
        row = c.get(f"/entity/{slug(owner)}/{owner_id}", params={"fields": fname}).json()["data"]
        n = count(q2["entity_type"], convert(q2["filters"], {"parent_entity_token": {"type": owner, "id": owner_id}}))
        rows.append(f"    {owner} {owner_id}: field reads {row['attributes'][fname]!r}, its own query counts {n}")

# ---------------------------------------------------------------- single_record

rows.append("\n=== single_record resolved end to end")
single = [k for k, s in fields.items() if s["properties"]["summary_default"]["value"] == "single_record"]
rows.append(f"  single_record fields: {single}")
key = "Asset.sg_latest_version" if "Asset.sg_latest_version" in single else single[0]
owner, fname = key.split(".")
props = fields[key]["properties"]
q3, sv, sf = props["query"]["value"], props["summary_value"]["value"], props["summary_field"]["value"]
sort = ("-" if sv["direction"] == "desc" else "") + sv["column"]
owners = flat(owner, [["project", "is", {"type": "Project", "id": PROJECT}]], ["code", fname], 200)
_lib.note_from(owners[:5])
picked = 0
for o in owners:
    filters = convert(q3["filters"], {"parent_entity_token": {"type": owner, "id": o["id"]}})
    n = count(q3["entity_type"], filters)
    if not n:
        continue
    top = search(q3["entity_type"], filters, [sf, sv["column"]], 1, sort=sort)
    rows.append(f"  {owner} {o['id']}: field reads {o['attributes'][fname]!r}, "
                f"query matches {n} {q3['entity_type']}, sort {sort!r} row 0 "
                f"{sf}={json.dumps(top[0]['attributes'][sf])} {sv['column']}={json.dumps(top[0]['attributes'][sv['column']])}")
    _lib.note_from(top[0])
    picked += 1
    if picked == 3:
        break
if "Project.sg_latest_version" in single:
    props = fields["Project.sg_latest_version"]["properties"]
    q4, sv4, sf4 = props["query"]["value"], props["summary_value"]["value"], props["summary_field"]["value"]
    sort4 = ("-" if sv4["direction"] == "desc" else "") + sv4["column"]
    for pid in _lib.sample_projects(c, env):
        row = c.get(f"/entity/projects/{pid}", params={"fields": "sg_latest_version"}).json()["data"]
        filters = convert(q4["filters"], {"parent_entity_token": {"type": "Project", "id": pid}})
        top = search(q4["entity_type"], filters, [sf4, sv4["column"]], 1, sort=sort4)
        _lib.note_from(top[0])
        rows.append(f"  Project {pid}: field reads {row['attributes']['sg_latest_version']!r}, "
                    f"query matches {count(q4['entity_type'], filters)} {q4['entity_type']}, sort {sort4!r} row 0 "
                    f"{sf4}={json.dumps(top[0]['attributes'][sf4])} "
                    f"{sv4['column']}={json.dumps(top[0]['attributes'][sv4['column']])}")

# ---------------------------------------------------------------- what a stored tree contains

rows.append("\n=== every stored page filter tree on the site: which shapes a translator must handle")
pages = flat("Page", [], ["name", "page_type", "entity_type", "project"])
ids = [p["id"] for p in pages]
settings = []
for i in range(0, len(ids), 300):
    settings += flat("PageSetting", [["page", "in", [{"type": "Page", "id": x} for x in ids[i:i + 300]]]],
                     ["page", "user", "settings_json"])
shared = {}
for s in settings:
    p = rel(s, "page")
    if p and rel(s, "user") is None and isinstance(s["attributes"]["settings_json"], dict):
        shared[p["id"]] = s["attributes"]["settings_json"]

relations, tokens_seen, group_keys, leaf_keys, nvalues = (collections.Counter() for _ in range(5))


def walk(node):
    if "conditions" in node:
        group_keys.update(k for k in node if k != "conditions")
        for ch in node["conditions"]:
            walk(ch)
        return
    leaf_keys.update(node.keys())
    relations[node.get("relation")] += 1
    vs = node.get("values")
    nvalues[(node.get("relation"), len(vs) if isinstance(vs, list) else -1)] += 1
    for v in (vs if isinstance(vs, list) else [vs]):
        if isinstance(v, dict):
            tokens_seen[v.get("valid")] += 1


trees = 0
for tree in shared.values():
    f = ((tree.get("children") or {}).get("body") or {}).get("settings", {}).get("filters")
    if isinstance(f, dict):
        trees += 1
        walk(f)
rows.append(f"  {len(pages)} pages, {len(shared)} with a shared PageSetting, {trees} holding a filter tree")
rows.append(f"  relations used:   {json.dumps(relations.most_common())}")
rows.append(f"  values per leaf:  {json.dumps([[str(k), v] for k, v in nvalues.most_common()])}")
rows.append(f"  `valid` on an entity value: {json.dumps(tokens_seen.most_common())}")
rows.append(f"  keys on a group:  {json.dumps(group_keys)}")
rows.append(f"  keys on a leaf:   {json.dumps(leaf_keys)}")

# ---------------------------------------------------------------- run a saved page

rows.append("\n=== run a saved page: read it, translate it, query it")
best = None
for p in pages:
    if rel(p, "project") is None or rel(p, "project")["id"] != PROJECT:
        continue
    tree = shared.get(p["id"])
    if not tree:
        continue
    body = (tree.get("children") or {}).get("body") or {}
    bs = body.get("settings") or {}
    cols = ((body.get("children") or {}).get("list_content") or {}).get("settings", {}).get("columns")
    f = bs.get("filters")
    # the one worth showing: a saved filter, so the tree holds more than the project scope
    if isinstance(f, dict) and cols and bs.get("entity_type") and f.get("filter_name"):
        best = (p, bs, cols)
        break
page, bs, cols = best
_lib.note_from(page)
_lib.note_names(bs["filters"].get("filter_name") or "")
et = bs["entity_type"]
rows.append(f"  page {page['id']}, page_type {page['attributes']['page_type']!r}, entity_type {et!r}")
rows.append(f"  body.settings.sorts    {json.dumps(bs.get('sorts'))}")
rows.append(f"  body.settings.grouping {json.dumps(bs.get('grouping'))}")
rows.append(f"  list_content.settings.columns {json.dumps(cols)}")
rows.append("  body.settings.filters as stored:")
rows.append("  " + json.dumps(bs["filters"], indent=1).replace("\n", "\n  "))
filters = convert(bs["filters"], {"project_token": {"type": "Project", "id": rel(page, "project")["id"]}})
rows.append("  translated:")
rows.append("  " + json.dumps(filters))
got = search(et, filters, cols)
rows.append(f"  POST /entity/{slug(et)}/_search with the page's own columns as fields -> {len(got)} rows")
_lib.note_from(got[:2])
rows.append("  first row:")
rows.append("  " + json.dumps(got[0], indent=1)[:900].replace("\n", "\n  "))

rows.append("\n  the independent control, written by hand rather than translated:")
leaf = bs["filters"]["conditions"][1]["conditions"][0]["conditions"][0]
control = [["project", "is", {"type": "Project", "id": rel(page, "project")["id"]}],
           [leaf["path"], leaf["relation"], leaf["values"][0]]]
rows.append(f"    api3_array {json.dumps(control)} -> {len(flat(et, control, ['id']))} rows")
rows.append(f"    _summarize record_count on the translated tree -> {count(et, filters)}")
rows.append(f"    every {et} in the project -> "
            f"{count(et, [['project', 'is', {'type': 'Project', 'id': rel(page, 'project')['id']}]], ARR)}")

rows.append("\n  the page's columns against /schema, and what ?fields returned")
schema = set(c.get(f"/schema/{et}/fields").json()["data"])
returned = set(got[0]["attributes"]) | set(got[0]["relationships"])
rows.append(f"    columns absent from /schema/{et}/fields: {[x for x in cols if x.split('.')[0] not in schema]}")
rows.append(f"    columns not returned by ?fields:         {[x for x in cols if x not in returned]}")
tl = [(p, shared[p['id']]) for p in pages
      if rel(p, "project") and rel(p, "project")["id"] == PROJECT and p["id"] in shared]
for p, tree in tl:
    cc = (((tree.get("children") or {}).get("body") or {}).get("children") or {}).get(
        "list_content", {}).get("settings", {}).get("columns") or []
    if "id" in cc:
        et2 = tree["children"]["body"]["settings"]["entity_type"]
        r = c.post(f"/entity/{slug(et2)}/_search", headers=ARR,
                   json={"filters": [], "fields": ["id", cc[1]], "page": {"size": 1}})
        rows.append(f"    a page column named 'id' on {et2}: ?fields=id,{cc[1]} -> {r.status_code} "
                    f"{json.dumps(r.json()['data'][0])[:200]}")
        break

# ---------------------------------------------------------------- what the translator must not skip

rows.append("\n=== the rewrites that are not optional")
proj = {"type": "Project", "id": PROJECT}
rows.append(f"  control, every Shot in the project: {count('Shot', [['project', 'is', proj]], ARR)}")
stored_leaf = {"path": "project", "relation": "is", "values": [proj], "active": "true"}
r = c.post(f"/entity/{slug('Shot')}/_search", headers=HASH,
           json={"filters": {"logical_operator": "and", "conditions": [stored_leaf]}, "fields": ["id"]})
rows.append(f"  a {{path, relation, values}} leaf inside a group -> {r.status_code} "
            f"{json.dumps(r.json()['errors'][0]['title'])}")
for label, value in (("{type, id}", proj),
                     ("+ a stale name", dict(proj, name="zzz_not_the_projects_name")),
                     ("+ name, valid, uuid", dict(proj, name="zzz", valid="valid",
                                                  uuid="00000000-0000-0000-0000-000000000000"))):
    rows.append(f"  entity value {label:<21} -> {count('Shot', [['project', 'is', value]], ARR)}")
rows.append(f"  a nested empty group, and[ and[ ] ] -> "
            f"{count('Shot', {'logical_operator': 'and', 'conditions': [{'logical_operator': 'and', 'conditions': []}]})}"
            f", against {count('Shot', [], ARR)} Shots site-wide: an empty group is no filter, not a no-match")
r = c.post(f"/entity/{slug('Version')}/_summarize", headers=ARR,
           json={"filters": [["created_at", "in_last", 4]],
                 "summary_fields": [{"field": "id", "type": "record_count"}]})
rows.append(f"  in_last with values[0] alone -> {r.status_code} {json.dumps(r.json()['errors'][0]['title'])}")
rows.append(f"  in_last with the whole values list -> "
            f"{count('Version', [['created_at', 'in_last', [4, 'WEEK']]], ARR)} Versions site-wide")

rows.append("\n=== a stored entity value can name a row that is gone")


def project_ids(node, out):
    if "conditions" in node:
        for ch in node["conditions"]:
            project_ids(ch, out)
        return
    for v in (node.get("values") or []):
        if isinstance(v, dict) and v.get("type") == "Project" and v.get("valid") != "project_token":
            out.add(v["id"])
    return out


stale = []
for p in pages:
    tree = shared.get(p["id"])
    own = rel(p, "project")
    if not tree or not own:
        continue
    f = ((tree.get("children") or {}).get("body") or {}).get("settings", {}).get("filters")
    if not isinstance(f, dict):
        continue
    named = set()
    project_ids(f, named)
    for n in named - {own["id"]}:
        stale.append((p["id"], own["id"], n, c.get(f"/entity/projects/{n}", params={"fields": "id"}).status_code))
rows.append(f"  pages whose stored filter names a project other than the page's own: {len(stale)}, "
            f"over {len(set(x[2] for x in stale))} named ids; "
            f"GET on those ids: {json.dumps(collections.Counter(x[3] for x in stale))}")
for pid, own_id, other, status in stale[:4]:
    rows.append(f"    page {pid}: Page.project is {own_id}, the stored filter names project {other}, "
                f"GET /entity/projects/{other} -> {status}")

rows.append("\n=== the query field itself, once more, as a field")
r = c.post(f"/entity/{slug('Shot')}/_search", headers=ARR,
           json={"filters": [["open_notes_count", "greater_than", 3]], "fields": ["id"]})
rows.append(f"  filter [['open_notes_count', 'greater_than', 3]] -> {r.status_code} "
            f"{json.dumps(r.json()['errors'][0]['title'])}")
for s in ("open_notes_count", "-open_notes_count", "code"):
    got2 = c.post(f"/entity/{slug('Shot')}/_search", headers=ARR,
                  json={"filters": [["project", "is", proj]], "fields": ["code", "open_notes_count"],
                        "sort": s, "page": {"size": 3}}).json()["data"]
    rows.append(f"  sort={s:<18} {[x['attributes']['open_notes_count'] for x in got2]}")
v = flat("Version", [["project", "is", proj], ["entity", "type_is", "Shot"]],
         ["code", "entity.Shot.open_notes_count"], 2)
rows.append(f"  dotted read entity.Shot.open_notes_count -> {json.dumps(v[0]['attributes'])}")
_lib.note_from(v[0])

_lib.emit("031_query_fields_and_pages", "\n".join(rows), env)
