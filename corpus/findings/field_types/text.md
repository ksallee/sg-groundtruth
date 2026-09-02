---
tags: [field-type, text, filter, operator, write, trap]
scope: api
verdict: A text field has no empty string: writing "" stores null, so `is ""` and `is None` are one filter; matching is case-insensitive, whitespace is stripped, and a non-string 400s.
---

# text

**Data type** `text`. Probed on `Version.sg_department` (stock, editable), with `description`,
`client_code`, `code` and `cached_display_name` as controls. All five report `data_type: text`,
`editable: True`; only `code` is `mandatory`. None is `unique`.

**Read** A plain JSON string under `attributes`, never under `relationships`. Absent means `null`, and
`null` is the only empty state a read can return.

```
keys on the row: ['attributes', 'id', 'links', 'relationships', 'type']
attributes: {"code": "sh010_comp_v001", "sg_department": null,
             "description": "<free text>", "cached_display_name": "sh010_comp_v001"}
python types: [('code','str'), ('sg_department','NoneType'), ('description','str')]
relationships: []
over 100 rows, sg_department is: {'null': 100, 'empty string': 0, 'value': 0}
```

**Write** `POST /entity/versions` on create, `PUT /entity/versions/<id>` to update; both take the field
as a bare string in the body. Only `String` and `NilClass` are accepted.

| sent | status | reads back as |
|---|---|---|
| `'  padded  '` | 200 | `'padded'`; both ends stripped |
| `'   '` (whitespace only) | 200 | `None`; stripped to `''`, then nulled |
| `'line1\nline2'` | 200 | `'line1\nline2'`; newlines survive a one-line field |
| `'héllo ✨ 漢字'` | 200 | `'héllo ✨ 漢字'` |
| `'<b>&amp;</b> "q" \'s\''` | 200 | unchanged; stored verbatim, no escaping |
| `'x' * 5000` | 200 | `len=5000` |
| `'x' * 100000` | 200 | `len=100000`; no length cap found |
| `12345` (int) | 400 | `API update() Version.sg_department expected [String, NilClass] data type(s) but got Integer: 12345` |
| `True` (bool) | 400 | `... but got TrueClass: true` |
| `['a','b']` (list) | 400 | `... but got Array: ["a", "b"]` |
| `{'a': 1}` (dict) | 400 | `... but got Hash: {"a" => 1}` |

**Clear**

| sent | result |
|---|---|
| `null` | 200, reads back `None` |
| `""` | 200, reads back `None`; coerced, not stored |
| key omitted from the PUT | 200, field unchanged |

Four rows differing only in how the field was left:

| body | reads back |
|---|---|
| `{"sg_department": "lighting"}` | `'lighting'` |
| `{"sg_department": ""}` | `None` |
| `{"sg_department": None}` | `None` |
| `{}` | `None` |

The last three are indistinguishable on read; there is no "set but blank" state.

**Filter** `POST /entity/versions/_search`, Content-Type `application/vnd+shotgun.api3_array+json`
(probe 004). A bogus operator 400s and names the whole vocabulary:

```
title:  "API read() Version.sg_department's 'text' data type doesn't support
         'definitely_not_an_operator' 'relation'"
source: {"Version.sg_department": " ... Value: {"path" => "sg_department",
         "relation" => "definitely_not_an_operator", "values" => [nil]}
         Valid relations: ["contains", "not_contains", "is", "is_not",
                           "starts_with", "ends_with", "in", "not_in"]"}
```

`is`, `is_not`, `contains`, `not_contains`, `starts_with` and `ends_with` take a scalar string;
`in` and `not_in` take a list. Which of the four rows above each filter returns:

| operator | value | returns |
|---|---|---|
| `is` | `'lighting'` | `value` |
| `is` | `'LIGHTING'` | `value`; case-blind |
| `is` | `None` | `empty`, `null`, `omitted` |
| `is` | `''` | `empty`, `null`, `omitted`; identical to `is None` |
| `is_not` | `'lighting'` | `empty`, `null`, `omitted`; null rows included |
| `is_not` | `None` or `''` | `value` |
| `contains` | `'ight'` | `value` |
| `contains` | `'IGHT'` | `value`; case-blind |
| `contains` | `''` | `value`; "has any value", not everything |
| `not_contains` | `'ight'` | `empty`, `null`, `omitted` |
| `starts_with` | `'light'` | `value` |
| `ends_with` | `'ing'` | `value` |
| `in` | `['lighting','comp']` | `value` |
| `in` | `'lighting'` | `value`; a bare string is accepted where a list is expected |
| `in` | `['']` | nothing, unlike `is ''` |
| `in` | `[None]` | 400 code 104 `Read failed for entity type [Version]`, `source` null, `detail` null |
| `not_in` | `['lighting']` | `empty`, `null`, `omitted` |
| `is`, `contains`, `starts_with`, `in` | `'ZZZNOPE'` | nothing, every time (baseline is 4) |

**Traps**
- Writing `""` returns 200 and stores `null`. A client round-tripping a form field cannot distinguish
  "user cleared it" from "never set"; encode that distinction in a sentinel string.
- Every operator is case-insensitive, including `is`. There is no case-sensitive text match. Filter
  broadly and re-check the case client-side.
- `is_not` and `not_contains` return the null rows, so `is_not X` is not the complement of `is X`.
  `is ''` matches exactly the rows `contains ''` skips.
- Leading and trailing whitespace is stripped on write, silently, so `'   '` is stored as `null`.
- `cached_display_name` reports `editable: True` and accepts a write at 200, then discards it. It
  mirrors `code`, and re-reads as the new `code` after a rename. Never write it.
- `in [None]` teaches nothing: code 104, `source: null`, `detail: null`. Use `is None`.
