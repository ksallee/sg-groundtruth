---
endpoint: GET /internal_api/session
coverage: measured
tags: [auth, token, user, launcher]
scope: api
measured: site-wide, one person's session read before and after every kind of activity
verdict: With the session token as the `_session_id` cookie, answers when the session and the licence lease expire, in epoch seconds. Reading it does not renew anything. 401 without the cookie.
---

# GET /internal_api/session

The call the web app's own session checker makes. The launcher's `sessionToken` is that page's
`_session_id` cookie, so a client holding one can ask the same question: how long is this session good
for, and is it still alive.

**Params**

| part | value |
|---|---|
| path | `<site>/internal_api/session`, not under `/api/v1` |
| `Cookie` | `_session_id=<session token>`. The only credential it takes |
| `Authorization: Bearer` | ignored. A REST bearer alone is 401 |

**Sample requests**

```python
r = requests.get(f"{site}/internal_api/session", cookies={"_session_id": session_token}, timeout=30)
```

```json
{"app": {"createdAt": 1788889023, "expiresAt": 1788975423, "forceExpiresAt": null},
 "license": {"createdAt": 1788881738, "expiresAt": 1788968138},
 "expirationReason": "session", "expired": false,
 "expiresAt": 1788975423, "notifyAt": 1788974523,
 "sessionInitUrl": "<site>/forge/init_auth..."}
```

Without the cookie, or with a REST bearer instead of it:

```json
{"message": "Unauthorized"}
```

**Response codes**

| status | when |
|---|---|
| 200 | the session is known. `expired` says whether it is still good |
| 401 | no `_session_id` cookie, or one the site no longer holds |

**Edge cases**

- Timestamps are epoch seconds. On the probed site `expiresAt - createdAt` is 86400 on both `app` and
  `license`, which is the site's `User Session Expiry` preference reading one day, and `notifyAt` is
  `expiresAt - 900`.
- `expiresAt` is a sliding window, and this call does not slide it. Two reads five seconds apart return
  the same value. What moves it is any spend of the session token: `POST /auth/access_token` with
  `grant_type=session_token`, `POST /internal_api/session`, or the licence renewal
  (`052_app_session_launcher`). A mint moves it only when the last move was 300s or more ago; the
  two `POST` renewals move it every time.
- `license` is the Autodesk Identity seat lease, separate from the session and renewed separately by
  `POST /internal_api/autodesk_identity/license_renewal`. `expirationReason` names which of the two the
  top-level `expiresAt` reports.
- The error envelope is `{"message": ...}`, as on every `/internal_api` call, not the `errors[]` array.

**Links**

- `endpoints/post_internal_api_session`
- `endpoints/post_internal_api_autodesk_identity_license_renewal`
- `endpoints/put_internal_api_app_session_request_id`
- `findings/052_app_session_launcher`
