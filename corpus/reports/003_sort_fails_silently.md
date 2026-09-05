---
evidence: [findings/026_result_order, findings/028_loud_and_silent, findings/017_filter_operators]
endpoints: [GET /entity/<type>, POST /entity/<type>/_search]
kind: api
status: unreported
scope: api
confirmed: 2026-09-04
measured: first sample project, Versions, read only
summary: A sort on an unknown or unsortable field answers 200 with the rows in default order, while the same field name in a filter answers 400 and names the reason.
---

# 003_sort_fails_silently

**Expected** A `sort` naming a field that does not exist, or one whose `data_type` cannot be sorted, is
rejected the way the same name is rejected in a filter.

**Actual** One request, two parameters, two contracts. Every row below is the same field name sent
against the same type:

| field | in `sort` | in a filter |
|---|---|---|
| `sg_not_a_field_at_all` | `200`, rows in default order | `400 API read() Version.sg_not_a_field_at_all doesn't exist.` |
| `open_notes_count` (`summary`) | `200`, rows in default order | `400 API read() Version.open_notes_count's 'summary' data type cannot be used in a filter.` |
| `sg_uploaded_movie` (`url`) | `200`, rows in default order | `400 API read() Version.sg_uploaded_movie's 'url' data type cannot be used in a filter.` |

Only the syntax of `sort` is validated, and there it is exact:

| sent | result |
|---|---|
| `sort=` | `400 {"sort": ["sort must be filled"]}` |
| `sort=id desc` | `400 {"sort": ["sort list is not valid"]}` |
| `sort=+id` | `400 {"sort": ["sort list is not valid"]}` |
| `"sort": [{"field_name": "id", "direction": "desc"}]` on `_search` | `400 {"sort": ["sort array is not valid"]}` |

An accepted-and-ignored sort returns the default order, which is `id` ascending. A caller sorting
ascending on a mistyped field gets a response indistinguishable from a working one.

**Reproduce**

```
curl -sS "$SITE/api/v1/entity/versions?sort=sg_not_a_field_at_all&page[size]=5" \
  -H "Authorization: Bearer $TOKEN" | head
# 200, rows id ascending

curl -sS "$SITE/api/v1/entity/versions?filter[sg_not_a_field_at_all]=x" \
  -H "Authorization: Bearer $TOKEN"
# 400 API read() Version.sg_not_a_field_at_all doesn't exist.
```

**Impact** Nothing in the response says the sort was dropped, so a client cannot detect it and a test
asserting on ordering passes against `id` ascending whenever that is what the intended sort would have
produced. The cost lands on whoever reads the output: a page of "most recent" that is oldest first, with
a 200 behind it. Guarding against it means fetching `/schema/<Type>/fields` and validating every sort key
before the read, which is the expensive call.

**Proposed change** Reject an unknown or unsortable `sort` field with the 400 the same name already
produces in a filter. The message exists and names the field and the `data_type`, so the validation is a
matter of applying it on the other parameter.
