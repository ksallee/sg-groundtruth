---
tags: [page, summary, pivot-column, inspector]
endpoints: [POST /entity/<type>/_search]
phase: read
scope: api
measured: site-wide, 3468 query widgets on 1107 listed pages
verdict: Stored pages group one level deep (one of 438 goes two), summarise a column once in 41 grids, and colour columns by DisplayColumn id, a type REST cannot read. mode is list on 94%.
---

# 073_page_grid_settings

**Q** Which grid settings do stored pages use: grouping depth, column summaries, formatting rules, pivot grouping, and which `mode` values?

**Endpoint** `POST /entity/page_settings/_search`

**Docs claim** Silent.

**Actual**

```
3468 query widgets; 524 are a page's own (/body or inside a canvas view), the rest embedded tabs
mode, every widget  {list: 3266, thumb: 158, browser: 39, card: 3, version_card: 1, grouped_notes: 1}
mode, page's own    {list: 436, thumb: 49, browser: 39}
query grouping      absent 2754, a list 438, the boolean false 276; depth {1: 437, 2: 1}
  method {exact: 396, week: 43}; entry keys (column, direction, method)
  the two-level one: [{"column": "entity.Asset.parents", "method": "exact"}, {"column": "entity", "method": "exact"}]
grid (list_content) grouping: absent 3400, an object 40, null 1
sorts: query depth {0: 1032, 1: 476, 2: 18}; grid depth {1: 1444, 0: 10}; both set 383, equal on 290
pivot_grouping [{"column": "entity", "method": "exact"}] 2473, [{"column": "sg_system_task_type", ...}] 82
  pivot columns in grid columns (step_N): 1253 over 28 names
grid summaries: 41 grids hold the key, 1 non-empty; summary_state {visible: 43, hidden: 22}
  {"shots.Shot.step_0$sg_status_list": {"type": "status_percentage", "column": "sg_status_list", "value": "fin"}}
formatting_rules on 301 widgets, 1701 rules; rule_type {display_column: 1680, row: 21}
  display_column rule: {"background_color": "192,192,192", "display_column": {"type": "DisplayColumn", "id": "148"},
                        "page_id": "<another page>", "enabled": true, "bold": false, ...}
  row rule: {"rule_type": "row", "row_entity_type": "<type>", "priority": 1, "background_color": "25,118,27",
             "condition": {"logical_operator": "and", "conditions": [{"path": "<checkbox field>", "relation": "is", "values": [true]}]}}
  a rule's page_id names its own page on 1 of 1701
GET /schema/DisplayColumn -> 404 "Entity type 'DisplayColumn' does not exist."; GET /entity/display_columns -> 404
records_per_page {50: 917, 100: 9, 25: 1}; server_side_filters {null: 115, "my_notes": 1}
```

**Teaches**

What a page runner has to implement, by how often the probed site stores it:

| setting | where | stored shape | reproducible over REST |
|---|---|---|---|
| `mode` | query widget | `list`, `thumb`, `browser`, `card`, ... | yes; `list` is the grid |
| `grouping` | query widget | `false`, or a list of `{column, method, direction}` | yes: `_summarize` nests one level per entry (probe 079). `method` is a `_summarize` grouping type (`exact`, `week`) |
| `sorts` | query widget and `list_content` | lists of `{column, direction}` | the first key via `?sort`; the rest client-side. The two lists disagree on 93 of 383 grids |
| `pivot_grouping`, `pivot_sorts` | query widget | the rows a pivot column (`step_N`) rolls up | the `step_N` column reads as a field (recipe 003) |
| `summaries` | `list_content` | `{<column key>: {type, column, value}}` | `status_list` yes; `status_percentage` with a `value` no (probe 079) |
| `formatting_rules`, `rule_type` `row` | query widget | a `condition` in the web tree shape | yes: convert it like a filter (recipe 003) |
| `formatting_rules`, `rule_type` `display_column` | query widget | `display_column: {type: "DisplayColumn", id}` | no: the rule names no field, and DisplayColumn is not a REST type |
| `records_per_page` | `list_content` | 25, 50, 100 | a client paging choice |

- `grouping: false` means none. Test for a list, not for truthiness of the key.
- A summary key can end in a pivot suffix, `shots.Shot.step_0$sg_status_list`, which names no column in
  the grid's `columns`. The `$` joins a pivot path to the field it summarises.
- A `display_column` rule's `page_id` points at another page on 1700 of 1701 rules: the rules were copied
  from the page they were first made on. Key a rule on the widget holding it, not on `page_id`.
- `server_side_filters: "my_notes"` names a filter the server applies and the tree does not show; on
  the probed site one widget uses it.
