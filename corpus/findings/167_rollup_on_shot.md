---
tags: [summary, query, schema, custom-field, error-handling]
endpoints: [POST /schema/<Type>/fields, PUT /schema/<Type>/fields/<field>, POST /entity/<type>/_summarize, GET /entity/<type>/<id>, POST /entity/<type>/_search]
phase: filter
scope: api
measured: sandbox project written, 2026-11-20; 2 Shots, 3 Bid Lines; four summary creates on Shot and Bid, all refused
verdict: A query (summary) field cannot be created over REST: 400 `data_type is not valid`, with or without a query. Total each Shot's Bid Lines with one `_summarize` grouped on the link.
---

# 167_rollup_on_shot

**Q** Can a Shot hold the total of its linked Bid Lines, as a query field created over the API, and
if not, which call returns the totals?

**Endpoint** `POST /schema/<Type>/fields ; POST /entity/<type>/_summarize ; GET /entity/shots/<id> ; POST /entity/shots/_search`

**Docs claim** `/spec.json`'s `CreateFieldRequest.data_type` enum does not list `summary` (probe 160).
A query field reads back as `data_type` `summary` (`field_types/summary`).

**Actual**

```
POST /schema/Shot/fields and /schema/<Bid>/fields, data_type "summary"
  properties [name]                                            -> 400 code 103
  properties [name, summary_default "sum", query <the tree a summary field reads back with>,
              summary_field <the currency amount>]             -> 400 code 103
  each: "Request Parameters invalid." source {"data_type": ["data_type is not valid"]}
PUT the amount field, summary_default "sum" -> 200, reads back "sum"; put back to "none" -> 200

Bid Lines: two on shot A, 1200.50 and 799.50; one on shot B, 300.25. <link> is the Bid Line's
entity field to Shot; it made the multi_entity sg_bid_lines on Shot (probe 142).
POST /entity/<bid line>/_summarize
  {"filters": [[project, is, <sandbox>], [<link>, in, [shot A, shot B]]],
   "summary_fields": [{"field": <amount>, "type": "sum"}, {"field": "id", "type": "count"}],
   "grouping": [{"field": <link>, "type": "exact", "direction": "asc"}]}
  -> 200 groups [{"group_name": "<shot A code>", "group_value": {"type": "Shot", "id": <A>, ...},
                  "summaries": {<amount>: 2000.0, "id": 2}},
                 {"group_name": "<shot B code>", ..., "summaries": {<amount>: 300.25, "id": 1}}]
     top-level summaries {<amount>: 2300.25}

GET shot A ?fields=sg_bid_lines,sg_bid_lines.<Bid Line>.<amount> -> 2 links; the dotted key absent
_search Shots [sg_bid_lines.<Bid Line>.<amount>, greater_than, 1000.0] -> [shot A]
_summarize Shots, sum of sg_bid_lines.<Bid Line>.<amount> -> 400 code 103
  "Summary field Shot.sg_bid_lines.CustomEntityNN.<amount> does not exist."
```

**Teaches**
- A query field is made in the web interface or not at all. REST reads one (`field_types/summary`) and
  cannot change its `query`: a field `PUT` takes only the seven properties probe 116 lists.
- `summary_default` on the amount field is one of those seven and accepts `"sum"`. It is the field's
  default summary setting, not a value on any row.
- The total per Shot is one `_summarize` on the child type, scoped with `[<link>, in, [Shots]]` and
  grouped on `<link>`: `group_value.id` keys each total to its Shot, and sums are JSON numbers (the
  amount itself reads as a string, `field_types/currency`). One call for N Shots (probe 080).
- Through the reverse field on Shot a dotted read is absent (probe 016) and a `_summarize` of the path
  is 400; only a filter works there.
- Run as a vendor, the same call totals Shots they cannot see, under an empty `group_name` (probe 165).
