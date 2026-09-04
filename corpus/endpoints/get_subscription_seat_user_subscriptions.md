---
endpoint: GET /subscription_seat/user_subscriptions
tags: [discovery, user, read-only]
scope: api
measured: site-wide
verdict: Returns a bare hash of user id to subscription string with no `data` and no `links`, holding only some HumanUser rows, and a `null` value means the user has no subscription rather than no such user.
---

# GET /subscription_seat/user_subscriptions

Which subscription each user holds. One call, no parameters, the whole site.

**Params**

| part | value |
|---|---|
| (none) | `/spec.json` declares `"parameters": []`. There is no filter, no page and no user selector |

**Sample requests**

```python
r = c.get("/subscription_seat/user_subscriptions")
```

On the probed site, 237 bytes for 14 keys. Ids replaced with placeholders:

```json
{
  "<id1>": null,
  "<id2>": "not_for_resale",
  "<id3>": "not_for_resale",
  "<id4>": null
}
```

The response is the hash. There is no `data` key wrapping it and no `links`.

| part | shape |
|---|---|
| key | the HumanUser id as a **string**, never an integer |
| value | the subscription name, or `null` |

**Response codes**

| status | when |
|---|---|
| 200 | always |
| 401 | `Request rejected due to invalid credentials.` |

**Edge cases**

- The hash holds a subset of HumanUser rows and the endpoint gives no rule for which. On the probed
  site it held 14 of 24 HumanUser rows, and `sg_status_list` did not predict membership: 5 of 6 `act`
  users were present and 9 of 18 `dis` users were too. Treat a missing key as unknown, not as
  "no subscription".
- `null` is a value in the hash, not an absence. A user present with `null` and a user absent are two
  different states and only the first one is stated.
- Keys are strings. Comparing them against an integer id from `/entity/human_users` matches nothing.
- On the probed site the only non-`null` value was `not_for_resale`. The vocabulary of subscription
  names is site data; read it off the hash rather than hardcoding a list.
- The size of this hash is not `assigned` from `GET /license_info`. On the probed site they were 14
  and 4.

**Links**

- `endpoints/post_subscription_seat_user_subscriptions`
- `endpoints/get_license_info`
- `endpoints/get_entity_type`
- `findings/047_site_facts_and_the_working_week`