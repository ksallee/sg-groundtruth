---
endpoint: POST /internal_api/app_session_request
coverage: measured
tags: [auth, token, user, launcher]
scope: api
measured: site-wide, six requests created, two approved by a person
verdict: Send `appName` and `machineId`, form or JSON, with no token and no cookie. The answer is a `sessionRequestId` to poll and a `url` a logged-in person opens in a browser to approve.
---

# POST /internal_api/app_session_request

Step one of the App Session Launcher: the browser-approved login that a desktop client uses instead of
a password on a site whose logins belong to Autodesk Identity. Outside `/api/v1`, undocumented, and
advertised only by `authentication_app_session_launcher_enabled` in the root document (`GET /`).

**A person has to approve it.** Nothing a client sends here produces a token. The token is handed out by
`PUT /internal_api/app_session_request/<sessionRequestId>` after someone logged into the site in a
browser opens `url` and clicks approve.

**Params**

| part | value |
|---|---|
| path | `<site>/internal_api/app_session_request`, not under `/api/v1` |
| auth | none. No `Authorization`, no cookie |
| `Content-Type` | `application/x-www-form-urlencoded` or `application/json`, both accepted |
| `appName` | required. The name shown to the person approving |
| `machineId` | required. Any string; the poll does not check it |

**Sample requests**

```python
import requests
r = requests.post(f"{site}/internal_api/app_session_request",
                  data={"appName": "my tool", "machineId": platform.node()}, timeout=30)
```

```json
{"sessionRequestId": "<id>", "url": "<site>/app_session_request/<id>?sticky_id=<id>"}
```

The same call with nothing in the body:

```json
{"message": "Missing params: appName, machineId"}
```

**Response codes**

| status | when |
|---|---|
| 200 | the request exists; `sessionRequestId` and `url` are the only keys |
| 400 | `Missing params: appName, machineId`, or `Missing params: machineId`. Names every absent one |
| 404 | `GET` on this path. JSON:API envelope, code 103 |

**Edge cases**

- The error envelope is `{"message": ...}`, not the `errors[]` envelope every `/api/v1` call answers with.
  A client that reads `errors[0].title` reads nothing here.
- `url` opened without a site cookie answers 302 to the site's login page with the approval page as
  `return_path`, so the person logs in with whatever the site uses, Autodesk Identity included, and lands
  back on the approval.
- A request nobody approves is forgotten after about five minutes (`052_app_session_launcher`), so a
  client waiting on a person has to be ready to issue a new one and show the new `url`.
- On the probed site `user_authentication_method` is `oxygen`, so this is the only way a person, rather
  than a script, reaches the REST API there.

**Links**

- `endpoints/put_internal_api_app_session_request_id`
- `endpoints/post_auth_access_token`
- `endpoints/get_root`
- `findings/052_app_session_launcher`
