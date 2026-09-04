---
endpoint: GET /preferences
tags: [schema, duration, discovery]
scope: api
measured: site-wide
verdict: The only place the unit behind a `duration` field is named. `prefs` narrows it to one key, and `hours_per_day` and `duration_units` are the pair a renderer needs.
---

# GET /preferences

A `duration` is a bare integer of minutes and no schema property says so (`field_types/duration`). This
is where the unit lives.

**Params**

| part | value |
|---|---|
| `prefs` | optional. A preference name, or a comma list; returns those keys alone |

**Sample requests**

Narrowed, which is the form worth calling:

```python
r = c.get("/preferences", params={"prefs": "hours_per_day"})
```

```json
{
  "data": { "hours_per_day": 8.0 },
  "links": { "self": "/api/v1/preferences?prefs=hours_per_day" }
}
```

Unnarrowed, 6131 bytes on the probed site. The keys a client reads:

| key | on the probed site | what it decides |
|---|---|---|
| `duration_units` | `days` | whether to render a duration in hours or days |
| `hours_per_day` | `8.0` | the divisor when it is days |
| `format_date_fields` | `08/04/22 OR 04/08/22 ...` | day/month order for display |
| `date_component_order` | `month_day` | the same, machine readable |
| `support_local_storage` | `true` | whether `PublishedFile.path` resolves per platform (probe 021) |

**Response codes**

| status | when |
|---|---|
| 200 | always, including for an unknown `prefs` name, which returns `{}` |

**Edge cases**

- `view_master_settings` and `creative_review_settings` are JSON encoded inside a string, not nested
  objects. Decode them a second time.
- `hours_per_day` is a float, `8.0`, not an integer.
- An unknown `prefs` name is not an error. The key is absent from `data` and the status is 200, so test
  for the key rather than the status.

**Links**

- `field_types/duration`
- `field_types/timecode`
- `findings/021_media_resolution`