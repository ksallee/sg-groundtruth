---
tags: [query, paging, cost, link, silent]
endpoints: [POST /entity/_text_search]
phase: filter
scope: api
measured: sandbox project written, 12 rows this probe made, and the project's own Versions for the cap
coverage: partial
unmeasured: Only `description` and a linked row's name were tried as fields beyond the name, and the tie-break between equal-length names was not reached. The probe's limit, not the site's.
verdict: `page.size` caps at 25 and defaults to 25 with no `links`, so page with `page.number`. Every word must match a case-insensitive substring of the name or of the linked row's name.
---

# 053_text_search_matching

**Q** How many rows does `_text_search` hand back, and what is a word matched against?

**Endpoint** `POST /entity/_text_search`

**Docs claim** The site's own `/spec.json` gives this body the shared `PaginationParameter`, whose
`size` is documented `default: 500`, and a `sort` string. Its example sends `"sort": "-id"` and
`{"number": 1, "size": 20}`.

**Actual**

```
page, text "v" over one project's Versions
  {"size": 24} -> 200, 24 rows   {"size": 25} -> 200, 25 rows   {"size": "25"} -> 200, 25 rows
  {"size": 26}, {"size": 100} -> 400 code 103 {"page": {"size": ["size must be less than 25"]}}
  {"size": 0}, {"size": -1}   -> 400 code 103 {"page": {"size": ["size must be greater than 0"]}}
  {"number": 0}               -> 400 code 103 {"page": {"number": ["number must be greater than 0"]}}
  absent, {}, {"number": 2}   -> 200, 25 rows, and "links": null on every one of them
  number 1, 2, 3 -> 25 rows each, ids disjoint
  sort "-id", "id", "code", "-not_a_field" -> 200, the same five ids in the same order as no sort

rows made: zzprobe_053_qat_0020, _qat_sh010, _kif_hello, _kif_only (Shot), _qat_charA,
  _kif_skyline, _kif_asset (Asset), _qat_v001, _zzz_v001 (Version, entity -> _qat_0020)
  _kif_only.description = "wubblefish glorp, a word this row's code does not hold"

  'qat' 'QAT' 'Qat' 'qAt'          -> the three _qat_ rows, the same three every time
  '020' 'h01' 'at' '_qat_' '053_qat' -> matched inside the name; '_' is not a separator
  'q' -> the three _qat_ rows      'k' -> the three _kif_ rows
  'qat 0020' '0020 qat' -> _qat_0020 alone   'qat kif' 'qat nomatch' -> 0 rows
  'wubblefish' 'wubble' 'glorp' -> 0 rows, over Shot.description and over Asset.description
  'qat' over Versions -> _qat_v001 and _zzz_v001, whose own code holds no "qat":
    {"name": "zzprobe_053_zzz_v001", "links": ["Shot", "zzprobe_053_qat_0020"], "status": "rev"}

order, one text over Shot, Asset and Version, the three keys given in three different orders
  _kif_only(20) _qat_0020(20) _qat_v001(21) _zzz_v001(21) _kif_asset(21) _kif_hello(21)
  _qat_charA(21) _qat_sh010(21) _kif_skyline(23)      identical for all three key orders
  not id ascending, not grouped by type, name length ascending
  three Shots created longest name first -> returned 15, then 24, then 40 characters

14 types scoped to one project, four fresh random words
  one _text_search 331-369 ms        14 x contains _search in sequence 3811-3859 ms
```

**Teaches**

| sent as `page` | answered |
|---|---|
| absent, `{}`, `{"number": 2}` | 200, 25 rows |
| `{"size": 25}`, `{"size": "25"}` | 200, 25 rows |
| `{"size": 26}` and up | 400 code 103, `{"page": {"size": ["size must be less than 25"]}}` |
| `{"size": 0}` and below | 400 code 103, `{"page": {"size": ["size must be greater than 0"]}}` |
| `{"number": 0}` | 400 code 103, `{"page": {"number": ["number must be greater than 0"]}}` |

- 25 is the cap and the default, and the message is off by one: `size must be less than 25` is what
  `{"size": 26}` answers, while `{"size": 25}` answers 200 with 25 rows. `page.size` is the only
  reason a caller sends `page` at all here, and neither bound is the 500 the spec documents.
- The response has no `links` key, so nothing in it says whether there is more. Page with
  `page.number`, which starts at 1 and answers disjoint ids, and stop when `data` is empty. This is
  the opposite of the paginated reads, where `links.next` is emitted forever (probe 006).
- `sort` is accepted and ignored. Four values, one of them a field that does not exist, all answered
  200 with the rows in the order no `sort` gives.

| text | matched |
|---|---|
| `qat`, `QAT`, `Qat`, `qAt` | the same rows: case is ignored |
| `020`, `h01`, `at` | anywhere inside the name, not a prefix |
| `_qat_`, `053_qat`, `qat_0020` | underscore is part of the string, not a word separator |
| `qat 0020`, `0020 qat` | the rows holding both, whichever order they are sent in |
| `qat kif`, `qat nomatch` | nothing: every word has to match |
| `q` | every row whose name holds a `q` |
| a word only in `description` | nothing |
| `qat` on a Version whose `entity` is a Shot named `..._qat_0020` | that Version |

- Every word must match, each as a case-insensitive substring, so a one-letter text is a legal query
  returning whatever fits in 25 rows. Send the longest distinguishing fragment, not a word.
- **A row matches on the name of the row it links to.** The pair under `attributes.links` is part of
  what is searched, so a Version whose `code` holds none of the text is returned because its `entity`
  is a Shot whose name does. Read `attributes.links` before deciding a row is a false positive.
- `description` is not searched, on Shot or on Asset, and neither is any other field measured here.
  A search over descriptions or note bodies is `POST /entity/<type>/_search` with `contains`.
- Rows come back shortest name first, across types, and the order does not change with the order the
  `entity_types` keys are given in. Three Shots created longest-name-first came back shortest first,
  so it is neither id nor creation order. A short generic name outranks a longer exact one, and with
  the cap at 25 the row a caller wants can be off the page: narrow with the per-type filter.
- On the probed site, one call over 14 types took 331-369 ms and the same words asked as one
  `contains` `_search` per type in sequence took 3811-3859 ms over four runs, about 270 ms a call.
  One call is worth it for a picker; a client that needs the full row still re-reads by `links.self`.
