---
intent: Resolve a query field's value, and run the rows a saved Page shows
tags: [query, filter, summary, page, schema, operator, dotted-field, trap, recipe]
scope: api
---

# 003_query_fields_and_pages

A query field and a saved Page are the same problem twice. Neither stores a result: both store a
condition tree in the web interface's representation, with tokens standing for the row being read.
Nothing on the REST side accepts that tree. Read it, rewrite it, run it yourself.

## Call

```python
import json
import re
import sys

sys.path.insert(0, "src")                      # or PYTHONPATH=src
from sg_groundtruth.client import FPT          # adds the bearer token and the /api/v1 prefix
from sg_groundtruth.env import load

c = FPT.from_env(load("."))                    # FPT_API_SITE_URL, FPT_API_SCRIPT_NAME, FPT_API_API_KEY
HASH = {"Content-Type": "application/vnd+shotgun.api3_hash+json"}   # nested groups need this one

# A relation whose value is a list. `in_last` names its unit second, so values[0] alone is a 400.
LIST_RELATIONS = {"in", "not_in", "between", "in_last", "not_in_last", "in_next", "not_in_next"}


def convert(node, tokens):
    """The stored condition tree -> the `filters` value of an api3_hash _search."""
    if "conditions" in node:                   # a group holds leaves and sub-groups as siblings
        return {"logical_operator": node.get("logical_operator", "and"),
                "conditions": [convert(child, tokens) for child in node["conditions"]]}
    values = [substitute(v, tokens) for v in (node.get("values") or [])]
    relation = node["relation"]
    # path, relation, values and nothing else: a leaf's `active` key is a 400.
    return [node["path"], relation,
            values if relation in LIST_RELATIONS else (values[0] if values else None)]


def substitute(value, tokens):
    """`valid` names a token. "valid" means a real row, whose name and uuid are labels, not inputs."""
    if not isinstance(value, dict):
        return value
    token = value.get("valid")
    if token in tokens:
        return tokens[token]
    if token and token != "valid":
        raise KeyError(f"no substitution for token {token!r}")
    return {"type": value["type"], "id": value["id"]}


def slug(entity_type):
    """Schema name -> URL slug. A Connection type already holds an underscore, so collapse the pair."""
    s = re.sub(r"(?<!^)(?=[A-Z])", "_", entity_type).lower().replace("__", "_")
    return s + ("es" if s.endswith(("s", "x", "ch", "sh")) else "s")


def search(entity_type, filters, fields, sort=None, size=500):
    out, page = [], 1
    while True:
        body = {"filters": filters, "fields": fields, "page": {"size": size, "number": page}}
        if sort:
            body["sort"] = sort
        r = c.post(f"/entity/{slug(entity_type)}/_search", headers=HASH, json=body)
        if not r.ok:
            raise SystemExit(r.text)           # never truncate an error body
        rows = r.json()["data"]
        out += rows
        if not rows:                           # links.next is emitted forever (probe 006)
            return out
        page += 1


def summarize(entity_type, filters, field, aggregate):
    r = c.post(f"/entity/{slug(entity_type)}/_summarize", headers=HASH,
               json={"filters": filters, "summary_fields": [{"field": field, "type": aggregate}]})
    if not r.ok:
        raise SystemExit(r.text)
    return r.json()["data"]["summaries"][field]


# ---- 1. resolve a query field --------------------------------------------------------------

def resolve_query_field(entity_type, field, row_id, tokens=None):
    """What the field would show, computed from the query the schema stores under it."""
    props = c.get(f"/schema/{entity_type}/fields/{field}").json()["data"]["properties"]
    query, aggregate = props["query"]["value"], props["summary_default"]["value"]
    target, column = query["entity_type"], props["summary_field"]["value"]
    filters = convert(query["filters"],
                      dict(tokens or {}, parent_entity_token={"type": entity_type, "id": row_id}))
    if aggregate != "single_record":
        return summarize(target, filters, column, aggregate)
    # single_record is not a _summarize type: sort the rows and take the first.
    order = props["summary_value"]["value"]
    rows = search(target, filters, [column, order["column"]],
                  sort=("-" if order["direction"] == "desc" else "") + order["column"], size=1)
    return rows[0]["attributes"][column] if rows else None


SHOT_ID = 862                                  # the caller supplies these
ASSET_ID = 1230
print("Shot.open_notes_count      field:",
      c.get(f"/entity/shots/{SHOT_ID}", params={"fields": "open_notes_count"})
      .json()["data"]["attributes"]["open_notes_count"],
      " resolved:", resolve_query_field("Shot", "open_notes_count", SHOT_ID))
print("Asset.sg_latest_version    field:",
      c.get(f"/entity/assets/{ASSET_ID}", params={"fields": "sg_latest_version"})
      .json()["data"]["attributes"]["sg_latest_version"],
      " resolved:", resolve_query_field("Asset", "sg_latest_version", ASSET_ID))


# ---- 2. run a saved page -------------------------------------------------------------------

def page_query(page_id):
    """A Page's shared layout: the entity type, the columns, and filters ready to send."""
    page = c.get(f"/entity/pages/{page_id}",
                 params={"fields": "name,entity_type,project"}).json()["data"]
    project = (page["relationships"]["project"] or {}).get("data")
    settings = search("PageSetting",
                      {"logical_operator": "and",
                       "conditions": [["page", "is", {"type": "Page", "id": page_id}],
                                      ["user", "is", None]]},   # the shared row, not a personal override
                      ["settings_json"])
    body = settings[0]["attributes"]["settings_json"]["children"]["body"]
    sorts = body["settings"].get("sorts") or []
    return {
        "entity_type": body["settings"]["entity_type"],
        "columns": body["children"]["list_content"]["settings"].get("columns") or [],
        "filters": convert(body["settings"]["filters"],
                           {"project_token": {"type": "Project", "id": project["id"]}} if project else {}),
        "sort": (("-" if sorts[0]["direction"] == "desc" else "") + sorts[0]["column"]) if sorts else None,
    }


PAGE_ID = 5099                                 # the caller supplies this
q = page_query(PAGE_ID)
print("\npage", PAGE_ID, q["entity_type"], "sort", q["sort"])
print("filters ", json.dumps(q["filters"]))
print("columns ", q["columns"])
rows = search(q["entity_type"], q["filters"], q["columns"], sort=q["sort"])
print(len(rows), "rows;", summarize(q["entity_type"], q["filters"], "id", "record_count"), "by record_count")
print(json.dumps(rows[0]))
```

## Response

```
Shot.open_notes_count      field: 13    resolved: 13
Asset.sg_latest_version    field: None  resolved: charA_v001

page 5099 Shot sort code
filters  {"logical_operator": "and", "conditions": [
           {"logical_operator": "and", "conditions": [["project", "is", {"type": "Project", "id": 70}]]},
           {"logical_operator": "and", "conditions": [
             {"logical_operator": "and", "conditions": [["sg_status_list", "is", "wtg"]]}]}]}
columns  ['image', 'sg_status_list', 'code', 'sg_sequence', 'description', 'created_by']
183 rows; 183 by record_count
{"type": "Shot",
 "attributes": {"image": null, "sg_status_list": "wtg", "code": "sh010", "description": "..."},
 "relationships": {
   "sg_sequence": {"data": {"id": 23, "name": "seq01", "type": "Sequence"},
                   "links": {"self": "/api/v1/entity/shots/868/relationships/sg_sequence",
                             "related": "/api/v1/entity/sequences/23"}},
   "created_by":  {"data": {"id": 24, "name": "<user>", "type": "HumanUser"}, "links": {...}}},
 "id": 868, "links": {"self": "/api/v1/entity/shots/868"}}
```

That page's stored tree, before translation, and the two controls it is checked against:

```
body.settings.filters as stored
  {"logical_operator": "and", "conditions": [
    {"logical_operator": "and", "top_level_project_filter": true, "conditions": [
      {"path": "project", "relation": "is", "active": true, "top_level_project_filter": true,
       "values": [{"type": "Project", "id": 70, "name": "<project>"}]}]},
    {"logical_operator": "and", "conditions": [
      {"logical_operator": "and", "conditions": [
        {"path": "sg_status_list", "relation": "is", "values": ["wtg"], "active": "true"}]}]}],
   "filter_name": "<saved filter>", "selected": true, "filter_id": 2}

control, written by hand rather than translated
  api3_array [["project", "is", {"type": "Project", "id": 70}], ["sg_status_list", "is", "wtg"]]  -> 183
  _summarize record_count on the translated tree                                                 -> 183
  every Shot in the project                                                                      -> 300
```

## Notes

### The field is not a shortcut

`GET` the field and you get a value with no way to tell whether it was computed. On the probed site
the stock `open_notes_count` agrees with its own query and every custom query field reads `null`
while its query matches rows:

| field | `summary_default` | the field reads | its own query returns |
|---|---|---|---|
| `Shot.open_notes_count`, rows 862, 863, 864 | `record_count` | 13, 12, 12 | 13, 12, 12 |
| `CustomEntity01.sg_test_results`, its three busiest rows | `record_count` | `null` | 1166, 718, 717 |
| `Asset.sg_latest_version` | `single_record` | `null` | 1 Version, whose `code` is `charA_v001` |
| `Project.sg_latest_version`, two projects | `single_record` | `null` | 100 and 53 Versions |

On the probed site a computed `record_count` reads an integer including `0`, so `null` on one of them
means uncomputed rather than empty. `single_record` has no such marker: an uncomputed field and a
query with no rows both read `null`. Resolve rather than read whenever the answer matters
(`field_types/summary`).

### The four flavours

`summary_default` names the aggregate. `single_record` is a sorted `_search` taking row 0; every other
value seen here is also a `_summarize` `type`, so one call covers the rest. The vocabulary is the
endpoint's own, from the 400 a bogus type returns:

```
type must be one of: record_count, count, sum, maximum, minimum, average, earliest, latest,
percentage, status_percentage, status_percentage_as_float, status_list, checked, unchecked
```

| flavour | `summary_default` | resolved by | on the probed site |
|---|---|---|---|
| count | `record_count` | `_summarize` `{"field": summary_field, "type": summary_default}` | 39 fields, all `open_notes_count` but one |
| single-record lookup | `single_record` | `_search`, `sort` built from `summary_value`, row 0's `summary_field` | 3 fields |
| aggregate | `sum`, `average`, `minimum`, `maximum`, `count`, `earliest`, `latest` | the same `_summarize` call | no field declares one |
| percentage | `percentage`, `status_percentage`, `status_percentage_as_float` | the same `_summarize` call | no field declares one |

Two of the four have rows here. For the other two the call shape was exercised without a stored field
to compare against: `_summarize` on `Shot.sg_cut_duration` answered 200 for `sum` (30636), `average`
(102.12), `minimum` (45), `maximum` (160), `count` (300) and `percentage` (0), and 500
`Shotgun Server Error` for `status_percentage` on that number field. Confirm the aggregate against a
real field of that flavour before trusting it.

`single_record` is not in the list above: `_summarize` with `"type": "single_record"` is 400. Sorting
is the only route, and `summary_value` holds the sort: `{"column": "created_at", "direction": "desc",
"detail_link": true}` becomes `?sort=-created_at`. `summary_field` names the column to read off the
row that comes back, which is `code` on all three single-record fields here and `id` on every
`record_count` one.

### The tree runs nowhere as stored

Both refusals, verbatim, from sending `Shot.open_notes_count`'s own `properties.query.filters`:

| sent | result |
|---|---|
| the tree as `filters` under `api3_hash` | 400 `Missing logical operator: {"path" => "note_links", "relation" => "is", "values" => [{"id" => 0, "name" => "Current Entity", "type" => "Entity", "valid" => "parent_entity_token"}]}` |
| its `conditions` as `filters` under `api3_array` | 400 `Invalid filter. Expected array of basic condition arrays but received: [...]` |

Translation is the only path (probe 030). What survives and what does not:

| part of the stored tree | in the request |
|---|---|
| `logical_operator` and `conditions` on a group | kept as they stand |
| a group's `filter_name`, `filter_id`, `selected`, `active`, `top_level_project_filter`, `qb_condition_subgroup` | tolerated, and dropped anyway |
| a leaf's `active` and `top_level_project_filter` | must be dropped: an extra key on a leaf is 400 |
| `{"path": p, "relation": r, "values": v}` | `[p, r, v[0]]`, or `[p, r, v]` for a `LIST_RELATIONS` relation |
| an entity value's `name`, `uuid`, `subtype`, `valid` | dropped; keep `{type, id}` |
| a group whose `conditions` is `[]` | keep or drop under `and`; it is no filter, not a no-match |

An empty group matches every row: `{"logical_operator": "and", "conditions": [{"logical_operator":
"and", "conditions": []}]}` returned 749, against 749 Shots site-wide. Under `and` that is the identity, and
every empty group on the probed site sits under one. Dropping it under an `or` would narrow the query.

### Tokens

A value whose `valid` key is anything other than the string `"valid"` is a placeholder the caller has
to fill in. `id` is `0` and `name` is a label written for the web interface, so neither is usable.

| `valid` | stands for | substitute |
|---|---|---|
| `parent_entity_token` | the row the query field is being read on | `{"type": <the field's own type>, "id": <row id>}` |
| `project_token` | the project the page belongs to | `Page.project`, read from the Page itself |
| `logged_in_user_token` | the person viewing | a script has no viewing user; supply one or refuse the page |

The token's own `type` is not always the type to send: `Shot.open_notes_count` stores
`{"id": 0, "name": "Current Entity", "type": "Entity", "valid": "parent_entity_token"}` and the
substitution that reproduces the number is `{"type": "Shot", "id": 862}`. On the probed site, over the
438 stored page filter trees, `valid` took four values: `"valid"` 345 times, `project_token` 20,
absent 14, `logged_in_user_token` twice.

### Relations whose value is a list

`values` is always an array in storage and almost always one element long. `in_last` and `in_next`
name a unit as a second element, and flattening to `values[0]` loses it:

| sent | result |
|---|---|
| `["created_at", "in_last", [4, "WEEK"]]` | 200 |
| `["created_at", "in_last", 4]` | 400 `API summarize() 'in_last' 'relation' expects a 2-element array: [4]` |

On the probed site the 438 stored trees used three relations: `is` 394 times with one value,
`is_not` 4 times with one, and `in_last` 9 times with two. Any site can store more, so key the
decision on the relation rather than on how many values happen to be present.

### Reading the page

`PageSetting` rows come in two shapes and only one is the page's (probe 023): filter on
`["user", "is", None]` or a personal column order reads as the page's own. The tree path is fixed:
`children.body.settings` holds `entity_type`, `filters`, `sorts` and `grouping`;
`children.body.children.list_content.settings` holds `columns`.

- `columns` are schema field names in display order and go straight into `?fields`. All six on the
  page above were returned. On the probed site another Shot page lists the pivot columns `step_35` and
  `step_106`, which are real fields in `/schema/Shot/fields` and were returned like any other.
- `id` is a legal column and is not a field. On an EventLogEntry page listing it, `?fields=id,user`
  answered 200 with `attributes: {}` and the id under the row's own `id` key. Drop `id` from the list
  and read `row["id"]`.
- A column absent from `/schema/<Type>/fields` is dropped at 200 with no error (probe 004), so check
  the list against the schema to know which columns you lost (probe 023).
- `sorts` and `grouping` are lists of `{column, direction}`. `?sort` takes one field, so the second
  and later sort keys and the grouping have to be applied client-side.

### The stored project can be a project that is gone

The `top_level_project_filter` condition duplicates the page's project scope and is not maintained.
On the probed site 19 pages store a filter naming a project other than their own `Page.project`. All
19 name the same id, and `GET /entity/projects/<that id>` is 404 on every one: the project was deleted
and the stored filter kept its id. Translated verbatim, those pages return 0 rows at 200. Substitute
`Page.project` over whatever the tree names, which is what `page_query` above does through
`project_token`.

On a live row the id decides and a stored `name` is a stale label the server never reads.
`["project", "is", {"type": "Project", "id": 70}]`, the same with
`"name": "zzz_not_the_projects_name"`, and the same again with `valid` and `uuid` attached all
returned 300.

### Once translated, the field is still unusable as a field

Re-running the query is the only way to select on one of these:

| attempt | result |
|---|---|
| `[["open_notes_count", "greater_than", 3]]` | 400 `API read() Shot.open_notes_count's 'summary' data type cannot be used in a filter.` |
| `?sort=open_notes_count`, `?sort=-open_notes_count` | 200, both returning the same order as `?sort=code` |
| `?fields=entity.Shot.open_notes_count` on a Version | 200, `13`, the linked Shot's stored value |

The dotted read returns what the linked row stores, so it inherits the same trap: `null` there means
uncomputed. Resolve the hop first, then resolve the field on the row you land on.

### The URL slug

`_search` needs a URL slug and the schema gives a type name. Underscore before each capital,
lowercase, then pluralise. The `<Type>_<field>_Connection` names already hold an underscore and the
naive rule doubles it, giving 404 `Entity type 'asset_linked_proj...' does not exist.` on 10 of the
114 types here. Collapsing the pair makes all 114 answer 200.
