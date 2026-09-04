---
endpoint: POST /subscription_seat/user_subscriptions
tags: [discovery, user, write, error-handling]
scope: api
measured: site-wide, rejections only
verdict: Body is a bare hash of user id to subscription string, not a JSON:API document. An unknown id is a whole-request 400, and a hash naming no user is a 200 returning `{}`.
---

# POST /subscription_seat/user_subscriptions

Assigns subscriptions to users, site-wide and for every user named in one call. The success path
was not exercised; see **Edge cases**.

**Params**

| part | value |
|---|---|
| body | a hash. Each key a HumanUser id, each value a subscription name. No `data`, no `attributes` |
| `Content-Type` | `application/json`. The vendor array type of `_search` is not needed |

**Sample requests**

A hash that names no user, which assigns nothing:

```python
r = c.post("/subscription_seat/user_subscriptions", json={})
```

```json
{}
```

A user id that is not on the site:

```python
r = c.post("/subscription_seat/user_subscriptions",
           json={"999999999": "definitely_not_a_subscription"})
```

```json
[{"id": "031d95c876d98d715e3fa9e5f4ccfaa4", "status": 400, "code": 103,
  "title": "Invalid humanUserId 999999999", "source": {}, "detail": null, "meta": null}]
```

A list where a hash is wanted:

```python
r = c.post("/subscription_seat/user_subscriptions",
           json=[{"999999999": "definitely_not_a_subscription"}])
```

```json
[{"id": "ddbb3576c29de17d5ea49e8531629931", "status": 400, "code": 103,
  "title": "Invalid JSON body. Expected Hash but received Array.", "source": {}, "detail": null,
  "meta": null}]
```

A key that is not a number:

```python
r = c.post("/subscription_seat/user_subscriptions",
           json={"definitely_not_a_user": "definitely_not_a_subscription"})
```

```json
[{"id": "22d78aa52f7e00aadc363704c26aad32", "status": 400, "code": 103,
  "title": "Invalid humanUserId definitely_not_a_user", "source": {}, "detail": null, "meta": null}]
```

**Response codes**

| status | when |
|---|---|
| 200 | every named user was assigned. The body is a hash of user id to `null` |
| 207 | at least one user failed. Same hash, the failed ones holding an error string |
| 400 | `Invalid humanUserId <key>` for any key that is not an id on the site |
| 400 | `Invalid JSON body. Expected Hash but received Array.` |
| 401 | `Request rejected due to invalid credentials.` |
| 404 | `Record does not exist.` |

**Edge cases**

- **The success path is deliberately unexercised.** Every call that could succeed changes the
  subscription of a real user of a real site, and there is no dry-run parameter and no undo. The
  rejections above are what pins the body shape; the 200 and 207 rows come from the site's own
  `/spec.json`.
- `{}` answers 200 with `{}`. A caller that treats a 200 as "the assignment happened" cannot tell an
  applied change from a body that named nobody.
- The whole request fails on the first unknown id: the 400 replaces the per-user hash, so nothing is
  reported about the ids that were valid. Validate ids against `/entity/human_users` first.
- A per-user failure is a **207**, not a 400, and its message is a string inside the hash rather than
  in an `errors` array. A client checking `r.ok` passes straight over it.
- The error message is in `title`. `detail` is `null`, `source` is `{}`.

**Links**

- `endpoints/get_subscription_seat_user_subscriptions`
- `endpoints/get_license_info`
- `findings/047_site_facts_and_the_working_week`