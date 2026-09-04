---
endpoint: GET /webhook/hooks/<hook_id>/deliveries
tags: [webhook, delivery, paging, filter]
scope: api
measured: called against a hook with no deliveries, and against the one site hook reporting 29
verdict: Takes status, entity_type, entity_id, from and acknowledgement as query params and answers 200 with zero rows for any of them. No delivery was observed, so the record shape is unprobed.
---

# GET /webhook/hooks/<hook_id>/deliveries

**Params**

| part | value |
|---|---|
| `status` | `delivered`, `failed` |
| `entity_type`, `entity_id` | narrow to one record |
| `from` | a unix timestamp |
| `acknowledgement` | substring match |

**Sample requests**

```python
r = c.get(f"/webhook/hooks/{uuid}/deliveries", params={"status": "failed"})
```

```json
{ "data": [], "included": [],
  "performance_metrics": { "event_count": 0, "event_time_span": 0, "process_time_sum": 0,
    "mean_process_time": 0, "max_process_time": 0, "min_process_time": 0,
    "end_event_time": 0, "start_event_time": 0, "process_time_ratio": 0 },
  "links": { "self": "/api/v1/webhook/hooks/<uuid>/deliveries",
             "next": "/api/v1/webhook/hooks/<uuid>/deliveries?page%5Bnumber%5D=2&page%5Bsize%5D=500" } }
```

**Response codes**

| status | when |
|---|---|
| 200 | including for a `status` the enum does not have, and for a `from` in the future |
| 404 | the hook does not exist |

**Edge cases**

- The body has `included` and `performance_metrics` alongside `data`. `performance_metrics` reports
  zeros rather than being absent when there is nothing to measure.
- **The record shape is unprobed.** No delivery was observed on the probed site, so the keys of a
  delivery, its response code and its timing fields are unknown here.
- **`num_deliveries` and this listing disagree in both directions, and what the counter counts is
  unmeasured.** On the probed site one hook reports `num_deliveries: 29` and returns zero records,
  and a hook that returns two records reports `num_deliveries: 0`. The guide says records are kept
  seven days, which explains the first case and not the second. Neither field alone answers "has this
  hook ever delivered"; read both.

**Links**

- `endpoints/get_webhook_deliveries_record_uuid`
- `findings/045_webhooks`
