---
endpoint: POST /internal_api/autodesk_identity/license_renewal
coverage: measured
tags: [auth, user, launcher]
scope: api
measured: site-wide, one person's licence lease renewed and read back
verdict: Renews the Autodesk Identity licence lease behind the `_session_id` cookie: `{"message": "OK"}` and `license.expiresAt` moves to now plus one day. 401 without the cookie.
---

# POST /internal_api/autodesk_identity/license_renewal

The third call in the web app's session checker. A person's browser session on an Autodesk Identity
site has two clocks, the site session and the seat licence, and this renews the second.

**Params**

| part | value |
|---|---|
| path | `<site>/internal_api/autodesk_identity/license_renewal` |
| `Cookie` | `_session_id=<session token>` |
| body | none |

**Sample requests**

```python
r = requests.post(f"{site}/internal_api/autodesk_identity/license_renewal",
                  cookies={"_session_id": session_token}, timeout=30)
```

```json
{"message": "OK"}
```

`GET /internal_api/session` read back before and after, on the probed site:

```
before  license {"createdAt": 1788881738, "expiresAt": 1788968138}
after   license {"createdAt": 1788889410, "expiresAt": 1788975810}     both reset to now
```

**Response codes**

| status | when |
|---|---|
| 200 | renewed |
| 401 | no `_session_id` cookie |
| 404 | `GET` on this path. JSON:API envelope, code 103 |

**Edge cases**

- It also moves the session's own `expiresAt`, so one call renews both clocks.
- Whether a REST bearer can still be minted once `license.expiresAt` has passed while the session is
  alive is not measured. On the probed site the licence lease started at the person's browser login and
  the session at the approval, so the licence is the one that runs out first.
- Only measured on a site whose `user_authentication_method` is `oxygen`. What it answers on a site
  without Autodesk Identity is not measured.

**Links**

- `endpoints/get_internal_api_session`
- `endpoints/post_internal_api_session`
- `findings/052_app_session_launcher`
