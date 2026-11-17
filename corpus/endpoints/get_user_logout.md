---
endpoint: GET /user/logout
coverage: untested
unmeasured: whether it ends a live session. Only answered with no cookie and a cookie no session holds; a live token needs a person to approve 131 --login. Blocked on the work
tags: [auth, launcher]
scope: api
measured: site-wide, no cookie and a random `_session_id`, GET and POST
verdict: The web app's sign-out route. Without a live session, GET and POST both answer 302 to `/user/login`. Whether it ends the session behind a launcher token is unmeasured.
---

# GET /user/logout

The sign-out route of the web app, outside `/api/v1` and undocumented. It is the one sign-out
candidate on the probed site that answers at all: `DELETE /internal_api/session`,
`DELETE /auth/access_token` and `POST /auth/revoke` are 404 code 103 (`131_session_revoke`).

**Params**

| part | value |
|---|---|
| path | `<site>/user/logout`, not under `/api/v1` |
| `Cookie` | `_session_id=<session token>`, the launcher's `sessionToken` (`052_app_session_launcher`) |
| method | `GET` and `POST` answer the same without a session |

**Sample requests**

```python
r = requests.get(f"{site}/user/logout", cookies={"_session_id": session_token},
                 allow_redirects=False, timeout=30)
```

```
302 text/html; charset=utf-8  location <site>/user/login
```

**Response codes**

| status | when |
|---|---|
| 302 | no cookie, or a `_session_id` no session holds. `location` is `<site>/user/login` |

**Edge cases**

- A 302 to the login page says nothing about the session. Read `GET /internal_api/session` after it:
  401 means the session ended, 200 means it did not.

**Links**

- `endpoints/get_internal_api_session`
- `findings/131_session_revoke`
- `findings/052_app_session_launcher`
