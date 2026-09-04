---
endpoint: GET /license_info
coverage: measured
tags: [discovery, user, read-only]
scope: api
measured: site-wide
verdict: Seat counts in a `{data, status}` envelope, not the JSON:API one. `rule` decides whether `free` is a number or `-1` for unlimited, and none of the three counts equals the HumanUser row count.
---

# GET /license_info

How many seats the site has and how many are spoken for. The only call that answers it.

**Params**

| part | value |
|---|---|
| (none) | takes no parameter. An unknown query parameter is ignored, still 200 |

**Sample requests**

```python
r = c.get("/license_info")
```

On the probed site, 104 bytes:

```json
{
  "data": {"assigned": 4, "rule": "quantity", "free": 46, "total": 50, "type": "license-count"},
  "status": "success"
}
```

An unknown query parameter changes nothing:

```python
r = c.get("/license_info", params={"prefs": "hours_per_day"})
```

```json
{
  "data": {"assigned": 4, "rule": "quantity", "free": 46, "total": 50, "type": "license-count"},
  "status": "success"
}
```

| key | type | means |
|---|---|---|
| `total` | integer | seats the site is licensed for |
| `assigned` | integer | seats spoken for |
| `free` | integer | `total - assigned` under `rule: quantity`; `-1` under `rule: unlimited` |
| `rule` | string | `quantity` or `unlimited`. Read it before reading `free` |
| `type` | string | `license-count` on the probed site |

**Response codes**

| status | when |
|---|---|
| 200 | always, including with an unrecognised query parameter |
| 401 | `Request rejected due to invalid credentials.` |

**Edge cases**

- The envelope is `{"data": ..., "status": "success"}`. There is no `links` and no `links.self`, so
  a client that reads every response through a JSON:API decoder fails on this one.
- The site's own `/spec.json` example gives the five values as strings (`"assigned": "56"`). The site
  returns integers. Type-check rather than trusting the example.
- `free` is `-1`, not `0` or `null`, when `rule` is `unlimited`. Subtracting it from `total` gives a
  number larger than the licence.
- `assigned` is not the HumanUser row count and not the size of the
  `GET /subscription_seat/user_subscriptions` hash. On the probed site the three were 4, 24 and 14.
  Do not derive one from another.
- `/spec.json` marks this call with the `sudo_as_login` security scope. A script token reads it
  without one.

**Links**

- `endpoints/get_subscription_seat_user_subscriptions`
- `endpoints/get_preferences`
- `findings/047_site_facts_and_the_working_week`