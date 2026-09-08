---
endpoint: POST /internal_api/session
coverage: measured
tags: [auth, token, user, launcher]
scope: api
measured: site-wide, one person's session renewed and read back
verdict: Renews the session behind the `_session_id` cookie: `{"message": "OK"}` and `expiresAt` moves to now plus the site's expiry window. 401 without the cookie.
---

# POST /internal_api/session

The renew half of the web app's session checker. A client that wants a session to outlive the site's
idle window calls this, or spends the session token at the token endpoint, before the window closes.

**Params**

| part | value |
|---|---|
| path | `<site>/internal_api/session` |
| `Cookie` | `_session_id=<session token>` |
| body | none |

**Sample requests**

```python
r = requests.post(f"{site}/internal_api/session", cookies={"_session_id": session_token}, timeout=30)
```

```json
{"message": "OK"}
```

`GET /internal_api/session` read back before and after, on the probed site:

```
before  expiresAt 1788975773
after   expiresAt 1788975774      now + 86400
```

**Response codes**

| status | when |
|---|---|
| 200 | renewed |
| 401 | no `_session_id` cookie, or one the site no longer holds |

**Edge cases**

- It is not needed to keep a REST client alive: minting a bearer with `grant_type=session_token` moves
  `expiresAt` by the same amount (`052_app_session_launcher`). It is the call for a client that holds a
  session token and has nothing to mint for a while.
- The web app calls it only when the page saw input in the last three minutes; a client renewing on a
  timer keeps a session alive indefinitely, which is the behaviour the site's `User Session Expiry`
  preference exists to bound. Renew on use, not on a clock.

**Links**

- `endpoints/get_internal_api_session`
- `endpoints/post_auth_access_token`
- `findings/052_app_session_launcher`
