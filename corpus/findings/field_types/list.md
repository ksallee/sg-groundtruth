---
tags: [field-type, list-field, filter, operator, schema, write, trap]
scope: api
verdict: A list is one bare string in attributes; a write outside valid_values 400s and is case-sensitive, while filters are case-insensitive and only is/is_not/in/not_in exist.
---

# list

**Data type** `list`, probed on `Version.sg_version_type` (stock, editable); `Shot.sg_shot_type` and
`Version.viewed_by_current_user` read for shape.

A `list` is the stripped-down sibling of `status_list` (probe 009).

| schema property | `list` | `status_list` |
|---|---|---|
| `default_value` | present | present |
| `summary_default` | present | present |
| `valid_values` | present | present |
| `display_values` | absent | present |
| `hidden_values` | absent | present |
| `GET /schema/Version/fields/<f>?project_id=<N>` | keys and `valid_values` identical, still no `hidden_values` | `hidden_values: ['pndl', 'pndvs']` |

```
Version.sg_version_type   properties: ['default_value', 'summary_default', 'valid_values']
Shot.sg_shot_type         properties: ['default_value', 'summary_default', 'valid_values']
Version.sg_status_list    properties: ['default_value', 'display_values', 'hidden_values', 'summary_default', 'valid_values']

valid_values  Version.sg_version_type ['Type A', 'Type B', 'Type C']   default_value 'Type A'
              Shot.sg_shot_type       ['VFX', '2D', 'Full CG', 'Trailer', 'Marketing', 'Look Dev']
              Version.viewed_by_current_user ['read', 'unread']        default_value None
```

With no `display_values` the stored value **is** the label; with no `hidden_values` a `list` is site-wide and
`project_id` changes nothing.

**Read** A bare string in `attributes`, never in `relationships`, and, despite the name, single-valued.

```
GET /entity/versions?fields=code,sg_version_type,viewed_by_current_user,sg_status_list
  attributes: {"code": "sh010_comp_v001", "sg_version_type": null,
               "viewed_by_current_user": "unread", "sg_status_list": "fin"}
  relationships keys: []
100 rows, distinct sg_version_type values: {'Type A': 99, None: 1}
python type of every non-null value: str
```

**Write** `PUT /entity/versions/<id>` with a plain string.

| sent | result |
|---|---|
| `'Type A'` | 200, reads back `"Type A"` |
| `'type a'` | 400 `Update failed for [Version.sg_version_type]: 'type a' is not a valid list value. Valid list values: 'Type A', 'Type B', 'Type C'.` |
| `'TYPE A'` | 400, same message |
| `'Type A '` (trailing space) | 400, same message |
| `'apr'` (a `status_list` code) | 400, same message |
| `'zzprobe_list_not_a_valid_value'` | 400, same message |
| `["Type A", "Type B"]` | 400 `API update() Version.sg_version_type expected [String, NilClass] data type(s) but got Array: ["Type A", "Type B"]` |
| `0` (an index) | 400 `... expected [String, NilClass] data type(s) but got Integer: 0` |
| key omitted from the POST | 201, reads back `"Type A"`; `default_value` is applied on create |
| `'zzprobe_list_not_a_valid_value'` on POST | 400 `Invalid field value, update failed [5 - Update failed for [Version.sg_version_type]: 'zzprobe_list_not_a_valid_value' is not a valid list value. Valid list values: 'Type A', 'Type B', 'Type C'.]` + `crud_error_uuid` |

`valid_values` after all eight attempts: `['Type A', 'Type B', 'Type C']`, unchanged. `/schema` is
authoritative for writes: a dropdown built from `valid_values` is complete, and a value outside it is
unreachable over REST.

**Clear**

| sent | reads back | matched by `is None` | matched by `is ''` |
|---|---|---|---|
| `'Type A'` (control) | `"Type A"` | 0 | 0 |
| `null` | `null` | 1 | 1 |
| `""` | `null` | 1 | 1 |

`is ''` is an alias for `is None` and matches only nulls; filter on `None`.

**Filter** Four operators, not eight. The text vocabulary of probe 017 does not apply.

```
[["sg_version_type", "definitely_not_an_operator", null]] -> 400
 title:  "API read() Version.sg_version_type's 'list' data type doesn't support
          'definitely_not_an_operator' 'relation'"
 source: {"Version.sg_version_type": " data type doesn't support 'definitely_not_an_operator' 'relation'.
          Value: {"path" => "sg_version_type", "relation" => "definitely_not_an_operator", "values" => [nil]}
          Valid relations: ["is", "is_not", "in", "not_in"]"}
```

Baseline 100 versions in the project.

| operator | value shape | matches |
|---|---|---|
| `is` | `'Type A'` | 99 |
| `is` | `'type a'` (wrong case) | 99 |
| `is` | `'zzprobe_...'` (not in schema) | 0 |
| `is` | `null` | 1 |
| `is_not` | `'Type A'` | 1 |
| `is_not` | `null` | 99 |
| `in` | `['Type A', 'Type B']` | 99 |
| `in` | `['zzprobe_...']` (not in schema) | 0 |
| `in` | `['Type A', 'zzprobe_...']` | 99; the junk member is dropped, no error |
| `in` | `'Type A'` (bare, not a list) | 99; a scalar is accepted where a list is expected |
| `not_in` | `['Type A']` | 1 |
| `contains`, `not_contains`, `starts_with`, `ends_with` | any | 400, same "doesn't support ... 'relation'" body |

The same bad value fails on write and passes on read:

| value | write | filter |
|---|---|---|
| `'type a'` (wrong case) | 400 | matches 99 |
| `'zzprobe_...'` (not in `valid_values`) | 400 | 0 rows, no error |

**Traps**
- Never round-trip a filter value into an update.
- An invalid operator 400s (probe 017); an invalid value does not, so a dropdown typo reads as "no rows match".
- "list" names the schema, not the value: it holds one string, and an array 400s with `expected [String, NilClass]`.
- `viewed_by_current_user` is flagged `editable: true` and takes a 200, but writing `'read'` reads back
  `'unread'`: computed per API user, not storage (probe 007).
- `default_value` is applied on create when the field is omitted, so a fill-rate count over a `list` measures
  the default, not intent (probe 007).
