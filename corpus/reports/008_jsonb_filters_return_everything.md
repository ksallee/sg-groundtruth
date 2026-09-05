---
evidence: [findings/023_pages, findings/field_types/jsonb]
endpoints: [POST /entity/<type>/_search, GET /entity/<type>]
kind: api
status: unreported
scope: api
confirmed: 2026-09-04
measured: first sample project, plus the site-wide PageSetting and EventLogEntry listings, read only
summary: A filter on PageSetting.settings_json or EventLogEntry.audit_trail is accepted and ignored, so the unfiltered set comes back at 200 and is_null and is_not_null each return every row.
---

# 008_jsonb_filters_return_everything

**Expected** A filter the schema advertises as valid either narrows the result or is rejected. `is null`
and `is_not null` over one field partition the rows between them.

**Actual** On `PageSetting.settings_json`, on the probed site:

| filter | rows returned |
|---|---|
| `contains "ZZZNOPE"` | 30145, the whole table |
| `is null` | 30145 |
| `is_not null` | 30145 |
| `[["page", "is", null]]`, another field on the same type | 26372 |

The endpoint filters correctly and this field does not. `is null` and `is_not null` each return every
row, so the two together count every row twice.

`EventLogEntry.audit_trail` behaves the same way: any operator returns the unfiltered page. That field
is also dropped from every response, named in `fields` or not, so it can be neither read nor selected
on.

Both fields are `jsonb` and both enumerate a relation vocabulary when sent a bogus operator, which is
what makes them look filterable:

```
[["meta", "definitely_not_an_operator", null]] -> 400
 "source": {"Note.meta": " ... Valid relations: [\"is\",\"is_not\",\"contains\",\"not_contains\"]"}
```

`Note.meta`, a third `jsonb` field, filters correctly on all four.

**Reproduce**

```
curl -sS -X POST "$SITE/api/v1/entity/page_settings/_search" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/vnd+shotgun.api3_hash+json" \
  -d '{"filters":[["settings_json","contains","ZZZNOPE"]],"page":{"size":1}}'
# 200, and the paging links describe the whole table

curl -sS -X POST "$SITE/api/v1/entity/page_settings/_search" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/vnd+shotgun.api3_hash+json" \
  -d '{"filters":[["settings_json","is",null]],"page":{"size":1}}'
# 200, the same count. is_not null returns it too
```

**Impact** A client that filters a `jsonb` field believes it narrowed and processes the whole table.
Where the filter was the safety check, every row is treated as a match. The failure scales with the
table: 30145 rows on the probed site, and nothing in the response says the filter was dropped. The
`Valid relations` list returned by the 400 tells a caller the operator is supported, so the natural way
to discover the vocabulary confirms behaviour the server does not have.

**Proposed change** Apply the filter, or reject an operator on these fields with the 400 that an
unsupported relation already produces. A field that enumerates a relation vocabulary and then ignores
every one of them is the worst of the three options.
