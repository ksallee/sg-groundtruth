---
endpoint: POST /auth/access_token
tags: [auth, token, client]
scope: api
measured: site-wide, one token minted
verdict: Form-encode it. `application/json` is 415 naming the one legal type, and the 600s bearer is cheaper to re-mint than the refresh_token is to use.
---

# POST /auth/access_token

The only call that takes no bearer token, because it is where the bearer comes from.

**Params**

| part | value |
|---|---|
| `Content-Type` | `application/x-www-form-urlencoded`. The only one accepted |
| `grant_type` | `client_credentials`, `password` or `session_token` (probe 027). Not `authorization_code` |
| `client_id` | the script name, for `client_credentials` |
| `client_secret` | the script key |

**Sample requests**

A script token:

```python
import requests
r = requests.post(f"{c.site}/api/v1/auth/access_token",
                  data={"grant_type": "client_credentials",
                        "client_id": "<script name>", "client_secret": "<script key>"},
                  headers={"Accept": "application/json"})
```

```json
{
  "token_type": "Bearer",
  "access_token": "<token>",
  "expires_in": 600,
  "refresh_token": "<token>"
}
```

The same body under a JSON content type:

```python
r = requests.post(f"{c.site}/api/v1/auth/access_token",
                  json={"grant_type": "client_credentials"},
                  headers={"Accept": "application/json"})
```

```json
{"errors": [{"status": 415, "code": 103,
             "title": "Unsupported Content-Type 'application/json'",
             "source": {"content_type": "Content-Type must be one of: 'application/x-www-form-urlencoded'"}}]}
```

**Response codes**

| status | when |
|---|---|
| 200 | the token, `expires_in` 600 |
| 400 | `Unsupported grant_type` |
| 400 | `Missing or invalid authentication arguments` for an absent `client_secret` |
| 415 | `Unsupported Content-Type 'application/json'` |

**Edge cases**

- A wrong `Content-Type` is reported as a problem with the body, not the header. Sending
  `application/json` is 415 here, and probe 001 records the form body under a JSON content type
  reaching `400 Invalid JSON body ... Empty input`. Neither error says "header".
- `refresh_token` is a second bearer credential in the response. Redact it wherever the access token is
  redacted; it is the value `_lib.scrub` used to let through.
- 600 seconds is short enough that a long job re-auths mid-run. Refreshing a minute early costs one call
  and removes the refresh path entirely.

**Links**

- `endpoints/get_root`
- `findings/001_auth`
- `findings/027_auth_permissions`