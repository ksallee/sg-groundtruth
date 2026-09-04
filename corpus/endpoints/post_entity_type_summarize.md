---
endpoint: POST /entity/<type>/_summarize
tags: [query, fill-rate, cost, list-field, summary]
scope: api
measured: sample project 1 of 1
verdict: Counts without paging rows. One `grouping` returns a field's distinct values and their counts at ~300ms, so rank a shortlist with it and never scan every field.
---

# POST /entity/<type>/_summarize

**Params**

| part | value |
|---|---|
| `Content-Type` | the same vendor types `_search` requires |
| `filters` | same shape as `_search` |
| `summary_fields` | `[{"field": "id", "type": "count"}]` |
| `grouping` | `[{"field": ..., "type": "exact", "direction": "asc"}]`. Optional |

**Sample requests**

Grouped, which is the call worth making:

```python
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
r = c.post("/entity/versions/_summarize", headers=ARR,
           json={"filters": [["project", "is", {"type": "Project", "id": 70}]],
                 "summary_fields": [{"field": "id", "type": "count"}],
                 "grouping": [{"field": "sg_status_list", "type": "exact", "direction": "asc"}]})
```

```json
{
  "data": {
    "summaries": { "id": 100 },
    "groups": [
      { "group_name": "na", "group_value": "na", "summaries": { "id": 28 } }
    ]
  }
}
```

Ungrouped, where the whole body is 45 bytes:

```python
r = c.post("/entity/versions/_summarize", headers=ARR,
           json={"filters": [["project", "is", {"type": "Project", "id": 70}]],
                 "summary_fields": [{"field": "id", "type": "count"}]})
```

```json
{ "summaries": { "id": 100 }, "groups": [] }
```

**Response codes**

| status | when |
|---|---|
| 200 | including for a field that cannot be summarized, where the body is near-empty |

**Edge cases**

- Summarizing an unsummarizable field, `image`, answers 200 with a 37-byte body and no summary. It does
  not 400. Test that the key you asked for is in `summaries` before reading it.
- `group_name` is the rendered label and `group_value` the raw one. For a `timecode` field the rendered
  form is `HH:MM:SS:FF`, which is how the frame rate is recovered when no field exposes it.
- One call per field at about 300ms. Over 71 fields that is 21 seconds. Rank a shortlist by fill rate
  first and summarize only the candidates.

**Links**

- `endpoints/post_entity_type_search`
- `field_types/timecode`
- `field_types/summary`
- `findings/020_summarize`