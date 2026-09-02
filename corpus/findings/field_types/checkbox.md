---
tags: [field-type, checkbox, filter, operator, fill-rate, inspector, trap]
scope: api
summary: A boolean.
verdict: A checkbox is two-state, never null - an untouched row already reads false, null is unwritable and unfilterable, and the only relations are is/is_not, so fill rate reads 100% on every checkbox.
---

# checkbox

**Data type** `checkbox`, probed on `Version.flagged` (stock, editable). `Version.client_approved`,
`sg_movie_has_slate`, `sg_frames_have_slate` and `Project.is_template`, `is_demo`, `archived` are the
same type and behave identically.

**Read** A plain JSON boolean under `attributes`: `true` or `false`, never `null`, never a string.
The schema exposes no `default_value` and no `valid_values`.

Every measured route to a null state:

| measured | result |
|---|---|
| 100 newest Versions on the sample project, all four checkboxes | `False` (bool), 100% |
| 20 oldest rows on the site, all four checkboxes | `False` (bool), 100% |
| `Project` site-wide, 22 projects | `is_template` {False, True}, `is_demo` {False, True}, `archived` {False} |
| `POST` create with the key omitted from the body | reads back `false`, matches `flagged is False` immediately |
| `_summarize` grouping on `flagged` | `[('[ ]', 100)]`, a ticked row `[X]`; two groups, no third |
| `is true` + `is false` over the 100-row baseline | 0 + 100 = 100 = baseline, nothing left over |

The 201 response from a create omits the field entirely; read the row back.

**Write** `true`, `false`, `"true"` and `"false"` only. Same on `POST` (create) and `PUT` (update).

| sent | result |
|---|---|
| `true` | 200, reads back `True` |
| `"true"` | 200, reads back `True` |
| `false` | 200, reads back `False` |
| `"false"` | 200, reads back `False` |
| `null` | 400 `API update() Version.flagged expected [String, FalseClass, TrueClass] data type(s) but got NilClass: nil` |
| `1` | 400 `... but got Integer: 1` |
| `0` | 400 `... but got Integer: 0` |
| `"1"` | 400 `Invalid data for 'checkbox' data type. Value: 1` |
| `"0"`, `"yes"`, `""`, `"checked"` | 400 `Invalid data for 'checkbox' data type. Value: <as sent>` |
| `null` on `POST` create | 400 `API create() ... got NilClass: nil` |

**Clear**

| sent | result |
|---|---|
| `false` | 200, value becomes `False` |
| `null` | 400, value stays `True` |
| `""` | 400, value stays `True` |

`false` is the only off state. A client that models unset as `None` and PUTs it gets a 400, and a partial
update built by dropping null-valued keys skips the field instead of clearing it.

**Filter** The relation list, from the API's own rejection of a bogus operator:

```
["flagged", "definitely_not_an_operator", null] -> 400
 title:  "API read() Version.flagged's 'checkbox' data type doesn't support
          'definitely_not_an_operator' 'relation'"
 source: {"Version.flagged": " data type doesn't support 'definitely_not_an_operator' 'relation'.
          Value: {"path" => "flagged", "relation" => "definitely_not_an_operator", "values" => [nil]}
          Valid relations: ["is", "is_not"]"}
```

| operator | value | matches |
|---|---|---|
| `is` | `true` | ticked rows; `"true"` returns the same ids |
| `is` | `false` | unticked rows; `"false"` returns the same ids |
| `is_not` | `true` | unticked rows |
| `is_not` | `false` | ticked rows |

Counts on a 100-Version baseline where every row is false, and on three sandbox rows with one ticked.
The sandbox column compares the ids returned, not the counts: equal counts would not prove equal rows.

| filter | baseline | sandbox, 3 rows |
|---|---|---|
| `is true` | 0 | 1, the ticked id |
| `is false` | 100 | 2, the two untouched ids |
| `is "true"` | 0 | 1, the same id as `is true` |
| `is "false"` | 100 | 2, the same ids as `is false` |
| `is_not true` | 100 | 2, the same ids as `is false` |
| `is_not false` | 0 | 1, the same id as `is true` |

| rejected filter | result |
|---|---|
| `is 1` | 400 `API read() Version.flagged expected [String, FalseClass, TrueClass] ... got Integer: 1` |
| `is "1"` | 400 `Invalid data for 'checkbox' data type. Value: 1` |
| `is null` | 400 `API read() Version.flagged expected [String, FalseClass, TrueClass] data type(s) but got NilClass: nil` |
| `is_not null` | 400 same body from `_search`; `_summarize` gives `API summarize() ...` (probe 020) |
| `in [true, false]` | 400 `Valid relations: ["is", "is_not"]` |

Ask for unticked rows as `["flagged", "is", false]`, not `is_not true`, though both returned the same
ids here; `is_not None` cannot be asked at all.

**Traps**
- **Fill rate is meaningless on this type.** Every checkbox on every row is non-null, so a fill-rate scan
  reports 100% for all four Version checkboxes while every row holds the same value (probe 007). Drop
  `data_type == "checkbox"` from fill ranking before scoring; no threshold separates an informative
  checkbox from a dead one.
- The `is_not None` fill-rate filter that works on every other type 400s here, in both `_search` and
  `_summarize` (probe 020). Special-case the type; do not catch the 400 and score 0.
- `_summarize` returns the UI glyph, not the value, so the empty-group trick that yields an empty count
  on a list field (`[('<value>', 99), ('', 1)]`) never sees `''` here and reports the field fully
  populated.
- Strings coerce on read and write (`"true"` -> `True`), so a checkbox set from a CSV or a form post
  works until someone sends `"1"`. That 400s with a different error shape (`Invalid data for 'checkbox'
  data type`, under `source`) than a bare `1` (`expected [String, FalseClass, TrueClass] ... got
  Integer`). Match on the status, not the title.
