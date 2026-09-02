---
tags: [query, sort, paging, filter, dotted-field, trap]
scope: api
verdict: Rows come back id ascending unless you sort; ["id", "in", [...]] discards the order of the list, and an unsortable or unknown sort field is a silent 200 no-op where the same name in a filter 400s.
---

# 026_result_order

**Q** In what order does a read return rows, and can a caller rely on it?

**Endpoint** `GET /entity/versions ; POST /entity/versions/_search`

**Docs claim** `sort=field`, `-field` for descending. Silent on the order of an unsorted read, and on
what a sort on a field that cannot be sorted does.

**Actual**

```
1. POST _search {"filters": [["id", "in", [...]]]}, eight ids
   sent      [25529, 17055, 25553, 25493, 25541, 25481, 25517, 25505]
   returned  [17055, 25481, 25493, 25505, 25517, 25529, 25541, 25553]   id ascending
   sent ascending  -> the same eight ids, indistinguishable from honouring the list
   sent descending -> id ascending
   GET filter[id]=<comma list, shuffled>  -> id ascending
   in + sort=-id   -> [25553, 25541, 25529, 25517, 25505, 25493, 25481, 17055]

2. no sort, page[size]=25, five identical GETs -> one ordering, == sort=id, != sort=-id

3. 100 rows walked at page[size]=10, for sort= id, none, -created_at, sg_status_list, code
   every walk: 100 rows, 100 distinct, 0 duplicated, 0 missed, same order as one unpaged read

4. sort=<field>, ascending and descending, against the unsorted order
   id  code  created_at  sg_status_list  entity  entity.Shot.code  200  order changes
   open_notes_count  (summary)  200  accepted and ignored: same rows as no sort
   sg_uploaded_movie (url)      200  accepted and ignored
   sg_not_a_field_at_all        200  accepted and ignored
   sort=         -> 400 "source": {"sort": ["sort must be filled"]}
   sort=id desc  -> 400 "source": {"sort": ["sort list is not valid"]}
   sort=+id      -> 400 "source": {"sort": ["sort list is not valid"]}
   the same three names in a filter:
   sg_not_a_field_at_all -> 400 API read() Version.sg_not_a_field_at_all doesn't exist.
   open_notes_count -> 400 API read() Version.open_notes_count's 'summary' data type cannot be used in a filter.
   sg_uploaded_movie -> 400 API read() Version.sg_uploaded_movie's 'url' data type cannot be used in a filter.

5. sort=sg_status_list      first 6 [25473, 25476, 25479, 25482, 25490, 25492]
   sort=sg_status_list,id   identical to sort=sg_status_list
   sort=sg_status_list,-id  first 6 [25563, 25562, 25558, 25557, 25555, 25554]
   POST _search "sort": [{"field_name": "id", "direction": "desc"}] -> 400 {"sort": ["sort array is not valid"]}
```

**Teaches**
- `["id", "in", [...]]` returns id ascending, never the order of the list. A caller that must preserve
  a selection re-sorts against what it sent: `pos = {i: n for n, i in enumerate(ids)}`, then
  `rows.sort(key=lambda r: pos[r["id"]])`. The bug hides because an already-ascending list comes back
  looking honoured.
- With no `sort`, the order is id ascending, and it held over five identical calls. Paging is stable:
  five walks of 100 rows at `page[size]=10`, including the unsorted one and one keyed on a
  low-cardinality status, each returned every row once, in the order of the same query read unpaged.
- Sorts fail silently where filters fail loudly (probe 017). A `summary` field, a `url` field and a
  name that does not exist all return 200 with the rows in default order; the same three names in a
  filter 400 and name the reason. Only sort *syntax* errors: an empty value, a space, a leading `+`.
  There is no way to detect a dropped sort from the response, so verify a sort field against
  `/schema/<Type>/fields` before relying on it.
- Multi-key sort is comma separated with `-` per key, and id ascending is the implicit tiebreak:
  `sg_status_list,id` returned the identical page to `sg_status_list` while `sg_status_list,-id` did
  not. A dotted path sorts (`entity.Shot.code` here, and site-wide `project.Project.name` reverses
  under `-`). POST `_search` takes `"sort"` only as the same string; the array-of-objects spelling
  400s `sort array is not valid`.
